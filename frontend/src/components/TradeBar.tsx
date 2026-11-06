'use client';
import { useState } from 'react';
import type { TradeSide } from '@/lib/types';

export function TradeBar({ selected, onTrade }: {
  selected: string; onTrade: (ticker: string, qty: number, side: TradeSide) => Promise<void>;
}) {
  const [ticker, setTicker] = useState('');
  const [qty, setQty] = useState('');
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const symbol = (ticker || selected).trim().toUpperCase();

  const run = async (side: TradeSide) => {
    const q = Number(qty);
    if (!symbol || !(q > 0)) {
      setMsg({ ok: false, text: 'Enter a ticker and a quantity above zero.' });
      return;
    }
    setBusy(true);
    try {
      await onTrade(symbol, q, side);
      setMsg({ ok: true, text: `${side === 'buy' ? 'Bought' : 'Sold'} ${q} ${symbol}` });
      setQty('');
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : 'Trade failed' });
    } finally {
      setBusy(false);
    }
  };

  const field = 'border border-line bg-bg px-2 py-1 font-mono text-xs text-ink outline-none focus:border-blue';
  return (
    <div data-testid="trade-bar" className="flex flex-wrap items-center gap-2 border border-line bg-panel px-3 py-2">
      <span className="text-[11px] font-semibold text-accent">Trade</span>
      <input data-testid="trade-ticker" aria-label="Ticker" placeholder={selected || 'Ticker'} value={ticker}
        onChange={(e) => setTicker(e.target.value)} className={`${field} w-24 uppercase`} />
      <input data-testid="trade-quantity" aria-label="Quantity" placeholder="Quantity" type="number" min="0" step="any" value={qty}
        onChange={(e) => setQty(e.target.value)} className={`${field} w-28`} />
      <button data-testid="buy-btn" disabled={busy} onClick={() => void run('buy')}
        className="bg-purple px-4 py-1 text-xs font-semibold text-white hover:brightness-125 disabled:opacity-50">Buy</button>
      <button data-testid="sell-btn" disabled={busy} onClick={() => void run('sell')}
        className="border border-purple px-4 py-1 text-xs font-semibold text-ink hover:bg-purple/30 disabled:opacity-50">Sell</button>
      {msg && (
        <span data-testid="trade-message" role="status" className={`text-xs ${msg.ok ? 'text-up' : 'text-down'}`}>{msg.text}</span>
      )}
    </div>
  );
}
