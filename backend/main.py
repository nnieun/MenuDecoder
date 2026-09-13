import io
import json
import re
import warnings
from uuid import UUID, uuid4

from fastapi import FastAPI, Depends, File, Form, Header, UploadFile, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from PIL import Image, UnidentifiedImageError

from .config import Settings
from .graph import Engine
from .mock import MockProvider
from .models import (Analysis, Accepted, Health, ContinueRequest, MessageRequest, EditRequest,
                     ChatMessage, ErrorResponse, ErrorDetail)
from .store import Store, DomainError


def create_app(settings=None, provider=None):
    settings = settings or Settings()
    store = Store(settings)
    if provider is None:
        if settings.ai_provider == 'openai':
            from .provider import OpenAIProvider
            provider = OpenAIProvider(settings)
        else:
            provider = MockProvider()
    engine = Engine(store, provider)
    errors = {n: {'model': ErrorResponse, 'description': text} for n, text in {
        401: '세션 토큰 필요', 404: '접근 불가 또는 만료', 409: '버전·중복 키 충돌',
        413: '3 MiB 초과', 415: 'JPEG·PNG만 허용', 422: '입력 오류', 429: '요청·예산 제한',
        502: '공급자 오류', 503: '서비스 설정 필요', 504: '공급자 시간 초과'}.items()}
    app = FastAPI(title='메뉴 읽기 API', version='1.0.0', description='익명 메뉴 분석. mock는 예시이며 openai 모드는 API 사용료가 발생합니다.', responses=errors)
    app.state.store, app.state.engine = store, engine
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=['GET', 'POST', 'PATCH', 'DELETE'],
                       allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'],
                       expose_headers=['X-Request-ID'])
    bearer = HTTPBearer(auto_error=False, description='접수 응답의 session_token. URL에 넣지 마세요.')

    @app.middleware('http')
    async def privacy_headers(request: Request, call_next):
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Request-ID'] = str(request.state.request_id)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        error = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.message, retryable=exc.retryable), request_id=request.state.request_id)
        return JSONResponse(status_code=exc.status, content=error.model_dump(mode='json'))

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return await domain_error(request, DomainError(422, 'VALIDATION_ERROR', '요청 형식과 필수 입력을 확인해 주세요.'))

    def token(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        return credentials.credentials if credentials else None

    def key(value: str = Header(alias='Idempotency-Key', description='최초 접수에는 암호학적 난수 32바이트의 64자리 hex. 재시도에는 같은 키.')):
        if not re.fullmatch(r'[a-f0-9]{64}', value):
            raise DomainError(422, 'VALIDATION_ERROR', '요청 키는 64자리 무작위 hex 문자열이어야 해요.')
        return value

    @app.get('/health', response_model=Health, operation_id='getHealth', tags=['운영'], summary='상태 확인')
    def health():
        return Health(mode=settings.ai_provider)

    @app.post('/api/v1/analyses', status_code=202, response_model=Accepted, operation_id='createAnalysis', tags=['분석'], summary='사진 접수', description='JPEG·PNG 한 장, 최대 3 MiB. 202는 접수이며 continue 요청으로 실행합니다.')
    def create(photo: UploadFile = File(), output_language: str = Form('ko'), request_key: str = Depends(key)):
        try:
            raw = photo.file.read(settings.max_upload_bytes + 1)
        finally:
            photo.file.close()
        if len(raw) > settings.max_upload_bytes:
            raise DomainError(413, 'FILE_TOO_LARGE', '사진은 최대 3 MiB까지 올릴 수 있어요.')
        if photo.content_type not in ('image/jpeg', 'image/png'):
            raise DomainError(415, 'UNSUPPORTED_MEDIA_TYPE', 'JPEG 또는 PNG 사진을 선택해 주세요.')
        if output_language != 'ko':
            raise DomainError(422, 'VALIDATION_ERROR', '한국어 출력만 지원해요.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as image:
                    actual = Image.MIME.get(image.format)
                    if actual != photo.content_type or image.width * image.height > settings.max_image_pixels:
                        raise ValueError('invalid image')
                    image.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise DomainError(422, 'VALIDATION_ERROR', '읽을 수 없는 사진이거나 해상도가 너무 높아요.') from None
        return store.create(request_key, raw, photo.content_type)

    @app.get('/api/v1/analyses/{id}', response_model=Analysis, operation_id='getAnalysis', tags=['분석'], summary='분석 상태 조회')
    def get(id: UUID, auth=Depends(token)):
        session = store.get(id, auth)
        with session.lock:
            return session.analysis.model_copy(deep=True)

    @app.post('/api/v1/analyses/{id}/continue', response_model=Analysis, operation_id='continueAnalysis', tags=['분석'], summary='한 구간 계속 실행')
    def advance(id: UUID, body: ContinueRequest, auth=Depends(token), request_key=Depends(key)):
        session = store.get(id, auth)
        def action():
            if body.state_version != session.analysis.state_version:
                raise DomainError(409, 'STATE_CONFLICT', '분석 상태가 바뀌었어요. 새로 조회해 주세요.', True)
            if not session.analysis.remaining_work:
                return False  # nothing to advance; avoid bumping state_version on a no-op
            engine.run(session)
        return store.mutate(session, 'continue', request_key, body.model_dump_json(), action)

    @app.post('/api/v1/analyses/{id}/messages', status_code=202, response_model=Analysis, operation_id='createMessage', tags=['대화'], summary='후속 질문 접수')
    def message(id: UUID, body: MessageRequest, auth=Depends(token), request_key=Depends(key)):
        session = store.get(id, auth)
        def action():
            a = session.analysis
            if a.remaining_work or not a.items or a.status == 'rate_limited':
                raise DomainError(409, 'STATE_CONFLICT', '현재 분석이 끝난 뒤 질문해 주세요.')
            if len(a.messages) >= settings.max_messages * 2:
                raise DomainError(429, 'RATE_LIMITED', '대화 한도에 도달했어요.')
            if not set(body.referenced_item_ids).issubset({i.item_id for i in a.items}):
                raise DomainError(422, 'VALIDATION_ERROR', '현재 분석에 없는 메뉴예요.')
            a.messages.append(ChatMessage(role='user', content=body.content, status='sending', referenced_item_ids=body.referenced_item_ids))
            a.status, a.remaining_work = 'partial', True
        return store.mutate(session, 'messages', request_key, body.model_dump_json(), action)

    @app.patch('/api/v1/analyses/{id}/items/{item_id}', status_code=202, response_model=Analysis, operation_id='editItem', tags=['메뉴'], summary='원문 수정·재처리 접수')
    def edit(id: UUID, item_id: UUID, body: EditRequest, auth=Depends(token), request_key=Depends(key)):
        session = store.get(id, auth)
        def action():
            item = next((i for i in session.analysis.items if i.item_id == item_id), None)
            if not item:
                raise DomainError(404, 'ANALYSIS_NOT_FOUND', '메뉴를 찾을 수 없어요.')
            if item.item_version != body.item_version:
                raise DomainError(409, 'STATE_CONFLICT', '다른 수정이 반영됐어요. 최신 원문을 확인해 주세요.', True)
            item.original_name, item.translated_name, item.description = body.original_name, '', ''
            item.item_version += 1
            item.citations, item.images, item.warnings = [], [], []
            item.status = 'reanalyzing'
            session.analysis.status, session.analysis.remaining_work = 'partial', True
        return store.mutate(session, 'items/' + str(item_id), request_key, body.model_dump_json(), action)

    @app.delete('/api/v1/analyses/{id}', status_code=204, operation_id='deleteAnalysis', tags=['분석'], summary='세션·분석 삭제', response_class=Response)
    def delete(id: UUID, auth=Depends(token)):
        store.get(id, auth)
        store.remove(str(id))
        return Response(status_code=204)

    return app


app = create_app()


if __name__ == '__main__':
    from pathlib import Path
    Path('docs').mkdir(exist_ok=True)
    Path('docs/openapi.json').write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
