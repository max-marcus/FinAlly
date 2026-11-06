import { fmtNum, fmtPct, fmtQty, fmtSigned, pnlClass } from '@/lib/format';
import type { Position } from '@/lib/types';
import { Panel } from './Panel';

export function PositionsTable({ positions }: { positions: Position[] }) {
  return (
    <Panel title="Positions" testId="positions" className="h-full">
      <div className="h-full overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-panel text-dim">
            <tr>
              {['Ticker', 'Qty', 'Avg cost', 'Price', 'Unrealized P&L', 'Chg %'].map((h, i) => (
                <th key={h} className={`px-3 py-1 font-normal ${i === 0 ? 'text-left' : 'text-right'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="font-mono">
            {positions.map((p) => (
              <tr key={p.ticker} data-testid={`position-row-${p.ticker}`} className="border-t border-line/60">
                <td className="px-3 py-1 font-semibold text-blue">{p.ticker}</td>
                <td data-testid={`position-qty-${p.ticker}`} className="px-3 text-right">{fmtQty(p.quantity)}</td>
                <td className="px-3 text-right">{fmtNum(p.avg_cost)}</td>
                <td className="px-3 text-right">{fmtNum(p.current_price)}</td>
                <td className={`px-3 text-right ${pnlClass(p.unrealized_pnl)}`}>{fmtSigned(p.unrealized_pnl)}</td>
                <td className={`px-3 text-right ${pnlClass(p.pnl_percent)}`}>{fmtPct(p.pnl_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {positions.length === 0 && <div data-testid="positions-empty" className="p-3 text-sm text-dim">No open positions.</div>}
      </div>
    </Panel>
  );
}
