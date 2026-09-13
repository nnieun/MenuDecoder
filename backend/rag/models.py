"""Document/section schema for the RAG corpus.

Kept separate from backend/models.py (the API contract) because this
schema is for offline corpus files, not HTTP request/response bodies.
"""
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


def now():
    return datetime.now(UTC)


class Section(BaseModel):
    """One retrievable unit of a document before chunking.

    For HTML this is the text under one heading. For PDF this is one
    physical page. page_index is 0-based; printed_page_label is the
    page number as printed on the page, when it could be parsed, and
    is None rather than guessed when it could not.
    """
    section_path: str
    text: str
    page_index: int | None = Field(default=None, ge=0)
    printed_page_label: str | None = None


class Document(BaseModel):
    source_id: str
    title: str
    doc_type: Literal['html', 'pdf']
    url: HttpUrl
    language: str
    publisher: str
    license_note: str
    collected_at: datetime = Field(default_factory=now)
    content_hash: str
    sections: list[Section]


class Chunk(BaseModel):
    """A retrievable unit after chunking (RAG 7단계의 '단계 2. 청킹').

    chunk_id encodes the chunking config so 256/512/1024 (and any future
    tokenizer/overlap change) never collide in the same vector collection.
    """
    chunk_id: str
    source_id: str
    section_path: str
    text: str
    token_count: int
    chunk_size: int
    overlap: int
    section_index: int
    span_index: int  # order of this chunk within its section (0 for the first/only one)
    page_index: int | None = None
    printed_page_label: str | None = None
