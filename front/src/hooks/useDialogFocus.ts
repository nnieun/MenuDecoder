import { useEffect, useRef } from 'react';
export default function useDialogFocus(onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const close = useRef(onClose); close.current = onClose;
  useEffect(() => {
    const root = ref.current;
    const previous = document.activeElement as HTMLElement | null;
    if (!root) return;
    const focusable = () => Array.from(root.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), [tabindex="0"]'));
    (focusable()[0] || root).focus();
    function keydown(e: KeyboardEvent) {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close.current(); }
      if (e.key !== 'Tab') return;
      const nodes = focusable(); const first = nodes[0]; const last = nodes[nodes.length - 1];
      if (!first) { e.preventDefault(); root?.focus(); return; }
      if (e.shiftKey && (document.activeElement === first || document.activeElement === root)) { e.preventDefault(); last.focus(); }
      if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    root.addEventListener('keydown', keydown);
    return () => { root.removeEventListener('keydown', keydown); previous?.focus(); };
  }, []);
  return ref;
}
