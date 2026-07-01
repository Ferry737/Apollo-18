"""
Apollo 18 — Smoke Tests
Verify core modules import and function correctly.
Run: python -m pytest tests/test_smoke.py -v
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Verify all core modules import without errors."""
    from apollo18.utils.logger import get_logger
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.strategies.strategy_engine import (
        SMACrossover, RSIMeanReversion, BollingerBreakout, StrategyFactory
    )
    from apollo18.backtest.engine import Backtester, BacktestConfig
    from apollo18.ml.genetic_optimizer import GeneticOptimizer, ONNXModelServer
    from apollo18.ml.learning_loop import SelfImprovementLoop
    from apollo18.risk.risk_manager import RiskManager, RiskLimits

    print("✅ All imports successful")


def test_database():
    """Test SQLite database initialization."""
    from apollo18.data.data_manager import Database
    db = Database(path=":memory:")
    tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [t["name"] for t in tables]
    assert "ohlcv" in table_names
    assert "strategies" in table_names
    assert "backtest_results" in table_names
    print(f"✅ Database: {len(table_names)} tables created")
    db.close()


def test_synthetic_data():
    """Test synthetic data generation."""
    from apollo18.data.data_manager import Database, MarketDataIngestor
    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=100)
    assert len(data) == 100
    assert "close" in data.columns
    print(f"✅ Synthetic data: {len(data)} bars generated")
    db.close()


def test_strategy_signals():
    """Test strategy signal generation."""
    import pandas as pd
    import numpy as np
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.strategies.strategy_engine import SMACrossover

    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=200)

    strategy = SMACrossover(fast=10, slow=30)
    signals = strategy.generate_signals(data)
    assert isinstance(signals, list)
    print(f"✅ SMA Crossover: {len(signals)} signals from {len(data)} bars")
    db.close()


def test_strategy_mutation():
    """Test strategy mutation produces valid variants."""
    from apollo18.strategies.strategy_engine import SMACrossover
    parent = SMACrossover(fast=10, slow=30)
    child = parent.mutate()
    assert child.generation == parent.generation + 1
    assert child.parameters["fast"] != parent.parameters["fast"] or \
           child.parameters["slow"] != parent.parameters["slow"]
    print(f"✅ Mutation: parent={parent.parameters} → child={child.parameters}")


def test_backtester():
    """Test backtesting engine."""
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.strategies.strategy_engine import SMACrossover
    from apollo18.backtest.engine import Backtester

    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=200)

    strategy = SMACrossover(fast=5, slow=20)
    backtester = Backtester()
    result = backtester.run(strategy, data)

    assert hasattr(result, "total_return")
    assert hasattr(result, "sharpe_ratio")
    assert hasattr(result, "max_drawdown")
    print(f"✅ Backtest: return={result.total_return:.2%} sharpe={result.sharpe_ratio:.2f}")
    db.close()


def test_walk_forward():
    """Test walk-forward validation."""
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.strategies.strategy_engine import SMACrossover
    from apollo18.backtest.engine import Backtester

    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=200)

    strategy = SMACrossover(fast=10, slow=30)
    backtester = Backtester()
    wf = backtester.walk_forward(strategy, data)

    assert "train" in wf
    assert "test" in wf
    assert "passed_validation" in wf
    print(f"✅ Walk-forward: passed={wf['passed_validation']} "
          f"overfitting={wf['overfitting_score']:.2f}")
    db.close()


def test_risk_manager():
    """Test risk manager circuit breakers."""
    from apollo18.risk.risk_manager import RiskManager, RiskLimits

    limits = RiskLimits(max_portfolio_drawdown_daily=0.05)
    rm = RiskManager(limits)

    # Simulate 6% drawdown
    rm._peak_equity = 100000
    event = rm.update_equity(94000)

    assert rm.halted is True
    assert event is not None
    assert event.severity == "critical"
    print(f"✅ Risk manager: circuit breaker triggered at {(100000-94000)/100000:.0%} DD")


def test_genetic_optimizer():
    """Test genetic optimizer initialization and fitness."""
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.ml.genetic_optimizer import GeneticOptimizer
    from apollo18.backtest.engine import Backtester

    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=200)

    optimizer = GeneticOptimizer(population_size=5, max_generations=2)
    pop = optimizer.initialize_population()
    assert len(pop) >= 5

    backtester = Backtester()
    pop = optimizer.evaluate_fitness(pop, data, backtester)
    assert all(hasattr(g, "fitness") for g in pop)
    assert pop[0].fitness >= pop[-1].fitness  # Sorted descending

    print(f"✅ Genetic optimizer: {len(pop)} genomes, best fitness={pop[0].fitness:.3f}")
    db.close()


def test_learning_loop():
    """Test self-improvement loop end-to-end."""
    from apollo18.data.data_manager import Database, MarketDataIngestor
    from apollo18.ml.learning_loop import SelfImprovementLoop
    from apollo18.backtest.engine import Backtester
    from apollo18.ml.genetic_optimizer import GeneticOptimizer

    db = Database(path=":memory:")
    ingestor = MarketDataIngestor(db)
    data = ingestor.generate_synthetic_data("TEST", days=150)

    optimizer = GeneticOptimizer(population_size=5, max_generations=2)
    loop = SelfImprovementLoop(db, Backtester(), optimizer)

    cycle = loop.run_cycle(data, "TEST")
    assert cycle.cycle_number >= 1
    assert cycle.strategies_evaluated > 0

    print(f"✅ Learning loop: cycle #{cycle.cycle_number}, "
          f"evaluated={cycle.strategies_evaluated}, "
          f"best={cycle.best_strategy_name}")
    db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Apollo 18 — Smoke Tests")
    print("=" * 60 + "\n")

    tests = [
        test_imports,
        test_database,
        test_synthetic_data,
        test_strategy_signals,
        test_strategy_mutation,
        test_backtester,
        test_walk_forward,
        test_risk_manager,
        test_genetic_optimizer,
        test_learning_loop,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}\n")

    sys.exit(1 if failed > 0 else 0)
