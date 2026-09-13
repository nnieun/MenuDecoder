# RAG 문서 수집·청킹 (RAG 7단계 중 단계 1~2)

`docs/menu_project_plan.md` 4·5·8절의 결정을 구현한다. 이 폴더는 임베딩·
Chroma·검색은 아직 포함하지 않는다 — 문서 수집·전처리·청킹까지만.

## 산출물

- `sources.py` — 수집 대상 6개 문서의 등록부(URL, 발행 주체, 언어, 이용
  조건 메모). 계획서 5절 후보(JNTO 웹페이지 5개)에 사용자 결정대로 PDF
  1개(MAFF washoku 가이드)를 더해 웹+PDF 혼합 요건을 채웠다.
- `documents.py` — HTML 정리(`clean_html`)와 PDF 페이지 추출
  (`extract_pdf`). 광고·내비게이션·탭 전환·브레드크럼·반복 바닥글
  ("Did this information help you?", "Recommended for You" 등)을 제거하고
  제목·섹션 구조·본문만 남긴다.
- `collect.py` — 실제 네트워크 수집 스크립트. `docs/openapi.json`처럼
  수동 실행 산출물이며 pytest에는 포함하지 않는다(실제 외부 요청이라서).
  실행: `.venv/Scripts/python -m backend.rag.collect`
- `documents/*.json` — 수집 결과. 문서당 `source_id, title, doc_type, url,
  language, publisher, license_note, collected_at, content_hash, sections`
  를 보존한다. `sections[].section_path`가 HTML은 제목 경로, PDF는
  물리 페이지 위치(`page_index`, 있으면 `printed_page_label`)를 담는다.
  `documents/manifest.json`이 전체 목록·해시·실패 사례를 요약한다.
- `chunking.py` — 256/512/1024 토큰 청킹(계획서 4절). 겹침은
  `floor(size*0.1)`로 고정(25/51/102). 공통 토크나이저는 tiktoken
  `cl100k_base`로 고정했다 — 모델별 실제 토크나이저 차이는 이후 임베딩
  비교 단계(EX-03)에서 별도로 기록한다.
- `stats.py` — 문서별·크기별 청크 수·토큰 분포 출력. 세 크기 사이에
  실제로 차이가 나는지(짧은 문서만 있으면 같은 결과가 나올 수 있다는
  계획서 4절의 경고) 눈으로 확인하는 용도.

## 실행한 검사

- `python -m backend.rag.stats` 결과: 256/512/1024 토큰에서 총 청크 수가
  각각 179 / 107 / 73개로 실제로 달라짐을 확인했다(짧은 문서만 모여
  크기별 결과가 동일해지는 경우가 아님).
- `backend/tests/test_rag_documents.py`, `test_rag_chunking.py`,
  `test_rag_corpus.py` — HTML 정리 규칙, 토큰 예산·겹침·section 경계
  보존, 실제 코퍼스의 언어·출처·해시 존재를 pytest로 검증한다.

## 문서별 선택 이유·발행 주체·언어·수집일·해시·이용 조건

`documents/manifest.json`이 기계가 읽을 수 있는 최신 값(수집일, 해시,
섹션 수)을 담고, 아래는 사람이 읽는 요약이다. 활용 목적은
`docs/menu_project_plan.md` 5절 표와 동일하다.

| source_id | 발행 주체 | 언어 | 형식 | 활용하려는 질문 범위 |
| --- | --- | --- | --- | --- |
| jnto-sushi | Japan National Tourism Organization | en | html | 음식 정의·종류 |
| jnto-ramen | Japan National Tourism Organization | en | html | 종류·지역 차이 |
| jnto-yakitori | Japan National Tourism Organization | en | html | 메뉴명·부위·소스 |
| jnto-etiquette | Japan National Tourism Organization | en | html | 음식 문화·용어 |
| jnto-izakaya | Japan National Tourism Organization | en | html | 메뉴 맥락·주문 관련 용어 |
| maff-washoku | 일본 농림수산성(MAFF) | en | pdf | 식문화·용어, PDF 형식 확보 |

**이용 조건 검토 (미확정 — 다음 검증 필요)**: 두 출처 모두 이 프로젝트
에서 정식 라이선스 조항을 법무 검토하지 않았다. `sources.py`의
`license_note`에 그대로 남겨 두었다 — 비상업 포트폴리오·RAG 실험 목적의
짧은 인용·발췌만 사용하고 전문 재배포는 하지 않는다는 가정으로 진행
중이며, 실제 공개 배포 전에는 각 발행처의 이용약관을 다시 확인해야
한다.

