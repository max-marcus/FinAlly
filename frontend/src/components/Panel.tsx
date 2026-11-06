import type { ReactNode } from 'react';

export function Panel({ title, right, children, className = '', testId }: {
  title: string; right?: ReactNode; children: ReactNode; className?: string; testId?: string;
}) {
  return (
    <section data-testid={testId} className={`flex min-h-0 flex-col border border-line bg-panel ${className}`}>
      <header className="flex h-7 shrink-0 items-center justify-between border-b border-line px-3">
        <h2 className="text-[11px] font-semibold tracking-wide text-accent">{title}</h2>
        {right}
      </header>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
