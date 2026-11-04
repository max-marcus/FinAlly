# Massive API Reference (formerly Polygon.io)

How FinAlly uses the Massive REST API to fetch **real-time (snapshot)** and **end-of-day (EOD)** stock prices for **multiple tickers**.

Sources: Massive OpenAPI spec (`https://api.massive.com/openapi`), the official `massive-com/client-python` repo, and the Massive pricing page. Field names below were checked against the OpenAPI spec and the Python client models. Plan/entitlement details come from third-party summaries of the pricing page; **confirm at https://massive.com/pricing** before relying on them.

## 1. Basics

| Item | Value |
|---|---|
| Base URL | `https://api.massive.com` (legacy `https://api.polygon.io` still works) |
| Python package | `massive` (`uv add massive`) — `from massive import RESTClient` |
| Auth | API key; client sends it for you. Raw HTTP: `?apiKey=KEY` query param or `Authorization: Bearer KEY` |
| Env var | `MASSIVE_API_KEY` (the client reads it if `api_key=` is omitted) |
| Timestamps | Aggregates: Unix **milliseconds**. Snapshot `lastTrade.t` / `lastQuote.t`: SIP Unix **nanoseconds**. `updated`: nanoseconds as well — always check units before dividing |
| Client | **Synchronous** (urllib3). In asyncio code wrap calls in `asyncio.to_thread` |

### Plans (individual, stocks) — verify on pricing page

| Plan | Price | Calls | Data |
|---|---|---|---|
| Basic | $0 | 5/min | End-of-day only, 2 yrs history |
| Starter | $29/mo | unlimited | 15-min delayed, snapshots, WebSockets |
| Developer | $79/mo | unlimited | 15-min delayed, + trades, 10 yrs |
| Advanced | $199/mo | unlimited | **Real-time**, quotes, 20+ yrs |

Practical consequence for FinAlly: a free key gives **EOD data only** (use the grouped-daily/previous-close endpoints); live-ish snapshot polling needs a paid plan. `lastTrade` is only returned if the plan includes trades, `lastQuote` only if it includes quotes — code must tolerate their absence.

Errors: `401` bad key, `403` endpoint not in plan, `429` rate limit, `5xx` server (client retries 3×).

## 2. Real-time prices: Snapshot for many tickers (one call)

`GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,TSLA`

- `tickers` is a **case-sensitive**, comma-separated list. Omit it for the whole market (~10k tickers — avoid).
- `include_otc=false` by default.
- Snapshot data is cleared overnight (~3:30–4am ET) and repopulates as exchanges report; pre-market values can be empty.

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient()  # reads MASSIVE_API_KEY
snaps = client.get_snapshot_all(
    SnapshotMarketType.STOCKS,
    tickers=["AAPL", "GOOGL", "MSFT"],
)
for s in snaps:                       # list[TickerSnapshot]
    price = s.last_trade.price if s.last_trade else s.day.close
    print(s.ticker, price, s.todays_change_percent, s.prev_day.close)
