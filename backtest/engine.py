"""Event-driven backtest engine.

Iterates bars chronologically; for each bar:
1. ask the strategy for a target weight,
2. rebalance via the (simulated) broker,
3. mark the portfolio to market,
4. publish progress + trade events,
5. check risk circuit breakers.

The engine is agnostic of any strategy, provider, or UI — it speaks only the
core value objects and the event bus.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

import numpy as np

from ..core.events import EventBus, ProgressEvent, TradeEvent
from ..core.models import BacktestResult, Bar
from ..strategy.base import Strategy
from .broker import SimulatedBroker
from .portfolio import Portfolio

LOG = logging.getLogger(__name__)

ProgressCb = Callable[[int, int], None]


@dataclass
class EngineConfig:
    initial_capital: float = 100000.0
    fee_bps: float = 5.0
    slippage_bps: float = 2.0
    daily_dd_halt_pct: float = 10.0
    monthly_dd_halt_pct: float = 20.0
    max_position_pct: float = 100.0  # MVP single-symbol; allow full allocation


class Engine:
    """Runs a strategy over a bar series and returns a :class:`BacktestResult`."""

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        bus: Optional[EventBus] = None,
    ) -> None:
        self.config = config or EngineConfig()
        self.broker = SimulatedBroker(
            fee_bps=self.config.fee_bps, slippage_bps=self.config.slippage_bps
        )
        self.bus = bus or EventBus()

    def run(
        self,
        strategy: Strategy,
        symbol: str,
        bars: list[Bar],
        progress_cb: Optional[ProgressCb] = None,
    ) -> BacktestResult:
        """Run ``strategy`` over ``bars`` and return results."""
        if not bars:
            return BacktestResult(symbol=symbol, initial_capital=self.config.initial_capital)

        strategy.reset()
        portfolio = Portfolio(initial_capital=self.config.initial_capital)
        result = BacktestResult(symbol=symbol, initial_capital=self.config.initial_capital)
        n = len(bars)

        # track a rolling window of equity for the monthly drawdown proxy
        month_window: list[float] = []
        day_start_equity = portfolio.equity
        peak_for_month = portfolio.equity
        last_month = bars[0].ts.month

        for i, bar in enumerate(bars):
            # 1. strategy decides target weight (clamped + position cap)
            try:
                target = float(strategy.on_bar(i, bar))
            except Exception as exc:  # noqa: BLE001 — a strategy bug must not abort
                LOG.warning("Strategy %s raised on bar %d: %s", strategy.name, i, exc)
                target = 0.0
            target = max(-1.0, min(1.0, target))
            cap = self.config.max_position_pct / 100.0
            target = max(-cap, min(cap, target))

            # 2. rebalance -> fill
            trade = self.broker.rebalance(symbol, target, bar, portfolio)
            if trade is not None:
                result.trades.append(trade)
                self.bus.publish(
                    TradeEvent(
                        ts=trade.ts, symbol=trade.symbol, side=trade.side,
                        qty=trade.qty, price=trade.price,
                    )
                )

            # 3. mark to market
            equity = portfolio.mark_to_market(symbol, bar.close, bar.ts)

            # 4. progress
            if progress_cb is not None and (i % max(1, n // 100) == 0 or i == n - 1):
                progress_cb(i + 1, n)
            self.bus.publish(
                ProgressEvent(done=i + 1, total=n, ts=bar.ts, equity=equity)
            )

            # 5. circuit breakers (monthly rollover bookkeeping first)
            if bar.ts.month != last_month:
                last_month = bar.ts.month
                month_window = []
                peak_for_month = equity
                day_start_equity = equity
            # daily drawdown: from the day's starting equity
            if bar.ts.date() != bars[max(0, i - 1)].ts.date():
                day_start_equity = portfolio.equity_curve[-2].equity if len(portfolio.equity_curve) >= 2 else day_start_equity
            peak_for_month = max(peak_for_month, equity)

            daily_dd = 0.0
            if day_start_equity > 0:
                daily_dd = (day_start_equity - equity) / day_start_equity * 100.0
            monthly_dd = 0.0
            if peak_for_month > 0:
                monthly_dd = (peak_for_month - equity) / peak_for_month * 100.0

            if daily_dd >= self.config.daily_dd_halt_pct:
                result.halted = True
                result.halt_reason = f"daily drawdown {daily_dd:.1f}% >= {self.config.daily_dd_halt_pct}%"
                break
            if monthly_dd >= self.config.monthly_dd_halt_pct:
                result.halted = True
                result.halt_reason = f"monthly drawdown {monthly_dd:.1f}% >= {self.config.monthly_dd_halt_pct}%"
                break

        result.equity_curve = portfolio.equity_curve
        result.trades = portfolio.trades
        result.final_equity = portfolio.equity
        return result


def run_backtest(
    strategy: Strategy,
    symbol: str,
    bars: list[Bar],
    config: Optional[EngineConfig] = None,
    progress_cb: Optional[ProgressCb] = None,
) -> BacktestResult:
    """Convenience wrapper: create an engine and run once."""
    return Engine(config=config).run(strategy, symbol, bars, progress_cb=progress_cb)
