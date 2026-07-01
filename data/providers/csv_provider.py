"""CSV provider — offline import of historical OHLCV bars.

Supports a header row containing (case-insensitive) any of: ts/time/date/datetime,
open, high, low, close, volume. Timestamps may be ISO-8601 strings or unix
seconds. This is the guaranteed-offline path so the app runs with no network.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ...core.models import Bar

LOG = logging.getLogger(__name__)


def _parse_ts(raw: str) -> datetime:
    raw = raw.strip()
    if not raw:
        raise ValueError("empty timestamp")
    # numeric unix seconds?
    try:
        return datetime.fromtimestamp(float(raw), tz=timezone.utc).replace(tzinfo=None)
    except ValueError:
        pass
    # ISO-8601; tolerate trailing Z
    s = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _norm_header(h: str) -> str:
    return h.strip().lower()


def load_csv(path: Path | str) -> Iterator[Bar]:
    """Yield Bar objects from a CSV file. Rows with bad data are skipped+logged."""
    path = Path(path)
    required = {"open", "high", "low", "close"}
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = {_norm_header(h): _norm_header(h) for h in (reader.fieldnames or [])}
        ts_key = next(
            (h for h in headers if h in ("ts", "time", "date", "datetime", "timestamp")), None
        )
        if ts_key is None:
            raise ValueError(f"{path}: no timestamp column found")
        missing = required - set(headers)
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        for i, row in enumerate(reader, start=2):
            try:
                ts = _parse_ts(row[ts_key] or "")
                bar = Bar(
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0.0),
                )
            except Exception as exc:  # noqa: BLE001
                LOG.warning("Skipping row %d in %s: %s", i, path.name, exc)
                continue
            yield bar


def fetch(symbol: str, path: Path | str) -> list[Bar]:
    """Convenience: load a CSV into a list of Bar (symbol tag ignored)."""
    return list(load_csv(path))
