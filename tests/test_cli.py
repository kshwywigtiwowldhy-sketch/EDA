import json
from pathlib import Path

import pandas as pd
from PIL import Image
import pytest

from severstal_eda.cli import run_eda


def make_synthetic_project(tmp_path: Path, *, include_train_csv: bool = True) -> Path:
    dataset = tmp_path / "dataset"
    train_images = dataset / "train_images"
    test_images = dataset / "test_images"
    train_images.mkdir(parents=True)
    test_images.mkdir()
    for image_id in ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]:
        Image.new("RGB", (4, 4), color=(100, 110, 120)).save(train_images / image_id)
    Image.new("RGB", (4, 4), color=(80, 80, 80)).save(test_images / "test.jpg")
    if include_train_csv:
        pd.DataFrame(
            {
                "ImageId": ["a.jpg", "b.jpg", "c.jpg", "c.jpg"],
                "ClassId": [1, 2, 3, 4],
                "EncodedPixels": ["1 2", "3 2", "5 2", "7 2"],
            }
        ).to_csv(dataset / "train.csv", index=False)
    pd.DataFrame(
        {"ImageId": ["test.jpg"], "EncodedPixels": [""]}
    ).to_csv(dataset / "sample_submission.csv", index=False)

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "eda.yaml"
    config_path.write_text(
        f"dataset_dir: {dataset.as_posix()}\n"
        "output_dir: ../outputs\n"
        "report_path: ../reports/eda_report.md\n"
        "log_path: ../logs/eda_run.jsonl\n"
        "manifest_path: ../MANIFEST.sha256\n"
        "image_height: 4\n"
        "image_width: 4\n"
        "seed: 42\n"
        "samples_per_group: 4\n",
        encoding="utf-8",
    )
    return config_path


def test_run_eda_writes_complete_audited_deliverables(tmp_path: Path):
    config_path = make_synthetic_project(tmp_path)

    result = run_eda(config_path)

    expected_tables = {
        "image_label_table.csv",
        "label_frequency.csv",
        "label_combinations.csv",
        "cooccurrence_counts.csv",
        "cooccurrence_conditional.csv",
        "mask_area_statistics.csv",
        "rare_classes.csv",
        "rare_combinations.csv",
        "selected_samples.csv",
    }
    expected_figures = {
        "label_frequency.png",
        "label_combinations.png",
        "cooccurrence_heatmap.png",
        "representative_samples.png",
        "rare_label_samples.png",
    }
    assert {path.name for path in (tmp_path / "outputs" / "tables").glob("*.csv")} == expected_tables
    assert {path.name for path in (tmp_path / "outputs" / "figures").glob("*.png")} == expected_figures
    assert (tmp_path / "outputs" / "run_summary.json").exists()
    assert (tmp_path / "reports" / "eda_report.md").exists()
    assert (tmp_path / "MANIFEST.sha256").exists()
    events = [
        json.loads(line)["event"]
        for line in (tmp_path / "logs" / "eda_run.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert events == ["run_started", "run_succeeded"]
    assert result.summary["train_images"] == 4
    assert result.summary["no_defect_images"] == 1


def test_run_eda_records_failure_when_required_input_is_missing(tmp_path: Path):
    config_path = make_synthetic_project(tmp_path, include_train_csv=False)

    with pytest.raises(FileNotFoundError, match="train.csv"):
        run_eda(config_path)

    records = [
        json.loads(line)
        for line in (tmp_path / "logs" / "eda_run.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [record["event"] for record in records] == ["run_started", "run_failed"]
    assert records[-1]["exception_type"] == "FileNotFoundError"
