import numpy as np
import pandas as pd

from severstal_eda.analysis import (
    cooccurrence_tables,
    label_combinations,
    label_frequency,
    mask_area_statistics,
    rare_summary,
)


def fixture_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ImageId": "a",
                "class_1": True,
                "class_2": False,
                "class_3": True,
                "class_4": False,
                "no_defect": False,
                "combination": "1+3",
            },
            {
                "ImageId": "b",
                "class_1": False,
                "class_2": True,
                "class_3": False,
                "class_4": False,
                "no_defect": False,
                "combination": "2",
            },
            {
                "ImageId": "c",
                "class_1": False,
                "class_2": False,
                "class_3": False,
                "class_4": False,
                "no_defect": True,
                "combination": "none",
            },
            {
                "ImageId": "d",
                "class_1": True,
                "class_2": False,
                "class_3": True,
                "class_4": False,
                "no_defect": False,
                "combination": "1+3",
            },
        ]
    )


def test_label_frequency_uses_all_images_as_denominator():
    frequency = label_frequency(fixture_table()).set_index("label")

    assert frequency.loc["class_1", "image_count"] == 2
    assert frequency.loc["class_2", "image_count"] == 1
    assert frequency.loc["no_defect", "image_fraction"] == 0.25


def test_exact_label_combinations_are_counted():
    combinations = label_combinations(fixture_table()).set_index("combination")

    assert combinations.loc["1+3", "image_count"] == 2
    assert combinations.loc["none", "image_count"] == 1
    assert combinations.loc["2", "image_fraction"] == 0.25


def test_cooccurrence_is_symmetric_with_frequency_on_diagonal():
    counts, conditional = cooccurrence_tables(fixture_table())

    assert counts.equals(counts.T)
    assert counts.loc["class_1", "class_1"] == 2
    assert counts.loc["class_1", "class_3"] == 2
    assert conditional.loc["class_1", "class_3"] == 1.0
    assert conditional.loc["class_2", "class_1"] == 0.0


def test_mask_area_statistics_include_quantiles_and_tiny_mask_rates():
    annotations = pd.DataFrame(
        {
            "ImageId": ["a", "b", "c", "d"],
            "ClassId": [1, 1, 1, 2],
            "EncodedPixels": ["1 1", "10 5", "100 50", "200 200"],
        }
    )

    statistics = mask_area_statistics(annotations, height=10, width=1000).set_index("class_id")
    class_1 = statistics.loc[1]

    assert class_1["annotation_count"] == 3
    assert class_1["minimum_pixels"] == 1
    assert class_1["median_pixels"] == 5
    assert class_1["maximum_pixels"] == 50
    assert np.isclose(class_1["proportion_below_0_1pct"], 2 / 3)
    assert class_1["proportion_below_1pct"] == 1.0


def test_rare_summary_sorts_by_count_then_lexically_and_excludes_no_defect():
    rare_classes, rare_combinations = rare_summary(fixture_table())

    assert rare_classes["label"].tolist() == ["class_4", "class_2", "class_1", "class_3"]
    assert rare_combinations["combination"].tolist() == ["2", "1+3"]
