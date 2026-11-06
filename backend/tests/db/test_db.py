import pytest

from app.db import (
    ChatRepository, Database, PositionRepository, SnapshotRepository,
    TradeRepository, UserRepository, WatchlistRepository,
)


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "sub" / "t.db")
    d.initialize()
    yield d
    d.close()


def test_seed_and_idempotent_init(db):
    assert UserRepository(db).get_cash() == 10000.0
    w = WatchlistRepository(db)
    assert w.tickers() == ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
    w.remove("AAPL")
    db.initialize()
    assert "AAPL" not in w.tickers()  # not re-seeded


def test_persistence(tmp_path):
    p = tmp_path / "x.db"
    d = Database(p); d.initialize(); UserRepository(d).set_cash(5.0); d.close()
    d2 = Database(p); d2.initialize()
    assert UserRepository(d2).get_cash() == 5.0


def test_watchlist(db):
    w = WatchlistRepository(db)
    assert w.add("pypl") is True
    assert w.add("PYPL") is False
    assert w.contains("pypl")
    assert w.remove("pypl") is True
    assert w.remove("pypl") is False


def test_positions_and_trades(db):
    p, t = PositionRepository(db), TradeRepository(db)
    p.upsert("aapl", 10, 100)
    pos = p.upsert("AAPL", 15, 110)
    assert (pos.quantity, pos.avg_cost) == (15, 110) and len(p.list()) == 1
    assert p.delete("AAPL") and p.get("AAPL") is None
    t.record("AAPL", "buy", 1, 2); t.record("AAPL", "sell", 1, 3)
    assert [x.side for x in t.list()] == ["sell", "buy"]
    assert len(t.list(limit=1)) == 1
    with pytest.raises(ValueError):
        t.record("AAPL", "hold", 1, 1)


def test_transaction_commit_and_rollback(db):
    u, p, t = UserRepository(db), PositionRepository(db), TradeRepository(db)
    with db.transaction():
        u.set_cash(8000); p.upsert("AAPL", 10, 200); t.record("AAPL", "buy", 10, 200)
    assert u.get_cash() == 8000 and p.get("AAPL") and len(t.list()) == 1
    with pytest.raises(RuntimeError):
        with db.transaction():
            u.set_cash(1)
            with db.transaction():  # nested joins outer
                p.delete("AAPL")
            raise RuntimeError
    assert u.get_cash() == 8000 and p.get("AAPL")


def test_snapshots(db):
    s = SnapshotRepository(db)
    for v in (1, 2, 3, 4):
        s.record(v)
    assert [x.total_value for x in s.list()] == [1, 2, 3, 4]
    assert [x.total_value for x in s.list(limit=2)] == [3, 4]
    assert s.prune(3) == 1
    assert [x.total_value for x in s.list()] == [2, 3, 4]


def test_chat(db):
    c = ChatRepository(db)
    c.add("user", "hi")
    c.add("assistant", "yo", {"trades": [{"ticker": "AAPL"}]})
    c.add("user", "again")
    r = c.recent(2)
    assert [m.content for m in r] == ["yo", "again"]
    assert r[0].actions == {"trades": [{"ticker": "AAPL"}]} and r[1].actions is None
    with pytest.raises(ValueError):
        c.add("system", "x")


def test_memory_db():
    d = Database(":memory:"); d.initialize()
    assert UserRepository(d).get_cash() == 10000.0
