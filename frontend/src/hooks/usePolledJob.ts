import { useEffect, useRef, useState } from 'react';
import type { Job } from '../types';

export function usePolledJob<T>(
  jobId: string | null,
  fetcher: (id: string) => Promise<Job<T>>,
): { job: Job<T> | null; error: string | null } {
  const [job, setJob] = useState<Job<T> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setJob(null);
    setError(null);
    if (!jobId) return undefined;

    const id = jobId;
    async function poll() {
      try {
        const next = await fetcher(id);
        if (cancelled) return;
        setJob(next);
        if (next.status === 'pending' || next.status === 'running') {
          timer.current = window.setTimeout(poll, 900);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    }

    void poll();
    return () => {
      cancelled = true;
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [jobId, fetcher]);

  return { job, error };
}
