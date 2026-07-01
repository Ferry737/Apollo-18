"""Optimizer — the self-improvement loop driver.

Evolves a population of SMA-crossover variants over generations:
- backtest each variant in-sample + out-of-sample (walk-forward),
- rank by risk-adjusted return with overfit/drawdown guardrails,
- keep the best survivors and mutate them into the next generation.

Returns the ranked final population plus history. This is deliberately small
and synchronous; Phase 2 parallelises and adds ML-generated variants.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from ..backtest.engine import Engine, EngineConfig
from ..backtest.metrics import compute_metrics
from ..core.models import Bar
from ..strategy.sma_cross import SmaCross
from .mutation import mutate_sma_cross
from .ranking import Candidate, rank

LOG = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    index: int
    best_score: float
    best_params: dict[str, Any]
    population: list[Candidate]


@dataclass
class OptimizationResult:
    best: Candidate | None
    generations: list[GenerationResult] = field(default_factory=list)
    final_ranking: list[Candidate] = field(default_factory=list)


def _split(bars: list[Bar], oos_ratio: float) -> tuple[list[Bar], list[Bar]]:
    """Walk-forward split: earlier bars train, later bars test (out-of-sample)."""
    cut = int(len(bars) * (1 - oos_ratio))
    cut = max(2, min(len(bars) - 2, cut))
    return bars[:cut], bars[cut:]


def _evaluate(
    params: dict[str, Any],
    symbol: str,
    in_sample: list[Bar],
    oos: list[Bar],
    engine: Engine,
    annualization: int,
) -> tuple[Any, Any]:
    strat = SmaCross(**params)
    res_in = engine.run(strat, symbol, in_sample)
    m_in = compute_metrics(res_in, annualization=annualization)
    strat.reset()
    res_oos = engine.run(strat, symbol, oos)
    m_oos = compute_metrics(res_oos, annualization=annualization)
    return m_in, m_oos


def optimize(
    symbol: str,
    bars: list[Bar],
    engine_config: EngineConfig | None = None,
    annualization: int = 365,
    population: int = 12,
    generations: int = 8,
    oos_ratio: float = 0.3,
    seed: int = 7,
    progress_cb: Callable[[int, int], None] | None = None,
) -> OptimizationResult:
    """Run the self-improvement loop over SMA-crossover variants."""
    if len(bars) < 20:
        raise ValueError("Need at least 20 bars to optimize")
    rng = random.Random(seed)
    engine = Engine(engine_config)
    in_sample, oos = _split(bars, oos_ratio)

    # seed population around a sensible default
    base = {"fast": 20, "slow": 50, "allow_short": False}
    current: list[dict[str, Any]] = [base] + mutate_sma_cross(base, rng, population - 1)

    history: list[GenerationResult] = []
    total_steps = generations * population
    step = 0

    for gen in range(generations):
        candidates: list[Candidate] = []
        for params in current:
            m_in, m_oos = _evaluate(params, symbol, in_sample, oos, engine, annualization)
            candidates.append(
                Candidate(
                    name="sma_cross",
                    params=dict(params),
                    metrics=m_in,
                    oos_metrics=m_oos,
                )
            )
            step += 1
            if progress_cb:
                progress_cb(min(step, total_steps), total_steps)

        ranked = rank(candidates)
        best = ranked[0] if ranked and not ranked[0].eliminated else None
        history.append(
            GenerationResult(
                index=gen,
                best_score=best.score if best else 0.0,
                best_params=best.params if best else {},
                population=ranked,
            )
        )
        LOG.info(
            "Gen %d: best score=%.3f params=%s",
            gen, history[-1].best_score, history[-1].best_params,
        )

        # survivors: top half of viable candidates, then refill by mutation
        survivors = [c for c in ranked if not c.eliminated][: max(2, population // 2)]
        if not survivors:
            # restart diversity if everything got eliminated this generation
            survivors = [Candidate(name="sma_cross", params=base, metrics=candidates[0].metrics)]
        next_params: list[dict[str, Any]] = [s.params for s in survivors]
        # mutate survivors to refill the population
        while len(next_params) < population:
            parent = rng.choice(survivors).params
            next_params.extend(mutate_sma_cross(parent, rng, 1))
        current = next_params[:population]

    final = rank(
        [c for g in history for c in g.population]
    )
    # de-duplicate by params, keep best score
    seen: dict[tuple, Candidate] = {}
    for c in final:
        key = tuple(sorted(c.params.items()))
        if key not in seen or c.score > seen[key].score:
            seen[key] = c
    deduped = sorted(seen.values(), key=lambda c: c.score, reverse=True)
    best = deduped[0] if deduped and not deduped[0].eliminated else None

    return OptimizationResult(best=best, generations=history, final_ranking=deduped)
