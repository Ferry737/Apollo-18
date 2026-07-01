"""
Apollo 18 — Strategy Manager Widget
Create, view, mutate, and manage trading strategies.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QScrollArea, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt

from apollo18.strategies.strategy_engine import StrategyFactory
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyManagerWidget(QWidget):
    """Strategy management page."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Strategy Management")
        title.setStyleSheet("color: #d1d4dc; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        subtitle = QLabel("Create, configure, and evolve trading strategies")
        subtitle.setStyleSheet("color: #6a7187; font-size: 13px;")
        layout.addWidget(subtitle)

        # Splitter: creation form + strategy list
        splitter = QSplitter(Qt.Horizontal)

        # ---- Left: Create Strategy ----
        create_group = QGroupBox("Create New Strategy")
        form = QFormLayout(create_group)
        form.setSpacing(12)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["SMACrossover", "RSIMeanReversion", "BollingerBreakout"])
        form.addRow("Type:", self.type_combo)

        self.name_input = QLabel("Auto-generated")
        self.name_input.setStyleSheet("color: #6a7187;")
        form.addRow("Name:", self.name_input)

        # SMA params
        self.fast_spin = QSpinBox()
        self.fast_spin.setRange(2, 200)
        self.fast_spin.setValue(10)
        form.addRow("Fast Period:", self.fast_spin)

        self.slow_spin = QSpinBox()
        self.slow_spin.setRange(3, 500)
        self.slow_spin.setValue(30)
        form.addRow("Slow Period:", self.slow_spin)

        # RSI params
        self.rsi_period = QSpinBox()
        self.rsi_period.setRange(5, 100)
        self.rsi_period.setValue(14)
        form.addRow("RSI Period:", self.rsi_period)

        self.rsi_oversold = QDoubleSpinBox()
        self.rsi_oversold.setRange(5, 50)
        self.rsi_oversold.setValue(30)
        form.addRow("RSI Oversold:", self.rsi_oversold)

        self.rsi_overbought = QDoubleSpinBox()
        self.rsi_overbought.setRange(50, 95)
        self.rsi_overbought.setValue(70)
        form.addRow("RSI Overbought:", self.rsi_overbought)

        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("Create Strategy")
        create_btn.setObjectName("PrimaryButton")
        create_btn.clicked.connect(self._create_strategy)
        btn_layout.addWidget(create_btn)

        mutate_btn = QPushButton("Mutate Random")
        mutate_btn.clicked.connect(self._mutate_random)
        btn_layout.addWidget(mutate_btn)

        form.addRow(btn_layout)
        splitter.addWidget(create_group)

        # ---- Right: Strategy Table ----
        table_group = QGroupBox("Registered Strategies")
        table_layout = QVBoxLayout(table_group)

        self.table = QTableWidget(7, 6)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Parameters", "Generation", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Sample data
        strategies = [
            ("SMA_10_30", "SMACrossover", '{"fast": 10, "slow": 30}', "0", "Active"),
            ("SMA_5_20", "SMACrossover", '{"fast": 5, "slow": 20}', "0", "Active"),
            ("SMA_20_50", "SMACrossover", '{"fast": 20, "slow": 50}', "0", "Active"),
            ("RSI_Default", "RSIMeanReversion", '{"period": 14}', "0", "Active"),
            ("RSI_7", "RSIMeanReversion", '{"period": 7}', "1", "Active"),
            ("BB_20", "BollingerBreakout", '{"period": 20}', "0", "Active"),
            ("BB_10", "BollingerBreakout", '{"period": 10}', "1", "Testing"),
        ]
        for i, (name, stype, params, gen, status) in enumerate(strategies):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(stype))
            self.table.setItem(i, 2, QTableWidgetItem(params))
            self.table.setItem(i, 3, QTableWidgetItem(gen))
            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(Qt.green)
            elif status == "Testing":
                status_item.setForeground(Qt.yellow)
            self.table.setItem(i, 4, status_item)

        table_layout.addWidget(self.table)
        splitter.addWidget(table_group)

        splitter.setSizes([350, 650])
        layout.addWidget(splitter)

        # Quick start hint
        hint = QLabel(
            "💡 Tip: The Learning Loop page can automatically generate, mutate, "
            "and evaluate thousands of strategy variants using genetic optimization."
        )
        hint.setStyleSheet("color: #6a7187; font-size: 12px; padding: 8px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def _create_strategy(self):
        QMessageBox.information(self, "Create Strategy", "Strategy creation requires a backtest run first.\nGo to the Backtest tab to validate.")

    def _mutate_random(self):
        QMessageBox.information(self, "Mutate", "Use the Learning Loop to run genetic optimization across all strategies.")
