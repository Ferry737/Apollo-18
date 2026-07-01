"""
Apollo 18 — ML Module
Strategy optimization via genetic algorithm + ONNX model inference support.
All inference runs locally. No cloud ML APIs.
"""
import json
import random
import os
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from apollo18.strategies.strategy_engine import (
    BaseStrategy, StrategyFactory, SMACrossover, RSIMeanReversion, BollingerBreakout
)
from apollo18.backtest.engine import Backtester, BacktestResult
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyGenome:
    """Represents a strategy as an evolvable genome."""
    strategy: BaseStrategy
    fitness: float = 0.0
    generation: int = 0
    backtest_result: Optional[BacktestResult] = None


class GeneticOptimizer:
    """
    Genetic algorithm for strategy optimization (the 'strategy mutation engine').
    Implements selection, crossover-inspired mutation, and fitness evaluation.
    """

    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.3,
        elite_ratio: float = 0.2,
        max_generations: int = 10,
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.elite_ratio = elite_ratio
        self.max_generations = max_generations
        self.history: list[dict] = []

    def initialize_population(self) -> list[StrategyGenome]:
        """Create initial diverse population from seed strategies + mutations."""
        seeds = StrategyFactory.seed_strategies()
        population = []

        # Add seeds
        for s in seeds:
            population.append(StrategyGenome(strategy=s, generation=0))

        # Fill rest with mutations of seeds
        while len(population) < self.population_size:
            parent = random.choice(seeds)
            child = parent.mutate()
            population.append(StrategyGenome(strategy=child, generation=0))

        return population

    def evaluate_fitness(
        self, population: list[StrategyGenome], data: pd.DataFrame,
        backtester: Backtester
    ) -> list[StrategyGenome]:
        """Backtest each genome and assign fitness scores."""
        for genome in population:
            result = backtester.run(genome.strategy, data)
            genome.backtest_result = result
            # Fitness = risk-adjusted return with penalties
            genome.fitness = self._compute_fitness(result)

        population.sort(key=lambda g: g.fitness, reverse=True)
        return population

    def _compute_fitness(self, result: BacktestResult) -> float:
        """
        Multi-objective fitness: Sharpe ratio weighted heavily,
        penalize drawdown, reward consistency.
        """
        if result.total_trades == 0:
            return -999.0

        sharpe_weight = 0.5
        return_weight = 0.3
        dd_penalty = 0.15
        consistency_weight = 0.05

        sharpe_score = result.sharpe_ratio * sharpe_weight
        return_score = result.total_return * return_weight
        dd_score = -abs(result.max_drawdown) * dd_penalty
        consistency = result.win_rate * consistency_weight

        # Bonus for more trades (statistical significance)
        trade_bonus = min(0.1, result.total_trades / 100)

        fitness = sharpe_score + return_score + dd_score + consistency + trade_bonus
        return round(float(fitness), 4)

    def evolve(self, population: list[StrategyGenome]) -> list[StrategyGenome]:
        """Produce next generation via selection + mutation."""
        elite_count = max(2, int(self.population_size * self.elite_ratio))
        new_population = []

        # Elitism: keep top performers
        elites = population[:elite_count]
        for e in elites:
            new_population.append(StrategyGenome(
                strategy=e.strategy,
                fitness=e.fitness,
                generation=e.generation + 1,
                backtest_result=e.backtest_result,
            ))

        # Fill rest with mutations of elites + random seeds
        while len(new_population) < self.population_size:
            parent = random.choice(elites)
            if random.random() < self.mutation_rate:
                child = parent.strategy.mutate()
                child.generation = parent.generation + 1
                new_population.append(StrategyGenome(
                    strategy=child,
                    generation=parent.generation + 1,
                ))
            else:
                # Occasionally inject fresh random strategy
                seed = random.choice(StrategyFactory.seed_strategies())
                new_population.append(StrategyGenome(
                    strategy=seed,
                    generation=parent.generation + 1,
                ))

        return new_population

    def run_evolution(
        self, data: pd.DataFrame, backtester: Backtester,
        on_generation: callable = None
    ) -> list[StrategyGenome]:
        """Run full genetic optimization loop."""
        logger.info(f"Starting genetic optimization: {self.max_generations} generations, "
                     f"pop={self.population_size}")

        population = self.initialize_population()

        for gen in range(self.max_generations):
            population = self.evaluate_fitness(population, data, backtester)

            best = population[0]
            avg_fitness = np.mean([g.fitness for g in population])

            gen_record = {
                "generation": gen,
                "best_fitness": round(float(best.fitness), 4),
                "avg_fitness": round(float(avg_fitness), 4),
                "best_strategy": best.strategy.name,
                "best_sharpe": best.backtest_result.sharpe_ratio if best.backtest_result else 0,
                "best_return": best.backtest_result.total_return if best.backtest_result else 0,
            }
            self.history.append(gen_record)
            logger.info(
                f"Gen {gen}: Best={best.strategy.name} Fitness={best.fitness:.3f} "
                f"Sharpe={gen_record['best_sharpe']:.2f}"
            )

            if on_generation:
                on_generation(gen_record)

            if gen < self.max_generations - 1:
                population = self.evolve(population)

        logger.info(f"Genetic optimization complete. Best: {population[0].strategy.name}")
        return population


