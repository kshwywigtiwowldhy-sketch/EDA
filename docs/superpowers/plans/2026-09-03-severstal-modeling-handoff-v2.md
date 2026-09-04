# Severstal Modeling Handoff V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已校验的 Severstal 数据审计与冻结 V2 划分整合进现有 EDA 仓库，并产出可核验的 GitHub 与 F 盘交付物。

**Architecture:** 保留现有 EDA 根目录和运行接口，通过新增只读交接材料、冻结划分、机器验证证据和独立归档扩展项目。静态交接测试直接验证文件数量、哈希、集合关系、JSON 证据和 ZIP 成员；任何失败都会阻止 F 盘同步和 GitHub 发布。

**Tech Stack:** Python 3.12、pytest、pandas、Python 标准库 `hashlib/json/zipfile/pathlib`、PowerShell 7、Git。

---

## 文件结构

- `tests/test_handoff_v2.py`：对仓库内 V2 交接材料执行不可变性和一致性测试。
- `README_建模交接必读.md`：建模同学的首要入口。
- `01_data_audit/*.md`：更新后的数据审计和阶段交接说明。
- `03_final_split_v2/split_report.md`：冻结划分方法、风险与统计复核。
- `03_final_split_v2/splits/*.csv`：无表头的冻结训练/验证 ID。
- `03_final_split_v2/evidence/*.json`：V1→V2 置换与机器校验结果。
- `deliverables/severstal_modeling_handoff_v2_20260902.zip`：用户提供的完整原始交接包。
- `deliverables/severstal_modeling_handoff_v2_20260902.zip.sha256`：完整交接包外部哈希。
- `deliverables/severstal_handoff_images_v2_20260902.zip`：全部交接图片的单独归档。
- `deliverables/severstal_handoff_images_v2_20260902.zip.sha256`：图片归档哈希。
- `README.md`：仓库总入口和冻结 V2 使用规则。
- `WORKFLOW.md`：复现、校验和建模读取命令。
- `PROGRESS.md`：工作留痕、校验结果和发布状态。

### Task 1: 添加冻结交接约束测试

**Files:**
- Create: `tests/test_handoff_v2.py`
- Test: `tests/test_handoff_v2.py`

- [ ] **Step 1: 写入缺失交接材料时会失败的测试**

```python
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
    assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in members)
    assert checksum.read_text(encoding="utf-8").split()[0] == sha256(archive)


def test_handoff_docs_use_final_anonymous_v2_contract() -> None:
    readme = (ROOT / "README_建模交接必读.md").read_text(encoding="utf-8")
    split_report = (ROOT / "03_final_split_v2/split_report.md").read_text(encoding="utf-8")
    combined = readme + split_report
    assert "header=None" in combined
    assert "5,902" in combined
    assert "class_1" in combined and "class_4" in combined
    assert "split_mask_area_distribution_v2.png" not in split_report
    assert "mask_area_split_distribution_v2.png" in split_report
```

- [ ] **Step 2: 运行测试并确认因交接材料尚未加入而失败**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_handoff_v2.py -q -p no:cacheprovider --basetemp='.test-tmp-handoff-red'
```

Expected: FAIL，首个失败为 `03_final_split_v2/splits/train_ids.csv` 不存在。

- [ ] **Step 3: 提交红灯测试**

```powershell
git add tests/test_handoff_v2.py
git commit -m "test: define frozen Severstal handoff v2 contract"
```

### Task 2: 导入经过校验的文本、划分和机器证据

**Files:**
- Create: `README_建模交接必读.md`
- Create: `01_data_audit/EDA交接说明.md`
- Create: `01_data_audit/severstal_data_audit_report.md`
- Create: `03_final_split_v2/split_report.md`
- Create: `03_final_split_v2/splits/train_ids.csv`
- Create: `03_final_split_v2/splits/valid_ids.csv`
- Create: `03_final_split_v2/evidence/split_v2_changes.json`
- Create: `03_final_split_v2/evidence/split_v2_verification.json`
- Test: `tests/test_handoff_v2.py`

- [ ] **Step 1: 从已校验解压目录复制指定文件**

```powershell
$source = '..\handoff_v2_review\severstal_modeling_handoff_v2_20260902'
New-Item -ItemType Directory -Force '01_data_audit', '03_final_split_v2\splits', '03_final_split_v2\evidence'
Copy-Item "$source\README_建模交接必读.md" 'README_建模交接必读.md'
Copy-Item "$source\01_data_audit\EDA交接说明.md" '01_data_audit\EDA交接说明.md'
Copy-Item "$source\01_data_audit\severstal_data_audit_report.md" '01_data_audit\severstal_data_audit_report.md'
Copy-Item "$source\03_final_split_v2\split_report.md" '03_final_split_v2\split_report.md'
Copy-Item "$source\03_final_split_v2\splits\*.csv" '03_final_split_v2\splits'
Copy-Item "$source\03_final_split_v2\evidence\*.json" '03_final_split_v2\evidence'
```

- [ ] **Step 2: 修正报告中的图文件名不一致**

将 `03_final_split_v2/split_report.md` 中的：

```text
split_mask_area_distribution_v2.png
```

替换为包内实际文件名：

```text
mask_area_split_distribution_v2.png
```

- [ ] **Step 3: 运行划分与机器证据测试**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_handoff_v2.py -q -p no:cacheprovider --basetemp='.test-tmp-handoff-import'
```

