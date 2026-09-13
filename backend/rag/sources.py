"""Registry of RAG corpus source documents.

menu_project_plan.md 5절의 후보 목록(JNTO 웹페이지 5개)과 사용자 결정
(웹+PDF 혼합)을 그대로 반영한다. 실제 본문·발행 주체·언어·수집일·해시는
collect.py가 backend/rag/documents/*.json에 채운다. 이용 조건은 아직
법무 검토를 거치지 않았으므로 license_note에 그 사실을 그대로 남긴다.
"""
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    title: str
    url: str
    doc_type: Literal['html', 'pdf']
    language: str
    publisher: str
    license_note: str
    note: str  # 활용하려는 질문 범위 (plan 5절 표의 '활용하려는 질문 범위')


UNVERIFIED_LICENSE = (
    '이용 조건 미확정. 비상업 포트폴리오·RAG 실험 목적의 짧은 인용·발췌만 사용하고 '
    '전문 재배포는 하지 않는다고 가정한다. 실제 게시 전 발행처 이용약관을 재확인해야 한다.'
)

SOURCES: list[SourceSpec] = [
    SourceSpec(
        source_id='jnto-sushi',
        title='Sushi in Japan Guide',
        url='https://www.japan.travel/en/guide/sushi-in-japan/',
        doc_type='html',
        language='en',
        publisher='Japan National Tourism Organization (JNTO)',
        license_note=UNVERIFIED_LICENSE,
        note='음식 정의·종류',
    ),
    SourceSpec(
        source_id='jnto-ramen',
        title='A Guide to Ramen in Japan',
        url='https://www.japan.travel/en/guide/a-guide-to-ramen-in-japan/',
        doc_type='html',
        language='en',
        publisher='Japan National Tourism Organization (JNTO)',
        license_note=UNVERIFIED_LICENSE,
        note='종류·지역 차이',
    ),
    SourceSpec(
        source_id='jnto-yakitori',
        title='Yakitori: A Guide to Chicken Skewers',
        url='https://www.japan.travel/en/guide/yakitori-a-guide-to-chicken-skewers/',
        doc_type='html',
        language='en',
        publisher='Japan National Tourism Organization (JNTO)',
        license_note=UNVERIFIED_LICENSE,
        note='메뉴명·부위·소스',
    ),
    SourceSpec(
        source_id='jnto-etiquette',
        title='Japanese Food Etiquette Guide',
        url='https://www.japan.travel/en/guide/japanese-food-etiquette/',
        doc_type='html',
        language='en',
        publisher='Japan National Tourism Organization (JNTO)',
        license_note=UNVERIFIED_LICENSE,
        note='음식 문화·용어',
    ),
    SourceSpec(
        source_id='jnto-izakaya',
        title='Izakaya Dining Guide',
        url='https://www.japan.travel/en/guide/dinner-at-a-japanese-tavern/',
        doc_type='html',
        language='en',
        publisher='Japan National Tourism Organization (JNTO)',
        license_note=UNVERIFIED_LICENSE,
        note='메뉴 맥락·주문 관련 용어',
    ),
    SourceSpec(
        source_id='maff-washoku',
        title='WASHOKU: Traditional Dietary Cultures of the Japanese',
        url='https://www.maff.go.jp/e/data/publish/attach/pdf/index-20.pdf',
        doc_type='pdf',
        language='en',
        publisher='일본 농림수산성 (MAFF)',
        license_note=(
            '일본 정부 간행물. 통상 출처 표기 시 이용 가능한 경우가 많으나 이 프로젝트에서 '
            '정확한 라이선스 조항을 확인하지 않았다. ' + UNVERIFIED_LICENSE
        ),
        note='식문화·용어, PDF 형식 확보 (웹페이지와 PDF 혼합 요건 충족)',
    ),
]
