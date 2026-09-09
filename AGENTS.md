# 프로젝트 작업 규칙

- `docs`의 기획 및 산출물 Markdown을 읽고 구현한다. `frontend_plan.md`는 수정하지 않는다.
- 사용자 지정 경로는 `front/`이며 기존 Mobile Web App Design 디자인을 유지한다. 서버·RAG는 `backend/`에 둔다.
- 커밋 author와 committer는 현재 사용자 `nnieun <162238064+nnieun@users.noreply.github.com>`만 사용한다.
- 매 커밋 직전에 `git var GIT_AUTHOR_IDENT`, `git var GIT_COMMITTER_IDENT`를 확인한다. 불일치하면 중단한다.
- GPT, Codex, Claude 및 AI·봇 명의나 공동 작성자 표기를 추가하지 않는다. 작성자 설정·환경 변수를 임의 변경하지 않는다.
- 기능별 `type(scope): 변경 내용` 커밋과 짧은 작업 브랜치를 사용한다. 원격 PR 검토 후 squash merge한다. 승인된 계정 외 push 금지.
- 모의 결과와 실제 AI 결과를 구분한다. 실행하지 않은 시험·실험·배포를 완료로 기록하지 않는다.
- 비밀 키·사용자 사진·토큰·런타임 데이터는 커밋하지 않는다.
