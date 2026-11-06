"""Composition root: the only place that reads env vars and wires concrete classes."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import create_api_router
from app.db import Database
from app.db.connection import default_db_path
from app.market import MarketDataSource, PriceCache, create_market_data_source, create_stream_router
from app.services.portfolio import PortfolioService
from app.services.protocols import ChatService, TradingService
from app.services.repository import DbPortfolioRepository
from app.services.snapshots import run_snapshot_loop
from app.services.trading import TradingFacade
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    db_path: str | os.PathLike = field(default_factory=default_db_path)
    static_dir: Path | None = None
    snapshot_interval: float = 30.0
    llm_mock: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        static = os.environ.get("STATIC_DIR")
        db = os.environ.get("DB_PATH")
        return cls(
            db_path=db or default_db_path(),
            static_dir=Path(static) if static else None,
            llm_mock=os.environ.get("LLM_MOCK", "").lower() == "true",
        )


ChatFactory = Callable[[TradingService, Database, Settings], ChatService]


def default_chat_factory(trading: TradingService, db: Database, settings: Settings) -> ChatService:
    """Wire llm-engineer's chat service (imported lazily so the API works without it)."""
    from app.chat import create_chat_service

    return create_chat_service(trading=trading, db=db, mock=settings.llm_mock)


def create_app(
    settings: Settings | None = None,
    *,
    market_source_factory: Callable[[PriceCache], MarketDataSource] = create_market_data_source,
    chat_factory: ChatFactory = default_chat_factory,
) -> FastAPI:
    settings = settings or Settings.from_env()

    db = Database(settings.db_path)
    db.initialize()
    cache = PriceCache()
    source = market_source_factory(cache)
    repo = DbPortfolioRepository(db)
    portfolio = PortfolioService(repo, cache)
    watchlist = WatchlistService(repo, source, cache)
    trading = TradingFacade(portfolio, watchlist)
    chat = chat_factory(trading, db, settings)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await source.start(repo.list_watchlist())
        task = asyncio.create_task(run_snapshot_loop(portfolio, settings.snapshot_interval))
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await source.stop()
            db.close()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.include_router(create_api_router(portfolio, watchlist, chat))
    app.include_router(create_stream_router(cache))

    static_dir = settings.static_dir
    if static_dir is None:
        for candidate in (PROJECT_ROOT / "static", PROJECT_ROOT / "backend" / "static", Path("static")):
            if candidate.is_dir():
                static_dir = candidate
                break
    if static_dir and Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    app.state.services = {"portfolio": portfolio, "watchlist": watchlist, "cache": cache}
    return app


def __getattr__(name: str) -> Any:
    # `uvicorn app.main:app` — build lazily so imports in tests have no side effects.
    if name == "app":
        global _app
        try:
            return _app
        except NameError:
            _app = create_app()
            return _app
    raise AttributeError(name)
