"""SQLite data-access layer for OHLCV bars.

One connection with WAL mode; parameterized queries only. The schema is created
on first open. Idempotent upserts so re-downloading a range is safe.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..core.models import Bar

LOG = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL,
    ts     INTEGER NOT NULL,   -- unix seconds
    open   REAL NOT NULL,
    high   REAL NOT NULL,
    low    REAL NOT NULL,
    close  REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (symbol, ts)
);
CREATE INDEX IF NOT EXISTS idx_bars_symbol_ts ON bars(symbol, ts);
"""


class Store:
    """Thin SQLite accessor for bars."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        LOG.info("Opened store at %s", self.path)

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # pragma: no cover
            pass

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------------------------------------------------------------- writes
    def upsert_bars(self, symbol: str, bars: Iterable[Bar]) -> int:
        rows = [
            (symbol, int(b.ts.timestamp()), b.open, b.high, b.low, b.close, b.volume)
            for b in bars
        ]
        if not rows:
            return 0
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO bars(symbol,ts,open,high,low,close,volume) "
                "VALUES(?,?,?,?,?,?,?)",
                rows,
            )
        return len(rows)

    # ----------------------------------------------------------------- reads
    def load_bars(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None
    ) -> list[Bar]:
        query = "SELECT ts,open,high,low,close,volume FROM bars WHERE symbol=?"
        params: list[object] = [symbol]
        if start is not None:
            query += " AND ts>=?"
            params.append(int(start.timestamp()))
        if end is not None:
            query += " AND ts<=?"
            params.append(int(end.timestamp()))
        query += " ORDER BY ts ASC"
        cur = self.conn.execute(query, params)
        out: list[Bar] = []
        for ts, o, h, l, c, v in cur.fetchall():
            out.append(
                Bar(ts=datetime.utcfromtimestamp(ts), open=o, high=h, low=l, close=c, volume=v)
            )
        return out

    def symbols(self) -> list[str]:
        cur = self.conn.execute("SELECT DISTINCT symbol FROM bars ORDER BY symbol")
        return [r[0] for r in cur.fetchall()]

    def bar_count(self, symbol: str | None = None) -> int:
        if symbol:
            cur = self.conn.execute("SELECT COUNT(*) FROM bars WHERE symbol=?", (symbol,))
        else:
            cur = self.conn.execute("SELECT COUNT(*) FROM bars")
        return int(cur.fetchone()[0])
