"""Best-effort wrappers around Termux-API binaries.

All public functions short-circuit with sensible defaults if the underlying
binary isn't on $PATH (e.g., when running inside PRoot Ubuntu without
termux-api). No exceptions surface to callers.
"""
from __future__ import annotations

import json
import shutil
import subprocess


def _run(argv: list[str], *, timeout: float = 5.0) -> subprocess.CompletedProcess | None:
    """Run a command, returning the result or None if the binary is missing or hangs."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def termux_api_available() -> bool:
    """True if `termux-notification` is on $PATH."""
    cp = _run(["which", "termux-notification"])
    return bool(cp and cp.returncode == 0)


def notify(title: str, content: str, *, group: str = "call-cleaner", action: str | None = None) -> bool:
    """Fire an Android notification. Returns True if delivered, False otherwise."""
    if not termux_api_available():
        return False
    argv = [
        "termux-notification",
        "--title", title,
        "--content", content,
        "--group", group,
    ]
    if action:
        argv += ["--action", action]
    cp = _run(argv)
    return bool(cp and cp.returncode == 0)


def is_low_battery(*, percent: int = 20) -> bool:
    """True if battery is at or below `percent` AND not charging."""
    cp = _run(["termux-battery-status"])
    if not cp or cp.returncode != 0:
        return False
    try:
        data = json.loads(cp.stdout or "{}")
    except json.JSONDecodeError:
        return False
    if data.get("status", "").upper() == "CHARGING":
        return False
    pct = data.get("percentage")
    if not isinstance(pct, (int, float)):
        return False
    return pct <= percent


def is_battery_saver_on() -> bool:
    """True if Android battery-saver / power-save mode is enabled.

    Reads `dumpsys deviceidle enabled` via the shell. Returns False if the
    command isn't available or returns ambiguous output.
    """
    cp = _run(["sh", "-c", "dumpsys power 2>/dev/null | grep -m1 mPowerSaveModeEnabled || echo unknown"])
    if not cp or cp.returncode != 0:
        return False
    out = (cp.stdout or "").strip().lower()
    if "true" in out or out == "on":
        return True
    return False


def is_low_storage(path: str = "/sdcard", *, gb_threshold: float = 2.0) -> bool:
    """True if free space at `path` is below `gb_threshold` GiB."""
    try:
        usage = shutil.disk_usage(path)
    except (OSError, FileNotFoundError):
        return False
    free_gb = usage[2] / (1024 ** 3)
    return free_gb < gb_threshold
