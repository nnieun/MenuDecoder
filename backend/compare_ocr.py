"""EX-09: OpenAI 단독 추출 대 PaddleOCR+OpenAI 구조화 비교.

Real, paid, manual comparison - not part of pytest. The OpenAI-only path
makes 1 real (billed) vision call; the PaddleOCR path runs OCR locally
(free, but downloads model weights on first run) then makes 1 real
(billed) text-structuring call. Run with:

    .venv/Scripts/python -m backend.compare_ocr

Ground truth is the same synthetic fixture manual_openai_smoke.py uses -
a real restaurant photo was not available for this comparison, so this
is a single-image smoke comparison, not the multi-photo EX-09 sample
menu_project_plan.md 22절 asks for. Treat the numbers below as "does the
PaddleOCR path work and roughly how does it compare on one clean image",
not as a statistically meaningful precision/recall/CER result.
"""
import platform
import sys
import time

from .config import Settings
from .evaluation import cer
from .manual_openai_smoke import build_fixture_image
from .provider import OpenAIProvider

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

GROUND_TRUTH = [
    {'name': '味噌ラーメン', 'price': '¥900'},
    {'name': '焼き鳥', 'price': '¥300'},
]
# An item counts as "found" if its original_name is within this CER of a
# ground-truth name. Documented here rather than left an unstated default:
# it is a lenient cutoff (roughly half the characters may be wrong) chosen
# for a 2-item smoke comparison, not a validated recognition threshold.
FOUND_CER_THRESHOLD = 0.5


def score(items):
    rows = []
    for truth in GROUND_TRUTH:
        match = min(items, key=lambda i: cer(truth['name'], i.original_name), default=None)
        name_cer = cer(truth['name'], match.original_name) if match else 1.0
        rows.append({
            'truth_name': truth['name'],
            'matched_name': match.original_name if match else None,
            'name_cer': name_cer,
            'found': match is not None and name_cer <= FOUND_CER_THRESHOLD,
            'price_exact_match': bool(match) and match.original_price_text == truth['price'],
        })
    found_count = sum(r['found'] for r in rows)
    return {
        'rows': rows,
        'recall': found_count / len(GROUND_TRUTH),
        'precision': found_count / len(items) if items else None,
        'mean_name_cer': sum(r['name_cer'] for r in rows) / len(rows),
        'price_accuracy': sum(r['price_exact_match'] for r in rows) / len(rows),
        'extracted_count': len(items),
    }


def report(label, items, elapsed, openai_calls, extra=''):
    result = score(items)
    print(f'\n=== {label} ===')
    print(f'  elapsed: {elapsed:.2f}s | OpenAI calls: {openai_calls}{extra}')
    if result['precision'] is None:
        print('  extracted 0 items')
    else:
        print(f'  extracted {result["extracted_count"]} item(s), recall {result["recall"]:.0%}, '
              f'precision {result["precision"]:.0%}')
    print(f'  mean name CER: {result["mean_name_cer"]:.3f} | price exact-match: {result["price_accuracy"]:.0%}')
    for row in result['rows']:
        print(f'    truth={row["truth_name"]!r} -> matched={row["matched_name"]!r} '
              f'cer={row["name_cer"]:.3f} found={row["found"]} price_ok={row["price_exact_match"]}')
    return result


def main():
    settings = Settings(ai_provider='openai')
    if not settings.openai_api_key:
        print('OPENAI_API_KEY is not set - nothing to compare.', file=sys.stderr)
        sys.exit(1)

    image = build_fixture_image()
    provider = OpenAIProvider(settings)
    calls = []
    charge = lambda: calls.append(1)

    print(f'runtime: {platform.platform()}, python {platform.python_version()}')

    started = time.perf_counter()
    openai_items = provider.extract(image, 'image/png', charge)
    openai_elapsed = time.perf_counter() - started
    openai_calls = len(calls)
    report('OpenAI 단독 (vision)', openai_items, openai_elapsed, openai_calls)

    print('\nLoading PaddleOCR pipeline (downloads model weights on first run)...')
    from .ocr import PaddleExtractor
    calls.clear()
    load_started = time.perf_counter()
    extractor = PaddleExtractor(provider)
    load_elapsed = time.perf_counter() - load_started
    started = time.perf_counter()
    paddle_items = extractor.extract(image, 'image/png', charge)
    paddle_elapsed = time.perf_counter() - started
    report('PaddleOCR 결합 (검출+인식 -> OpenAI 구조화)', paddle_items, paddle_elapsed, len(calls),
           extra=f' | pipeline load: {load_elapsed:.2f}s (first run only)')
    print(f'\n  raw OCR blocks: {extractor.last_blocks}')

    print('\n비고: 이미지 1장(합성)에 대한 결과이며, 실제 메뉴판 다수 표본의 EX-09 실험을 대체하지 않는다.')


if __name__ == '__main__':
    main()
