import { test, expect } from '@playwright/test';
import { resetState } from './helpers';

test.beforeEach(async ({ request }) => resetState(request));

test('health', async ({ request }) => {
  const r = await request.get('/api/health');
  expect(r.ok()).toBeTruthy();
});

test('portfolio starts with cash and no positions', async ({ request }) => {
  const pf = await (await request.get('/api/portfolio')).json();
  expect(pf.cash_balance).toBeCloseTo(10000, 1);
  expect(pf.positions).toHaveLength(0);
});

test('buy then sell updates cash', async ({ request }) => {
  const buy = await request.post('/api/portfolio/trade', { data: { ticker: 'AAPL', quantity: 5, side: 'buy' } });
  expect(buy.ok()).toBeTruthy();
  let pf = await (await request.get('/api/portfolio')).json();
  expect(pf.cash_balance).toBeLessThan(10000);
  expect(pf.positions[0].ticker).toBe('AAPL');
  const sell = await request.post('/api/portfolio/trade', { data: { ticker: 'AAPL', quantity: 5, side: 'sell' } });
  expect(sell.ok()).toBeTruthy();
  pf = await (await request.get('/api/portfolio')).json();
  expect(pf.positions).toHaveLength(0);
});

test('rejects oversell and insufficient cash', async ({ request }) => {
  const a = await request.post('/api/portfolio/trade', { data: { ticker: 'AAPL', quantity: 1, side: 'sell' } });
  expect(a.status()).toBeGreaterThanOrEqual(400);
  const b = await request.post('/api/portfolio/trade', { data: { ticker: 'AAPL', quantity: 1e6, side: 'buy' } });
  expect(b.status()).toBeGreaterThanOrEqual(400);
});

test('portfolio history has snapshots after a trade', async ({ request }) => {
  await request.post('/api/portfolio/trade', { data: { ticker: 'MSFT', quantity: 1, side: 'buy' } });
  const h = await (await request.get('/api/portfolio/history')).json();
  const arr = Array.isArray(h) ? h : h.snapshots ?? h.history;
  expect(arr.length).toBeGreaterThan(0);
});

test('SSE stream emits price events', async ({ page, baseURL }) => {
  await page.goto('/');
  const evt = await page.evaluate(
    (url) =>
      new Promise<string>((resolve, reject) => {
        const es = new EventSource(url);
        es.onmessage = (e) => { es.close(); resolve(e.data); };
        setTimeout(() => reject(new Error('no SSE event')), 8000);
      }),
    `${baseURL}/api/stream/prices`,
  );
  expect(evt).toContain('AAPL');
});

test('mock chat executes a buy', async ({ request }) => {
  const r = await request.post('/api/chat', { data: { message: 'buy 5 TSLA' } });
  expect(r.ok()).toBeTruthy();
  const body = await r.json();
  expect(body.message).toBeTruthy();
  expect(body.message).toBe('Buying 5 TSLA at market.');
  expect(body.trades[0].status).toBe('executed');
  const pf = await (await request.get('/api/portfolio')).json();
  expect(pf.positions.find((p: any) => p.ticker === 'TSLA')?.quantity).toBeCloseTo(5);
});

test('mock chat failed sell reports an error', async ({ request }) => {
  const body = await (await request.post('/api/chat', { data: { message: 'sell 5 AAPL' } })).json();
  expect(body.trades[0].status).toBe('failed');
  expect(body.message).toContain('could not be completed');
});

test('mock chat adds a watchlist ticker', async ({ request }) => {
  await request.post('/api/chat', { data: { message: 'add PYPL' } });
  const wl = await (await request.get('/api/watchlist')).json();
  expect(wl.watchlist.map((w: any) => w.ticker)).toContain('PYPL');
});
