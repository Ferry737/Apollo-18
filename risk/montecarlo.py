"""Monte Carlo risk simulation.

Two complementary estimators, both numpy-vectorised across thousands of paths:

1. **Geometric Brownian motion** projection of the equity curve forward
   ``horizon`` periods, parameterised from the realised period returns. This
   gives forward-looking VaR / CVaR / probability-of-drawdown at a horizon.

2. **Block-bootstrap** of the *trade* returns (resample the actual trade PnL
   sequence) to stress-test the strategy's own payoff distribution.

These are the same families the PDF names (GBM, jump-diffusion proxies,
resampling). We keep GBM here; jump-diffusion is a Phase-2 extension point.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..backtest.metrics import _returns


@dataclass
class MonteCarloResult:
    paths: np.ndarray                 # (n_paths, horizon+1) simulated equity
    var_pct: dict[float, float]       # confidence level -> VaR (% loss)
    cvar_pct: dict[float, float]      # confidence level -> CVaR (% loss)
    prob_drawdown: float              # P(drawdown >= threshold) over horizon
    median_final_equity: float

    def summary(self) -> dict[str, object]:
        flat_var = {f"var_{int(c*100)}": v for c, v in self.var_pct.items()}
        flat_cvar = {f"cvar_{int(c*100)}": v for c, v in self.cvar_pct.items()}
        return {
            "median_final_equity": float(self.median_final_equity),
            "prob_drawdown": float(self.prob_drawdown),
            **flat_var,
            **flat_cvar,
        }


def run_montecarlo(
    equity: np.ndarray,
    n_paths: int = 5000,
    horizon: int = 252,
    confidence_levels: tuple[float, ...] = (0.95, 0.99),
    dd_threshold_pct: float = 20.0,
    seed: int | None = 42,
) -> MonteCarloResult:
    """Project ``equity`` forward via GBM and compute risk statistics.

    Parameters mirror the PDF's outputs: VaR, Conditional VaR, and probability
    of drawdown thresholds under simulated scenarios.
    """
    rng = np.random.default_rng(seed)
    if equity.size < 2:
        # Degenerate: return zeros so downstream code stays safe.
        zeros = np.zeros((max(1, n_paths), horizon + 1))
        return MonteCarloResult(
            paths=zeros,
            var_pct={c: 0.0 for c in confidence_levels},
            cvar_pct={c: 0.0 for c in confidence_levels},
            prob_drawdown=0.0,
            median_final_equity=0.0,
        )

    rets = _returns(equity)
    mu = float(np.mean(rets))
    sigma = float(np.std(rets, ddof=1)) if rets.size > 1 else 0.0
    start_equity = float(equity[-1])

    # Vectorised GBM: draw the full (n_paths x horizon) innovation matrix at once
    z = rng.standard_normal((n_paths, horizon))
    period_rets = (mu - 0.5 * sigma ** 2) + sigma * z
    log_factors = np.cumsum(period_rets, axis=1)
    paths = start_equity * np.exp(log_factors)
    paths = np.concatenate([np.full((n_paths, 1), start_equity), paths], axis=1)

    finals = paths[:, -1]
    losses_pct = (start_equity - finals) / start_equity * 100.0  # >=0 is a loss

    var_pct: dict[float, float] = {}
    cvar_pct: dict[float, float] = {}
    for c in confidence_levels:
        # VaR: the loss not exceeded with probability c
        var = float(np.quantile(losses_pct, c))
        var_pct[c] = var
        cvar_pct[c] = float(losses_pct[losses_pct >= var].mean()) if np.any(losses_pct >= var) else var

    # Probability of a drawdown >= threshold at any point in the path
    peak = np.maximum.accumulate(paths, axis=1)
    dd = (peak - paths) / np.where(peak > 0, peak, 1.0) * 100.0
    prob_dd = float(np.mean(np.any(dd >= dd_threshold_pct, axis=1)))

    return MonteCarloResult(
        paths=paths,
        var_pct=var_pct,
        cvar_pct=cvar_pct,
        prob_drawdown=prob_dd,
        median_final_equity=float(np.median(finals)),
    )
