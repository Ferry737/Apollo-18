"""Theme — a Bloomberg/TradingView-inspired dark design system.

Centralised color tokens and typography so every widget looks consistent. Kept
as plain constants (no Qt dependency at import time) so it can be reused and
tested without a running QApplication.
"""
from __future__ import annotations

# Palette (dark, high-contrast for financial data)
BG = "#0b0f17"          # app background
SURFACE = "#121826"     # panels / cards
SURFACE_2 = "#1b2333"   # raised surfaces, table alt rows
BORDER = "#26324a"
TEXT = "#e6edf7"
TEXT_MUTED = "#8a98b4"
GREEN = "#22c55e"       # positive / long
RED = "#ef4444"         # negative / short
ACCENT = "#3b82f6"      # primary action / equity curve
AMBER = "#f59e0b"       # warnings / drawdown

# Spacing scale (px)
SP_XS = 4
SP_S = 8
SP_M = 12
SP_L = 16
SP_XL = 24

QSS = f"""
QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Inter", "Arial", sans-serif;
    font-size: 13px;
}}
QFrame#Card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QLabel#Title {{
    font-size: 16px;
    font-weight: 600;
}}
QLabel#Muted {{
    color: {TEXT_MUTED};
}}
QLabel#H1 {{
    font-size: 20px;
    font-weight: 700;
}}
QLabel#SimTag {{
    color: {AMBER};
    font-weight: 700;
    background-color: rgba(245,158,11,0.12);
    border: 1px solid {AMBER};
    border-radius: 3px;
    padding: 2px 8px;
}}
QPushButton {{
    background-color: {ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{ background-color: #2563eb; }}
QPushButton:disabled {{ background-color: {SURFACE_2}; color: {TEXT_MUTED}; }}
QPushButton#Ghost {{
    background-color: transparent;
    border: 1px solid {BORDER};
    color: {TEXT};
}}
QPushButton#Ghost:hover {{ border-color: {ACCENT}; }}
QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 8px;
    min-height: 20px;
}}
QComboBox:hover, QSpinBox:hover {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}
QStatusBar {{
    background-color: {SURFACE};
    border-top: 1px solid {BORDER};
    color: {TEXT_MUTED};
}}
QProgressBar {{
    background-color: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 3px;
    text-align: center;
    height: 14px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}
QTableWidget {{
    background-color: {SURFACE};
    alternate-background-color: {SURFACE_2};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QHeaderView::section {{
    background-color: {SURFACE_2};
    color: {TEXT_MUTED};
    border: none;
    border-right: 1px solid {BORDER};
    padding: 6px;
    font-weight: 600;
}}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; }}
QTabBar::tab {{
    background-color: {SURFACE};
    color: {TEXT_MUTED};
    padding: 8px 16px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{ background-color: {ACCENT}; color: #ffffff; }}
"""
