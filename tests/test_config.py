import pytest

from call_cleaner import config


def write(tmp_path, body):
    p = tmp_path / "config.toml"
    p.write_text(body)
    return p


VALID = """\
default_preset = "default"

[trash]
dir = "/sdcard/.CallCleanerTrash"
retention_days = 30

[paths]
calls = "/sdcard/Music/Recordings/Call Recordings"
callapp = "/sdcard/Music/CallAppRecording"

[[preset.default.rules]]
folder = "@calls"
age_days = 90
action = "trash"

[[preset.default.rules]]
folder = "@callapp"
age_days = 90
action = "trash"

[[preset.aggressive.rules]]
folder = "@calls"
age_days = 14
action = "trash"
"""


def test_parses_valid(tmp_path):
    cfg = config.load(write(tmp_path, VALID))
    assert cfg.default_preset == "default"
    assert cfg.trash.dir == "/sdcard/.CallCleanerTrash"
    assert cfg.trash.retention_days == 30
    assert set(cfg.presets) == {"default", "aggressive"}
    assert len(cfg.presets["default"].rules) == 2


def test_alias_resolution(tmp_path):
    cfg = config.load(write(tmp_path, VALID))
    rule = cfg.presets["default"].rules[0]
    assert rule.folder == "/sdcard/Music/Recordings/Call Recordings"


def test_literal_path_passes_through(tmp_path):
    body = VALID + """
[[preset.lit.rules]]
folder = "/sdcard/SomeFolder"
age_days = 30
action = "delete"
"""
    cfg = config.load(write(tmp_path, body))
    assert cfg.presets["lit"].rules[0].folder == "/sdcard/SomeFolder"


def test_default_preset_must_exist(tmp_path):
    body = VALID.replace('"default"', '"missing"', 1)
    with pytest.raises(config.ConfigError, match="default_preset"):
        config.load(write(tmp_path, body))


def test_unknown_alias(tmp_path):
    body = VALID.replace('"@calls"', '"@nope"', 1)
    with pytest.raises(config.ConfigError, match="alias.*nope"):
        config.load(write(tmp_path, body))


def test_negative_age(tmp_path):
    body = VALID.replace("age_days = 90", "age_days = -1", 1)
    with pytest.raises(config.ConfigError, match="age_days"):
        config.load(write(tmp_path, body))


def test_invalid_action(tmp_path):
    body = VALID.replace('action = "trash"', 'action = "burn"', 1)
    with pytest.raises(config.ConfigError, match="action"):
        config.load(write(tmp_path, body))


def test_bad_preset_name(tmp_path):
    body = VALID + """
[[preset."BadName!".rules]]
folder = "@calls"
age_days = 1
action = "trash"
"""
    with pytest.raises(config.ConfigError, match="preset name"):
        config.load(write(tmp_path, body))


def test_zero_retention(tmp_path):
    body = VALID.replace("retention_days = 30", "retention_days = 0")
    with pytest.raises(config.ConfigError, match="retention_days"):
        config.load(write(tmp_path, body))


def test_malformed_toml(tmp_path):
    with pytest.raises(config.ConfigError, match="parse"):
        config.load(write(tmp_path, "this is = = not toml"))


def test_missing_file(tmp_path):
    with pytest.raises(config.ConfigError, match="not found"):
        config.load(tmp_path / "nope.toml")


def test_default_template():
    body = config.default_template()
    assert "default_preset" in body
    assert "[[preset.default.rules]]" in body
    # Round-trips without error.
    import tomllib
    tomllib.loads(body)


def test_init_writes_template_when_absent(tmp_home):
    p = config.init()
    assert p.exists()
    assert "default_preset" in p.read_text()


def test_init_does_not_overwrite(tmp_home):
    p = config.init()
    p.write_text("custom = true\n")
    p2 = config.init()
    assert p == p2
    assert p.read_text() == "custom = true\n"


def test_age_days_zero_is_valid(tmp_path):
    body = VALID.replace("age_days = 90", "age_days = 0", 1)
    cfg = config.load(write(tmp_path, body))
    assert cfg.presets["default"].rules[0].age_days == 0


def test_age_days_bool_rejected(tmp_path):
    body = VALID.replace("age_days = 90", "age_days = true", 1)
    with pytest.raises(config.ConfigError, match="age_days"):
        config.load(write(tmp_path, body))


def test_retention_days_bool_rejected(tmp_path):
    body = VALID.replace("retention_days = 30", "retention_days = true")
    with pytest.raises(config.ConfigError, match="retention_days"):
        config.load(write(tmp_path, body))


def test_alias_must_be_absolute(tmp_path):
    body = VALID.replace(
        '"/sdcard/Music/Recordings/Call Recordings"',
        '"relative/path"',
    )
    with pytest.raises(config.ConfigError, match="relative"):
        config.load(write(tmp_path, body))
