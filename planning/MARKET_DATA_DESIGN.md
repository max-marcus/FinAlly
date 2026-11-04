# Market Data Backend — Design

Implementation-level design for FinAlly's market data subsystem: the unified interface, shared price cache, GBM simulator, Massive (Polygon.io) client, SSE stream, and how they plug into the rest of the FastAPI backend.

Everything lives in `backend/app/market/`. This document is consistent with the code already in that directory (see `MARKET_DATA_SUMMARY.md`) and calls out, in **"Delta"** blocks, the small additions needed to fully satisfy `PLAN.md` (notably *daily change %* in the watchlist, which the current per-tick `change` does not provide). It supersedes `archive/MARKET_DATA_DESIGN.md`.

## Contents

1. [Architecture](#1-architecture)
2. [Files](#2-files)
3. [Data model — `PriceUpdate`](#3-data-model)
4. [Price cache](#4-price-cache)
5. [Unified interface](#5-unified-interface)
6. [Factory](#6-factory)
7. [Simulator](#7-simulator)
8. [Massive client](#8-massive-client)
9. [SSE endpoint](#9-sse-endpoint)
10. [App integration](#10-app-integration)
11. [Watchlist ↔ market data coordination](#11-watchlist--market-data-coordination)
12. [Error handling & edge cases](#12-error-handling--edge-cases)
13. [Testing](#13-testing)
14. [Configuration reference](#14-configuration-reference)

---

## 1. Architecture

```
                    ┌──────────────────────────┐
 MASSIVE_API_KEY ──▶│ create_market_data_source│
                    └────────────┬─────────────┘
                                 │ returns one of
              ┌──────────────────┴───────────────────┐
              ▼                                      ▼
   SimulatorDataSource (default)            MassiveDataSource
   GBM + Cholesky, tick every 0.5s          REST snapshot poll every 15s
              │      implement MarketDataSource      │
              └──────────────────┬───────────────────┘
                                 │ cache.update(ticker, price, ts)
                                 ▼
                       PriceCache (thread-safe, in-memory)
                                 │ read-only
        ┌────────────────────────┼──────────────────────────┐
        ▼                        ▼                          ▼
  SSE /api/stream/prices   Trade execution          Portfolio valuation
  (every 0.5s, if changed) (fill at cache price)    (snapshots, heatmap)
```

Principles:

- **Push into a cache, never return prices.** Producers run on their own clock (0.5 s vs 15 s); consumers read the cache on theirs. No consumer knows which source is active.
- **One writer at a time**, many readers. The cache is the single source of truth for "current price".
- **Sources are resilient.** A failed tick/poll is logged and retried; the last known prices stay in the cache.
- **Source-specific dependencies stay behind the factory.** (`massive` is a core dependency in `pyproject.toml`, so imports are top-level; see §12.)

## 2. Files

```
backend/app/market/
├── __init__.py        # public API re-exports
├── models.py          # PriceUpdate (frozen dataclass)
├── cache.py           # PriceCache
├── interface.py       # MarketDataSource (ABC)
├── seed_prices.py     # SEED_PRICES, TICKER_PARAMS, DEFAULT_PARAMS, correlation constants
├── simulator.py       # GBMSimulator (math) + SimulatorDataSource (async wrapper)
├── massive_client.py  # MassiveDataSource
├── factory.py         # create_market_data_source()
└── stream.py          # create_stream_router() — SSE
```

Public API (`app/market/__init__.py`):

```python
from .cache import PriceCache
from .factory import create_market_data_source
from .interface import MarketDataSource
from .models import PriceUpdate
from .stream import create_stream_router

__all__ = ["PriceUpdate", "PriceCache", "MarketDataSource",
           "create_market_data_source", "create_stream_router"]
```

The rest of the backend imports **only** from `app.market`.

---

## 3. Data model

`models.py` — the only type that leaves this subsystem.

```python
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    ticker: str
    price: float
    previous_price: float          # price at the prior cache update (tick-to-tick)
    timestamp: float = field(default_factory=time.time)   # Unix seconds

    @property
    def change(self) -> float:
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:            # drives the green/red flash
        if self.price > self.previous_price:
            return "up"
        if self.price < self.previous_price:
            return "down"
        return "flat"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker, "price": self.price,
            "previous_price": self.previous_price, "timestamp": self.timestamp,
            "change": self.change, "change_percent": self.change_percent,
            "direction": self.direction,
        }
```

Derived fields are properties, so they can never disagree with `price`/`previous_price`. `frozen`+`slots` makes instances safe to share across tasks and cheap to create.

> **Delta — daily change %.** PLAN §10 asks the watchlist to show *daily* change %, but `change_percent` above is tick-to-tick (it flashes, it doesn't accumulate). Add a reference price (the day's baseline) alongside:
>
> ```python
> @dataclass(frozen=True, slots=True)
> class PriceUpdate:
>     ticker: str
>     price: float
>     previous_price: float
>     timestamp: float = field(default_factory=time.time)
>     day_open: float | None = None      # baseline for daily change; None → unknown
>
>     @property
>     def day_change_percent(self) -> float:
>         base = self.day_open
>         if not base:
>             return 0.0
>         return round((self.price - base) / base * 100, 4)
> ```
>
> and include `"day_open"` and `"day_change_percent"` in `to_dict()`. Semantics per source: **simulator** → `day_open` = seed price (the session start); **Massive** → `day.previous_close` from the snapshot (matches how a real terminal shows "change on the day"). Field is optional so existing tests and callers keep working.

## 4. Price cache

`cache.py`

```python
from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version = 0               # bumped on every update(); SSE change detection

    def update(self, ticker: str, price: float, timestamp: float | None = None) -> PriceUpdate:
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price      # first tick → "flat"
            update = PriceUpdate(ticker=ticker, price=round(price, 2),
                                 previous_price=round(previous_price, 2), timestamp=ts)
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None: ...
    def get_all(self) -> dict[str, PriceUpdate]: ...     # shallow-copy snapshot
    def get_price(self, ticker: str) -> float | None: ...
    def remove(self, ticker: str) -> None: ...

    @property
    def version(self) -> int:
        return self._version
    def __len__(self) -> int: ...
    def __contains__(self, ticker: str) -> bool: ...
```

(`get*`/`remove`/`__len__`/`__contains__` all take the lock; see the repo for the one-liners.)

Why `threading.Lock` and not `asyncio.Lock`: `MassiveDataSource` fetches in `asyncio.to_thread`, and the cache is touched from real OS threads as well as the event loop. The critical sections are single dict operations, so contention is negligible.

**Version counter.** The SSE loop compares `cache.version` with the last version it sent and skips serialization when nothing changed — important for Massive, which updates every 15 s while SSE wakes every 0.5 s. The unlocked read of an `int` is atomic under the GIL; if you ever target free-threaded Python, take the lock in the property.

> **Delta — day baseline in the cache.** To support `day_open`, extend `update()` with an optional `day_open: float | None = None` and remember it per ticker (set on first sight, or overwritten when the caller supplies one, e.g. Massive's `previous_close`):
>
> ```python
> def update(self, ticker, price, timestamp=None, day_open=None) -> PriceUpdate:
>     with self._lock:
>         prev = self._prices.get(ticker)
>         previous_price = prev.price if prev else price
>         baseline = day_open if day_open is not None else (prev.day_open if prev else price)
>         ...
>         update = PriceUpdate(ticker=ticker, price=round(price, 2),
>                              previous_price=round(previous_price, 2),
>                              timestamp=ts, day_open=round(baseline, 2))
> ```
>
> The simulator's first `update()` (the seeding call) therefore pins `day_open` to the seed price with no extra code.

## 5. Unified interface

`interface.py`

```python
from abc import ABC, abstractmethod


class MarketDataSource(ABC):
    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing updates into the cache. Call exactly once."""

    @abstractmethod
    async def stop(self) -> None:
        """Cancel background work. Idempotent."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Track a ticker. No-op if already tracked."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking and evict from the cache. No-op if absent."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Currently tracked tickers."""
```

Contract every implementation must honor (and the shared test-suite in §13 asserts):

| Rule | Why |
|---|---|
| After `start()` returns, the cache has an entry for every started ticker the source can price | SSE and trades work on the first request |
| `stop()` is idempotent and leaves no running task | clean lifespan shutdown, clean tests |
| `remove_ticker()` evicts the cache entry | no stale prices on the stream |
| Errors in the background loop never propagate | the feed must outlive any single bad tick |
| Tickers are case-insensitive; implementations normalize with `.upper().strip()` | `"aapl"` from the LLM or UI must not create a second entry |

> **Delta — normalization.** `MassiveDataSource` already normalizes; `SimulatorDataSource.add_ticker/remove_ticker` currently do not. Add `ticker = ticker.upper().strip()` at the top of both (and in `start()` for the list). Validation of *whether a symbol is real* belongs in the watchlist route (§11), not here.

## 6. Factory

`factory.py` — selects the source from the environment.

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if api_key:
        return MassiveDataSource(api_key=api_key, price_cache=price_cache)
    return SimulatorDataSource(price_cache=price_cache)
```

Returns an *unstarted* source. Whitespace-only keys count as unset. Optional tuning from env, if desired:

```python
poll = float(os.environ.get("MASSIVE_POLL_INTERVAL", "15"))   # paid tiers: 2–5
return MassiveDataSource(api_key=api_key, price_cache=price_cache, poll_interval=poll)
```

## 7. Simulator

### 7.1 Seed data — `seed_prices.py`

Constants only, no logic.

```python
SEED_PRICES = {"AAPL": 190.00, "GOOGL": 175.00, "MSFT": 420.00, "AMZN": 185.00,
               "TSLA": 250.00, "NVDA": 800.00, "META": 500.00, "JPM": 195.00,
               "V": 280.00, "NFLX": 600.00}

TICKER_PARAMS = {                       # sigma = annual volatility, mu = annual drift
    "AAPL": {"sigma": 0.22, "mu": 0.05}, "GOOGL": {"sigma": 0.25, "mu": 0.05},
    "MSFT": {"sigma": 0.20, "mu": 0.05}, "AMZN":  {"sigma": 0.28, "mu": 0.05},
    "TSLA": {"sigma": 0.50, "mu": 0.03}, "NVDA":  {"sigma": 0.40, "mu": 0.08},
    "META": {"sigma": 0.30, "mu": 0.05}, "JPM":   {"sigma": 0.18, "mu": 0.04},
    "V":    {"sigma": 0.17, "mu": 0.04}, "NFLX":  {"sigma": 0.35, "mu": 0.05},
}
DEFAULT_PARAMS = {"sigma": 0.25, "mu": 0.05}      # tickers added at runtime

CORRELATION_GROUPS = {
    "tech":    {"AAPL", "GOOGL", "MSFT", "AMZN", "META", "NVDA", "NFLX"},
    "finance": {"JPM", "V"},
}
INTRA_TECH_CORR, INTRA_FINANCE_CORR = 0.6, 0.5
CROSS_GROUP_CORR = 0.3          # cross-sector and unknown tickers
TSLA_CORR = 0.3                 # TSLA is a loner
```

Unknown tickers start at `random.uniform(50, 300)`.

### 7.2 The math — `GBMSimulator`

Per step, for each ticker:

```
S(t+dt) = S(t) · exp( (μ − σ²/2)·dt + σ·√dt·Z )
```

- `dt = 0.5 s / (252 days · 6.5 h · 3600 s) ≈ 8.48e-8` of a trading year → per-tick moves are fractions of a cent to a few cents, accumulating naturally. GBM is multiplicative, so prices are always positive.
- `Z` is **correlated**: draw `n` independent normals, multiply by the Cholesky factor `L` of the correlation matrix `C` (`C = L·Lᵀ`), giving `Z = L @ z_indep`.
- **Shock events**: each ticker each tick has `event_probability = 0.001` of an extra ±2–5 % jump. With 10 tickers at 2 ticks/s that is one visible jump roughly every 50 s.

```python
class GBMSimulator:
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR

    def __init__(self, tickers, dt=DEFAULT_DT, event_probability=0.001):
        self._dt, self._event_prob = dt, event_probability
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None
        for t in tickers:
            self._add_ticker_internal(t)       # no Cholesky rebuild per ticker
        self._rebuild_cholesky()               # one rebuild for the batch

    def step(self) -> dict[str, float]:
        n = len(self._tickers)
        if n == 0:
            return {}
        z = np.random.standard_normal(n)
        if self._cholesky is not None:
            z = self._cholesky @ z
        out = {}
        for i, t in enumerate(self._tickers):
            mu, sigma = self._params[t]["mu"], self._params[t]["sigma"]
            self._prices[t] *= math.exp((mu - 0.5 * sigma**2) * self._dt
                                        + sigma * math.sqrt(self._dt) * z[i])
            if random.random() < self._event_prob:
                self._prices[t] *= 1 + random.uniform(0.02, 0.05) * random.choice([-1, 1])
            out[t] = round(self._prices[t], 2)
        return out

    def add_ticker(self, ticker):     # no-op if present; rebuilds Cholesky
    def remove_ticker(self, ticker):  # no-op if absent; rebuilds Cholesky
    def get_price(self, ticker): ...
    def get_tickers(self): ...

    def _rebuild_cholesky(self):
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                corr[i, j] = corr[j, i] = self._pairwise_correlation(self._tickers[i], self._tickers[j])
        self._cholesky = np.linalg.cholesky(corr)

    @staticmethod
    def _pairwise_correlation(t1, t2) -> float:
        tech, fin = CORRELATION_GROUPS["tech"], CORRELATION_GROUPS["finance"]
        if "TSLA" in (t1, t2):           return TSLA_CORR
        if t1 in tech and t2 in tech:    return INTRA_TECH_CORR
        if t1 in fin and t2 in fin:      return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR
```

Why Cholesky doesn't fail here: every off-diagonal value is in `[0.3, 0.6]` with a unit diagonal. That is not a proof of positive-definiteness for every possible mix, but it was checked empirically for the 10 defaults plus 60 unknown tickers (70 total). If correlation constants are ever made user-configurable, wrap `np.linalg.cholesky` in `try/except LinAlgError` and fall back to the identity matrix.

### 7.3 Async wrapper — `SimulatorDataSource`

```python
class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache, update_interval=0.5, event_probability=0.001):
        self._cache, self._interval, self._event_prob = price_cache, update_interval, event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers):
        self._sim = GBMSimulator(tickers=tickers, event_probability=self._event_prob)
        for t in tickers:                                   # seed → data before the first tick
            self._cache.update(t, self._sim.get_price(t))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
        self._task = None

    async def add_ticker(self, ticker):
        if self._sim:
            self._sim.add_ticker(ticker)
            self._cache.update(ticker, self._sim.get_price(ticker))   # price immediately

    async def remove_ticker(self, ticker):
        if self._sim: self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    def get_tickers(self): return self._sim.get_tickers() if self._sim else []

    async def _run_loop(self):
        while True:
            try:
                for t, p in self._sim.step().items():
                    self._cache.update(t, p)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
```

`step()` for ≤ ~50 tickers takes microseconds; it runs directly on the event loop (no thread hop needed).

Example — what a few seconds of output looks like (illustrative):

```
t=0.0  AAPL 190.00  GOOGL 175.00  NVDA 800.00
t=0.5  AAPL 190.01  GOOGL 175.00  NVDA 799.97
t=1.0  AAPL 190.01  GOOGL 175.02  NVDA 800.11
t=1.5  AAPL 189.98  GOOGL 174.99  NVDA 800.04   ← tech names drift together (ρ=0.6)
```

---

## 8. Massive client

### 8.1 API facts used

| Item | Value |
|---|---|
| Package | `massive` (`from massive import RESTClient`) |
| Auth | API key via `RESTClient(api_key=...)` (sent as bearer token) |
| Endpoint | `GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=A,B,C` — **all watched tickers in one call** |
| Python | `client.get_snapshot_all(market_type=SnapshotMarketType.STOCKS, tickers=[...])` |
| Fields used | `last_trade.price`, `last_trade.timestamp` (Unix **ms**), `day.previous_close`, `day.change_percent` |
| Limits | Free: 5 req/min → poll every 15 s. Paid: poll 2–5 s |
| Errors | 401 bad key · 403 plan lacks endpoint · 429 rate limit · 5xx (client retries 3×) |

Sample parsed snapshot:

```json
{ "ticker": "AAPL",
  "day": {"previous_close": 129.61, "change_percent": -3.5, "...": "..."},
  "last_trade": {"price": 125.07, "timestamp": 1675190399000, "...": "..."} }
```

Because it is one request regardless of ticker count, the request rate depends only on `poll_interval` — adding tickers never threatens the free-tier limit.

### 8.2 Implementation — `massive_client.py`

The `RESTClient` is **synchronous**; every call goes through `asyncio.to_thread` so the event loop (and SSE) never blocks.

```python
class MassiveDataSource(MarketDataSource):
    def __init__(self, api_key, price_cache, poll_interval=15.0):
        self._api_key, self._cache, self._interval = api_key, price_cache, poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers):
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = [t.upper().strip() for t in tickers]
        await self._poll_once()                       # prime the cache before serving
        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
        self._task, self._client = None, None

    async def add_ticker(self, ticker):
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)              # priced on the next poll

    async def remove_ticker(self, ticker):
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)

    def get_tickers(self): return list(self._tickers)

    async def _poll_loop(self):
        while True:
            await asyncio.sleep(self._interval)       # first poll already done in start()
            await self._poll_once()

    async def _poll_once(self):
        if not self._tickers or not self._client:
            return
        try:
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            for snap in snapshots:
                try:
                    self._cache.update(
                        ticker=snap.ticker,
                        price=snap.last_trade.price,
                        timestamp=snap.last_trade.timestamp / 1000.0,   # ms → s
                        # Delta: day_open=snap.day.previous_close,
                    )
                except (AttributeError, TypeError) as e:
                    logger.warning("Skipping snapshot for %s: %s", getattr(snap, "ticker", "???"), e)
        except Exception as e:                        # 401/403/429/network
            logger.error("Massive poll failed: %s", e)

    def _fetch_snapshots(self) -> list:
        return self._client.get_snapshot_all(
            market_type=SnapshotMarketType.STOCKS, tickers=self._tickers)
```

The `_fetch_snapshots` split exists purely so tests can patch it (§13).

### 8.3 Behavior notes

- **Market closed / weekends**: `last_trade` is the last print; prices simply don't move. The SSE stream keeps working; the `version` counter still bumps on each poll, so the client gets a (unchanged) refresh every 15 s. This is expected, not a bug.
- **Stale timestamps**: the cache stores the *exchange* timestamp, not the poll time, so a UI can show "as of" honestly.
- **Unknown/delisted symbol**: Massive omits it from the response; it never enters the cache. See §11 for how the watchlist route reports this.
- **Newly added ticker** has no price until the next poll (≤ 15 s on the free tier). Trades on it are rejected with a clear message (§12.2). 

> **Delta — fast add + failure backoff** (optional polish, both small):
>
> ```python
> # in __init__:  self._wake = asyncio.Event()
> async def add_ticker(self, ticker):
>     ...
>     self._wake.set()                      # ask the loop to poll soon
>
> async def _poll_loop(self):
>     failures = 0
>     while True:
>         try:   # wait for interval OR an early wake, whichever first
>             await asyncio.wait_for(self._wake.wait(), timeout=self._interval * (2 ** min(failures, 3)))
>         except asyncio.TimeoutError:
>             pass
>         self._wake.clear()
>         failures = 0 if await self._poll_once() else failures + 1
> ```
>
> with `_poll_once` returning `True` on success. To stay inside the 5 req/min free tier, enforce a minimum spacing (e.g. skip an early-wake poll if the last poll was < 12 s ago). Exponential backoff (capped at 8× the interval) stops a revoked key or 429 storm from hammering the API.

---

## 9. SSE endpoint

`stream.py` — `GET /api/stream/prices`.

```python
def create_stream_router(price_cache: PriceCache) -> APIRouter:
    router = APIRouter(prefix="/api/stream", tags=["streaming"])   # per-call router

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                     "X-Accel-Buffering": "no"},
        )
    return router


async def _generate_events(price_cache, request, interval=0.5) -> AsyncGenerator[str, None]:
    yield "retry: 1000\n\n"                       # browser reconnect delay (ms)
    last_version = -1
    try:
        while True:
            if await request.is_disconnected():
                break
            if price_cache.version != last_version:
                last_version = price_cache.version
                prices = price_cache.get_all()
                if prices:
                    yield f"data: {json.dumps({t: u.to_dict() for t, u in prices.items()})}\n\n"
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass
```

Notes:

- The router is created **inside** the factory function (the current code uses a module-level `router`, which would double-register `/prices` if the factory were called twice — e.g. across tests). Moving it inside is the one-line fix.
- Each event is a **full snapshot** of every tracked ticker, keyed by symbol. Simple and self-healing: after any reconnect the client is immediately consistent, no replay/Last-Event-ID logic needed.
- Cadence is a fixed 0.5 s *poll* of the cache rather than reacting to writes, giving the frontend evenly spaced samples — which is what clean sparklines need.

Wire format:

```
retry: 1000

data: {"AAPL":{"ticker":"AAPL","price":190.5,"previous_price":190.42,"timestamp":1707580800.5,"change":0.08,"change_percent":0.042,"direction":"up"},"GOOGL":{...}}

```

Client:

```ts
const es = new EventSource('/api/stream/prices');
es.onopen    = () => setStatus('connected');          // green dot
es.onerror   = () => setStatus('reconnecting');       // yellow; EventSource retries by itself
es.onmessage = (e) => {
  const prices: Record<string, PriceTick> = JSON.parse(e.data);
  for (const t of Object.values(prices)) {
    appendToSparkline(t.ticker, t.price);             // sparklines accumulate client-side
    flash(t.ticker, t.direction);                     // CSS class, removed after ~500ms
  }
};
```

## 10. App integration

Create the objects once, start the source in `lifespan`, and **register routers at app-construction time** (not inside `lifespan` — routes added after startup begins are fragile and break `TestClient` ordering). Because the cache exists before startup, the router can be built immediately:

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from app.market import PriceCache, MarketDataSource, create_market_data_source, create_stream_router


def create_app() -> FastAPI:
    price_cache = PriceCache()
    source = create_market_data_source(price_cache)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.price_cache = price_cache
        app.state.market_source = source
        await source.start(await load_tracked_tickers())     # see §11
        # ... start portfolio-snapshot background task here ...
        try:
            yield
        finally:
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.include_router(create_stream_router(price_cache))
    # app.include_router(portfolio_router); watchlist_router; chat_router
    # app.mount("/", StaticFiles(directory="static", html=True))   # LAST — it matches everything
    return app

app = create_app()


# FastAPI dependencies for other routers
def get_price_cache(request: Request) -> PriceCache:    return request.app.state.price_cache
def get_market_source(request: Request) -> MarketDataSource: return request.app.state.market_source
```

How other modules consume it:

```python
@router.post("/portfolio/trade")
async def trade(req: TradeRequest, cache: PriceCache = Depends(get_price_cache)):
    price = cache.get_price(req.ticker.upper())
    if price is None:
        raise HTTPException(400, f"No price available yet for {req.ticker}; try again shortly.")
    ...  # fill at `price`; cash/position math in the portfolio module

# portfolio valuation: sum(pos.quantity * (cache.get_price(pos.ticker) or pos.avg_cost) ...)
# LLM context: {t: cache.get(t).to_dict() for t in watchlist}
```

Static mount must be registered last so `/api/*` and `/api/stream/*` win.

## 11. Watchlist ↔ market data coordination

**Tracked set = watchlist ∪ tickers with open positions.** A user who drops a ticker from the watchlist but still holds shares must keep getting prices, or portfolio value, the heatmap and the P&L chart go stale.

```python
async def load_tracked_tickers() -> list[str]:
    wl  = await db.watchlist_tickers()
    pos = await db.position_tickers(quantity_gt=0)
    return sorted(set(wl) | set(pos))
```

Add flow (`POST /api/watchlist`, also used by LLM `watchlist_changes`):

```python
@router.post("/watchlist")
async def add(payload: WatchlistAdd, source=Depends(get_market_source), cache=Depends(get_price_cache)):
    ticker = payload.ticker.upper().strip()
    if not re.fullmatch(r"[A-Z.]{1,5}", ticker):
        raise HTTPException(422, "Invalid ticker symbol")
    await db.insert_watchlist(ticker)           # UNIQUE(user_id, ticker) → idempotent
    await source.add_ticker(ticker)
    return {"ticker": ticker, "price": cache.get_price(ticker)}   # None for Massive until next poll
```

Remove flow:

```python
@router.delete("/watchlist/{ticker}")
async def remove(ticker: str, source=Depends(get_market_source)):
    ticker = ticker.upper()
    await db.delete_watchlist(ticker)
    pos = await db.get_position(ticker)
    if pos is None or pos.quantity == 0:        # keep pricing held positions
        await source.remove_ticker(ticker)
    return {"status": "ok"}
```

Mirror rule on trades: selling a position to zero when the ticker is no longer on the watchlist should call `source.remove_ticker()`; buying a ticker not on the watchlist (possible via the trade bar) must call `source.add_ticker()` first so a price exists.

**Simulator caveat for unknown symbols:** the simulator will happily "price" any string (random $50–300 seed). That is intended for the demo, but the route's format validation above keeps junk out. With Massive, a bogus symbol simply never gets a price — surface that as "no price available" rather than inserting it silently (optionally verify with one `get_snapshot_ticker` call before inserting).

## 12. Error handling & edge cases

### 12.1 Summary

| Situation | Behavior |
|---|---|
| Empty watchlist at startup | `start([])` is valid: simulator yields `{}`, Massive skips polling; SSE sends nothing until a ticker is added |
| Massive 401/403 | Logged each poll; last cache values retained; fix `.env`, restart |
| Massive 429 | Logged; next poll after interval (with backoff, if implemented) |
| Network timeout | Logged; retried next cycle |
| Malformed snapshot (`last_trade` missing) | That ticker skipped with a warning; others processed |
| Simulator step exception | Logged with traceback; loop continues |
| Client disconnects mid-stream | `is_disconnected()` ends the generator; no leak |
| `stop()` twice / before `start()` | No-op |

### 12.2 Trade on a ticker with no price

```python
price = cache.get_price(ticker)
if price is None:
    raise HTTPException(400, f"Price not yet available for {ticker}. Please try again shortly.")
```

The same error string is returned to the LLM in the chat flow so it can tell the user.

### 12.3 `massive` import

`massive` is declared a core dependency, so `massive_client.py` imports it at module top and `factory.py` imports both sources eagerly. That keeps tests patchable (`patch("app.market.massive_client.RESTClient")`). The cost is that the simulator-only path still needs the package installed — acceptable inside the Docker image, where `uv sync` installs everything. If a lighter install is ever wanted, move the import into `MassiveDataSource.start()` and have tests use `patch(..., create=True)`.

### 12.4 Concurrency & precision

- Writers: one background task (or one worker thread for Massive's fetch, with the cache write back on the loop). Readers: SSE per client + request handlers. All through `PriceCache`'s lock.
- Prices are rounded to cents at the cache boundary. Trade math should use the cache value, and portfolio code should round money to cents consistently (not this module's concern, but fills must use exactly the price the user saw).
- The simulator's internal prices stay unrounded (`step()` rounds only its output), so rounding error never accumulates in the random walk.

---

## 13. Testing

Layout: `backend/tests/market/` with `asyncio_mode = "auto"` (already set in `pyproject.toml`). Existing: `test_models`, `test_cache`, `test_simulator`, `test_simulator_source`, `test_factory`, `test_massive` (73 tests, 84 % coverage). Run with:

```bash
cd backend && uv run --extra dev pytest -q --cov=app
```

Key cases, with representative snippets:

**Math / simulator**

```python
def test_prices_positive_and_change():
    sim = GBMSimulator(["AAPL"])
    assert all(sim.step()["AAPL"] > 0 for _ in range(10_000))

def test_default_universe_cholesky_ok():            # gap flagged in the review
    sim = GBMSimulator(list(SEED_PRICES))
    assert sim._cholesky is not None and len(sim.step()) == 10

def test_correlation_realised():                    # tech names should co-move
    sim = GBMSimulator(["AAPL", "MSFT"], event_probability=0)
    a, m = [], []
    prev = {t: sim.get_price(t) for t in ("AAPL", "MSFT")}
    for _ in range(5000):
        cur = sim.step()
        a.append(cur["AAPL"] - prev["AAPL"]); m.append(cur["MSFT"] - prev["MSFT"]); prev = cur
    assert np.corrcoef(a, m)[0, 1] > 0.3             # loose: rounding to cents adds noise

def test_gbm_deterministic_with_seed():
    np.random.seed(1); random.seed(1); a = GBMSimulator(["AAPL"]).step()
    np.random.seed(1); random.seed(1); b = GBMSimulator(["AAPL"]).step()
    assert a == b
```

**Cache** — direction/change on up/down/first update, `version` increments, `remove`, `get_all` returns a copy, and a thread-safety test:

```python
def test_concurrent_writers():
    cache = PriceCache()
    def work(n):
        for i in range(1000): cache.update(f"T{n}", 100 + i)
    ts = [threading.Thread(target=work, args=(n,)) for n in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert cache.version == 8000 and len(cache) == 8
```

**Simulator source** — `start()` seeds the cache immediately; `add_ticker` seeds; `remove_ticker` evicts; `stop()` is idempotent; the loop writes new prices (use `update_interval=0.01` and `await asyncio.sleep(0.1)`, assert `cache.version` advanced instead of relying on a price differing).

**Massive** — mock the `RESTClient`, never the network:

```python
def _snap(ticker, price, ts_ms):
    s = MagicMock(); s.ticker = ticker
    s.last_trade.price = price; s.last_trade.timestamp = ts_ms
    return s

async def test_poll_updates_cache_and_converts_ms():
    cache = PriceCache(); src = MassiveDataSource("k", cache, poll_interval=60)
    src._tickers, src._client = ["AAPL"], MagicMock()
    with patch.object(src, "_fetch_snapshots", return_value=[_snap("AAPL", 190.5, 1707580800000)]):
        await src._poll_once()
    assert cache.get("AAPL").price == 190.5
    assert cache.get("AAPL").timestamp == 1707580800.0

async def test_failure_keeps_last_price():
    cache = PriceCache(); cache.update("AAPL", 190.0)
    src = MassiveDataSource("k", cache); src._tickers, src._client = ["AAPL"], MagicMock()
    with patch.object(src, "_fetch_snapshots", side_effect=RuntimeError("429")):
        await src._poll_once()                      # must not raise
    assert cache.get_price("AAPL") == 190.0
```

Also: malformed snapshot skipped, `start()` performs an immediate poll, `stop()` cancels the task.

**Interface conformance** — one parametrized suite run against both sources (Massive with `_fetch_snapshots` patched): start→cache populated, add/remove round-trip, double-stop OK, `get_tickers()` reflects mutations.

**Factory** — unset / empty / whitespace key → `SimulatorDataSource`; non-empty → `MassiveDataSource` (use `monkeypatch.setenv`).

**SSE** — the review's biggest gap. Test the generator directly with a stub request instead of a live server (avoids the never-ending response problem of `TestClient`):

```python
class _Req:
    client = None
    def __init__(self, disconnect_after): self._n, self._after = 0, disconnect_after
    async def is_disconnected(self):
        self._n += 1
        return self._n > self._after

async def test_sse_emits_snapshot_then_skips_unchanged():
    cache = PriceCache(); cache.update("AAPL", 190.0)
    chunks = [c async for c in _generate_events(cache, _Req(3), interval=0.01)]
    assert chunks[0] == "retry: 1000\n\n"
    data = [c for c in chunks if c.startswith("data: ")]
    assert len(data) == 1                                   # version unchanged → sent once
    assert json.loads(data[0][6:])["AAPL"]["price"] == 190.0
```

And one end-to-end check with `httpx.AsyncClient(transport=ASGITransport(app))` using `client.stream("GET", "/api/stream/prices")` and reading the first `data:` line before closing.

**E2E** (in `test/`, Playwright): default 10 tickers appear, prices change within a few seconds, connection dot is green; kill/restart the SSE (stop the container briefly) and assert it returns to green.

## 14. Configuration reference

| Parameter | Where | Default | Notes |
|---|---|---|---|
| `MASSIVE_API_KEY` | env | unset | Set → Massive; unset/blank → simulator |
| `MASSIVE_POLL_INTERVAL` | env (optional) | `15` s | Free tier ≥ 12 s (5 req/min); paid 2–5 s |
| `update_interval` | `SimulatorDataSource` | `0.5` s | Simulator tick |
| `event_probability` | `GBMSimulator` | `0.001` | Per ticker per tick shock chance |
| `dt` | `GBMSimulator` | ≈ `8.48e-8` | Tick as fraction of a trading year; keep in sync with `update_interval` |
| SSE `interval` | `_generate_events` | `0.5` s | Cache poll cadence |
| SSE `retry` | stream preamble | `1000` ms | Browser reconnect delay |
| `SEED_PRICES`, `TICKER_PARAMS` | `seed_prices.py` | see §7.1 | Add rows to tune a new default ticker |

### Implementation checklist for the "Deltas"

All optional relative to what is already shipped; none change the `MarketDataSource` contract.

- [ ] `PriceUpdate.day_open` + `day_change_percent`; `PriceCache.update(..., day_open=None)`; Massive passes `snap.day.previous_close` (guard `None`/`0`)
- [ ] Normalize tickers (`upper().strip()`) in `SimulatorDataSource`
- [ ] Move the `APIRouter` inside `create_stream_router`
- [ ] Massive: early-wake on `add_ticker`, min poll spacing, failure backoff
- [ ] SSE generator tests + 10-ticker Cholesky test + concurrent-writer cache test
- [ ] Watchlist routes keep position tickers tracked (§11)
