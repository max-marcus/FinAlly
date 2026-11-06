'use client';
import { useMemo } from 'react';
import type { Snapshot } from '@/lib/types';
import { LineChart } from './LineChart';
import { Panel } from './Panel';

export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const points = useMemo(
    () => snapshots.map((s) => ({ time: new Date(s.recorded_at).getTime() / 1000, value: s.total_value })).filter((p) => Number.isFinite(p.time)),
    [snapshots],
  );
  return (
    <Panel title="Portfolio value over time" testId="pnl-chart" className="h-full">
      {points.length === 0 ? (
        <div className="p-4 text-sm text-dim">Snapshots appear here every 30 seconds and after each trade.</div>
      ) : (
        <LineChart points={points} color="#ecad0a" testId="pnl-chart-canvas" />
      )}
    </Panel>
  );
}