## 전처리 규칙 (요약)

- HTML: `.content-main-wrapper`(없으면 `main`/`article`/`body`) 안에서만
  본문을 찾는다. `script/style/nav/form/svg`와 JNTO 템플릿의 탭
  전환(`.mod-keyvisual__anchor-items`)·브레드크럼
  (`.mod-breadcrumb__items`)·태그 목록(`.mod-tag-list__items`)을 제거한
  뒤, "Did this information help you?" 등 위젯성 제목을 만나면 그
  지점부터 문서 끝까지 버린다(반복 바닥글 제거). 제목이 없는 앞부분
  텍스트(내비게이션 잔여물)는 첫 heading 이전이면 수집하지 않는다.
- PDF: 물리 페이지 단위로 텍스트를 추출한다. 첫 줄이 순수 숫자면
  인쇄 페이지 번호로 보고 본문에서 분리해 `printed_page_label`에 넣는다
  (추측하지 않고, 아니면 `null`로 둔다). 폰트 인코딩 문제로 생기는
  `U+FFFD`가 텍스트의 20%를 넘는 페이지는 버리고, 그 미만이면 해당
  문자만 제거한다.
- 두 형식 모두 `_MIN_SECTION_CHARS`(40자) 미만인 섹션은 노이즈로 보고
  버린다.

## 알려진 실패 사례·한계

- **geo-IP 지역화**: `japan.travel`은 요청 IP에 따라 `/en/` URL에도
  한국어 본문을 서빙한다(`Accept-Language` 헤더로는 안 바뀌고, 서버가
  응답에 내려주는 `django_language` 쿠키를 요청에 실어 보내야 영어로
  고정된다). `collect.py`가 수집한 언어가 실제로 `en`인지 표본
  검사(`_check_language`)로 확인하고, 최대 5회까지 재시도한다. 이
  안전장치가 없었다면 언어 라벨은 `en`인데 본문은 한국어인 문서가 그대로
  저장될 뻔했다.
- **PDF 폰트 인코딩**: MAFF PDF의 일부 CFF Type1 폰트가 fontTools 없이는
  완전히 디코딩되지 않아 `U+FFFD`가 섞여 나온다(경고 로그 참고). 위
  규칙으로 페이지 단위 필터링만 했고, fontTools 설치를 통한 완전한
  글리프 복구는 하지 않았다.
- **일본어 원문 자료 미포함**: 계획서 5절은 "위 후보는 영어 자료라 일본어
  원문 문서와 한국어 질의의 조합을 평가하기에 충분하지 않다"고 명시한다.
  이번 수집은 사용자 결정(계획서 후보 + PDF 1개로 최소 시작)에 따라
  영어 자료만 포함했고, 일본어 원문 자료 수집은 다음 단계로 남는다.
- **표제 경로 중복**: HTML 섹션의 `section_path`가 페이지 제목과 h1을
  중복 포함해 다소 장황하다(예: "Sushi in Japan Guide > GUIDE Sushi in
  Japan Guide ..."). 검색·청킹 동작에는 영향이 없으나 출처 표시용으로는
  다듬을 여지가 있다.

## retriever.py — BM25 검색 (단계 5의 일부)

`retriever.py`는 이 폴더가 만든 청크 위에 `rank_bm25`로 BM25 검색만
붙인다. `backend/provider.py`(OpenAIProvider)의 `describe()`/`answer()`가
이 `Retriever.search()` 결과를 근거로 실제 OpenAI 호출의 프롬프트를
구성하고, 모델이 인용한 chunk_id를 이 결과 집합과 대조해 존재하지 않는
근거는 표시 전에 버린다. 기본 청크 크기는 계획서 4절의 초기 제안값인
512 토큰(`DEFAULT_CHUNK_SIZE`)을 그대로 썼다 — 최적값이라는 근거는 아직
없다.

## 다음 단계 (아직 미구현)

임베딩(OpenAI `text-embedding-3-small` 대 `BAAI/bge-m3`) 비교 → Chroma
색인 → Hybrid(BM25+dense, RRF) → Reranking. 지금은 BM25 단독으로만
검색하며, 이는 "먼저 검색만 평가해 비용을 줄인다"는 계획서 8절의 순서를
따른 의도적 축소이지 최종 설계가 아니다. `backend/provider.py`가
extract·describe·images·answer를 실제 OpenAI 호출로 구현했지만
(`backend/manual_openai_smoke.py` 참고), 이는 실제 API 연결을 검증한
것이지 필수 비교 실험(EX-01~EX-08)을 수행한 것은 아니다.
