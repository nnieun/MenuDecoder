"""Fetch backend/rag/sources.py's SOURCES and write backend/rag/documents/*.json.

Run with: .venv/Scripts/python -m backend.rag.collect

This is an offline, manually-run script, not part of the API request path
and not part of pytest (it hits real network endpoints). Re-running it
refreshes collected_at/content_hash for every source; it does not diff
against the previous version, so review `git diff` after running it.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

from .documents import clean_html, extract_pdf
from .models import Document, now
from .sources import SOURCES

OUT_DIR = Path(__file__).parent / 'documents'
TIMEOUT = 30.0
USER_AGENT = 'menu-decoder-rag-collector/1.0 (portfolio project; contact via repository)'
# japan.travel geo-localizes by request IP and silently serves Korean body
# text on /en/ URLs; Accept-Language does not override this, but the site's
# own Django locale cookie does (confirmed: it round-trips django_language=en
# in Set-Cookie once accepted, and forcing it on the request keeps the body
# in English regardless of geo-IP).
REQUEST_HEADERS = {'User-Agent': USER_AGENT, 'Accept-Language': 'en-US,en;q=0.9', 'Cookie': 'django_language=en'}


def content_hash(sections) -> str:
    joined = '\n\n'.join(s.text for s in sections)
    return hashlib.sha256(joined.encode('utf-8')).hexdigest()


def _non_ascii_ratio(text: str) -> float:
    if not text:
        return 0.0
    non_ascii = sum(1 for ch in text if ord(ch) > 0x2FF)  # past Latin/combining marks
    return non_ascii / len(text)


def _check_language(spec, sections) -> None:
    """Catch silent geo-localization (e.g. an /en/ URL served in Korean)."""
    if spec.language != 'en':
        return
    sample = '\n'.join(s.text for s in sections[:2])[:2000]
    ratio = _non_ascii_ratio(sample)
    if ratio > 0.2:
        raise ValueError(
            f'{spec.source_id}: expected language=en but {ratio:.0%} of sampled text is '
            f'non-ASCII/CJK. The site likely geo-localized the response; check REQUEST_HEADERS.'
        )


MAX_ATTEMPTS = 5


def _fetch_once(spec):
    # A fresh client per attempt: the site sits behind a load balancer pool
    # and some pods geo-localize the body to Korean regardless of
    # Accept-Language, so a retry with a new connection often lands on a
    # pod that honors it. A reused/kept-alive connection tends to repeat
    # the same (wrong) pod.
    with httpx.Client(timeout=TIMEOUT, headers=REQUEST_HEADERS, follow_redirects=True) as client:
        response = client.get(spec.url)
        response.raise_for_status()
        if spec.doc_type == 'html':
            title, sections = clean_html(response.text)
            title = title or spec.title
        else:
            title = spec.title
            sections = extract_pdf(response.content)
    return title, sections


def collect_one(spec) -> Document:
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            time.sleep(2)
        try:
            title, sections = _fetch_once(spec)
        except httpx.HTTPError as exc:
            last_error = exc
            print(f'  retry {attempt}/{MAX_ATTEMPTS} {spec.source_id}: {exc}', file=sys.stderr)
            continue
        if not sections:
            last_error = ValueError(f'{spec.source_id}: no sections extracted, refusing to write an empty document')
            continue
        try:
            _check_language(spec, sections)
        except ValueError as exc:
            last_error = exc
            print(f'  retry {attempt}/{MAX_ATTEMPTS} {spec.source_id}: {exc}', file=sys.stderr)
            continue
        break
    else:
        raise last_error
    return Document(
        source_id=spec.source_id,
        title=title,
        doc_type=spec.doc_type,
        url=spec.url,
        language=spec.language,
        publisher=spec.publisher,
        license_note=spec.license_note,
        collected_at=now(),
        content_hash=content_hash(sections),
        sections=sections,
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    failures = []
    for spec in SOURCES:
        try:
            document = collect_one(spec)
        except Exception as exc:  # noqa: BLE001 - report and continue with the rest
            failures.append({'source_id': spec.source_id, 'url': spec.url, 'error': str(exc)})
            print(f'FAILED {spec.source_id}: {exc}', file=sys.stderr)
            continue
        out_path = OUT_DIR / f'{spec.source_id}.json'
        out_path.write_text(document.model_dump_json(indent=2) + '\n', encoding='utf-8')
        manifest.append({
            'source_id': document.source_id,
            'title': document.title,
            'doc_type': document.doc_type,
            'url': str(document.url),
            'language': document.language,
            'publisher': document.publisher,
            'collected_at': document.collected_at.isoformat(),
            'content_hash': document.content_hash,
            'section_count': len(document.sections),
        })
        print(f'OK {spec.source_id}: {len(document.sections)} sections')
    manifest_path = OUT_DIR / 'manifest.json'
    manifest_path.write_text(json.dumps({'documents': manifest, 'failures': failures}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if failures:
        print(f'{len(failures)} source(s) failed; see manifest.json', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
