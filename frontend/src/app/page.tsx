'use client';
import { useEffect, useState } from 'react';
import { ChatPanel } from '@/components/ChatPanel';
import { Header } from '@/components/Header';
import { Heatmap } from '@/components/Heatmap';
import { MainChart } from '@/components/MainChart';
import { PnlChart } from '@/components/PnlChart';
import { PositionsTable } from '@/components/PositionsTable';
import { TradeBar } from '@/components/TradeBar';
import { Watchlist } from '@/components/Watchlist';
import { useChat } from '@/hooks/useChat';
import { usePriceStream } from '@/hooks/usePriceStream';
import { useTerminalData } from '@/hooks/useTerminalData';

export default function Page() {
  const { prices, history, status } = usePriceStream();
  const data = useTerminalData(prices);
  const chat = useChat(data.refreshAll);
  const [selected, setSelected] = useState('');
  const [chatOpen, setChatOpen] = useState(true);

  useEffect(() => {
    if (!selected && data.watchlist.length) setSelected(data.watchlist[0].ticker);
  }, [selected, data.watchlist]);

  return (
    <div className="flex h-screen min-h-[640px] flex-col">
      <Header portfolio={data.portfolio} status={status} chatOpen={chatOpen} onToggleChat={() => setChatOpen((o) => !o)} />
      <main className="flex min-h-0 flex-1 gap-1 p-1">
        <div className="w-[340px] shrink-0">
          <Watchlist items={data.watchlist} prices={prices} history={history} selected={selected}
            onSelect={setSelected} onAdd={data.addTicker} onRemove={data.removeTicker} />
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="min-h-0 flex-[3]"><MainChart ticker={selected} values={history[selected] ?? []} prices={prices} /></div>
          <div className="grid min-h-0 flex-[2] grid-cols-2 gap-1">
            <Heatmap positions={data.portfolio.positions} />
            <PnlChart snapshots={data.history} />
          </div>
          <div className="min-h-0 flex-[2]"><PositionsTable positions={data.portfolio.positions} /></div>
          <TradeBar selected={selected} onTrade={data.trade} />
        </div>
        {chatOpen && (
          <div className="w-[340px] shrink-0">
            <ChatPanel messages={chat.messages} loading={chat.loading} onSend={chat.send} />
          </div>
        )}
      </main>
    </div>
  );
}
