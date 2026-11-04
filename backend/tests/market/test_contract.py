"""Shared contract tests run against every MarketDataSource implementation (Liskov)."""

from unittest.mock import MagicMock, patch

import pytest

from app.market.cache import PriceCache
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource
from app.market.stream import create_stream_router


def _fake_snapshots(**kwargs):
    snaps = []
    for t in kwargs["tickers"]:
        snap = MagicMock()
        snap.ticker = t
        snap.last_trade.price = 100.0
        snap.last_trade.timestamp = 1_700_000_000_000
        snaps.append(snap)
    return snaps


@pytest.fixture(params=["simulator", "massive"])
def make_source(request):
    """Yield a factory (cache) -> unstarted source, with the network mocked for Massive."""
    if request.param == "simulator":
        yield lambda cache: SimulatorDataSource(price_cache=cache, update_interval=0.05)
    else:
        with patch("app.market.massive_client.RESTClient") as rest:
            rest.return_value.get_snapshot_all.side_effect = _fake_snapshots
            yield lambda cache: MassiveDataSource(
                api_key="test", price_cache=cache, poll_interval=3600
            )


async def test_cache_seeded_after_start(make_source):
    cache = PriceCache()
    source = make_source(cache)
    await source.start(["AAPL", "MSFT"])
    try:
        assert cache.get("AAPL") is not None
        assert cache.get("MSFT") is not None
    finally:
        await source.stop()


async def test_tickers_are_upper_cased(make_source):
    cache = PriceCache()
    source = make_source(cache)
    await source.start(["aapl"])
    try:
        await source.add_ticker(" msft ")
        assert sorted(source.get_tickers()) == ["AAPL", "MSFT"]
    finally:
        await source.stop()


async def test_add_ticker_is_idempotent(make_source):
    cache = PriceCache()
    source = make_source(cache)
    await source.start(["AAPL"])
    try:
        await source.add_ticker("AAPL")
        assert source.get_tickers() == ["AAPL"]
    finally:
        await source.stop()


async def test_remove_ticker_clears_cache_and_ignores_unknown(make_source):
    cache = PriceCache()
    source = make_source(cache)
    await source.start(["AAPL", "MSFT"])
    try:
        await source.remove_ticker("msft")
        assert source.get_tickers() == ["AAPL"]
        assert cache.get("MSFT") is None
        await source.remove_ticker("ZZZZ")  # no-op, must not raise
    finally:
        await source.stop()


async def test_stop_is_idempotent(make_source):
    cache = PriceCache()
    source = make_source(cache)
    await source.start(["AAPL"])
    await source.stop()
    await source.stop()


def test_stream_router_has_no_shared_state():
    cache = PriceCache()
    r1 = create_stream_router(cache)
    r2 = create_stream_router(cache)
    assert r1 is not r2
    assert [r.path for r in r1.routes] == ["/api/stream/prices"]
    assert [r.path for r in r2.routes] == ["/api/stream/prices"]


def test_cache_normalizes_ticker_case_and_accepts_zero_timestamp():
    cache = PriceCache()
    update = cache.update("aapl", 10.0, timestamp=0.0)
    assert update.ticker == "AAPL"
    assert update.timestamp == 0.0
    assert cache.get("aapl") is update
    assert "aapl" in cache
