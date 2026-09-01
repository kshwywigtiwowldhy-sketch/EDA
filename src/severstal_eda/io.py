"""Configuration and read-only dataset input helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class EDAConfig:
    """Immutable settings for one reproducible EDA run."""

    dataset_dir: Path
    output_dir: Path
    report_path: Path
    log_path: Path
    manifest_path: Path
    image_height: int = 256
    image_width: int = 1600
    seed: int = 42
    samples_per_group: int = 4
    class_colors: dict[str, str] | None = None


@dataclass(frozen=True)
class DatasetPaths:
    """Validated locations of the official competition inputs."""

    train_csv: Path
    sample_submission: Path
    train_images: Path
    test_images: Path


def _resolve_path(value: str | Path, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_config(config_path: str | Path) -> EDAConfig:
    """Load YAML settings and resolve every path relative to the YAML file."""

    config_path = Path(config_path).resolve()
    with config_path.open("r", encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    required = ("dataset_dir", "output_dir", "report_path", "log_path", "manifest_path")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Missing required configuration keys: {', '.join(missing)}")

    base_dir = config_path.parent
    return EDAConfig(
        dataset_dir=_resolve_path(raw["dataset_dir"], base_dir),
        output_dir=_resolve_path(raw["output_dir"], base_dir),
        report_path=_resolve_path(raw["report_path"], base_dir),
        log_path=_resolve_path(raw["log_path"], base_dir),
        manifest_path=_resolve_path(raw["manifest_path"], base_dir),
        image_height=int(raw.get("image_height", 256)),
        image_width=int(raw.get("image_width", 1600)),
        seed=int(raw.get("seed", 42)),
        samples_per_group=int(raw.get("samples_per_group", 4)),
        class_colors={str(key): str(value) for key, value in raw.get("class_colors", {}).items()},
    )


def validate_dataset(dataset_dir: str | Path) -> DatasetPaths:
    """Return official input paths, failing before analysis if any are missing."""

    dataset_dir = Path(dataset_dir).resolve()
    paths = DatasetPaths(
        train_csv=dataset_dir / "train.csv",
        sample_submission=dataset_dir / "sample_submission.csv",
        train_images=dataset_dir / "train_images",
        test_images=dataset_dir / "test_images",
    )
    for required in (
        paths.train_csv,
        paths.sample_submission,
        paths.train_images,
        paths.test_images,
    ):
        if not required.exists():
            raise FileNotFoundError(f"Required dataset input missing: {required}")
    return paths