Expected: 划分和 JSON 测试 PASS；两个归档测试仍因 ZIP 尚未生成而 FAIL。

- [ ] **Step 4: 提交可审阅材料**

```powershell
git add README_建模交接必读.md 01_data_audit 03_final_split_v2
git commit -m "docs: add audited modeling handoff v2 split"
```

### Task 3: 建立完整包与图片包

**Files:**
- Create: `deliverables/severstal_modeling_handoff_v2_20260902.zip`
- Create: `deliverables/severstal_modeling_handoff_v2_20260902.zip.sha256`
- Create: `deliverables/severstal_handoff_images_v2_20260902.zip`
- Create: `deliverables/severstal_handoff_images_v2_20260902.zip.sha256`
- Test: `tests/test_handoff_v2.py`

- [ ] **Step 1: 原样复制完整包及外部哈希**

```powershell
New-Item -ItemType Directory -Force 'deliverables'
Copy-Item 'C:\Users\A\xwechat_files\wxid_j31k8xta6cf322_9e8c\msg\file\2026-09\severstal_modeling_handoff_v2_20260902.zip' 'deliverables'
Copy-Item 'C:\Users\A\xwechat_files\wxid_j31k8xta6cf322_9e8c\msg\file\2026-09\severstal_modeling_handoff_v2_20260902.zip.sha256' 'deliverables'
```

- [ ] **Step 2: 以来源相对路径收集 12 张图片并生成单一 ZIP**

使用一次性构建目录，仅复制以下路径：

```text
01_data_audit/*.png
02_eda/outputs/figures/*.png
03_final_split_v2/evidence/*.png
03_final_split_v2/figures/*.png
```

然后使用 `Compress-Archive` 生成 `deliverables/severstal_handoff_images_v2_20260902.zip`，归档成员必须是测试中列出的 12 个相对路径。

- [ ] **Step 3: 计算图片 ZIP 的 SHA-256 并写入校验文件**

校验文件格式：

```text
<小写 SHA-256>  severstal_handoff_images_v2_20260902.zip
```

- [ ] **Step 4: 运行归档测试并确认全部通过**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/test_handoff_v2.py -q -p no:cacheprovider --basetemp='.test-tmp-handoff-archives'
```

Expected: `5 passed`。

- [ ] **Step 5: 提交归档**

```powershell
git add deliverables tests/test_handoff_v2.py
git commit -m "feat: package verified Severstal handoff archives"
```

### Task 4: 更新入口、复现说明和留痕

**Files:**
- Modify: `README.md`
- Modify: `WORKFLOW.md`
- Modify: `PROGRESS.md`
- Test: `tests/test_handoff_v2.py`

- [ ] **Step 1: 在主 README 添加冻结 V2 快速入口**

新增内容必须包含：

```markdown
## 建模交接：最终冻结 V2

