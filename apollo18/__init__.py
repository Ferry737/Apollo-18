"""
Apollo 18 — Self-Improving AI Quantitative Trading Firm
"""
__version__ = "1.0.0"
__author__ = "Apollo 18"
__license__ = "MIT"

# Core paths
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data_cache")
LOG_DIR = os.path.join(ROOT_DIR, "logs")
MODEL_DIR = os.path.join(ROOT_DIR, "models")
CONFIG_DIR = os.path.join(ROOT_DIR, "config")

# Ensure dirs exist
for d in [DATA_DIR, LOG_DIR, MODEL_DIR, CONFIG_DIR]:
    os.makedirs(d, exist_ok=True)
