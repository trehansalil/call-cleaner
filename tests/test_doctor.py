import json
import time

from call_cleaner import config, doctor, state


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


def test_ok_when_everything_fresh(tmp_path, fake_sdcard):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert rep.status == "ok"


def test_warn_when_run_is_stale(tmp_path, fake_sdcard):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    # 2 days ago > 36h threshold
    state.save(state_path, state.State(last_run_at=int(time.time()) - 2 * 86400))
    (fake_sdcard / ".CallCleanerTrash").mkdir()
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert rep.status == "warn"
    assert any("stale" in m.lower() for m in rep.messages)


def test_error_when_config_invalid(tmp_path, fake_sdcard):
    bad = tmp_path / "bad.toml"
    bad.write_text("not = valid = toml")
    state_path = tmp_path / "state.json"
    rep = doctor.run(config_path=bad, state_path=state_path)
    assert rep.status == "error"


def test_error_when_trash_dir_unwritable(tmp_path, fake_sdcard, monkeypatch):
    cfg_path = write_valid_config(tmp_path, fake_sdcard)
    state_path = tmp_path / "state.json"
    state.save(state_path, state.State(last_run_at=int(time.time())))
    # Trash dir doesn't exist AND its parent doesn't either
    monkeypatch.setattr(
        doctor, "_check_writable",
        lambda p: (False, f"{p} not writable"),
    )
    rep = doctor.run(config_path=cfg_path, state_path=state_path)
    assert rep.status == "error"
