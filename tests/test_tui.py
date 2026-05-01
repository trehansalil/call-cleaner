import os
import time
from unittest.mock import patch

import pytest

from call_cleaner import cli, tui


class FakeScreen:
    """Pretends to be a curses window. Captures keys and rendered lines."""

    def __init__(self, keys, size=(40, 100)):
        self._keys = list(keys)
        self.size = size
        self.lines: list[str] = []

    def getmaxyx(self):
        return self.size

    def getkey(self):
        if not self._keys:
            return "q"
        return self._keys.pop(0)

    def addstr(self, y, x, s, *a):
        while len(self.lines) <= y:
            self.lines.append("")
        line = self.lines[y]
        if len(line) < x:
            line = line + " " * (x - len(line))
        self.lines[y] = line[:x] + s + line[x + len(s):]

    def erase(self):
        self.lines = []

    def refresh(self):
        pass

    def clear(self):
        self.erase()


def write_cfg(home, sdcard):
    p = home / ".config" / "call-cleaner" / "config.toml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"""\
default_preset = "default"
[trash]
dir = "{sdcard}/.CallCleanerTrash"
retention_days = 30
[paths]
calls = "{sdcard}/recordings"
[[preset.default.rules]]
folder = "@calls"
age_days = 90
action = "trash"
[[preset.aggressive.rules]]
folder = "@calls"
age_days = 7
action = "trash"
""")


def make_old_file(p, days=120):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    mt = time.time() - days * 86400
    os.utime(p, (mt, mt))


def test_quit_returns_zero(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    rc = tui._loop(FakeScreen(["q"]))
    assert rc == 0


def test_too_small_renders_message(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    screen = FakeScreen(["q"], size=(10, 30))
    tui._loop(screen)
    assert any("too small" in l.lower() for l in screen.lines)


def test_main_view_renders_hotkey_help(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    screen = FakeScreen(["q"])
    tui._loop(screen)
    rendered = "\n".join(screen.lines)
    for hint in ["[r]", "[s]", "[t]", "[p]", "[c]", "[g]", "[q]"]:
        assert hint in rendered


def test_r_invokes_run_action(tmp_home, fake_sdcard, monkeypatch):
    write_cfg(tmp_home, fake_sdcard)
    calls = []
    monkeypatch.setattr(tui, "_invoke_cli", lambda *a: calls.append(list(a)))
    tui._loop(FakeScreen(["r", "q"]))
    assert ["run"] in calls


def test_g_invokes_purge_action(tmp_home, fake_sdcard, monkeypatch):
    write_cfg(tmp_home, fake_sdcard)
    calls = []
    monkeypatch.setattr(tui, "_invoke_cli", lambda *a: calls.append(list(a)))
    tui._loop(FakeScreen(["g", "q"]))
    assert ["purge"] in calls


def test_p_cycles_preset(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    screen = FakeScreen(["p", "q"])
    tui._loop(screen)
    rendered = "\n".join(screen.lines)
    # After cycling once with 2 presets defined, label should now be "aggressive".
    assert "aggressive" in rendered


def test_t_switches_to_trash_mode_then_q_returns(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    cli.main(["run"])
    screen = FakeScreen(["t", "q"])
    tui._loop(screen)
    rendered = "\n".join(screen.lines)
    assert "Trash" in rendered or "trash" in rendered


def test_trash_mode_R_restores_selected(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    cli.main(["run"])
    assert not src.exists()
    # t -> trash mode, R -> restore the (only) item, q -> quit
    tui._loop(FakeScreen(["t", "R", "q"]))
    assert src.exists()


def test_trash_mode_D_deletes_selected(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    cli.main(["run"])
    bin_dir = fake_sdcard / ".CallCleanerTrash"
    assert any(p.suffix == ".mp3" for p in bin_dir.iterdir())
    # t -> trash mode, D -> delete, y -> confirm, q -> quit
    tui._loop(FakeScreen(["t", "D", "y", "q"]))
    assert not any(p.suffix == ".mp3" for p in bin_dir.iterdir())


def test_trash_mode_arrows_move_cursor(tmp_home, fake_sdcard):
    write_cfg(tmp_home, fake_sdcard)
    for i in range(3):
        f = fake_sdcard / "recordings" / f"old{i}.mp3"
        make_old_file(f)
    cli.main(["run"])
    screen = FakeScreen(["t", "j", "j", "q"])
    state_seen = []
    real_draw = tui._draw_trash

    def capture(scr, st):
        state_seen.append(st.cursor)
        real_draw(scr, st)

    with patch.object(tui, "_draw_trash", capture):
        tui._loop(screen)
    # Cursor moved twice with 'j'.
    assert max(state_seen) == 2
