"""BM25 retriever over the collected+chunked corpus (RAG 7단계의 '단계 5. Retriever' 중 BM25만).

의도적으로 임베딩(OpenAI/BGE-M3)·Chroma·Hybrid·Reranking은 아직 넣지
않았다. menu_project_plan.md 8절 "비용을 줄이면서 모든 비교를 하는
순서"의 취지대로, 먼저 비용이 들지 않는 검색(BM25)으로 프롬프트·인용
연결부터 실제로 동작시키고, 임베딩·Hybrid·Reranking 비교는 EX-01~EX-06의
별도 실험으로 남긴다. 이 모듈이 그 실험들의 최종 형태라고 주장하지
않는다 — 지금은 describe()/answer()가 실제 근거를 인용할 수 있게 하는
최소 구현이다.
"""
import re
import unicodedata
from functools import lru_cache

from rank_bm25 import BM25Okapi

from .chunking import chunk_document
from .models import Chunk, Document
from .stats import load_documents

DEFAULT_CHUNK_SIZE = 512  # menu_project_plan.md 4절의 초기 기준값 제안
DEFAULT_TOP_K = 5

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
# Query expansion v1 for the English corpus; original source text stays intact.
ALIASES = {
    'ramen': ('라멘', '라면', 'ラーメン', 'らーめん'),
    'yakitori': ('야키토리', '焼き鳥', '焼鳥'),
    'sushi': ('스시', '초밥', '寿司', '鮨', 'すし'),
    'sashimi': ('사시미', '생선회', '刺身', '刺し身'),
    'tempura': ('덴푸라', '텐푸라', '天ぷら', '天麩羅'),
    'izakaya': ('이자카야', '居酒屋'),
    'miso': ('미소', '된장', '味噌', 'みそ'),
    'soy sauce': ('간장', '쇼유', '醤油', 'しょうゆ'),
    'pork': ('돼지고기', '豚肉'),
    'chicken': ('닭고기', '鶏肉'),
    'broth': ('육수', '국물', '出汁', 'だし'),
}

@lru_cache(maxsize=1)
def _japanese_tokenizer():
    from sudachipy import dictionary
    return dictionary.Dictionary().create()



def _tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize('NFKC', text).lower()
    expanded = []
    for english, aliases in ALIASES.items():
        if any(alias in normalized for alias in aliases):
            expanded.extend(english.split())
    tokens = []
    for word in _TOKEN_RE.findall(normalized):
        if re.search(r'[\u3040-\u30ff\u3400-\u9fff]', word):
            tokens.extend(m.normalized_form().lower() for m in _japanese_tokenizer().tokenize(word))
        else:
            tokens.append(word)
    return tokens + expanded


class Retriever:
    def __init__(self, documents: list[Document], chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size
        self.documents = {d.source_id: d for d in documents}
        self.chunks: list[Chunk] = []
        for doc in documents:
            self.chunks.extend(chunk_document(doc, chunk_size=chunk_size))
        corpus = [_tokenize(c.text) for c in self.chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Chunk]:
        if not self._bm25 or not query.strip():
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.chunks[i] for i in ranked[:top_k] if scores[i] > 0]

    def document_for(self, source_id: str) -> Document | None:
        return self.documents.get(source_id)


@lru_cache(maxsize=1)
def default_retriever() -> Retriever:
    """Process-wide singleton: BM25 index build is a few ms but no need to repeat it per request."""
    return Retriever(load_documents())
