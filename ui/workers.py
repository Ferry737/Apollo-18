"""Workers — run expensive work off the UI thread.

Qt rule: only the main thread may touch widgets. These QObjects live on a
QThread; they emit signals carrying plain Python payloads, and the main window
updates widgets inside the signal slots. No widget is referenced from here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PySide6.QtCore import QObject, Signal

from ..backtest.engine import Engine, EngineConfig
from ..backtest.metrics import Metrics, compute_metrics
from ..core.models import BacktestResult
from ..improve.optimizer import OptimizationResult, optimize
from ..risk.montecarlo import MonteCarloResult, run_montecarlo
from ..strategy.base import Strategy

LOG = logging.getLogger(__name__)


@dataclass
class BacktestPayload:
    """Everything the UI needs to render one backtest run."""

    result: BacktestResult
    metrics: Metrics
    monte_carlo: MonteCarloResult
    timestamps: list[Any] = field(default_factory=list)
    equity: list[float] = field(default_factory=list)
    drawdown: list[float] = field(default_factory=list)


@dataclass
class OptimizePayload:
    result: OptimizationResult
    equity: list[float] = field(default_factory=list)


class BacktestWorker(QObject):
    """Runs a single backtest + metrics + Monte Carlo on a worker thread."""

    progress = Signal(int, int)
    finished = Signal(object)   # BacktestPayload
    failed = Signal(str)

    def __init__(
        self,
        strategy: Strategy,
        symbol: str,
        bars: list,
        config: EngineConfig,
        annualization: int = 365,
        mc_paths: int = 5000,
        mc_horizon: int = 252,
    ) -> None:
        super().__init__()
        self.strategy = strategy
        self.symbol = symbol
        self.bars = bars
        self.config = config
        self.annualization = annualization
        self.mc_paths = mc_paths
        self.mc_horizon = mc_horizon

    def run(self) -> None:
        try:
            engine = Engine(self.config)
            result = engine.run(
                self.strategy, self.symbol, self.bars, progress_cb=self.progress.emit
            )
            metrics = compute_metrics(result, annualization=self.annualization)
            equity = result.equity_series
            mc = run_montecarlo(
                equity,
                n_paths=self.mc_paths,
                horizon=self.mc_horizon,
                dd_threshold_pct=15.0,
            )
            # drawdown series for the chart
            peak = np.maximum.accumulate(equity)
            dd = (peak - equity) / np.where(peak > 0, peak, 1.0) * 100.0
            payload = BacktestPayload(
                result=result,
                metrics=metrics,
                monte_carlo=mc,
                timestamps=result.timestamps,
                equity=equity.tolist(),
                drawdown=dd.tolist(),
            )
            self.finished.emit(payload)
        except Exception as exc:  # noqa: BLE001 — surface to UI, don't crash thread
            LOG.exception("Backtest worker failed")
            self.failed.emit(str(exc))


class OptimizeWorker(QObject):
    """Runs the self-improvement loop on a worker thread."""

    progress = Signal(int, int)
    finished = Signal(object)   # OptimizePayload
    failed = Signal(str)

    def __init__(
        self,
        symbol: str,
        bars: list,
        config: EngineConfig,
        annualization: int = 365,
        population: int = 12,
        generations: int = 8,
        oos_ratio: float = 0.3,
    ) -> None:
        super().__init__()
        self.symbol = symbol
        self.bars = bars
        self.config = config
        self.annualization = annualization
        self.population = population
        self.generations = generations
        self.oos_ratio = oos_ratio

    def run(self) -> None:
        try:
            res = optimize(
                self.symbol,
                self.bars,
                engine_config=self.config,
                annualization=self.annualization,
                population=self.population,
                generations=self.generations,
                oos_ratio=self.oos_ratio,
                progress_cb=self.progress.emit,
            )
            self.finished.emit(OptimizePayload(result=res))
        except Exception as exc:  # noqa: BLE001
            LOG.exception("Optimize worker failed")
            self.failed.emit(str(exc))
