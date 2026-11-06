def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_initial_portfolio(client):
    p = client.get("/api/portfolio").json()
    assert p["cash_balance"] == 10000.0
    assert p["total_value"] == 10000.0
    assert p["positions"] == []


def test_default_watchlist_has_prices(client):
    w = client.get("/api/watchlist").json()["watchlist"]
    assert [i["ticker"] for i in w][:3] == ["AAPL", "GOOGL", "MSFT"]
    assert len(w) == 10
    assert all(i["price"] == 100.0 for i in w)


def test_buy_and_sell(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 10, "side": "buy"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trade"]["ticker"] == "AAPL"
    assert body["cash_balance"] == 9000.0
    p = client.get("/api/portfolio").json()
    assert p["positions"][0]["quantity"] == 10
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 10, "side": "sell"})
    assert r.status_code == 200
    p = client.get("/api/portfolio").json()
    assert p["positions"] == []
    assert p["cash_balance"] == 10000.0


def test_fractional_and_avg_cost(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 0.5, "side": "buy"})
    p = client.get("/api/portfolio").json()
    assert p["positions"][0]["quantity"] == 0.5
    assert p["positions"][0]["avg_cost"] == 100.0


def test_insufficient_cash(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"})
    assert r.status_code == 400
    assert "Insufficient cash" in r.json()["detail"]


def test_insufficient_shares(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert r.status_code == 400
    assert "Insufficient shares" in r.json()["detail"]


def test_unknown_ticker_no_price(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "ZZZZ", "quantity": 1, "side": "buy"})
    assert r.status_code == 400


def test_invalid_request(client):
    assert client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": -1, "side": "buy"}).status_code == 422
    assert client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "hold"}).status_code == 422


def test_history_records_after_trade(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    h = client.get("/api/portfolio/history").json()["snapshots"]
    assert len(h) >= 1 and h[-1]["total_value"] == 10000.0


def test_watchlist_add_remove(client):
    r = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert r.json() == {"ticker": "PYPL", "added": True}
    assert client.post("/api/watchlist", json={"ticker": "PYPL"}).json()["added"] is False
    assert any(i["ticker"] == "PYPL" and i["price"] == 50.0 for i in client.get("/api/watchlist").json()["watchlist"])
    assert client.delete("/api/watchlist/PYPL").json()["removed"] is True
    assert client.delete("/api/watchlist/PYPL").status_code == 404


def test_invalid_ticker(client):
    assert client.post("/api/watchlist", json={"ticker": "bad ticker!"}).status_code == 400


def test_held_position_keeps_price_after_unwatch(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    client.delete("/api/watchlist/AAPL")
    p = client.get("/api/portfolio").json()
    assert p["positions"][0]["current_price"] == 100.0


def test_chat(client):
    r = client.post("/api/chat", json={"message": "hi"})
    assert r.json()["message"] == "echo hi"
