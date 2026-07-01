"""
Apollo 18 — Dashboard Widget
Main overview: portfolio metrics, equity curve chart, strategy status, live data.
"""
import json
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QGridLayout, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QComboBox
)
from PyQt5.QtCore import Qt, QTimer

import numpy as np

from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class Card(QFrame):
    """Reusable card component with header."""
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("CardHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 8, 16, 8)

        title_label = QLabel(title)
        title_label.setObjectName("CardTitle")
        h_layout.addWidget(title_label)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("CardSubtitle")
            h_layout.addWidget(sub)
            h_layout.addStretch()

        layout.addWidget(header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(16, 12, 16, 12)
        layout.addWidget(self.body)

    def add_widget(self, widget):
        self.body_layout.addWidget(widget)


class MetricCard(Card):
    """KPI metric display card."""
    def __init__(self, label: str, value: str = "—", color: str = ""):
        super().__init__(label)
        self.value_label = QLabel(value)
        if color == "green":
            self.value_label.setObjectName("MetricValueGreen")
        elif color == "red":
            self.value_label.setObjectName("MetricValueRed")
        else:
            self.value_label.setObjectName("MetricValue")
        self.add_widget(self.value_label)

    def set_value(self, value: str, color: str = ""):
        self.value_label.setText(value)
        if color == "green":
            self.value_label.setStyleSheet("color: #00c853; font-size: 28px; font-weight: 700;")
        elif color == "red":
            self.value_label.setStyleSheet("color: #ff1744; font-size: 28px; font-weight: 700;")
        else:
            self.value_label.setStyleSheet("color: #d1d4dc; font-size: 28px; font-weight: 700;")


class EquityChart(QWidget):
    """Simple matplotlib-based equity curve chart."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        try:
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            self.fig = Figure(figsize=(8, 3), facecolor='#0d1117')
            self.canvas = FigureCanvasQTAgg(self.fig)
            self.ax = self.fig.add_subplot(111)
            self.ax.set_facecolor('#0d1117')
            self.ax.tick_params(colors='#6a7187', labelsize=8)
            for spine in self.ax.spines.values():
                spine.set_color('#1c2536')
            self.ax.grid(True, color='#161b22', linewidth=0.5)
            layout.addWidget(self.canvas)
            self._has_chart = True
            self._draw_placeholder()
        except ImportError:
            fallback = QLabel("📈 Equity Curve\n\n(matplotlib required for charting)")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet("color: #6a7187; font-size: 14px; padding: 40px;")
            layout.addWidget(fallback)
            self._has_chart = False

    def _draw_placeholder(self):
        """Draw initial placeholder data."""
        x = np.linspace(0, 100, 100)
        y = 100000 + np.cumsum(np.random.randn(100) * 200)
        self._draw(x, y)

    def _draw(self, x, y):
        if not self._has_chart:
            return
        self.ax.clear()
        self.ax.fill_between(range(len(y)), y, alpha=0.15, color='#2962ff')
        self.ax.plot(range(len(y)), y, color='#2962ff', linewidth=1.5)
        self.ax.set_facecolor('#0d1117')
        self.ax.tick_params(colors='#6a7187', labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color('#1c2536')
        self.ax.grid(True, color='#161b22', linewidth=0.5)
        self.fig.tight_layout(pad=0.5)
        self.canvas.draw()

    def update_data(self, equity_curve: list):
        """Update chart from equity curve data."""
        if not equity_curve or not self._has_chart:
            return
        values = [e.get("equity", 0) for e in equity_curve]
        self._draw(range(len(values)), values)


class DashboardWidget(QWidget):
    """Main dashboard page — portfolio overview."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #0a0e17; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # ---- Row 1: KPI Metrics ----
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(16)

        self.metric_equity = MetricCard("Portfolio Equity", "$100,000.00")
        self.metric_return = MetricCard("Total Return", "+0.00%", "green")
        self.metric_sharpe = MetricCard("Sharpe Ratio", "0.00")
        self.metric_drawdown = MetricCard("Max Drawdown", "0.00%", "red")

        for card in [self.metric_equity, self.metric_return, self.metric_sharpe, self.metric_drawdown]:
            metrics_row.addWidget(card)

        layout.addLayout(metrics_row)

        # ---- Row 2: Equity Curve + Strategy Status ----
        row2 = QHBoxLayout()
        row2.setSpacing(16)

        # Equity chart
        chart_card = Card("Equity Curve", "Portfolio performance over time")
        self.equity_chart = EquityChart()
        chart_card.add_widget(self.equity_chart)
        row2.addWidget(chart_card, 3)

        # Active strategies table
        strat_card = Card("Active Strategies", "Live positions")
        strat_table = QTableWidget(5, 4)
        strat_table.setHorizontalHeaderLabels(["Strategy", "Type", "Sharpe", "Status"])
        strat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        strat_table.verticalHeader().setVisible(False)
        strat_table.setEditTriggers(QTableWidget.NoEditTriggers)

        sample_data = [
            ("SMA_10_30", "SMACrossover", "1.42", "Active"),
            ("SMA_5_20", "SMACrossover", "0.87", "Active"),
            ("RSI_Default", "RSIMeanReversion", "1.15", "Active"),
            ("BB_20", "BollingerBreakout", "0.65", "Testing"),
            ("SMA_20_50", "SMACrossover", "-0.23", "Retiring"),
        ]
        for i, (name, stype, sharpe, status) in enumerate(sample_data):
            strat_table.setItem(i, 0, QTableWidgetItem(name))
            strat_table.setItem(i, 1, QTableWidgetItem(stype))
            strat_table.setItem(i, 2, QTableWidgetItem(sharpe))
            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(Qt.green)
            elif status == "Retiring":
                status_item.setForeground(Qt.red)
            strat_table.setItem(i, 3, status_item)

        strat_card.add_widget(strat_table)
        row2.addWidget(strat_card, 2)

        layout.addLayout(row2)

        # ---- Row 3: Risk Status + Learning Cycles ----
        row3 = QHBoxLayout()
        row3.setSpacing(16)

        risk_card = Card("Risk Monitor", "Circuit breakers & limits")
        risk_layout = QGridLayout()
        risk_layout.setSpacing(12)

        risk_items = [
            ("Daily DD Limit", "3.0%", "10.0%", "green"),
            ("Monthly DD Limit", "7.2%", "20.0%", "green"),
            ("Open Positions", "3", "10", ""),
            ("Cash Reserve", "15%", "5%", "green"),
        ]
        for i, (label, current, limit, color) in enumerate(risk_items):
            risk_layout.addWidget(QLabel(label), i, 0)
            val_label = QLabel(f"{current} / {limit}")
            if color == "green":
                val_label.setStyleSheet("color: #00c853;")
            risk_layout.addWidget(val_label, i, 1)

        risk_card.add_widget(self._wrap(risk_layout))
        row3.addWidget(risk_card)

        # Learning cycles
        learn_card = Card("Learning Cycles", "Self-improvement history")
        cycle_table = QTableWidget(3, 4)
        cycle_table.setHorizontalHeaderLabels(["Cycle", "Evaluated", "Promoted", "Best Sharpe"])
        cycle_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cycle_table.verticalHeader().setVisible(False)
        cycle_table.setEditTriggers(QTableWidget.NoEditTriggers)

        cycle_data = [
            ("#1", "15", "8", "1.42"),
            ("#2", "15", "10", "1.55"),
            ("#3", "15", "9", "1.38"),
        ]
        for i, (c, ev, pr, sh) in enumerate(cycle_data):
            cycle_table.setItem(i, 0, QTableWidgetItem(c))
            cycle_table.setItem(i, 1, QTableWidgetItem(ev))
            cycle_table.setItem(i, 2, QTableWidgetItem(pr))
            cycle_table.setItem(i, 3, QTableWidgetItem(sh))

        learn_card.add_widget(cycle_table)
        row3.addWidget(learn_card)

        layout.addLayout(row3)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _wrap(self, layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w
