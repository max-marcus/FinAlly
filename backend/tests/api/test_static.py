from fastapi.testclient import TestClient

from app.main import Settings, create_app
from tests.api.conftest import StubSource


def test_static_served_and_api_wins(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<h1>hi</h1>")
    app = create_app(
        Settings(db_path=str(tmp_path / "s.db"), static_dir=static, snapshot_interval=3600, llm_mock=True),
        market_source_factory=StubSource,
    )
    with TestClient(app) as c:
        assert "hi" in c.get("/").text
        assert c.get("/api/health").json() == {"status": "ok"}
