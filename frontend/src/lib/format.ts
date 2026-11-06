const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' });

export const fmtUsd = (n: number): string => usd.format(n);
export const fmtNum = (n: number, digits = 2): string =>
  n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const fmtQty = (n: number): string =>
  n.toLocaleString('en-US', { maximumFractionDigits: 4 });
export const fmtSigned = (n: number): string => `${n >= 0 ? '+' : '-'}${fmtUsd(Math.abs(n))}`;
export const fmtPct = (n: number): string => `${n >= 0 ? '+' : '-'}${Math.abs(n).toFixed(2)}%`;
export const pnlClass = (n: number): string => (n > 0 ? 'text-up' : n < 0 ? 'text-down' : 'text-dim');
