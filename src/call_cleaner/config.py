"""TOML config parsing + validation."""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

_PRESET_NAME_RE = re.compile(r"^[a-z0-9_-]+$")
_VALID_ACTIONS = {"trash", "delete"}


class ConfigError(ValueError):
    """Raised on invalid or unreadable config."""


@dataclass(frozen=True)
class Rule:
    folder: str
    age_days: int
    action: str
    rule_index: int


@dataclass(frozen=True)
class Preset:
    name: str
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class TrashSettings:
    dir: str
    retention_days: int


@dataclass(frozen=True)
class Config:
    default_preset: str
    trash: TrashSettings
    paths: dict[str, str] = field(default_factory=dict)
    presets: dict[str, Preset] = field(default_factory=dict)


def default_template() -> str:
    return """\
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
"""


def init(path: Path | None = None) -> Path:
    """Write a default config file if it doesn't exist. Return its path."""
    if path is None:
        path = paths.config_path()
    paths.ensure_parent(path)
    if not path.exists():
        path.write_text(default_template())
    return path


def load(path: Path) -> Config:
    if not path.exists():
        raise ConfigError(f"config not found: {path}")
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"parse error: {e}") from e

    aliases = raw.get("paths", {}) or {}
    if not isinstance(aliases, dict) or not all(isinstance(v, str) for v in aliases.values()):
        raise ConfigError("[paths] must be a table of name = '/abs/path' strings")

    trash_raw = raw.get("trash", {})
    if not isinstance(trash_raw, dict):
        raise ConfigError("[trash] must be a table")
    trash_dir = trash_raw.get("dir", paths.DEFAULT_TRASH_DIR)
    retention = trash_raw.get("retention_days", 30)
    if not isinstance(retention, int) or retention <= 0:
        raise ConfigError("trash.retention_days must be a positive integer")
    if not isinstance(trash_dir, str):
        raise ConfigError("trash.dir must be a string")
    trash = TrashSettings(dir=trash_dir, retention_days=retention)

    presets_raw = raw.get("preset", {})
    if not isinstance(presets_raw, dict):
        raise ConfigError("[preset.<name>] sections must be tables")

    presets: dict[str, Preset] = {}
    for name, body in presets_raw.items():
        if not _PRESET_NAME_RE.match(name):
            raise ConfigError(f"invalid preset name {name!r}: must match [a-z0-9_-]+")
        rules_raw = body.get("rules") if isinstance(body, dict) else None
        if not isinstance(rules_raw, list) or not rules_raw:
            raise ConfigError(f"preset {name!r}: must have at least one [[preset.{name}.rules]] entry")
        rules: list[Rule] = []
        for i, r in enumerate(rules_raw):
            if not isinstance(r, dict):
                raise ConfigError(f"preset {name!r} rule #{i}: must be a table")
            folder = r.get("folder")
            age = r.get("age_days")
            action = r.get("action")
            if not isinstance(folder, str):
                raise ConfigError(f"preset {name!r} rule #{i}: folder must be a string")
            resolved = _resolve_alias(folder, aliases)
            if resolved is None:
                raise ConfigError(f"preset {name!r} rule #{i}: unknown alias {folder!r}")
            if not isinstance(age, int) or age < 0:
                raise ConfigError(f"preset {name!r} rule #{i}: age_days must be a non-negative integer")
            if action not in _VALID_ACTIONS:
                raise ConfigError(
                    f"preset {name!r} rule #{i}: action must be one of {sorted(_VALID_ACTIONS)}"
                )
            rules.append(Rule(folder=resolved, age_days=age, action=action, rule_index=i))
        presets[name] = Preset(name=name, rules=tuple(rules))

    default_preset = raw.get("default_preset")
    if not isinstance(default_preset, str) or default_preset not in presets:
        raise ConfigError(f"default_preset must name an existing preset (got {default_preset!r})")

    return Config(
        default_preset=default_preset,
        trash=trash,
        paths=dict(aliases),
        presets=presets,
    )


def _resolve_alias(folder: str, aliases: dict[str, str]) -> str | None:
    if folder.startswith("@"):
        return aliases.get(folder[1:])
    if folder.startswith("/"):
        return folder
    return None
