'use client';
import { useMemo } from 'react';
import { fmtPct } from '@/lib/format';
import { layoutTreemap } from '@/lib/portfolio';
import type { Position } from '@/lib/types';
import { Panel } from './Panel';

/** Maps P&L % to a green/red fill; saturates at +/-10%. */
export function pnlColor(pct: number): string {
  const a = 0.25 + Math.min(Math.abs(pct) / 10, 1) * 0.6;
  return pct >= 0 ? `rgba(46,204,143,${a.toFixed(2)})` : `rgba(255,92,106,${a.toFixed(2)})`;
}

export function Heatmap({ positions }: { positions: Position[] }) {
  const rects = useMemo(() => layoutTreemap(positions, 100, 100), [positions]);
  return (
    <Panel title="Portfolio heatmap" testId="heatmap" className="h-full">
      {rects.length === 0 ? (
        <div className="p-4 text-sm text-dim">No positions yet. Buy a ticker to see it here.</div>
      ) : (
        <div className="relative h-full w-full">
          {rects.map((r) => (
            <div
              key={r.ticker}
              data-testid={`heatmap-cell-${r.ticker}`}
              data-pnl={r.pnl_percent >= 0 ? 'profit' : 'loss'}
              style={{ left: `${r.x}%`, top: `${r.y}%`, width: `${r.w}%`, height: `${r.h}%`, background: pnlColor(r.pnl_percent) }}
              className="absolute flex flex-col items-center justify-center overflow-hidden border border-bg"
            >
              <span className="font-mono text-sm font-bold text-ink">{r.ticker}</span>
              <span className="font-mono text-[11px] text-ink/80">{fmtPct(r.pnl_percent)}</span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
