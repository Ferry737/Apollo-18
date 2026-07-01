"""Downloaders — persist bars from providers into the Store.

READ-ONLY by construction: every provider only fetches historical OHLCV.
"""
from __future__ import annotations

import logging
from datetime import datetime

from ..core.models import Bar
from .store import Store

LOG = logging.getLogger(__name__)


def download_ccxt(
    store: Store,
    symbol: str,
    exchange: str = "binance",
    timeframe: str = "1d",
    limit: int = 1000,
    since: datetime | None = None,
) -> int:
    from .providers import ccxt_provider

    bars = ccxt_provider.fetch(
        symbol, exchange=exchange, timeframe=timeframe, limit=limit, since=since
    )
    return store.upsert_bars(symbol, bars)


def download_yfinance(
    store: Store,
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
    start: datetime | None = None,
    end: datetime | None = None,
) -> int:
    from .providers import yfinance_provider

    bars = yfinance_provider.fetch(
        symbol, period=period, interval=interval, start=start, end=end
    )
    return store.upsert_bars(symbol, bars)


def import_csv(store: Store, symbol: str, path: str) -> int:
    from .providers import csv_provider

    bars = csv_provider.fetch(symbol, path)
    return store.upsert_bars(symbol, bars)
