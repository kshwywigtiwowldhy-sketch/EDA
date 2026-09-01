# Severstal Steel Defect EDA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, tested EDA package and executed notebook for label frequency, label co-occurrence, representative samples, and rare-label analysis on the official Severstal dataset.

**Architecture:** A small Python package is the only source of analysis logic. The CLI and notebook call the same package functions, write deterministic tables and figures, and record configuration, hashes, dependency versions, selected image IDs, and run events. Raw Kaggle data remains read-only and outside Git.

**Tech Stack:** Python 3.12, pandas, NumPy, Pillow, Matplotlib, PyYAML, pytest, nbformat, nbclient, Git.

---

## File map

- `.gitignore`: exclude virtual environments, caches, credentials, and raw data.
- `pyproject.toml`: package metadata, pytest settings, and console entry point.
- `requirements.txt`: reproducible runtime and test dependencies.
- `config/eda_config.yaml`: dataset path, image dimensions, seed, colors, and output paths.
- `src/severstal_eda/io.py`: validated configuration, CSV loading, and image inventory.
- `src/severstal_eda/rle.py`: strict Severstal column-major RLE parsing and decoding.
- `src/severstal_eda/labels.py`: complete image-level multilabel table, including no-defect images.
- `src/severstal_eda/analysis.py`: frequency, combinations, co-occurrence, mask-area, and rare-label tables.
- `src/severstal_eda/visualization.py`: deterministic plots and image/mask overlays.
- `src/severstal_eda/provenance.py`: JSONL events, SHA-256 hashes, environment metadata, and manifest.
- `src/severstal_eda/cli.py`: fail-closed end-to-end workflow.
- `tests/`: synthetic, fast unit and integration tests.
- `notebooks/severstal_eda.ipynb`: executable narrative that calls the package API.
- `reports/eda_report.md`: generated Chinese findings with links to tables and figures.
- `WORKFLOW.md`: reusable Chinese execution and troubleshooting guide.

### Task 1: Project scaffold and validated configuration

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `config/eda_config.yaml`
- Create: `src/severstal_eda/__init__.py`
- Create: `src/severstal_eda/io.py`
- Create: `tests/test_io.py`

- [ ] **Step 1: Create the isolated environment and install dependencies**

Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Expected: installation exits with code 0 and `.venv` remains untracked.

- [ ] **Step 2: Write failing configuration tests**

```python
from pathlib import Path
import pytest
from severstal_eda.io import load_config, validate_dataset

def test_load_config_resolves_dataset_path(tmp_path: Path):
    cfg = tmp_path / "eda.yaml"
    cfg.write_text("dataset_dir: data\nimage_height: 256\nimage_width: 1600\n", encoding="utf-8")
    loaded = load_config(cfg)
    assert loaded.dataset_dir == (tmp_path / "data").resolve()
    assert (loaded.image_height, loaded.image_width) == (256, 1600)

def test_validate_dataset_fails_closed(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="train.csv"):
        validate_dataset(tmp_path)
```

- [ ] **Step 3: Verify the tests fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_io.py -v`

Expected: FAIL because `severstal_eda.io` does not exist.

- [ ] **Step 4: Implement immutable configuration and dataset validation**

```python
@dataclass(frozen=True)
class EDAConfig:
    dataset_dir: Path
    output_dir: Path
    report_path: Path
    log_path: Path
    manifest_path: Path
    image_height: int = 256
    image_width: int = 1600
    seed: int = 42
    samples_per_group: int = 4

def validate_dataset(dataset_dir: Path) -> DatasetPaths:
    paths = DatasetPaths(
        train_csv=dataset_dir / "train.csv",
        sample_submission=dataset_dir / "sample_submission.csv",
        train_images=dataset_dir / "train_images",
        test_images=dataset_dir / "test_images",
    )
    for required in (paths.train_csv, paths.sample_submission, paths.train_images, paths.test_images):
        if not required.exists():
            raise FileNotFoundError(f"Required dataset input missing: {required}")
    return paths
```

- [ ] **Step 5: Run tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_io.py -v`

Expected: PASS.

Commit: `git commit -m "build: scaffold reproducible EDA package"`

### Task 2: Strict column-major RLE support

**Files:**
- Create: `src/severstal_eda/rle.py`
- Create: `tests/test_rle.py`

- [ ] **Step 1: Write failing RLE tests**

