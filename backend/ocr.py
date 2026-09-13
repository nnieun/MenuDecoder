"""Optional PaddleOCR detection + recognition, then OpenAI menu structuring."""
import io
import json

import numpy as np
from PIL import Image

from .models import MenuItem
from .provider import EXTRACT_INSTRUCTIONS, ExtractedMenu


class PaddleExtractor:
    def __init__(self, provider, pipeline=None):
        self.provider = provider
        if pipeline is None:
            from paddleocr import PaddleOCR
            # enable_mkldnn=False works around a crash on this CPU/paddle build:
            # NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
            # [pir::ArrayAttribute<pir::DoubleAttribute>] in the oneDNN instruction
            # path of PP-OCRv6's text-detection predictor. Re-test without this if
            # paddlepaddle is upgraded.
            pipeline = PaddleOCR(lang='japan', use_doc_orientation_classify=False,
                                 use_doc_unwarping=False, use_textline_orientation=False,
                                 enable_mkldnn=False)
        self.pipeline = pipeline
        self.last_blocks = []

    def extract(self, image, mime, charge):
        with Image.open(io.BytesIO(image)) as source:
            pixels = np.asarray(source.convert('RGB'))[:, :, ::-1]
        blocks = []
        for result in self.pipeline.predict(input=pixels):
            payload = result.json
            payload = json.loads(payload) if isinstance(payload, str) else payload
            payload = payload.get('res', payload)
            texts = payload.get('rec_texts', [])
            polygons = payload.get('rec_polys', [])
            for index, text in enumerate(texts):
                blocks.append({'text': text, 'polygon': polygons[index] if index < len(polygons) else None})
        self.last_blocks = blocks
        charge()
        ocr_instructions = EXTRACT_INSTRUCTIONS.replace('사진', 'OCR 결과') + (
            ' OCR은 한 줄에 이름과 가격이 붙어서 인식될 수 있습니다'
            '(예: "味噌ラーメン　¥900"). original_name에는 가격·통화 기호를 제외한 '
            '음식명만 남기고, 가격 부분은 original_price_text로 분리하세요.'
        )
        response = self.provider._call('parse', model=self.provider.model, store=False, max_output_tokens=4000,
            instructions=ocr_instructions,
            input=json.dumps(blocks, ensure_ascii=False), text_format=ExtractedMenu)
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError('OCR structuring failed')
        return [MenuItem(original_name=i.original_name, translated_name=i.translated_name,
                         original_price_text=i.original_price_text) for i in parsed.items]
