# DB Interface (backend/app/db)

Stdlib `sqlite3`, synchronous API (safe to call from FastAPI sync endpoints / threadpool and, for these tiny queries, directly from async code). One shared connection guarded by an RLock. No business logic: trade/P&L math lives in the portfolio service.

All timestamps are ISO-8601 UTC strings. All IDs are UUID4 strings. `user_id` defaults to `"default"` on every method. Tickers are upper-cased by the repos.

## Database (app/db/connection.py)

```python
class Database:
    def __init__(self, path: str | os.PathLike = "db/finally.db")   # ":memory:" supported (tests)
    def initialize(self) -> None      # idempotent: creates tables (IF NOT EXISTS) + seeds if users_profile empty. Creates parent dir.
    def close(self) -> None           # idempotent
    @contextmanager
    def transaction(self) -> Iterator[None]   # BEGIN ... COMMIT; rollback on exception; re-entrant (nested = joins outer)
    def execute(self, sql, params=()) -> int  # returns rowcount; autocommits unless inside transaction()
    def query(self, sql, params=()) -> list[sqlite3.Row]
    def query_one(self, sql, params=()) -> sqlite3.Row | None

def default_db_path() -> Path   # <project root>/db/finally.db. Composition root may override from env.
```
`initialize()` is called by the composition root (main.py lifespan). The path is never read from env inside this package.

## Records (app/db/models.py) — frozen dataclasses

```python
@dataclass(frozen=True) class Profile:      id: str; cash_balance: float; created_at: str
@dataclass(frozen=True) class WatchlistItem: id: str; user_id: str; ticker: str; added_at: str
@dataclass(frozen=True) class Position:     id: str; user_id: str; ticker: str; quantity: float; avg_cost: float; updated_at: str
@dataclass(frozen=True) class Trade:        id: str; user_id: str; ticker: str; side: str; quantity: float; price: float; executed_at: str
@dataclass(frozen=True) class Snapshot:     id: str; user_id: str; total_value: float; recorded_at: str
@dataclass(frozen=True) class ChatMessage:  id: str; user_id: str; role: str; content: str; actions: dict | list | None; created_at: str
```

## Repositories (all take `Database` in ctor)

```python
class UserRepository:
    def get_cash(self, user_id="default") -> float
    def set_cash(self, amount: float, user_id="default") -> None
    def get_profile(self, user_id="default") -> Profile | None

class WatchlistRepository:
    def list(self, user_id="default") -> list[WatchlistItem]         # ordered by added_at, rowid
    def tickers(self, user_id="default") -> list[str]
    def add(self, ticker: str, user_id="default") -> bool            # False if already present
    def remove(self, ticker: str, user_id="default") -> bool         # False if not present
    def contains(self, ticker: str, user_id="default") -> bool

class PositionRepository:
    def list(self, user_id="default") -> list[Position]              # ordered by ticker
    def get(self, ticker: str, user_id="default") -> Position | None
    def upsert(self, ticker: str, quantity: float, avg_cost: float, user_id="default") -> Position
    def delete(self, ticker: str, user_id="default") -> bool         # services call this when qty hits 0

class TradeRepository:
    def record(self, ticker, side, quantity, price, user_id="default") -> Trade   # side in {"buy","sell"} else ValueError
    def list(self, user_id="default", limit: int | None = None) -> list[Trade]    # newest first

class SnapshotRepository:
    def record(self, total_value: float, user_id="default") -> Snapshot
    def list(self, user_id="default", limit: int | None = None) -> list[Snapshot] # oldest -> newest (chart order); with limit = most recent N, still oldest->newest
    def prune(self, keep: int, user_id="default") -> int             # delete oldest beyond `keep`

class ChatRepository:
    def add(self, role: str, content: str, actions: dict | list | None = None, user_id="default") -> ChatMessage  # role in {"user","assistant"}
    def recent(self, limit: int = 20, user_id="default") -> list[ChatMessage]     # last N, oldest -> newest
```

## Atomic trade example
```python
with db.transaction():
    users.set_cash(new_cash)
    positions.upsert("AAPL", qty, avg)   # or positions.delete(...)
    trades.record("AAPL", "buy", 10, 190.0)
snapshots.record(total_value)
```
Inside `transaction()` repo calls don't commit individually; exception => full rollback.

## Wiring
`from app.db import Database, UserRepository, WatchlistRepository, PositionRepository, TradeRepository, SnapshotRepository, ChatRepository`
