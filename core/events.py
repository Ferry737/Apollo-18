"""Event bus — a tiny in-process pub/sub used to decouple the engine from the UI.

The backtest engine publishes progress events; UI widgets subscribe. Kept
deliberately simple (synchronous callbacks). For Qt, the UI marshals updates to
the main thread via signals; this bus just delivers the payloads.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .enums import Side


@dataclass
class ProgressEvent:
    """Published as a backtest runs."""

    done: int
    total: int
    ts: datetime
    equity: float


@dataclass
class TradeEvent:
    """Published when a simulated fill occurs."""

    ts: datetime
    symbol: str
    side: Side
    qty: float
    price: float


@dataclass
class HaltEvent:
    """Published when a circuit breaker trips."""

    ts: datetime
    reason: str


Handler = Callable[[Any], None]


class EventBus:
    """Minimal synchronous event bus keyed by event type."""

    def __init__(self) -> None:
        self._subs: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._subs[event_type].append(handler)

    def publish(self, event: Any) -> None:
        for handler in list(self._subs.get(type(event), [])):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 — a UI handler error must not kill the engine
                pass
