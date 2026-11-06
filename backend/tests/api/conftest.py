import pytest
from fastapi.testclient import TestClient

from app.main import Settings, create_app
from app.market import MarketDataSource, PriceCache


class StubSource(MarketDataSource):
    def __init__(self, cache: PriceCache):
        self.cache = cache
        self.tickers: list[str] = []

    async def start(self, tickers):
        self.tickers = list(tickers)
        for t in tickers:
            self.cache.update(t, 100.0)

    async def stop(self):
        pass

    async def add_ticker(self, ticker):
        if ticker not in self.tickers:
            self.tickers.append(ticker)
            self.cache.update(ticker, 50.0)

    async def remove_ticker(self, ticker):
        if ticker in self.tickers:
            self.tickers.remove(ticker)
        self.cache.remove(ticker)

    def get_tickers(self):
        return list(self.tickers)


class FakeChat:
    def __init__(self, trading):
        self.trading = trading

    async def handle_message(self, message):
        return {"message": f"echo {message}", "trades": [], "watchlist_changes": []}


@pytest.fixture
def client(tmp_path):
    app = create_app(
        Settings(db_path=str(tmp_path / "t.db"), static_dir=None, snapshot_interval=3600),
        market_source_factory=StubSource,
        chat_factory=lambda trading, db, settings: FakeChat(trading),
    )
    with TestClient(app) as c:
        yield c
