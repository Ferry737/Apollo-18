"""
Apollo 18 — Risk Management Module
Circuit breakers, position limits, drawdown protection.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskLimits:
    """Configurable risk limits."""
    max_position_pct: float = 0.20        # Max 20% capital in single asset
    max_portfolio_drawdown_daily: float = 0.10   # 10% daily DD → circuit breaker
    max_portfolio_drawdown_monthly: float = 0.20 # 20% monthly DD → circuit breaker
    max_concentration: float = 0.15       # No single asset > 15% of capital
    max_leverage: float = 1.0             # No leverage by default
    min_cash_reserve: float = 0.05        # Keep 5% in cash
    max_open_positions: int = 10
    stop_loss_pct: float = 0.05           # 5% stop loss per position
    daily_loss_limit: float = 0.03        # 3% daily loss → halt


@dataclass
class RiskEvent:
    """Recorded risk event."""
    event_type: str
    severity: str  # "info", "warning", "critical"
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False


class RiskManager:
    """
    Enforces risk limits and triggers circuit breakers.
    Monitors portfolio in real-time.
    """

    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.events: list[RiskEvent] = []
        self.halted = False
        self._daily_pnl = 0.0
        self._peak_equity = 0.0
        self._current_drawdown = 0.0

    def check_position_size(
        self, symbol: str, position_value: float, total_equity: float
    ) -> tuple[bool, str]:
        """Validate if a position size is within limits."""
        if self.halted:
            return False, "Trading halted — circuit breaker active"

        pct = position_value / total_equity if total_equity > 0 else 0

        if pct > self.limits.max_position_pct:
            return False, f"Position {symbol}: {pct:.1%} exceeds max {self.limits.max_position_pct:.1%}"

        if pct > self.limits.max_concentration:
            return False, f"Concentration {symbol}: {pct:.1%} exceeds max {self.limits.max_concentration:.1%}"

        return True, "OK"

    def update_equity(self, current_equity: float) -> Optional[RiskEvent]:
        """Track equity and detect drawdown breaches."""
        if current_equity > self._peak_equity:
            self._peak_equity = current_equity

        if self._peak_equity > 0:
            self._current_drawdown = (self._peak_equity - current_equity) / self._peak_equity

        # Circuit breaker: daily drawdown
        if self._current_drawdown >= self.limits.max_portfolio_drawdown_daily:
            event = RiskEvent(
                event_type="circuit_breaker",
                severity="critical",
                message=f"Daily drawdown circuit breaker triggered: {self._current_drawdown:.2%} >= {self.limits.max_portfolio_drawdown_daily:.2%}",
            )
            self.events.append(event)
            self.halted = True
            logger.critical(event.message)
            return event

        # Warning zone
        if self._current_drawdown >= self.limits.max_portfolio_drawdown_daily * 0.7:
            event = RiskEvent(
                event_type="drawdown_warning",
                severity="warning",
                message=f"Drawdown approaching limit: {self._current_drawdown:.2%}",
            )
            self.events.append(event)
            logger.warning(event.message)
            return event

        return None

    def check_daily_pnl(self, pnl: float, equity: float) -> Optional[RiskEvent]:
        """Check if daily loss limit is breached."""
        self._daily_pnl += pnl
        loss_pct = abs(min(0, self._daily_pnl)) / equity if equity > 0 else 0

        if loss_pct >= self.limits.daily_loss_limit:
            event = RiskEvent(
                event_type="daily_loss_limit",
                severity="critical",
                message=f"Daily loss limit breached: {loss_pct:.2%} >= {self.limits.daily_loss_limit:.2%}",
            )
            self.events.append(event)
            self.halted = True
            logger.critical(event.message)
            return event

        return None

    def reset_daily(self):
        """Reset daily counters (call at start of each trading day)."""
        self._daily_pnl = 0.0
        logger.info("Risk manager daily counters reset")

    def force_halt(self, reason: str = "Manual halt"):
        """Manually trigger trading halt."""
        self.halted = True
        event = RiskEvent(
            event_type="manual_halt",
            severity="critical",
            message=reason,
        )
        self.events.append(event)
        logger.critical(reason)

    def resume(self):
        """Resume trading after halt."""
        self.halted = False
        self._daily_pnl = 0.0
        logger.info("Trading resumed — circuit breaker cleared")

    @property
    def status(self) -> dict:
        return {
            "halted": self.halted,
            "current_drawdown": round(self._current_drawdown, 4),
            "peak_equity": round(self._peak_equity, 2),
            "daily_pnl": round(self._daily_pnl, 2),
            "total_events": len(self.events),
            "unresolved_events": len([e for e in self.events if not e.resolved]),
        }
