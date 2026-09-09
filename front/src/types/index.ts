export type AnalysisStatus =
  | 'queued'
  | 'reading'
  | 'needs_review'
  | 'searching_docs'
  | 'searching_images'
  | 'partial'
  | 'done'
  | 'failed'
  | 'rate_limited'
  | 'session_expired';

export type ItemStatus = 'pending' | 'done' | 'failed' | 'reanalyzing';

export interface MenuImage {
  image_id: string;
  image_url: string;
  source_page_url: string;
  caption: string;
  reference_only: true;
}

export interface Citation {
  source_id: string;
  document_title: string;
  source_url: string;
  section_path: string;
  pdf_page_index?: number;
  printed_page_label?: string;
}

export interface MenuItem {
  item_id: string;
  original_name: string;
  translated_name: string;
  original_price_text: string;
  description: string;
  item_version: number;
  status: ItemStatus;
  citations: Citation[];
  images: MenuImage[];
  warnings: string[];
}

export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  status: 'sending' | 'done' | 'failed';
  referenced_item_ids: string[];
  citations: Citation[];
}

export interface Analysis {
  analysis_id: string;
  status: AnalysisStatus;
  state_version: number;
  items: MenuItem[];
  messages: ChatMessage[];
  remaining_work: boolean;
  request_id: string;
}
