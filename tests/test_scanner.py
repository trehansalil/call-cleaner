import os
import time

import pytest

from call_cleaner import config, scanner


def make_file(path, *, age_days, size=10):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    mtime = time.time() - age_days * 86400
    os.utime(path, (mtime, mtime))


def rule(folder, age_days=90, action="trash", index=0):
    return config.Rule(folder=str(folder), age_days=age_days, action=action, rule_index=index)


def test_matches_old_audio_file(tmp_path):
    f = tmp_path / "old.mp3"
    make_file(f, age_days=120)
    matches = scanner.scan_rule(rule(tmp_path, age_days=90))
    assert [m.path for m in matches] == [f]


def test_skips_recent_file(tmp_path):
    make_file(tmp_path / "new.mp3", age_days=10)
    assert scanner.scan_rule(rule(tmp_path, age_days=90)) == []


def test_skips_non_audio(tmp_path):
    f = tmp_path / "old.txt"
    make_file(f, age_days=120)
    assert scanner.scan_rule(rule(tmp_path, age_days=90)) == []


def test_age_boundary_inclusive(tmp_path):
    f = tmp_path / "exactly.mp3"
    make_file(f, age_days=90)
    matches = scanner.scan_rule(rule(tmp_path, age_days=90))
    assert [m.path for m in matches] == [f]


def test_skips_hidden(tmp_path):
    make_file(tmp_path / ".hidden.mp3", age_days=120)
    assert scanner.scan_rule(rule(tmp_path, age_days=90)) == []


def test_non_recursive(tmp_path):
    sub = tmp_path / "sub"
    make_file(sub / "buried.mp3", age_days=120)
    assert scanner.scan_rule(rule(tmp_path, age_days=90)) == []


def test_missing_folder_returns_empty(tmp_path):
    missing = tmp_path / "nope"
    assert scanner.scan_rule(rule(missing)) == []


def test_all_audio_extensions(tmp_path):
    exts = [".mp3", ".m4a", ".amr", ".aac", ".wav", ".opus", ".3gp", ".ogg"]
    for i, ext in enumerate(exts):
        make_file(tmp_path / f"f{i}{ext}", age_days=120)
    matches = scanner.scan_rule(rule(tmp_path, age_days=90))
    assert len(matches) == len(exts)


def test_extensions_case_insensitive(tmp_path):
    make_file(tmp_path / "UPPER.MP3", age_days=120)
    matches = scanner.scan_rule(rule(tmp_path, age_days=90))
    assert len(matches) == 1


def test_match_carries_size_and_mtime(tmp_path):
    f = tmp_path / "old.mp3"
    make_file(f, age_days=120, size=42)
    [m] = scanner.scan_rule(rule(tmp_path, age_days=90))
    assert m.size == 42
    assert m.mtime > 0
    assert m.rule.action == "trash"


def test_scan_preset_iterates_rules(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    make_file(a / "x.mp3", age_days=120)
    make_file(b / "y.m4a", age_days=200)
    preset = config.Preset(
        name="default",
        rules=(rule(a, age_days=90, index=0), rule(b, age_days=180, index=1)),
    )
    matches = scanner.scan_preset(preset)
    assert {m.path.name for m in matches} == {"x.mp3", "y.m4a"}
