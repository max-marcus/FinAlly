'use client';
import { useMemo } from 'react';
import { fmtNum } from '@/lib/format';
import type { PriceMap } from '@/lib/types';
import { LineChart } from './LineChart';
import { Panel } from './Panel';

export function MainChart({ ticker, values, prices }: { ticker: string; values: number[]; prices: PriceMap }) {
  const points = useMemo(() => {
    const base = Math.floor(Date.now() / 1000) - values.length;
    return values.map((value, i) => ({ time: base + i, value }));
  }, [values]);
  const u = prices[ticker];
  return (
    <Panel
      title={ticker ? `${ticker} price` : 'Price chart'}
      testId="main-chart"
      className="h-full"
      right={<span className="font-mono text-xs text-ink">{u ? fmtNum(u.price) : ''}</span>}
    >
      {ticker ? <LineChart points={points} color="#209dd7" testId="main-chart-canvas" /> : (
        <div className="p-4 text-sm text-dim">Select a ticker in the watchlist to chart it.</div>
      )}
    </Panel>
  );
}
