# FinAlly API Contract

All endpoints are same-origin under `/api`. JSON in/out. Errors: HTTP 4xx with `{"detail": "<human readable message>"}`.
Tickers are upper-cased by the server. Timestamps are ISO-8601 UTC strings.

## GET /api/health
`200 {"status": "ok"}`

## GET /api/stream/prices  (SSE, owned by app/market)
Each event: `data: {"AAPL": {"ticker","price","previous_price","timestamp","change","change_percent","direction"}, ...}`

## GET /api/portfolio
```json
{
  "cash_balance": 10000.0,
  "positions_value": 1900.0,
  "total_value": 11900.0,
  "unrealized_pnl": 50.0,
  "unrealized_pnl_percent": 2.7,
  "positions": [
    {"ticker": "AAPL", "quantity": 10.0, "avg_cost": 185.0, "current_price": 190.0,
     "market_value": 1900.0, "unrealized_pnl": 50.0, "unrealized_pnl_percent": 2.7}
  ]
}
```
`unrealized_pnl` is total across positions. If no live price is cached for a ticker, `avg_cost` is used as current price.

## POST /api/portfolio/trade
Request: `{"ticker": "AAPL", "quantity": 10, "side": "buy" | "sell"}` (quantity > 0, fractional OK).
Success `200`:
```json
{"trade": {"id","ticker","side","quantity","price","executed_at"},
 "cash_balance": 8100.0, "total_value": 10000.0}
```
Errors `400`: insufficient cash, insufficient shares, no price available for ticker, invalid side/quantity (pydantic validation errors are `422`).

## GET /api/portfolio/history
`200 {"snapshots": [{"total_value": 10000.0, "recorded_at": "..."}]}` ordered oldest first. A snapshot is recorded every 30s and after every trade.

## GET /api/watchlist
`200 {"watchlist": [{"ticker","price","previous_price","change","change_percent","direction"}]}` (price fields are `null` until a price is available).

## POST /api/watchlist
Request `{"ticker": "PYPL"}`. `200 {"ticker": "PYPL", "added": true}` (`added: false` if already present). `400` for invalid ticker (must match `^[A-Z][A-Z0-9.\-]{0,9}$`).

## DELETE /api/watchlist/{ticker}
`200 {"ticker": "PYPL", "removed": true}`; `404` if not on the watchlist.

## POST /api/chat
Request `{"message": "buy 10 AAPL"}`.
Response `200` (verified against real mock-mode output):
```json
{"message": "Buying 1 AAPL at market.",
 "trades": [{"ticker":"AAPL","side":"buy","quantity":1.0,"price":190.0,"status":"executed","error":null}],
 "watchlist_changes": [{"ticker":"PYPL","action":"add","status":"executed","error":null}]}
```
`status` is "executed" or "failed" (then `error` holds the reason, `price` may be null). No `actions`/`errors` fields.
Trade response of POST /api/portfolio/trade also includes a top-level `price`.

## Service interface used by chat (Python protocol, `app/services/protocols.py`)
```python
class TradingService(Protocol):
    def execute_trade(self, ticker: str, side: str, quantity: float) -> TradeResult   # raises TradeError(message)
    def get_portfolio(self) -> dict                                                     # same shape as GET /api/portfolio
    def get_watchlist(self) -> list[dict]                                               # same shape as GET /api/watchlist items
    async def add_watchlist(self, ticker: str) -> bool
    async def remove_watchlist(self, ticker: str) -> bool

class ChatService(Protocol):                       # implemented by llm-engineer
    async def handle_message(self, message: str) -> dict   # returns the POST /api/chat response shape
```
`execute_trade` is synchronous (SQLite); `TradeError` and `TradeResult` live in `app/services/errors.py` / `app/services/portfolio.py`.
