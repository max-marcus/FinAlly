'use client';
import { useEffect, useRef, useState } from 'react';
import type { ChatActions, ChatMessage } from '@/lib/types';
import { Panel } from './Panel';

export function ActionList({ actions }: { actions?: ChatActions | null }) {
  if (!actions) return null;
  const { trades, watchlist_changes } = actions;
  if (!trades.length && !watchlist_changes.length) return null;
  return (
    <ul data-testid="chat-actions" className="mt-2 space-y-1">
      {trades.map((t, i) => {
        const failed = !!t.error || t.status === 'failed' || t.status === 'error';
        return (
          <li key={`t${i}`} data-testid="chat-trade-action"
            className={`border-l-2 px-2 py-1 font-mono text-[11px] ${failed ? 'border-down text-down' : 'border-up text-up'}`}>
            {failed ? `Trade failed: ${t.side} ${t.quantity} ${t.ticker}${t.error ? ` (${t.error})` : ''}`
              : `${t.side === 'buy' ? 'Bought' : 'Sold'} ${t.quantity} ${t.ticker}${t.price ? ` @ ${t.price.toFixed(2)}` : ''}`}
          </li>
        );
      })}
      {watchlist_changes.map((w, i) => {
        const failed = !!w.error || w.status === 'failed' || w.status === 'error';
        return (
          <li key={`w${i}`} data-testid="chat-watchlist-action"
            className={`border-l-2 px-2 py-1 font-mono text-[11px] ${failed ? 'border-down text-down' : 'border-blue text-blue'}`}>
            {failed ? `Watchlist change failed: ${w.action} ${w.ticker}${w.error ? ` (${w.error})` : ''}`
              : `${w.action === 'add' ? 'Added' : 'Removed'} ${w.ticker} ${w.action === 'add' ? 'to' : 'from'} watchlist`}
          </li>
        );
      })}
    </ul>
  );
}

export function ChatMessageView({ m }: { m: ChatMessage }) {
  const user = m.role === 'user';
  return (
    <div data-testid="chat-message" data-role={m.role} className={`flex flex-col ${user ? 'items-end' : 'items-start'}`}>
      <div className={`max-w-[92%] whitespace-pre-wrap px-3 py-2 text-xs leading-relaxed ${user ? 'bg-blue/20 text-ink' : 'border border-line bg-raised text-ink'}`}>
        {m.content}
        <ActionList actions={m.actions} />
      </div>
    </div>
  );
}

export function ChatPanel({ messages, loading, onSend }: {
  messages: ChatMessage[]; loading: boolean; onSend: (t: string) => Promise<void> | void;
}) {
  const [text, setText] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView?.({ block: 'end' }); }, [messages, loading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || loading) return;
    void onSend(text);
    setText('');
  };

  return (
    <Panel title="AI assistant" testId="chat-panel" className="h-full">
      <div className="flex h-full flex-col">
        <div data-testid="chat-messages" className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
          {messages.length === 0 && (
            <p className="text-xs text-dim">Ask about your portfolio, or tell me to trade. Try: &ldquo;Buy 5 shares of AAPL&rdquo;.</p>
          )}
          {messages.map((m) => <ChatMessageView key={m.id} m={m} />)}
          {loading && (
            <div data-testid="chat-loading" role="status" className="flex items-center gap-1 text-xs text-dim">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent [animation-delay:300ms]" />
              <span className="ml-1">Thinking</span>
            </div>
          )}
          <div ref={end} />
        </div>
        <form onSubmit={submit} className="flex gap-1 border-t border-line p-2">
          <input data-testid="chat-input" aria-label="Message" value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Message FinAlly"
            className="min-w-0 flex-1 border border-line bg-bg px-2 py-1.5 text-xs text-ink outline-none focus:border-blue" />
          <button data-testid="chat-send" type="submit" disabled={loading}
            className="bg-purple px-3 text-xs font-semibold text-white hover:brightness-125 disabled:opacity-50">Send</button>
        </form>
      </div>
    </Panel>
  );
}
