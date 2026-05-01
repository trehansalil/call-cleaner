from call_cleaner import paths


def test_config_path_under_xdg_default(tmp_home):
    assert paths.config_path() == tmp_home / ".config" / "call-cleaner" / "config.toml"


def test_config_path_respects_xdg_config_home(tmp_home, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_home / "cfg"))
    assert paths.config_path() == tmp_home / "cfg" / "call-cleaner" / "config.toml"


def test_state_path_under_xdg_default(tmp_home):
    assert paths.state_path() == tmp_home / ".local" / "share" / "call-cleaner" / "state.json"


def test_log_path_under_xdg_default(tmp_home):
    assert paths.log_path() == tmp_home / ".local" / "share" / "call-cleaner" / "run.log"


def test_default_trash_dir():
    assert paths.DEFAULT_TRASH_DIR == "/sdcard/.CallCleanerTrash"


def test_data_dir_respects_xdg_data_home(tmp_home, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_home / "data"))
    assert paths.state_path() == tmp_home / "data" / "call-cleaner" / "state.json"
    assert paths.log_path() == tmp_home / "data" / "call-cleaner" / "run.log"


def test_ensure_parent_creates_missing_dirs(tmp_path):
    target = tmp_path / "a" / "b" / "c.txt"
    paths.ensure_parent(target)
    assert (tmp_path / "a" / "b").is_dir()
