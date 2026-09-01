"""Normalize Severstal annotations and build a complete image-level label table."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


CLASS_IDS = (1, 2, 3, 4)
CLASS_COLUMNS = [f"class_{class_id}" for class_id in CLASS_IDS]


def normalize_annotations(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize current and legacy Kaggle CSV schemas to positive annotation rows."""

    frame = frame.copy()
    if "ImageId_ClassId" in frame.columns:
        split = frame["ImageId_ClassId"].astype(str).str.rsplit("_", n=1, expand=True)
        if split.shape[1] != 2:
            raise ValueError("ImageId_ClassId must end with an underscore and class ID")
        frame["ImageId"] = split[0]
        frame["ClassId"] = split[1]

    required = ["ImageId", "ClassId", "EncodedPixels"]
    if not set(required).issubset(frame.columns):
        raise ValueError(f"Unsupported annotation columns: {frame.columns.tolist()}")

    frame = frame.loc[:, required]
    encoded = frame["EncodedPixels"].fillna("").astype(str).str.strip()
    frame = frame.loc[encoded.ne("")].copy()
    frame["EncodedPixels"] = encoded.loc[frame.index]
    try:
        frame["ClassId"] = pd.to_numeric(frame["ClassId"], errors="raise").astype(int)
    except (TypeError, ValueError) as exc:
        raise ValueError("ClassId must be an integer in 1..4") from exc
    if not frame["ClassId"].isin(CLASS_IDS).all():
        raise ValueError("ClassId must be in 1..4")
    if frame[["ImageId", "ClassId"]].duplicated().any():
        raise ValueError("Duplicate positive annotation for the same image and class")
    return frame.sort_values(["ImageId", "ClassId"], kind="stable").reset_index(drop=True)


def build_image_label_table(
    annotations: pd.DataFrame,
    image_ids: Iterable[str],
) -> pd.DataFrame:
    """Complete positive annotations against the authoritative train-image inventory."""

    inventory = pd.Index([str(image_id) for image_id in image_ids], name="ImageId")
    if inventory.has_duplicates:
        duplicates = sorted(inventory[inventory.duplicated()].unique().tolist())
        raise ValueError(f"Duplicate image IDs in inventory: {duplicates[:5]}")

    normalized = normalize_annotations(annotations)
    unknown = sorted(set(normalized["ImageId"]) - set(inventory))
    if unknown:
        raise ValueError(f"Annotated images not present in train image inventory: {unknown[:5]}")

    if normalized.empty:
        positive = pd.DataFrame(False, index=inventory, columns=CLASS_COLUMNS)
    else:
        positive = pd.crosstab(normalized["ImageId"], normalized["ClassId"]).gt(0)
        positive = positive.reindex(index=inventory, columns=CLASS_IDS, fill_value=False)
        positive.columns = CLASS_COLUMNS

    positive = positive.astype(bool)
    table = positive.reset_index()
    table["no_defect"] = ~table[CLASS_COLUMNS].any(axis=1)
    table["positive_class_count"] = table[CLASS_COLUMNS].sum(axis=1).astype(int)

    def combination(row: pd.Series) -> str:
        labels = [str(class_id) for class_id in CLASS_IDS if bool(row[f"class_{class_id}"])]
        return "+".join(labels) if labels else "none"

    table["combination"] = table.apply(combination, axis=1)
    return table.sort_values("ImageId", kind="stable").reset_index(drop=True)

