"""Historical feed — the single read API the backtester uses.

Pulls bars from the Store (offline). If the Store is empty for a symbol, the
caller is expected to have downloaded them first (see ``downloader.download``).
"""
from __future__ import annotations

import logging
from datetime import datetime

from ..core.models import Bar
from .store import Store

LOG = logging.getLogger(__name__)


class HistoricalFeed:
    """Chronological bar iterator backed by the SQLite store."""

    def __init__(self, store: Store) -> None:
        self.store = store

    def get_bars(
        self, symbol: str, start: datetime | None = None, end: datetime | None = None
    ) -> list[Bar]:
        bars = self.store.load_bars(symbol, start=start, end=end)
        if not bars:
            LOG.warning("No bars stored for %s — download data first.", symbol)
        return bars
