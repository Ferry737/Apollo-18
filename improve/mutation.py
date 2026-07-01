"""Mutation — produces new strategy parameter variants from survivors.

For the MVP this is a small, deterministic perturbation over SMA windows (a
lightweight stand-in for the PDF's "strategy mutation engine"). Phase 2 will
swap this for an ML-generated / hyperparameter-optimization variant factory.
"""
from __future__ import annotations

import random
from typing import Any

from ..strategy.sma_cross import SmaCross


def mutate_sma_cross(
    base: dict[str, Any], rng: random.Random | None = None, n: int = 6
) -> list[dict[str, Any]]:
    """Return ``n`` perturbed parameter dicts near ``base``."""
    rng = rng or random.Random()
    fast0 = int(base.get("fast", 20))
    slow0 = int(base.get("slow", 50))
    out: list[dict[str, Any]] = []
    for _ in range(n):
        fast = max(2, fast0 + rng.choice([-4, -2, -1, 1, 2, 4]))
        slow = max(fast + 1, slow0 + rng.choice([-8, -4, -2, 2, 4, 8]))
        out.append({"fast": fast, "slow": slow, "allow_short": base.get("allow_short", False)})
    return out
