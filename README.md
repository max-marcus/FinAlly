# FinAlly

FinAlly is a simulated trading workstation with live prices and an AI chat assistant that can place market orders. It is the capstone project for an agentic coding course. The product spec is [`planning/PLAN.md`](planning/PLAN.md).

## Status

The market data library in `backend/` is built and tested. The frontend, portfolio, chat API, SQLite database, and Docker image are specified in the plan and are still to be built.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/)

## Market data

The library in `backend/app/market/` writes prices into a shared in-memory cache.

- With no API key, a geometric Brownian motion simulator generates prices. The default watchlist is AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, and NFLX.
- With `MASSIVE_API_KEY` set to a non-empty value, `create_market_data_source()` polls Massive (Polygon.io) into the same cache.

`create_stream_router(cache)` returns a FastAPI router for `GET /api/stream/prices` (server-sent events, about every 500 ms). That router is a library function. An application that mounts it is still to be built, so nothing serves the endpoint yet.

From `backend/`:

```bash
uv sync --extra dev
uv run market_data_demo.py   # 60-second terminal dashboard of simulated prices
uv run pytest                # market data tests
uv run ruff check .          # lint
```

The demo always uses the simulator. It does not read `MASSIVE_API_KEY`. Stop it with Ctrl+C.

Set `MASSIVE_API_KEY` in the environment before code that calls `create_market_data_source()`. Do not commit the key. `.env` is gitignored.

## Layout

```
backend/     Market data library, tests, and the terminal demo
planning/    Product spec (PLAN.md), market data summary, and design archive
LICENSE      MIT
```

Further notes:

- [`planning/MARKET_DATA_SUMMARY.md`](planning/MARKET_DATA_SUMMARY.md) — what the market data library does
- [`backend/README.md`](backend/README.md) — module list, tests, and lint
- [`backend/CLAUDE.md`](backend/CLAUDE.md) — public API for downstream code

## License

MIT. See [LICENSE](LICENSE).
