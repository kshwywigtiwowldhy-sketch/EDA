"""Audited end-to-end runner for the approved Severstal EDA scope."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import tempfile
from typing import Any

import pandas as pd

from severstal_eda.analysis import (
    cooccurrence_tables,
    label_combinations,
    label_frequency,
    mask_area_statistics,
    rare_summary,
)
from severstal_eda.io import EDAConfig, load_config, validate_dataset
from severstal_eda.labels import CLASS_COLUMNS, build_image_label_table
from severstal_eda.provenance import append_event, sha256_file, write_manifest
from severstal_eda.visualization import (
    save_cooccurrence_heatmap,
    save_label_combinations_plot,
    save_label_frequency_plot,
    save_sample_grid,
    select_sample_ids,
)


@dataclass(frozen=True)
class RunResult:
    """Successful run metadata returned to the CLI and notebook."""

    summary: dict[str, Any]
    output_paths: tuple[Path, ...]
    selected_samples: dict[str, list[str]]


def _package_versions() -> dict[str, str]:
    packages = ["matplotlib", "numpy", "pandas", "Pillow", "PyYAML", "pyparsing"]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _append_unique(target: list[str], candidates: list[str]) -> None:
    for candidate in candidates:
        if candidate not in target:
            target.append(candidate)


def _select_run_samples(
    image_labels: pd.DataFrame,
    rare_classes: pd.DataFrame,
    rare_combinations: pd.DataFrame,
    *,
    count: int,
    seed: int,
) -> dict[str, list[str]]:
    representative: list[str] = []
    for offset, column in enumerate(CLASS_COLUMNS, start=1):
        single_class = image_labels.loc[
            image_labels[column] & image_labels["positive_class_count"].eq(1), "ImageId"
        ].tolist()
        candidates = single_class or image_labels.loc[image_labels[column], "ImageId"].tolist()
        _append_unique(
            representative,
            select_sample_ids(candidates, count=1, seed=seed + offset),
        )
    _append_unique(
        representative,
        select_sample_ids(
            image_labels.loc[image_labels["no_defect"], "ImageId"].tolist(),
            count=1,
            seed=seed + 10,
        ),
    )
    _append_unique(
        representative,
        select_sample_ids(
            image_labels.loc[image_labels["positive_class_count"].gt(1), "ImageId"].tolist(),
            count=1,
            seed=seed + 11,
        ),
    )

    rare: list[str] = []
    for offset, label in enumerate(rare_classes["label"].head(2), start=20):
        candidates = image_labels.loc[image_labels[str(label)], "ImageId"].tolist()
        _append_unique(rare, select_sample_ids(candidates, count=1, seed=seed + offset))
    for offset, combination in enumerate(
        rare_combinations["combination"].head(2), start=30
    ):
        candidates = image_labels.loc[
            image_labels["combination"].eq(str(combination)), "ImageId"
        ].tolist()
        _append_unique(rare, select_sample_ids(candidates, count=1, seed=seed + offset))
    if len(rare) < count:
        candidates = image_labels.loc[~image_labels["no_defect"], "ImageId"].tolist()
        _append_unique(
            rare,
            select_sample_ids(candidates, count=count, seed=seed + 40),
        )
    return {
        "representative": representative,
        "rare": rare[: max(1, count)],
    }


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        values: list[str] = []
        for value in row:
            if isinstance(value, float):
                values.append(f"{value:.6f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _render_report(
    *,
    summary: dict[str, Any],
    frequency: pd.DataFrame,
    combinations: pd.DataFrame,
    cooccurrence: pd.DataFrame,
    area_statistics: pd.DataFrame,
    rare_classes: pd.DataFrame,
    rare_combinations: pd.DataFrame,
    selected_samples: dict[str, list[str]],
) -> str:
    positive_frequency = frequency.loc[frequency["label"].ne("no_defect")]
    most_common = positive_frequency.sort_values("image_count", ascending=False).iloc[0]
    rarest = rare_classes.iloc[0]
    rarest_combination = rare_combinations.iloc[0]
    compact_area = area_statistics.loc[
        :,
        [
            "class_id",
            "annotation_count",
            "minimum_pixels",
            "median_pixels",
            "q95_pixels",
            "maximum_pixels",
            "proportion_below_1pct",
        ],
    ]
    return f"""# Severstal 钢板缺陷 EDA 报告

本报告仅覆盖已批准的四项内容：标签频率、标签共现、样本可视化和稀有标签分析。原始 Kaggle 数据保持只读；统计分母为训练图片清单中的全部 {summary['train_images']:,} 张图片。

