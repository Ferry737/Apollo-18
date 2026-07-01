"""Core value objects: Bar, Signal, Trade, Position, EquityPoint."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np

from .enums import Side


@dataclass(frozen=True)
class Bar:
    """A single OHLCV bar."""

    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        # Lightweight sanity check; raises on obviously bad data.
        for name in ("open", "high", "low", "close"):
            v = getattr(self, name)
            if not np.isfinite(v):
                raise ValueError(f"Bar {name} is not finite: {v}")
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise ValueError(f"Inconsistent OHLC for bar @ {self.ts}")


@dataclass(frozen=True)
class Signal:
    """A strategy's desired position for a symbol at a point in time.

    The strategy layer emits target exposures as fractions of capital in
    [-1, 1]; the broker turns them into fills. Decoupling target-vs-fill keeps
    the backtest realistic (slippage/fees) and the strategy simple.
    """

    ts: datetime
    symbol: str
    target_weight: float  # -1.0 .. 1.0 of capital

    @property
    def side(self) -> Side:
        if self.target_weight > 1e-9:
            return Side.LONG
        if self.target_weight < -1e-9:
            return Side.SHORT
        return Side.FLAT


@dataclass
class Trade:
    """A (simulated) executed fill."""

    ts: datetime
    symbol: str
    side: Side
    qty: float
    price: float
    fee: float = 0.0
    slippage: float = 0.0
    realized_pnl: float = 0.0   # set by the portfolio when a trade closes lots

    @property
    def notional(self) -> float:
        return self.qty * self.price


@dataclass
class Position:
    """Mark-to-market position for a symbol."""

    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0

    def update_on_fill(self, trade: Trade) -> None:
        """Roll the position average on a new fill."""
        if trade.side == Side.LONG:
            new_qty = self.qty + trade.qty
            if abs(new_qty) < 1e-12:
                self.avg_price = 0.0
            else:
                self.avg_price = (
                    self.avg_price * self.qty + trade.price * trade.qty
                ) / new_qty if (self.qty + trade.qty) != 0 else 0.0
            self.qty = new_qty
        elif trade.side == Side.SHORT:
            new_qty = self.qty - trade.qty
            self.avg_price = 0.0 if abs(new_qty) < 1e-12 else self.avg_price
            self.qty = new_qty
        # FLAT handled by the broker via an offsetting fill


@dataclass
class EquityPoint:
    """One row of the equity curve."""

    ts: datetime
    equity: float
    cash: float
    positions_value: float


@dataclass
class BacktestResult:
    """Everything a backtest produces, consumed by metrics + the UI."""

    symbol: str
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
    halted: bool = False
    halt_reason: Optional[str] = None
    final_equity: float = 0.0
    initial_capital: float = 0.0

    @property
    def equity_series(self) -> np.ndarray:
        return np.array([p.equity for p in self.equity_curve], dtype=float)

    @property
    def timestamps(self) -> list[datetime]:
        return [p.ts for p in self.equity_curve]
