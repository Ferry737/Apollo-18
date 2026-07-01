"""Configuration loading and runtime path resolution.

Paths are resolved relative to the application directory (next to the EXE when
frozen by PyInstaller, next to the package otherwise) — never relative to CWD,
which is unreliable for a portable single-binary desktop app.
"""
from __future__ import annotations

import os
import sys
import logging
import logging.config
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

LOG = logging.getLogger(__name__)


def app_dir() -> Path:
    """Directory the application lives in.

    When frozen with PyInstaller, ``sys.executable`` points at the EXE and its
    directory is where config/data/logs should sit. In development, fall back to
    the project root (parent of the ``apollo18`` package).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # dev: project root = parent of this file's package dir
    return Path(__file__).resolve().parent.parent


def resolve_path(path_str: str) -> Path:
    """Resolve a path that may be relative to the app dir."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return app_dir() / p


@dataclass
class AppConfig:
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "AppConfig":
        path = Path(path) if path else (app_dir() / "config" / "default.yaml")
        if not path.exists():
            LOG.warning("Config file not found at %s; using defaults.", path)
            return cls(raw={})
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        LOG.info("Loaded config from %s", path)
        return cls(raw=data)

    def get(self, *keys: str, default: Any = None) -> Any:
        cur: Any = self.raw
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[k]
        return cur

    # convenience accessors ---------------------------------------------------
    @property
    def store_path(self) -> Path:
        p = self.get("data", "store_path", default="data/apollo18.sqlite")
        resolved = resolve_path(p)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @property
    def initial_capital(self) -> float:
        return float(self.get("backtest", "initial_capital", default=100000.0))

    @property
    def fee_bps(self) -> float:
        return float(self.get("backtest", "fee_bps", default=5.0))

    @property
    def slippage_bps(self) -> float:
        return float(self.get("backtest", "slippage_bps", default=2.0))

    @property
    def annualization(self) -> int:
        return int(self.get("backtest", "annualization", default=365))


def setup_logging(config: "AppConfig | None" = None) -> None:
    """Configure logging from config/logging.yaml if present."""
    log_cfg = app_dir() / "config" / "logging.yaml"
    if log_cfg.exists():
        try:
            with open(log_cfg, "r", encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh)
            # Make the file handler path absolute under the app dir
            handlers = cfg.get("handlers", {})
            if "file" in handlers and "filename" in handlers["file"]:
                handlers["file"]["filename"] = str(
                    resolve_path(handlers["file"]["filename"])
                )
            logging.config.dictConfig(cfg)
            return
        except Exception as exc:  # pragma: no cover - logging is best-effort
            logging.basicConfig(level=logging.INFO)
            LOG.warning("Failed to load logging config %s: %s", log_cfg, exc)
    logging.basicConfig(level=logging.INFO)
