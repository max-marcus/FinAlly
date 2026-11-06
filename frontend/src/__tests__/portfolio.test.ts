import { layoutTreemap, revaluePortfolio } from '@/lib/portfolio';
import { normalizePortfolio } from '@/lib/api';
import { appendHistory, parsePriceEvent } from '@/hooks/usePriceStream';
import type { Portfolio } from '@/lib/types';

const pf: Portfolio = {
  cash_balance: 1000, total_value: 0, unrealized_pnl: 0,
  positions: [{ ticker: 'AAPL', quantity: 10, avg_cost: 100, current_price: 100, unrealized_pnl: 0, pnl_percent: 0 }],
};

describe('portfolio calcs', () => {
  it('revalues with live prices', () => {
    const r = revaluePortfolio(pf, { AAPL: { ticker: 'AAPL', price: 110, previous_price: 100, timestamp: 0, change: 10, change_percent: 10, direction: 'up' } });
    expect(r.total_value).toBe(2100);
    expect(r.unrealized_pnl).toBe(100);
    expect(r.positions[0].pnl_percent).toBeCloseTo(10);
  });
  it('treemap areas sum to the full canvas and track weight', () => {
    const ps = [
      { ...pf.positions[0], ticker: 'A', current_price: 30, quantity: 1 },
      { ...pf.positions[0], ticker: 'B', current_price: 10, quantity: 1 },
      { ...pf.positions[0], ticker: 'C', current_price: 10, quantity: 1 },
    ];
    const rects = layoutTreemap(ps, 100, 100);
    expect(rects).toHaveLength(3);
    expect(rects.reduce((s, r) => s + r.w * r.h, 0)).toBeCloseTo(10000);
    const a = rects.find((r) => r.ticker === 'A')!;
    expect(a.w * a.h).toBeCloseTo(6000);
  });
  it('normalizes backend portfolio shape', () => {
    const n = normalizePortfolio({ cash_balance: 5, total_value: 15, positions: [{ ticker: 'X', quantity: 2, avg_cost: 4, current_price: 5 }] });
    expect(n.positions[0].unrealized_pnl).toBe(2);
  });
});

describe('stream helpers', () => {
  it('parses SSE payload and ignores junk', () => {
    expect(parsePriceEvent('{"AAPL":{"price":1}}')).toHaveProperty('AAPL');
    expect(parsePriceEvent('nope')).toBeNull();
  });
  it('caps history', () => {
    let h = {};
    for (let i = 0; i < 5; i++) h = appendHistory(h, { A: { ticker: 'A', price: i } as never }, 3);
    expect((h as Record<string, number[]>).A).toEqual([2, 3, 4]);
  });
});

import { api, normalizeWatchlist } from '@/lib/api';
describe('contract normalisation', () => {
  it('reads {watchlist:[...]}', () => {
    expect(normalizeWatchlist({ watchlist: [{ ticker: 'A', price: null }] })[0]).toEqual({ ticker: 'A', price: null });
  });
  it('reads position unrealized_pnl_percent', () => {
    const n = normalizePortfolio({ cash_balance: 1, positions: [{ ticker: 'X', quantity: 1, avg_cost: 10, current_price: 11, unrealized_pnl: 1, unrealized_pnl_percent: 10 }] });
    expect(n.positions[0].pnl_percent).toBe(10);
  });
  it('chat uses top-level trades', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ message: 'hi', actions: [{ type: 'trade' }], trades: [{ ticker: 'A', side: 'buy', quantity: 1, status: 'executed' }], watchlist_changes: [] }) }));
    const r = await api.chat('x');
    expect(r.actions?.trades).toHaveLength(1);
  });
});
