export interface AnalysisRecord {
  analysis_id: string;
  thumbnail_url: string;
  restaurant_hint: string;
  item_count: number;
  status: 'done' | 'partial' | 'failed';
  created_at: string;
  last_message?: string;
}

export const MOCK_HISTORY: AnalysisRecord[] = [
  {
    analysis_id: 'mock-001',
    thumbnail_url:
      'https://images.unsplash.com/photo-1591947205642-47274e6c3405?w=160&h=160&fit=crop&auto=format',
    restaurant_hint: '교토 이자카야 메뉴판',
    item_count: 5,
    status: 'done',
    created_at: '2026-09-09T14:32:00',
    last_message: '탄탄멘 맵기 2단계가 한국 기준으로 어느 정도인가요?',
  },
  {
    analysis_id: 'mock-002',
    thumbnail_url:
      'https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=160&h=160&fit=crop&auto=format',
    restaurant_hint: '오사카 스시 레스토랑',
    item_count: 12,
    status: 'done',
    created_at: '2026-09-08T19:10:00',
    last_message: undefined,
  },
  {
    analysis_id: 'mock-003',
    thumbnail_url:
      'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=160&h=160&fit=crop&auto=format',
    restaurant_hint: '도쿄 라멘 가게',
    item_count: 8,
    status: 'partial',
    created_at: '2026-09-07T12:55:00',
    last_message: '차슈는 돼지고기인가요?',
  },
  {
    analysis_id: 'mock-004',
    thumbnail_url:
      'https://images.unsplash.com/photo-1544025162-d76694265947?w=160&h=160&fit=crop&auto=format',
    restaurant_hint: '삿포로 야키니쿠',
    item_count: 20,
    status: 'done',
    created_at: '2026-09-05T20:00:00',
    last_message: undefined,
  },
];
