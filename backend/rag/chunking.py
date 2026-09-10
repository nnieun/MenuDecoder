"""Token-based chunking (RAG 7단계의 '단계 2. 청킹').

menu_project_plan.md 4절의 결정을 그대로 구현한다:
- 비교 대상 청크 크기는 256 / 512 / 1024 토큰.
- 겹침은 각 크기의 약 10%를 내림한 값으로 고정: floor(256*0.1)=25,
  floor(512*0.1)=51, floor(1024*0.1)=102.
- 섹션(음식명·제목) 경계를 먼저 보존한 뒤 토큰 길이로 분할한다.
- 제목(section_path)은 검색 본문에 포함하되 토큰 예산 안에 포함한다.
- 공통 토크나이저와 버전을 고정한다 — 여기서는 tiktoken의
  cl100k_base로 고정한다. (모델별 실제 토크나이저 차이는 임베딩 비교
  단계에서 별도로 기록한다; 지금은 청크 경계를 만드는 공통 기준일 뿐이다.)

단순 글자 수를 토큰 수로 보고하지 않기 위해, Chunk.token_count는 항상
이 토크나이저로 인코딩한 실제 토큰 수다.
"""
import math

import tiktoken

from .models import Chunk, Document

TOKENIZER_NAME = 'cl100k_base'
CHUNK_SIZES = (256, 512, 1024)

_encoding = None


def _tokenizer():
    global _encoding
    if _encoding is None:
        _encoding = tiktoken.get_encoding(TOKENIZER_NAME)
    return _encoding


def overlap_for(chunk_size: int) -> int:
    return math.floor(chunk_size * 0.1)


def chunk_document(document: Document, chunk_size: int, overlap: int | None = None) -> list[Chunk]:
    if chunk_size not in CHUNK_SIZES:
        raise ValueError(f'chunk_size must be one of {CHUNK_SIZES}, got {chunk_size}')
    overlap = overlap_for(chunk_size) if overlap is None else overlap
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(f'overlap must be in [0, chunk_size); got overlap={overlap}, chunk_size={chunk_size}')

    enc = _tokenizer()
    chunks: list[Chunk] = []

    for section_index, section in enumerate(document.sections):
        heading = section.section_path.strip()
        heading_tokens = enc.encode(heading) if heading else []
        # Guard against a pathological heading that alone exceeds the budget
        # (should not happen with real sources, but must not crash).
        max_heading_tokens = max(1, chunk_size // 2)
        if len(heading_tokens) > max_heading_tokens:
            heading_tokens = heading_tokens[:max_heading_tokens]
            heading = enc.decode(heading_tokens)
        budget = chunk_size - len(heading_tokens)

        body_tokens = enc.encode(section.text)
        stride = max(1, budget - overlap)
        starts = range(0, max(len(body_tokens), 1), stride)

        span_index = 0
        for start in starts:
            window = body_tokens[start:start + budget]
            if not window:
                continue
            body_text = enc.decode(window)
            text = f'{heading}\n\n{body_text}' if heading else body_text
            # Re-encode the final joined string rather than summing the
            # separately-encoded heading/body token counts: BPE merges
            # across the join boundary can change the true count by a
            # token or two, and token_count must reflect reality, not an
            # approximation (plan: "단순 글자 수를 토큰 수로 보고하지 않는다").
            # If that boundary merge pushed the real count over budget,
            # trim tokens off the tail until it actually fits.
            true_count = len(enc.encode(text))
            while true_count > chunk_size and len(window) > 1:
                window = window[:-1]
                body_text = enc.decode(window)
                text = f'{heading}\n\n{body_text}' if heading else body_text
                true_count = len(enc.encode(text))
            chunks.append(Chunk(
                chunk_id=f'{document.source_id}:{chunk_size}:{section_index}:{span_index}',
                source_id=document.source_id,
                section_path=section.section_path,
                text=text,
                token_count=true_count,
                chunk_size=chunk_size,
                overlap=overlap,
                section_index=section_index,
                span_index=span_index,
                page_index=section.page_index,
                printed_page_label=section.printed_page_label,
            ))
            span_index += 1
            if start + budget >= len(body_tokens):
                break

    return chunks
