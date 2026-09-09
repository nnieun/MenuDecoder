import type { Analysis } from '../types';

export const MOCK_ANALYSIS: Analysis = {
  analysis_id: 'mock-001',
  status: 'partial',
  state_version: 3,
  remaining_work: true,
  request_id: 'req-mock-001',
  messages: [],
  items: [
    {
      item_id: 'item-1',
      original_name: '黒毛和牛サーロインステーキ',
      translated_name: '흑모 와규 서로인 스테이크',
      original_price_text: '¥6,800',
      description:
        '일본 최고급 흑모 와규를 두툼하게 썰어 구운 서로인 스테이크입니다. 특유의 마블링으로 부드럽고 진한 풍미가 특징이며, 제철 채소와 함께 제공됩니다. 국내산 와규와는 다른 깊은 감칠맛이 있습니다.',
      item_version: 1,
      status: 'done',
      warnings: [],
      citations: [
        {
          source_id: 'src-1',
          document_title: '와규 품종 안내',
          source_url: 'https://example.com/wagyu',
          section_path: '흑모 와규 > 서로인',
        },
      ],
      images: [
        {
          image_id: 'img-1',
          image_url:
            'https://images.unsplash.com/photo-1544025162-d76694265947?w=400&h=300&fit=crop&auto=format',
          source_page_url: 'https://unsplash.com',
          caption: '와규 서로인 스테이크 참고 사진',
          reference_only: true,
        },
      ],
    },
    {
      item_id: 'item-2',
      original_name: '本日の鮮魚の刺身盛り合わせ',
      translated_name: '오늘의 생선회 모둠',
      original_price_text: '¥3,200',
      description:
        '그날 입고된 제철 생선을 얇게 썰어 모둠으로 담아낸 회 플레이트입니다. 방문일에 따라 참치, 광어, 연어, 방어 등 구성이 달라집니다. 신선도를 중시하는 가게 방침에 따라 그날 아침 경매에서 직접 구입합니다.',
      item_version: 1,
      status: 'done',
      warnings: [],
      citations: [],
      images: [
        {
          image_id: 'img-2',
          image_url:
            'https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=400&h=300&fit=crop&auto=format',
          source_page_url: 'https://unsplash.com',
          caption: '생선회 모둠 참고 사진',
          reference_only: true,
        },
      ],
    },
    {
      item_id: 'item-3',
      original_name: '特製担々麺（辛さ調整可）',
      translated_name: '특제 탄탄멘 (매운맛 조절 가능)',
      original_price_text: '¥1,450',
      description:
        '참깨 베이스의 진한 육수에 매콤한 고기 소보로와 청경채를 올린 중화풍 국수입니다. 매운맛은 1~5단계로 조절 가능하며, 기본은 2단계입니다. 땅콩 알레르기가 있는 경우 직원에게 알려주세요.',
      item_version: 1,
      status: 'done',
      warnings: ['땅콩 알레르기 주의'],
      citations: [],
      images: [
        {
          image_id: 'img-3',
          image_url:
            'https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400&h=300&fit=crop&auto=format',
          source_page_url: 'https://unsplash.com',
          caption: '탄탄멘 참고 사진',
          reference_only: true,
        },
      ],
    },
    {
      item_id: 'item-4',
      original_name: '京野菜の天ぷら盛り合わせ',
      translated_name: '교토 채소 튀김 모둠',
      original_price_text: '¥1,200',
      description:
        '교토 근교에서 재배한 제철 야채를 가볍게 튀겨낸 덴푸라 모둠입니다. 유바(두부피), 마, 연근, 은행 등이 포함되며 천일염과 튀김간장 두 가지 소스와 함께 나옵니다.',
      item_version: 1,
      status: 'searching_images' as any,
      warnings: [],
      citations: [],
      images: [],
    },
    {
      item_id: 'item-5',
      original_name: '抹茶アイスクリーム',
      translated_name: '말차 아이스크림',
      original_price_text: '¥680',
      description:
        '교토산 최고급 말차를 사용한 진한 그린티 아이스크림입니다. 쌉쌀한 말차 향이 진하게 나며 단팥과 함께 제공됩니다.',
      item_version: 1,
      status: 'done',
      warnings: [],
      citations: [],
      images: [
        {
          image_id: 'img-5',
          image_url:
            'https://images.unsplash.com/photo-1589568060706-e9b7bf8793a5?w=400&h=300&fit=crop&auto=format',
          source_page_url: 'https://unsplash.com',
          caption: '말차 아이스크림 참고 사진',
          reference_only: true,
        },
      ],
    },
  ],
};

export const STATUS_LABELS: Record<string, string> = {
  queued: '메뉴판을 받았어요',
  reading: '메뉴 이름을 읽고 있어요',
  needs_review: '잘 읽히지 않는 부분을 확인해 주세요',
  searching_docs: '음식 설명을 찾고 있어요',
  searching_images: '참고 사진을 찾고 있어요',
  partial: '준비된 메뉴부터 보여드려요',
  done: '분석이 완료됐어요',
  failed: '분석을 완료하지 못했어요',
  rate_limited: '잠시 분석을 이용할 수 없어요',
  session_expired: '이용 중인 세션이 만료됐어요',
};
