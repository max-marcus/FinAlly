import pytest

from app.db import Database
from app.market import PriceCache
from app.services.errors import TradeError
from app.services.portfolio import PortfolioService
from app.services.repository import DbPortfolioRepository


@pytest.fixture
def setup():
    db = Database(":memory:")
    db.initialize()
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return PortfolioService(DbPortfolioRepository(db), cache), cache


def test_avg_cost_on_second_buy(setup):
    svc, cache = setup
    svc.execute_trade("AAPL", "buy", 10)
    cache.update("AAPL", 200.0)
    svc.execute_trade("AAPL", "buy", 10)
    pos = svc.get_portfolio()["positions"][0]
    assert pos["avg_cost"] == 150.0 and pos["quantity"] == 20


def test_sell_at_loss_and_pnl(setup):
    svc, cache = setup
    svc.execute_trade("AAPL", "buy", 10)
    cache.update("AAPL", 90.0)
    p = svc.get_portfolio()
    assert p["unrealized_pnl"] == -100.0
    svc.execute_trade("AAPL", "sell", 10)
    assert svc.get_portfolio()["cash_balance"] == 9900.0


def test_partial_sell(setup):
    svc, _ = setup
    svc.execute_trade("AAPL", "buy", 10)
    svc.execute_trade("AAPL", "sell", 4)
    assert svc.get_portfolio()["positions"][0]["quantity"] == 6


def test_validation(setup):
    svc, _ = setup
    for args in [("AAPL", "buy", 0), ("AAPL", "x", 1), ("", "buy", 1), ("AAPL", "buy", 101), ("AAPL", "sell", 1)]:
        with pytest.raises(TradeError):
            svc.execute_trade(*args)
    assert svc.get_portfolio()["cash_balance"] == 10000.0


def test_exact_cash_buy(setup):
    svc, _ = setup
    svc.execute_trade("AAPL", "buy", 100)
    assert svc.get_portfolio()["cash_balance"] == 0.0