## 关键结论

- 有缺陷图片 {summary['defective_images']:,} 张，无缺陷图片 {summary['no_defect_images']:,} 张；无缺陷比例为 {summary['no_defect_fraction']:.2%}。
- 最常见正类别是 `{most_common['label']}`，共有 {int(most_common['image_count']):,} 张（占全部训练图 {most_common['image_fraction']:.2%}）。
- 最稀有单类别是 `{rarest['label']}`，共有 {int(rarest['image_count']):,} 张（{rarest['image_fraction']:.2%}）。
- 最稀有的已出现正标签组合是 `{rarest_combination['combination']}`，仅 {int(rarest_combination['image_count']):,} 张。
- 多标签图片共有 {summary['multilabel_images']:,} 张。共现矩阵用于显示组合数量，条件矩阵另存为 CSV，避免把方向性条件概率误读为对称关系。

## 标签频率

{_markdown_table(frequency)}

![标签频率](../outputs/figures/label_frequency.png)

## 精确标签组合

{_markdown_table(combinations)}

![标签组合](../outputs/figures/label_combinations.png)

## 标签共现

{_markdown_table(cooccurrence.reset_index(names='label'))}

![共现热图](../outputs/figures/cooccurrence_heatmap.png)

## 样本可视化

代表性样本固定使用种子 {summary['seed']}，所选图片 ID 为：`{', '.join(selected_samples['representative'])}`。

![代表性样本](../outputs/figures/representative_samples.png)

## 稀有标签与微小掩码

稀有类别按图片数升序、标签名稳定排序；精确组合中的 `none` 不参与“稀有正标签组合”排名。掩码面积通过 RLE 长度直接求和，阈值比例相对于 {summary['image_height']}×{summary['image_width']} 的图像面积计算。

{_markdown_table(compact_area)}

稀有样本 ID：`{', '.join(selected_samples['rare'])}`。

![稀有标签样本](../outputs/figures/rare_label_samples.png)

## 可复现性

- 配置：`config/eda_config.yaml`
- 随机种子：{summary['seed']}
- 完整表格：`outputs/tables/`
- 运行摘要：`outputs/run_summary.json`
- 事件日志：`logs/eda_run.jsonl`
- SHA-256 清单：`MANIFEST.sha256`

