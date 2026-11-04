# Market Simulator

How FinAlly generates realistic live stock prices when no `MASSIVE_API_KEY` is set. Implementation: `backend/app/market/simulator.py` (+ `seed_prices.py`). Runs in-process, no network, no dependencies beyond `numpy`.

## 1. Goals

Believable, lively, correlated price action at ~2 updates/second for demo purposes; starts from realistic prices; cheap enough to run for many tickers; deterministic when seeded for tests.

## 2. Model: Geometric Brownian Motion

```
S(t+dt) = S(t) · exp( (μ − σ²/2)·dt + σ·√dt · Z )
```

- `μ` annualized drift, `σ` annualized volatility (per ticker, `TICKER_PARAMS`)
- `dt` = tick length as a fraction of a trading year: `0.5 s / (252 · 6.5 · 3600 s) ≈ 8.5e-8`
- `Z` standard normal, **correlated across tickers** (below)

The exponential form guarantees prices stay positive and moves are proportional to price. At this `dt` a tick moves a $190 stock by a few cents, and moves accumulate to realistic daily ranges (σ=0.22 → ~1.4% daily).

## 3. Correlated moves

Each tick: draw `n` independent normals `z`, multiply by the lower-triangular Cholesky factor `L` of the correlation matrix `C` (`L Lᵀ = C`) to get correlated `Z = L z`.

Correlation rules (`_pairwise_correlation`):

| Pair | ρ |
|---|---|
| both tech (AAPL GOOGL MSFT AMZN META NVDA NFLX) | 0.6 |
| both finance (JPM V) | 0.5 |
| anything with TSLA | 0.3 |
| cross-sector / unknown ticker | 0.3 |

The matrix is rebuilt (O(n²), n<50) whenever a ticker is added or removed. All pairwise ρ ≤ 0.6 keeps `C` positive definite, so `np.linalg.cholesky` is safe.

## 4. Random events

Per ticker per tick, with probability `event_probability` (default 0.001): multiply price by `1 ± U(0.02, 0.05)`. With 10 tickers at 2 ticks/s this yields a visible jump roughly every 50 s — the "drama" in the spec. Set to 0 in tests that need pure GBM.

## 5. Seed data (`seed_prices.py`)

- `SEED_PRICES` — AAPL 190, GOOGL 175, MSFT 420, AMZN 185, TSLA 250, NVDA 800, META 500, JPM 195, V 280, NFLX 600.
- `TICKER_PARAMS` — e.g. TSLA σ0.50/μ0.03, NVDA σ0.40/μ0.08, JPM σ0.18, V σ0.17, default σ0.25/μ0.05 (`DEFAULT_PARAMS`).
- Unknown tickers added dynamically start at `random.uniform(50, 300)` with default params.
- Seed prices are approximations from project creation, not live quotes; refresh occasionally.

## 6. Code structure

```
GBMSimulator            pure math, synchronous, no I/O — unit-testable
  __init__(tickers, dt=DEFAULT_DT, event_probability=0.001)
  step() -> {ticker: price}        one tick for all tickers (hot path)
  add_ticker / remove_ticker       rebuild Cholesky
  get_price / get_tickers
  _rebuild_cholesky, _pairwise_correlation

SimulatorDataSource(MarketDataSource)    asyncio wrapper
  start(tickers)   create GBMSimulator, seed PriceCache, spawn _run_loop task
  _run_loop        while True: step(); cache.update(...) per ticker; sleep(0.5)
  stop             cancel task (idempotent)
  add_ticker       sim.add_ticker + immediate cache seed (price visible at once)
  remove_ticker    sim.remove_ticker + cache.remove
```

Separation of `GBMSimulator` (math) from `SimulatorDataSource` (scheduling/cache) is deliberate: the math is tested without asyncio, the wrapper without math. Exceptions inside the loop are logged and the loop continues.

Design notes (SOLID): `GBMSimulator` has a single responsibility (price math) and no knowledge of the cache or asyncio; `SimulatorDataSource` depends on the `PriceCache` and `MarketDataSource` abstractions and is substitutable for `MassiveDataSource`; correlation and parameter tables live in `seed_prices.py` so tuning never edits the math (open/closed). Inject RNGs and `dt` rather than reading globals.

## 7. Planned extensions (see MARKET_INTERFACE.md)

1. **prev_close baseline**: set `prev_close = seed price` per ticker at start so "daily change %" is meaningful (currently only tick-over-tick change exists).
2. **SimulatorEodSource**: deterministic daily bars/history — a GBM walk backward from the seed price with `dt = 1/252`, seeded by `random.Random(f"{ticker}")` so repeated calls are identical; OHLC built from intraday sub-steps so `low ≤ open,close ≤ high`.
3. **Reproducibility**: accept an optional `seed` in `GBMSimulator` and use a local `np.random.Generator` / `random.Random` instead of the module-level RNGs (the current code uses global `np.random` and `random`, which makes exact-value tests awkward).
4. **Market-hours realism** (optional): none today — the simulator runs 24/7. Not needed for the demo.

## 8. Testing

Existing (`backend/tests/market/test_simulator.py`, `test_simulator_source.py`): prices positive and rounded to cents, add/remove rebuilds correlation, events fire when probability=1, correlated tickers show positive sample correlation over many steps, the data source seeds the cache on `start()`, stops cleanly, and handles ticker add/remove.

Add: seeded determinism once §7.3 lands; statistical check that the log-return std over N steps ≈ `σ√(N·dt)` within tolerance; unknown-ticker default parameters.

## 9. Tuning cheat-sheet

| Want | Change |
|---|---|
| Livelier charts | raise `σ` or `dt` (e.g. ×10 for demos) |
| More dramatic news | raise `event_probability` |
| Tighter sector co-movement | raise `INTRA_*_CORR` (keep matrix positive definite, <1) |
| Slower/faster ticks | `update_interval` (and scale `dt` proportionally to keep volatility per real-time constant) |
