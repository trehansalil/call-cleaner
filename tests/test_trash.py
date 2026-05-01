# tests/test_trash.py
import json
import os
import time

import pytest

from call_cleaner import trash


def make_file(p, content=b"abc"):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)


def test_trash_moves_file_and_writes_sidecar(tmp_path):
    src = tmp_path / "src" / "song.mp3"
    make_file(src, b"hello")
    bin_dir = tmp_path / "trash"
    item = trash.trash_file(src, bin_dir, retention_days=30, preset="default", rule_index=0)
    assert not src.exists()
    payload = bin_dir / f"{item.id}.mp3"
    sidecar = bin_dir / f"{item.id}.json"
    assert payload.exists()
    assert payload.read_bytes() == b"hello"
    assert sidecar.exists()
    meta = json.loads(sidecar.read_text())
    assert meta["original_path"] == str(src)
    assert meta["preset"] == "default"
    assert meta["rule_index"] == 0
    assert meta["expires_at"] - meta["trashed_at"] == 30 * 86400


def test_list_round_trip(tmp_path):
    src = tmp_path / "x.mp3"
    make_file(src)
    bin_dir = tmp_path / "trash"
    item = trash.trash_file(src, bin_dir, retention_days=30, preset="default", rule_index=0)
    items = trash.list_items(bin_dir)
    ids = [i.id for i in items]
    assert item.id in ids
    found = next(i for i in items if i.id == item.id)
    assert found.original_path == str(src)
    assert found.orphaned is False


def test_restore_returns_file(tmp_path):
    src = tmp_path / "y.m4a"
    make_file(src, b"yo")
    bin_dir = tmp_path / "trash"
    item = trash.trash_file(src, bin_dir, retention_days=30, preset="default", rule_index=0)
    assert not src.exists()
    trash.restore(item.id, bin_dir)
    assert src.exists()
    assert src.read_bytes() == b"yo"
    assert not (bin_dir / f"{item.id}.json").exists()


def test_restore_refuses_overwrite(tmp_path):
    src = tmp_path / "z.mp3"
    make_file(src, b"original")
    bin_dir = tmp_path / "trash"
    item = trash.trash_file(src, bin_dir, retention_days=30, preset="default", rule_index=0)
    make_file(src, b"new content")
    with pytest.raises(trash.RestoreConflict):
        trash.restore(item.id, bin_dir)
    # Trash entry still intact
    assert (bin_dir / f"{item.id}.json").exists()


def test_restore_creates_parent_dirs(tmp_path):
    src = tmp_path / "deep" / "tree" / "a.mp3"
    make_file(src, b"abc")
    bin_dir = tmp_path / "trash"
    item = trash.trash_file(src, bin_dir, retention_days=30, preset="default", rule_index=0)
    # Remove parent tree
    import shutil
    shutil.rmtree(tmp_path / "deep")
    trash.restore(item.id, bin_dir)
    assert src.exists()


def test_purge_deletes_only_expired(tmp_path):
    src1 = tmp_path / "old.mp3"
    src2 = tmp_path / "fresh.mp3"
    make_file(src1)
    make_file(src2)
    bin_dir = tmp_path / "trash"
    expired = trash.trash_file(src1, bin_dir, retention_days=30, preset="x", rule_index=0)
    fresh = trash.trash_file(src2, bin_dir, retention_days=30, preset="x", rule_index=0)
    # Backdate expired
    sidecar = bin_dir / f"{expired.id}.json"
    meta = json.loads(sidecar.read_text())
    meta["expires_at"] = int(time.time()) - 1
    sidecar.write_text(json.dumps(meta))
    removed = trash.purge(bin_dir)
    assert removed == 1
    assert not (bin_dir / f"{expired.id}.mp3").exists()
    assert (bin_dir / f"{fresh.id}.mp3").exists()


def test_empty_removes_all_including_orphans(tmp_path):
    src = tmp_path / "a.mp3"
    make_file(src)
    bin_dir = tmp_path / "trash"
    trash.trash_file(src, bin_dir, retention_days=30, preset="x", rule_index=0)
    # Drop a stray payload + a stray sidecar
    (bin_dir / "orphan.mp3").write_bytes(b"x")
    (bin_dir / "orphan-sidecar.json").write_text("{}")
    n = trash.empty(bin_dir)
    assert n == 4  # 2 from real + 2 orphans
    assert list(bin_dir.iterdir()) == []


def test_list_flags_orphans(tmp_path):
    bin_dir = tmp_path / "trash"
    bin_dir.mkdir()
    (bin_dir / "lonely.mp3").write_bytes(b"x")
    items = trash.list_items(bin_dir)
    assert len(items) == 1
    assert items[0].orphaned is True
    assert items[0].original_path is None


def test_id_format_is_sortable(tmp_path):
    src = tmp_path / "a.mp3"
    make_file(src)
    bin_dir = tmp_path / "trash"
    a = trash.trash_file(src, bin_dir, retention_days=30, preset="x", rule_index=0)
    make_file(src, b"b")
    b = trash.trash_file(src, bin_dir, retention_days=30, preset="x", rule_index=0)
    assert a.id < b.id  # newer ids sort after older ones lexicographically


def test_trash_dir_is_created(tmp_path):
    src = tmp_path / "a.mp3"
    make_file(src)
    bin_dir = tmp_path / "trash" / "nested"  # does not exist
    trash.trash_file(src, bin_dir, retention_days=30, preset="x", rule_index=0)
    assert bin_dir.is_dir()
