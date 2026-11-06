export type Direction = 'up' | 'down' | 'flat';

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

export type PriceMap = Record<string, PriceUpdate>;
export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  unrealized_pnl: number;
  positions: Position[];
}

export interface Snapshot {
  total_value: number;
  recorded_at: string;
}

export interface WatchlistItem {
  ticker: string;
  price: number | null;
}

export type TradeSide = 'buy' | 'sell';

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: TradeSide;
}

export interface ChatTradeAction {
  ticker: string;
  side: TradeSide;
  quantity: number;
  price?: number;
  status?: string;
  error?: string | null;
}

export interface ChatWatchlistAction {
  ticker: string;
  action: 'add' | 'remove';
  status?: string;
  error?: string | null;
}

export interface ChatActions {
  trades: ChatTradeAction[];
  watchlist_changes: ChatWatchlistAction[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  actions?: ChatActions | null;
}
