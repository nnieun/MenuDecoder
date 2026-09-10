"""Print chunk-count/length distribution per source x chunk size.

menu_project_plan.md 4절: "각 크기의 실제 길이 분포·청크 수·섹션 분할
수를 먼저 확인한다." 비교 실험(EX-01)을 시작하기 전에 코퍼스가 세 크기
사이에 실제로 차이를 만들 만큼 충분히 긴지 눈으로 확인하기 위한 스크립트.

Run with: .venv/Scripts/python -m backend.rag.stats
"""
from pathlib import Path

from .chunking import CHUNK_SIZES, chunk_document
from .models import Document

DOCS_DIR = Path(__file__).parent / 'documents'


def load_documents() -> list[Document]:
    docs = []
    for path in sorted(DOCS_DIR.glob('*.json')):
        if path.name == 'manifest.json':
            continue
        docs.append(Document.model_validate_json(path.read_text(encoding='utf-8')))
    return docs


def main():
    docs = load_documents()
    if not docs:
        print('no documents collected yet; run `python -m backend.rag.collect` first')
        return
    print(f'{len(docs)} documents, {sum(len(d.sections) for d in docs)} sections total\n')
    for size in CHUNK_SIZES:
        total_chunks = 0
        total_tokens = 0
        print(f'--- chunk_size={size} ---')
        for doc in docs:
            chunks = chunk_document(doc, chunk_size=size)
            total_chunks += len(chunks)
            total_tokens += sum(c.token_count for c in chunks)
            token_counts = [c.token_count for c in chunks]
            print(f'  {doc.source_id:16s} sections={len(doc.sections):3d} chunks={len(chunks):3d} '
                  f'tokens(min/avg/max)={min(token_counts):4d}/{sum(token_counts)//len(token_counts):4d}/{max(token_counts):4d}')
        print(f'  TOTAL chunks={total_chunks} avg_tokens={total_tokens // total_chunks}\n')


if __name__ == '__main__':
    main()
