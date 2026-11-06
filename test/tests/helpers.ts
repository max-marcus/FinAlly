import { APIRequestContext, Page } from '@playwright/test';

// Ids from planning/FRONTEND_TESTIDS.md.
export const ids = {
  connectionStatus: 'connection-dot',
  totalValue: 'total-value',
  cashBalance: 'cash-balance',
  watchlist: 'watchlist',
  watchlistRow: (t: string) => `watchlist-row-${t}`,
  price: (t: string) => `price-${t}`,
  removeTicker: (t: string) => `remove-${t}`,
  addTickerInput: 'watchlist-input',
  addTickerButton: 'watchlist-add',
  mainChart: 'main-chart',
  heatmap: 'heatmap',
  pnlChart: 'pnl-chart',
  positionsTable: 'positions',
  positionRow: (t: string) => `position-row-${t}`,
  tradeTicker: 'trade-ticker',
  tradeQuantity: 'trade-quantity',
  buyButton: 'buy-btn',
  sellButton: 'sell-btn',
  chatInput: 'chat-input',
  chatSend: 'chat-send',
  chatMessages: 'chat-messages',
  chatAction: 'chat-trade-action',
};

export const DEFAULT_TICKERS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];

/** Parse "$1,234.56" -> 1234.56 */
export const money = (s: string | null) => parseFloat((s ?? '').replace(/[^0-9.\-]/g, ''));

export const tid = (page: Page, id: string) => page.getByTestId(id);

/** Restore a clean state through the API: sell all positions, remove non-default tickers, re-add defaults. */
export async function resetState(request: APIRequestContext) {
  const pf = await (await request.get('/api/portfolio')).json();
  for (const p of pf.positions ?? []) {
    await request.post('/api/portfolio/trade', { data: { ticker: p.ticker, quantity: p.quantity, side: 'sell' } });
  }
  const wl = await (await request.get('/api/watchlist')).json();
  const items: any[] = Array.isArray(wl) ? wl : wl.watchlist ?? wl.tickers ?? [];
  for (const it of items) {
    const t = typeof it === 'string' ? it : it.ticker;
    if (!DEFAULT_TICKERS.includes(t)) await request.delete(`/api/watchlist/${t}`);
  }
  for (const t of DEFAULT_TICKERS) await request.post('/api/watchlist', { data: { ticker: t } });
}
