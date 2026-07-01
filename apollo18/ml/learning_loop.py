"""
Apollo 18 — Self-Improvement Learning Loop
The core feedback mechanism: backtest → evaluate → mutate → re-rank → repeat.

This is the 'brain' of Apollo 18 that drives continuous strategy evolution.
"""
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from apollo18.data.data_manager import Database
from apollo18.strategies.strategy_engine import BaseStrategy, StrategyFactory
from apollo18.backtest.engine import Backtester, BacktestConfig
from apollo18.ml.genetic_optimizer import GeneticOptimizer, StrategyGenome, ONNXModelServer
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LearningCycle:
    """Represents one iteration of the self-improvement loop."""
    cycle_number: int
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    strategies_evaluated: int = 0
    strategies_promoted: int = 0
    strategies_retired: int = 0
    best_sharpe: float = 0.0
    best_strategy_name: str = ""
    notes: str = ""


class SelfImprovementLoop:
    """
    Orchestrates the self-improving feedback loop:

    1. Acquire/refresh market data
    2. Backtest all active strategies (walk-forward)
    3. Run genetic optimization to generate mutations
    4. Evaluate fitness (risk-adjusted returns)
    5. Promote winners, retire losers
    6. Optionally retrain ML model
    7. Repeat

    Safety guardrails:
    - Out-of-sample validation required
    - Overfitting detection (>50% Sharpe degradation = rejected)
    - Minimum trade count for statistical significance
    - Drawdown-based strategy retirement
    """

    def __init__(
        self,
        db: Database,
        backtester: Backtester = None,
        optimizer: GeneticOptimizer = None,
        model_server: ONNXModelServer = None,
    ):
        self.db = db
        self.backtester = backtester or Backtester()
        self.optimizer = optimizer or GeneticOptimizer(population_size=15, max_generations=5)
        self.model_server = model_server or ONNXModelServer()
        self.cycle_count = self._get_last_cycle_number()
        self.best_strategies: list[StrategyGenome] = []

    def _get_last_cycle_number(self) -> int:
        """Read last cycle number from DB."""
        rows = self.db.query(
            "SELECT MAX(cycle_number) as max_cycle FROM learning_cycles"
        )
        if rows and rows[0]["max_cycle"]:
            return rows[0]["max_cycle"]
        return 0

    def run_cycle(
        self, data: pd.DataFrame, symbol: str = "BTC/USDT",
        retrain_model: bool = False
    ) -> LearningCycle:
        """Execute one full self-improvement cycle."""
        self.cycle_count += 1
        cycle = LearningCycle(cycle_number=self.cycle_count)
        logger.info(f"=== Learning Cycle {self.cycle_count} START ===")

        # Step 1: Run genetic optimization
        logger.info("Step 1: Genetic optimization...")
        population = self.optimizer.run_evolution(
            data=data,
            backtester=self.backtester,
        )

        # Step 2: Walk-forward validation on top candidates
        logger.info("Step 2: Walk-forward validation...")
        validated = []
        for genome in population[:10]:
            wf = self.backtester.walk_forward(genome.strategy, data)
            if wf["passed_validation"]:
                genome.fitness *= (1 - wf["overfitting_score"] * 0.5)
                validated.append(genome)
            else:
                logger.info(
                    f"  Rejected {genome.strategy.name}: overfitting score="
                    f"{wf['overfitting_score']:.2f}"
                )

        cycle.strategies_evaluated = len(population)
        cycle.strategies_promoted = len(validated)

        # Step 3: Store results in DB
        logger.info("Step 3: Storing results...")
        self._store_results(validated, symbol)

        # Step 4: Retire underperformers
        retired = self._retire_underperformers(validated)
        cycle.strategies_retired = retired

        # Step 5: Update best strategies ranking
        self.best_strategies = sorted(validated, key=lambda g: g.fitness, reverse=True)

        if self.best_strategies:
            best = self.best_strategies[0]
            cycle.best_sharpe = best.backtest_result.sharpe_ratio if best.backtest_result else 0
            cycle.best_strategy_name = best.strategy.name

        # Step 6: Optional model retraining
        if retrain_model:
            logger.info("Step 6: Retraining ML model...")
            result = self.model_server.train_simple_model(data)
            if result:
                cycle.notes += f"Model retrained (accuracy: {result['accuracy']:.3f}). "

        # Step 7: Record cycle
        cycle.completed_at = datetime.now().isoformat()
        self._record_cycle(cycle)

        logger.info(
            f"=== Cycle {self.cycle_count} COMPLETE: "
            f"evaluated={cycle.strategies_evaluated} "
            f"promoted={cycle.strategies_promoted} "
            f"retired={cycle.strategies_retired} "
            f"best={cycle.best_strategy_name} "
            f"sharpe={cycle.best_sharpe:.2f} ==="
        )

        return cycle

    def _store_results(self, validated: list[StrategyGenome], symbol: str):
        """Store validated strategies and backtest results in DB."""
        for genome in validated:
            # Insert or update strategy
            existing = self.db.query(
                "SELECT id FROM strategies WHERE name = ?", (genome.strategy.name,)
            )
            if existing:
                strategy_id = existing[0]["id"]
                self.db.execute(
                    """UPDATE strategies SET performance = ?, status = 'active',
                       generation = ? WHERE id = ?""",
                    (json.dumps(genome.backtest_result.to_dict()),
                     genome.generation, strategy_id)
                )
            else:
                cur = self.db.execute(
                    """INSERT INTO strategies (name, type, parameters, status, performance, generation)
                       VALUES (?, ?, ?, 'active', ?, ?)""",
                    (genome.strategy.name, genome.strategy.__class__.__name__,
                     json.dumps(genome.strategy.parameters),
                     json.dumps(genome.backtest_result.to_dict()),
                     genome.generation)
                )
                strategy_id = cur.lastrowid

            # Store backtest result
            br = genome.backtest_result
            self.db.execute(
                """INSERT INTO backtest_results
                   (strategy_id, start_date, end_date, total_return, sharpe_ratio,
                    max_drawdown, win_rate, total_trades, equity_curve)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (strategy_id, "", "", br.total_return, br.sharpe_ratio,
                 br.max_drawdown, br.win_rate, br.total_trades,
                 json.dumps(br.equity_curve[:100]))  # Store first 100 points
            )

    def _retire_underperformers(self, validated: list[StrategyGenome]) -> int:
        """Mark strategies with negative Sharpe as retired."""
        retired_names = {
            g.strategy.name for g in validated
            if g.backtest_result and g.backtest_result.sharpe_ratio < 0
        }
        count = 0
        for name in retired_names:
            self.db.execute(
                "UPDATE strategies SET status = 'retired' WHERE name = ?", (name,)
            )
            count += 1
        return count

    def _record_cycle(self, cycle: LearningCycle):
        """Record learning cycle in database."""
        self.db.execute(
            """INSERT INTO learning_cycles
               (cycle_number, started_at, completed_at, strategies_evaluated,
                strategies_promoted, strategies_retired, best_sharpe, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (cycle.cycle_number, cycle.started_at, cycle.completed_at,
             cycle.strategies_evaluated, cycle.strategies_promoted,
             cycle.strategies_retired, cycle.best_sharpe, cycle.notes)
        )

    def get_optimization_history(self) -> list[dict]:
        """Return the genetic optimizer's generation-by-generation history."""
        return self.optimizer.history

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """Get top-performing strategies from database."""
        rows = self.db.query(
            """SELECT s.name, s.type, s.generation, s.status,
                      b.sharpe_ratio, b.total_return, b.max_drawdown, b.win_rate,
                      b.total_trades
               FROM strategies s
               JOIN backtest_results b ON s.id = b.strategy_id
               WHERE s.status = 'active'
               ORDER BY b.sharpe_ratio DESC LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in rows]
