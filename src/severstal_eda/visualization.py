"""Deterministic, non-interactive plots and mask-overlay sample grids."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np
import pandas as pd
from PIL import Image

from severstal_eda.labels import normalize_annotations
from severstal_eda.rle import decode_rle


CLASS_COLORS = {
    1: "#00A6FB",
    2: "#F15BB5",
    3: "#FEE440",
    4: "#00C49A",
}


def select_sample_ids(ids: Iterable[str], *, count: int, seed: int) -> list[str]:
    """Select stable unique IDs regardless of input ordering."""

    if count < 0:
        raise ValueError("Sample count must be non-negative")
    ordered = np.asarray(sorted(set(str(image_id) for image_id in ids)), dtype=object)
    if count == 0 or len(ordered) == 0:
        return []
    if len(ordered) <= count:
        return ordered.tolist()
    rng = np.random.default_rng(seed)
    selected = ordered[rng.choice(len(ordered), size=count, replace=False)].tolist()
    return sorted(selected)


def _prepare_output(output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_label_frequency_plot(
    frequency: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Save class and no-defect image counts as a readable bar chart."""

    path = _prepare_output(output_path)
    labels = frequency["label"].astype(str).tolist()
    counts = frequency["image_count"].astype(int).to_numpy()
    colors = [
        CLASS_COLORS.get(int(label.rsplit("_", 1)[1]), "#8D99AE")
        if label.startswith("class_")
        else "#8D99AE"
        for label in labels
    ]
    fig, axis = plt.subplots(figsize=(8.5, 5.2), dpi=140)
    try:
        bars = axis.bar(labels, counts, color=colors, edgecolor="#333333", linewidth=0.6)
        axis.bar_label(bars, labels=[f"{value:,}" for value in counts], padding=3, fontsize=9)
        axis.set_title("Severstal label frequency (image level)")
        axis.set_xlabel("Label")
        axis.set_ylabel("Images")
        axis.grid(axis="y", alpha=0.25)
        axis.set_ylim(0, max(counts, default=0) * 1.14 if len(counts) else 1)
        fig.savefig(path, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path


def save_label_combinations_plot(
    combinations: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Save exact multilabel combination counts on a logarithmic horizontal scale."""

    path = _prepare_output(output_path)
    ordered = combinations.sort_values("image_count", ascending=True, kind="stable")
    labels = ordered["combination"].astype(str).tolist()
    counts = ordered["image_count"].astype(int).to_numpy()
    fig_height = max(4.8, 0.42 * len(ordered) + 1.8)
    fig, axis = plt.subplots(figsize=(9.5, fig_height), dpi=140)
    try:
        bars = axis.barh(labels, counts, color="#457B9D")
        axis.bar_label(bars, labels=[f"{value:,}" for value in counts], padding=3, fontsize=8)
        axis.set_xscale("log")
        axis.set_title("Exact image-level label combinations")
        axis.set_xlabel("Images (log scale)")
        axis.set_ylabel("Combination")
        axis.grid(axis="x", alpha=0.25)
        fig.savefig(path, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path


def save_cooccurrence_heatmap(
    counts: pd.DataFrame,
    output_path: str | Path,
) -> Path:
    """Save the symmetric class co-occurrence count matrix."""

    path = _prepare_output(output_path)
    values = counts.to_numpy(dtype=float)
    fig, axis = plt.subplots(figsize=(6.8, 5.8), dpi=140)
    try:
        image = axis.imshow(values, cmap="Blues")
        axis.set_xticks(range(len(counts.columns)), counts.columns, rotation=35, ha="right")
        axis.set_yticks(range(len(counts.index)), counts.index)
        threshold = values.max() / 2 if values.size else 0
        for row in range(values.shape[0]):
            for column in range(values.shape[1]):
                axis.text(
                    column,
                    row,
                    f"{int(values[row, column]):,}",
                    ha="center",
                    va="center",
                    color="white" if values[row, column] > threshold else "#222222",
                    fontsize=9,
                )
        axis.set_title("Defect-class co-occurrence counts")
        fig.colorbar(image, ax=axis, fraction=0.046, pad=0.04, label="Images")
        fig.savefig(path, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path


def save_sample_grid(
    sample_ids: Sequence[str],
    annotations: pd.DataFrame,
    *,
    image_dir: str | Path,
    output_path: str | Path,
    height: int,
    width: int,
    title: str,
    class_colors: dict[int, str] | None = None,
) -> Path:
    """Save deterministic image samples with transparent decoded class masks."""

    if not sample_ids:
        raise ValueError("At least one sample image is required")
    colors = CLASS_COLORS if class_colors is None else class_colors
    normalized = normalize_annotations(annotations)
    image_dir = Path(image_dir)
    path = _prepare_output(output_path)
    columns = min(2, len(sample_ids))
    rows = int(np.ceil(len(sample_ids) / columns))
    fig, axes = plt.subplots(
        rows,
        columns,
        figsize=(12.5, max(3.0, rows * 2.65)),
        dpi=140,
        squeeze=False,
    )
    try:
        for axis, image_id in zip(axes.flat, sample_ids, strict=False):
            image_path = image_dir / image_id
            if not image_path.is_file():
                raise FileNotFoundError(f"Sample image missing: {image_path}")
            with Image.open(image_path) as source:
                image = np.asarray(source.convert("RGB"), dtype=np.float32) / 255.0
            if image.shape[:2] != (height, width):
                raise ValueError(
                    f"Unexpected sample dimensions for {image_id}: {image.shape[:2]}"
                )

            rows_for_image = normalized.loc[normalized["ImageId"].eq(image_id)]
            overlay = image.copy()
            present: list[str] = []
            for annotation in rows_for_image.itertuples(index=False):
                class_id = int(annotation.ClassId)
                mask = decode_rle(
                    annotation.EncodedPixels,
                    height=height,
                    width=width,
                ).astype(bool)
                color = np.asarray(to_rgb(colors[class_id]), dtype=np.float32)
                overlay[mask] = 0.58 * overlay[mask] + 0.42 * color
                present.append(str(class_id))
            axis.imshow(np.clip(overlay, 0.0, 1.0))
            label_text = "+".join(present) if present else "none"
            axis.set_title(f"{image_id} | labels: {label_text}", fontsize=8)
            axis.axis("off")

        for axis in list(axes.flat)[len(sample_ids) :]:
            axis.axis("off")
        fig.suptitle(title, fontsize=13)
        fig.savefig(path, bbox_inches="tight")
    finally:
        plt.close(fig)
    return path

