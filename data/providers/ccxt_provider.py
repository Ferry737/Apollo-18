"""CCXT provider — READ-ONLY historical OHLCV from crypto exchanges.

Uses ``ccxt.fetch_ohlcv`` which is a public, unauthenticated endpoint. No API
keys are required and no order is ever placed. Optional dependency: importable
only if ccxt is installed.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ...core.models import Bar

LOG = logging.getLogger(__name__)


def fetch(
    symbol: str,
    exchange: str = "binance",
    timeframe: str = "1d",
    limit: int = 1000,
    since: datetime | None = None,
) -> list[Bar]:
    """Fetch historical OHLCV from a crypto exchange (read-only)."""
    try:
        import ccxt  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "ccxt is not installed. Install with: pip install ccxt"
        ) from exc

    ex: Any = getattr(ccxt, exchange)({"enableRateLimit": True})
    since_ms = int(since.timestamp() * 1000) if since else None
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
    bars: list[Bar] = []
    for ts_ms, o, h, l, c, v in raw:
        bars.append(
            Bar(
                ts=datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v or 0.0),
            )
        )
    LOG.info("Fetched %d %s bars for %s from %s", len(bars), timeframe, symbol, exchange)
    return bars
