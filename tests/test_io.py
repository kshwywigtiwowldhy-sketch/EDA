from pathlib import Path

import pytest

from severstal_eda.io import load_config, validate_dataset


def test_load_config_resolves_paths_relative_to_config(tmp_path: Path):
    config_path = tmp_path / "config" / "eda.yaml"
    config_path.parent.mkdir()
    config_path.write_text(
        "dataset_dir: ../data\n"
        "output_dir: ../artifacts\n"
        "report_path: ../reports/report.md\n"
        "log_path: ../logs/events.jsonl\n"
        "manifest_path: ../artifacts/manifest.json\n"
        "image_height: 256\n"
        "image_width: 1600\n",
        encoding="utf-8",
    )

    loaded = load_config(config_path)

    assert loaded.dataset_dir == (config_path.parent / "../data").resolve()
    assert loaded.output_dir == (config_path.parent / "../artifacts").resolve()
    assert (loaded.image_height, loaded.image_width) == (256, 1600)


def test_validate_dataset_fails_closed_when_train_csv_is_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train.csv"):
        validate_dataset(tmp_path)


def test_validate_dataset_returns_all_required_paths(tmp_path: Path):
    (tmp_path / "train.csv").write_text("ImageId,ClassId,EncodedPixels\n", encoding="utf-8")
    (tmp_path / "sample_submission.csv").write_text("ImageId,EncodedPixels\n", encoding="utf-8")
    (tmp_path / "train_images").mkdir()
    (tmp_path / "test_images").mkdir()

    paths = validate_dataset(tmp_path)

    assert paths.train_csv == tmp_path / "train.csv"
    assert paths.train_images == tmp_path / "train_images"
    assert paths.test_images == tmp_path / "test_images"
