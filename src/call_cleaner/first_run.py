"""Auto-detect known call-recording paths and seed a starter config.toml.

Used by install.sh on Termux side. Falls back to interactive line-by-line
input if detection finds nothing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import paths as paths_mod

# Map: alias name → relative path under the scan root (default /sdcard).
KNOWN_RECORDING_PATHS: dict[str, str] = {
    "oneplus_calls":   "Music/Recordings/Call Recordings",
    "oneplus_callapp": "Music/CallAppRecording",
    "oneplus_voice":   "Music/Recordings/Standard Recordings",
    "samsung_calls":   "Recordings/Call",
    "xiaomi_calls":    "MIUI/sound_recorder/call_rec",
    "google_phone":    "Recordings",
    "generic_calls":   "Call Recordings",
}


def detect(root: str = "/sdcard") -> dict[str, str]:
    """Return aliases pointing at directories that exist under `root`."""
    out: dict[str, str] = {}
    root_path = Path(root)
    if not root_path.is_dir():
        return out
    for alias, rel in KNOWN_RECORDING_PATHS.items():
        full = root_path / rel
        if full.is_dir():
            out[alias] = str(full)
    return out


def write_seeded_config(path: Path, found: dict[str, str]) -> None:
    """Write a config.toml from detected aliases. Raises ValueError if empty."""
    if not found:
        raise ValueError("need at least one folder; none provided")
    paths_mod.ensure_parent(path)
    lines = [
        'default_preset = "default"',
        "",
        "[trash]",
        f'dir = "{paths_mod.DEFAULT_TRASH_DIR}"',
        "retention_days = 30",
        "",
        "[paths]",
    ]
    for alias, abs_path in found.items():
        lines.append(f'{alias} = "{abs_path}"')
    lines.append("")
    for alias in found:
        lines.append(f"[[preset.default.rules]]")
        lines.append(f'folder = "@{alias}"')
        lines.append(f"age_days = 90")
        lines.append(f'action = "trash"')
        lines.append("")
    path.write_text("\n".join(lines))


def interactive_prompt() -> dict[str, str]:
    """Read `name=/abs/path` lines from stdin until blank. Skip invalid lines."""
    print("No known call-recording folders auto-detected.", file=sys.stderr)
    print("Enter your folders one per line as 'name=/abs/path' (blank line to finish):", file=sys.stderr)
    found: dict[str, str] = {}
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break
        if not line:
            break
        if "=" not in line:
            print(f"  skipped (no '='): {line!r}", file=sys.stderr)
            continue
        name, _, path = line.partition("=")
        name = name.strip()
        path = path.strip()
        if not name or not path:
            print(f"  skipped (empty name or path): {line!r}", file=sys.stderr)
            continue
        if not path.startswith("/"):
            print(f"  skipped (not absolute): {path!r}", file=sys.stderr)
            continue
        if not Path(path).is_dir():
            print(f"  skipped (not a directory): {path!r}", file=sys.stderr)
            continue
        found[name] = path
    return found


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="call_cleaner.first_run")
    p.add_argument("--detect", action=argparse.BooleanOptionalAction, default=True,
                   help="auto-detect known recording paths under --root (default: --detect)")
    p.add_argument("--root", default="/sdcard",
                   help="path to scan for known recording folders")
    args = p.parse_args(argv)

    found: dict[str, str] = {}
    if args.detect:
        found = detect(root=args.root)
    if not found:
        found = interactive_prompt()
    if not found:
        print("ERROR: no folders provided.", file=sys.stderr)
        print("Run `cleaner config edit` later to add some.", file=sys.stderr)
        return 1
    cfg_path = paths_mod.config_path()
    write_seeded_config(cfg_path, found)
    print(f"wrote {cfg_path} with {len(found)} folder(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
