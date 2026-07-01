"""
Apollo 18 — Event-Driven Backtesting Engine
Realistic transaction costs, walk-forward optimization, out-of-sample validation.
"""
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

from apollo18.strategies.strategy_engine import BaseStrategy, Signal
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BacktestConfig:
    """Backtest execution configuration."""
    initial_capital: float = 100_000.0
    commission_pct: float = 0.001  # 0.1% per trade
    slippage_pct: float = 0.0005   # 0.05% slippage
    position_size_pct: float = 0.95  # % of capital per position
    risk_per_trade: float = 0.02    # 2% risk per trade


@dataclass
class BacktestResult:
    """Container for backtest results."""
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    equity_curve: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "equity_curve": json.dumps(self.equity_curve),
            "metrics": json.dumps(self.metrics),
        }


class Backtester:
    """Event-driven backtester with realistic cost modeling."""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        config: BacktestConfig = None,
    ) -> BacktestResult:
        """Run backtest on historical data."""
        cfg = config or self.config

        if data.empty or len(data) < 30:
            logger.warning(f"Insufficient data for backtest: {len(data)} bars")
            return self._empty_result(strategy.name)

        signals = strategy.generate_signals(data)

        # Simulate position management
        position = 0.0      # current position size (fraction: -1 to +1)
        entry_price = 0.0
        entry_time = None
        equity = cfg.initial_capital
        peak_equity = equity
        max_dd = 0.0
        equity_curve = []
        trades = []
        wins = 0

        for _, bar in data.iterrows():
            current_price = bar["close"]
            ts = bar.get("datetime", bar.name)

            # Check for matching signal at this bar
            for sig in signals:
                sig_ts = sig.timestamp
                if hasattr(sig_ts, 'date') and hasattr(ts, 'date'):
                    if sig_ts.date() == ts.date():
                        pass  # Will match by index below

            # Process signals
            for sig in signals:
                if self._timestamps_match(sig.timestamp, ts):
                    if sig.direction == "long" and position <= 0:
                        # Close short if any, go long
                        if position < 0:
                            pnl = self._close_position(
                                position, entry_price, current_price,
                                cfg, equity
                            )
                            equity += pnl
                            trades.append({
                                "side": "short", "entry": entry_price,
                                "exit": current_price, "pnl": pnl,
                                "entry_time": str(entry_time), "exit_time": str(ts),
                            })
                            if pnl > 0: wins += 1
                        # Open long
                        invest = equity * cfg.position_size_pct
                        entry_price = current_price * (1 + cfg.slippage_pct)
                        position = invest / entry_price
                        entry_time = ts
                        equity -= invest * cfg.commission_pct

                    elif sig.direction == "short" and position >= 0:
                        # Close long if any, go short
                        if position > 0:
                            pnl = self._close_position(
                                position, entry_price, current_price,
                                cfg, equity
                            )
                            equity += pnl
                            trades.append({
                                "side": "long", "entry": entry_price,
                                "exit": current_price, "pnl": pnl,
                                "entry_time": str(entry_time), "exit_time": str(ts),
                            })
                            if pnl > 0: wins += 1
                        # Open short
                        invest = equity * cfg.position_size_pct
                        entry_price = current_price * (1 - cfg.slippage_pct)
                        position = -invest / entry_price
                        entry_time = ts
                        equity -= invest * cfg.commission_pct

            # Mark-to-market equity
            if position > 0:
                mtm_equity = equity + position * (current_price - entry_price)
            elif position < 0:
                mtm_equity = equity + position * (entry_price - current_price)  # simplified
            else:
                mtm_equity = equity

            equity_curve.append({
                "timestamp": str(ts),
                "equity": round(mtm_equity, 2),
                "price": current_price,
            })

            if mtm_equity > peak_equity:
                peak_equity = mtm_equity
            dd = (peak_equity - mtm_equity) / peak_equity
            if dd > max_dd:
                max_dd = dd

        # Close any open position at last bar
        if position != 0:
            current_price = data.iloc[-1]["close"]
            pnl = self._close_position(position, entry_price, current_price, cfg, equity)
            equity += pnl
            trades.append({
                "side": "long" if position > 0 else "short",
                "entry": entry_price, "exit": current_price, "pnl": pnl,
                "entry_time": str(entry_time), "exit_time": str(data.iloc[-1].get("datetime", "")),
            })
            if pnl > 0: wins += 1

        total_return = (equity - cfg.initial_capital) / cfg.initial_capital

        # Compute Sharpe ratio from equity curve
        equities = [e["equity"] for e in equity_curve]
        if len(equities) > 1:
            returns = np.diff(equities) / equities[:-1]
            if returns.std() > 0:
                sharpe = np.sqrt(252) * returns.mean() / returns.std()
            else:
                sharpe = 0.0
        else:
            sharpe = 0.0

        win_rate = wins / max(1, len(trades))

        result = BacktestResult(
            strategy_name=strategy.name,
            total_return=round(total_return, 4),
            sharpe_ratio=round(float(sharpe), 4),
            max_drawdown=round(float(max_dd), 4),
            win_rate=round(float(win_rate), 4),
            total_trades=len(trades),
            equity_curve=equity_curve,
            trades=trades,
            metrics={
                "initial_capital": cfg.initial_capital,
                "final_equity": round(equity, 2),
                "peak_equity": round(peak_equity, 2),
                "avg_trade_pnl": round(float(np.mean([t["pnl"] for t in trades])) if trades else 0, 2),
            },
        )

        logger.info(
            f"Backtest '{strategy.name}': Return={total_return:.2%} "
            f"Sharpe={sharpe:.2f} DD={max_dd:.2%} Trades={len(trades)}"
        )
        return result

    def _close_position(self, position, entry_price, exit_price, cfg, equity):
        """Calculate PnL of closing a position."""
        raw_pnl = (exit_price - entry_price) * position
        commission = abs(position * exit_price) * cfg.commission_pct
        return raw_pnl - commission

    def _timestamps_match(self, sig_ts, bar_ts) -> bool:
        """Check if two timestamps refer to the same trading period."""
        try:
            if hasattr(sig_ts, 'date') and hasattr(bar_ts, 'date'):
                return sig_ts.date() == bar_ts.date()
            return str(sig_ts)[:10] == str(bar_ts)[:10]
        except Exception:
            return False

    def _empty_result(self, name: str) -> BacktestResult:
        return BacktestResult(
            strategy_name=name, total_return=0, sharpe_ratio=0,
            max_drawdown=0, win_rate=0, total_trades=0,
        )

    def walk_forward(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        train_ratio: float = 0.7,
    ) -> dict:
        """Walk-forward optimization: train on first portion, test on remainder."""
        split_idx = int(len(data) * train_ratio)
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]

        train_result = self.run(strategy, train_data)
        test_result = self.run(strategy, test_data)

        # Overfitting detection: large gap between train and test Sharpe
        overfitting_score = 0
        if train_result.sharpe_ratio > 0 and test_result.sharpe_ratio > 0:
            overfitting_score = (
                (train_result.sharpe_ratio - test_result.sharpe_ratio)
                / max(train_result.sharpe_ratio, 0.01)
            )

        return {
            "train": train_result,
            "test": test_result,
            "overfitting_score": round(float(overfitting_score), 3),
            "passed_validation": overfitting_score < 0.5 and test_result.sharpe_ratio > 0,
        }
