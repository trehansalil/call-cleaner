"""Trash bin: move files to a trash dir with sidecar JSON metadata."""
from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


SIDECAR_EXT = ".json"


class RestoreConflict(Exception):
    """Raised when a restore target already exists."""


@dataclass(frozen=True)
class TrashItem:
    id: str
    payload: Path | None       # may be None when orphaned (sidecar with no payload)
    sidecar: Path | None       # may be None when orphaned (payload with no sidecar)
    original_path: str | None
    size_bytes: int | None
    mtime: float | None
    trashed_at: int | None
    expires_at: int | None
    preset: str | None
    rule_index: int | None
    orphaned: bool


def _new_id() -> str:
    # Use microsecond-resolution timestamp so IDs sort chronologically even
    # when two items are created within the same second.
    ts_us = int(time.time() * 1_000_000)
    return f"{ts_us:020d}-{uuid.uuid4().hex[:8]}"


def _payload_for(bin_dir: Path, id_: str) -> Path | None:
    matches = list(bin_dir.glob(f"{id_}.*"))
    matches = [m for m in matches if m.suffix != SIDECAR_EXT]
    return matches[0] if matches else None


def trash_file(
    src: Path,
    bin_dir: Path,
    *,
    retention_days: int,
    preset: str,
    rule_index: int,
    now: int | None = None,
) -> TrashItem:
    bin_dir.mkdir(parents=True, exist_ok=True)
    id_ = _new_id()
    ext = src.suffix
    payload = bin_dir / f"{id_}{ext}"
    sidecar = bin_dir / f"{id_}{SIDECAR_EXT}"
    now_ts = int(now if now is not None else time.time())
    st = src.stat()
    try:
        os.rename(src, payload)
    except OSError:
        shutil.move(str(src), str(payload))
    meta = {
        "id": id_,
        "original_path": str(src),
        "size_bytes": st.st_size,
        "mtime": st.st_mtime,
        "trashed_at": now_ts,
        "expires_at": now_ts + retention_days * 86400,
        "preset": preset,
        "rule_index": rule_index,
    }
    sidecar.write_text(json.dumps(meta, indent=2))
    return TrashItem(
        id=id_,
        payload=payload,
        sidecar=sidecar,
        original_path=meta["original_path"],
        size_bytes=meta["size_bytes"],
        mtime=meta["mtime"],
        trashed_at=meta["trashed_at"],
        expires_at=meta["expires_at"],
        preset=meta["preset"],
        rule_index=meta["rule_index"],
        orphaned=False,
    )


def list_items(bin_dir: Path) -> list[TrashItem]:
    if not bin_dir.is_dir():
        return []
    seen: dict[str, dict] = {}
    for entry in sorted(bin_dir.iterdir()):
        if entry.suffix == SIDECAR_EXT:
            id_ = entry.stem
            try:
                meta = json.loads(entry.read_text())
            except (OSError, json.JSONDecodeError):
                meta = {}
            seen.setdefault(id_, {})["sidecar"] = entry
            seen[id_]["meta"] = meta
        else:
            id_ = entry.stem
            seen.setdefault(id_, {})["payload"] = entry
    items: list[TrashItem] = []
    for id_, parts in sorted(seen.items()):
        sidecar = parts.get("sidecar")
        payload = parts.get("payload")
        meta = parts.get("meta", {})
        orphaned = sidecar is None or payload is None
        items.append(TrashItem(
            id=id_,
            payload=payload,
            sidecar=sidecar,
            original_path=meta.get("original_path"),
            size_bytes=meta.get("size_bytes"),
            mtime=meta.get("mtime"),
            trashed_at=meta.get("trashed_at"),
            expires_at=meta.get("expires_at"),
            preset=meta.get("preset"),
            rule_index=meta.get("rule_index"),
            orphaned=orphaned,
        ))
    return items


def restore(id_: str, bin_dir: Path) -> Path:
    sidecar = bin_dir / f"{id_}{SIDECAR_EXT}"
    payload = _payload_for(bin_dir, id_)
    if not sidecar.exists() or payload is None:
        raise FileNotFoundError(f"trash item {id_!r} not found or orphaned")
    meta = json.loads(sidecar.read_text())
    target = Path(meta["original_path"])
    if target.exists():
        raise RestoreConflict(f"{target} already exists; not overwriting")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.rename(payload, target)
    except OSError:
        shutil.move(str(payload), str(target))
    sidecar.unlink()
    return target


def purge(bin_dir: Path, *, now: float | None = None) -> int:
    if not bin_dir.is_dir():
        return 0
    if now is None:
        now = time.time()
    removed = 0
    for sidecar in list(bin_dir.glob(f"*{SIDECAR_EXT}")):
        try:
            meta = json.loads(sidecar.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        expires = meta.get("expires_at")
        if not isinstance(expires, (int, float)) or expires > now:
            continue
        payload = _payload_for(bin_dir, sidecar.stem)
        if payload and payload.exists():
            try:
                payload.unlink()
            except OSError:
                continue
        try:
            sidecar.unlink()
        except OSError:
            continue
        removed += 1
    return removed


def empty(bin_dir: Path) -> int:
    if not bin_dir.is_dir():
        return 0
    n = 0
    for entry in list(bin_dir.iterdir()):
        try:
            if entry.is_file():
                entry.unlink()
                n += 1
        except OSError:
            continue
    return n
