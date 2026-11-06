import { fmtSigned, fmtUsd, pnlClass } from '@/lib/format';
import type { ConnectionStatus, Portfolio } from '@/lib/types';
import { ConnectionDot } from './ConnectionDot';

export function Header({ portfolio, status, chatOpen, onToggleChat }: {
  portfolio: Portfolio; status: ConnectionStatus; chatOpen: boolean; onToggleChat: () => void;
}) {
  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-line bg-panel px-4">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-lg font-bold text-accent">FinAlly</span>
        <span className="hidden text-xs text-dim sm:inline">AI trading workstation</span>
      </div>
      <div className="flex items-center gap-6 font-mono text-sm">
        <div className="text-right">
          <div className="text-[10px] text-dim">Portfolio value</div>
          <div data-testid="total-value" className="font-semibold text-ink">{fmtUsd(portfolio.total_value)}</div>
        </div>
        <div className="hidden text-right sm:block">
          <div className="text-[10px] text-dim">Unrealized P&amp;L</div>
          <div data-testid="total-pnl" className={pnlClass(portfolio.unrealized_pnl)}>{fmtSigned(portfolio.unrealized_pnl)}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-dim">Cash</div>
          <div data-testid="cash-balance" className="text-blue">{fmtUsd(portfolio.cash_balance)}</div>
        </div>
        <ConnectionDot status={status} />
        <button
          data-testid="chat-toggle"
          onClick={onToggleChat}
          className="border border-line px-2 py-1 text-xs text-ink hover:border-blue"
          aria-expanded={chatOpen}
        >
          {chatOpen ? 'Hide assistant' : 'Show assistant'}
        </button>
      </div>
    </header>
  );
}
