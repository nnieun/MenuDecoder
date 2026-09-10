"""Real OpenAI-backed provider.

Mirrors MockProvider's interface (extract/describe/images/answer) so
backend/main.py can swap providers without touching graph.py or store.py.
Uses the Responses API's structured-output parsing (`responses.parse`,
`text_format=<pydantic model>`) so every model turn returns a typed,
validated object instead of ad-hoc JSON parsing.

Deliberately BM25-only for grounding (backend/rag/retriever.py) — no
embeddings yet. menu_project_plan.md 8절의 "먼저 검색만 평가"라는 비용
절감 순서를 따라, 임베딩(OpenAI/BGE-M3) 비교는 EX-03에서 별도로 한다.

Any exception raised here (other than the DomainError a `charge()` call
may raise for budget limits) propagates up to graph.py's per-item/
per-message `except Exception` handler, which already turns it into a
sanitized failure without leaking internals — so this module does not
need its own broad try/except.
"""
import base64
import hashlib
from urllib.parse import urlparse

import httpx
from openai import OpenAI
from pydantic import BaseModel

from .models import ChatMessage, Citation, MenuImage, MenuItem
from .rag.retriever import Retriever, default_retriever

IMAGE_FETCH_TIMEOUT = 6.0
MAX_IMAGE_CANDIDATES = 3


def _citation(chunk, document) -> Citation:
    return Citation(
        source_id=document.source_id,
        document_title=document.title,
        source_url=document.url,
        section_path=chunk.section_path,
        pdf_page_index=chunk.page_index,
        printed_page_label=chunk.printed_page_label,
        chunk_id=chunk.chunk_id,
    )


def _context_block(chunks, retriever: Retriever) -> str:
    parts = []
    for chunk in chunks:
        document = retriever.document_for(chunk.source_id)
        title = document.title if document else chunk.source_id
        parts.append(f'[{chunk.chunk_id}] {title} — {chunk.section_path}\n{chunk.text}')
    return '\n\n'.join(parts) if parts else '(관련 문서를 찾지 못했습니다.)'


def _citations_from(result_chunk_ids, chunks, retriever: Retriever) -> list[Citation]:
    valid = {c.chunk_id: c for c in chunks}
    citations = []
    for chunk_id in result_chunk_ids:
        chunk = valid.get(chunk_id)
        if chunk is None:
            continue  # 존재하지 않는(혹은 지어낸) 근거 번호는 표시 전에 거절한다
        document = retriever.document_for(chunk.source_id)
        if document is None:
            continue
        citations.append(_citation(chunk, document))
    return citations


class ExtractedItem(BaseModel):
    original_name: str
    translated_name: str
    original_price_text: str | None = None


class ExtractedMenu(BaseModel):
    items: list[ExtractedItem]


EXTRACT_INSTRUCTIONS = (
    '사진은 일본어 메뉴판입니다. 실제로 인쇄된 메뉴 항목만 추출하세요. '
    '사진에 없는 메뉴를 지어내지 마세요. original_name에는 원문 그대로(일본어)를, '
    'translated_name에는 자연스러운 한국어 음식명을 적으세요. '
    'original_price_text는 메뉴판에 적힌 가격 문자열을 그대로(통화 기호 포함) 옮기고, '
    '가격이 안 보이면 null로 두세요. 세금·옵션 가격을 추정해서 더하지 마세요.'
)


class DescribeOutput(BaseModel):
    description: str
    supporting_chunk_ids: list[str]
    insufficient_evidence: bool
    warning: str | None = None


DESCRIBE_INSTRUCTIONS = (
    '당신은 일본 메뉴판의 음식을 한국어로 설명하는 도우미입니다. '
    '[근거] 섹션에 주어진 문서 조각만 사실의 근거로 사용하세요. '
    '근거에 없는 재료·조리법·유래를 지어내지 마세요. '
    '문장이 사용한 근거 조각의 id를 supporting_chunk_ids에 정확히 그대로(대괄호 없이) 적으세요. '
    '근거가 부족하면 insufficient_evidence를 true로 하고 설명을 짧게 줄이며, '
    'warning에 부족한 이유를 한국어로 간단히 적으세요. 충분하면 warning은 null로 두세요.'
)


class ImageCandidate(BaseModel):
    image_url: str
    source_page_url: str
    caption: str


class ImageSearchOutput(BaseModel):
    candidates: list[ImageCandidate]


IMAGES_INSTRUCTIONS = (
    '웹 검색 도구로 주어진 일본 음식의 실제 사진을 찾으세요. '
    '검색 결과에서 실제로 확인한 이미지 파일 URL만 image_url에 적으세요. '
    '검색하지 않았거나 존재를 확신할 수 없는 주소는 만들어내지 마세요. '
    '이미지를 찾지 못했으면 candidates를 빈 배열로 반환하세요. 최대 3개까지만 반환하세요.'
)


class AnswerOutput(BaseModel):
    content: str
    supporting_chunk_ids: list[str]


ANSWER_INSTRUCTIONS = (
    '일본 메뉴판에 대한 후속 질문에 한국어로 답하세요. '
    '[근거] 섹션의 문서 조각만 사실 근거로 사용하고, 없는 내용을 지어내지 마세요. '
    '[직전 대화]는 지시어("그거", "아까 그 음식")가 가리키는 대상을 이해하는 데만 쓰고, '
    '그 자체를 새로운 사실 근거로 삼지 마세요. 근거가 부족하면 모른다고 솔직히 답하세요. '
    '답변에 사용한 근거 조각 id를 supporting_chunk_ids에 정확히 그대로 적으세요.'
)


