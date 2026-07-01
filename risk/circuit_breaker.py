"""Circuit breaker — enforces hard drawdown limits.

The engine already checks drawdown on each bar and halts the run. This class is
the reusable, testable rule: feed it the current equity and peak and it tells
you whether to trip. Mirrors the PDF's risk guardrails (10% daily / 20% monthly
drawdown -> halt), kept configurable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CircuitBreaker:
    daily_dd_halt_pct: float = 10.0
    monthly_dd_halt_pct: float = 20.0

    def should_trip(
        self, daily_dd_pct: float, monthly_dd_pct: float
    ) -> tuple[bool, str | None]:
        """Return (tripped, reason)."""
        if daily_dd_pct >= self.daily_dd_halt_pct:
            return True, f"daily drawdown {daily_dd_pct:.1f}% >= {self.daily_dd_halt_pct}%"
        if monthly_dd_pct >= self.monthly_dd_halt_pct:
            return True, f"monthly drawdown {monthly_dd_pct:.1f}% >= {self.monthly_dd_halt_pct}%"
        return False, None