建模前先阅读 [README_建模交接必读.md](README_建模交接必读.md) 和
[03_final_split_v2/split_report.md](03_final_split_v2/split_report.md)。
只使用 `03_final_split_v2/splits/train_ids.csv` 与 `valid_ids.csv`；两份文件无表头，
使用 Pandas 时指定 `header=None`。不在 `train.csv` 中的 5,902 张训练图片需要四通道全零掩码。
类别仅使用 `class_1`～`class_4`，最终验证划分不得按模型分数反复调整。
```

- [ ] **Step 2: 在 WORKFLOW 添加读取和校验命令**

加入以下读取示例：

```python
train_ids = pd.read_csv(
    "03_final_split_v2/splits/train_ids.csv", header=None, names=["ImageId"]
)
valid_ids = pd.read_csv(
    "03_final_split_v2/splits/valid_ids.csv", header=None, names=["ImageId"]
)
```

并记录完整测试命令：

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='.test-tmp-final'
```

- [ ] **Step 3: 在 PROGRESS 记录输入哈希、V2 变化、验证和发布闸门**

记录以下事实：

```text
V1 有 19 条强跨集合近重复边，涉及 18 个组；V2 置换 18+18 张图片后降为 0。
训练/验证数量与所有精确标签组合计数保持不变。
交接包及 55 项内部清单通过哈希校验。
GitHub 推送必须等待最终隐私清单批准。
```

- [ ] **Step 4: 运行全部测试和差异检查**

Run:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='.test-tmp-final-docs'
git diff --check
```

Expected: `36 passed`，`git diff --check` 无输出。

- [ ] **Step 5: 提交文档**

```powershell
git add README.md WORKFLOW.md PROGRESS.md
git commit -m "docs: publish frozen v2 modeling handoff guidance"
```

### Task 5: 隐私与发布候选审查

**Files:**
- Inspect: all Git-tracked files on `handoff/severstal-v2`

- [ ] **Step 1: 扫描常见密钥和个人路径模式**

Run:

```powershell
git grep -I -n -E 'gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{16}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY'
git grep -I -n -E 'xwechat_files|C:[/\\]Users[/\\]|D:/kagllee|F:/|F:\\'
```

Expected: 密钥模式 0 命中；路径命中逐项列入隐私审查，不静默忽略。

- [ ] **Step 2: 输出上传内容与隐私清单并等待用户批准**

清单必须单列：

- Git 作者身份；
- 报告中的本机数据路径；
- 图片 ID 和 V2 置换记录；
- 完整交接 ZIP 内的同类信息；
- 已明确排除的 API Key、Token、验证码、原始 Kaggle 数据和本地配置。

Expected: 用户明确回复批准后才进入 Task 6。

### Task 6: 同步 F 盘独立交付目录

**Files:**
- Create: `F:\eda\severstal_modeling_handoff_v2_20260902\`
- Create: `F:\eda\severstal_modeling_handoff_v2_20260902.zip`

- [ ] **Step 1: 创建专用目录并复制 GitHub 发布候选快照**

使用 `git archive HEAD` 生成无 `.git`、无 `.venv`、无缓存的干净快照，再解压到：

```text
F:\eda\severstal_modeling_handoff_v2_20260902\
```

- [ ] **Step 2: 生成独立总 ZIP**

将上述专用目录压缩为：

```text
F:\eda\severstal_modeling_handoff_v2_20260902.zip
```

- [ ] **Step 3: 核对 F 盘快照与 Git 提交树**

比较文件数和逐文件 SHA-256；验证总 ZIP CRC，并确认 F 盘目录不含 `.git`、`.venv`、缓存和私密本地配置。

Expected: 文件差异 0、哈希不一致 0、ZIP CRC 错误为空。

### Task 7: 发布到 GitHub main

**Files:**
- Update: Git refs only

- [ ] **Step 1: 运行发布前最终验证**

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='.test-tmp-release'
git diff --check
git status --short --branch
```

Expected: `36 passed`、无差异错误、工作区清洁。

- [ ] **Step 2: 普通推送功能分支**

```powershell
git push -u origin handoff/severstal-v2
```

- [ ] **Step 3: 快进合并到 main 并推送**

```powershell
git checkout main
git pull --ff-only origin main
git merge --ff-only handoff/severstal-v2
git push origin main
```

- [ ] **Step 4: 核对远端 main**

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: 两个 SHA 完全一致；禁止使用强制推送。
