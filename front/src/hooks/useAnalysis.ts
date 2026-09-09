import { useCallback, useEffect, useState } from 'react';
import { api, advanceOnce, normalize, ApiError, type Analysis, type StrictAnalysis } from '../api/client';

export default function useAnalysis(id: string) {
  const [analysis, setAnalysis] = useState<StrictAnalysis | null>(null);
  const [error, setError] = useState('');
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [revision, setRevision] = useState(0);
  const accept = useCallback((raw: Analysis) => {
    const next = normalize(raw);
    setAnalysis(old => old && old.analysis_id === next.analysis_id && old.state_version > next.state_version ? old : next);
  }, []);
  useEffect(() => {
    let stopped = false;
    let running = false;
    async function sync() {
      if (running || document.hidden || stopped) return;
      running = true;
      try {
        let current = await api.get(id);
        if (!stopped) { accept(current); setError(''); setErrorStatus(null); }
        while (!stopped && !document.hidden && current.remaining_work && ['queued','reading','searching_docs','searching_images','partial'].includes(current.status)) {
          current = await advanceOnce(id, current.state_version);
          if (!stopped) accept(current);
        }
      } catch (e) {
        if (!stopped) {
          setError((e as Error).message);
          setErrorStatus(e instanceof ApiError ? e.status : null);
        }
      }
      finally { running = false; }
    }
    void sync();
    document.addEventListener('visibilitychange', sync);
    window.addEventListener('online', sync);
    return () => { stopped = true; document.removeEventListener('visibilitychange', sync); window.removeEventListener('online', sync); };
  }, [id, revision, accept]);
  return { analysis, accept, error, errorStatus, setError, refresh: () => setRevision(n => n + 1) };
}
