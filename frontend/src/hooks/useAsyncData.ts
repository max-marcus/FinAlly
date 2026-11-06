'use client';
import { useCallback, useEffect, useRef, useState } from 'react';

/** Generic fetch-and-hold hook with manual refresh and optional polling. */
export function useAsyncData<T>(fetcher: () => Promise<T>, initial: T, pollMs?: number) {
  const [data, setData] = useState<T>(initial);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    }
  }, []);

  useEffect(() => {
    void refresh();
    if (!pollMs) return;
    const id = setInterval(() => void refresh(), pollMs);
    return () => clearInterval(id);
  }, [refresh, pollMs]);

  return { data, error, refresh };
}