class ONNXModelServer:
    """
    Local ONNX model inference for ML-augmented signal generation.
    Falls back gracefully if onnxruntime is not installed.
    """

    def __init__(self, model_dir: str = None):
        from apollo18 import MODEL_DIR
        self.model_dir = model_dir or MODEL_DIR
        self._session = None
        self._model = None

    @property
    def session(self):
        if self._session is None:
            try:
                import onnxruntime as ort
                # Look for any .onnx file in model_dir
                onnx_files = [
                    f for f in os.listdir(self.model_dir)
                    if f.endswith(".onnx")
                ] if os.path.exists(self.model_dir) else []

                if onnx_files:
                    model_path = os.path.join(self.model_dir, onnx_files[0])
                    self._session = ort.InferenceSession(model_path)
                    logger.info(f"ONNX model loaded: {onnx_files[0]}")
                else:
                    logger.info("No ONNX model found — ML inference disabled (using strategies only)")
            except ImportError:
                logger.info("onnxruntime not installed — ML inference disabled")
        return self._session

    def predict(self, features: np.ndarray) -> np.ndarray:
        """Run inference on feature array."""
        if self.session is None:
            # Fallback: simple logistic-like scoring
            return 1 / (1 + np.exp(-features.mean(axis=1)))

        input_name = self.session.get_inputs()[0].name
        result = self.session.run(None, {input_name: features.astype(np.float32)})
        return result[0]

    def train_simple_model(self, data: pd.DataFrame, save: bool = True):
        """
        Train a simple scikit-learn model and export to ONNX format.
        This is a lightweight feature predictor, not a full trading agent.
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split

            df = data.copy()
            df["target"] = (df["close"].shift(-5) > df["close"]).astype(int)

            df["return_1d"] = df["close"].pct_change(1)
            df["return_5d"] = df["close"].pct_change(5)
            df["volatility"] = df["return_1d"].rolling(20).std()
            df["rsi"] = self._compute_rsi(df["close"], 14)

            features = ["return_1d", "return_5d", "volatility", "rsi"]
            df_clean = df.dropna(subset=features + ["target"])

            if len(df_clean) < 50:
                logger.warning("Not enough data to train model")
                return None

            X = df_clean[features].values
            y = df_clean["target"].values

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

            clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            clf.fit(X_train, y_train)
            accuracy = clf.score(X_test, y_test)
            logger.info(f"Trained RandomForest: accuracy={accuracy:.3f}")

            if save:
                self._export_to_onnx(clf, features)

            return {"model": clf, "accuracy": accuracy, "features": features}

        except ImportError:
            logger.warning("scikit-learn not installed — model training skipped")
            return None

    def _export_to_onnx(self, model, feature_names: list):
        """Export sklearn model to ONNX format."""
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType

            initial_type = [("float_input", FloatTensorType([None, len(feature_names)]))]
            onnx_model = convert_sklearn(model, initial_types=initial_type)

            from apollo18 import MODEL_DIR
            save_path = os.path.join(MODEL_DIR, "apollo18_predictor.onnx")
            with open(save_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
            logger.info(f"ONNX model exported: {save_path}")
        except ImportError:
            logger.info("skl2onnx not installed — ONNX export skipped, using sklearn directly")

    def _compute_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