def _looks_like_image(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False
        with httpx.Client(timeout=IMAGE_FETCH_TIMEOUT, follow_redirects=True) as client:
            response = client.head(url)
            if response.status_code >= 400 or 'image' not in response.headers.get('content-type', ''):
                response = client.get(url, headers={'Range': 'bytes=0-0'})
            return response.status_code < 400 and response.headers.get('content-type', '').startswith('image/')
    except httpx.HTTPError:
        return False


class OpenAIProvider:
    def __init__(self, settings, retriever: Retriever | None = None):
        self.settings = settings
        self.model = settings.openai_model
        self.client = OpenAI(api_key=settings.openai_api_key)
        self._retriever = retriever

    @property
    def retriever(self) -> Retriever:
        if self._retriever is None:
            self._retriever = default_retriever()
        return self._retriever

    def extract(self, image: bytes, mime: str, charge) -> list[MenuItem]:
        charge()
        data_url = f'data:{mime};base64,{base64.b64encode(image).decode()}'
        response = self.client.responses.parse(
            model=self.model,
            instructions=EXTRACT_INSTRUCTIONS,
            input=[{
                'role': 'user',
                'content': [
                    {'type': 'input_text', 'text': '이 사진에서 메뉴 항목을 추출해 주세요.'},
                    {'type': 'input_image', 'image_url': data_url, 'detail': 'high'},
                ],
            }],
            text_format=ExtractedMenu,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError('extract: model did not return structured output')
        return [
            MenuItem(
                original_name=i.original_name,
                translated_name=i.translated_name,
                original_price_text=i.original_price_text,
            )
            for i in parsed.items
        ]

    def describe(self, item: MenuItem, charge):
        query = f'{item.translated_name} {item.original_name}'.strip()
        chunks = self.retriever.search(query)
        charge()
        response = self.client.responses.parse(
            model=self.model,
            instructions=DESCRIBE_INSTRUCTIONS,
            input=[{
                'role': 'user',
                'content': [{
                    'type': 'input_text',
                    'text': (
                        f'메뉴명(원문): {item.original_name}\n메뉴명(한국어): {item.translated_name}\n\n'
                        f'[근거]\n{_context_block(chunks, self.retriever)}'
                    ),
                }],
            }],
            text_format=DescribeOutput,
        )
        result = response.output_parsed
        if result is None:
            raise RuntimeError('describe: model did not return structured output')
        item.description = result.description
        item.citations = _citations_from(result.supporting_chunk_ids, chunks, self.retriever)
        item.warnings = [result.warning] if result.warning else []
        if result.insufficient_evidence and not item.warnings:
            item.warnings.append('확인 가능한 문서 근거가 부족해요.')

    def images(self, item: MenuItem, charge):
        query_text = f'음식명(일본어 원문): {item.original_name}\n음식명(한국어): {item.translated_name}'
        charge()
        response = self.client.responses.parse(
            model=self.model,
            instructions=IMAGES_INSTRUCTIONS,
            input=[{'role': 'user', 'content': [{'type': 'input_text', 'text': query_text}]}],
            tools=[{'type': 'web_search'}],
            text_format=ImageSearchOutput,
        )
        result = response.output_parsed
        candidates = result.candidates[:MAX_IMAGE_CANDIDATES] if result else []
        verified: list[MenuImage] = []
        for candidate in candidates:
            if not _looks_like_image(candidate.image_url):
                continue
            image_id = hashlib.sha1(candidate.image_url.encode()).hexdigest()[:16]
            verified.append(MenuImage(
                image_id=image_id,
                image_url=candidate.image_url,
                source_page_url=candidate.source_page_url or candidate.image_url,
                caption=candidate.caption,
            ))
        item.images = verified
        if not verified:
            item.warnings.append('참고 사진을 찾지 못했어요.')

    def answer(self, analysis, message, charge) -> ChatMessage:
        if not message.referenced_item_ids and len(analysis.items) > 1:
            # 대상이 모호하면 추측하지 않고 되묻는다 (LLM 호출 없이, 계획서 7절)
            return ChatMessage(
                role='assistant',
                content='어떤 음식을 말씀하시는지 메뉴 이름을 알려 주세요.',
                referenced_item_ids=[],
            )
        target_ids = message.referenced_item_ids or ([analysis.items[0].item_id] if analysis.items else [])
        items = [i for i in analysis.items if i.item_id in target_ids]
        item_names = ' '.join(f'{i.translated_name} {i.original_name}' for i in items)
        query = f'{message.content} {item_names}'.strip()
        chunks = self.retriever.search(query)

        recent = analysis.messages[-6:]
        history = '\n'.join(f'{"사용자" if m.role == "user" else "도우미"}: {m.content}' for m in recent if m.status == 'done')

        charge()
        response = self.client.responses.parse(
            model=self.model,
            instructions=ANSWER_INSTRUCTIONS,
            input=[{
                'role': 'user',
                'content': [{
                    'type': 'input_text',
                    'text': (
                        f'[직전 대화]\n{history or "(없음)"}\n\n'
                        f'[현재 메뉴]\n{item_names or "(선택된 메뉴 없음)"}\n\n'
                        f'[질문]\n{message.content}\n\n'
                        f'[근거]\n{_context_block(chunks, self.retriever)}'
                    ),
                }],
            }],
            text_format=AnswerOutput,
        )
        result = response.output_parsed
        if result is None:
            raise RuntimeError('answer: model did not return structured output')
        citations = _citations_from(result.supporting_chunk_ids, chunks, self.retriever)
        return ChatMessage(role='assistant', content=result.content, referenced_item_ids=target_ids, citations=citations)
