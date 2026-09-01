import pandas as pd
import pytest

from severstal_eda.labels import build_image_label_table, normalize_annotations


def test_unannotated_images_become_no_defect_rows():
    annotations = pd.DataFrame(
        {
            "ImageId": ["a.jpg", "a.jpg", "b.jpg"],
            "ClassId": [1, 3, 2],
            "EncodedPixels": ["1 1", "4 1", "2 1"],
        }
    )

    table = build_image_label_table(annotations, ["a.jpg", "b.jpg", "c.jpg"])
    indexed = table.set_index("ImageId")

    assert bool(indexed.loc["c.jpg", "no_defect"])
    assert indexed.loc["c.jpg", ["class_1", "class_2", "class_3", "class_4"]].sum() == 0
    assert indexed.loc["a.jpg", "combination"] == "1+3"


def test_normalize_annotations_supports_legacy_compound_identifier():
    legacy = pd.DataFrame(
        {
            "ImageId_ClassId": ["steel_part_01.jpg_4", "steel_part_01.jpg_1"],
            "EncodedPixels": ["3 2", "1 1"],
        }
    )

    normalized = normalize_annotations(legacy)

    assert normalized["ImageId"].tolist() == ["steel_part_01.jpg", "steel_part_01.jpg"]
    assert normalized["ClassId"].tolist() == [1, 4]


def test_empty_encoded_pixels_are_not_treated_as_positive_labels():
    annotations = pd.DataFrame(
        {
            "ImageId": ["a.jpg", "b.jpg"],
            "ClassId": [1, 2],
            "EncodedPixels": [None, "  "],
        }
    )

    table = build_image_label_table(annotations, ["a.jpg", "b.jpg"])

    assert table["no_defect"].all()


def test_duplicate_image_inventory_is_rejected():
    annotations = pd.DataFrame(columns=["ImageId", "ClassId", "EncodedPixels"])

    with pytest.raises(ValueError, match="Duplicate image IDs"):
        build_image_label_table(annotations, ["a.jpg", "a.jpg"])


def test_annotations_for_unknown_images_are_rejected():
    annotations = pd.DataFrame(
        {"ImageId": ["missing.jpg"], "ClassId": [3], "EncodedPixels": ["1 1"]}
    )

    with pytest.raises(ValueError, match="not present"):
        build_image_label_table(annotations, ["a.jpg"])
