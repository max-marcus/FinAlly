import json

import pytest

from app.llm import ChatService, MockLLMClient, build_default_handlers
from app.llm.service import FALLBACK_MESSAGE, parse_llm_output


class FakePortfolio:
    def __init__(self, fail_on=None):
        self.trades = []
        self.fail_on = fail_on

    def get_context(self):
        return {"cash": 10000, "positions": []}

    def execute_trade(self, ticker, side, quantity):
        if self.fail_on == ticker:
            raise ValueError("Insufficient cash")
        self.trades.append((ticker, side, quantity))


class FakeWatchlist:
    def __init__(self):
        self.added, self.removed = [], []

    async def add_ticker(self, t):  # async port allowed
        self.added.append(t)

    def remove_ticker(self, t):
        self.removed.append(t)


class FakeRepo:
    def __init__(self):
        self.msgs = []

    def add(self, role, content, actions=None):
        self.msgs.append({"role": role, "content": content, "actions": actions})

    def recent(self, limit=20):
        return list(self.msgs[-limit:])


class StubLLM:
    def __init__(self, raw):
        self.raw, self.seen = raw, None

    async def complete(self, messages):
        self.seen = messages
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


def make(llm, portfolio=None):
    portfolio = portfolio or FakePortfolio()
    wl, repo = FakeWatchlist(), FakeRepo()
    svc = ChatService(llm, repo, portfolio, build_default_handlers(portfolio, wl))
    return svc, portfolio, wl, repo


def test_parse_plain_and_fenced_and_prose():
    raw = '{"message": "hi", "trades": [{"ticker": "aapl", "side": "BUY", "quantity": 2}]}'
    r = parse_llm_output(raw)
    assert r.trades[0].ticker == "AAPL" and r.trades[0].side == "buy"
    assert parse_llm_output(f"```json\n{raw}\n```").message == "hi"
    assert parse_llm_output(f"Sure! {raw} done").message == "hi"
    assert parse_llm_output('{"message": "x", "trades": null}').trades == []


@pytest.mark.parametrize("raw", ["", "nope", "{}", '{"message": "x", "trades": [{"ticker": "A", "side": "hold", "quantity": 1}]}',
                                 '{"message": "x", "trades": [{"ticker": "A", "side": "buy", "quantity": -1}]}'])
def test_parse_malformed(raw):
    with pytest.raises(ValueError):
        parse_llm_output(raw)


async def test_trade_and_watchlist_executed_and_persisted():
    raw = json.dumps({"message": "ok", "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 3}],
                      "watchlist_changes": [{"ticker": "PYPL", "action": "add"}, {"ticker": "V", "action": "remove"}]})
    svc, pf, wl, repo = make(StubLLM(raw))
    res = await svc.chat("go")
    assert pf.trades == [("AAPL", "buy", 3)]
    assert wl.added == ["PYPL"] and wl.removed == ["V"]
    d = res.to_dict()
    assert len(d["trades"]) == 1 and len(d["watchlist_changes"]) == 2
    assert all(x["status"] == "executed" and x["error"] is None for x in d["trades"] + d["watchlist_changes"])
    assert sorted(d) == ["message", "trades", "watchlist_changes"]
    assert [m["role"] for m in repo.msgs] == ["user", "assistant"]
    assert repo.msgs[1]["actions"]["actions"] == res.actions


async def test_failed_trade_reported_not_raised():
    raw = json.dumps({"message": "ok", "trades": [
        {"ticker": "TSLA", "side": "buy", "quantity": 1000}, {"ticker": "AAPL", "side": "buy", "quantity": 1}]})
    svc, pf, _, _ = make(StubLLM(raw), FakePortfolio(fail_on="TSLA"))
    res = await svc.chat("go")
    assert pf.trades == [("AAPL", "buy", 1)]
    assert "Insufficient cash" in res.message
    bad = [t for t in res.to_dict()["trades"] if t["status"] == "failed"]
    assert bad[0]["ticker"] == "TSLA" and "Insufficient" in bad[0]["error"]


@pytest.mark.parametrize("llm", [StubLLM("garbage"), StubLLM(RuntimeError("boom"))])
async def test_malformed_or_failing_llm_falls_back(llm):
    svc, pf, _, repo = make(llm)
    res = await svc.chat("hi")
    assert res.message == FALLBACK_MESSAGE and res.actions == [] and pf.trades == []
    assert len(repo.msgs) == 2


async def test_history_and_context_in_prompt():
    llm = StubLLM('{"message": "a"}')
    svc, _, _, repo = make(llm)
    await svc.chat("first")
    await svc.chat("second")
    roles = [m["role"] for m in llm.seen]
    assert roles == ["system", "user", "assistant", "user"]
    assert "FinAlly" in llm.seen[0]["content"] and "10000" in llm.seen[0]["content"]
    assert llm.seen[-1]["content"] == "second"


@pytest.mark.parametrize("text,key,expect", [
    ("please buy", "trades", {"ticker": "AAPL", "side": "buy", "quantity": 1.0}),
    ("buy 5 tsla", "trades", {"ticker": "TSLA", "side": "buy", "quantity": 5.0}),
    ("sell 2 MSFT", "trades", {"ticker": "MSFT", "side": "sell", "quantity": 2.0}),
    ("add pypl", "watchlist_changes", {"ticker": "PYPL", "action": "add"}),
    ("remove NFLX", "watchlist_changes", {"ticker": "NFLX", "action": "remove"}),
])
async def test_mock_triggers(text, key, expect):
    out = json.loads(await MockLLMClient().complete([{"role": "user", "content": text}]))
    assert out[key] == [expect]
    parse_llm_output(json.dumps(out))


async def test_mock_default_is_plain_text():
    out = json.loads(await MockLLMClient().complete([{"role": "user", "content": "how am I doing?"}]))
    assert out["trades"] == [] and out["watchlist_changes"] == [] and out["message"]


async def test_handle_message_with_trading_adapter():
    from app.llm.adapters import TradingServiceAdapter

    class Trading:
        def __init__(self):
            self.calls = []

        def execute_trade(self, t, s, q):
            self.calls.append((t, s, q))
            return {"price": 190.0}

        def get_portfolio(self):
            return {"cash": 1}

        def get_watchlist(self):
            return []

        async def add_watchlist(self, t):
            return False

        async def remove_watchlist(self, t):
            return True

    tr, repo = Trading(), FakeRepo()
    ad = TradingServiceAdapter(tr)
    svc = ChatService(MockLLMClient(), repo, ad, build_default_handlers(ad, ad))
    out = await svc.handle_message("buy 2 aapl")
    assert tr.calls == [("AAPL", "buy", 2.0)] and out["trades"][0]["price"] == 190.0
    out = await svc.handle_message("add pypl")
    assert out["watchlist_changes"][0]["status"] == "failed"
