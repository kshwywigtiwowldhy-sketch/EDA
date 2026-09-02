"""Run-event logging and cryptographic artifact manifests."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return the lowercase SHA-256 digest of a file without loading it at once."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(
    paths: Iterable[str | Path],
    manifest_path: str | Path,
    *,
    base_dir: str | Path,
) -> Path:
    """Write sorted SHA-256 lines using portable paths relative to ``base_dir``."""

    base_dir = Path(base_dir).resolve()
    manifest_path = Path(manifest_path)
    entries: list[tuple[str, Path]] = []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Artifact missing while building manifest: {path}")
        try:
            relative = path.relative_to(base_dir).as_posix()
        except ValueError as exc:
            raise ValueError(f"Artifact is outside manifest base directory: {path}") from exc
        entries.append((relative, path))

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        for relative, path in sorted(entries, key=lambda entry: entry[0]):
            handle.write(f"{sha256_file(path)}  {relative}\n")
    return manifest_path


def append_event(path: str | Path, event: str, **payload: object) -> None:
    """Append one UTC-timestamped JSON object to an audit log."""

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