```python
import numpy as np
import pytest
from severstal_eda.rle import decode_rle, rle_area

def test_decode_column_major_rle():
    mask = decode_rle("1 2 6 2", height=2, width=4)
    np.testing.assert_array_equal(mask, np.array([[1, 0, 1, 0], [1, 0, 1, 0]], dtype=np.uint8))

@pytest.mark.parametrize("rle", ["1", "0 2", "8 2", "1 -2", "a b"])
def test_decode_rejects_malformed_or_out_of_bounds(rle):
    with pytest.raises(ValueError):
        decode_rle(rle, height=2, width=4)

def test_rle_area_without_allocating_mask():
    assert rle_area("1 2 6 2", height=2, width=4) == 4
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rle.py -v`

Expected: FAIL because RLE functions are undefined.

- [ ] **Step 3: Implement strict parsing and Fortran-order decoding**

```python
def parse_rle(rle: str, *, height: int, width: int) -> tuple[np.ndarray, np.ndarray]:
    tokens = str(rle).split()
    if not tokens or len(tokens) % 2:
        raise ValueError("RLE must contain start/length pairs")
    values = np.asarray(tokens, dtype=np.int64)
    starts, lengths = values[0::2] - 1, values[1::2]
    ends = starts + lengths
    if np.any(starts < 0) or np.any(lengths <= 0) or np.any(ends > height * width):
        raise ValueError("RLE span is outside the image")
    return starts, lengths

def decode_rle(rle: str, *, height: int, width: int) -> np.ndarray:
    starts, lengths = parse_rle(rle, height=height, width=width)
    flat = np.zeros(height * width, dtype=np.uint8)
    for start, length in zip(starts, lengths, strict=True):
        flat[start:start + length] = 1
    return flat.reshape((height, width), order="F")
```

- [ ] **Step 4: Run tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_rle.py -v`

Expected: PASS.

Commit: `git commit -m "feat: validate and decode Severstal RLE masks"`

### Task 3: Complete image-level label table

**Files:**
- Modify: `src/severstal_eda/io.py`
- Create: `src/severstal_eda/labels.py`
- Create: `tests/test_labels.py`

- [ ] **Step 1: Write failing label completion tests**

```python
import pandas as pd
from severstal_eda.labels import build_image_label_table

