"""Resolve XDG paths and built-in defaults."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_TRASH_DIR = "/sdcard/.CallCleanerTrash"
APP_NAME = "call-cleaner"


def _xdg(env: str, fallback: str) -> Path:
    val = os.environ.get(env)
    if val:
        return Path(val)
    return Path(os.environ["HOME"]) / fallback


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / APP_NAME


def config_path() -> Path:
    return config_dir() / "config.toml"


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / APP_NAME


def state_path() -> Path:
    return data_dir() / "state.json"


def log_path() -> Path:
    return data_dir() / "run.log"


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


TERMUX_PREFIX = "/data/data/com.termux/files/usr"


def is_termux() -> bool:
    """True if running inside native Termux (vs PRoot Ubuntu / generic Linux)."""
    return os.environ.get("PREFIX") == TERMUX_PREFIX
