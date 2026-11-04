# Market Data Interface

The unified Python API for stock prices in FinAlly. All downstream code (SSE, portfolio, trades, chat) uses this and never knows whether prices come from Massive or the simulator.

Selection rule: **`MASSIVE_API_KEY` set and non-empty → Massive; otherwise → simulator.** See `MASSIVE_API.md` for the provider and `MARKET_SIMULATOR.md` for the simulator.

Code lives in `backend/app/market/`. Items marked **[exists]** are implemented and tested; **[proposed]** are additions this design calls for.

## 1. Architecture

```
            create_market_data_source(cache)          [exists] factory.py
                          │
        ┌─────────────────┴──────────────────┐
 SimulatorDataSource                  MassiveDataSource      both: MarketDataSource ABC
 (GBM, 500ms ticks)                   (snapshot poll 2–15s)
        │  writes                            │  writes
        └──────────────► PriceCache ◄────────┘
                        (latest price per ticker, thread-safe, version counter)
                              │ reads
        ┌─────────────┬───────┴───────┬────────────────┐
   SSE /api/stream   portfolio     trade execution   watchlist API
```

Principles: push model (sources write to the cache on their own schedule; consumers only read the cache); strategy pattern (one ABC, two implementations); the cache is the single source of truth for "current price".

## 2. Live prices

### PriceUpdate [exists] — `models.py`
Frozen dataclass: `ticker, price, previous_price, timestamp` (Unix **seconds**) + properties `change`, `change_percent`, `direction` (`up|down|flat`) and `to_dict()`.

### PriceCache [exists] — `cache.py`
`update(ticker, price, timestamp=None) -> PriceUpdate`, `get`, `get_price`, `get_all`, `remove`, `version`, `__len__`, `__contains__`. `previous_price` is the prior *tick* (drives flash animations).

### MarketDataSource [exists] — `interface.py`
```python
class MarketDataSource(ABC):
    async def start(self, tickers: list[str]) -> None: ...   # begin background task, seed cache
    async def stop(self) -> None: ...                        # idempotent
    async def add_ticker(self, ticker: str) -> None: ...     # no-op if present
    async def remove_ticker(self, ticker: str) -> None: ...  # also clears cache entry
    def get_tickers(self) -> list[str]: ...
```

### Factory [exists] — `factory.py`
```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    return MassiveDataSource(api_key=key, price_cache=price_cache) if key \
        else SimulatorDataSource(price_cache=price_cache)
```

### Typical use (FastAPI lifespan)
```python
cache = PriceCache()
source = create_market_data_source(cache)
await source.start(watchlist_tickers)          # reads DB watchlist
app.include_router(create_stream_router(cache))
...
price = cache.get_price("AAPL")                # trades & portfolio valuation
await source.add_ticker("PYPL")                # watchlist POST
await source.stop()                            # shutdown
```

Ticker validation rule for callers: a trade or watchlist add for a ticker with no cache entry should be rejected (Massive: unknown tickers never appear; simulator: any new ticker gets a random seed price in $50–300, so the simulator accepts everything — acceptable for a demo).

## 3. End-of-day prices [proposed]

Live polling alone cannot supply a true previous close or history (and the Massive free tier has *only* EOD data). Add a second, small, stateless interface with the same two implementations.

```python
# app/market/eod.py  [proposed]
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True, slots=True)
class DailyBar:
    ticker: str
    day: date
    open: float
    high: float
    low: float
    close: float
    volume: float

class EodDataSource(ABC):
    @abstractmethod
    async def get_daily_bars(self, tickers: list[str], day: date | None = None) -> dict[str, DailyBar]:
        """EOD bar per ticker for `day` (default: most recent completed session).
        Tickers with no data are omitted."""

    @abstractmethod
    async def get_history(self, ticker: str, start: date, end: date) -> list[DailyBar]:
        """Daily bars, ascending by date."""

    async def get_previous_closes(self, tickers: list[str]) -> dict[str, float]:
        bars = await self.get_daily_bars(tickers)
        return {t: b.close for t, b in bars.items()}
```

