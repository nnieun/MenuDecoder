"""Bounded single-process development store; never suitable for serverless production."""
import hashlib
import hmac
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from threading import RLock

from .models import Accepted, Analysis, now


class DomainError(Exception):
    def __init__(self, status, code, message, retryable=False):
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


def digest(value: bytes):
    return hashlib.sha256(value).hexdigest()


@dataclass
class Session:
    analysis: Analysis
    token_hash: str
    expires_at: object
    image: bytes = b''
    mime: str = ''
    lock: RLock = field(default_factory=RLock)
    deleted: bool = False
    steps: int = 0
    calls: int = 0
    # Idempotent snapshots contain no raw session token.
    operations: dict = field(default_factory=dict)


class Store:
    def __init__(self, settings):
        self.settings = settings
        self.sessions = {}
        self.initial = {}
        self.lock = RLock()
        self.total_calls = 0
        self.on_delete = lambda _: None
        # Process-local secret so the session token can't be recomputed from a
        # leaked Idempotency-Key alone (e.g. captured in access/gateway logs).
        self.secret = secrets.token_bytes(32)

    def cleanup(self):
        with self.lock:
            for sid, session in list(self.sessions.items()):
                if session.expires_at <= now():
                    self.remove(sid)

    def remove(self, sid):
        with self.lock:
            session = self.sessions.pop(sid, None)
            if session:
                session.deleted = True
                session.image = b''
                session.operations.clear()
                session.analysis.items.clear()
                session.analysis.messages.clear()
                self.on_delete(sid)
            self.initial = {k: v for k, v in self.initial.items() if v[1] != sid}

    def create(self, key, image, mime):
        self.cleanup()
        # Initial key is a 256-bit client capability. Server retains only its hash;
        # retry token is derived from that same capability plus a server-side secret
        # (not stored as plaintext, and not computable from a leaked key alone).
        key_hash = digest(key.encode())
        payload_hash = digest(mime.encode() + image)
        token = hmac.new(self.secret, ('menu-session:' + key).encode(), hashlib.sha256).hexdigest()
        with self.lock:
            if key_hash in self.initial:
                previous_hash, sid = self.initial[key_hash]
                if previous_hash != payload_hash:
                    raise DomainError(409, 'IDEMPOTENCY_CONFLICT', '같은 요청 키에 다른 사진을 보낼 수 없어요.')
                session = self.sessions[sid]
            else:
                if len(self.sessions) >= self.settings.max_sessions:
                    raise DomainError(429, 'RATE_LIMITED', '현재 이용 가능한 세션 수를 초과했어요.')
                analysis = Analysis(mode=self.settings.ai_provider)
                session = Session(analysis, digest(token.encode()), now() + timedelta(seconds=self.settings.session_ttl_seconds), image, mime)
                sid = str(analysis.analysis_id)
                self.sessions[sid] = session
                self.initial[key_hash] = (payload_hash, sid)
            return Accepted(analysis_id=session.analysis.analysis_id, session_token=token, expires_at=session.expires_at, mode=session.analysis.mode)

    def get(self, sid, token):
        self.cleanup()
        if not token:
            raise DomainError(401, 'SESSION_REQUIRED', '세션 토큰이 필요해요.')
        with self.lock:
            session = self.sessions.get(str(sid))
            if not session or not hmac.compare_digest(session.token_hash, digest(token.encode())):
                raise DomainError(404, 'ANALYSIS_NOT_FOUND', '접근할 수 없거나 만료된 분석이에요.')
            session.expires_at = now() + timedelta(seconds=self.settings.session_ttl_seconds)
            return session

    def charge(self, session):
        with self.lock:
            if session.deleted:
                raise DomainError(404, 'ANALYSIS_NOT_FOUND', '삭제된 분석이에요.')
            if session.calls >= self.settings.max_provider_calls or self.total_calls >= self.settings.global_provider_calls:
                raise DomainError(429, 'BUDGET_LIMIT_REACHED', '설정된 AI 호출 한도에 도달했어요.')
            session.calls += 1
            self.total_calls += 1

    def mutate(self, session, path, key, body, action):
        fingerprint = digest(body.encode())
        operation_key = (path, key)
        if not session.lock.acquire(blocking=False):
            raise DomainError(409, 'STATE_CONFLICT', '다른 요청이 실행 중이에요. 최신 상태를 확인해 주세요.', True)
        try:
            if session.deleted:
                raise DomainError(404, 'ANALYSIS_NOT_FOUND', '삭제된 분석이에요.')
            if operation_key in session.operations:
                previous_hash, result = session.operations[operation_key]
                if previous_hash != fingerprint:
                    raise DomainError(409, 'IDEMPOTENCY_CONFLICT', '같은 요청 키의 내용이 달라요.')
                return result.model_copy(deep=True)
            if len(session.operations) >= self.settings.max_steps * 3:
                raise DomainError(429, 'RATE_LIMITED', '세션 요청 한도에 도달했어요.')
            action()
            if session.deleted:
                raise DomainError(404, 'ANALYSIS_NOT_FOUND', '삭제된 분석이에요.')
            session.analysis.state_version += 1
            result = session.analysis.model_copy(deep=True)
            session.operations[operation_key] = (fingerprint, result)
            return result
        finally:
            session.lock.release()
