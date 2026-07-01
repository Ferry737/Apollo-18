"""
Apollo 18 — Main Window
Tab-based dashboard with side navigation (Bloomberg/TradingView style).
"""
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QLabel, QStackedWidget, QTabWidget, QScrollArea,
    QStatusBar, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QIcon

from apollo18.ui.widgets.dashboard import DashboardWidget
from apollo18.ui.widgets.strategies import StrategyManagerWidget
from apollo18.ui.widgets.backtest import BacktestWidget
from apollo18.ui.widgets.learning import LearningLoopWidget
from apollo18.ui.widgets.settings import SettingsWidget
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class NavButton(QPushButton):
    """Square sidebar navigation button."""
    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setFixedSize(44, 50)
        self.setText(f"{icon}\n{label}")
        self.setCursor(Qt.PointingHandCursor)


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation + stacked content."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Apollo 18 — AI Quantitative Trading Firm")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        self._init_ui()
        self._init_status_bar()
        self._init_timer()

        logger.info("Main window initialized")

    def _init_ui(self):
        """Build the main layout: sidebar + content area."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- Sidebar ----
        sidebar = QFrame()
        sidebar.setObjectName("SideNav")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(2)
        sidebar_layout.setAlignment(Qt.AlignTop)

        # Logo
        logo = QLabel("🚀")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 24px; padding: 10px;")
        sidebar_layout.addWidget(logo)

        # Nav buttons
        self.nav_buttons = []
        self.nav_pages = {}

        nav_items = [
            ("📊", "Dashboard", DashboardWidget),
            ("⚡", "Strategies", StrategyManagerWidget),
            ("🔬", "Backtest", BacktestWidget),
            ("🧠", "Learning", LearningLoopWidget),
            ("⚙", "Settings", SettingsWidget),
        ]

        for icon, label, widget_class in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda checked, l=label: self._switch_page(l))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append((label, btn))

        sidebar_layout.addStretch()

        # ---- Content Area ----
        content_wrapper = QWidget()
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        content_layout.addWidget(top_bar)

        # Stacked pages
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # Create pages
        self.pages = {}
        for icon, label, widget_class in nav_items:
            page = widget_class()
            self.pages[label] = page
            self.stack.addWidget(page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_wrapper, 1)

        # Select first page
        self.nav_buttons[0][1].setChecked(True)
        self.stack.setCurrentIndex(0)

    def _build_top_bar(self) -> QFrame:
        """Build the top bar with logo and live status."""
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(50)
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Apollo 18")
        title.setObjectName("LogoLabel")
        layout.addWidget(title)

        sub = QLabel("Self-Improving AI Quantitative Trading Firm")
        sub.setStyleSheet("color: #6a7187; font-size: 11px; padding-left: 8px;")
        layout.addWidget(sub)

        layout.addStretch()

        # Status indicators
        self.status_label = QLabel("● System Ready")
        self.status_label.setStyleSheet("color: #00c853; font-size: 11px; font-weight: 600;")
        layout.addWidget(self.status_label)

        return top_bar

    def _init_status_bar(self):
        """Initialize bottom status bar."""
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready", 0)
        self.status.setStyleSheet("background-color: #0d1117; color: #6a7187; border-top: 1px solid #1c2536;")

    def _init_timer(self):
        """Refresh timer for UI updates."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_tick)
        self.timer.start(2000)

    def _on_tick(self):
        """Periodic UI refresh."""
        pass  # Pages handle their own refresh

    def _switch_page(self, label: str):
        """Switch to a navigation page."""
        for lbl, btn in self.nav_buttons:
            btn.setChecked(lbl == label)
        if label in self.pages:
            idx = self.stack.indexOf(self.pages[label])
            self.stack.setCurrentIndex(idx)
            self.status.showMessage(f"Viewing: {label}", 3000)
