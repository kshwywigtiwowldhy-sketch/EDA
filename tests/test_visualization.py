from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

from severstal_eda.visualization import (
    resolve_label_colors,
    save_cooccurrence_heatmap,
    save_label_combinations_plot,
    save_label_frequency_plot,
    save_sample_grid,
    select_sample_ids,
)


def test_label_colors_use_supplied_class_palette_and_neutral_no_defect():
    colors = resolve_label_colors(
        ["class_1", "class_2", "no_defect"],
        class_colors={1: "#111111", 2: "#222222"},
    )

    assert colors == ["#111111", "#222222", "#8D99AE"]


def test_sample_selection_is_stable_and_unique():
    ids = [f"img_{index}.jpg" for index in range(20)]

    first = select_sample_ids(ids, count=4, seed=42)
    second = select_sample_ids(reversed(ids), count=4, seed=42)

    assert first == second
    assert len(first) == len(set(first)) == 4


def test_statistical_plots_are_written_and_figures_are_closed(tmp_path: Path):
    frequency = pd.DataFrame(
        {"label": ["class_1", "class_2", "no_defect"], "image_count": [2, 1, 3]}
    )
    combinations = pd.DataFrame(
        {"combination": ["none", "1", "1+2"], "image_count": [3, 2, 1]}
    )
    cooccurrence = pd.DataFrame(
        [[2, 1], [1, 1]],
        index=["class_1", "class_2"],
        columns=["class_1", "class_2"],
    )

    outputs = [
        save_label_frequency_plot(frequency, tmp_path / "frequency.png"),
        save_label_combinations_plot(combinations, tmp_path / "combinations.png"),
        save_cooccurrence_heatmap(cooccurrence, tmp_path / "cooccurrence.png"),
    ]

    assert all(path.exists() and path.stat().st_size > 0 for path in outputs)
    assert plt.get_fignums() == []


def test_sample_grid_overlays_rle_masks(tmp_path: Path):
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    Image.new("RGB", (4, 4), color=(120, 120, 120)).save(image_dir / "a.jpg")
    annotations = pd.DataFrame(
        {"ImageId": ["a.jpg"], "ClassId": [1], "EncodedPixels": ["1 4"]}
    )

    output = save_sample_grid(
        ["a.jpg"],
        annotations,
        image_dir=image_dir,
        output_path=tmp_path / "samples.png",
        height=4,
        width=4,
        title="Samples",
    )

    assert output.exists() and output.stat().st_size > 0
    assert plt.get_fignums() == []
