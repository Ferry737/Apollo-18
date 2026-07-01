"""Strategy package — the Strategy ABC and built-in strategies."""
from .base import Strategy
from .sma_cross import SmaCross
from .registry import REGISTRY, all_strategies, get_strategy

__all__ = ["Strategy", "SmaCross", "REGISTRY", "all_strategies", "get_strategy"]
