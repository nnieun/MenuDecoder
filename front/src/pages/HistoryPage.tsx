import { useNavigate } from 'react-router-dom';
import { MOCK_HISTORY } from '../mocks/historyData';
import type { AnalysisRecord } from '../mocks/historyData';

function statusLabel(status: AnalysisRecord['status']) {
  if (status === 'done') return { text: '완료', cls: 'bg-green-50 text-green-600' };
  if (status === 'partial') return { text: '분석 중', cls: 'bg-orange-50 text-orange-500' };
  return { text: '실패', cls: 'bg-red-50 text-red-500' };
}

function relativeDate(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  const d = Math.floor(h / 24);
  if (h < 1) return '방금 전';
  if (h < 24) return `${h}시간 전`;
  if (d < 7) return `${d}일 전`;
  return new Date(iso).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
}

export default function HistoryPage() {
  const navigate = useNavigate();

  return (
    <div className="mobile-container flex flex-col min-h-screen">
      <header className="safe-header flex items-center gap-3 px-4 pb-4 border-b border-gray-100 bg-white">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
          aria-label="뒤로 가기"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M12.5 15L7.5 10L12.5 5" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <span className="font-bold text-gray-900">분석 기록</span>
      </header>

      <main className="flex-1 px-4 py-4">
        {MOCK_HISTORY.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <span className="text-5xl">🍽️</span>
            <p className="text-gray-400 text-sm">아직 분석한 메뉴판이 없어요</p>
            <button
              onClick={() => navigate('/')}
              className="mt-2 bg-orange-500 text-white text-sm font-semibold px-5 py-3 rounded-xl"
            >
              첫 메뉴판 분석하기
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-3" role="list">
            {MOCK_HISTORY.map((record) => {
              const badge = statusLabel(record.status);
              return (
                <li key={record.analysis_id}>
                  <button
                    onClick={() => navigate(`/analyses/${record.analysis_id}`)}
                    className="w-full text-left bg-white border border-gray-100 rounded-2xl overflow-hidden shadow-sm active:bg-gray-50 transition-colors flex gap-0"
                  >
                    {/* Thumbnail */}
                    <div className="w-24 shrink-0 bg-gray-100 self-stretch">
                      <img
                        src={record.thumbnail_url}
                        alt={record.restaurant_hint}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    </div>

                    {/* Info */}
                    <div className="flex-1 px-4 py-4 min-w-0">
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <p className="font-semibold text-gray-900 text-sm leading-snug truncate">
                          {record.restaurant_hint}
                        </p>
                        <span className={`shrink-0 text-[11px] font-semibold px-2 py-0.5 rounded-full ${badge.cls}`}>
                          {badge.text}
                        </span>
                      </div>

                      <p className="text-xs text-gray-400 mb-2">{relativeDate(record.created_at)}</p>

                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1 text-xs text-gray-500">
                          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                            <rect x="1" y="1" width="11" height="11" rx="2" stroke="#9CA3AF" strokeWidth="1.2" />
                            <path d="M3.5 4.5h6M3.5 6.5h4" stroke="#9CA3AF" strokeWidth="1.2" strokeLinecap="round" />
                          </svg>
                          메뉴 {record.item_count}개
                        </span>
                        {record.last_message && (
                          <span className="flex items-center gap-1 text-xs text-gray-400 truncate min-w-0">
                            <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                              <path d="M2 2.5h9a.5.5 0 01.5.5v5a.5.5 0 01-.5.5H4.5L2 10.5V3a.5.5 0 01.5-.5H2z" stroke="#9CA3AF" strokeWidth="1.2" strokeLinejoin="round" />
                            </svg>
                            <span className="truncate">{record.last_message}</span>
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Chevron */}
                    <div className="flex items-center pr-3 pl-1 text-gray-300">
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M6 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </main>

      {/* New analysis CTA */}
      <div className="px-4 pb-8 pt-3 bg-white border-t border-gray-100">
        <button
          onClick={() => navigate('/')}
          className="w-full bg-orange-500 text-white font-bold py-4 rounded-2xl text-sm flex items-center justify-center gap-2 shadow-md shadow-orange-100"
        >
          <span>📷</span> 새 메뉴판 분석하기
        </button>
      </div>
    </div>
  );
}
