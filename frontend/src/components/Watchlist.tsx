'use client';
import { useState } from 'react';
import { fmtPct, pnlClass } from '@/lib/format';
import type { PriceMap, WatchlistItem } from '@/lib/types';
import type { PriceHistory } from '@/hooks/usePriceStream';
import { Panel } from './Panel';
import { PriceCell } from './PriceCell';
import { Sparkline } from './Sparkline';

export function Watchlist({ items, prices, history, selected, onSelect, onAdd, onRemove }: {
  items: WatchlistItem[]; prices: PriceMap; history: PriceHistory; selected: string;
  onSelect: (t: string) => void; onAdd: (t: string) => Promise<void>; onRemove: (t: string) => Promise<void>;
}) {
  const [input, setInput] = useState('');
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = input.trim().toUpperCase();
    if (!t) return;
    try {
      await onAdd(t);
      setInput('');
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add ticker');
    }
  };

  return (
    <Panel title="Watchlist" testId="watchlist" className="h-full">
      <div className="flex h-full flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-panel text-dim">
              <tr>
                <th className="px-3 py-1 text-left font-normal">Ticker</th>
                <th className="px-1 py-1 text-right font-normal">Price</th>
                <th className="px-1 py-1 text-right font-normal">Chg %</th>
                <th className="px-1 py-1 font-normal">Trend</th>
                <th className="w-6" />
              </tr>
            </thead>
            <tbody>
              {items.map((it) => {
                const u = prices[it.ticker];
                const price = u?.price ?? it.price;
                return (
                  <tr
                    key={it.ticker}
                    data-testid={`watchlist-row-${it.ticker}`}
                    onClick={() => onSelect(it.ticker)}
                    className={`cursor-pointer border-t border-line/60 hover:bg-raised ${selected === it.ticker ? 'bg-raised' : ''}`}
                  >
                    <td className="px-3 py-1.5 font-mono font-semibold text-blue">{it.ticker}</td>
                    <td className="px-1 text-right"><PriceCell price={price} testId={`price-${it.ticker}`} /></td>
                    <td data-testid={`change-${it.ticker}`} className={`px-1 text-right font-mono ${pnlClass(u?.change_percent ?? 0)}`}>
                      {u ? fmtPct(u.change_percent) : '--'}
                    </td>
                    <td className="px-1"><Sparkline values={history[it.ticker] ?? []} /></td>
                    <td className="pr-2 text-right">
                      <button
                        data-testid={`remove-${it.ticker}`}
                        aria-label={`Remove ${it.ticker}`}
                        onClick={(e) => { e.stopPropagation(); void onRemove(it.ticker); }}
                        className="text-dim hover:text-down"
                      >
                        x
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <form onSubmit={submit} className="flex gap-1 border-t border-line p-2">
          <input
            data-testid="watchlist-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Add ticker"
            aria-label="Add ticker"
            className="min-w-0 flex-1 border border-line bg-bg px-2 py-1 font-mono text-xs uppercase text-ink outline-none focus:border-blue"
          />
          <button data-testid="watchlist-add" type="submit" className="bg-purple px-3 text-xs font-semibold text-white hover:brightness-125">
            Add
          </button>
        </form>
        {error && <div data-testid="watchlist-error" className="px-2 pb-2 text-xs text-down">{error}</div>}
      </div>
    </Panel>
  );
}
