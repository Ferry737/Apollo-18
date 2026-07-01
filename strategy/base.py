"""Strategy interface.

A strategy is stateful: it is fed bars one at a time (in order) and, after each
bar, emits a target weight for the symbol in [-1, 1]. The engine converts the
change between the current portfolio weight and the target weight into orders.

Keeping strategies as target-weight-producers (rather than order-producers)
makes them simple, testable, and consistent with how the broker applies fees and
slippage. Strategies are intentionally framework-agnostic — no Qt, no DB.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..core.models import Bar


@dataclass
class Strategy(ABC):
    """Base class for all strategies.

    Subclasses set ``name`` and implement :meth:`on_bar`. Override
    :meth:`reset` if you carry mutable state between runs.
    """

    name: str = "base"

    @abstractmethod
    def on_bar(self, i: int, bar: Bar) -> float:
        """Return the target weight in [-1, 1] for this bar.

        ``i`` is the 0-based index into the full bar series. Strategies should
        return 0.0 until they have warmed up.
        """
        raise NotImplementedError

    def reset(self) -> None:
        """Reset mutable state so a strategy can be re-run deterministically."""
        return None

    def params(self) -> dict[str, Any]:
        """Return the strategy's parameters (for mutation / logging)."""
        return {"name": self.name}
