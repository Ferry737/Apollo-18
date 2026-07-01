"""SMA-crossover strategy.

Long when the fast simple moving average is above the slow one, flat otherwise
(no shorts in the MVP — keep the risk surface small). Classic first strategy:
trend-following, easy to reason about, and a good baseline for the
self-improvement loop to mutate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.models import Bar
from .base import Strategy


@dataclass
class SmaCross(Strategy):
    fast: int = 20
    slow: int = 50
    allow_short: bool = False
    name: str = "sma_cross"

    def __post_init__(self) -> None:
        if self.fast >= self.slow:
            raise ValueError("fast window must be < slow window")
        if self.fast < 1:
            raise ValueError("fast window must be >= 1")
        self._closes: list[float] = []

    def reset(self) -> None:
        self._closes = []

    def on_bar(self, i: int, bar: Bar) -> float:
        self._closes.append(bar.close)
        if len(self._closes) < self.slow:
            return 0.0
        window = self._closes[-self.slow:]
        slow_sma = sum(window) / self.slow
        fast_sma = sum(self._closes[-self.fast:]) / self.fast
        if fast_sma > slow_sma:
            return 1.0
        if self.allow_short and fast_sma < slow_sma:
            return -1.0
        return 0.0

    def params(self) -> dict[str, object]:
        return {"name": self.name, "fast": self.fast, "slow": self.slow, "allow_short": self.allow_short}
