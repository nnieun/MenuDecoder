from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, ConfigDict


def now():
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Citation(BaseModel):
    source_id: str
    document_title: str
    source_url: HttpUrl
    section_path: str
    pdf_page_index: int | None = Field(default=None, ge=0)
    printed_page_label: str | None = None
    chunk_id: str


class MenuImage(BaseModel):
    image_id: str
    image_url: HttpUrl
    source_page_url: HttpUrl
    caption: str
    reference_only: Literal[True] = True


class MenuItem(BaseModel):
    item_id: UUID = Field(default_factory=uuid4)
    original_name: str
    translated_name: str = ''
    original_price_text: str | None = None
    description: str = ''
    item_version: int = 1
    status: Literal['pending', 'searching_docs', 'searching_images', 'needs_review', 'done', 'failed', 'reanalyzing'] = 'pending'
    citations: list[Citation] = Field(default_factory=list)
    images: list[MenuImage] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # Approximate location of this item's text in the uploaded photo, as a
    # fraction of image width/height (0,0 = top-left, 1,1 = bottom-right).
    # The vision model estimates this directly - it is not a precise
    # bounding box and can be off by roughly one menu row. None when the
    # provider didn't return one (mock mode, or the model omitted it).
    center_x: float | None = Field(default=None, ge=0, le=1)
    center_y: float | None = Field(default=None, ge=0, le=1)


class ChatMessage(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    role: Literal['user', 'assistant']
    content: str
    status: Literal['sending', 'done', 'failed'] = 'done'
    referenced_item_ids: list[UUID] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    # A tap on a menu chip/pin fetches that item's photo+description the same
    # way an explicit question does (describe()/images() are still driven by
    # resolve_targets on this message), but it should not read like the user
    # typed a question - the frontend hides silent messages from "대화" and
    # the backend never generates a conversational answer for one (see
    # graph.py). Not part of any user-facing product decision to hide the
    # underlying fetch, only to not fake a chat exchange for it.
    silent: bool = False


class Analysis(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    status: Literal['queued', 'reading', 'needs_review', 'searching_docs', 'searching_images', 'partial', 'done', 'failed', 'rate_limited'] = 'queued'
    state_version: int = 1
    created_at: datetime = Field(default_factory=now)
    items: list[MenuItem] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    remaining_work: bool = True
    request_id: UUID = Field(default_factory=uuid4)
    mode: Literal['mock', 'openai']
    warnings: list[str] = Field(default_factory=list)


class Accepted(BaseModel):
    analysis_id: UUID
    session_token: str
    expires_at: datetime
    status: Literal['queued'] = 'queued'
    mode: Literal['mock', 'openai']


class ContinueRequest(StrictModel):
    state_version: int = Field(ge=1)


class MessageRequest(StrictModel):
    content: str = Field(min_length=1, max_length=2000)
    referenced_item_ids: list[UUID] = Field(default_factory=list, max_length=20)
    silent: bool = False


class EditRequest(StrictModel):
    original_name: str = Field(min_length=1, max_length=300)
    item_version: int = Field(ge=1)


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: UUID = Field(default_factory=uuid4)


class Health(BaseModel):
    status: Literal['ok'] = 'ok'
    mode: Literal['mock', 'openai']
    storage: Literal['memory-local-only'] = 'memory-local-only'

