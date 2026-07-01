"""
Apollo 18 — Learning Loop Widget
Run the self-improvement genetic optimization cycle.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSplitter, QScrollArea,
    QPlainTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class LearningWorker(QThread):
    """Background worker for running the self-improvement loop."""
    progress = pyqtSignal(int, str)
    generation_update = pyqtSignal(dict)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

    def run(self):
        try:
            import pandas as pd
            from apollo18.data.data_manager import Database, MarketDataIngestor
            from apollo18.backtest.engine import Backtester
            from apollo18.ml.genetic_optimizer import GeneticOptimizer
            from apollo18.ml.learning_loop import SelfImprovementLoop

            self.progress.emit(5, "Initializing...")

            db = Database()
            ingestor = MarketDataIngestor(db)

            self.progress.emit(10, "Loading market data...")

            data = ingestor.get_stored_data(self.config["symbol"], "1d", 500)
            if data.empty:
                data = ingestor.generate_synthetic_data(self.config["symbol"], 500,
                                                        self.config.get("start_price", 50000))

            self.progress.emit(20, "Setting up learning loop...")

            backtester = Backtester()
            optimizer = GeneticOptimizer(
                population_size=self.config["population"],
                max_generations=self.config["generations"],
                mutation_rate=self.config["mutation_rate"],
            )
            loop = SelfImprovementLoop(db, backtester, optimizer)

            def on_gen(record):
                self.generation_update.emit(record)

            self.progress.emit(30, "Running genetic optimization...")

            cycle = loop.run_cycle(
                data=data,
                symbol=self.config["symbol"],
                retrain_model=self.config.get("retrain", False),
            )

            self.progress.emit(90, "Storing results...")

            leaderboard = loop.get_leaderboard(20)
            history = loop.get_optimization_history()

            self.progress.emit(100, "Complete!")

            self.finished.emit({
                "cycle": {
                    "number": cycle.cycle_number,
                    "evaluated": cycle.strategies_evaluated,
                    "promoted": cycle.strategies_promoted,
                    "retired": cycle.strategies_retired,
                    "best_sharpe": cycle.best_sharpe,
                    "best_strategy": cycle.best_strategy_name,
                },
                "leaderboard": leaderboard,
                "history": history,
            })

            db.close()

        except Exception as e:
            self.error.emit(str(e))
            logger.exception("Learning worker error")


class LearningLoopWidget(QWidget):
    """Self-improvement loop control and visualization."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🧠 Self-Improvement Loop")
        title.setStyleSheet("color: #d1d4dc; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Genetic algorithm optimization: backtest → evaluate → mutate → re-rank → repeat"
        )
        subtitle.setStyleSheet("color: #6a7187; font-size: 13px;")
        layout.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left: Configuration ----
        config_group = QGroupBox("Evolution Parameters")
        form = QFormLayout(config_group)
        form.setSpacing(10)

        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(["BTC/USDT", "ETH/USDT", "AAPL", "SYNTH"])
        form.addRow("Symbol:", self.symbol_combo)

        self.pop_spin = QSpinBox()
        self.pop_spin.setRange(5, 100)
        self.pop_spin.setValue(15)
        form.addRow("Population Size:", self.pop_spin)

        self.gen_spin = QSpinBox()
        self.gen_spin.setRange(1, 50)
        self.gen_spin.setValue(5)
        form.addRow("Generations:", self.gen_spin)

        self.mutation_spin = QDoubleSpinBox()
        self.mutation_spin.setRange(0, 1)
        self.mutation_spin.setValue(0.3)
        self.mutation_spin.setSingleStep(0.05)
        form.addRow("Mutation Rate:", self.mutation_spin)

        self.retrain_check = QComboBox()
        self.retrain_check.addItems(["No", "Yes"])
        form.addRow("Retrain ML Model:", self.retrain_check)

        # Run button
        self.run_btn = QPushButton("🚀 Start Learning Cycle")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(44)
        self.run_btn.clicked.connect(self._run_learning)
        form.addRow(self.run_btn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        form.addRow(self.progress)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6a7187; font-size: 11px;")
        form.addRow(self.status_label)

        splitter.addWidget(config_group)

        # ---- Right: Results ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Generation history table
        gen_label = QLabel("Generation History")
        gen_label.setStyleSheet("color: #d1d4dc; font-size: 14px; font-weight: 600;")
        right_layout.addWidget(gen_label)

        self.gen_table = QTableWidget(0, 5)
        self.gen_table.setHorizontalHeaderLabels(
            ["Generation", "Best Strategy", "Best Fitness", "Best Sharpe", "Best Return"]
        )
        self.gen_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.gen_table.verticalHeader().setVisible(False)
        self.gen_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.gen_table)

        # Leaderboard
        lb_label = QLabel("Strategy Leaderboard")
        lb_label.setStyleSheet("color: #d1d4dc; font-size: 14px; font-weight: 600; margin-top: 12px;")
        right_layout.addWidget(lb_label)

        self.lb_table = QTableWidget(0, 6)
        self.lb_table.setHorizontalHeaderLabels(
            ["Rank", "Strategy", "Type", "Sharpe", "Return", "Max DD"]
        )
        self.lb_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lb_table.verticalHeader().setVisible(False)
        self.lb_table.setEditTriggers(QTableWidget.NoEditTriggers)
        right_layout.addWidget(self.lb_table)

        right_layout.addStretch()
        splitter.addWidget(right_widget)

        splitter.setSizes([320, 680])
        layout.addWidget(splitter)

    def _run_learning(self):
        config = {
            "symbol": self.symbol_combo.currentText(),
            "population": self.pop_spin.value(),
            "generations": self.gen_spin.value(),
            "mutation_rate": self.mutation_spin.value(),
            "retrain": self.retrain_check.currentText() == "Yes",
        }

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.run_btn.setEnabled(False)
        self.gen_table.setRowCount(0)
        self.lb_table.setRowCount(0)

        self.worker = LearningWorker(config)
        self.worker.progress.connect(self._on_progress)
        self.worker.generation_update.connect(self._on_generation)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress.setValue(pct)
        self.status_label.setText(msg)

    def _on_generation(self, record: dict):
        row = self.gen_table.rowCount()
        self.gen_table.insertRow(row)
        self.gen_table.setItem(row, 0, QTableWidgetItem(str(record.get("generation", ""))))
        self.gen_table.setItem(row, 1, QTableWidgetItem(record.get("best_strategy", "")))
        self.gen_table.setItem(row, 2, QTableWidgetItem(f"{record.get('best_fitness', 0):.3f}"))
        self.gen_table.setItem(row, 3, QTableWidgetItem(f"{record.get('best_sharpe', 0):.2f}"))
        self.gen_table.setItem(row, 4, QTableWidgetItem(f"{record.get('best_return', 0):.2%}"))

    def _on_finished(self, data: dict):
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)

        cycle = data["cycle"]
        self.status_label.setText(
            f"Cycle #{cycle['number']} complete: "
            f"Evaluated {cycle['evaluated']}, Promoted {cycle['promoted']}, "
            f"Retired {cycle['retired']}. Best: {cycle['best_strategy']} "
            f"(Sharpe {cycle['best_sharpe']:.2f})"
        )

        # Fill leaderboard
        leaderboard = data.get("leaderboard", [])
        self.lb_table.setRowCount(0)
        for i, entry in enumerate(leaderboard[:20]):
            row = self.lb_table.rowCount()
            self.lb_table.insertRow(row)
            self.lb_table.setItem(row, 0, QTableWidgetItem(f"#{i+1}"))
            self.lb_table.setItem(row, 1, QTableWidgetItem(entry.get("name", "")))
            self.lb_table.setItem(row, 2, QTableWidgetItem(entry.get("type", "")))
            self.lb_table.setItem(row, 3, QTableWidgetItem(f"{entry.get('sharpe_ratio', 0):.2f}"))
            self.lb_table.setItem(row, 4, QTableWidgetItem(f"{entry.get('total_return', 0):.2%}"))
            self.lb_table.setItem(row, 5, QTableWidgetItem(f"{entry.get('max_drawdown', 0):.2%}"))

    def _on_error(self, error: str):
        self.progress.setVisible(False)
        self.run_btn.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error}")
        self.status_label.setStyleSheet("color: #ff1744; font-size: 11px;")
