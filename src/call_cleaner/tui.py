"""Curses single-screen TUI."""
from __future__ import annotations

import curses
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import config as config_mod
from . import paths as paths_mod
from . import scanner
from . import state as state_mod
from . import trash as trash_mod

MIN_HEIGHT = 16
MIN_WIDTH = 60

HOTKEYS_MAIN = "[r] Run  [s] Scan  [t] Trash  [p] Preset  [c] Config  [g] Purge  [q] Quit"
HOTKEYS_TRASH = "[R] Restore  [D] Delete  [j/k] Move  [q/esc] Back"


@dataclass
class _State:
    mode: str = "main"               # "main" | "trash"
    preset_name: str | None = None
    cursor: int = 0
    matches: list = field(default_factory=list)
    trash_items: list = field(default_factory=list)
    flash: str = ""

    @classmethod
    def fresh(cls) -> "_State":
        s = cls()
        cfg = _load_cfg_quiet()
        if cfg:
            s.preset_name = cfg.default_preset
            s.matches = _scan_quiet(cfg, s.preset_name)
        return s


def run() -> int:
    return curses.wrapper(_loop)


def _loop(stdscr) -> int:
    state = _State.fresh()
    while True:
        h, w = stdscr.getmaxyx()
        if h < MIN_HEIGHT or w < MIN_WIDTH:
            stdscr.erase()
            stdscr.addstr(0, 0, "terminal too small")
            stdscr.refresh()
            try:
                key = stdscr.getkey()
            except KeyboardInterrupt:
                return 0
            if key == "q":
                return 0
            continue
        if state.mode == "main":
            _draw_main(stdscr, state)
        else:
            _draw_trash(stdscr, state)
        try:
            key = stdscr.getkey()
        except KeyboardInterrupt:
            return 0
        if state.mode == "main":
            rc = _handle_main(key, state, stdscr)
        else:
            rc = _handle_trash(key, state, stdscr)
        if rc is not None:
            return rc


def _handle_main(key: str, state: _State, stdscr) -> int | None:
    if key == "q":
        return 0
    if key == "r":
        _invoke_cli("run")
        _refresh_main(state)
        state.flash = "ran preset"
    elif key == "s":
        _refresh_main(state)
        state.flash = "scanned"
    elif key == "t":
        state.mode = "trash"
        state.cursor = 0
        state.trash_items = _list_trash_quiet()
    elif key == "p":
        _cycle_preset(state)
        _refresh_main(state)
    elif key == "c":
        _suspend_curses_and_run(stdscr, [_python_m_args() + ["config", "edit"]])
        _refresh_main(state)
    elif key == "g":
        _invoke_cli("purge")
        state.flash = "purged"
    return None


def _handle_trash(key: str, state: _State, stdscr) -> int | None:
    if key in ("q", "\x1b"):  # esc
        state.mode = "main"
        state.cursor = 0
        return None
    if key in ("KEY_UP", "k"):
        state.cursor = max(0, state.cursor - 1)
    elif key in ("KEY_DOWN", "j"):
        state.cursor = min(max(0, len(state.trash_items) - 1), state.cursor + 1)
    elif key == "R":
        if state.trash_items:
            item = state.trash_items[state.cursor]
            cfg = _load_cfg_quiet()
            if cfg and item.id:
                try:
                    trash_mod.restore(item.id, Path(cfg.trash.dir))
                    state.flash = f"restored {item.original_path}"
                except Exception as e:
                    state.flash = f"restore failed: {e}"
            state.trash_items = _list_trash_quiet()
            state.cursor = min(state.cursor, max(0, len(state.trash_items) - 1))
    elif key == "D":
        if state.trash_items:
            item = state.trash_items[state.cursor]
            try:
                confirm = stdscr.getkey()
            except KeyboardInterrupt:
                return 0
            if confirm in ("y", "Y"):
                cfg = _load_cfg_quiet()
                if cfg and item.id:
                    if item.payload and item.payload.exists():
                        try:
                            item.payload.unlink()
                        except OSError:
                            pass
                    if item.sidecar and item.sidecar.exists():
                        try:
                            item.sidecar.unlink()
                        except OSError:
                            pass
                    state.flash = f"deleted {item.id}"
            state.trash_items = _list_trash_quiet()
            state.cursor = min(state.cursor, max(0, len(state.trash_items) - 1))
    return None


