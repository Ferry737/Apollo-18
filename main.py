"""
Apollo 18 — Self-Improving AI Quantitative Trading Firm
Local, portable, zero-cloud-dependency trading system.

Entry point for the desktop application.
"""
import sys
import os

# Ensure portable path resolution
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont

from apollo18.ui.main_window import MainWindow
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Launch Apollo 18 desktop application."""
    logger.info("Apollo 18 starting...")

    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Apollo 18")
    app.setOrganizationName("Apollo18")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply dark theme stylesheet
    from apollo18.ui.theme import DARK_THEME
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    logger.info("Apollo 18 UI launched successfully")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
