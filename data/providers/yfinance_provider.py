"""yfinance provider — READ-ONLY historical OHLCV for equities/ETFs.

Public data only; no authentication. Optional dependency.
"""
from __future__ import annotations

import logging
from datetime import datetime

from ...core.models import Bar

LOG = logging.getLogger(__name__)


def fetch(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[Bar]:
    """Fetch historical OHLCV from Yahoo Finance (read-only)."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "yfinance is not installed. Install with: pip install yfinance"
        ) from exc

    kwargs: dict[str, object] = {"interval": interval, "auto_adjust": False}
    if start is not None and end is not None:
        kwargs["start"] = start.strftime("%Y-%m-%d")
        kwargs["end"] = end.strftime("%Y-%m-%d")
    else:
        kwargs["period"] = period

    df = yf.download(symbol, **kwargs, progress=False)  # type: ignore[arg-type]
    if df is None or df.empty:  # type: ignore[union-attr]
        return []
    bars: list[Bar] = []
    for ts, row in df.iterrows():  # type: ignore[union-attr]
        try:
            bars.append(
                Bar(
                    ts=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row.get("Volume") or 0.0),
                )
            )
        except Exception as exc:  # noqa: BLE001
            LOG.warning("Skipping row %s: %s", ts, exc)
    LOG.info("Fetched %d %s bars for %s", len(bars), interval, symbol)
    return bars
