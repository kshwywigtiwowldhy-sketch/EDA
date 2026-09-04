from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).parents[1]
TRAIN_SHA256 = "4bd175ac3399a433f3f8164fa523e7eb982a40a0eff7b23ac731414bc1a84b0b"
VALID_SHA256 = "4f08d19ac713e179b5bb566e4819cf55e10a8c04b2a5fb0f8733f12b83eeef5f"
HANDOFF_SHA256 = "72faab26d057529de6d9d16b13ea13de0a7ae5dd4e40a1cea575649d59b32922"
EXPECTED_IMAGE_MEMBERS = {
    "01_data_audit/class_distribution.png",
    "01_data_audit/defect_examples.png",
    "02_eda/outputs/figures/cooccurrence_heatmap.png",
    "02_eda/outputs/figures/label_combinations.png",
    "02_eda/outputs/figures/label_frequency.png",
    "02_eda/outputs/figures/rare_label_samples.png",
    "02_eda/outputs/figures/representative_samples.png",
    "03_final_split_v2/evidence/cross_split_near_duplicates_1.png",
    "03_final_split_v2/evidence/cross_split_near_duplicates_2.png",
    "03_final_split_v2/evidence/cross_split_near_duplicates_3.png",
    "03_final_split_v2/figures/mask_area_split_distribution_v2.png",
    "03_final_split_v2/figures/split_distribution.png",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_ids(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_frozen_v2_split_is_complete_disjoint_and_headerless() -> None:
    train_path = ROOT / "03_final_split_v2/splits/train_ids.csv"
    valid_path = ROOT / "03_final_split_v2/splits/valid_ids.csv"
    train_ids = read_ids(train_path)
    valid_ids = read_ids(valid_path)

    assert train_ids[0].lower() != "imageid"
    assert valid_ids[0].lower() != "imageid"
    assert len(train_ids) == len(set(train_ids)) == 10_054
    assert len(valid_ids) == len(set(valid_ids)) == 2_514
    assert set(train_ids).isdisjoint(valid_ids)
    assert len(set(train_ids) | set(valid_ids)) == 12_568
    assert sha256(train_path) == TRAIN_SHA256
    assert sha256(valid_path) == VALID_SHA256


def test_machine_verification_matches_frozen_split() -> None:
    evidence = json.loads(
        (ROOT / "03_final_split_v2/evidence/split_v2_verification.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["train_count"] == 10_054
    assert evidence["valid_count"] == 2_514
    assert evidence["overlap"] == 0
    assert evidence["union"] == 12_568
    assert evidence["missing"] == 0
    assert evidence["unknown"] == 0
    assert evidence["strong_cross_split_near_duplicate_edges"] == 0
    assert evidence["train_sha256"] == TRAIN_SHA256
    assert evidence["valid_sha256"] == VALID_SHA256


def test_complete_handoff_archive_matches_external_hash() -> None:
    archive = ROOT / "deliverables/severstal_modeling_handoff_v2_20260902.zip"
    checksum = ROOT / "deliverables/severstal_modeling_handoff_v2_20260902.zip.sha256"
    assert sha256(archive) == HANDOFF_SHA256
    assert checksum.read_text(encoding="utf-8").split()[0] == HANDOFF_SHA256


def test_image_archive_contains_only_expected_png_files() -> None:
    archive = ROOT / "deliverables/severstal_handoff_images_v2_20260902.zip"
    checksum = ROOT / "deliverables/severstal_handoff_images_v2_20260902.zip.sha256"
    with zipfile.ZipFile(archive) as bundle:
        members = set(bundle.namelist())
        assert bundle.testzip() is None
    assert members == EXPECTED_IMAGE_MEMBERS
    assert all(
        not Path(name).is_absolute() and ".." not in Path(name).parts
        for name in members
    )
    assert checksum.read_text(encoding="utf-8").split()[0] == sha256(archive)


def test_handoff_docs_use_final_anonymous_v2_contract() -> None:
    readme = (ROOT / "README_建模交接必读.md").read_text(encoding="utf-8")
    split_report = (ROOT / "03_final_split_v2/split_report.md").read_text(
        encoding="utf-8"
    )
    combined = readme + split_report
    assert "header=None" in combined
    assert "5,902" in combined
    assert "class_1" in combined and "class_4" in combined
    assert "split_mask_area_distribution_v2.png" not in split_report
    assert "mask_area_split_distribution_v2.png" in split_report
