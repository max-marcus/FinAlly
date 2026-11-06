import os

from fastapi.testclient import TestClient

from app.main import Settings, create_app


def test_chat_endpoint_with_mock(tmp_path):
    settings = Settings(db_path=str(tmp_path / "t.db"), llm_mock=True)
    with TestClient(create_app(settings)) as c:
        r = c.post("/api/chat", json={"message": "add pypl"})
        assert r.status_code == 200, r.text
        assert r.json()["watchlist_changes"][0]["ticker"] == "PYPL"
        r = c.post("/api/chat", json={"message": "how am I doing?"})
        assert r.json()["trades"] == []
        r = c.post("/api/chat", json={"message": "sell 5 MSFT"})
        t = r.json()["trades"][0]
        assert t["status"] == "failed" and t["error"]