def test_unannotated_images_become_no_defect_rows():
    annotations = pd.DataFrame({
        "ImageId": ["a.jpg", "a.jpg", "b.jpg"],
        "ClassId": [1, 3, 2],
        "EncodedPixels": ["1 1", "4 1", "2 1"],
    })
    table = build_image_label_table(annotations, ["a.jpg", "b.jpg", "c.jpg"])
    row = table.set_index("ImageId").loc["c.jpg"]
    assert row["no_defect"]
    assert row[["class_1", "class_2", "class_3", "class_4"]].sum() == 0
    assert table.set_index("ImageId").loc["a.jpg", "combination"] == "1+3"
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_labels.py -v`

Expected: FAIL because `build_image_label_table` is undefined.

- [ ] **Step 3: Implement schema normalization and image inventory completion**

```python
def normalize_annotations(frame: pd.DataFrame) -> pd.DataFrame:
    if "ImageId_ClassId" in frame.columns:
        split = frame["ImageId_ClassId"].str.rsplit("_", n=1, expand=True)
        frame = frame.assign(ImageId=split[0], ClassId=split[1].astype(int))
    required = {"ImageId", "ClassId", "EncodedPixels"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Unsupported annotation columns: {frame.columns.tolist()}")
    frame = frame.loc[frame["EncodedPixels"].notna(), list(required)].copy()
    frame["ClassId"] = frame["ClassId"].astype(int)
    if not frame["ClassId"].isin([1, 2, 3, 4]).all():
        raise ValueError("ClassId must be in 1..4")
    return frame.sort_values(["ImageId", "ClassId"]).reset_index(drop=True)
```

- [ ] **Step 4: Add duplicate image detection and run tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_labels.py tests/test_io.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit: `git commit -m "feat: build complete multilabel image table"`

### Task 4: Frequency, co-occurrence, and rare-label statistics

**Files:**
- Create: `src/severstal_eda/analysis.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: Write failing analysis tests**

```python
import pandas as pd
from severstal_eda.analysis import label_frequency, label_combinations, cooccurrence_tables, rare_summary

def fixture_table():
    return pd.DataFrame([
        {"ImageId":"a", "class_1":True,  "class_2":False, "class_3":True,  "class_4":False, "no_defect":False, "combination":"1+3"},
        {"ImageId":"b", "class_1":False, "class_2":True,  "class_3":False, "class_4":False, "no_defect":False, "combination":"2"},
        {"ImageId":"c", "class_1":False, "class_2":False, "class_3":False, "class_4":False, "no_defect":True,  "combination":"none"},
    ])

def test_frequency_and_combinations_are_exact():
    table = fixture_table()
    assert label_frequency(table).set_index("label").loc["class_2", "image_count"] == 1
    assert label_combinations(table).set_index("combination").loc["1+3", "image_count"] == 1

def test_cooccurrence_is_symmetric_with_frequency_diagonal():
    table = fixture_table()
    counts, conditional = cooccurrence_tables(table)
    assert counts.equals(counts.T)
    assert counts.loc["class_1", "class_1"] == 1
    assert conditional.loc["class_1", "class_3"] == 1.0
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -v`

Expected: FAIL because analysis functions are undefined.

- [ ] **Step 3: Implement vectorized tables**

```python
CLASS_COLUMNS = ["class_1", "class_2", "class_3", "class_4"]

def cooccurrence_tables(image_labels: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    matrix = image_labels[CLASS_COLUMNS].astype(int)
    counts = matrix.T.dot(matrix)
    denominators = counts.values.diagonal()
    conditional = counts.div(pd.Series(denominators, index=counts.index), axis=0).fillna(0.0)
    return counts, conditional
```

- [ ] **Step 4: Add mask-area quantiles and rare rankings**

`mask_area_statistics` must return per-class count, mean, minimum, q01, q05, q25, median, q75, q95, q99, maximum, and proportions below 0.01%, 0.1%, and 1% of image area. `rare_summary` sorts classes and exact combinations by ascending image count with stable lexical tie-breaking.

- [ ] **Step 5: Run tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_analysis.py -v`

Expected: PASS.

Commit: `git commit -m "feat: compute EDA frequency and rarity tables"`

### Task 5: Deterministic plots and mask overlays

**Files:**
- Create: `src/severstal_eda/visualization.py`
- Create: `tests/test_visualization.py`

- [ ] **Step 1: Write failing deterministic-selection test**

```python
from severstal_eda.visualization import select_sample_ids

def test_sample_selection_is_stable():
    ids = [f"img_{i}.jpg" for i in range(20)]
    assert select_sample_ids(ids, count=4, seed=42) == select_sample_ids(ids, count=4, seed=42)
    assert len(set(select_sample_ids(ids, count=4, seed=42))) == 4
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_visualization.py -v`

Expected: FAIL because visualization helpers are undefined.

- [ ] **Step 3: Implement deterministic selection and fixed colors**

```python
CLASS_COLORS = {1: "#00A6FB", 2: "#F15BB5", 3: "#FEE440", 4: "#00F5D4"}

def select_sample_ids(ids: Sequence[str], *, count: int, seed: int) -> list[str]:
    ordered = np.asarray(sorted(set(ids)), dtype=object)
    if len(ordered) <= count:
        return ordered.tolist()
    rng = np.random.default_rng(seed)
    return sorted(ordered[rng.choice(len(ordered), size=count, replace=False)].tolist())
```

- [ ] **Step 4: Implement five verified figures**

Create `label_frequency.png`, `label_combinations.png`, `cooccurrence_heatmap.png`, `representative_samples.png`, and `rare_label_samples.png`. Each image uses explicit size and DPI, readable labels, fixed colors, `bbox_inches="tight"`, and closes the Matplotlib figure after saving.

- [ ] **Step 5: Run tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_visualization.py -v`

Expected: PASS.

Commit: `git commit -m "feat: add deterministic EDA visualizations"`

### Task 6: Provenance and fail-closed CLI

**Files:**
- Create: `src/severstal_eda/provenance.py`
- Create: `src/severstal_eda/cli.py`
- Create: `tests/test_provenance.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing provenance tests**

```python
from pathlib import Path
from severstal_eda.provenance import sha256_file, write_manifest

def test_manifest_is_sorted_and_hashes_outputs(tmp_path: Path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = tmp_path / "MANIFEST.sha256"
    write_manifest([tmp_path / "b.txt", tmp_path / "a.txt"], manifest, base_dir=tmp_path)
    lines = manifest.read_text(encoding="utf-8").splitlines()
    assert lines[0].endswith("  a.txt")
    assert len(sha256_file(tmp_path / "a.txt")) == 64
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_provenance.py tests/test_cli.py -v`

Expected: FAIL because provenance and CLI modules are undefined.

- [ ] **Step 3: Implement JSONL events and manifest**

```python
def append_event(path: Path, event: str, **payload: object) -> None:
    record = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "event": event, **payload}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
```

- [ ] **Step 4: Implement one end-to-end API and CLI**

`run_eda(config_path: Path) -> RunResult` validates inputs, records `run_started`, writes all tables and figures to temporary paths, atomically replaces final outputs only after success, writes the report and manifest, and records `run_succeeded`. On any exception it records `run_failed` with exception type and re-raises.

CLI command:

```powershell
.\.venv\Scripts\python.exe -m severstal_eda.cli --config config\eda_config.yaml
```

- [ ] **Step 5: Run all tests and commit**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

Commit: `git commit -m "feat: add audited end-to-end EDA runner"`

### Task 7: Executable notebook, Chinese report, and reusable workflow

**Files:**
- Create: `notebooks/severstal_eda.ipynb`
- Create: `reports/eda_report.md`
- Create: `WORKFLOW.md`
- Modify: `README.md`

- [ ] **Step 1: Build the notebook from explicit cells**

The notebook must contain: objective and scope; configuration; input provenance; package execution; label-frequency display; combination and co-occurrence display; representative samples; rare-label statistics; limitations; artifact inventory. It imports `run_eda` instead of duplicating formulas.

- [ ] **Step 2: Execute the notebook non-interactively**

Run:

```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute notebooks\severstal_eda.ipynb --output severstal_eda.executed.ipynb --ExecutePreprocessor.timeout=900
```

Expected: exit code 0 and no cell has an error output.

- [ ] **Step 3: Write `WORKFLOW.md`**

Document exact PowerShell 7 setup, data path configuration, environment creation, tests, CLI run, notebook execution, output interpretation, deterministic seed, hash verification, Git workflow, F-drive mirroring, and failure recovery for missing files, unsupported CSV schema, malformed RLE, and insufficient disk space.

- [ ] **Step 4: Generate the evidence-bounded Chinese report**

The report cites generated CSV values, names class 2 as rare only if the table proves it, distinguishes annotation-row and image-level frequency, explains conditional co-occurrence direction, includes selected image IDs, and states that audit/split/modeling are outside scope.

- [ ] **Step 5: Commit**

Commit: `git commit -m "docs: add executable notebook and EDA workflow"`

### Task 8: Full-data verification and publication

**Files:**
- Modify: `MANIFEST.sha256`
- Create: `outputs/tables/*.csv`
- Create: `outputs/figures/*.png`
- Create: `logs/eda_run.jsonl`
- Copy verified deliverables to: `F:\eda\severstal_eda`

- [ ] **Step 1: Run the full test suite**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS with no warnings promoted to errors.

- [ ] **Step 2: Run full EDA against official data**

Run: `.\.venv\Scripts\python.exe -m severstal_eda.cli --config config\eda_config.yaml`

Expected invariants: 12,568 training images; 5,506 test images; 6,666 defective training images; 5,902 no-defect training images; class annotation counts 897, 247, 5,150, and 801 for classes 1-4.

- [ ] **Step 3: Verify artifacts and figures**

Check every manifest hash, CSV schema, JSONL final event, and notebook execution status. Visually inspect every PNG for clipping, unreadable text, incorrect masks, and color/legend mismatch.

- [ ] **Step 4: Mirror only verified deliverables to F drive**

Copy the repository deliverable tree to `F:\eda\severstal_eda`, excluding `.git`, `.venv`, caches, credentials, and raw data. Recompute the mirror manifest and compare it to the repository manifest.

- [ ] **Step 5: Commit and publish**

Commit: `git commit -m "chore: verify and publish Severstal EDA artifacts"`

Push branch `eda/severstal-analysis` to `https://github.com/kshwywigtiwowldhy-sketch/EDA.git`. If GitHub authentication still denies write access, preserve the local commits and report the exact publication blocker without exposing credentials.
