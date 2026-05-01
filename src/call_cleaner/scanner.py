"""Walk configured folders and yield files that match each rule."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Preset, Rule

AUDIO_EXTS = {".mp3", ".m4a", ".amr", ".aac", ".wav", ".opus", ".3gp", ".ogg"}


@dataclass(frozen=True)
class Match:
    path: Path
    size: int
    mtime: float
    rule: Rule


def scan_rule(rule: Rule, *, now: float | None = None) -> list[Match]:
    folder = Path(rule.folder)
    if not folder.is_dir():
        return []
    if now is None:
        now = time.time()
    cutoff = now - rule.age_days * 86400
    matches: list[Match] = []
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return []
    for entry in entries:
        name = entry.name
        if name.startswith("."):
            continue
        if not entry.is_file(follow_symlinks=False):
            continue
        if Path(name).suffix.lower() not in AUDIO_EXTS:
            continue
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if st.st_mtime > cutoff:
            continue
        matches.append(Match(path=Path(entry.path), size=st.st_size, mtime=st.st_mtime, rule=rule))
    matches.sort(key=lambda m: m.mtime)
    return matches


def scan_preset(preset: Preset, *, now: float | None = None) -> list[Match]:
    out: list[Match] = []
    for r in preset.rules:
        out.extend(scan_rule(r, now=now))
    return out
