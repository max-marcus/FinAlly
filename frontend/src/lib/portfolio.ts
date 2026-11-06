import type { Portfolio, Position, PriceMap } from './types';

/** Recompute position valuation using live prices; falls back to server-supplied price. */
export function revaluePosition(p: Position, prices: PriceMap): Position {
  const live = prices[p.ticker]?.price ?? p.current_price;
  const cost = p.avg_cost * p.quantity;
  const pnl = live * p.quantity - cost;
  return {
    ...p,
    current_price: live,
    unrealized_pnl: pnl,
    pnl_percent: cost > 0 ? (pnl / cost) * 100 : 0,
  };
}

export function revaluePortfolio(pf: Portfolio, prices: PriceMap): Portfolio {
  const positions = pf.positions.map((p) => revaluePosition(p, prices));
  const marketValue = positions.reduce((s, p) => s + p.current_price * p.quantity, 0);
  return {
    ...pf,
    positions,
    total_value: pf.cash_balance + marketValue,
    unrealized_pnl: positions.reduce((s, p) => s + p.unrealized_pnl, 0),
  };
}

export interface TreemapRect {
  ticker: string;
  x: number;
  y: number;
  w: number;
  h: number;
  pnl_percent: number;
  weight: number;
}

/** Slice-and-dice treemap: alternate split direction, largest first. */
export function layoutTreemap(positions: Position[], width: number, height: number): TreemapRect[] {
  const items = positions
    .map((p) => ({ p, value: p.current_price * p.quantity }))
    .filter((i) => i.value > 0)
    .sort((a, b) => b.value - a.value);
  const total = items.reduce((s, i) => s + i.value, 0);
  const out: TreemapRect[] = [];

  const place = (list: typeof items, x: number, y: number, w: number, h: number) => {
    if (list.length === 0) return;
    if (list.length === 1) {
      const { p, value } = list[0];
      out.push({ ticker: p.ticker, x, y, w, h, pnl_percent: p.pnl_percent, weight: value / total });
      return;
    }
    const sum = list.reduce((s, i) => s + i.value, 0);
    // Split into two groups of roughly equal value.
    let acc = 0;
    let k = 0;
    while (k < list.length - 1 && acc + list[k].value <= sum / 2) acc += list[k++].value;
    if (k === 0) acc = list[k++].value;
    const a = list.slice(0, k);
    const b = list.slice(k);
    const ratio = acc / sum;
    if (w >= h) {
      place(a, x, y, w * ratio, h);
      place(b, x + w * ratio, y, w * (1 - ratio), h);
    } else {
      place(a, x, y, w, h * ratio);
      place(b, x, y + h * ratio, w, h * (1 - ratio));
    }
  };
  place(items, 0, 0, width, height);
  return out;
}
