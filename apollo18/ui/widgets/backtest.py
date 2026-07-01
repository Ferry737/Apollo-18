"""
Apollo 18 — Backtest Widget
Run and visualize backtest results: equity curves, metrics, trade history.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QScrollArea, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

import numpy as np

from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class BacktestWorker(QThread):
    """Background worker for running backtests."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def run(self):
        try:
            import pandas as pd
            from apollo18.data.data_manager import Database, MarketDataIngestor
            from apollo18.strategies.strategy_engine import StrategyFactory
            from apollo18.backtest.engine import Backtester, BacktestConfig

            self.progress.emit(10)

            db = Database()
            ingestor = MarketDataIngestor(db)

            # Get or generate data
            data = ingestor.get_stored_data(self.config["symbol"], "1d", 500)
            if data.empty:
                data = ingestor.generate_synthetic_data(self.config["symbol"], 500,
                                                        self.config.get("start_price", 50000))

            self.progress.emit(30)

            # Create strategy
            strategy = StrategyFactory.create(
                self.config["strategy_type"],
                fast=self.config.get("fast", 10),
                slow=self.config.get("slow", 30),
            )

            self.progress.emit(50)

            # Run backtest
            bt_config = BacktestConfig(
                initial_capital=self.config.get("capital", 100000),
                commission_pct=self.config.get("commission", 0.001),
                slippage_pct=self.config.get("slippage", 0.0005),
            )
            backtester = Backtester(bt_config)
            result = backtester.run(strategy, data)

            self.progress.emit(80)

            # Walk-forward validation
            wf = backtester.walk_forward(strategy, data)

            self.progress.emit(100)

            self.finished.emit({
                "result": result,
                "walk_forward": {
                    "train_sharpe": wf["train"].sharpe_ratio,
                    "test_sharpe": wf["test"].sharpe_ratio,
                    "overfitting_score": wf["overfitting_score"],
                    "passed": wf["passed_validation"],
                },
            })

            db.close()

        except Exception as e:
            self.error.emit(str(e))
            logger.exception("Backtest worker error")


