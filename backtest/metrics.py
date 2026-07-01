"""Performance metrics — turns a BacktestResult into the KPI numbers.

All annualisation uses ``annualization`` periods (365 for crypto/24-7, 252 for
equities). Implemented as pure functions over numpy arrays so they are trivial
to test and reuse in the Monte Carlo / optimizer modules.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.models import BacktestResult


def _returns(equity: np.ndarray) -> np.ndarray:
    """Period returns from an equity curve. Returns at least one 0.0 for safety."""
    if equity.size < 2:
        return np.zeros(1)
    rets = np.diff(equity) / equity[:-1]
    rets = np.where(np.isfinite(rets), rets, 0.0)
    return rets


@dataclass
class Metrics:
    total_return_pct: float
    cagr_pct: float
    volatility_annualized_pct: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    n_trades: int
    n_periods: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "total_return_pct": self.total_return_pct,
            "cagr_pct": self.cagr_pct,
            "volatility_annualized_pct": self.volatility_annualized_pct,
            "sharpe": self.sharpe,
            "sortino": self.sortino,
            "calmar": self.calmar,
            "max_drawdown_pct": self.max_drawdown_pct,
            "win_rate_pct": self.win_rate_pct,
            "profit_factor": self.profit_factor,
            "n_trades": self.n_trades,
            "n_periods": self.n_periods,
        }


def _drawdown(equity: np.ndarray) -> tuple[float, np.ndarray]:
    """Max drawdown % and the per-point drawdown series."""
    if equity.size == 0:
        return 0.0, np.zeros(0)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.where(peak > 0, peak, 1.0)
    return float(np.max(dd) * 100.0), dd


def _trade_pnl(result: BacktestResult) -> np.ndarray:
    """Realized PnL per trade (lot accounting done in Portfolio.apply_trade).

    Trades that only open or add to a position realize ~0; trades that close
    lots realize (fill_price - avg_cost) * lots_closed. This is what makes
    win-rate and profit-factor meaningful.
    """
    if not result.trades:
        return np.zeros(0)
    return np.array([float(t.realized_pnl) for t in result.trades], dtype=float)


def compute_metrics(
    result: BacktestResult, annualization: int = 365, risk_free: float = 0.0
) -> Metrics:
    """Compute the full metric suite for a backtest result."""
    equity = result.equity_series
    n_periods = int(equity.size)
    if n_periods < 2:
        zero = Metrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, n_periods)
        return zero

    rets = _returns(equity)
    ann = float(annualization)

    total_return_pct = (equity[-1] / equity[0] - 1.0) * 100.0 if equity[0] > 0 else 0.0
    years = max(n_periods / ann, 1e-9)
    cagr_pct = ((equity[-1] / equity[0]) ** (1.0 / years) - 1.0) * 100.0 if equity[0] > 0 else 0.0

    mean_r = float(np.mean(rets))
    std_r = float(np.std(rets, ddof=1)) if rets.size > 1 else 0.0
    vol_annual = std_r * np.sqrt(ann) * 100.0

    rf_per = risk_free / ann
    excess = rets - rf_per
    sharpe = (mean_r - rf_per) / std_r * np.sqrt(ann) if std_r > 1e-12 else 0.0

    downside = rets[rets < 0]
    dd_std = float(np.std(downside, ddof=1)) if downside.size > 1 else 0.0
    sortino = (mean_r - rf_per) / dd_std * np.sqrt(ann) if dd_std > 1e-12 else 0.0

    max_dd, _ = _drawdown(equity)
    calmar = cagr_pct / max_dd if max_dd > 1e-9 else 0.0

    pnl = _trade_pnl(result)
    n_trades = int(pnl.size)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    win_rate = (wins.size / n_trades * 100.0) if n_trades else 0.0
    gross_profit = float(wins.sum()) if wins.size else 0.0
    gross_loss = float(abs(losses.sum())) if losses.size else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 1e-12 else float("inf")

    return Metrics(
        total_return_pct=total_return_pct,
        cagr_pct=cagr_pct,
        volatility_annualized_pct=vol_annual,
        sharpe=float(sharpe),
        sortino=float(sortino),
        calmar=float(calmar),
        max_drawdown_pct=float(max_dd),
        win_rate_pct=float(win_rate),
        profit_factor=float(profit_factor),
        n_trades=n_trades,
        n_periods=n_periods,
    )
