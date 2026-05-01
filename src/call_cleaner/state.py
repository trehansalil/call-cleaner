"""Atomic JSON state file."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from . import paths


@dataclass
class State:
    last_run_at: int | None = None
    last_run_preset: str | None = None
    last_run_trashed: int = 0
    last_run_freed_bytes: int = 0
    last_purge_at: int | None = None
    last_purge_removed: int = 0


def load(path: Path | None = None) -> State:
    if path is None:
        path = paths.state_path()
    if not path.exists():
        return State()
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return State()
    if not isinstance(data, dict):
        return State()
    return State(**{k: data.get(k, getattr(State(), k)) for k in State().__dict__})


def save(path: Path, s: State) -> None:
    paths.ensure_parent(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(s), f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
