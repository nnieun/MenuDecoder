import type { components } from './schema';
export type Analysis = components['schemas']['Analysis'];
export type MenuItem = components['schemas']['MenuItem'];
export type ChatMessage = components['schemas']['ChatMessage'];
export type Citation = components['schemas']['Citation'];
export type MenuImage = components['schemas']['MenuImage'];
type Accepted = components['schemas']['Accepted'];
const base = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const storageKey = 'menu-decoder-session';
export const newKey = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2, '0')).join('');
export function session(): Accepted | null {
  try { return JSON.parse(sessionStorage.getItem(storageKey) || 'null'); } catch { return null; }
}
export function clearSession() { sessionStorage.removeItem(storageKey); }
export class ApiError extends Error {
  constructor(public status: number, message: string, public retryable = false) { super(message); }
}
async function request<T>(path: string, init: RequestInit = {}, id?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (id) {
    const current = session();
    if (!current || current.analysis_id !== id) throw new ApiError(401, '현재 탭에서 접근할 수 없는 분석이에요.');
    headers.set('Authorization', `Bearer ${current.session_token}`);
  }
  let response: Response;
  try { response = await fetch(base + path, { ...init, headers, signal: AbortSignal.timeout(180000) }); }
  catch { throw new ApiError(0, '서버 연결이 끊겼어요. 연결 상태를 확인한 후 다시 시도해 주세요.', true); }
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(response.status, data?.error?.message || '요청을 처리하지 못했어요.', data?.error?.retryable ?? false);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
const root = (id: string) => `/api/v1/analyses/${encodeURIComponent(id)}`;
function post<T>(id: string, path: string, body: unknown, key: string, method = 'POST') {
  return request<T>(root(id) + path, { method, headers: { 'Content-Type': 'application/json', 'Idempotency-Key': key }, body: JSON.stringify(body) }, id);
}
const pendingMutations = new Map<string, string>();
async function retryableMutation<T>(identity: string, action: (key: string) => Promise<T>) {
  const key = pendingMutations.get(identity) || newKey();
  pendingMutations.set(identity, key);
  try {
    const result = await action(key);
    pendingMutations.delete(identity);
    return result;
  } catch (error) {
    // A definitive client rejection can be corrected; network/server failures
    // may have committed already and must keep the original operation key.
    if (error instanceof ApiError && error.status >= 400 && error.status < 500) pendingMutations.delete(identity);
    throw error;
  }
}
export const api = {
  health: () => request<components['schemas']['Health']>('/health'),
  async create(file: Blob, _key: string) {
    const data = new FormData(); data.set('photo', file, 'menu.png'); data.set('output_language', 'ko');
    const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer())), n => n.toString(16).padStart(2, '0')).join('');
    const accepted = await retryableMutation('upload:' + hash, stableKey => request<Accepted>('/api/v1/analyses', { method: 'POST', body: data, headers: { 'Idempotency-Key': stableKey } }));
    sessionStorage.setItem(storageKey, JSON.stringify(accepted));
    return accepted;
  },
  get: (id: string) => request<Analysis>(root(id), {}, id),
  advance: (id: string, version: number, key: string) => post<Analysis>(id, '/continue', { state_version: version }, key),
  message: (id: string, content: string, _key: string) => retryableMutation(JSON.stringify([id, 'message', content]), key => post<Analysis>(id, '/messages', { content }, key)),
  edit: (id: string, item: MenuItem, original_name: string, _key: string) => retryableMutation(JSON.stringify([id, item.item_id, item.item_version, original_name]), key => post<Analysis>(id, `/items/${item.item_id}`, { original_name, item_version: item.item_version }, key, 'PATCH')),
  delete: (id: string) => request<void>(root(id), { method: 'DELETE' }, id),
};
// Shared single flight across React remounts; only the first subscriber sends a step.
const flights = new Map<string, Promise<Analysis>>();
const stepKeys = new Map<string, string>();
export function advanceOnce(id: string, version: number) {
  const key = `${id}:${version}`;
  if (!flights.has(key)) {
    const operationKey = stepKeys.get(key) || newKey(); stepKeys.set(key, operationKey);
    const promise = api.advance(id, version, operationKey).then(value => { stepKeys.delete(key); return value; }).finally(() => flights.delete(key));
    flights.set(key, promise);
  }
  return flights.get(key)!;
}
// Pydantic default_factory fields are optional in the generated OpenAPI schema even though
// the server always sends them; normalize once so render code can treat arrays as required.
export type StrictItem = Omit<MenuItem, 'citations' | 'images' | 'warnings'> & { citations: Citation[]; images: MenuImage[]; warnings: string[] };
export type StrictMessage = Omit<ChatMessage, 'referenced_item_ids' | 'citations'> & { referenced_item_ids: string[]; citations: Citation[] };
export type StrictAnalysis = Omit<Analysis, 'items' | 'messages' | 'warnings'> & { items: StrictItem[]; messages: StrictMessage[]; warnings: string[] };
export function normalize(a: Analysis): StrictAnalysis {
  return {
    ...a,
    warnings: a.warnings ?? [],
    items: (a.items ?? []).map(i => ({ ...i, citations: i.citations ?? [], images: i.images ?? [], warnings: i.warnings ?? [] })),
    messages: (a.messages ?? []).map(m => ({ ...m, referenced_item_ids: m.referenced_item_ids ?? [], citations: m.citations ?? [] })),
  };
}
export function safeUrl(value: string) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined; } catch { return undefined; }
}
