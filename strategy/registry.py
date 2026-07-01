"""Strategy registry — name -> factory for the UI and optimizer."""
from __future__ import annotations

from typing import Callable

from .base import Strategy
from .sma_cross import SmaCross

# factory takes optional kwargs and returns a fresh, reset strategy instance
Factory = Callable[..., Strategy]

REGISTRY: dict[str, Factory] = {
    "sma_cross": lambda **kw: SmaCross(**kw),
}


def all_strategies() -> list[str]:
    return sorted(REGISTRY)


def get_strategy(name: str, **kwargs: object) -> Strategy:
    if name not in REGISTRY:
        raise KeyError(f"Unknown strategy '{name}'. Available: {all_strategies()}")
    return REGISTRY[name](**kwargs)
