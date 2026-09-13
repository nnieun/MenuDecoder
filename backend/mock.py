from .models import ChatMessage, MenuItem
from .targets import NO_IMAGE_FOUND_WARNING


class MockProvider:
    """Explicit test fixture: no images or invented citations masquerade as evidence."""
    def extract(self, image, mime, charge):
        return [MenuItem(original_name='味噌ラーメン', translated_name='미소 라멘', original_price_text='¥900',
                          center_x=0.3, center_y=0.25),
                MenuItem(original_name='焼き鳥', translated_name='야키토리', original_price_text='¥300',
                          center_x=0.3, center_y=0.6)]

    def describe(self, item, charge):
        item.description = '모의 분석 예시입니다. 실제 메뉴판을 읽거나 음식 정보를 검색한 결과가 아닙니다.'
        item.warnings = ['실제 조리법과 재료는 확인되지 않았어요.']

    def images(self, item, charge):
        item.warnings.append(NO_IMAGE_FOUND_WARNING)

    def answer(self, analysis, message, charge):
        if not message.referenced_item_ids and len(analysis.items) > 1:
            content = '어떤 음식을 말씀하시는지 메뉴 이름을 알려 주세요. (모의 응답)'
        else:
            content = '현재 메뉴에 관한 모의 응답입니다. 실제 답변은 OpenAI와 문서 색인을 설정한 뒤 제공돼요.'
        return ChatMessage(role='assistant', content=content, referenced_item_ids=message.referenced_item_ids)
