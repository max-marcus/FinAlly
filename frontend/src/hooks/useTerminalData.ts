'use client';
import { useCallback, useMemo } from 'react';
import { api, type Api } from '@/lib/api';
import { revaluePortfolio } from '@/lib/portfolio';
import type { Portfolio, PriceMap, Snapshot, WatchlistItem } from '@/lib/types';
import { useAsyncData } from './useAsyncData';

const EMPTY_PF: Portfolio = { cash_balance: 10000, total_value: 10000, unrealized_pnl: 0, positions: [] };

/** Holds portfolio, watchlist and history; exposes mutations that refresh dependent data. */
export function useTerminalData(prices: PriceMap, client: Api = api) {
  const pf = useAsyncData(() => client.getPortfolio(), EMPTY_PF, 10000);
  const wl = useAsyncData<WatchlistItem[]>(() => client.getWatchlist(), [], 15000);
  const hist = useAsyncData<Snapshot[]>(() => client.getHistory(), [], 15000);

  const portfolio = useMemo(() => revaluePortfolio(pf.data, prices), [pf.data, prices]);

  const refreshAll = useCallback(async () => {
    await Promise.all([pf.refresh(), wl.refresh(), hist.refresh()]);
  }, [pf.refresh, wl.refresh, hist.refresh]);

  const addTicker = useCallback(
    async (t: string) => {
      await client.addTicker(t.trim().toUpperCase());
      await wl.refresh();
    },
    [client, wl.refresh],
  );
  const removeTicker = useCallback(
    async (t: string) => {
      await client.removeTicker(t);
      await wl.refresh();
    },
    [client, wl.refresh],
  );
  const trade = useCallback(
    async (ticker: string, quantity: number, side: 'buy' | 'sell') => {
      await client.trade({ ticker: ticker.trim().toUpperCase(), quantity, side });
      await Promise.all([pf.refresh(), hist.refresh()]);
    },
    [client, pf.refresh, hist.refresh],
  );

  return {
    portfolio,
    watchlist: wl.data,
    history: hist.data,
    addTicker,
    removeTicker,
    trade,
    refreshAll,
  };
}
