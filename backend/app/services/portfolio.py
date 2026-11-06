"""Portfolio service: trade execution, valuation, snapshots."""

from __future__ import annotations

from typing import Any

from .errors import TradeError
from .protocols import PortfolioRepository, PriceLookup

EPS = 1e-9


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


class PortfolioService:
    def __init__(self, repo: PortfolioRepository, prices: PriceLookup) -> None:
        self._repo = repo
        self._prices = prices

    def get_portfolio(self) -> dict[str, Any]:
        cash = self._repo.get_cash()
        positions = []
        positions_value = 0.0
        cost_basis = 0.0
        for p in self._repo.list_positions():
            qty, avg = float(p["quantity"]), float(p["avg_cost"])
            price = self._prices.get_price(p["ticker"])
            if price is None:
                price = avg
            value = qty * price
            pnl = value - qty * avg
            positions.append(
                {
                    "ticker": p["ticker"],
                    "quantity": qty,
                    "avg_cost": avg,
                    "current_price": price,
                    "market_value": value,
                    "unrealized_pnl": pnl,
                    "unrealized_pnl_percent": (pnl / (qty * avg) * 100) if qty * avg else 0.0,
                }
            )
            positions_value += value
            cost_basis += qty * avg
        pnl_total = positions_value - cost_basis
        return {
            "cash_balance": cash,
            "positions_value": positions_value,
            "total_value": cash + positions_value,
            "unrealized_pnl": pnl_total,
            "unrealized_pnl_percent": (pnl_total / cost_basis * 100) if cost_basis else 0.0,
            "positions": positions,
        }

    def total_value(self) -> float:
        return self.get_portfolio()["total_value"]

    def execute_trade(self, ticker: str, side: str, quantity: float) -> dict[str, Any]:
        ticker = normalize_ticker(ticker)
        side = (side or "").lower()
        if not ticker:
            raise TradeError("Ticker is required")
        if side not in ("buy", "sell"):
            raise TradeError("Side must be 'buy' or 'sell'")
        if not isinstance(quantity, (int, float)) or not quantity > 0:
            raise TradeError("Quantity must be greater than zero")
        quantity = float(quantity)
        price = self._prices.get_price(ticker)
        if price is None:
            raise TradeError(f"No price available for {ticker}")

        cash = self._repo.get_cash()
        existing = next((p for p in self._repo.list_positions() if p["ticker"] == ticker), None)
        held = float(existing["quantity"]) if existing else 0.0
        avg = float(existing["avg_cost"]) if existing else 0.0

        if side == "buy":
            cost = quantity * price
            if cost > cash + EPS:
                raise TradeError(
                    f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}"
                )
            new_cash = cash - cost
            new_qty = held + quantity
            new_avg = (held * avg + cost) / new_qty
        else:
            if quantity > held + EPS:
                raise TradeError(
                    f"Insufficient shares: trying to sell {quantity:g} {ticker}, own {held:g}"
                )
            new_cash = cash + quantity * price
            new_qty = max(held - quantity, 0.0)
            if new_qty < EPS:
                new_qty = 0.0
            new_avg = avg

        trade = self._repo.apply_trade(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            new_cash=new_cash,
            new_quantity=new_qty,
            new_avg_cost=new_avg,
        )
        total = self.snapshot()
        return {"trade": trade, "price": price, "cash_balance": new_cash, "total_value": total}

    def snapshot(self) -> float:
        total = self.total_value()
        self._repo.insert_snapshot(total)
        return total

    def history(self) -> dict[str, Any]:
        return {
            "snapshots": [
                {"total_value": s["total_value"], "recorded_at": s["recorded_at"]}
                for s in self._repo.list_snapshots()
            ]
        }
