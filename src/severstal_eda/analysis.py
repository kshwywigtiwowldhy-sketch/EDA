"""Tabular statistics for the four approved Severstal EDA topics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from severstal_eda.labels import CLASS_COLUMNS, CLASS_IDS, normalize_annotations
from severstal_eda.rle import rle_area


def label_frequency(image_labels: pd.DataFrame) -> pd.DataFrame:
    """Count each class and no-defect images using the full inventory denominator."""

    columns = [*CLASS_COLUMNS, "no_defect"]
    missing = [column for column in columns if column not in image_labels]
    if missing:
        raise ValueError(f"Image label table is missing columns: {missing}")
    total_images = len(image_labels)
    if total_images == 0:
        raise ValueError("Image label table is empty")
    counts = image_labels[columns].astype(bool).sum(axis=0).astype(int)
    return pd.DataFrame(
        {
            "label": counts.index,
            "image_count": counts.values,
            "image_fraction": counts.values / total_images,
        }
    )


def label_combinations(image_labels: pd.DataFrame) -> pd.DataFrame:
    """Count exact image-level label combinations, including no-defect images."""

    if "combination" not in image_labels:
        raise ValueError("Image label table is missing column: combination")
    total_images = len(image_labels)
    if total_images == 0:
        raise ValueError("Image label table is empty")
    counts = image_labels["combination"].astype(str).value_counts(dropna=False)
    table = counts.rename_axis("combination").reset_index(name="image_count")
    table["image_fraction"] = table["image_count"] / total_images
    return table.sort_values(
        ["image_count", "combination"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)


def cooccurrence_tables(image_labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return class-pair counts and row-conditional co-occurrence probabilities."""

    missing = [column for column in CLASS_COLUMNS if column not in image_labels]
    if missing:
        raise ValueError(f"Image label table is missing columns: {missing}")
    matrix = image_labels[CLASS_COLUMNS].astype(int)
    counts = matrix.T.dot(matrix).astype(int)
    denominators = pd.Series(np.diag(counts), index=counts.index, dtype=float)
    conditional = counts.div(denominators.replace(0, np.nan), axis=0).fillna(0.0)
    return counts, conditional


def mask_area_statistics(
    annotations: pd.DataFrame,
    *,
    height: int,
    width: int,
) -> pd.DataFrame:
    """Summarize per-annotation mask area and rare tiny-mask prevalence by class."""

    normalized = normalize_annotations(annotations)
    image_area = int(height) * int(width)
    if image_area <= 0:
        raise ValueError("Image dimensions must be positive")
    if not normalized.empty:
        normalized = normalized.copy()
        normalized["area_pixels"] = normalized["EncodedPixels"].map(
            lambda encoded: rle_area(encoded, height=height, width=width)
        )

    quantiles = {
        "q01_pixels": 0.01,
        "q05_pixels": 0.05,
        "q25_pixels": 0.25,
        "median_pixels": 0.50,
        "q75_pixels": 0.75,
        "q95_pixels": 0.95,
        "q99_pixels": 0.99,
    }
    rows: list[dict[str, float | int]] = []
    for class_id in CLASS_IDS:
        areas = normalized.loc[normalized["ClassId"].eq(class_id), "area_pixels"].astype(float)
        row: dict[str, float | int] = {
            "class_id": class_id,
            "annotation_count": int(len(areas)),
            "mean_pixels": float(areas.mean()) if len(areas) else np.nan,
            "minimum_pixels": float(areas.min()) if len(areas) else np.nan,
            "maximum_pixels": float(areas.max()) if len(areas) else np.nan,
        }
        for name, quantile in quantiles.items():
            row[name] = float(areas.quantile(quantile)) if len(areas) else np.nan
        row["mean_image_fraction"] = float(areas.mean() / image_area) if len(areas) else np.nan
        row["proportion_below_0_01pct"] = float((areas < image_area * 0.0001).mean()) if len(areas) else np.nan
        row["proportion_below_0_1pct"] = float((areas < image_area * 0.001).mean()) if len(areas) else np.nan
        row["proportion_below_1pct"] = float((areas < image_area * 0.01).mean()) if len(areas) else np.nan
        rows.append(row)
    columns = [
        "class_id",
        "annotation_count",
        "mean_pixels",
        "minimum_pixels",
        "q01_pixels",
        "q05_pixels",
        "q25_pixels",
        "median_pixels",
        "q75_pixels",
        "q95_pixels",
        "q99_pixels",
        "maximum_pixels",
        "mean_image_fraction",
        "proportion_below_0_01pct",
        "proportion_below_0_1pct",
        "proportion_below_1pct",
    ]
    return pd.DataFrame(rows).loc[:, columns]


def rare_summary(image_labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank positive classes and exact positive combinations from rarest upward."""

    classes = label_frequency(image_labels)
    classes = classes.loc[classes["label"].ne("no_defect")]
    classes = classes.sort_values(
        ["image_count", "label"], ascending=[True, True], kind="stable"
    ).reset_index(drop=True)

    combinations = label_combinations(image_labels)
    combinations = combinations.loc[combinations["combination"].ne("none")]
    combinations = combinations.sort_values(
        ["image_count", "combination"], ascending=[True, True], kind="stable"
    ).reset_index(drop=True)
    return classes, combinations

