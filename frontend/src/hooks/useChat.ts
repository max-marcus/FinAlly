'use client';
import { useCallback, useRef, useState } from 'react';
import { api, type Api } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';

export function useChat(onActions?: () => void, client: Api = api) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const seq = useRef(0);
  const nextId = () => `m${++seq.current}`;

  const send = useCallback(
    async (text: string) => {
      const content = text.trim();
      if (!content) return;
      setMessages((m) => [...m, { id: nextId(), role: 'user', content }]);
      setLoading(true);
      try {
        const r = await client.chat(content);
        setMessages((m) => [...m, { id: nextId(), role: 'assistant', content: r.content, actions: r.actions }]);
        if (r.actions && (r.actions.trades.length || r.actions.watchlist_changes.length)) onActions?.();
      } catch (e) {
        setMessages((m) => [
          ...m,
          { id: nextId(), role: 'assistant', content: `Could not reach the assistant: ${e instanceof Error ? e.message : 'unknown error'}` },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [client, onActions],
  );

  return { messages, loading, send };
}
