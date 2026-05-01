# tests/test_e2e.py
import json
import os
import time

import pytest

from call_cleaner import cli, paths


def test_full_run_then_restore(tmp_home, fake_sdcard, capsys, monkeypatch):
    """
    Build a tree with mtimes spread over 200 days, run preset default,
    assert the right files moved into trash, then restore one and confirm
    it lands back at its original path.
    """
    # 1. Lay out a fake /sdcard.
    src = fake_sdcard / "Music" / "Recordings" / "Call Recordings"
    src.mkdir(parents=True)
    files = {}
    for days, name in [(200, "ancient.mp3"), (95, "older.m4a"), (10, "fresh.mp3")]:
        p = src / name
        p.write_bytes(b"x" * 100)
        mt = time.time() - days * 86400
        os.utime(p, (mt, mt))
        files[name] = (p, days)

    # Non-audio file should be ignored even if old.
    junk = src / "notes.txt"
    junk.write_bytes(b"junk")
    mt = time.time() - 200 * 86400
    os.utime(junk, (mt, mt))

    # 2. Write config.
    cfg = tmp_home / ".config" / "call-cleaner" / "config.toml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(f"""\
default_preset = "default"
[trash]
dir = "{fake_sdcard}/.CallCleanerTrash"
retention_days = 30
[paths]
calls = "{src}"
[[preset.default.rules]]
folder = "@calls"
age_days = 90
action = "trash"
""")

    # 3. Run `cleaner run`.
    rc = cli.main(["run"])
    assert rc == 0
    assert not files["ancient.mp3"][0].exists()
    assert not files["older.m4a"][0].exists()
    assert files["fresh.mp3"][0].exists()      # too new
    assert junk.exists()                        # non-audio

    # 4. Trash list shows two items.
    capsys.readouterr()
    cli.main(["trash", "list", "--json"])
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 2

    # 5. Restore one and assert it landed in its original folder.
    target_id = next(r["id"] for r in rows if r["original_path"].endswith("ancient.mp3"))
    rc = cli.main(["trash", "restore", target_id])
    assert rc == 0
    assert files["ancient.mp3"][0].exists()

    # 6. State reflects the run.
    state_path = paths.state_path()
    state_doc = json.loads(state_path.read_text())
    assert state_doc["last_run_preset"] == "default"
    assert state_doc["last_run_trashed"] == 2
    assert state_doc["last_run_freed_bytes"] >= 200
