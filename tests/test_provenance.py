import hashlib
import json
from pathlib import Path

from severstal_eda.provenance import append_event, sha256_file, write_manifest


def test_manifest_is_sorted_and_hashes_outputs(tmp_path: Path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = tmp_path / "MANIFEST.sha256"

    write_manifest(
        [tmp_path / "b.txt", tmp_path / "a.txt"],
        manifest,
        base_dir=tmp_path,
    )

    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("  a.txt")
    assert lines[1].endswith("  b.txt")
    assert sha256_file(tmp_path / "a.txt") == hashlib.sha256(b"a").hexdigest()


def test_append_event_writes_one_json_object_per_line(tmp_path: Path):
    log_path = tmp_path / "logs" / "events.jsonl"

    append_event(log_path, "run_started", seed=42)
    append_event(log_path, "run_succeeded", outputs=5)

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event"] for record in records] == ["run_started", "run_succeeded"]
    assert records[0]["seed"] == 42
    assert all(record["timestamp_utc"].endswith("+00:00") for record in records)

