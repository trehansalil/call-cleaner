import logging

import pytest


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """A throwaway $HOME with empty XDG dirs."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    return home


@pytest.fixture
def fake_sdcard(tmp_path):
    """A throwaway /sdcard root for filesystem tests."""
    sdcard = tmp_path / "sdcard"
    sdcard.mkdir()
    return sdcard


@pytest.fixture(autouse=True)
def _reset_call_cleaner_logger():
    yield
    logger = logging.getLogger("call_cleaner")
    for h in list(logger.handlers):
        logger.removeHandler(h)