本报告中的结论均来自本次执行生成的表格，不延伸到验证集划分、建模或提交策略。
"""


def run_eda(config_path: str | Path) -> RunResult:
    """Run the complete EDA, publishing final files only after generation succeeds."""

    config_path = Path(config_path).resolve()
    config: EDAConfig | None = None
    try:
        config = load_config(config_path)
        append_event(config.log_path, "run_started", config_path=str(config_path), seed=config.seed)
        paths = validate_dataset(config.dataset_dir)
        manifest_base = config.manifest_path.parent.resolve()
        try:
            output_relative = config.output_dir.relative_to(manifest_base)
            report_relative = config.report_path.relative_to(manifest_base)
        except ValueError as exc:
            raise ValueError("Output and report paths must be inside the manifest base directory") from exc
        manifest_base.mkdir(parents=True, exist_ok=True)

        annotations = pd.read_csv(paths.train_csv)
        image_ids = sorted(path.name for path in paths.train_images.glob("*.jpg"))
        test_image_count = sum(1 for _ in paths.test_images.glob("*.jpg"))
        image_labels = build_image_label_table(annotations, image_ids)
        frequency = label_frequency(image_labels)
        combinations = label_combinations(image_labels)
        cooccurrence, conditional = cooccurrence_tables(image_labels)
        area_statistics = mask_area_statistics(
            annotations,
            height=config.image_height,
            width=config.image_width,
        )
        rare_classes, rare_combinations = rare_summary(image_labels)
        selected_samples = _select_run_samples(
            image_labels,
            rare_classes,
            rare_combinations,
            count=config.samples_per_group,
            seed=config.seed,
        )

        summary: dict[str, Any] = {
            "train_images": len(image_labels),
            "test_images": test_image_count,
            "positive_annotations": int(len(annotations)),
            "defective_images": int((~image_labels["no_defect"]).sum()),
            "no_defect_images": int(image_labels["no_defect"].sum()),
            "no_defect_fraction": float(image_labels["no_defect"].mean()),
            "multilabel_images": int(image_labels["positive_class_count"].gt(1).sum()),
            "class_counts": {
                str(class_id): int(image_labels[f"class_{class_id}"].sum())
                for class_id in range(1, 5)
            },
            "image_height": config.image_height,
            "image_width": config.image_width,
            "seed": config.seed,
            "selected_samples": selected_samples,
            "input_hashes": {
                "config": sha256_file(config_path),
                "train_csv": sha256_file(paths.train_csv),
                "sample_submission": sha256_file(paths.sample_submission),
            },
            "environment": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "packages": _package_versions(),
            },
        }

        with tempfile.TemporaryDirectory(prefix=".eda-stage-", dir=manifest_base) as temporary:
            stage_root = Path(temporary)
            stage_output = stage_root / output_relative
            stage_tables = stage_output / "tables"
            stage_figures = stage_output / "figures"
            stage_report = stage_root / report_relative
            stage_tables.mkdir(parents=True)
            stage_figures.mkdir(parents=True)
            stage_report.parent.mkdir(parents=True, exist_ok=True)

            tables = {
                "image_label_table.csv": image_labels,
                "label_frequency.csv": frequency,
                "label_combinations.csv": combinations,
                "cooccurrence_counts.csv": cooccurrence.reset_index(names="label"),
                "cooccurrence_conditional.csv": conditional.reset_index(names="given_label"),
                "mask_area_statistics.csv": area_statistics,
                "rare_classes.csv": rare_classes,
                "rare_combinations.csv": rare_combinations,
                "selected_samples.csv": pd.DataFrame(
                    [
                        {"group": group, "ImageId": image_id}
                        for group, ids in selected_samples.items()
                        for image_id in ids
                    ]
                ),
            }
            stage_artifacts: list[Path] = []
            for filename, table in tables.items():
                table_path = stage_tables / filename
                table.to_csv(table_path, index=False, encoding="utf-8")
                stage_artifacts.append(table_path)

            stage_artifacts.extend(
                [
                    save_label_frequency_plot(
                        frequency, stage_figures / "label_frequency.png"
                    ),
                    save_label_combinations_plot(
                        combinations, stage_figures / "label_combinations.png"
                    ),
                    save_cooccurrence_heatmap(
                        cooccurrence, stage_figures / "cooccurrence_heatmap.png"
                    ),
                ]
            )
            colors = (
                {int(key): value for key, value in config.class_colors.items()}
                if config.class_colors
                else None
            )
            stage_artifacts.append(
                save_sample_grid(
                    selected_samples["representative"],
                    annotations,
                    image_dir=paths.train_images,
                    output_path=stage_figures / "representative_samples.png",
                    height=config.image_height,
                    width=config.image_width,
                    title="Representative class, no-defect, and multilabel samples",
                    class_colors=colors,
                )
            )
            stage_artifacts.append(
                save_sample_grid(
                    selected_samples["rare"],
                    annotations,
                    image_dir=paths.train_images,
                    output_path=stage_figures / "rare_label_samples.png",
                    height=config.image_height,
                    width=config.image_width,
                    title="Rare classes and rare exact combinations",
                    class_colors=colors,
                )
            )

            summary_path = stage_output / "run_summary.json"
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            stage_artifacts.append(summary_path)
            stage_report.write_text(
                _render_report(
                    summary=summary,
                    frequency=frequency,
                    combinations=combinations,
                    cooccurrence=cooccurrence,
                    area_statistics=area_statistics,
                    rare_classes=rare_classes,
                    rare_combinations=rare_combinations,
                    selected_samples=selected_samples,
                ),
                encoding="utf-8",
            )
            stage_artifacts.append(stage_report)

            stage_manifest = stage_root / config.manifest_path.name
            write_manifest(
                stage_artifacts,
                stage_manifest,
                base_dir=stage_root,
            )

            final_paths: list[Path] = []
            for staged in [path for path in stage_artifacts if path != stage_report]:
                relative = staged.relative_to(stage_root)
                destination = manifest_base / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, destination)
                final_paths.append(destination)
            config.manifest_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage_manifest, config.manifest_path)
            final_paths.append(config.manifest_path)
            config.report_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(stage_report, config.report_path)
            final_paths.append(config.report_path)

        append_event(
            config.log_path,
            "run_succeeded",
            artifact_count=len(final_paths),
            train_images=summary["train_images"],
        )
        return RunResult(
            summary=summary,
            output_paths=tuple(final_paths),
            selected_samples=selected_samples,
        )
    except Exception as exc:
        if config is not None:
            append_event(
                config.log_path,
                "run_failed",
                exception_type=type(exc).__name__,
                message=str(exc),
            )
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True, help="Path to EDA YAML config")
    args = parser.parse_args(argv)
    result = run_eda(args.config)
    print(json.dumps(result.summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

