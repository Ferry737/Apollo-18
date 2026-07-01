"""Enumerations used across the app."""
from __future__ import annotations

from enum import Enum


class Side(str, Enum):
    """Direction of a trade."""

    LONG = "long"
    FLAT = "flat"
    SHORT = "short"


class OrderType(str, Enum):
    """Order kinds the simulated broker understands."""

    MARKET = "market"


class RunMode(str, Enum):
    """Execution context for the app."""

    PAPER = "paper"   # MVP: simulated fills only
    LIVE = "live"     # reserved for Phase 3 (off by default); not used in MVP
