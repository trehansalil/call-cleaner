import io

import pytest

from call_cleaner import config as config_mod
from call_cleaner import first_run


def test_detect_returns_only_existing_paths(tmp_path, monkeypatch):
    sdcard = tmp_path / "sdcard"
    (sdcard / "Music" / "Recordings" / "Call Recordings").mkdir(parents=True)
    (sdcard / "Recordings" / "Call").mkdir(parents=True)
    monkeypatch.setattr(first_run, "KNOWN_RECORDING_PATHS", {
        "oneplus_calls": "Music/Recordings/Call Recordings",
        "samsung_calls": "Recordings/Call",
        "missing":       "Recordings/DoesNotExist",
    })
    found = first_run.detect(root=str(sdcard))
    assert set(found) == {"oneplus_calls", "samsung_calls"}
    assert found["oneplus_calls"].endswith("Music/Recordings/Call Recordings")


def test_detect_handles_no_root(tmp_path, monkeypatch):
    monkeypatch.setattr(first_run, "KNOWN_RECORDING_PATHS", {"x": "any"})
    found = first_run.detect(root=str(tmp_path / "doesnt_exist"))
    assert found == {}


def test_write_seeded_config_round_trips(tmp_path):
    cfg_path = tmp_path / "config.toml"
    found = {
        "calls":  str(tmp_path / "Music" / "Recordings" / "Call Recordings"),
        "voice":  str(tmp_path / "Music" / "Recordings" / "Standard Recordings"),
    }
    for v in found.values():
        from pathlib import Path
        Path(v).mkdir(parents=True)
    first_run.write_seeded_config(cfg_path, found)
    cfg = config_mod.load(cfg_path)
    assert cfg.default_preset == "default"
    assert set(cfg.paths) == {"calls", "voice"}
    assert len(cfg.presets["default"].rules) == 2


def test_write_seeded_config_requires_at_least_one(tmp_path):
    cfg_path = tmp_path / "config.toml"
    with pytest.raises(ValueError, match="at least one"):
        first_run.write_seeded_config(cfg_path, {})


def test_interactive_prompt_reads_lines(tmp_path, monkeypatch):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    inputs = iter([f"calls={real_dir}", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    found = first_run.interactive_prompt()
    assert found == {"calls": str(real_dir)}


def test_interactive_prompt_rejects_relative(tmp_path, monkeypatch):
    real_dir = tmp_path / "ok"
    real_dir.mkdir()
    inputs = iter(["bad=relative/path", f"good={real_dir}", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    found = first_run.interactive_prompt()
    # Bad line skipped; good one accepted.
    assert found == {"good": str(real_dir)}


def test_interactive_prompt_rejects_missing_paths(tmp_path, monkeypatch):
    real_dir = tmp_path / "ok"
    real_dir.mkdir()
    nonexist = tmp_path / "nope"
    inputs = iter([f"x={nonexist}", f"good={real_dir}", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    found = first_run.interactive_prompt()
    assert "good" in found
    assert "x" not in found


def test_main_detect_writes_config(tmp_home, fake_sdcard, monkeypatch):
    p = fake_sdcard / "Music" / "Recordings" / "Call Recordings"
    p.mkdir(parents=True)
    monkeypatch.setattr(first_run, "KNOWN_RECORDING_PATHS", {
        "calls": "Music/Recordings/Call Recordings",
    })
    rc = first_run.main(["--detect", "--root", str(fake_sdcard)])
    assert rc == 0
    from call_cleaner import paths
    assert paths.config_path().exists()
    cfg = config_mod.load(paths.config_path())
    assert "calls" in cfg.paths


def test_main_falls_back_to_prompt_when_nothing_detected(tmp_home, fake_sdcard, monkeypatch):
    monkeypatch.setattr(first_run, "KNOWN_RECORDING_PATHS", {})
    real = fake_sdcard / "manual"
    real.mkdir()
    inputs = iter([f"manual={real}", ""])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    rc = first_run.main(["--detect", "--root", str(fake_sdcard)])
    assert rc == 0
    from call_cleaner import paths
    cfg = config_mod.load(paths.config_path())
    assert "manual" in cfg.paths
