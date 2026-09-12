from backend.rag.vector import rrf, mmr, VectorRetriever
from backend.config import Settings
from backend.rag.models import Document, Section


class FixedEmbeddings:
    model = 'test-fixture-not-real-model'
    def encode(self, texts, charge=lambda: None):
        return [[1., 0.] if 'ramen' in t.lower() else [0., 1.] for t in texts]


def test_rrf_combines_rankings_without_duplicate_votes():
    assert rrf([['a', 'a', 'b'], ['b', 'c']])[0] == 'b'


def test_mmr_avoids_nearly_identical_candidates():
    result = mmr([1, 0], [[1, 0], [.999, .001], [.5, .866]], 2, weight=.2)
    assert result == [0, 2]


def test_chroma_explicit_vectors_survive_reopen(tmp_path):
    docs = [Document(source_id='test', title='Food', doc_type='html', url='https://example.com',
                     language='en', publisher='test', license_note='fixture', content_hash='fixture',
                     sections=[Section(section_path='Ramen', text='Ramen noodles in broth.'),
                               Section(section_path='Sushi', text='Sushi rice and fish.')])]
    settings = Settings(data_dir=tmp_path, retrieval_mode='similarity')
    first = VectorRetriever(docs, settings, embedder=FixedEmbeddings())
    assert first.build()['count'] == 2
    reopened = VectorRetriever(docs, settings, embedder=FixedEmbeddings())
    assert 'Ramen' in reopened.search('ramen', 1)[0].section_path
    assert reopened.name == first.name


def test_candidate_pool_grows_with_top_k(tmp_path):
    # 30 distinct single-section documents so chunking produces exactly 30 chunks,
    # with embeddings placed on an arc so similarity to the query strictly decreases
    # with index - chunk 29 is the worst match and would fall outside a fixed top-20 pool.
    import math

    class ArcEmbeddings:
        model = 'test-fixture-arc'
        def encode(self, texts, charge=lambda: None):
            vectors = []
            for text in texts:
                index = int(text.rsplit('-', 1)[-1])
                angle = index * 0.02
                vectors.append([math.cos(angle), math.sin(angle)])
            return vectors

    docs = [
        Document(source_id=f'doc-{i}', title=f'Food {i}', doc_type='html', url='https://example.com',
                 language='en', publisher='test', license_note='fixture', content_hash=f'fixture-{i}',
                 sections=[Section(section_path=f'Food {i}', text=f'food-{i}')])
        for i in range(30)
    ]
    settings = Settings(data_dir=tmp_path, retrieval_mode='similarity')
    retriever = VectorRetriever(docs, settings, embedder=ArcEmbeddings())
    retriever.build()

    # Query aligned with chunk 0 (angle 0); with the old fixed n_results=20, chunk 29
    # (the worst match) could never be returned no matter what top_k was requested.
    result = retriever.search('food-0', top_k=30)
    assert len(result) == 30
    assert any('food-29' in c.text for c in result)
