"""SQLite connection management, transactions and lazy initialization."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from .seed import seed_defaults

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def default_db_path() -> Path:
    """<project root>/db/finally.db (backend/app/db/connection.py -> parents[3])."""
    return Path(__file__).resolve().parents[3] / "db" / "finally.db"


class Database:
    """One shared connection guarded by a re-entrant lock."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = str(path) if path is not None else str(default_db_path())
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None
        self._depth = 0

    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            if self._path != ":memory:":
                Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                self._path, check_same_thread=False, isolation_level=None
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            if self._path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL")
            self._conn = conn
        return self._conn

    def initialize(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.executescript(_SCHEMA_PATH.read_text())
            with self.transaction():
                seed_defaults(self)

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self._lock:
            conn = self._connect()
            if self._depth > 0:
                self._depth += 1
                try:
                    yield
                finally:
                    self._depth -= 1
                return
            conn.execute("BEGIN IMMEDIATE")
            self._depth = 1
            try:
                yield
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
            finally:
                self._depth = 0

    def execute(self, sql: str, params: Sequence = ()) -> int:
        # isolation_level=None => autocommit unless inside our explicit BEGIN.
        with self._lock:
            return self._connect().execute(sql, params).rowcount

    def query(self, sql: str, params: Sequence = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._connect().execute(sql, params).fetchall()

    def query_one(self, sql: str, params: Sequence = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._connect().execute(sql, params).fetchone()
