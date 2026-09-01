# Severstal EDA Design Specification

## Objective

Build a reproducible exploratory data analysis package for the Severstal Steel
Defect Detection dataset. The approved scope is limited to four areas:

1. label frequency;
2. label co-occurrence;
3. sample visualization;
4. rare-label analysis.

Data auditing, train/validation split generation, model training, inference, and
submission generation are explicitly out of scope.

## Inputs and safety

- The raw dataset is read from `D:\kagllee\dataset`.
- Raw images and competition CSV files are treated as read-only inputs.
- Raw competition data and images are not committed to GitHub.
- Generated artifacts are written to the repository and mirrored to
  `F:\eda\severstal_eda` when filesystem permission is available.
- Existing files under `F:\eda` are not overwritten.

## Architecture

The Python package is the sole source of analytical logic. The command-line
entry point and Jupyter notebook both call the same tested functions, so the
script and notebook cannot silently produce different statistics.

Planned components:

- `io.py`: load configuration, annotations, image inventory, and output paths.
- `rle.py`: validate and decode Severstal column-major RLE masks.
- `labels.py`: build the complete image-level multilabel table, including
  unannotated images as no-defect samples.
- `analysis.py`: compute label frequency, combination counts, co-occurrence,
  mask-area statistics, and rare-label summaries.
- `visualization.py`: render deterministic charts and mask-overlay panels.
- `provenance.py`: record parameters, dependency versions, input/output hashes,
  timestamps, and run status.
- `cli.py`: run the complete workflow from a YAML configuration.

## Analytical outputs

### Label frequency

- annotation-row counts and proportions for classes 1-4;
- image-level counts and proportions for no-defect and classes 1-4;
- imbalance ratios relative to the rarest class;
- machine-readable CSV tables and a labeled bar chart.

### Label co-occurrence

- exact image-level label-combination counts;
- single-, double-, triple-label, and no-defect counts;
- symmetric 4-by-4 co-occurrence count and conditional-rate matrices;
- combination bar chart and co-occurrence heatmap.

### Sample visualization

- representative samples for each class;
- no-defect samples;
- multilabel samples;
- original image, binary mask, and fixed-color overlay views;
- image ID and class combination shown on each panel;
- random seed 42 and recorded selected IDs for reproducibility.

### Rare-label analysis

- class 2 frequency relative to other classes;
- rare combinations and their sample counts;
- per-class mask-area quantiles and small-mask proportions;
- representative rare-class and rare-combination overlays;
- evidence-bounded risk notes without prescribing a model architecture.

## Deliverables

```text
EDA/
|-- README.md
|-- WORKFLOW.md
|-- requirements.txt
|-- config/eda_config.yaml
|-- src/severstal_eda/
|-- tests/
|-- notebooks/severstal_eda.ipynb
|-- reports/eda_report.md
|-- outputs/figures/
|-- outputs/tables/
|-- logs/eda_run.jsonl
|-- MANIFEST.sha256
`-- docs/superpowers/
```

`WORKFLOW.md` documents setup, configuration, execution, verification,
reproduction, output interpretation, and common failure modes.

## Reproducibility and provenance

- All random sampling uses seed 42.
- Configuration values are stored in YAML.
- Every run appends a JSON Lines event log.
- Input metadata and SHA-256 hashes are recorded without copying raw inputs.
- Output files receive SHA-256 entries in `MANIFEST.sha256`.
- Charts use explicit dimensions, titles, axes, legends, and fixed class colors.
- The notebook records its execution environment and calls the package API.

## Error handling

The workflow fails closed when required inputs are missing, annotation columns
are unsupported, RLE is malformed, image dimensions disagree with the expected
shape, or output files cannot be written. A failed run is recorded in the log,
and an incomplete report is not presented as final.

## Testing strategy

Development follows red-green-refactor. Tests use small synthetic fixtures and
cover:

- empty and non-empty column-major RLE decoding;
- malformed and out-of-bounds RLE rejection;
- completion of unannotated images as no-defect records;
- exact class-frequency and multilabel-combination counts;
- co-occurrence symmetry and diagonal counts;
- rare-label and rare-combination ranking;
- deterministic sample selection with seed 42;
- output schema and manifest generation.

Before delivery, all tests, the full EDA run, Notebook execution, artifact
inventory, hashes, and representative figures are verified.

## Version-control and publishing

Work is performed on branch `eda/severstal-analysis` with focused commits for
specification, tests, analysis modules, visualization, Notebook/report, and
final verification. The same deliverable tree is mirrored to
`F:\eda\severstal_eda` after verification. GitHub publication excludes raw
competition data and personal credentials.
