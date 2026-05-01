import json
from unittest.mock import patch

import pytest

from call_cleaner import notifier


# A helper that builds a fake CompletedProcess.
class FakeCP:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_termux_api_available_true_when_which_succeeds(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=0))
    assert notifier.termux_api_available() is True


def test_termux_api_available_false_when_which_fails(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=1))
    assert notifier.termux_api_available() is False


def test_termux_api_available_false_when_binary_missing(monkeypatch):
    def boom(*a, **kw):
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(notifier.subprocess, "run", boom)
    assert notifier.termux_api_available() is False


def test_notify_returns_true_on_success(monkeypatch):
    calls = []

    def fake_run(args, **kw):
        calls.append(args)
        return FakeCP(returncode=0)

    monkeypatch.setattr(notifier.subprocess, "run", fake_run)
    ok = notifier.notify("hello", "world")
    assert ok is True
    # First call is `which`, second is termux-notification.
    assert any("termux-notification" in c[0] for c in calls)
    nargs = next(c for c in calls if c[0] == "termux-notification")
    assert "--title" in nargs and "hello" in nargs
    assert "--content" in nargs and "world" in nargs


def test_notify_returns_false_when_binary_missing(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=1))
    assert notifier.notify("t", "c") is False


def test_notify_passes_action_when_provided(monkeypatch):
    args_seen = []

    def fake_run(args, **kw):
        args_seen.append(args)
        return FakeCP(returncode=0)

    monkeypatch.setattr(notifier.subprocess, "run", fake_run)
    notifier.notify("t", "c", action="cleaner trash list")
    nargs = next(a for a in args_seen if a[0] == "termux-notification")
    assert "--action" in nargs
    i = nargs.index("--action")
    assert nargs[i + 1] == "cleaner trash list"


def test_is_low_battery_below_threshold(monkeypatch):
    payload = json.dumps({"percentage": 15, "status": "DISCHARGING"})

    def fake_run(args, **kw):
        if args[0] == "termux-battery-status":
            return FakeCP(returncode=0, stdout=payload)
        return FakeCP(returncode=0)

    monkeypatch.setattr(notifier.subprocess, "run", fake_run)
    assert notifier.is_low_battery(percent=20) is True


def test_is_low_battery_above_threshold(monkeypatch):
    payload = json.dumps({"percentage": 80, "status": "DISCHARGING"})
    monkeypatch.setattr(
        notifier.subprocess, "run",
        lambda args, **kw: FakeCP(returncode=0, stdout=payload) if args[0] == "termux-battery-status" else FakeCP(returncode=0),
    )
    assert notifier.is_low_battery(percent=20) is False


def test_is_low_battery_false_when_unavailable(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=1))
    assert notifier.is_low_battery() is False


def test_is_low_battery_charging_does_not_count_as_low(monkeypatch):
    payload = json.dumps({"percentage": 5, "status": "CHARGING"})
    monkeypatch.setattr(
        notifier.subprocess, "run",
        lambda args, **kw: FakeCP(returncode=0, stdout=payload) if args[0] == "termux-battery-status" else FakeCP(returncode=0),
    )
    assert notifier.is_low_battery(percent=20) is False


def test_is_battery_saver_on(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=0, stdout="off"))
    assert notifier.is_battery_saver_on() is False


def test_is_battery_saver_on_when_enabled(monkeypatch):
    monkeypatch.setattr(notifier.subprocess, "run", lambda *a, **kw: FakeCP(returncode=0, stdout="on"))
    assert notifier.is_battery_saver_on() is True


def test_is_low_storage_below_threshold(tmp_path, monkeypatch):
    fake = (100 * 1024**3, 99 * 1024**3, 1 * 1024**3)  # 1 GB free
    monkeypatch.setattr(notifier.shutil, "disk_usage", lambda p: fake)
    assert notifier.is_low_storage(str(tmp_path), gb_threshold=2.0) is True


def test_is_low_storage_above_threshold(tmp_path, monkeypatch):
    fake = (100 * 1024**3, 90 * 1024**3, 10 * 1024**3)  # 10 GB free
    monkeypatch.setattr(notifier.shutil, "disk_usage", lambda p: fake)
    assert notifier.is_low_storage(str(tmp_path), gb_threshold=2.0) is False


def test_is_low_storage_false_when_path_missing(tmp_path, monkeypatch):
    def boom(p):
        raise FileNotFoundError("no such path")

    monkeypatch.setattr(notifier.shutil, "disk_usage", boom)
    assert notifier.is_low_storage("/nonexistent") is False
