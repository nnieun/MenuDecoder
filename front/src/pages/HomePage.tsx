import { useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';

export default function HomePage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    sessionStorage.setItem('preview_url', url);
    sessionStorage.setItem('preview_name', file.name);
    navigate('/upload');
  }

  return (
    <div className="mobile-container flex flex-col min-h-screen">
      {/* Header */}
      <header className="safe-header flex items-center gap-2 px-4 pb-4 border-b border-gray-100">
        <span className="text-2xl">🍱</span>
        <span className="font-bold text-lg text-gray-900">메뉴 읽기</span>
        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/history"
            className="flex items-center gap-1 text-xs text-gray-500 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full font-medium transition-colors"
            aria-label="분석 기록 보기"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" />
              <path d="M7 4.5V7l2 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            기록
          </Link>
          <span className="text-xs bg-orange-50 text-orange-500 px-2 py-1 rounded-full font-medium">
            모의 모드
          </span>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col px-5 pt-8 pb-6">
        <div className="mb-8">
          <p className="text-xs font-semibold text-orange-500 tracking-widest mb-2">일본어 메뉴판 번역</p>
          <h1 className="text-2xl font-bold text-gray-900 leading-tight mb-3">
            일본 식당 메뉴판,<br />이제 쉽게 읽어요
          </h1>
          <p className="text-gray-500 text-sm leading-relaxed">
            메뉴판 사진을 올리면 한국어 이름, 설명, 참고 사진까지 한 번에 보여드려요.
          </p>
        </div>

        {/* Sample image */}
        <div className="relative rounded-2xl overflow-hidden mb-8 bg-gray-100 aspect-[4/3]">
          <img
            src="https://images.unsplash.com/photo-1591947205642-47274e6c3405?w=480&h=360&fit=crop&auto=format"
            alt="일본 식당 메뉴판 예시"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
          <div className="absolute bottom-4 left-4 right-4">
            <span className="bg-white/90 text-gray-800 text-xs font-medium px-3 py-1.5 rounded-full">
              📷 메뉴판을 찍거나 사진을 선택하세요
            </span>
          </div>
        </div>

        {/* Feature pills */}
        <div className="flex flex-wrap gap-2 mb-8">
          {['한국어 번역', '자동 참고 사진', '설명 출처 제공', '후속 질문 가능'].map((f) => (
            <span
              key={f}
              className="text-xs bg-orange-50 text-orange-600 px-3 py-1.5 rounded-full font-medium"
            >
              {f}
            </span>
          ))}
        </div>

        {/* CTA buttons */}
        <div className="flex flex-col gap-3 mt-auto">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="w-full bg-orange-500 text-white font-bold py-4 rounded-2xl text-base active:bg-orange-600 transition-colors flex items-center justify-center gap-2 shadow-md shadow-orange-200"
          >
            <span className="text-lg">📷</span> 지금 촬영하기
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full bg-orange-50 text-orange-500 font-bold py-4 rounded-2xl text-base active:bg-orange-100 transition-colors flex items-center justify-center gap-2 border border-orange-200"
          >
            <span className="text-lg">🖼️</span> 사진 선택하기
          </button>
        </div>

        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleFileSelect}
        />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          className="hidden"
          onChange={handleFileSelect}
        />
      </main>

      {/* Footer note */}
      <footer className="px-5 pb-8 text-center text-xs text-gray-400">
        JPEG · PNG 지원 · 최대 3MB
      </footer>
    </div>
  );
}
