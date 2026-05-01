"""argparse subcommand dispatch."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import config as config_mod
from . import doctor as doctor_mod
from . import install_schedule
from . import log as log_mod
from . import notifier
from . import paths as paths_mod
from . import scanner
from . import state as state_mod
from . import trash as trash_mod


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n} B" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def _load_config() -> config_mod.Config:
    return config_mod.load(paths_mod.config_path())


def _resolve_preset(cfg: config_mod.Config, name: str | None) -> config_mod.Preset:
    if name is None:
        name = cfg.default_preset
    if name not in cfg.presets:
        raise SystemExit(f"unknown preset: {name!r}")
    return cfg.presets[name]


def cmd_scan(args) -> int:
    cfg = _load_config()
    preset = _resolve_preset(cfg, args.preset)
    matches = scanner.scan_preset(preset)
    if not matches:
        print("nothing to clean.")
        return 0
    total = sum(m.size for m in matches)
    print(f"{len(matches)} file(s), {_human_size(total)} total (preset={preset.name}):")
    for m in matches:
        when = time.strftime("%Y-%m-%d", time.localtime(m.mtime))
        print(f"  {when}  {_human_size(m.size):>9}  {m.path}")
    return 0


_interrupt_requested = False


def _install_sigint_handler():
    import signal

    def _handler(signum, frame):
        global _interrupt_requested
        _interrupt_requested = True

    signal.signal(signal.SIGINT, _handler)


def cmd_run(args) -> int:
    global _interrupt_requested
    _interrupt_requested = False
    _install_sigint_handler()
    logger = log_mod.setup()
    cfg = _load_config()
    preset = _resolve_preset(cfg, args.preset)
    if not args.dry_run:
        # Skip on low battery or battery saver — exit 0 (skipping is normal).
        if notifier.is_low_battery():
            print("INFO: skipping run: low battery", file=sys.stderr)
            logger.info("skipping run: low battery")
            return 0
        if notifier.is_battery_saver_on():
            print("INFO: skipping run: battery saver on", file=sys.stderr)
            logger.info("skipping run: battery saver on")
            return 0
    matches = scanner.scan_preset(preset)
    if args.dry_run:
        return cmd_scan(args)
    if not matches:
        print("nothing to clean.")
        return 0
    bin_dir = Path(cfg.trash.dir)
    n = 0
    freed = 0
    for m in matches:
        try:
            cur_mtime = m.path.stat().st_mtime
        except OSError:
            print(f"INFO: vanished, skipping: {m.path}", file=sys.stderr)
            logger.info("vanished, skipping: %s", m.path)
            continue
        if cur_mtime != m.mtime:
            print(f"INFO: mtime changed since scan, skipping: {m.path}", file=sys.stderr)
            logger.info("mtime changed since scan, skipping: %s", m.path)
            continue
        if m.rule.action == "delete":
            try:
                m.path.unlink()
                n += 1
                freed += m.size
            except OSError as e:
                print(f"WARN: could not delete {m.path}: {e}", file=sys.stderr)
                logger.warning("could not delete %s: %s", m.path, e)
        else:
            try:
                trash_mod.trash_file(
                    m.path, bin_dir,
                    retention_days=cfg.trash.retention_days,
                    preset=preset.name,
                    rule_index=m.rule.rule_index,
                )
                n += 1
                freed += m.size
            except OSError as e:
                print(f"WARN: could not trash {m.path}: {e}", file=sys.stderr)
                logger.warning("could not trash %s: %s", m.path, e)
        if _interrupt_requested:
            print("INFO: interrupted, exiting cleanly.", file=sys.stderr)
            logger.info("interrupted, exiting cleanly.")
            break
    s = state_mod.load(paths_mod.state_path())
    s.last_run_at = int(time.time())
    s.last_run_preset = preset.name
    s.last_run_trashed = n
    s.last_run_freed_bytes = freed
    state_mod.save(paths_mod.state_path(), s)
    print(f"processed {n} file(s), freed {_human_size(freed)} (preset={preset.name})")
    logger.info("run complete: preset=%s trashed=%d freed=%d", preset.name, n, freed)
    # Notification on completion (best-effort; no-op if termux-api missing).
    if n > 0:
        notifier.notify("Call Cleaner", f"trashed {n}, freed {_human_size(freed)}")
    if notifier.is_low_storage():
        notifier.notify(
            "Storage low",
            "tap to open trash",
            action="cleaner trash list",
        )
    return 130 if _interrupt_requested else 0


def cmd_trash_list(args) -> int:
    cfg = _load_config()
    items = trash_mod.list_items(Path(cfg.trash.dir))
    if args.json:
        rows = [{
            "id": i.id,
            "original_path": i.original_path,
            "size_bytes": i.size_bytes,
            "trashed_at": i.trashed_at,
            "expires_at": i.expires_at,
            "orphaned": i.orphaned,
        } for i in items]
        print(json.dumps(rows, indent=2))
        return 0
    if not items:
        print("trash is empty.")
        return 0
    for i in items:
        when = time.strftime("%Y-%m-%d", time.localtime(i.trashed_at)) if i.trashed_at else "?"
        size = _human_size(i.size_bytes) if i.size_bytes is not None else "?"
        flag = " [ORPHAN]" if i.orphaned else ""
        print(f"  {i.id}  {when}  {size:>9}  {i.original_path}{flag}")
    return 0


def cmd_trash_restore(args) -> int:
    cfg = _load_config()
    try:
        target = trash_mod.restore(args.id, Path(cfg.trash.dir))
    except trash_mod.RestoreConflict as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"restored {target}")
    return 0


def cmd_trash_empty(args) -> int:
    cfg = _load_config()
    bin_dir = Path(cfg.trash.dir)
    items = trash_mod.list_items(bin_dir)
    if not items:
        print("trash already empty.")
        return 0
    if not args.force:
        ans = input(f"empty {len(items)} trash item(s)? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("aborted.")
            return 1
    n = trash_mod.empty(bin_dir)
    print(f"emptied {n} entr{'y' if n == 1 else 'ies'}.")
    return 0


def cmd_purge(args) -> int:
    logger = log_mod.setup()
    cfg = _load_config()
    n = trash_mod.purge(Path(cfg.trash.dir))
    s = state_mod.load(paths_mod.state_path())
    s.last_purge_at = int(time.time())
    s.last_purge_removed = n
    state_mod.save(paths_mod.state_path(), s)
    logger.info("purge complete: removed=%d", n)
    print(f"purged {n} expired item(s).")
    return 0


def cmd_config_init(args) -> int:
    p = config_mod.init()
    print(f"wrote {p}")
    return 0


def cmd_config_edit(args) -> int:
    p = paths_mod.config_path()
    config_mod.init(p)  # ensure exists
    editor = os.environ.get("EDITOR", "vi")
    subprocess.call([editor, str(p)])
    try:
        config_mod.load(p)
    except config_mod.ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("config valid.")
    return 0


def cmd_config_validate(args) -> int:
    try:
        config_mod.load(paths_mod.config_path())
    except config_mod.ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print("config valid.")
    return 0


def cmd_doctor(args) -> int:
    rep = doctor_mod.run()
    for m in rep.messages:
        print(m)
    print(f"status: {rep.status}")
    return 0 if rep.status == "ok" else (1 if rep.status == "warn" else 2)


def cmd_install_schedule(args) -> int:
    print(install_schedule.render())
    return 0


def cmd_tui(args) -> int:
    from . import tui
    return tui.run()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cleaner", description="Sweep old call recordings.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scan"); sp.add_argument("--preset"); sp.set_defaults(func=cmd_scan)
    sp = sub.add_parser("run")
    sp.add_argument("--preset"); sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_run)

    sp_t = sub.add_parser("trash")
    tsub = sp_t.add_subparsers(dest="trash_cmd", required=True)
    sp = tsub.add_parser("list"); sp.add_argument("--json", action="store_true"); sp.set_defaults(func=cmd_trash_list)
    sp = tsub.add_parser("restore"); sp.add_argument("id"); sp.set_defaults(func=cmd_trash_restore)
    sp = tsub.add_parser("empty"); sp.add_argument("--force", action="store_true"); sp.set_defaults(func=cmd_trash_empty)

    sp = sub.add_parser("purge"); sp.set_defaults(func=cmd_purge)

    sp_c = sub.add_parser("config")
    csub = sp_c.add_subparsers(dest="config_cmd", required=True)
    csub.add_parser("init").set_defaults(func=cmd_config_init)
    csub.add_parser("edit").set_defaults(func=cmd_config_edit)
    csub.add_parser("validate").set_defaults(func=cmd_config_validate)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("install-schedule").set_defaults(func=cmd_install_schedule)
    sub.add_parser("tui").set_defaults(func=cmd_tui)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
