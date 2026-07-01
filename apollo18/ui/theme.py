"""
Apollo 18 — Professional Dark Theme
Bloomberg/TradingView-inspired financial dashboard aesthetic.
"""

DARK_THEME = """
/* ===== Apollo 18 Dark Theme ===== */
QWidget {
    background-color: #0a0e17;
    color: #d1d4dc;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #0a0e17;
}

/* ===== Side Navigation ===== */
QFrame#SideNav {
    background-color: #0d1117;
    border-right: 1px solid #1c2536;
    min-width: 60px;
    max-width: 60px;
}

QPushButton#NavButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 12px;
    margin: 4px 8px;
    color: #6a7187;
    font-size: 11px;
    text-align: center;
}

QPushButton#NavButton:hover {
    background-color: #161b22;
    color: #d1d4dc;
}

QPushButton#NavButton:checked {
    background-color: #1c2536;
    color: #2962ff;
    border-left: 3px solid #2962ff;
    border-radius: 4px;
}

/* ===== Top Bar ===== */
QFrame#TopBar {
    background-color: #0d1117;
    border-bottom: 1px solid #1c2536;
    min-height: 50px;
}

QLabel#LogoLabel {
    color: #2962ff;
    font-size: 18px;
    font-weight: bold;
    padding-left: 16px;
}

QLabel#StatusLabel {
    color: #6a7187;
    font-size: 11px;
    padding-right: 16px;
}

/* ===== Cards / Panels ===== */
QFrame#Card {
    background-color: #0d1117;
    border: 1px solid #1c2536;
    border-radius: 10px;
    padding: 0px;
}

QFrame#CardHeader {
    border-bottom: 1px solid #1c2536;
    padding: 10px 16px;
    min-height: 36px;
}

QLabel#CardTitle {
    color: #d1d4dc;
    font-size: 14px;
    font-weight: 600;
}

QLabel#CardSubtitle {
    color: #6a7187;
    font-size: 11px;
}

/* ===== Metric Labels ===== */
QLabel#MetricValue {
    color: #d1d4dc;
    font-size: 28px;
    font-weight: 700;
}

QLabel#MetricValueGreen {
    color: #00c853;
    font-size: 28px;
    font-weight: 700;
}

QLabel#MetricValueRed {
    color: #ff1744;
    font-size: 28px;
    font-weight: 700;
}

QLabel#MetricLabel {
    color: #6a7187;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel#MetricChange {
    font-size: 12px;
    font-weight: 600;
}

/* ===== Tables ===== */
QTableView {
    background-color: #0d1117;
    border: 1px solid #1c2536;
    border-radius: 8px;
    gridline-color: #1c2536;
    selection-background-color: #1c2536;
    selection-color: #2962ff;
}

QHeaderView::section {
    background-color: #0d1117;
    color: #6a7187;
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid #1c2536;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QTableView::item {
    padding: 8px 12px;
    border-bottom: 1px solid #161b22;
}

QTableView::item:hover {
    background-color: #161b22;
}

/* ===== Buttons ===== */
QPushButton {
    background-color: #1c2536;
    color: #d1d4dc;
    border: 1px solid #2a3447;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2a3447;
    border-color: #3a4759;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton#PrimaryButton {
    background-color: #2962ff;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#PrimaryButton:hover {
    background-color: #1e4dd8;
}

QPushButton#PrimaryButton:pressed {
    background-color: #1840b5;
}

QPushButton#SuccessButton {
    background-color: #00c853;
    color: #0a0e17;
    border: none;
    font-weight: 600;
}

QPushButton#DangerButton {
    background-color: #ff1744;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

/* ===== Tabs ===== */
QTabWidget::pane {
    border: 1px solid #1c2536;
    border-radius: 8px;
    background-color: #0d1117;
}

QTabBar::tab {
    background-color: transparent;
    color: #6a7187;
    padding: 10px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 13px;
}

QTabBar::tab:selected {
    color: #2962ff;
    border-bottom: 2px solid #2962ff;
}

QTabBar::tab:hover:!selected {
    color: #d1d4dc;
}

/* ===== Scrollbar ===== */
QScrollBar:vertical {
    background-color: #0d1117;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #2a3447;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #3a4759;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #0d1117;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background-color: #2a3447;
    border-radius: 4px;
    min-width: 30px;
}

/* ===== ComboBox ===== */
QComboBox {
    background-color: #1c2536;
    color: #d1d4dc;
    border: 1px solid #2a3447;
    border-radius: 6px;
    padding: 6px 12px;
    min-width: 100px;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QComboBox QAbstractItemView {
    background-color: #0d1117;
    border: 1px solid #2a3447;
    selection-background-color: #1c2536;
    padding: 4px;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background-color: #161b22;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #d1d4dc;
    height: 6px;
}

QProgressBar::chunk {
    background-color: #2962ff;
    border-radius: 4px;
}

/* ===== Text Edit ===== */
QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #00c853;
    border: 1px solid #1c2536;
    border-radius: 8px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    padding: 8px;
}

/* ===== SpinBox ===== */
QSpinBox, QDoubleSpinBox {
    background-color: #1c2536;
    color: #d1d4dc;
    border: 1px solid #2a3447;
    border-radius: 6px;
    padding: 6px 10px;
}

/* ===== Group Box ===== */
QGroupBox {
    border: 1px solid #1c2536;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    color: #6a7187;
    font-size: 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
"""
