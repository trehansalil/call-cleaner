"""Health check — verify config, trash dir, state recency."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config as config_mod
from . import paths as paths_mod
from . import state as state_mod

STALE_RUN_SECS = 36 * 3600  # 36 hours


@dataclass
class Report:
    status: str = "ok"   # "ok" | "warn" | "error"
    messages: list[str] = field(default_factory=list)

    def warn(self, msg: str) -> None:
        self.messages.append(f"WARN: {msg}")
        if self.status == "ok":
            self.status = "warn"

    def error(self, msg: str) -> None:
        self.messages.append(f"ERROR: {msg}")
        self.status = "error"

    def info(self, msg: str) -> None:
        self.messages.append(msg)


def _check_writable(p: Path) -> tuple[bool, str]:
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".cleaner-write-probe"
        probe.write_text("")
        probe.unlink()
        return True, ""
    except OSError as e:
        return False, str(e)


def run(*, config_path: Path | None = None, state_path: Path | None = None) -> Report:
    rep = Report()
    if config_path is None:
        config_path = paths_mod.config_path()
    if state_path is None:
        state_path = paths_mod.state_path()

    try:
        cfg = config_mod.load(config_path)
        rep.info(f"config OK: {config_path}")
    except config_mod.ConfigError as e:
        rep.error(f"config: {e}")
        return rep

    trash_dir = Path(cfg.trash.dir)
    ok, why = _check_writable(trash_dir)
    if ok:
        rep.info(f"trash dir writable: {trash_dir}")
    else:
        rep.error(f"trash dir not writable: {trash_dir}: {why}")

    s = state_mod.load(state_path)
    if s.last_run_at is None:
        rep.warn("no recorded runs yet")
    else:
        age = time.time() - s.last_run_at
        if age > STALE_RUN_SECS:
            rep.warn(f"last run is stale: {age/3600:.1f}h ago")
        else:
            rep.info(f"last run: {age/3600:.1f}h ago")

    return rep
