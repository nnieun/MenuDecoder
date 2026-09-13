let selected: File | null = null;
let preview: string | null = null;
export function setPhoto(file: File) {
  if (!['image/jpeg', 'image/png'].includes(file.type)) throw new Error('JPEG 또는 PNG 파일만 지원해요.');
  if (file.size > 3145728) throw new Error('사진은 최대 3 MiB까지 올릴 수 있어요.');
  clearPhoto(); selected = file; preview = URL.createObjectURL(file);
  return preview;
}
export function getPhoto() { return { file: selected, url: preview }; }
export function clearPhoto() { if (preview) URL.revokeObjectURL(preview); selected = null; preview = null; }
export async function transformPhoto(rotation: number, crop: number[]) {
  if (!selected) throw new Error('사진을 다시 선택해 주세요.');
  const image = await createImageBitmap(selected);
  try {
    const canvas = document.createElement('canvas');
    canvas.width = rotation % 180 ? image.height : image.width;
    canvas.height = rotation % 180 ? image.width : image.height;
    const ctx = canvas.getContext('2d')!;
    ctx.translate(canvas.width / 2, canvas.height / 2); ctx.rotate(rotation * Math.PI / 180);
    ctx.drawImage(image, -image.width / 2, -image.height / 2);
    const [left, top, right, bottom] = crop;
    const output = document.createElement('canvas');
    output.width = Math.max(1, Math.round(canvas.width * (right - left) / 100));
    output.height = Math.max(1, Math.round(canvas.height * (bottom - top) / 100));
    output.getContext('2d')!.drawImage(canvas, canvas.width * left / 100, canvas.height * top / 100, output.width, output.height, 0, 0, output.width, output.height);
    const blob = await new Promise<Blob>((resolve, reject) => output.toBlob(b => b ? resolve(b) : reject(new Error('이미지 변환 실패')), 'image/png'));
    if (blob.size > 3145728) throw new Error('변환한 사진이 3 MiB를 초과해요. 영역을 더 작게 선택해 주세요.');
    return blob;
  } finally { image.close(); }
}

// Server discards the uploaded photo right after extraction (no re-fetch endpoint),
// so the analysis screen keeps its own copy client-side for visual side-by-side
// comparison. sessionStorage only - cleared with the tab, never sent anywhere.
const photoKey = (analysisId: string) => `menu-decoder-photo:${analysisId}`;
function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('사진을 저장하지 못했어요.'));
    reader.readAsDataURL(blob);
  });
}
export async function savePhotoForAnalysis(analysisId: string, blob: Blob) {
  try { sessionStorage.setItem(photoKey(analysisId), await blobToDataUrl(blob)); }
  catch { /* best-effort only; the analysis itself doesn't depend on this */ }
}
export function getPhotoForAnalysis(analysisId: string) {
  try { return sessionStorage.getItem(photoKey(analysisId)); } catch { return null; }
}
export function clearPhotoForAnalysis(analysisId: string) {
  try { sessionStorage.removeItem(photoKey(analysisId)); } catch { /* ignore */ }
}
