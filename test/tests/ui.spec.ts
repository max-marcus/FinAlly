import { test, expect } from '@playwright/test';
import { DEFAULT_TICKERS, ids, money, resetState, tid } from './helpers';

test.beforeEach(async ({ request, page }) => {
  await resetState(request);
  await page.goto('/');
});

test('fresh start: watchlist, $10k, streaming prices', async ({ page }) => {
  for (const t of DEFAULT_TICKERS) await expect(tid(page, ids.watchlistRow(t))).toBeVisible();
  await expect.poll(async () => money(await tid(page, ids.cashBalance).textContent())).toBeCloseTo(10000, 0);
  await expect(tid(page, ids.connectionStatus)).toBeVisible();
  const first = await tid(page, ids.price('AAPL')).textContent();
  await expect.poll(async () => tid(page, ids.price('AAPL')).textContent(), { timeout: 15_000 }).not.toBe(first);
});

test('add and remove a ticker', async ({ page }) => {
  await tid(page, ids.addTickerInput).fill('PYPL');
  await tid(page, ids.addTickerButton).click();
  await expect(tid(page, ids.watchlistRow('PYPL'))).toBeVisible();
  await tid(page, ids.removeTicker('PYPL')).click();
  await expect(tid(page, ids.watchlistRow('PYPL'))).toHaveCount(0);
});

test('buy then sell shares', async ({ page }) => {
  await tid(page, ids.tradeTicker).fill('AAPL');
  await tid(page, ids.tradeQuantity).fill('10');
  await tid(page, ids.buyButton).click();
  await expect(tid(page, ids.positionRow('AAPL'))).toBeVisible();
  await expect.poll(async () => money(await tid(page, ids.cashBalance).textContent())).toBeLessThan(10000);

  await tid(page, ids.tradeQuantity).fill('10');
  await tid(page, ids.sellButton).click();
  await expect(tid(page, ids.positionRow('AAPL'))).toHaveCount(0);
});

test('heatmap and P&L chart render after a trade', async ({ page }) => {
  await tid(page, ids.tradeTicker).fill('NVDA');
  await tid(page, ids.tradeQuantity).fill('5');
  await tid(page, ids.buyButton).click();
  await expect(tid(page, ids.heatmap)).toBeVisible();
  await expect(tid(page, ids.pnlChart)).toBeVisible();
});

test('mocked AI chat executes a trade inline', async ({ page }) => {
  await tid(page, ids.chatInput).fill('buy 5 AAPL');
  await tid(page, ids.chatSend).click();
  await expect(tid(page, ids.chatMessages)).toContainText('Buying 5 AAPL at market.');
  await expect(tid(page, ids.chatAction).first()).toBeVisible();
  await expect(tid(page, ids.positionRow('AAPL'))).toBeVisible();
});

test('SSE reconnects after the stream request fails', async ({ page }) => {
  const dot = tid(page, ids.connectionStatus);
  await expect(dot).toHaveAttribute('data-status', 'connected');
  // Block the stream, then reload so the new EventSource cannot connect.
  await page.route('**/api/stream/prices', (route) => route.abort());
  await page.reload();
  await expect(dot).not.toHaveAttribute('data-status', 'connected');
  // Unblock: EventSource's built-in retry should reconnect and prices should flow again.
  await page.unroute('**/api/stream/prices');
  await expect(dot).toHaveAttribute('data-status', 'connected', { timeout: 30_000 });
  const before = await tid(page, ids.price('AAPL')).textContent();
  await expect.poll(async () => tid(page, ids.price('AAPL')).textContent(), { timeout: 15_000 }).not.toBe(before);
});
