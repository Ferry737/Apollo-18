"""
Apollo 18 — Strategy Engine
Modular strategy framework with built-in strategies and mutation support.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Signal:
    """Trading signal output from a strategy."""
    timestamp: pd.Timestamp
    symbol: str
    direction: str  # "long", "short", "flat"
    strength: float = 1.0  # 0.0 to 1.0
    price: float = 0.0
    metadata: dict = field(default_factory=dict)


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, parameters: dict):
        self.name = name
        self.parameters = parameters
        self.generation = 0
        self.parent_id: Optional[int] = None

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Process OHLCV data and return list of signals."""
        pass

    @abstractmethod
    def mutate(self) -> "BaseStrategy":
        """Create a mutated variant of this strategy for the learning loop."""
        pass

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "parameters": json.dumps(self.parameters),
            "generation": self.generation,
        }

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.name}' gen={self.generation}>"


class SMACrossover(BaseStrategy):
    """Simple Moving Average crossover strategy — classic momentum."""

    def __init__(self, fast: int = 10, slow: int = 30, name: str = "SMA_Default"):
        super().__init__(name, {"fast": fast, "slow": slow})

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        df = data.copy()
        fast = self.parameters["fast"]
        slow = self.parameters["slow"]

        df["sma_fast"] = df["close"].rolling(fast).mean()
        df["sma_slow"] = df["close"].rolling(slow).mean()
        df["prev_fast"] = df["sma_fast"].shift(1)
        df["prev_slow"] = df["sma_slow"].shift(1)

        signals = []
        for _, row in df.iterrows():
            if pd.isna(row["sma_fast"]) or pd.isna(row["sma_slow"]):
                continue

            # Crossover detection
            crossed_up = (
                row["prev_fast"] <= row["prev_slow"]
                and row["sma_fast"] > row["sma_slow"]
            )
            crossed_down = (
                row["prev_fast"] >= row["prev_slow"]
                and row["sma_fast"] < row["sma_slow"]
            )

            if crossed_up:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="long",
                    price=row["close"],
                ))
            elif crossed_down:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="short",
                    price=row["close"],
                ))

        logger.debug(f"{self.name}: {len(signals)} signals from {len(df)} bars")
        return signals

    def mutate(self) -> "SMACrossover":
        """Mutate SMA parameters with small random perturbation."""
        fast = max(2, int(self.parameters["fast"] * np.random.uniform(0.7, 1.3)))
        slow = max(fast + 1, int(self.parameters["slow"] * np.random.uniform(0.7, 1.3)))
        child = SMACrossover(fast=fast, slow=slow, name=f"SMA_{fast}_{slow}")
        child.generation = self.generation + 1
        return child


class RSIMeanReversion(BaseStrategy):
    """RSI-based mean reversion strategy."""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70,
                 name: str = "RSI_Default"):
        super().__init__(name, {
            "period": period, "oversold": oversold, "overbought": overbought
        })

    def _compute_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        df = data.copy()
        period = self.parameters["period"]
        df["rsi"] = self._compute_rsi(df["close"], period)
        df["prev_rsi"] = df["rsi"].shift(1)

        signals = []
        for _, row in df.iterrows():
            if pd.isna(row["rsi"]):
                continue

            # Oversold → buy, Overbought → sell
            if row["prev_rsi"] < self.parameters["oversold"] and row["rsi"] >= self.parameters["oversold"]:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="long",
                    strength=min(1.0, (self.parameters["oversold"] - row["prev_rsi"]) / 30),
                    price=row["close"],
                ))
            elif row["prev_rsi"] > self.parameters["overbought"] and row["rsi"] <= self.parameters["overbought"]:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="short",
                    strength=min(1.0, (row["prev_rsi"] - self.parameters["overbought"]) / 30),
                    price=row["close"],
                ))

        return signals

    def mutate(self) -> "RSIMeanReversion":
        period = max(5, int(self.parameters["period"] * np.random.uniform(0.7, 1.3)))
        oversold = np.clip(self.parameters["oversold"] * np.random.uniform(0.8, 1.2), 10, 45)
        overbought = np.clip(self.parameters["overbought"] * np.random.uniform(0.8, 1.2), 55, 90)
        child = RSIMeanReversion(period=period, oversold=oversold, overbought=overbought,
                                 name=f"RSI_{period}")
        child.generation = self.generation + 1
        return child


class BollingerBreakout(BaseStrategy):
    """Bollinger Bands breakout strategy."""

    def __init__(self, period: int = 20, num_std: float = 2.0, name: str = "BB_Default"):
        super().__init__(name, {"period": period, "num_std": num_std})

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        df = data.copy()
        period = self.parameters["period"]
        num_std = self.parameters["num_std"]

        df["ma"] = df["close"].rolling(period).mean()
        df["std"] = df["close"].rolling(period).std()
        df["upper"] = df["ma"] + num_std * df["std"]
        df["lower"] = df["ma"] - num_std * df["std"]

        signals = []
        for _, row in df.iterrows():
            if pd.isna(row["upper"]):
                continue

            if row["close"] > row["upper"]:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="long",
                    price=row["close"],
                ))
            elif row["close"] < row["lower"]:
                signals.append(Signal(
                    timestamp=row.get("datetime", row.name),
                    symbol=row.get("symbol", "UNKNOWN"),
                    direction="short",
                    price=row["close"],
                ))

        return signals

    def mutate(self) -> "BollingerBreakout":
        period = max(5, int(self.parameters["period"] * np.random.uniform(0.7, 1.3)))
        num_std = np.clip(self.parameters["num_std"] * np.random.uniform(0.8, 1.2), 1.0, 3.5)
        child = BollingerBreakout(period=period, num_std=num_std, name=f"BB_{period}")
        child.generation = self.generation + 1
        return child


class StrategyFactory:
    """Factory for creating and registering strategies."""

    REGISTRY = {
        "SMACrossover": SMACrossover,
        "RSIMeanReversion": RSIMeanReversion,
        "BollingerBreakout": BollingerBreakout,
    }

    @classmethod
    def create(cls, strategy_type: str, **kwargs) -> BaseStrategy:
        if strategy_type not in cls.REGISTRY:
            raise ValueError(f"Unknown strategy type: {strategy_type}. Available: {list(cls.REGISTRY.keys())}")
        return cls.REGISTRY[strategy_type](**kwargs)

    @classmethod
    def from_parameters(cls, strategy_type: str, parameters: dict, name: str) -> BaseStrategy:
        """Reconstruct strategy from stored parameters."""
        if strategy_type == "SMACrossover":
            return SMACrossover(fast=parameters["fast"], slow=parameters["slow"], name=name)
        elif strategy_type == "RSIMeanReversion":
            return RSIMeanReversion(
                period=parameters["period"],
                oversold=parameters["oversold"],
                overbought=parameters["overbought"],
                name=name,
            )
        elif strategy_type == "BollingerBreakout":
            return BollingerBreakout(
                period=parameters["period"],
                num_std=parameters["num_std"],
                name=name,
            )
        raise ValueError(f"Cannot reconstruct: {strategy_type}")

    @classmethod
    def seed_strategies(cls) -> list[BaseStrategy]:
        """Create initial set of seed strategies for the learning loop."""
        return [
            SMACrossover(fast=10, slow=30),
            SMACrossover(fast=5, slow=20),
            SMACrossover(fast=20, slow=50),
            RSIMeanReversion(period=14),
            RSIMeanReversion(period=7),
            BollingerBreakout(period=20),
            BollingerBreakout(period=10),
        ]
