import json
import os
import time
from unittest.mock import patch

import pytest

from call_cleaner import cli, paths


def write_min_config(home, sdcard):
    cfg_dir = home / ".config" / "call-cleaner"
    cfg_dir.mkdir(parents=True)
    cfg = cfg_dir / "config.toml"
    cfg.write_text(f"""\
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
""")
    return cfg


def make_old_file(p, days=120):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    mt = time.time() - days * 86400
    os.utime(p, (mt, mt))


def test_help_does_not_crash(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0


def test_config_init_creates_file(tmp_home):
    rc = cli.main(["config", "init"])
    assert rc == 0
    assert paths.config_path().exists()


def test_config_validate_ok(tmp_home, fake_sdcard):
    write_min_config(tmp_home, fake_sdcard)
    rc = cli.main(["config", "validate"])
    assert rc == 0


def test_config_validate_fails(tmp_home, capsys):
    paths.config_path().parent.mkdir(parents=True)
    paths.config_path().write_text("not valid")
    rc = cli.main(["config", "validate"])
    assert rc != 0


def test_scan_dry_run_does_not_modify(tmp_home, fake_sdcard):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    rc = cli.main(["scan"])
    assert rc == 0
    assert (fake_sdcard / "recordings" / "old.mp3").exists()


def test_run_trashes_old_file(tmp_home, fake_sdcard):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    rc = cli.main(["run"])
    assert rc == 0
    assert not src.exists()
    trash_files = list((fake_sdcard / ".CallCleanerTrash").iterdir())
    assert any(p.suffix == ".mp3" for p in trash_files)
    assert any(p.suffix == ".json" for p in trash_files)


def test_run_dry_run_does_not_modify(tmp_home, fake_sdcard):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    rc = cli.main(["run", "--dry-run"])
    assert rc == 0
    assert src.exists()


def test_trash_list_after_run(tmp_home, fake_sdcard, capsys):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    cli.main(["run"])
    capsys.readouterr()
    rc = cli.main(["trash", "list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "old.mp3" in out


def test_trash_restore_round_trip(tmp_home, fake_sdcard, capsys):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    cli.main(["run"])
    # Pick the id from `trash list --json`
    capsys.readouterr()
    cli.main(["trash", "list", "--json"])
    out = capsys.readouterr().out
    items = json.loads(out)
    assert items, "expected at least one trash item"
    rc = cli.main(["trash", "restore", items[0]["id"]])
    assert rc == 0
    assert src.exists()


def test_purge_removes_expired(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    cli.main(["run"])
    bin_dir = fake_sdcard / ".CallCleanerTrash"
    [side] = bin_dir.glob("*.json")
    meta = json.loads(side.read_text())
    meta["expires_at"] = int(time.time()) - 1
    side.write_text(json.dumps(meta))
    rc = cli.main(["purge"])
    assert rc == 0
    assert list(bin_dir.glob("*.mp3")) == []
    assert list(bin_dir.glob("*.json")) == []


def test_doctor_prints_status(tmp_home, fake_sdcard, capsys):
    write_min_config(tmp_home, fake_sdcard)
    cli.main(["doctor"])
    out = capsys.readouterr().out
    assert "ok" in out.lower() or "warn" in out.lower()


def test_install_schedule_prints(tmp_home, capsys):
    rc = cli.main(["install-schedule"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "termux-job-scheduler" in out


def test_run_skips_file_whose_mtime_changed(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    # Bump the mtime to "now" between scan and run by patching scanner.scan_preset
    # to return matches whose recorded mtime is stale.
    real_scan = cli.scanner.scan_preset

    def stale(*a, **kw):
        out = real_scan(*a, **kw)
        # Return matches with an mtime that won't match the current file.
        return [
            cli.scanner.Match(path=m.path, size=m.size, mtime=m.mtime - 1, rule=m.rule)
            for m in out
        ]

    monkeypatch.setattr(cli.scanner, "scan_preset", stale)
    rc = cli.main(["run"])
    assert rc == 0
    # File untouched because mtime changed since scan
    assert src.exists()


def test_run_handles_sigint_between_files(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    for i in range(3):
        make_old_file(fake_sdcard / "recordings" / f"old{i}.mp3")

    real_trash = cli.trash_mod.trash_file
    calls = {"n": 0}

    def trash_then_signal(*a, **kw):
        calls["n"] += 1
        result = real_trash(*a, **kw)
        # After the first successful trash, simulate SIGINT.
        if calls["n"] == 1:
            cli._interrupt_requested = True
        return result

    monkeypatch.setattr(cli.trash_mod, "trash_file", trash_then_signal)
    rc = cli.main(["run"])
    assert rc == 130
    # Only one file moved; the others remain.
    remaining = list((fake_sdcard / "recordings").glob("*.mp3"))
    assert len(remaining) == 2


def test_run_writes_to_log_file(tmp_home, fake_sdcard):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    cli.main(["run"])
    log_path = paths.log_path()
    assert log_path.exists()
    body = log_path.read_text()
    assert "run complete" in body
