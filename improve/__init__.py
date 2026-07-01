"""Self-improvement package — the optimizer/mutation/ranking loop.

acquire bars -> backtest candidate -> extract metrics -> rank by risk-adjusted
return, reject overfit via walk-forward + out-of-sample -> mutate survivors ->
repeat. Guardrails enforce the PDF's quality bars (min Sharpe, max drawdown,
train/OOS gap) before a variant is promoted.
"""
from .optimizer import OptimizationResult, optimize
from .ranking import Candidate, rank
from .mutation import mutate_sma_cross

__all__ = ["optimize", "OptimizationResult", "rank", "Candidate", "mutate_sma_cross"]