def _draw_main(stdscr, state: _State) -> None:
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    cfg = _load_cfg_quiet()
    preset_label = state.preset_name or "?"
    stdscr.addstr(0, 0, f"Call Cleaner    preset: {preset_label}"[: w - 1])
    s = state_mod.load(paths_mod.state_path())
    if s.last_run_at:
        ago = (time.time() - s.last_run_at) / 3600
        line = f"Last run: {ago:.1f}h ago  trashed {s.last_run_trashed}  freed {s.last_run_freed_bytes} B"
    else:
        line = "Last run: never"
    stdscr.addstr(1, 0, line[: w - 1])
    stdscr.addstr(2, 0, ("Trash: %d items" % len(_list_trash_quiet()))[: w - 1])
    stdscr.addstr(4, 0, HOTKEYS_MAIN[: w - 1])
    if state.flash:
        stdscr.addstr(5, 0, state.flash[: w - 1])
    stdscr.addstr(7, 0, "Last scan:"[: w - 1])
    for i, m in enumerate(state.matches[: h - 9]):
        when = time.strftime("%Y-%m-%d", time.localtime(m.mtime))
        stdscr.addstr(9 + i, 0, f"  {when}  {m.size:>9} B  {m.path}"[: w - 1])
    stdscr.refresh()


def _draw_trash(stdscr, state: _State) -> None:
    h, w = stdscr.getmaxyx()
    stdscr.erase()
    stdscr.addstr(0, 0, "Call Cleaner — Trash"[: w - 1])
    stdscr.addstr(2, 0, HOTKEYS_TRASH[: w - 1])
    if state.flash:
        stdscr.addstr(3, 0, state.flash[: w - 1])
    if not state.trash_items:
        stdscr.addstr(5, 0, "trash is empty.")
    else:
        for i, item in enumerate(state.trash_items[: h - 6]):
            marker = "▸" if i == state.cursor else " "
            when = time.strftime("%Y-%m-%d", time.localtime(item.trashed_at)) if item.trashed_at else "?"
            line = f" {marker} {item.id}  {when}  {item.original_path}"
            stdscr.addstr(5 + i, 0, line[: w - 1])
    stdscr.refresh()


def _load_cfg_quiet() -> config_mod.Config | None:
    try:
        return config_mod.load(paths_mod.config_path())
    except config_mod.ConfigError:
        return None


def _scan_quiet(cfg: config_mod.Config, preset_name: str) -> list:
    try:
        return scanner.scan_preset(cfg.presets[preset_name])
    except Exception:
        return []


def _list_trash_quiet() -> list:
    cfg = _load_cfg_quiet()
    if not cfg:
        return []
    return trash_mod.list_items(Path(cfg.trash.dir))


def _refresh_main(state: _State) -> None:
    cfg = _load_cfg_quiet()
    if cfg and state.preset_name:
        state.matches = _scan_quiet(cfg, state.preset_name)


def _cycle_preset(state: _State) -> None:
    cfg = _load_cfg_quiet()
    if not cfg:
        return
    names = list(cfg.presets.keys())
    if not names:
        return
    try:
        i = names.index(state.preset_name) if state.preset_name in names else -1
    except ValueError:
        i = -1
    state.preset_name = names[(i + 1) % len(names)]


def _python_m_args() -> list[str]:
    return [sys.executable, "-m", "call_cleaner"]


def _invoke_cli(*subargs: str) -> int:
    """Run a `cleaner <subcmd>` step out-of-process. Tests monkeypatch this."""
    return subprocess.call(_python_m_args() + list(subargs))


def _suspend_curses_and_run(stdscr, argvs: list[list[str]]) -> None:
    curses.endwin()
    try:
        for argv in argvs:
            subprocess.call(argv)
    finally:
        stdscr.refresh()
