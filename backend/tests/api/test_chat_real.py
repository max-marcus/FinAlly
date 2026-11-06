from fastapi.testclient import TestClient

from app.main import Settings, create_app
from tests.api.conftest import StubSource


def test_mock_llm_chat_end_to_end(tmp_path):
    app = create_app(
        Settings(db_path=str(tmp_path / "c.db"), snapshot_interval=3600, llm_mock=True),
        market_source_factory=StubSource,
    )
    with TestClient(app) as c:
        r = c.post("/api/chat", json={"message": "buy 1 AAPL"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "message" in body and "trades" in body and "watchlist_changes" in body