class BacktestWidget(QWidget):
    """Backtest configuration and results visualization."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Backtest Engine")
        title.setStyleSheet("color: #d1d4dc; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Event-driven simulation with walk-forward validation")
        subtitle.setStyleSheet("color: #6a7187; font-size: 13px;")
        layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left: Configuration ----
        config_group = QGroupBox("Configuration")
        form = QFormLayout(config_group)
        form.setSpacing(10)

        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC/USDT", "ETH/USDT", "AAPL", "SYNTH"])
        form.addRow("Symbol:", self.symbol_combo)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["SMACrossover", "RSIMeanReversion", "BollingerBreakout"])
        form.addRow("Strategy:", self.strategy_combo)

        self.fast_spin = QSpinBox()
        self.fast_spin.setRange(2, 200)
        self.fast_spin.setValue(10)
        form.addRow("Fast Period:", self.fast_spin)

        self.slow_spin = QSpinBox()
        self.slow_spin.setRange(3, 500)
        self.slow_spin.setValue(30)
        form.addRow("Slow Period:", self.slow_spin)

        self.capital_spin = QSpinBox()
        self.capital_spin.setRange(1000, 10000000)
        self.capital_spin.setValue(100000)
        self.capital_spin.setSingleStep(10000)
        form.addRow("Initial Capital ($):", self.capital_spin)

        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0, 0.05)
        self.commission_spin.setValue(0.001)
        self.commission_spin.setSingleStep(0.0005)
        self.commission_spin.setDecimals(4)
        form.addRow("Commission (%):", self.commission_spin)

        self.slippage_spin = QDoubleSpinBox()
        self.slippage_spin.setRange(0, 0.05)
        self.slippage_spin.setValue(0.0005)
        self.slippage_spin.setSingleStep(0.0001)
        self.slippage_spin.setDecimals(4)
        form.addRow("Slippage (%):", self.slippage_spin)

        # Run button
        self.run_btn = QPushButton("▶ Run Backtest")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(40)
        self.run_btn.clicked.connect(self._run_backtest)
        form.addRow(self.run_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        form.addRow(self.progress)

        splitter.addWidget(config_group)

        # ---- Right: Results ----
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        # Metrics grid
        metrics_grid = QHBoxLayout()
        metrics_grid.setSpacing(16)

        self.lbl_return = self._make_metric("Total Return", "—")
        self.lbl_sharpe = self._make_metric("Sharpe Ratio", "—")
        self.lbl_dd = self._make_metric("Max Drawdown", "—")
        self.lbl_trades = self._make_metric("Total Trades", "—")
        self.lbl_winrate = self._make_metric("Win Rate", "—")

        for m in [self.lbl_return, self.lbl_sharpe, self.lbl_dd, self.lbl_trades, self.lbl_winrate]:
            metrics_grid.addWidget(m)

        results_layout.addLayout(metrics_grid)

        # Walk-forward validation
        wf_label = QLabel("Walk-Forward Validation")
        wf_label.setStyleSheet("color: #d1d4dc; font-size: 14px; font-weight: 600; margin-top: 12px;")
        results_layout.addWidget(wf_label)

        self.wf_result = QLabel("Not run yet")
        self.wf_result.setStyleSheet("color: #6a7187; font-size: 12px;")
        results_layout.addWidget(self.wf_result)

        # Equity curve chart
        chart_label = QLabel("Equity Curve")
        chart_label.setStyleSheet("color: #d1d4dc; font-size: 14px; font-weight: 600; margin-top: 12px;")
        results_layout.addWidget(chart_label)

        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self.fig = Figure(figsize=(6, 3), facecolor='#0d1117')
            self.chart_canvas = FigureCanvasQTAgg(self.fig)
            self.chart_ax = self.fig.add_subplot(111)
            self.chart_ax.set_facecolor('#0d1117')
            self.chart_ax.tick_params(colors='#6a7187', labelsize=8)
            for spine in self.chart_ax.spines.values():
                spine.set_color('#1c2536')
            self.chart_ax.grid(True, color='#161b22', linewidth=0.5)
            results_layout.addWidget(self.chart_canvas)
        except ImportError:
            placeholder = QLabel("📈 (matplotlib required)")
            placeholder.setStyleSheet("color: #6a7187; padding: 40px;")
            results_layout.addWidget(placeholder)

        results_layout.addStretch()
        splitter.addWidget(results_group)

        splitter.setSizes([350, 650])
        layout.addWidget(splitter)

    def _make_metric(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedHeight(80)
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: #6a7187; font-size: 10px; text-transform: uppercase;")
        val = QLabel(value)
        val.setStyleSheet("color: #d1d4dc; font-size: 20px; font-weight: 700;")
        l.addWidget(lbl)
        l.addWidget(val)

        card._value_label = val
        return card

    def _run_backtest(self):
        """Launch backtest in background thread."""
        config = {
            "symbol": self.symbol_combo.currentText(),
            "strategy_type": self.strategy_combo.currentText(),
            "fast": self.fast_spin.value(),
            "slow": self.slow_spin.value(),
            "capital": self.capital_spin.value(),
            "commission": self.commission_spin.value() / 100,
            "slippage": self.slippage_spin.value() / 100,
        }

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.run_btn.setEnabled(False)

        self.worker = BacktestWorker(config)
        self.worker.progress.connect(lambda v: self.progress.setValue(v))
        self.worker.finished.connect(self._on_backtest_done)
        self.worker.error.connect(self._on_backtest_error)
        self.worker.start()

    def _on_backtest_done(self, data: dict):
        """Handle backtest completion."""
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)

        result = data["result"]
        wf = data["walk_forward"]

        # Update metrics
        ret_pct = f"{result.total_return:+.2%}"
        color = "green" if result.total_return >= 0 else "red"
        self.lbl_return._value_label.setText(ret_pct)
        self.lbl_return._value_label.setStyleSheet(f"color: {'#00c853' if color == 'green' else '#ff1744'}; font-size: 20px; font-weight: 700;")

        self.lbl_sharpe._value_label.setText(f"{result.sharpe_ratio:.2f}")
        self.lbl_dd._value_label.setText(f"{result.max_drawdown:.2%}")
        self.lbl_trades._value_label.setText(str(result.total_trades))
        self.lbl_winrate._value_label.setText(f"{result.win_rate:.1%}")

        # Walk-forward
        wf_text = (
            f"Train Sharpe: {wf['train_sharpe']:.2f}  |  "
            f"Test Sharpe: {wf['test_sharpe']:.2f}  |  "
            f"Overfitting: {wf['overfitting_score']:.2f}  |  "
            f"Status: {'✅ PASSED' if wf['passed'] else '❌ FAILED'}"
        )
        self.wf_result.setText(wf_text)
        self.wf_result.setStyleSheet(
            f"color: {'#00c853' if wf['passed'] else '#ff1744'}; font-size: 12px;"
        )

        # Draw equity curve
        if hasattr(self, 'chart_canvas') and result.equity_curve:
            equities = [e["equity"] for e in result.equity_curve]
            self.chart_ax.clear()
            self.chart_ax.fill_between(range(len(equities)), equities,
                                        min(equities) * 0.95, alpha=0.15, color='#2962ff')
            self.chart_ax.plot(range(len(equities)), equities, color='#2962ff', linewidth=1.5)
            self.chart_ax.set_facecolor('#0d1117')
            self.chart_ax.tick_params(colors='#6a7187', labelsize=8)
            for spine in self.chart_ax.spines.values():
                spine.set_color('#1c2536')
            self.chart_ax.grid(True, color='#161b22', linewidth=0.5)
            self.fig.tight_layout(pad=0.5)
            self.chart_canvas.draw()

    def _on_backtest_error(self, error: str):
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.wf_result.setText(f"❌ Error: {error}")
        self.wf_result.setStyleSheet("color: #ff1744; font-size: 12px;")
