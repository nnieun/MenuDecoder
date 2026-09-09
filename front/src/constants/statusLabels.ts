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
