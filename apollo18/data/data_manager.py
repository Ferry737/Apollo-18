"""
Apollo 18 — Data Layer
SQLite-embedded storage + market data ingestion via CCXT and yfinance.
No external database server required.
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np

from apollo18 import DATA_DIR
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = os.path.join(DATA_DIR, "apollo18.db")


class Database:
    """SQLite database wrapper with WAL mode for concurrent reads."""

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()

    def _connect(self):
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        logger.info(f"Database connected: {self.path}")

    def _init_schema(self):
        """Create all tables if not exists."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                UNIQUE(symbol, timeframe, timestamp)
            );

            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT (datetime('now')),
                performance TEXT,
                generation INTEGER DEFAULT 0,
                parent_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                total_return REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                win_rate REAL,
                total_trades INTEGER,
                equity_curve TEXT,
                FOREIGN KEY (strategy_id) REFERENCES strategies(id)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                entry_price REAL,
                exit_price REAL,
                entry_time TEXT,
                exit_time TEXT,
                quantity REAL,
                pnl REAL,
                status TEXT DEFAULT 'closed'
            );

            CREATE TABLE IF NOT EXISTS learning_cycles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cycle_number INTEGER NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                strategies_evaluated INTEGER,
                strategies_promoted INTEGER,
                strategies_retired INTEGER,
                best_sharpe REAL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS risk_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                timestamp TEXT DEFAULT (datetime('now')),
                resolved INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf ON ohlcv(symbol, timeframe, timestamp);
            CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
        """)
        self._conn.commit()
        logger.info("Database schema initialized")

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> list:
        cur = self._conn.execute(sql, params)
        return cur.fetchall()

    def query_df(self, sql: str, params: tuple = ()) -> pd.DataFrame:
        return pd.read_sql_query(sql, self._conn, params=params)

    def close(self):
        if self._conn:
            self._conn.close()
            logger.info("Database closed")


class MarketDataIngestor:
    """Fetches OHLCV data from free APIs. CCXT for crypto, yfinance for stocks."""

    def __init__(self, db: Database):
        self.db = db
        self._ccxt = None
        self._yf = None

    @property
    def ccxt(self):
        if self._ccxt is None:
            try:
                import ccxt
                self._ccxt = ccxt.binance({"enableRateLimit": True})
                logger.info("CCXT (Binance) initialized for crypto data")
            except ImportError:
                logger.warning("ccxt not installed — crypto data unavailable")
        return self._ccxt

    @property
    def yf(self):
        if self._yf is None:
            try:
                import yfinance
                self._yf = yfinance
                logger.info("yfinance initialized for stock data")
            except ImportError:
                logger.warning("yfinance not installed — stock data unavailable")
        return self._yf

    def fetch_crypto_ohlcv(
        self, symbol: str = "BTC/USDT", timeframe: str = "1d", limit: int = 500
    ) -> pd.DataFrame:
        """Fetch crypto OHLCV from Binance via CCXT."""
        if not self.ccxt:
            return pd.DataFrame()
        try:
            ohlcv = self.ccxt.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["symbol"] = symbol
            df["timeframe"] = timeframe
            self._store_ohlcv(df, symbol, timeframe)
            logger.info(f"Fetched {len(df)} bars of {symbol} {timeframe}")
            return df
        except Exception as e:
            logger.error(f"CCXT fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_stock_ohlcv(
        self, symbol: str = "AAPL", period: str = "1y"
    ) -> pd.DataFrame:
        """Fetch stock OHLCV from Yahoo Finance."""
        if not self.yf:
            return pd.DataFrame()
        try:
            ticker = self.yf.Ticker(symbol)
            df = ticker.history(period=period)
            df = df.reset_index()
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            df["symbol"] = symbol
            df["timeframe"] = "1d"
            df["timestamp"] = df["date"].astype(int) // 10**9
            df.rename(columns={"date": "datetime"}, inplace=True)
            self._store_ohlcv(df, symbol, "1d")
            logger.info(f"Fetched {len(df)} bars of {symbol}")
            return df
        except Exception as e:
            logger.error(f"yfinance fetch failed for {symbol}: {e}")
            return pd.DataFrame()

    def _store_ohlcv(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Bulk insert OHLCV into database with conflict resolution."""
        records = []
        for _, row in df.iterrows():
            records.append(
                (symbol, timeframe, int(row["timestamp"]),
                 row.get("open"), row.get("high"), row.get("low"),
                 row.get("close"), row.get("volume"))
            )
        self.db.conn.executemany(
            """INSERT OR REPLACE INTO ohlcv
               (symbol, timeframe, timestamp, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        self.db.conn.commit()

    def get_stored_data(
        self, symbol: str, timeframe: str = "1d", limit: int = 500
    ) -> pd.DataFrame:
        """Retrieve stored OHLCV data as DataFrame."""
        df = self.db.query_df(
            """SELECT * FROM ohlcv
               WHERE symbol = ? AND timeframe = ?
               ORDER BY timestamp DESC LIMIT ?""",
            (symbol, timeframe, limit)
        )
        if df.empty:
            return df
        df = df.sort_values("timestamp")
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        return df

    def generate_synthetic_data(
        self, symbol: str = "SYNTH", days: int = 500, start_price: float = 50000
    ) -> pd.DataFrame:
        """Generate synthetic OHLCV data for offline testing (geometric Brownian motion)."""
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, days)
        prices = [start_price]
        for r in returns[1:]:
            prices.append(prices[-1] * (1 + r))

        timestamps = []
        base = datetime(2024, 1, 1)
        for i in range(days):
            ts = base + timedelta(days=i)
            timestamps.append(int(ts.timestamp()))

        records = []
        for i, (ts, close) in enumerate(zip(timestamps, prices)):
            noise = np.random.uniform(0.995, 1.005)
            open_p = prices[i - 1] if i > 0 else close * noise
            high = max(open_p, close) * np.random.uniform(1.0, 1.01)
            low = min(open_p, close) * np.random.uniform(0.99, 1.0)
            vol = np.random.uniform(100, 10000)
            records.append(
                (symbol, "1d", ts, open_p, high, low, close, vol)
            )

        self.db.conn.executemany(
            """INSERT OR REPLACE INTO ohlcv
               (symbol, timeframe, timestamp, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            records
        )
        self.db.conn.commit()
        logger.info(f"Generated {days} bars of synthetic data for {symbol}")
        return self.get_stored_data(symbol, "1d", days)
