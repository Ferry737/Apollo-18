"""Ranking — score and sort backtest candidates.

Score = risk-adjusted return (Sharpe) with hard penalties/eliminations for
exceeding drawdown or overfit thresholds. Keeps the PDF's KPI philosophy: a
high-return but deep-drawdown or overfit strategy should not win.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..backtest.metrics import Metrics


@dataclass
class Candidate:
    """A scored strategy variant."""

    name: str
    params: dict[str, Any]
    metrics: Metrics
    oos_metrics: Metrics | None = None
    score: float = 0.0
    eliminated: bool = False
    reason: str = ""

    @property
    def overfit_gap(self) -> float:
        """Difference between in-sample and out-of-sample Sharpe."""
        if self.oos_metrics is None:
            return 0.0
        return float(self.metrics.sharpe - self.oos_metrics.sharpe)


def rank(
    candidates: list[Candidate],
    min_sharpe: float = 0.5,
    max_drawdown_pct: float = 25.0,
    max_overfit_gap: float = 1.0,
) -> list[Candidate]:
    """Score and sort candidates; mark violators as eliminated."""
    for c in candidates:
        m = c.metrics
        if m.sharpe < min_sharpe:
            c.eliminated = True
            c.reason = f"Sharpe {m.sharpe:.2f} < {min_sharpe}"
        elif m.max_drawdown_pct > max_drawdown_pct:
            c.eliminated = True
            c.reason = f"maxDD {m.max_drawdown_pct:.1f}% > {max_drawdown_pct}%"
        elif c.oos_metrics is not None and c.overfit_gap > max_overfit_gap:
            c.eliminated = True
            c.reason = f"overfit gap {c.overfit_gap:.2f} > {max_overfit_gap}"
        else:
            # Score: Sharpe minus a small drawdown penalty; OOS-aware.
            oos_sharpe = c.oos_metrics.sharpe if c.oos_metrics else m.sharpe
            c.score = oos_sharpe - 0.02 * m.max_drawdown_pct

    viable = [c for c in candidates if not c.eliminated]
    viable.sort(key=lambda c: c.score, reverse=True)
    eliminated = sorted(
        [c for c in candidates if c.eliminated], key=lambda c: c.metrics.sharpe, reverse=True
    )
    return viable + eliminated
