from typing import TypedDict
from contextvars import ContextVar
from .observability import Telemetry

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .models import ChatMessage
from .store import DomainError


class StepState(TypedDict):
    stage: str
    version: int


_active_session = ContextVar('active_session')


class Engine:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider
        self.checkpointer = InMemorySaver()
        self.telemetry = getattr(provider, "telemetry", Telemetry(store.settings))
        builder = StateGraph(StepState)
        # User content stays in the session store. Checkpoints contain metadata only.
        def advance(state, config):
            session = _active_session.get()
            self.step(session)
            return {'stage': session.analysis.status, 'version': session.analysis.state_version}
        stages = ['reading', 'describing', 'images', 'answering', 'review']
        def route(state):
            session = _active_session.get()
            analysis = session.analysis
            if analysis.status in ('queued', 'reading'):
                return 'reading'
            item = next((i for i in analysis.items if i.status in ('pending', 'reanalyzing', 'searching_docs', 'searching_images')), None)
            if item:
                return 'images' if item.status == 'searching_images' else 'describing'
            return 'answering' if any(m.status == 'sending' for m in analysis.messages) else 'review'
        for stage in stages:
            builder.add_node(stage, advance)
            builder.add_edge(stage, END)
        builder.add_conditional_edges(START, route, {stage: stage for stage in stages})
        self.graph = builder.compile(checkpointer=self.checkpointer)
        store.on_delete = self.checkpointer.delete_thread

    def run(self, session):
        token = _active_session.set(session)
        thread_id = str(session.analysis.analysis_id)
        try:
            with self.telemetry.span('analysis.step', {'analysis_id': thread_id, 'state_version': session.analysis.state_version,
                                                      'stage': session.analysis.status, 'calls': session.calls}):
                self.graph.invoke({'stage': session.analysis.status, 'version': session.analysis.state_version},
                                  {'configurable': {'thread_id': thread_id}})
        finally:
            _active_session.reset(token)
            # A step may finish after deletion. Remove its newly written checkpoint.
            if session.deleted:
                self.checkpointer.delete_thread(thread_id)
            self.telemetry.flush()

    def step(self, session):
        a = session.analysis
        if not a.remaining_work:
            return
        if session.steps >= self.store.settings.max_steps:
            a.status, a.remaining_work = 'rate_limited', False
            a.warnings.append('실행 구간 한도에 도달했어요.')
            return
        session.steps += 1
        charge = lambda: self.store.charge(session)
        current_item = None
        current_message = None
        try:
            if a.status == 'queued':
                a.status = 'reading'
                return
            if a.status == 'reading':
                try:
                    a.items = self.provider.extract(session.image, session.mime, charge)
                finally:
                    session.image = b''
                if len(a.items) > self.store.settings.max_items:
                    a.items = []
                    a.warnings.append('메뉴가 너무 많아요. 영역을 나누어 다시 촬영해 주세요.')
                if not a.items:
                    a.status, a.remaining_work = 'needs_review', False
                    return
            else:
                current_item = next((i for i in a.items if i.status in ('pending', 'reanalyzing', 'searching_docs', 'searching_images')), None)
                if current_item:
                    if current_item.status == 'searching_images':
                        self.provider.images(current_item, charge)
                        current_item.status = 'done'
                    else:
                        self.provider.describe(current_item, charge)
                        current_item.status = 'searching_images'
                else:
                    current_message = next((m for m in a.messages if m.role == 'user' and m.status == 'sending'), None)
                    if current_message:
                        answer = self.provider.answer(a, current_message, charge)
                        current_message.status = 'done'
                        a.messages.append(answer)
        except DomainError as exc:
            if exc.status == 429:
                a.status, a.remaining_work = 'rate_limited', False
                a.warnings.append(exc.message)
                return
            raise
        except Exception:
            if current_item:
                current_item.status = 'failed'
                current_item.warnings.append('외부 서비스 처리에 실패했어요. 원문 수정으로 재처리할 수 있어요.')
            elif current_message:
                current_message.status = 'failed'
                a.messages.append(ChatMessage(role='assistant', content='답변 처리에 실패했어요. 잠시 후 다시 질문해 주세요.', status='failed'))
            else:
                a.status, a.remaining_work = 'failed', False
                a.warnings.append('메뉴를 읽지 못했어요. API 설정이나 사진을 확인해 주세요.')
                return
        a.remaining_work = any(i.status in ('pending', 'reanalyzing', 'searching_docs', 'searching_images') for i in a.items) or any(m.status == 'sending' for m in a.messages)
        if a.remaining_work:
            a.status = 'partial' if any(i.status == 'done' for i in a.items) else 'searching_docs'
        elif any(i.status == 'needs_review' for i in a.items):
            a.status = 'needs_review'
        else:
            a.status = 'done' if any(i.status == 'done' for i in a.items) else 'failed'
