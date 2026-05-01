import os
import time

from call_cleaner import cli


def write_min_config(home, sdcard):
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
""")


def make_old_file(p, days=120):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")
    mt = time.time() - days * 86400
    os.utime(p, (mt, mt))


def test_run_skips_on_low_battery(tmp_home, fake_sdcard, monkeypatch, capsys):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: True)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: False)
    rc = cli.main(["run"])
    assert rc == 0
    # File untouched — run was skipped.
    assert src.exists()


def test_run_skips_on_battery_saver(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    src = fake_sdcard / "recordings" / "old.mp3"
    make_old_file(src)
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: False)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: True)
    rc = cli.main(["run"])
    assert rc == 0
    assert src.exists()


def test_run_calls_notify_on_success(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: False)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: False)
    monkeypatch.setattr(cli.notifier, "is_low_storage", lambda **kw: False)
    seen = []
    monkeypatch.setattr(
        cli.notifier, "notify",
        lambda title, content, **kw: seen.append((title, content)) or True,
    )
    rc = cli.main(["run"])
    assert rc == 0
    assert any(t == "Call Cleaner" and "trashed 1" in c for t, c in seen)


def test_run_calls_low_storage_notify(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: False)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: False)
    monkeypatch.setattr(cli.notifier, "is_low_storage", lambda **kw: True)
    seen = []
    monkeypatch.setattr(
        cli.notifier, "notify",
        lambda title, content, **kw: seen.append((title, content, kw.get("action"))) or True,
    )
    cli.main(["run"])
    assert any(t == "Storage low" for t, c, a in seen)


def test_run_no_low_storage_notify_when_nothing_trashed(tmp_home, fake_sdcard, monkeypatch):
    # Config exists but no old files — n will be 0 after the run.
    write_min_config(tmp_home, fake_sdcard)
    # Note: NO call to make_old_file — recordings dir empty.
    (fake_sdcard / "recordings").mkdir(exist_ok=True)
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: False)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: False)
    monkeypatch.setattr(cli.notifier, "is_low_storage", lambda **kw: True)  # storage IS low
    seen = []
    monkeypatch.setattr(
        cli.notifier, "notify",
        lambda title, content, **kw: seen.append((title, content)) or True,
    )
    rc = cli.main(["run"])
    assert rc == 0
    # No notifications fired because n == 0.
    assert seen == []


def test_run_no_notify_when_dry_run(tmp_home, fake_sdcard, monkeypatch):
    write_min_config(tmp_home, fake_sdcard)
    make_old_file(fake_sdcard / "recordings" / "old.mp3")
    monkeypatch.setattr(cli.notifier, "is_low_battery", lambda **kw: False)
    monkeypatch.setattr(cli.notifier, "is_battery_saver_on", lambda: False)
    monkeypatch.setattr(cli.notifier, "is_low_storage", lambda **kw: False)
    seen = []
    monkeypatch.setattr(
        cli.notifier, "notify",
        lambda title, content, **kw: seen.append((title, content)) or True,
    )
    rc = cli.main(["run", "--dry-run"])
    assert rc == 0
    assert seen == []  # dry-run never notifies
