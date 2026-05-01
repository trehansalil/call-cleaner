import time

from call_cleaner import doctor, state


def write_valid_config(tmp_path, sdcard):
    body = f"""\
default_preset = "default"

[trash]
dir = "{sdcard}/.CallCleanerTrash"
retention_days = 30

[paths]
calls = "{sdcard}/Music/Recordings/Call Recordings"

[[preset.default.rules]]
folder = "@calls"
age_days = 90
action = "trash"
"""
    p = tmp_path / "config.toml"
    p.write_text(body)
    return p


def test_termux_warns_when_termux_notification_missing(tmp_path, fake_sdcard, monkeypatch):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.setattr(doctor, "_termux_notification_available", lambda: False)
    monkeypatch.setattr(doctor, "_user_shortcut_exists", lambda name: True)
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert any("termux-api" in m for m in rep.messages)
    assert rep.status in ("warn", "ok")  # warn dominates ok


def test_termux_warns_when_shortcut_missing(tmp_path, fake_sdcard, monkeypatch):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.setattr(doctor, "_termux_notification_available", lambda: True)
    monkeypatch.setattr(doctor, "_user_shortcut_exists", lambda name: False)
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert any("install-schedule" in m for m in rep.messages)


def test_termux_ok_when_everything_present(tmp_path, fake_sdcard, monkeypatch):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    monkeypatch.setattr(doctor, "_termux_notification_available", lambda: True)
    monkeypatch.setattr(doctor, "_user_shortcut_exists", lambda name: True)
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert rep.status == "ok"


def test_proot_still_includes_proot_distro_note(tmp_path, fake_sdcard, monkeypatch):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    monkeypatch.delenv("PREFIX", raising=False)  # PRoot/Linux env
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert any("proot-distro" in m for m in rep.messages)
