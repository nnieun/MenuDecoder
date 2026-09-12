"""Explicit embeddings and versioned Chroma indexes. No implicit model download."""
import hashlib
import json
from pathlib import Path

import numpy as np
from openai import OpenAI

from .retriever import Retriever


def rrf(rankings, limit=20, constant=60):
    scores = {}
    for ranking in rankings:
        for rank, identifier in enumerate(dict.fromkeys(ranking), 1):
            scores[identifier] = scores.get(identifier, 0.0) + 1 / (constant + rank)
    return sorted(scores, key=lambda identifier: (-scores[identifier], identifier))[:limit]


def mmr(query, vectors, k, weight=0.5):
    if len(vectors) == 0:
        return []
    matrix = np.asarray(vectors, dtype=float)
    matrix /= np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-12)
    q = np.asarray(query, dtype=float)
    q /= max(np.linalg.norm(q), 1e-12)
    relevance = matrix @ q
    selected = [int(np.argmax(relevance))]
    while len(selected) < min(k, len(matrix)):
        redundancy = (matrix @ matrix[selected].T).max(axis=1)
        scores = weight * relevance - (1 - weight) * redundancy
        scores[selected] = -np.inf
        selected.append(int(np.argmax(scores)))
    return selected[:k]


class Embeddings:
    def __init__(self, settings, model=None):
        self.settings = settings
        self.model = model or settings.embedding_model
        self.local = None
        self.client = None
        self.last_usage = None

    def encode(self, texts, charge=lambda: None):
        if self.model == 'BAAI/bge-m3':
            if self.local is None:
                from sentence_transformers import SentenceTransformer
                self.local = SentenceTransformer(self.model, revision=self.settings.bge_revision)
            lengths = [len(self.local.tokenizer.encode(t)) for t in texts]
            if max(lengths, default=0) > self.local.max_seq_length:
                raise ValueError('BGE input would be truncated')
            return self.local.encode(texts, normalize_embeddings=True).tolist()
        if self.client is None:
            self.client = OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.request_timeout_seconds, max_retries=0)
        charge()
        response = self.client.embeddings.create(model=self.model, input=texts)
        self.last_usage = response.usage.model_dump()
        return [d.embedding for d in sorted(response.data, key=lambda d: d.index)]


class VectorRetriever(Retriever):
    def __init__(self, documents, settings, chunk_size=512, embedder=None, client=None):
        super().__init__(documents, chunk_size)
        import chromadb
        self.settings = settings
        self.embedder = embedder or Embeddings(settings)
        self.client = client or (chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port, ssl=True)
                                 if settings.chroma_host else chromadb.PersistentClient(path=str(settings.data_dir / 'chroma')))
        fingerprint = json.dumps({'chunks': [c.model_dump() for c in self.chunks],
                                  'model': self.embedder.model, 'revision': settings.bge_revision}, sort_keys=True)
        self.version = hashlib.sha256(fingerprint.encode()).hexdigest()
        self.name = 'food-' + self.version[:24]
        self.by_id = {c.chunk_id: c for c in self.chunks}

    def build(self, charge=lambda: None):
        collection = self.client.get_or_create_collection(self.name, embedding_function=None,
            metadata={'version': self.version, 'model': self.embedder.model}, configuration={'hnsw': {'space': 'cosine'}})
        existing = set(collection.get(include=[])['ids'])
        missing = [c for c in self.chunks if c.chunk_id not in existing]
        for start in range(0, len(missing), 32):
            batch = missing[start:start + 32]
            vectors = self.embedder.encode([c.text for c in batch], charge)
            collection.upsert(ids=[c.chunk_id for c in batch], embeddings=vectors,
                              documents=[c.text for c in batch], metadatas=[{'source_id': c.source_id} for c in batch])
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        manifest = {'collection': self.name, 'version': self.version, 'model': self.embedder.model,
                    'chunk_size': self.chunk_size, 'count': collection.count(), 'chunks': [c.model_dump() for c in self.chunks]}
        (self.settings.data_dir / (self.name + '.json')).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        return manifest

    def search(self, query, top_k=5, mode=None, charge=lambda: None):
        mode = mode or self.settings.retrieval_mode
        if mode == 'bm25':
            return super().search(query, top_k)
        collection = self.client.get_collection(self.name, embedding_function=None)
        if collection.metadata.get('version') != self.version or collection.count() != len(self.chunks):
            raise ValueError('Index version/count mismatch: rebuild required')
        vector = self.embedder.encode([query], charge)[0]
        # Candidate pool must grow with top_k, or a relevant chunk ranked just
        # outside a fixed window could never surface no matter what top_k is asked for.
        pool = min(max(20, top_k * 4), len(self.chunks))
        result = collection.query(query_embeddings=[vector], n_results=pool, include=['embeddings', 'distances'])
        dense = result['ids'][0]
        if mode == 'mmr':
            selected = mmr(vector, result['embeddings'][0], top_k)
            ids = [dense[i] for i in selected]
        elif mode == 'hybrid':
            sparse = [c.chunk_id for c in super().search(query, pool)]
            ids = rrf([sparse, dense], limit=pool)
        else:
            ids = dense
        chunks = [self.by_id[i] for i in ids]
        if self.settings.reranker == 'bge':
            from sentence_transformers import CrossEncoder
            if not hasattr(self, '_reranker'):
                self._reranker = CrossEncoder('BAAI/bge-reranker-v2-m3', revision=self.settings.reranker_revision)
            scores = self._reranker.predict([(query, c.text) for c in chunks])
            chunks = [c for _, c in sorted(zip(scores, chunks), key=lambda pair: -pair[0])]
        return chunks[:top_k]


def main():
    import argparse
    from backend.config import Settings
    from .stats import load_documents
    parser = argparse.ArgumentParser(description='Build a versioned index; OpenAI embeddings incur API charges.')
    parser.add_argument('--model', default='text-embedding-3-small', choices=['text-embedding-3-small', 'BAAI/bge-m3'])
    parser.add_argument('--chunk-size', type=int, choices=[256, 512, 1024], default=512)
    args = parser.parse_args()
    settings = Settings(embedding_model=args.model)
    print(VectorRetriever(load_documents(), settings, args.chunk_size).build()['collection'])


if __name__ == '__main__':
    main()
