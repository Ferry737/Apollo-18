"""
Apollo 18 — Settings Widget
Risk limits, data sources, model configuration, and packaging controls.
"""
import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QSpinBox, QDoubleSpinBox, QComboBox,
    QGroupBox, QFormLayout, QCheckBox, QTabWidget,
    QScrollArea, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt

from apollo18 import CONFIG_DIR
from apollo18.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsWidget(QWidget):
    """Settings and configuration page."""

    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: #0a0e17; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Settings")
        title.setStyleSheet("color: #d1d4dc; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        # ---- Risk Limits ----
        risk_group = QGroupBox("🛡 Risk Management Limits")
        risk_form = QFormLayout(risk_group)
        risk_form.setSpacing(10)

        self.max_position = QDoubleSpinBox()
        self.max_position.setRange(0.01, 1.0)
        self.max_position.setValue(0.20)
        self.max_position.setSingleStep(0.01)
        risk_form.addRow("Max Position Size (%):", self.max_position)

        self.dd_daily = QDoubleSpinBox()
        self.dd_daily.setRange(0.01, 0.50)
        self.dd_daily.setValue(0.10)
        self.dd_daily.setSingleStep(0.01)
        risk_form.addRow("Daily Drawdown Limit (%):", self.dd_daily)

        self.dd_monthly = QDoubleSpinBox()
        self.dd_monthly.setRange(0.01, 0.90)
        self.dd_monthly.setValue(0.20)
        self.dd_monthly.setSingleStep(0.01)
        risk_form.addRow("Monthly Drawdown Limit (%):", self.dd_monthly)

        self.max_concentration = QDoubleSpinBox()
        self.max_concentration.setRange(0.01, 1.0)
        self.max_concentration.setValue(0.15)
        risk_form.addRow("Max Concentration (%):", self.max_concentration)

        self.daily_loss = QDoubleSpinBox()
        self.daily_loss.setRange(0.001, 0.20)
        self.daily_loss.setValue(0.03)
        risk_form.addRow("Daily Loss Limit (%):", self.daily_loss)

        layout.addWidget(risk_group)

        # ---- Data Sources ----
        data_group = QGroupBox("📡 Data Sources")
        data_form = QFormLayout(data_group)
        data_form.setSpacing(10)

        self.crypto_source = QComboBox()
        self.crypto_source.addItems(["Binance (CCXT)", "Coinbase (CCXT)", "Kraken (CCXT)"])
        data_form.addRow("Crypto Data:", self.crypto_source)

        self.stock_source = QComboBox()
        self.stock_source.addItems(["Yahoo Finance (Free)", "Alpha Vantage (Free Tier)", "Finnhub (Free Tier)"])
        data_form.addRow("Stock Data:", self.stock_source)

        self.synth_check = QCheckBox("Generate synthetic data for offline testing")
        self.synth_check.setChecked(True)
        data_form.addRow("", self.synth_check)

        layout.addWidget(data_group)

        # ---- ML Configuration ----
        ml_group = QGroupBox("🤖 ML Model Configuration")
        ml_form = QFormLayout(ml_group)
        ml_form.setSpacing(10)

        self.ml_backend = QComboBox()
        self.ml_backend.addItems(["ONNX Runtime (Recommended)", "scikit-learn (Fallback)", "Disabled"])
        ml_form.addRow("Inference Backend:", self.ml_backend)

        self.ml_model_label = QLabel("No model loaded")
        self.ml_model_label.setStyleSheet("color: #6a7187; font-size: 12px;")
        ml_form.addRow("Active Model:", self.ml_model_label)

        train_btn = QPushButton("Train New Model")
        train_btn.clicked.connect(self._train_model)
        ml_form.addRow("", train_btn)

        layout.addWidget(ml_group)

        # ---- Packaging ----
        pkg_group = QGroupBox("📦 Build & Package (.EXE)")
        pkg_form = QFormLayout(pkg_group)
        pkg_form.setSpacing(10)

        self.pkg_info = QLabel(
            "Build a portable Windows .EXE with PyInstaller.\n"
            "All dependencies (Python, SQLite, models) are bundled."
        )
        self.pkg_info.setStyleSheet("color: #6a7187; font-size: 12px;")
        pkg_form.addRow("", self.pkg_info)

        build_btn = QPushButton("🔨 Build .EXE")
        build_btn.setObjectName("PrimaryButton")
        build_btn.clicked.connect(self._build_exe)
        pkg_form.addRow("", build_btn)

        layout.addWidget(pkg_group)

        # ---- Save / Reset ----
        btn_row = QHBoxLayout()

        save_btn = QPushButton("💾 Save Settings")
        save_btn.setObjectName("SuccessButton")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        reset_btn = QPushButton("↺ Reset to Defaults")
        reset_btn.setMinimumHeight(40)
        reset_btn.clicked.connect(self._load_config)
        btn_row.addWidget(reset_btn)

        layout.addLayout(btn_row)
        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _load_config(self):
        """Load settings from config file."""
        config_path = os.path.join(CONFIG_DIR, "settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                risk = cfg.get("risk", {})
                self.max_position.setValue(risk.get("max_position", 0.20))
                self.dd_daily.setValue(risk.get("dd_daily", 0.10))
                self.dd_monthly.setValue(risk.get("dd_monthly", 0.20))
                logger.info("Settings loaded")
            except Exception as e:
                logger.warning(f"Failed to load settings: {e}")

    def _save_config(self):
        """Save settings to config file."""
        config = {
            "risk": {
                "max_position": self.max_position.value(),
                "dd_daily": self.dd_daily.value(),
                "dd_monthly": self.dd_monthly.value(),
                "max_concentration": self.max_concentration.value(),
                "daily_loss": self.daily_loss.value(),
            },
            "data": {
                "crypto_source": self.crypto_source.currentText(),
                "stock_source": self.stock_source.currentText(),
                "synthetic": self.synth_check.isChecked(),
            },
            "ml": {
                "backend": self.ml_backend.currentText(),
            },
        }

        config_path = os.path.join(CONFIG_DIR, "settings.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"Settings saved: {config_path}")
        QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def _train_model(self):
        QMessageBox.information(
            self, "Train Model",
            "Go to the Learning Loop tab and enable 'Retrain ML Model' to train.\n"
            "The model will be saved as ONNX in the models/ directory."
        )

    def _build_exe(self):
        QMessageBox.information(
            self, "Build .EXE",
            "PyInstaller build command:\n\n"
            "pyinstaller --onefile --windowed --name Apollo18 \\\n"
            "  --add-data \"apollo18;apollo18\" \\\n"
            "  --hidden-import PyQt5 \\\n"
            "  --hidden-import matplotlib.backends.backend_qt5agg \\\n"
            "  main.py\n\n"
            "See packaging/build_exe.py for the full build script.\n"
            "(Run on a Windows machine for Windows .EXE output)"
        )
