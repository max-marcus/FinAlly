'use client';
import { ColorType, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

export interface ChartPoint { time: number; value: number }

/** Thin canvas chart wrapper: render-only, data is supplied by the parent. */
export function LineChart({ points, color, testId }: { points: ChartPoint[]; color: string; testId?: string }) {
  const el = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!el.current) return;
    const c = createChart(el.current, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#7c8a9c', fontSize: 11 },
      grid: { vertLines: { color: '#1a2332' }, horzLines: { color: '#1a2332' } },
      rightPriceScale: { borderColor: '#252f3d' },
      timeScale: { borderColor: '#252f3d', timeVisible: true, secondsVisible: true },
      crosshair: { mode: 1 },
    });
    chart.current = c;
    series.current = c.addLineSeries({ color, lineWidth: 2, priceLineVisible: false });
    return () => { c.remove(); chart.current = null; series.current = null; };
  }, [color]);

  useEffect(() => {
    if (!series.current) return;
    const clean: { time: UTCTimestamp; value: number }[] = [];
    for (const p of points) {
      const t = Math.floor(p.time) as UTCTimestamp;
      if (clean.length && t <= clean[clean.length - 1].time) continue;
      clean.push({ time: t, value: p.value });
    }
    series.current.setData(clean);
    chart.current?.timeScale().fitContent();
  }, [points, color]);

  return <div ref={el} data-testid={testId} data-points={points.length} className="h-full w-full" />;
}
