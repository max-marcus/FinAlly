'use client';
import { useEffect, useRef, useState } from 'react';
import type { ConnectionStatus, PriceMap, PriceUpdate } from '@/lib/types';

export const MAX_HISTORY = 240;
export type PriceHistory = Record<string, number[]>;

/** Pure reducer: fold one SSE payload into history arrays (sparklines / main chart). */
export function appendHistory(history: PriceHistory, update: PriceMap, max = MAX_HISTORY): PriceHistory {
  const next: PriceHistory = { ...history };
  for (const [ticker, u] of Object.entries(update)) {
    const arr = next[ticker] ? next[ticker] : [];
    next[ticker] = [...arr.slice(-(max - 1)), u.price];
  }
  return next;
}

export function parsePriceEvent(raw: string): PriceMap | null {
  try {
    const data = JSON.parse(raw) as Record<string, PriceUpdate>;
    if (!data || typeof data !== 'object') return null;
    return data;
  } catch {
    return null;
  }
}

export interface PriceStream {
  prices: PriceMap;
  history: PriceHistory;
  status: ConnectionStatus;
}

type EventSourceFactory = (url: string) => EventSource;

export function usePriceStream(
  url = '/api/stream/prices',
  factory: EventSourceFactory = (u) => new EventSource(u),
): PriceStream {
  const [prices, setPrices] = useState<PriceMap>({});
  const [history, setHistory] = useState<PriceHistory>({});
  const [status, setStatus] = useState<ConnectionStatus>('reconnecting');
  const factoryRef = useRef(factory);

  useEffect(() => {
    const es = factoryRef.current(url);
    es.onopen = () => setStatus('connected');
    es.onmessage = (e: MessageEvent) => {
      const data = parsePriceEvent(e.data);
      if (!data) return;
      setStatus('connected');
      setPrices((p) => ({ ...p, ...data }));
      setHistory((h) => appendHistory(h, data));
    };
    es.onerror = () => setStatus(es.readyState === 2 ? 'disconnected' : 'reconnecting');
    return () => es.close();
  }, [url]);

  return { prices, history, status };
}
