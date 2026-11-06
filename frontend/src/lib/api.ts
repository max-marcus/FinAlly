import type {
  ChatActions,
  ChatMessage,
  Portfolio,
  Position,
  Snapshot,
  TradeRequest,
  WatchlistItem,
} from './types';

/** Single module that talks to the backend. Response normalisation lives here so contract changes stay cheap. */

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const b = body as { detail?: unknown; error?: string; message?: string } | null;
    const detail = typeof b?.detail === 'string' ? b.detail : b?.error ?? b?.message;
    throw new ApiError(detail ?? `Request failed (${res.status})`, res.status);
  }
  return body as T;
}

const num = (v: unknown, d = 0): number => (typeof v === 'number' && Number.isFinite(v) ? v : d);

export function normalizePosition(r: Record<string, unknown>): Position {
  const quantity = num(r.quantity);
  const avg = num(r.avg_cost);
  const price = num(r.current_price ?? r.price, avg);
  const pnl = num(r.unrealized_pnl, (price - avg) * quantity);
  const pct = num(r.pnl_percent ?? r.unrealized_pnl_percent ?? r.pnl_pct, avg > 0 ? ((price - avg) / avg) * 100 : 0);
  return { ticker: String(r.ticker), quantity, avg_cost: avg, current_price: price, unrealized_pnl: pnl, pnl_percent: pct };
}

export function normalizePortfolio(r: Record<string, unknown>): Portfolio {
  const positions = ((r.positions as Record<string, unknown>[]) ?? []).map(normalizePosition);
  const cash = num(r.cash_balance ?? r.cash, 0);
  return {
    cash_balance: cash,
    total_value: num(r.total_value, cash),
    unrealized_pnl: num(r.unrealized_pnl, positions.reduce((s, p) => s + p.unrealized_pnl, 0)),
    positions,
  };
}

export function normalizeWatchlist(r: unknown): WatchlistItem[] {
  const list = Array.isArray(r) ? r : ((r as { tickers?: unknown[]; watchlist?: unknown[] })?.tickers ?? (r as { watchlist?: unknown[] })?.watchlist ?? []);
  return (list as unknown[]).map((i) =>
    typeof i === 'string'
      ? { ticker: i, price: null }
      : { ticker: String((i as { ticker: string }).ticker), price: (i as { price?: number | null }).price ?? null },
  );
}

export function normalizeSnapshots(r: unknown): Snapshot[] {
  const list = Array.isArray(r) ? r : ((r as { snapshots?: unknown[]; history?: unknown[] })?.snapshots ?? (r as { history?: unknown[] })?.history ?? []);
  return (list as Record<string, unknown>[]).map((s) => ({
    total_value: num(s.total_value),
    recorded_at: String(s.recorded_at),
  }));
}

export function normalizeActions(r: unknown): ChatActions | null {
  if (!r || typeof r !== 'object') return null;
  const a = r as Partial<ChatActions>;
  return { trades: a.trades ?? [], watchlist_changes: a.watchlist_changes ?? [] };
}

export const api = {
  async getPortfolio(): Promise<Portfolio> {
    return normalizePortfolio(await request('/api/portfolio'));
  },
  async trade(t: TradeRequest): Promise<void> {
    await request('/api/portfolio/trade', { method: 'POST', body: JSON.stringify(t) });
  },
  async getHistory(): Promise<Snapshot[]> {
    return normalizeSnapshots(await request('/api/portfolio/history'));
  },
  async getWatchlist(): Promise<WatchlistItem[]> {
    return normalizeWatchlist(await request('/api/watchlist'));
  },
  async addTicker(ticker: string): Promise<void> {
    await request('/api/watchlist', { method: 'POST', body: JSON.stringify({ ticker }) });
  },
  async removeTicker(ticker: string): Promise<void> {
    await request(`/api/watchlist/${encodeURIComponent(ticker)}`, { method: 'DELETE' });
  },
  async chat(message: string): Promise<Omit<ChatMessage, 'id' | 'role'>> {
    const r = await request<{ message?: string; trades?: unknown; watchlist_changes?: unknown; actions?: unknown }>(
      '/api/chat',
      { method: 'POST', body: JSON.stringify({ message }) },
    );
    // Contract: top-level `trades` / `watchlist_changes`; `actions` is a flat list we ignore.
    const actions = normalizeActions({ trades: r.trades, watchlist_changes: r.watchlist_changes });
    return { content: r.message ?? '', actions };
  },
};

export type Api = typeof api;
