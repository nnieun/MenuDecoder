"""EX-09: OpenAI 단독 추출 대 PaddleOCR+OpenAI 구조화 비교.

Real, paid, manual comparison - not part of pytest. The OpenAI-only path
makes 1 real (billed) vision call; the PaddleOCR path runs OCR locally
(free, but downloads model weights on first run) then makes 1 real
(billed) text-structuring call. Run with:

    .venv/Scripts/python -m backend.compare_ocr                 # synthetic fixture
    .venv/Scripts/python -m backend.compare_ocr --fixture real   # real menu photo

The synthetic fixture (manual_openai_smoke.py's rendered text) has exact,
unambiguous ground truth but tells us little about real photos. The
"real" fixture is an actual restaurant menu photo saved at
backend/rag/fixtures/images.jpg, with ground truth transcribed by hand
below (REAL_MENU_GROUND_TRUTH) - transcription error is possible and not
independently verified against the physical menu.
"""
import argparse
import platform
import sys
import time
from pathlib import Path

from .config import Settings
from .evaluation import cer
from .manual_openai_smoke import build_fixture_image
from .provider import OpenAIProvider

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, 'reconfigure'):
        _stream.reconfigure(encoding='utf-8', errors='replace')

SYNTHETIC_GROUND_TRUTH = [
    {'name': '味噌ラーメン', 'price': '¥900'},
    {'name': '焼き鳥', 'price': '¥300'},
]

REAL_MENU_IMAGE = Path(__file__).parent / 'rag' / 'fixtures' / 'images.jpg'
# Transcribed by hand from the photo. Each row's price is the main
# (tax-status A) figure printed before the parenthesized second figure -
# e.g. "まぐろ丼 ¥1,130 (1,243)" -> price "¥1,130". The parenthetical is
# real printed content too (likely the other tax-inclusive/exclusive
# figure) but we only check the primary figure since which one a model
# echoes first is not itself a correctness question this comparison
# is trying to answer.
REAL_MENU_GROUND_TRUTH = [
    {'name': 'まぐろ丼', 'price': '¥1,130'},
    {'name': '穴子丼', 'price': '¥1,780'},
    {'name': 'ま～さん丼', 'price': '¥1,130'},
    {'name': 'うな重', 'price': '¥3,500'},
    {'name': 'うな丼', 'price': '¥1,780'},
    {'name': '刺盛(1〜2人前)', 'price': '¥800'},
    {'name': '刺盛(3〜4人前)', 'price': '¥1,700'},
    {'name': '刺盛(4〜5人前)', 'price': '¥2,500'},
    {'name': 'まぐろ刺', 'price': '¥680'},
    {'name': 'カンパチ刺', 'price': '¥680'},
    {'name': '島タコ刺', 'price': '¥680'},
    {'name': 'サーモン刺', 'price': '¥680'},
    {'name': '白身刺', 'price': '¥680'},
]

# An item counts as "found" if its original_name is within this CER of a
# ground-truth name. Documented here rather than left an unstated default:
# it is a lenient cutoff (roughly half the characters may be wrong) chosen
# for this small smoke comparison, not a validated recognition threshold.
FOUND_CER_THRESHOLD = 0.5


def _normalize_price(value: str) -> str:
    return value.replace(',', '').replace(' ', '').replace('￥', '¥')  # fullwidth -> halfwidth yen


def _price_ok(extracted: str | None, truth_price: str) -> bool:
    if not extracted:
        return False
    return _normalize_price(truth_price) in _normalize_price(extracted)


