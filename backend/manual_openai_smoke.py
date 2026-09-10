"""Real, paid, manual smoke test for backend/provider.py.

Not part of pytest on purpose - it calls the real OpenAI API and costs
money. Run it yourself, once OPENAI_API_KEY is set in backend/.env,
whenever provider.py changes in a way that could break the real
extract -> describe -> images -> answer chain:

    .venv/Scripts/python -m backend.manual_openai_smoke

It builds a synthetic menu photo (Japanese text rendered with a real
font, not a real restaurant photo - see backend/rag/README.md's "다음
단계"), so the ground truth is exactly known:
    味噌ラーメン  ¥900
    焼き鳥        ¥300
and reports whether extract() actually read that, whether describe()
attached citations to the real corpus, and whether images()/answer()
ran without raising and reported an outcome (rather than pretending
success). It does not assert - it prints, because "correct" here is a
judgment call at the settings/model boundary that stats/tests should
not silently gate.
"""
import io
import sys

from PIL import Image, ImageDraw, ImageFont

from .config import Settings
from .models import Analysis, ChatMessage
from .provider import OpenAIProvider

FONT_PATH = r'C:\Windows\Fonts\msgothic.ttc'


def build_fixture_image() -> bytes:
    font = ImageFont.truetype(FONT_PATH, 28)
    img = Image.new('RGB', (500, 200), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), '味噌ラーメン  ¥900', font=font, fill='black')
    draw.text((20, 90), '焼き鳥  ¥300', font=font, fill='black')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def main():
    settings = Settings(ai_provider='openai')
    if not settings.openai_api_key:
        print('OPENAI_API_KEY is not set in backend/.env - nothing to test.', file=sys.stderr)
        sys.exit(1)

    provider = OpenAIProvider(settings)
    calls = []
    charge = lambda: calls.append(1)

    print('=== extract() ===')
    items = provider.extract(build_fixture_image(), 'image/png', charge)
    for item in items:
        print(f'  {item.original_name!r} -> {item.translated_name!r} ({item.original_price_text})')
    expected = {'味噌ラーメン', '焼き鳥'}
    found = {item.original_name for item in items}
    print(f'  ground truth match: {expected & found} / expected {expected}')

    if not items:
        print('no items extracted; stopping here', file=sys.stderr)
        sys.exit(1)

    target = items[0]
    print(f'\n=== describe({target.original_name!r}) ===')
    provider.describe(target, charge)
    print(f'  description: {target.description}')
    print(f'  citations: {[c.chunk_id for c in target.citations]}')
    print(f'  warnings: {target.warnings}')

    print(f'\n=== images({target.original_name!r}) ===')
    provider.images(target, charge)
    print(f'  verified images: {[(i.image_url, i.source_page_url) for i in target.images]}')
    print(f'  warnings: {target.warnings}')

    print('\n=== answer() ===')
    analysis = Analysis(mode='openai', items=items)
    message = ChatMessage(role='user', content='그 라멘은 매워?', referenced_item_ids=[target.item_id])
    reply = provider.answer(analysis, message, charge)
    print(f'  content: {reply.content}')
    print(f'  citations: {[c.chunk_id for c in reply.citations]}')

    print(f'\ntotal charge() calls (real API turns): {len(calls)}')


if __name__ == '__main__':
    main()
