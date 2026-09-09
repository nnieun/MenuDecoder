import { useState, useRef, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { MOCK_ANALYSIS, STATUS_LABELS } from '../mocks/analysisData';
import type { Analysis, MenuItem, ChatMessage } from '../types';

// ─── Status Badge ────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: Analysis['status'] }) {
  const isActive = ['queued', 'reading', 'searching_docs', 'searching_images', 'partial'].includes(status);
  const isError = status === 'failed' || status === 'rate_limited' || status === 'session_expired';
  const base = 'inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full';
  const color = isError
    ? 'bg-red-50 text-red-600'
    : isActive
    ? 'bg-orange-50 text-orange-600'
    : 'bg-green-50 text-green-600';
  return (
    <span className={`${base} ${color}`} role="status" aria-live="polite">
      {isActive && (
        <span className="w-2 h-2 rounded-full bg-orange-400 animate-pulse inline-block" />
      )}
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ─── Citations Panel ──────────────────────────────────────────────────────────
function CitationsPanel({ item, onClose }: { item: MenuItem; onClose: () => void }) {
  const dialogRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end"
      role="dialog"
      aria-modal="true"
      aria-label="출처 보기"
    >
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div
        ref={dialogRef}
        tabIndex={-1}
        className="relative w-full max-w-md mx-auto bg-white rounded-t-3xl px-5 pt-5 pb-10 outline-none"
        onKeyDown={(e) => e.key === 'Escape' && onClose()}
      >
        <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-4" />
        <h2 className="font-bold text-gray-900 mb-1">{item.translated_name}</h2>
        <p className="text-xs text-gray-500 mb-5">{item.original_name}</p>

        {item.citations.length === 0 && item.images.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">출처 정보가 없어요.</p>
        ) : null}

        {item.citations.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">문서 출처</p>
            {item.citations.map((c) => (
              <div key={c.source_id} className="bg-gray-50 rounded-xl p-3 mb-2">
                <p className="text-sm font-medium text-gray-800">{c.document_title}</p>
                <p className="text-xs text-gray-500 mt-0.5">{c.section_path}</p>
                {c.source_url && (
                  <a
                    href={c.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-orange-500 mt-1 inline-block"
                  >
                    원본 보기 →
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {item.images.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">사진 출처</p>
            {item.images.map((img) => (
              <div key={img.image_id} className="bg-gray-50 rounded-xl p-3 mb-2 flex items-center gap-3">
                <img src={img.image_url} alt={img.caption} className="w-12 h-12 object-cover rounded-lg bg-gray-200" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-500 truncate">{img.caption}</p>
                  <a
                    href={img.source_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-orange-500"
                  >
                    원본 페이지 →
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={onClose}
          className="mt-4 w-full py-3 rounded-xl bg-gray-100 text-gray-700 font-semibold text-sm"
        >
          닫기
        </button>
      </div>
    </div>
  );
}

// ─── Edit Panel ───────────────────────────────────────────────────────────────
function EditPanel({ item, onClose, onSave }: { item: MenuItem; onClose: () => void; onSave: (id: string, name: string) => void }) {
  const [value, setValue] = useState(item.original_name);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  function handleSave() {
    if (!value.trim() || value === item.original_name) { onClose(); return; }
    setSaving(true);
    setTimeout(() => {
      onSave(item.item_id, value.trim());
      onClose();
    }, 600);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end" role="dialog" aria-modal="true" aria-label="원문 수정">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-md mx-auto bg-white rounded-t-3xl px-5 pt-5 pb-10"
           onKeyDown={(e) => e.key === 'Escape' && onClose()}>
        <div className="w-10 h-1 bg-gray-200 rounded-full mx-auto mb-4" />
        <h2 className="font-bold text-gray-900 mb-1">원문 수정</h2>
        <p className="text-xs text-gray-500 mb-4">잘못 읽힌 일본어 원문을 수정하면 다시 분석해요.</p>
        <div className="bg-gray-50 rounded-xl px-3 py-2 mb-3">
          <p className="text-xs text-gray-400 mb-1">현재 원문</p>
          <p className="text-sm text-gray-700 font-medium">{item.original_name}</p>
        </div>
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full border border-gray-200 rounded-xl px-3 py-3 text-sm text-gray-900 resize-none outline-none focus:border-orange-400 transition-colors"
          rows={3}
          aria-label="수정할 원문 입력"
        />
        <div className="flex gap-2 mt-3">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl bg-gray-100 text-gray-600 font-semibold text-sm">
            취소
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !value.trim()}
            className="flex-1 py-3 rounded-xl bg-orange-500 disabled:bg-orange-300 text-white font-semibold text-sm flex items-center justify-center gap-1.5"
          >
            {saving ? <><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block" />저장 중</> : '수정 후 재분석'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Menu Card ────────────────────────────────────────────────────────────────
function MenuCard({
  item,
  onCitations,
  onEdit,
}: {
  item: MenuItem;
  onCitations: (item: MenuItem) => void;
  onEdit: (item: MenuItem) => void;
}) {
  const [imgError, setImgError] = useState(false);
  const isSearching = (item.status as string) === 'searching_images';

  return (
    <article className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm">
      {/* Image */}
      <div className="relative bg-gray-100 aspect-[4/3]">
        {isSearching && item.images.length === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <span className="w-6 h-6 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-gray-400">참고 사진 찾는 중...</span>
          </div>
        ) : item.images.length > 0 && !imgError ? (
          <>
            <img
              src={item.images[0].image_url}
              alt={item.images[0].caption}
              className="w-full h-full object-cover"
              onError={() => setImgError(true)}
            />
            <span className="absolute top-2 left-2 bg-black/60 text-white text-[10px] font-medium px-2 py-1 rounded-full">
              참고 사진
            </span>
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-gray-300 text-4xl">🍽️</span>
          </div>
        )}
      </div>

      <div className="px-4 py-4">
        {/* Names */}
        <div className="mb-1">
          <h3 className="font-bold text-gray-900 text-base leading-snug">{item.translated_name}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{item.original_name}</p>
        </div>

        {/* Price */}
        {item.original_price_text && (
          <span className="inline-block bg-orange-50 text-orange-600 text-sm font-bold px-2.5 py-1 rounded-lg mt-2 mb-3">
            {item.original_price_text}
          </span>
        )}

        {/* Status: reanalyzing */}
        {item.status === 'reanalyzing' && (
          <div className="flex items-center gap-1.5 mb-3 text-xs text-orange-600">
            <span className="w-3 h-3 border border-orange-400 border-t-transparent rounded-full animate-spin inline-block" />
            재분석 중이에요
          </div>
        )}

        {/* Description */}
        {item.description ? (
          <p className="text-sm text-gray-700 leading-relaxed mb-3">{item.description}</p>
        ) : (
          <p className="text-sm text-gray-400 leading-relaxed mb-3 italic">설명을 불러오고 있어요...</p>
        )}

        {/* Warnings */}
        {item.warnings.map((w) => (
          <div key={w} className="flex items-start gap-1.5 mb-3 bg-yellow-50 rounded-lg px-3 py-2">
            <span className="text-yellow-500 text-xs mt-0.5">⚠️</span>
            <span className="text-xs text-yellow-700">{w}</span>
          </div>
        ))}

        {/* Actions */}
        <div className="flex gap-2 mt-1">
          <button
            onClick={() => onCitations(item)}
            className="flex items-center gap-1 text-xs text-gray-500 bg-gray-50 hover:bg-gray-100 px-3 py-2 rounded-lg transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 4h10M2 7h7M2 10h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
            출처 보기
          </button>
          <button
            onClick={() => onEdit(item)}
            className="flex items-center gap-1 text-xs text-gray-500 bg-gray-50 hover:bg-gray-100 px-3 py-2 rounded-lg transition-colors"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M9.5 2.5l2 2-7 7H2.5v-2l7-7z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/></svg>
            원문 수정
          </button>
        </div>
      </div>
    </article>
  );
}

// ─── Delete Confirm ───────────────────────────────────────────────────────────
function DeleteConfirm({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-5" role="dialog" aria-modal="true">
      <div className="absolute inset-0 bg-black/40" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl px-5 pt-6 pb-5 w-full max-w-sm shadow-xl">
        <h2 className="font-bold text-gray-900 text-base mb-2">분석을 삭제할까요?</h2>
        <p className="text-sm text-gray-500 mb-5">지금까지의 메뉴 분석과 대화가 모두 삭제돼요. 이 작업은 취소할 수 없어요.</p>
        <div className="flex gap-2">
          <button onClick={onCancel} className="flex-1 py-3 rounded-xl bg-gray-100 text-gray-700 font-semibold text-sm">취소</button>
          <button onClick={onConfirm} className="flex-1 py-3 rounded-xl bg-red-500 text-white font-semibold text-sm">삭제</button>
        </div>
      </div>
    </div>
  );
}

// ─── Analysis Page ────────────────────────────────────────────────────────────
export default function AnalysisPage() {
  const { analysisId } = useParams();
  const navigate = useNavigate();
  const [analysis, setAnalysis] = useState<Analysis>(MOCK_ANALYSIS);
  const [citationItem, setCitationItem] = useState<MenuItem | null>(null);
  const [editItem, setEditItem] = useState<MenuItem | null>(null);
  const [showDelete, setShowDelete] = useState(false);
  const [chatInput, setChatInput] = useState('');
  const [sendingChat, setSendingChat] = useState(false);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Simulate partial → done progression
  useEffect(() => {
    if (analysis.status === 'partial') {
      const t = setTimeout(() => {
        setAnalysis((a) => ({ ...a, status: 'done', remaining_work: false }));
      }, 3000);
      return () => clearTimeout(t);
    }
  }, [analysis.status]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [analysis.messages.length]);

  function handleSendMessage() {
    const content = chatInput.trim();
    if (!content || sendingChat) return;

    const userMsg: ChatMessage = {
      message_id: `msg-${Date.now()}`,
      role: 'user',
      content,
      status: 'sending',
      referenced_item_ids: [],
      citations: [],
    };
    setAnalysis((a) => ({ ...a, messages: [...a.messages, userMsg] }));
    setChatInput('');
    setSendingChat(true);

    // Mock response
    setTimeout(() => {
      const assistantMsg: ChatMessage = {
        message_id: `msg-${Date.now()}-res`,
        role: 'assistant',
        content: `"${content}"에 대해 답변드릴게요. 이 서비스는 현재 모의 모드로 동작 중이에요. 실제 백엔드 연동 후 정확한 답변을 드릴 수 있어요.`,
        status: 'done',
        referenced_item_ids: [],
        citations: [],
      };
      setAnalysis((a) => ({
        ...a,
        messages: [
          ...a.messages.map((m) => (m.message_id === userMsg.message_id ? { ...m, status: 'done' as const } : m)),
          assistantMsg,
        ],
      }));
      setSendingChat(false);
    }, 1200);
  }

  function handleEditSave(itemId: string, newName: string) {
    setAnalysis((a) => ({
      ...a,
      items: a.items.map((i) =>
        i.item_id === itemId ? { ...i, original_name: newName, status: 'reanalyzing', item_version: i.item_version + 1 } : i
      ),
    }));
    setTimeout(() => {
      setAnalysis((a) => ({
        ...a,
        items: a.items.map((i) => (i.item_id === itemId && i.status === 'reanalyzing' ? { ...i, status: 'done' } : i)),
      }));
    }, 2000);
  }

  function handleDelete() {
    setShowDelete(false);
    sessionStorage.clear();
    navigate('/', { replace: true });
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }

  const _ = analysisId; // used in URL

  return (
    <div className="mobile-container flex flex-col" style={{ height: '100dvh' }}>
      {/* Header */}
      <header className="safe-header flex items-center gap-2 px-4 pb-3 border-b border-gray-100 bg-white shrink-0 z-10">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100"
          aria-label="홈으로"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M12.5 15L7.5 10L12.5 5" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <div className="flex-1">
          <StatusBadge status={analysis.status} />
        </div>
        <button
          onClick={() => setShowDelete(true)}
          className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 text-gray-400"
          aria-label="분석 삭제"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M3 4.5h12M7.5 4.5V3h3v1.5M6 4.5v9a1.5 1.5 0 001.5 1.5h3A1.5 1.5 0 0012 13.5v-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Mock mode notice */}
        <div className="mx-4 mt-3 mb-1 bg-blue-50 border border-blue-100 rounded-xl px-3 py-2 flex items-start gap-2">
          <span className="text-blue-400 text-xs mt-0.5">ℹ️</span>
          <p className="text-xs text-blue-600">모의 모드 — 테스트용 예시 데이터입니다. 실제 분석 결과가 아니에요.</p>
        </div>

        {/* Menu cards */}
        <div className="flex flex-col gap-3 px-4 py-3">
          {analysis.items.map((item) => (
            <MenuCard
              key={item.item_id}
              item={item}
              onCitations={setCitationItem}
              onEdit={setEditItem}
            />
          ))}
          {analysis.remaining_work && (
            <div className="flex items-center justify-center gap-2 py-4 text-sm text-gray-400">
              <span className="w-4 h-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin inline-block" />
              나머지 메뉴를 분석 중이에요...
            </div>
          )}
        </div>

        {/* Chat messages */}
        {analysis.messages.length > 0 && (
          <div className="px-4 pb-3 flex flex-col gap-3">
            <div className="flex items-center gap-2 mt-2">
              <div className="flex-1 h-px bg-gray-100" />
              <span className="text-xs text-gray-400 shrink-0">대화</span>
              <div className="flex-1 h-px bg-gray-100" />
            </div>
            {analysis.messages.map((msg) => (
              <div key={msg.message_id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-orange-100 flex items-center justify-center text-sm shrink-0 mr-2 mt-1">
                    🍱
                  </div>
                )}
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-orange-500 text-white rounded-br-sm'
                      : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                  }`}
                >
                  {msg.content}
                  {msg.status === 'sending' && (
                    <span className="ml-1 inline-block w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                  )}
                </div>
              </div>
            ))}
            <div ref={chatBottomRef} />
          </div>
        )}

        {/* Bottom padding for input */}
        <div className="h-4" />
      </div>

      {/* Chat input */}
      <div className="shrink-0 bg-white border-t border-gray-100 px-4 py-3 pb-safe">
        <div className="flex items-end gap-2 bg-gray-50 rounded-2xl px-3 py-2">
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="메뉴에 대해 궁금한 점을 물어보세요"
            className="flex-1 bg-transparent text-sm text-gray-900 placeholder-gray-400 resize-none outline-none max-h-28 min-h-[24px]"
            rows={1}
            aria-label="후속 질문 입력"
            disabled={sendingChat}
          />
          <button
            onClick={handleSendMessage}
            disabled={!chatInput.trim() || sendingChat}
            className="w-9 h-9 rounded-xl bg-orange-500 disabled:bg-gray-200 text-white flex items-center justify-center shrink-0 transition-colors"
            aria-label="질문 보내기"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 8h12M9 3l5 5-5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Panels */}
      {citationItem && <CitationsPanel item={citationItem} onClose={() => setCitationItem(null)} />}
      {editItem && <EditPanel item={editItem} onClose={() => setEditItem(null)} onSave={handleEditSave} />}
      {showDelete && <DeleteConfirm onCancel={() => setShowDelete(false)} onConfirm={handleDelete} />}
    </div>
  );
}
