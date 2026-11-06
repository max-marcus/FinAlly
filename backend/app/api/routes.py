"""HTTP routes: translate HTTP <-> service calls only."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.errors import NotFoundError, TradeError
from app.services.portfolio import PortfolioService
from app.services.protocols import ChatService
from app.services.watchlist import WatchlistService


class TradeRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)
    quantity: float = Field(gt=0)
    side: Literal["buy", "sell"]


class WatchlistAddRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=16)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def create_api_router(
    portfolio: PortfolioService,
    watchlist: WatchlistService,
    chat: ChatService,
) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @router.get("/portfolio")
    def get_portfolio() -> dict:
        return portfolio.get_portfolio()

    @router.post("/portfolio/trade")
    def trade(req: TradeRequest) -> dict:
        try:
            return portfolio.execute_trade(req.ticker, req.side, req.quantity)
        except TradeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.get("/portfolio/history")
    def history() -> dict:
        return portfolio.history()

    @router.get("/watchlist")
    def get_watchlist() -> dict:
        return {"watchlist": watchlist.list()}

    @router.post("/watchlist")
    async def add_watchlist(req: WatchlistAddRequest) -> dict:
        try:
            added = await watchlist.add(req.ticker)
        except TradeError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        return {"ticker": req.ticker.strip().upper(), "added": added}

    @router.delete("/watchlist/{ticker}")
    async def remove_watchlist(ticker: str) -> dict:
        try:
            await watchlist.remove(ticker)
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        return {"ticker": ticker.strip().upper(), "removed": True}

    @router.post("/chat")
    async def post_chat(req: ChatRequest) -> dict:
        return await chat.handle_message(req.message)

    return router