**MassiveEodSource** — `get_daily_bars` uses *grouped daily* (one call for all tickers; filter locally; walk back over weekends/holidays up to ~5 days when `results` is empty); `get_history` uses `list_aggs(ticker, 1, "day", start, end)`. All sync client calls go through `asyncio.to_thread`. Respect the 5 calls/min free limit: results for a given date are immutable once the session is closed, so cache them in memory (`dict[(date)] -> bars`).

**SimulatorEodSource** — deterministic and offline: `get_daily_bars` returns bars derived from `SEED_PRICES` (close = seed price; open/high/low via a seeded `random.Random(hash((ticker, day)))` ±1–2%); `get_history` generates a GBM random walk backwards from the seed price using the same per-ticker `mu/sigma` with `dt = 1/252`, seeded per ticker so repeated calls are identical.

Selection: same rule, one factory:
```python
def create_eod_source() -> EodDataSource:
    return MassiveEodSource(key) if key else SimulatorEodSource()
```

## 4. Day-change baseline [proposed]

The watchlist shows "daily change %". The cache's `previous_price` is tick-over-tick, so add a per-ticker `prev_close` alongside it:

- `PriceCache.set_prev_close(ticker, price)` / `get_prev_close(ticker)`; `PriceUpdate.to_dict()` gains `prev_close` and `day_change_percent`.
- Massive live source: fill from snapshot `prev_day.close` on every poll (free).
- Simulator: `prev_close = seed price` at start (the session "open").
- At startup, if a source lacks it, populate via `EodDataSource.get_previous_closes`.

## 5. Behavior contract (both implementations)

1. `start()` leaves the cache populated for every requested ticker before returning (Massive: immediate first poll; simulator: seed prices).
2. Tickers are normalized upper-case, stripped.
3. Failures never propagate out of the background task; log and retry next interval.
4. `PriceUpdate.timestamp` is Unix seconds (Massive snapshot timestamps are **nanoseconds** — convert).
5. Missing fields degrade gracefully: price = `last_trade.price` → `min.close` → `day.close`; skip the ticker if none exist.
6. Poll intervals: simulator 0.5 s; Massive 15 s default, configurable (paid plans 2–5 s). Free-key users (EOD only) should be told in logs that snapshots are unavailable (HTTP 403) and the system falls back to the simulator for live ticks.

## 6. SOLID mapping

- **S** — `MassiveDataSource` fetches and normalizes; `PriceCache` stores; `stream.py` formats SSE; the factory selects. None does two jobs. Keep `GBMSimulator` (math) apart from `SimulatorDataSource` (scheduling).
- **O** — Add a provider (e.g. another vendor) as a new `MarketDataSource` + `EodDataSource` pair and one branch in the factories; consumers are untouched.
- **L** — Both sources satisfy the §5 contract; verify with a single parametrized contract test run over every implementation.
- **I** — Live (`MarketDataSource`) and end-of-day (`EodDataSource`) are separate interfaces, because the free Massive tier supports only the latter and a simulator needs no HTTP. Consumers needing only a price take `PriceCache` (or a `Callable[[str], float | None]`), not a source.
- **D** — Services receive `PriceCache`/sources by injection from the composition root. Only the factories read `MASSIVE_API_KEY`; the `massive` import stays inside the Massive classes. Inject the `RESTClient` into `MassiveDataSource`'s constructor (default: build from the key) so tests pass a fake without patching.

## 7. Testing

- Unit-test both sources against the ABC contract with the same parametrized tests.
- Massive: mock `RESTClient` (patch `get_snapshot_all`, `get_grouped_daily_aggs`, `list_aggs`); include cases for missing `last_trade`, ns timestamps, empty results (holiday), 403/429.
- Simulator EOD: assert determinism (two calls equal) and OHLC invariants (`low ≤ open,close ≤ high`).
