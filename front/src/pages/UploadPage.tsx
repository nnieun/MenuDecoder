import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

type Rotation = 0 | 90 | 180 | 270;

export default function UploadPage() {
  const navigate = useNavigate();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [filename, setFilename] = useState('');
  const [rotation, setRotation] = useState<Rotation>(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const url = sessionStorage.getItem('preview_url');
    const name = sessionStorage.getItem('preview_name') ?? '';
    if (!url) {
      navigate('/', { replace: true });
      return;
    }
    setPreviewUrl(url);
    setFilename(name);
    return () => {
      // cleanup is deferred to navigation
    };
  }, [navigate]);

  function rotate() {
    setRotation((r) => ((r + 90) % 360) as Rotation);
  }

  function handleReselect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    if (file.size > 3 * 1024 * 1024) {
      setError('파일 크기가 3MB를 초과해요. 더 작은 사진을 선택해 주세요.');
      return;
    }
    if (!['image/jpeg', 'image/png'].includes(file.type)) {
      setError('JPEG 또는 PNG 파일만 지원해요.');
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const url = URL.createObjectURL(file);
    sessionStorage.setItem('preview_url', url);
    sessionStorage.setItem('preview_name', file.name);
    setPreviewUrl(url);
    setFilename(file.name);
    setRotation(0);
  }

  function handleAnalyze() {
    setSubmitting(true);
    // Mock: navigate to analysis page after short delay
    setTimeout(() => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      sessionStorage.removeItem('preview_url');
      sessionStorage.removeItem('preview_name');
      navigate('/analyses/mock-001', { replace: true });
    }, 800);
  }

  const rotateStyle: React.CSSProperties = {
    transform: `rotate(${rotation}deg)`,
    transition: 'transform 0.3s ease',
  };

  return (
    <div className="mobile-container flex flex-col min-h-screen">
      {/* Header */}
      <header className="safe-header flex items-center gap-3 px-4 pb-4 border-b border-gray-100">
        <button
          onClick={() => navigate('/')}
          className="w-9 h-9 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors"
          aria-label="뒤로 가기"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M12.5 15L7.5 10L12.5 5" stroke="#1A1A1A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        <span className="font-bold text-gray-900">사진 확인</span>
      </header>

      <main className="flex-1 flex flex-col px-5 py-6 gap-5">
        {/* Image preview */}
        <div className="relative bg-gray-100 rounded-2xl overflow-hidden flex items-center justify-center"
             style={{ minHeight: 240 }}>
          {previewUrl && (
            <img
              src={previewUrl}
              alt="업로드할 메뉴판 미리보기"
              className="max-w-full max-h-80 object-contain"
              style={rotateStyle}
            />
          )}
          {/* Rotate button */}
          <button
            onClick={rotate}
            className="absolute bottom-3 right-3 bg-white rounded-full shadow-md w-10 h-10 flex items-center justify-center active:bg-gray-50"
            aria-label="사진 회전"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M3 9a6 6 0 1 0 6-6" stroke="#FF6F0F" strokeWidth="2" strokeLinecap="round"/>
              <path d="M9 3V1M9 3L7 5M9 3L11 5" stroke="#FF6F0F" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        {/* Filename */}
        <div className="flex items-center gap-2 bg-gray-50 rounded-xl px-4 py-3">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="1" width="12" height="14" rx="2" stroke="#9CA3AF" strokeWidth="1.5"/>
            <path d="M5 6h6M5 9h4" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <span className="text-sm text-gray-600 truncate flex-1">{filename || '선택된 파일'}</span>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="text-xs text-orange-500 font-semibold shrink-0"
          >
            다시 선택
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-start gap-2">
            <span className="text-red-500 text-sm shrink-0 mt-0.5">⚠️</span>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Info box */}
        <div className="bg-orange-50 rounded-xl px-4 py-3 flex items-start gap-2">
          <span className="text-sm shrink-0">💡</span>
          <p className="text-xs text-orange-700 leading-relaxed">
            메뉴판이 똑바로 보이도록 회전 버튼으로 조정해 주세요. 분석 정확도가 높아져요.
          </p>
        </div>

        <div className="flex-1" />

        {/* Analyze button */}
        <button
          onClick={handleAnalyze}
          disabled={submitting}
          className="w-full bg-orange-500 disabled:bg-orange-300 text-white font-bold py-4 rounded-2xl text-base transition-colors flex items-center justify-center gap-2 shadow-md shadow-orange-200"
        >
          {submitting ? (
            <>
              <span className="animate-spin inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
              분석 시작 중...
            </>
          ) : (
            '분석 시작하기'
          )}
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleReselect}
        />
      </main>
    </div>
  );
}
