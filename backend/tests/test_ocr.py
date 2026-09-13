import io
from unittest.mock import Mock
from PIL import Image
from backend.ocr import PaddleExtractor
from backend.provider import ExtractedMenu, ExtractedItem


def test_detection_and_recognition_feed_same_output_schema():
    pipeline, provider = Mock(), Mock()
    result = Mock(); result.json = {'res': {'rec_texts': ['焼き鳥', '300円'], 'rec_polys': [[[0, 0], [10, 0], [10, 10], [0, 10]]]}}
    pipeline.predict.return_value = [result]
    provider._call.return_value.output_parsed = ExtractedMenu(items=[ExtractedItem(original_name='焼き鳥', translated_name='야키토리', original_price_text='300円')])
    extractor = PaddleExtractor(provider, pipeline)
    image = io.BytesIO(); Image.new('RGB', (20, 20)).save(image, format='PNG')
    calls = []
    items = extractor.extract(image.getvalue(), 'image/png', lambda: calls.append(True))
    assert items[0].original_price_text == '300円'
    assert len(extractor.last_blocks) == 2 and calls == [True]
