import type { ConnectionStatus } from '@/lib/types';

const COLORS: Record<ConnectionStatus, string> = {
  connected: 'bg-up',
  reconnecting: 'bg-accent',
  disconnected: 'bg-down',
};

export function ConnectionDot({ status }: { status: ConnectionStatus }) {
  return (
    <span className="flex items-center gap-2 text-xs text-dim" title={`Price stream ${status}`}>
      <span data-testid="connection-dot" data-status={status} className={`h-2.5 w-2.5 rounded-full ${COLORS[status]}`} />
      <span data-testid="connection-label">{status}</span>
    </span>
  );
}
