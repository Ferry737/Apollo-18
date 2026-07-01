# 🚀 Apollo 18 — Self-Improving AI Quantitative Trading Firm

**A fully local, portable, zero-cloud-dependency AI quantitative trading system that continuously improves itself through genetic optimization and backtesting feedback loops.**

![Apollo 18](https://img.shields.io/badge/Apollo-18-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey) ![Python](https://img.shields.io/badge/Python-3.10%2B-blue)

---

## ✨ Features

| Module | Description |
|--------|-------------|
| **📊 Dashboard** | Bloomberg/TradingView-inspired dark UI with real-time equity curves, KPI metrics, and strategy monitoring |
| **⚡ Strategy Engine** | Modular strategies (SMA Crossover, RSI Mean Reversion, Bollinger Breakout) with mutation support |
| **🔬 Backtester** | Event-driven simulation with realistic transaction costs, walk-forward optimization, and overfitting detection |
| **🧠 Self-Improvement Loop** | Genetic algorithm that generates, evaluates, mutates, and ranks thousands of strategy variants |
| **🤖 ML Module** | Local ONNX model inference + scikit-learn training pipeline for feature-augmented signals |
| **🛡 Risk Manager** | Circuit breakers, position limits, drawdown protection, and daily loss limits |
| **💾 SQLite Embedded** | Zero-configuration database — no external DB server needed |
| **📦 Single .EXE** | Portable PyInstaller build — works on any Windows 10+ machine |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Apollo 18 Desktop                   │
│                   (PyQt5 Dark Theme)                  │
├─────────┬─────────┬──────────┬──────────┬───────────┤
│Dashboard│Strategies│ Backtest │ Learning │ Settings  │
├─────────┴─────────┴──────────┴──────────┴───────────┤
│                    Core Engine                        │
├────────────┬──────────────┬───────────┬─────────────┤
│ Data Layer │Strategy Engine│ Backtester│ ML Module   │
│ (SQLite +  │ (SMA, RSI,   │ (Event-  │ (Genetic    │
│  CCXT +    │  Bollinger + │  Driven +│  Optimizer +│
│  yfinance) │  Mutation)   │  Walk-Fwd│  ONNX/ONNX) │
├────────────┴──────────────┴───────────┴─────────────┤
│              Self-Improvement Loop                    │
│   backtest → evaluate → mutate → re-rank → repeat    │
├───────────────────────────────────────────────────────┤
│              Risk Manager                             │
│   circuit breakers · position limits · drawdown halt  │
└───────────────────────────────────────────────────────┘
```

### Self-Improvement Loop Flow

```
     ┌──────────────────────────────────────────┐
     │              START CYCLE                   │
     └──────────────┬───────────────────────────┘
                    ▼
     ┌──────────────────────────┐
     │  1. Acquire Market Data   │ ← CCXT / yfinance / synthetic
     └──────────────┬───────────┘
                    ▼
     ┌──────────────────────────┐
     │  2. Backtest Population   │ ← Event-driven engine
     │     (N strategies)       │
     └──────────────┬───────────┘
                    ▼
     ┌──────────────────────────┐
     │  3. Evaluate Fitness      │ ← Sharpe × Return - Drawdown
     │     (risk-adjusted)      │
     └──────────────┬───────────┘
                    ▼
     ┌──────────────────────────┐
     │  4. Walk-Forward Validate │ ← Overfitting detection
     └──────────────┬───────────┘
                    ▼
     ┌──────────────────────────┐
     │  5. Genetic Mutation      │ ← Elitism + mutation
     │     (top performers)     │
     └──────────────┬───────────┘
                    ▼
     ┌──────────────────────────┐
     │  6. Promote / Retire      │ ← Strategy lifecycle
     │     + Retrain ML Model   │
     └──────────────┬───────────┘
                    ▼
              ┌──────────┐
              │  REPEAT  │
              └──────────┘
```

---

## 📁 Project Structure

```
Apollo-18/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── apollo18.spec              # PyInstaller spec
├── apollo18/
│   ├── __init__.py            # Core paths & constants
│   ├── data/
│   │   └── data_manager.py    # SQLite DB + CCXT/yfinance ingestor
│   ├── strategies/
│   │   └── strategy_engine.py # SMA, RSI, Bollinger + mutation
│   ├── backtest/
│   │   └── engine.py          # Event-driven backtester + walk-forward
│   ├── ml/
│   │   ├── genetic_optimizer.py  # Genetic algorithm + ONNX
│   │   └── learning_loop.py      # Self-improvement orchestrator
│   ├── risk/
│   │   └── risk_manager.py    # Circuit breakers + limits
│   ├── ui/
│   │   ├── main_window.py     # MainWindow + sidebar nav
│   │   ├── theme.py           # Bloomberg/TradingView dark theme
│   │   └── widgets/
│   │       ├── dashboard.py   # Portfolio overview + KPIs
│   │       ├── strategies.py  # Strategy manager
│   │       ├── backtest.py    # Backtest runner + results
│   │       ├── learning.py    # Learning loop control
│   │       └── settings.py    # Configuration + packaging
│   └── utils/
│       └── logger.py          # Logging configuration
├── packaging/
│   └── build_exe.py           # PyInstaller build script
├── config/                    # JSON settings (runtime)
├── data_cache/                # SQLite database (runtime)
├── logs/                      # Application logs
├── models/                    # ONNX model files
└── tests/
    └── test_smoke.py          # Smoke tests
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** (3.12+ recommended)
- **pip** or **uv**

### Install & Run

```bash
# Clone
git clone https://github.com/Ferry737/Apollo-18.git
cd Apollo-18

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Launch
python main.py
```

### Build Portable .EXE (Windows)

```bash
# Install PyInstaller (already in requirements.txt)
python packaging/build_exe.py

# Output: dist/Apollo18.exe
```

The `.EXE` bundles:
- ✅ Python runtime
- ✅ All Python packages
- ✅ SQLite engine
- ✅ ONNX runtime + models
- ✅ PyQt5 UI framework

---

## 🧪 Running the Self-Improvement Loop

1. Open the **Learning** tab in the UI
2. Select a symbol (e.g., BTC/USDT)
3. Set population size (15 recommended) and generations (5 recommended)
4. Optionally enable **"Retrain ML Model"**
5. Click **🚀 Start Learning Cycle**

The system will:
- Generate synthetic data if no market data is cached
- Backtest all strategies in the population
- Score each by risk-adjusted fitness
- Mutate top performers to create next generation
- Repeat for N generations
- Validate against overfitting via walk-forward analysis
- Promote winners, retire losers

---

## 🔒 Safety Guardrails

| Guardrail | Implementation |
|-----------|---------------|
| **Overfitting Detection** | Walk-forward validation: reject strategies where test Sharpe degrades >50% vs train |
| **Out-of-Sample Testing** | 70/30 train/test split with pass/fail validation |
| **Minimum Trade Count** | Strategies with <10 trades receive fitness penalty |
| **Drawdown Circuit Breaker** | Auto-halt trading when daily DD >10% or monthly DD >20% |
| **Position Limits** | Max 20% in single position, max 15% concentration |
| **Daily Loss Limit** | Auto-halt when daily loss exceeds 3% |

---

## 📊 Built-in Strategies

### SMA Crossover
Classic momentum strategy. Buy when fast MA crosses above slow MA.

### RSI Mean Reversion
Buy oversold, sell overbought using Relative Strength Index.

### Bollinger Breakout
Enter long when price breaks above upper Bollinger Band, short when below lower.

All strategies support **mutation** — the genetic optimizer perturbs their parameters to create variants for evaluation.

---

## 💻 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 | Windows 11 / Linux |
| **CPU** | Dual-core 2GHz | Quad-core 3GHz+ |
| **RAM** | 4 GB | 8 GB+ |
| **Disk** | 500 MB | 1 GB (with data cache) |
| **GPU** | Not required | Optional (ONNX inference acceleration) |

### Tested Hardware
- AMD Ryzen 7 9700X
- 32 GB DDR5
- Asus B650E Max Gaming WIFI
- NVIDIA GeForce RTX 5070

---

## 📜 License

MIT License — completely free and open source.

## ⚠️ Disclaimer

Apollo 18 is for educational and research purposes only. It is **not** financial advice. Trading involves risk of loss. Always validate strategies thoroughly before deploying real capital.
