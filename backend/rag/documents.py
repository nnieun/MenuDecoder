"""HTML/PDF -> Section extraction (RAG 7단계의 '단계 1. 문서 수집·읽기·전처리').

목표는 완벽한 범용 파서가 아니라, backend/rag/sources.py에 등록된 실제
문서들에서 광고·내비게이션·반복 바닥글을 제거하고 제목·섹션 구조·본문을
보존하는 것이다. 실패하면 예외를 삼키지 않고 그대로 올린다 — 전처리
실패를 조용히 빈 문서로 바꾸지 않기 위해서.
"""
import io
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .models import Section

# 문서 본문이 아니라 위젯·관련 콘텐츠 UI인 제목들. 이 제목을 만나면 그
# 지점부터 문서 끝까지 버린다 (반복 바닥글 제거).
_BOILERPLATE_HEADING_PREFIXES = (
    'did this information help you',
    'thank you for your feedback',
    'recommended for you',
    'keywords',
)

_CONTENT_SELECTORS = ('.content-main-wrapper', 'main', 'article')
_HEADING_TAGS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
_BLOCK_TAGS = ('p', 'li')
_MIN_SECTION_CHARS = 40


def _is_boilerplate_heading(text: str) -> bool:
    lowered = text.strip().lower()
    return any(lowered.startswith(p) for p in _BOILERPLATE_HEADING_PREFIXES)


def clean_html(html: str) -> tuple[str, list[Section]]:
    """Return (title, sections) extracted from a JNTO-style guide page."""
    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.title
    title = title_tag.get_text(strip=True).split('|')[0].strip() if title_tag else ''

    container = None
    for selector in _CONTENT_SELECTORS:
        container = soup.select_one(selector)
        if container:
            break
    if container is None:
        container = soup.body or soup

    junk_selectors = (
        'script, style, noscript, svg, form, nav, '
        '.mod-keyvisual__anchor-items, .mod-breadcrumb__items, .mod-tag-list__items'
    )
    for junk in container.select(junk_selectors):
        junk.decompose()

    blocks = container.find_all(list(_HEADING_TAGS) + list(_BLOCK_TAGS))

    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    buffer: list[str] = []

    def flush():
        text = '\n\n'.join(buffer).strip()
        buffer.clear()
        if len(text) < _MIN_SECTION_CHARS:
            return
        path = ' > '.join([title] + [t for _, t in stack]) if title else ' > '.join(t for _, t in stack)
        sections.append(Section(section_path=path or title or '(no title)', text=text))

    for el in blocks:
        if el.name in _HEADING_TAGS:
            heading_text = el.get_text(' ', strip=True)
            if not heading_text:
                continue
            if _is_boilerplate_heading(heading_text):
                flush()
                break
            flush()
            level = int(el.name[1])
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading_text))
        elif stack:
            # Text before the first heading is breadcrumb/tab-switcher chrome
            # in this template ("OVERVIEW / KEYWORDS / HOME / ..."), not body
            # content, so it is only collected once a real heading has started.
            text = el.get_text(' ', strip=True)
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                buffer.append(text)
    else:
        flush()

    return title, sections


_PRINTED_PAGE_RE = re.compile(r'^\s*(\d{1,3})\s*$')


def extract_pdf(data: bytes) -> list[Section]:
    """One Section per physical PDF page. printed_page_label is None when
    the first line of the page is not a bare page number (no guessing)."""
    reader = PdfReader(io.BytesIO(data))
    sections: list[Section] = []
    for index, page in enumerate(reader.pages):
        raw = (page.extract_text() or '').strip()
        if not raw:
            continue
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        printed_label = None
        text_lines = lines
        if lines:
            m = _PRINTED_PAGE_RE.match(lines[0])
            if m:
                printed_label = m.group(1)
                text_lines = lines[1:]
        text = '\n'.join(text_lines).strip()
        # Some embedded fonts have unmapped glyphs pypdf can't decode; those
        # come out as U+FFFD rather than real characters. A page that is
        # mostly replacement characters has no usable text, so drop it;
        # otherwise just strip the stray marks out of otherwise-good text.
        if text.count('�') > len(text) * 0.2:
            continue
        text = re.sub(r'�+\s*', '', text).strip()
        if len(text) < _MIN_SECTION_CHARS:
            continue
        sections.append(Section(
            section_path=f'page {index + 1}',
            text=text,
            page_index=index,
            printed_page_label=printed_label,
        ))
    return sections