```

Response (per ticker, raw JSON keys):

```json
{
  "ticker": "AAPL",
  "day":      {"o": 129.61, "h": 130.15, "l": 125.07, "c": 125.07, "v": 111237700, "vw": 127.35},
  "min":      {"o": 125.1, "h": 125.2, "l": 125.0, "c": 125.07, "v": 5200, "av": 111237700, "t": 1675190340000},
  "prevDay":  {"o": 128.0, "h": 130.0, "l": 127.5, "c": 129.61, "v": 98000000, "vw": 128.9},
  "lastTrade":{"p": 125.07, "s": 100, "x": 4, "t": 1675190399000000000},
  "lastQuote":{"p": 125.06, "s": 5, "P": 125.08, "S": 10, "t": 1675190399500000000},
  "todaysChange": -4.54,
  "todaysChangePerc": -3.50,
  "updated": 1675190399000000000
}
```

Python model attribute names (snake_case): `ticker`, `day`, `min`, `prev_day`, `last_trade` (`.price`, `.size`, `.timestamp`), `last_quote` (`.bid_price`/`.ask_price` style names — in the raw JSON `p`/`P`), `todays_change`, `todays_change_percent`, `updated`.

**Fields FinAlly uses:** current price = `last_trade.price` (fallback `min.close`, then `day.close`); previous close = `prev_day.close`; day change % = `todays_change_percent`; time = `last_trade.timestamp` (**nanoseconds**).

Single-ticker variant: `client.get_snapshot_ticker(SnapshotMarketType.STOCKS, "AAPL")`.

## 3. End-of-day prices

### 3a. Grouped daily — every ticker's OHLCV for one date (1 call)

`GET /v2/aggs/grouped/locale/us/market/stocks/{date}?adjusted=true`

Best way to get EOD closes for many tickers: one call, then filter locally.

```python
bars = client.get_grouped_daily_aggs("2026-10-30", adjusted=True)   # list[GroupedDailyAgg]
wanted = {"AAPL", "GOOGL", "MSFT"}
closes = {b.ticker: b.close for b in bars if b.ticker in wanted}
```

Raw result row: `{"T":"AAPL","o":..,"h":..,"l":..,"c":..,"v":..,"vw":..,"n":..,"t":<ms end of window>}`. Returns an empty `results` on weekends/holidays — walk back to the previous weekday until non-empty. Data for the current day typically is not final until after the close.

### 3b. Previous close — one ticker

`GET /v2/aggs/ticker/{ticker}/prev`

```python
prev = client.get_previous_close_agg("AAPL")   # list[PreviousCloseAgg], 1 item
print(prev[0].close)
```

Result row: `{"o","h","l","c","v","vw","n","t"}` (no `T` field; ticker is at top level).

### 3c. Aggregate bars — one ticker over a range (history / charts)

`GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}` — `timespan` ∈ second|minute|hour|day|week|month|quarter|year; `limit` ≤ 50000 (default 5000); `sort=asc|desc`; paginated via `next_url` (the client's `list_aggs` follows pages automatically).

```python
bars = list(client.list_aggs("AAPL", 1, "day", "2026-09-01", "2026-10-30", limit=50000))
# Agg: .open .high .low .close .volume .vwap .timestamp(ms) .transactions
```

### 3d. Daily open/close — one ticker, one date

`GET /v1/open-close/{ticker}/{date}` → `client.get_daily_open_close_agg("AAPL", "2026-10-30")` returns `open, high, low, close, volume, pre_market, after_hours`.

### Which endpoint when

| Need | Endpoint | Calls for N tickers |
|---|---|---|
| Live price + day change | Snapshot (`tickers=`) | 1 |
| EOD close for N tickers, one date | Grouped daily | 1 |
| Prior close for seeding / day-change baseline | Snapshot `prevDay.c` (paid) or `/prev` | 1 or N |
| Price history for one ticker | Aggregates | 1 (+pages) |

On the free tier (5 calls/min) prefer grouped daily (1 call regardless of N); `/prev` per ticker burns the budget for watchlists >5.

## 4. Polling design

- Paid: poll the snapshot every 2–15 s. Free: no snapshot; refresh EOD (grouped daily) once at startup and again each evening — and fall back to the simulator for intraday motion, or show static EOD prices.
- Always one request for the union of watched tickers, never one per ticker.
- Catch all exceptions in the poll loop; log and retry next interval. Never let a bad key or 429 kill the task.
- Unknown tickers are silently absent from the response — compare requested vs. returned and log the difference.

## 5. Known issues in the current `massive_client.py` (to fix)

1. It divides `last_trade.timestamp` by `1000` as if milliseconds; snapshot trade timestamps are **nanoseconds** (use `/ 1e9`). Guard: if value > 1e17 treat as ns, > 1e11 as ms.
2. It assumes `snap.last_trade` always exists; it is `None` on plans without trades and pre-market. Use the fallback chain in §2.
3. An older draft referenced `day.previous_close`; that field does not exist — use `prev_day.close`.
4. `PriceCache` computes `previous_price` from the previous *tick*, so "daily change %" in the watchlist is really tick change. The EOD/`prev_day.close` value should be stored separately (see MARKET_INTERFACE.md §4).
