from call_cleaner import state


def test_default_when_missing(tmp_path):
    p = tmp_path / "state.json"
    s = state.load(p)
    assert s.last_run_at is None
    assert s.last_run_preset is None
    assert s.last_run_trashed == 0
    assert s.last_run_freed_bytes == 0
    assert s.last_purge_at is None
    assert s.last_purge_removed == 0


def test_round_trip(tmp_path):
    p = tmp_path / "state.json"
    s = state.State(
        last_run_at=1714200000,
        last_run_preset="default",
        last_run_trashed=3,
        last_run_freed_bytes=19287654,
        last_purge_at=1714200030,
        last_purge_removed=0,
    )
    state.save(p, s)
    assert state.load(p) == s


def test_save_is_atomic_no_partial_file_on_crash(tmp_path, monkeypatch):
    p = tmp_path / "state.json"
    state.save(p, state.State(last_run_at=1, last_run_preset="x"))

    # Force the rename to fail; a partial tempfile should not become state.json.
    real_replace = state.os.replace

    def boom(src, dst):
        raise OSError("simulated failure")

    monkeypatch.setattr(state.os, "replace", boom)
    try:
        state.save(p, state.State(last_run_at=2, last_run_preset="y"))
    except OSError:
        pass
    monkeypatch.setattr(state.os, "replace", real_replace)
    # Original is intact.
    s = state.load(p)
    assert s.last_run_at == 1


def test_corrupt_file_returns_default(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{not valid json")
    s = state.load(p)
    assert s.last_run_at is None  # falls back to default rather than crashing