def score(items, ground_truth):
    rows = []
    for truth in ground_truth:
        match = min(items, key=lambda i: cer(truth['name'], i.original_name), default=None)
        name_cer = cer(truth['name'], match.original_name) if match else 1.0
        rows.append({
            'truth_name': truth['name'],
            'matched_name': match.original_name if match else None,
            'matched_price': match.original_price_text if match else None,
            'name_cer': name_cer,
            'found': match is not None and name_cer <= FOUND_CER_THRESHOLD,
            'price_ok': _price_ok(match.original_price_text if match else None, truth['price']),
        })
    found_count = sum(r['found'] for r in rows)
    return {
        'rows': rows,
        'recall': found_count / len(ground_truth),
        'precision': found_count / len(items) if items else None,
        'mean_name_cer': sum(r['name_cer'] for r in rows) / len(rows),
        'price_accuracy': sum(r['price_ok'] for r in rows) / len(rows),
        'extracted_count': len(items),
    }


def report(label, items, ground_truth, elapsed, openai_calls, extra=''):
    result = score(items, ground_truth)
    print(f'\n=== {label} ===')
    print(f'  elapsed: {elapsed:.2f}s | OpenAI calls: {openai_calls}{extra}')
    if result['precision'] is None:
        print('  extracted 0 items')
    else:
        print(f'  extracted {result["extracted_count"]} item(s) (ground truth {len(ground_truth)}), '
              f'recall {result["recall"]:.0%}, precision {result["precision"]:.0%}')
    print(f'  mean name CER: {result["mean_name_cer"]:.3f} | price match: {result["price_accuracy"]:.0%}')
    for row in result['rows']:
        print(f'    truth={row["truth_name"]!r} -> matched={row["matched_name"]!r} '
              f'price={row["matched_price"]!r} cer={row["name_cer"]:.3f} '
              f'found={row["found"]} price_ok={row["price_ok"]}')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixture', choices=['synthetic', 'real'], default='synthetic')
    args = parser.parse_args()

    settings = Settings(ai_provider='openai')
    if not settings.openai_api_key:
        print('OPENAI_API_KEY is not set - nothing to compare.', file=sys.stderr)
        sys.exit(1)

    if args.fixture == 'real':
        if not REAL_MENU_IMAGE.exists():
            print(f'{REAL_MENU_IMAGE} not found.', file=sys.stderr)
            sys.exit(1)
        image = REAL_MENU_IMAGE.read_bytes()
        mime = 'image/jpeg'
        ground_truth = REAL_MENU_GROUND_TRUTH
        fixture_note = f'실제 메뉴판 사진({REAL_MENU_IMAGE.name}), 정답은 손으로 옮겨 적어 오탈자 가능성 있음'
    else:
        image = build_fixture_image()
        mime = 'image/png'
        ground_truth = SYNTHETIC_GROUND_TRUTH
        fixture_note = '합성 이미지(정답 정확히 앎)'

    provider = OpenAIProvider(settings)
    calls = []
    charge = lambda: calls.append(1)

    print(f'runtime: {platform.platform()}, python {platform.python_version()}')
    print(f'fixture: {fixture_note}')

    started = time.perf_counter()
    openai_items = provider.extract(image, mime, charge)
    openai_elapsed = time.perf_counter() - started
    openai_calls = len(calls)
    report('OpenAI 단독 (vision)', openai_items, ground_truth, openai_elapsed, openai_calls)

    print('\nLoading PaddleOCR pipeline (downloads model weights on first run)...')
    from .ocr import PaddleExtractor
    calls.clear()
    load_started = time.perf_counter()
    extractor = PaddleExtractor(provider)
    load_elapsed = time.perf_counter() - load_started
    started = time.perf_counter()
    paddle_items = extractor.extract(image, mime, charge)
    paddle_elapsed = time.perf_counter() - started
    report('PaddleOCR 결합 (검출+인식 -> OpenAI 구조화)', paddle_items, ground_truth, paddle_elapsed, len(calls),
           extra=f' | pipeline load: {load_elapsed:.2f}s (first run only)')
    print(f'\n  raw OCR blocks ({len(extractor.last_blocks)}): {extractor.last_blocks}')

    print(f'\n비고: 이미지 1장({args.fixture})에 대한 결과이며, 실제 메뉴판 다수 표본의 EX-09 실험을 대체하지 않는다.')


if __name__ == '__main__':
    main()
