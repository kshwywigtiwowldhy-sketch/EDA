# Severstal EDA 可复用工作流程

本文记录本项目从环境准备到最终交付的完整流程，便于以后在新电脑、新数据路径或新分支上复现。所有命令均以 PowerShell 7 为准。

## 1. 工作范围

本流程只回答四类问题：

- 每个类别在全部训练图片中出现多少次、占比多少；
- 哪些类别会在同一张图片上共现，精确标签组合有多少；
- 代表性、无缺陷、多标签和稀有样本的图像与掩码是什么样；
- 哪些类别、组合和微小掩码最稀有。

第 2～12 节保留原始 EDA 流程；验证集设计、模型结构、训练、调参和比赛提交不属于 EDA 程序。第 13 节另行记录冻结 V2 的建模交接、归档与发布流程。

## 2. 输入与只读原则

必须存在以下官方数据文件：

```text
<dataset_dir>/train.csv
<dataset_dir>/sample_submission.csv
<dataset_dir>/train_images/*.jpg
<dataset_dir>/test_images/*.jpg
```

程序只读取这些文件，不修改、不移动、不重命名，也不会把原始数据复制进 Git。公开的 `config/eda_config.yaml` 使用相对示例路径；复制为被 Git 忽略的 `config/eda_config.local.yaml` 后，再填写本机数据位置。

程序支持两种标注格式：

- 当前格式：`ImageId, ClassId, EncodedPixels`；
- 旧格式：`ImageId_ClassId, EncodedPixels`。

CSV 中没有正标注行的训练图片必须通过图片清单补回，并显式标为 `no_defect=True`。因此频率分母永远是全部训练图片，而不是仅有缺陷的图片。

## 3. 环境准备

在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

项目锁定 Python 3.12 和关键依赖版本。Matplotlib 3.10.6 与 PyParsing 3.2.3 的组合用于避免弃用警告污染测试输出。

## 4. 配置

`config/eda_config.yaml`（公开模板）与 `config/eda_config.local.yaml`（本机私有配置）包含：

- 数据集目录；
- 表格、图形、报告、日志和清单路径；
- 图片尺寸 256×1600；
- 固定随机种子 42；
- 样本数量；
- 四类掩码的固定颜色。

路径若为相对路径，按 YAML 文件所在目录解析。程序在运行前检查所有必需输入，缺失时立即失败并写入 `run_failed`。

## 5. 测试驱动开发与验证

核心模块依次为：

```text
io.py             配置和输入存在性
rle.py            1-based、列优先 RLE 严格解析与解码
labels.py         完整图像级多标签表
analysis.py       频率、组合、共现、面积与稀有排序
visualization.py  确定性采样和五张图
provenance.py     JSONL 日志和 SHA-256
cli.py            失败关闭的端到端流程
```

运行测试：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

如当前 Windows 沙箱无权访问历史 pytest 临时目录，可指定一个新的专用目录：

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider --basetemp ..\pytest-temp-current -q
```

每个新功能遵循：先写失败测试，确认失败原因正确，再写最小实现，最后运行全量回归。

## 6. 正式运行

```powershell
Copy-Item config\eda_config.yaml config\eda_config.local.yaml
# 编辑 local 文件中的 dataset_dir 后运行：
.\.venv\Scripts\python.exe -m severstal_eda.cli --config config\eda_config.local.yaml
```

运行器执行以下步骤：

1. 读取配置并记录 `run_started`；
2. 验证输入文件和目录；
3. 读取 CSV 和完整训练图片清单；
4. 标准化标签并补入无缺陷图片；
5. 严格验证全部正 RLE，并以运行长度之和计算掩码面积；
6. 计算频率、组合、共现、条件共现、面积分位数和稀有排序；
7. 用固定种子选择代表性和稀有样本；
8. 在同盘临时目录生成全部表格、图形、摘要和报告；
9. 生成 SHA-256 清单；
10. 仅在全部成功后替换最终文件，报告最后发布；
11. 记录 `run_succeeded`。任何异常记录 `run_failed` 并重新抛出。

## 7. 统计口径

### 标签频率

`image_count` 是包含该类别的图片数；`image_fraction = image_count / 12568`。同一张多标签图片可同时计入多个类别，因此四类数量与无缺陷数量相加可以大于总图片数。

### 精确组合

每张图只有一个精确组合，例如 `1+3`、`2+4` 或 `none`。所有组合数量相加必须等于训练图片总数。

### 共现

- 对称计数矩阵：`C[i,j]` 为同时含类别 i 和 j 的图片数；
- 对角线：等于各类别图片数；
- 条件矩阵：按行除以该行对角线，表示“已知行类别存在时，列类别同时出现”的比例，因此不要求对称。

### 掩码面积

Severstal RLE 为 1-based、列优先（Fortran order）。单条标注面积直接等于所有 run length 之和，不需要为 7,095 条标注全部分配 256×1600 掩码。报告给出最小值、1/5/25/50/75/95/99 分位数、最大值，以及低于图片面积 0.01%、0.1%、1% 的比例。

### 稀有标签

类别和正标签组合按图片数升序排序，数量相同时使用稳定字典序。`none` 不参加稀有正标签组合排名，但保留在总组合表中。

## 8. 产物解释

正式表格位于 `outputs/tables/`：

- `image_label_table.csv`：12,568 行完整图片级标签；
- `label_frequency.csv`：四类和无缺陷频率；
- `label_combinations.csv`：全部精确组合；
- `cooccurrence_counts.csv`：对称共现计数；
- `cooccurrence_conditional.csv`：有方向的条件共现；
- `mask_area_statistics.csv`：每类面积和微小掩码统计；
- `rare_classes.csv`、`rare_combinations.csv`：稀有排序；
- `selected_samples.csv`：固定抽样 ID。

正式图位于 `outputs/figures/`：

- `label_frequency.png`；
- `label_combinations.png`；
- `cooccurrence_heatmap.png`；
- `representative_samples.png`；
- `rare_label_samples.png`。

上述五张 PNG 同时以确定性顺序打包为 `outputs/figures.zip`，便于把全部图片作为单个文件上传和传输；ZIP 内路径统一为 `figures/<文件名>`。

`outputs/run_summary.json` 记录环境、输入哈希、种子和所选样本；`logs/eda_run.jsonl` 记录每次成功与失败；`MANIFEST.sha256` 用于校验正式产物。

## 9. Notebook 执行

```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=180 notebooks\severstal_eda.ipynb
```

Notebook 调用与 CLI 相同的 `run_eda`，随后读取正式 CSV 和图形展示，不另写一套计算逻辑。

若 Jupyter 无权写用户配置目录，将以下环境变量指向一个新的可写临时目录：`JUPYTER_DATA_DIR`、`JUPYTER_CONFIG_DIR`、`JUPYTER_RUNTIME_DIR`、`IPYTHONDIR` 和 `MPLCONFIGDIR`。

## 10. 完整性核验

```powershell
Get-Content MANIFEST.sha256 | ForEach-Object {
    $parts = $_ -split '  ', 2
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $parts[1]).Hash.ToLowerInvariant()
    if ($actual -ne $parts[0]) { throw "Hash mismatch: $($parts[1])" }
}
```

还应人工检查五张图：标题、坐标轴、标签、数字是否可读；掩码是否与钢板缺陷位置对齐；代表性、无缺陷、多标签、稀有类别和稀有组合是否都出现。

## 11. GitHub 隐私审批门槛

任何上传、推送或 PR 之前必须：

1. 扫描工作树、暂存区和全部拟推送提交历史；
2. 检查 API key、token、OAuth、Cookie、`.env`、`kaggle.json`、邮箱、用户名、本机绝对路径和账号日志；
3. 检查原始比赛数据、ZIP 和 Notebook 内嵌图片是否适合公开；
4. 输出逐项隐私清单，敏感值只显示掩码或哈希指纹；
5. 对每项给出“保留、脱敏、排除”的建议；
6. 等待数据所有者明确批准；
7. 只有批准后才允许 `git push` 或任何 GitHub 写操作。

`.gitignore` 已排除原始数据、一般 ZIP、虚拟环境、本机配置、Kaggle 凭据、token 和 `.env`；仅明确放行经过验证的 `outputs/figures.zip`，但这不能替代上传前人工审查。

## 12. 中断与恢复

每个阶段完成后：

- 更新 `PROGRESS.md`；
- 运行对应测试；
- 创建一个聚焦的本地 Git 提交；
- 记录下一项工作。

恢复时先运行：

```powershell
git status --short
git log --oneline -8
Get-Content PROGRESS.md
.\.venv\Scripts\python.exe -m pytest -q
```

只要原始数据目录仍在，就不需要重新下载或重新进行 Kaggle 登录。

## 13. 冻结 V2 建模交接与可复用流程

本节是用户要求的“方便以后使用的工作流程总结”。它不改写前述 EDA 流程，而是把最终冻结 V2 从接收、审计、测试、归档到发布的顺序固化为以后可以逐项复用的 Markdown 工作手册。

### 13.1 接收完整包并先验证身份

完整 ZIP 与同名 sidecar 必须成组接收，禁止先解压后校验。ZIP 哈希须同时匹配 sidecar 和固定值 `72faab26d057529de6d9d16b13ea13de0a7ae5dd4e40a1cea575649d59b32922`；还须验证单行 sidecar、CRC、无重复或不安全成员，以及包根 `MANIFEST.sha256` 恰有 55 项且逐文件哈希和实际文件集合完全一致。

从仓库根目录在 PowerShell 7 中运行以下只读校验。参数集中在代码开头；临时目录使用唯一名称，创建前拒绝覆盖，`finally` 清理前再次确认它是仓库根下的精确目标。

```powershell
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath '.').Path
$archiveRelative = 'deliverables/severstal_modeling_handoff_v2_20260902.zip'
$sidecarRelative = 'deliverables/severstal_modeling_handoff_v2_20260902.zip.sha256'
$expectedArchiveSha = '72faab26d057529de6d9d16b13ea13de0a7ae5dd4e40a1cea575649d59b32922'
$archivePath = Join-Path $repoRoot $archiveRelative
$sidecarPath = Join-Path $repoRoot $sidecarRelative
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

foreach ($requiredFile in @($archivePath, $sidecarPath, $python)) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) { throw "Required file is missing: $requiredFile" }
}

$actualArchiveSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
if ($actualArchiveSha -cne $expectedArchiveSha) { throw 'Complete handoff ZIP SHA-256 mismatch' }

$sidecarRecords = @(Get-Content -LiteralPath $sidecarPath)
if ($sidecarRecords.Count -ne 1 -or [string]::IsNullOrWhiteSpace($sidecarRecords[0])) { throw 'The complete ZIP sidecar must contain exactly one record' }
$sidecarMatch = [regex]::Match($sidecarRecords[0], '^([0-9a-f]{64})  ([^\r\n]+)$')
if (-not $sidecarMatch.Success) { throw 'The complete ZIP sidecar format is invalid' }
if ($sidecarMatch.Groups[1].Value -cne $expectedArchiveSha -or
    $sidecarMatch.Groups[2].Value -cne [IO.Path]::GetFileName($archivePath)) {
    throw 'The complete ZIP sidecar digest or filename does not match'
}

$auditName = '.handoff-audit-' + [guid]::NewGuid().ToString('N')
$auditRoot = Join-Path $repoRoot $auditName
if (Test-Path -LiteralPath $auditRoot) { throw "Refusing to overwrite audit directory: $auditRoot" }

try {
    @'
from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

archive_path = Path(sys.argv[1])
extract_root = Path(sys.argv[2])


def is_safe_relative(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        bool(name)
        and "\\" not in name
        and not path.is_absolute()
        and not path.anchor
        and ".." not in path.parts
        and re.match(r"^[A-Za-z]:", name) is None
        and path.as_posix() == name
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if extract_root.exists():
    raise RuntimeError("audit directory already exists")

with zipfile.ZipFile(archive_path) as bundle:
    member_names = bundle.namelist()
    if len(member_names) != len(set(member_names)):
        raise RuntimeError("duplicate ZIP member")
    if any(not is_safe_relative(name) for name in member_names):
        raise RuntimeError("unsafe ZIP member path")
    if bundle.testzip() is not None:
        raise RuntimeError("ZIP CRC failure")
    bundle.extractall(extract_root)

root_entries = list(extract_root.iterdir())
if len(root_entries) != 1 or not root_entries[0].is_dir():
    raise RuntimeError("the archive must contain exactly one package root")
package_root = root_entries[0].resolve()
manifest_path = package_root / "MANIFEST.sha256"
if not manifest_path.is_file():
    raise RuntimeError("MANIFEST.sha256 is missing")

records = [
    line
    for line in manifest_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(records) != 55:
    raise RuntimeError("MANIFEST.sha256 must contain exactly 55 records")

listed_files: set[str] = set()
for record in records:
    match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", record)
    if match is None:
        raise RuntimeError("invalid MANIFEST.sha256 record")
    expected_digest, relative_name = match.groups()
    if not is_safe_relative(relative_name) or relative_name in listed_files:
        raise RuntimeError("unsafe or duplicate manifest path")
    listed_files.add(relative_name)
    relative_path = PurePosixPath(relative_name)
    target = package_root.joinpath(*relative_path.parts)
    if not target.resolve().is_relative_to(package_root) or not target.is_file():
        raise RuntimeError("manifest target is missing or outside the package root")
    if sha256(target) != expected_digest:
        raise RuntimeError("manifest SHA-256 mismatch")

actual_files = {
    path.relative_to(package_root).as_posix()
    for path in package_root.rglob("*")
    if path.is_file()
}
if actual_files != listed_files | {"MANIFEST.sha256"}:
    raise RuntimeError("unlisted or missing package member")

print("complete handoff archive verified")
'@ | & $python - $archivePath $auditRoot
    if ($LASTEXITCODE -ne 0) { throw 'Read-only ZIP verification failed' }
}
finally {
    if (Test-Path -LiteralPath $auditRoot) {
        $resolvedAuditRoot = (Resolve-Path -LiteralPath $auditRoot).Path
        $expectedAuditRoot = [IO.Path]::GetFullPath($auditRoot)
        if ($resolvedAuditRoot -ne $expectedAuditRoot -or
            (Split-Path -Parent $resolvedAuditRoot) -ne $repoRoot -or
            [IO.Path]::GetFileName($resolvedAuditRoot) -ne $auditName) {
            throw "Refusing unsafe audit cleanup: $resolvedAuditRoot"
        }
        Remove-Item -LiteralPath $resolvedAuditRoot -Recurse -Force
    }
}
```

### 13.2 阅读入口并按白名单导入

先阅读包根部 `README_建模交接必读.md` 和 `03_final_split_v2/split_report.md`，再做任何建模或复制操作。两者分别定义使用边界与冻结划分的证据。

从外部审计工作区合并 V2 补充资料时，不做目录级递归复制。常规导入白名单只允许经过人工逐项确认的 Markdown、TXT、CSV 和 JSON；12 张发布图片使用第 13.4 节的独立成员白名单处理。明确排除 `__pycache__`、`.pytest_cache`、其他缓存、`*.egg-info`、虚拟环境、本地配置、凭据文件以及原始 Kaggle CSV/图片/ZIP。原始比赛数据继续从 Kaggle 合规获取，不进入本交接包。

### 13.3 用契约测试冻结关键事实

在合并和归档前运行契约测试，逐项锁定以下事实：

- 训练/验证分别为 10,054 / 2,514，集合内无重复、集合间无交集，并集为全部 12,568 张图片；
- `train_ids.csv` 与 `valid_ids.csv` 分别保持 SHA-256 `4bd175ac3399a433f3f8164fa523e7eb982a40a0eff7b23ac731414bc1a84b0b` 和 `4f08d19ac713e179b5bb566e4819cf55e10a8c04b2a5fb0f8733f12b83eeef5f`；
- 两份 CSV 无表头，所有图片 ID 已知，所有精确标签组合在 V1 → V2 后的训练/验证计数不变；
- 类别名称只能是匿名的 `class_1`～`class_4`，5,902 张无缺陷图片按零掩码契约处理；
- V2 的强跨集合近重复边为 0；
- 面积分布图名只能是 `mask_area_split_distribution_v2.png`，旧误名不得出现在面向建模的最终文档中。

文档和归档完成后的全量回归固定在仓库根目录、现有虚拟环境和 PowerShell 7 中运行。固定临时目录 `.test-tmp-final` 不得预先存在；以下保护先确认其父目录就是仓库根，`finally` 清理前再确认精确绝对路径，避免 pytest 覆盖未知既有目录：

```powershell
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath '.').Path
$testTemp = [IO.Path]::GetFullPath((Join-Path $repoRoot '.test-tmp-final'))
if ((Split-Path -Parent $testTemp) -ne $repoRoot) { throw "Unsafe pytest temp parent: $testTemp" }
if (Test-Path -LiteralPath $testTemp) { throw "Refusing to overwrite existing pytest temp directory: $testTemp" }

try {
    & '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider --basetemp='.test-tmp-final'
    if ($LASTEXITCODE -ne 0) { throw 'Full pytest regression failed' }
}
finally {
    if (Test-Path -LiteralPath $testTemp) {
        $resolvedTestTemp = (Resolve-Path -LiteralPath $testTemp).Path
        if ($resolvedTestTemp -ne $testTemp -or
            (Split-Path -Parent $resolvedTestTemp) -ne $repoRoot) {
            throw "Refusing unsafe pytest temp cleanup: $resolvedTestTemp"
        }
        Remove-Item -LiteralPath $resolvedTestTemp -Recurse -Force
    }
}
```

### 13.4 从图片白名单构建独立的 12 图 ZIP

图片包 `deliverables/severstal_handoff_images_v2_20260902.zip` 只能使用紧邻脚本中逐行列出的 `$members` 数组；它是本文唯一规范的 12 个 POSIX 相对路径白名单，并与 `tests/test_handoff_v2.py` 的 `EXPECTED_IMAGE_MEMBERS` 同源锁定。不得通过通配符把目录中新出现的图片自动带入。

以下 PowerShell 7/.NET 示例从仓库根运行。先把 `$verifiedSourceRoot` 设置为已通过第 13.1 节同等 CRC、路径和 55 项清单检查的交接包根目录，即直接包含 `01_data_audit/`、`02_eda/` 和 `03_final_split_v2/` 的目录；不得指向未经验证的解压结果。脚本先逐项验证 `$members` 中的源文件，再复制到唯一 staging 并保留目录结构。目标 ZIP 已存在时会停止，不会覆盖正式归档。

```powershell
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath '.').Path
$verifiedSourceRoot = '<verified-handoff-package-root>'
if ($verifiedSourceRoot.Contains('<') -or $verifiedSourceRoot.Contains('>') -or
    -not [IO.Path]::IsPathRooted($verifiedSourceRoot)) { throw 'Set $verifiedSourceRoot to the verified absolute package root' }
$sourceRoot = (Resolve-Path -LiteralPath $verifiedSourceRoot).Path
if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { throw "Verified package root is missing: $sourceRoot" }
$archiveRelative = 'deliverables/severstal_handoff_images_v2_20260902.zip'
$archivePath = [IO.Path]::GetFullPath((Join-Path $repoRoot $archiveRelative))
$sidecarPath = [IO.Path]::GetFullPath($archivePath + '.sha256')
$archiveParent = Split-Path -Parent $archivePath
$members = @(
    '01_data_audit/class_distribution.png'
    '01_data_audit/defect_examples.png'
    '02_eda/outputs/figures/cooccurrence_heatmap.png'
    '02_eda/outputs/figures/label_combinations.png'
    '02_eda/outputs/figures/label_frequency.png'
    '02_eda/outputs/figures/rare_label_samples.png'
    '02_eda/outputs/figures/representative_samples.png'
    '03_final_split_v2/evidence/cross_split_near_duplicates_1.png'
    '03_final_split_v2/evidence/cross_split_near_duplicates_2.png'
    '03_final_split_v2/evidence/cross_split_near_duplicates_3.png'
    '03_final_split_v2/figures/mask_area_split_distribution_v2.png'
    '03_final_split_v2/figures/split_distribution.png'
)

if ($members.Count -ne 12 -or @($members | Sort-Object -Unique).Count -ne 12) { throw 'The image member whitelist must contain exactly 12 unique paths' }
if (-not $archivePath.StartsWith(
    $repoRoot + [IO.Path]::DirectorySeparatorChar,
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "Image archive must stay inside the repository: $archivePath"
}
if (-not (Test-Path -LiteralPath $archiveParent -PathType Container)) { throw "Archive parent is missing: $archiveParent" }
foreach ($outputPath in @($archivePath, $sidecarPath)) {
    if ((Split-Path -Parent $outputPath) -ne $archiveParent) { throw "Unsafe image archive output path: $outputPath" }
    if (Test-Path -LiteralPath $outputPath) { throw "Refusing to overwrite existing image archive output: $outputPath" }
}

foreach ($member in $members) {
    $parts = @($member -split '/')
    if ($member.Contains('\') -or [IO.Path]::IsPathRooted($member) -or
        $member -match '^[A-Za-z]:' -or $parts -contains '..') {
        throw "Unsafe image member path: $member"
    }
    $source = Join-Path $sourceRoot $member.Replace('/', [IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Whitelisted image is missing: $member" }
}

$stagingName = '.handoff-images-' + [guid]::NewGuid().ToString('N')
$stagingRoot = Join-Path $repoRoot $stagingName
if (Test-Path -LiteralPath $stagingRoot) { throw "Refusing to overwrite staging directory: $stagingRoot" }

$outputsCompleted = $false
try {
    $null = New-Item -ItemType Directory -Path $stagingRoot
    foreach ($member in $members) {
        $nativeRelative = $member.Replace('/', [IO.Path]::DirectorySeparatorChar)
        $source = Join-Path $sourceRoot $nativeRelative
        $destination = Join-Path $stagingRoot $nativeRelative
        $null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination)
        Copy-Item -LiteralPath $source -Destination $destination
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        $stagingRoot,
        $archivePath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    $archiveSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
    $sidecarRecord = '{0}  {1}{2}' -f $archiveSha, [IO.Path]::GetFileName($archivePath), "`n"
    [IO.File]::WriteAllText(
        $sidecarPath,
        $sidecarRecord,
        [Text.UTF8Encoding]::new($false)
    )
    if ([IO.File]::ReadAllText($sidecarPath, [Text.Encoding]::UTF8) -cne $sidecarRecord -or
        $sidecarRecord -notmatch '^[0-9a-f]{64}  [^\r\n]+\n$') {
        throw 'Image archive sidecar is not exactly one valid record'
    }
    $outputsCompleted = $true
}
catch {
    if (-not $outputsCompleted) {
        foreach ($outputPath in @($sidecarPath, $archivePath)) {
            if (-not (Test-Path -LiteralPath $outputPath)) { continue }
            $resolvedOutput = (Resolve-Path -LiteralPath $outputPath).Path
            if ($resolvedOutput -ne $outputPath -or
                (Split-Path -Parent $resolvedOutput) -ne $archiveParent -or
                [IO.Path]::GetFileName($resolvedOutput) -notin @(
                    [IO.Path]::GetFileName($archivePath),
                    [IO.Path]::GetFileName($sidecarPath)
                )) {
                throw "Refusing unsafe partial output cleanup: $resolvedOutput"
            }
            Remove-Item -LiteralPath $resolvedOutput -Force
        }
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $stagingRoot) {
        $resolvedStaging = (Resolve-Path -LiteralPath $stagingRoot).Path
        $expectedStaging = [IO.Path]::GetFullPath($stagingRoot)
        if ($resolvedStaging -ne $expectedStaging -or
            (Split-Path -Parent $resolvedStaging) -ne $repoRoot -or
            [IO.Path]::GetFileName($resolvedStaging) -ne $stagingName) {
            throw "Refusing unsafe staging cleanup: $resolvedStaging"
        }
        Remove-Item -LiteralPath $resolvedStaging -Recurse -Force
    }
}
```

脚本用实际 ZIP 哈希生成唯一、无 BOM、严格单行的 sidecar，不把 `Get-FileHash` 的格式化输出重定向到文件。当前冻结图片 ZIP 的审计哈希为 `41232694f20e10b2dd2e5f3ccb0a64dbce64a96a9a9820a8ac6bed0e1f7cda50`。构建完成后立即运行合同测试；它验证 12 个成员、集合相等、路径安全、ZIP CRC、sidecar 文件名和哈希，预期为 5 passed：

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q -p no:cacheprovider tests/test_handoff_v2.py
```

### 13.5 建模端只读取冻结 V2

旧划分全部作废。必须从解压后的项目根或仓库根运行建模读取代码，并且只导入以下两个无表头文件：

```python
import pandas as pd

train_ids = pd.read_csv(
    "03_final_split_v2/splits/train_ids.csv", header=None, names=["ImageId"]
)
valid_ids = pd.read_csv(
    "03_final_split_v2/splits/valid_ids.csv", header=None, names=["ImageId"]
)
```

将 ID 与完整的 `train_images/` 清单对齐，而不是只以内含正标注的 `train.csv` 为样本全集。不在 `train.csv` 中的 5,902 张训练图片是无缺陷样本；为每张图生成形状为 `(4, H, W)` 的四通道全零掩码。如果项目统一采用通道在后的布局，等价形状为 `(H, W, 4)`，但同一训练管线内必须保持一种布局。类别只称为 `class_1`～`class_4`，不引入未经官方确认的中文缺陷名。

### 13.6 理解 V1 风险并冻结 V2

V1 在最终复核中存在 19 条强跨集合近重复边，涉及 18 个跨集合近重复组，可能令验证分数偏乐观。V2 将 18 张相关验证图移入训练集，并以 18 张安全训练图一对一置换到验证集；训练/验证仍为 10,054 / 2,514，所有精确标签组合计数保持不变，强跨集合近重复边降为 0。

V2 发布后即冻结。除非发现新的、可复核的明确数据泄漏证据，否则不得根据模型验证分数反复换样本、调种子或修改划分；若确需新版本，应保留 V2，另发带新版本号、报告、测试和哈希的划分。

### 13.7 发布前隐私与批准闸门

#### 13.7.1 只报告类别和位置的隐私扫描

将基线、最终获批对象和获批功能分支填写完整，再从仓库根运行以下 PowerShell 7 命令。它要求工作树干净，并扫描基线到获批提交的文件历史及每个提交的 Git 作者、提交者和消息元数据。所有 Git 路径生产命令都显式设置 `core.quotePath=false`，以本仓库已验证的逐行路径协议返回真实 Unicode 路径；worktree 路径保留为 PowerShell 数组并在 `--` 后逐项传递，含空格的文件名不会被字符串拼接拆分，index 内容则由 `git grep --cached ... --` 直接扫描完整索引，不以暂存差异代替索引。worktree、index 和 history 的文件内容扫描统一复用 `$secretPatterns`，文件名另按 `$sensitivePathPatterns` 分类；内容与文件名命中都只输出范围、命中类别和仓库相对位置，另外输出不含路径的 index 扫描文件数摘要。作者/提交者姓名与邮箱无条件以“提交 SHA、类别、脱敏指纹”进入清单；消息只在内存中匹配同等敏感模式，命中时仅输出提交 SHA 和类别。脚本不回显姓名、邮箱、消息或秘密值，也不把原始元数据写入文件。不得为了调试去掉 `-l`；ZIP、Notebook 和图片仍须人工审查。

```powershell
$ErrorActionPreference = "Stop"
$approvedBaseCommitSha = '<approved-full-40-character-base-commit-sha>'
$approvedCommitSha = '<approved-full-40-character-commit-sha>'
$featureBranch = '<approved-feature-branch>'
foreach ($candidateSha in @($approvedBaseCommitSha, $approvedCommitSha)) {
    if ($candidateSha -cnotmatch '^[0-9a-fA-F]{40}$') {
        throw 'Set both approved commit parameters to full 40-character hexadecimal SHAs'
    }
    git cat-file -e "${candidateSha}^{commit}"
    if ($LASTEXITCODE -ne 0) { throw 'An approved commit parameter does not identify a local commit' }
    $resolvedCandidate = @(git rev-parse --verify "${candidateSha}^{commit}")
    if ($LASTEXITCODE -ne 0 -or $resolvedCandidate.Count -ne 1 -or
        $resolvedCandidate[0].ToLowerInvariant() -cne $candidateSha.ToLowerInvariant()) {
        throw 'An approved commit parameter does not resolve to its exact SHA'
    }
}
$approvedBaseCommitSha = $approvedBaseCommitSha.ToLowerInvariant()
$approvedCommitSha = $approvedCommitSha.ToLowerInvariant()
if ($featureBranch.Contains('<') -or $featureBranch.Contains('>')) {
    throw 'Set $featureBranch to the user-approved feature branch'
}
$validatedFeatureBranch = @(git check-ref-format --branch $featureBranch)
if ($LASTEXITCODE -ne 0 -or $validatedFeatureBranch.Count -ne 1 -or
    $validatedFeatureBranch[0] -cne $featureBranch) {
    throw 'The approved feature branch name is invalid'
}
$currentBranch = @(git branch --show-current)
if ($LASTEXITCODE -ne 0 -or $currentBranch.Count -ne 1 -or
    $currentBranch[0] -cne $featureBranch) {
    throw 'The current branch is not the approved feature branch'
}
$currentHeadSha = @(git rev-parse --verify HEAD)
if ($LASTEXITCODE -ne 0 -or $currentHeadSha.Count -ne 1 -or
    $currentHeadSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Current HEAD is not the approved commit'
}
$localFeatureSha = @(git rev-parse --verify "refs/heads/${featureBranch}^{commit}")
if ($LASTEXITCODE -ne 0 -or $localFeatureSha.Count -ne 1 -or
    $localFeatureSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'The local feature-branch tip is not the approved commit'
}
$worktreeState = @(git -c core.quotePath=false status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw 'Unable to verify the worktree state' }
if ($worktreeState.Count -ne 0) { throw 'The worktree must be clean before approval review' }
git merge-base --is-ancestor $approvedBaseCommitSha $approvedCommitSha
if ($LASTEXITCODE -ne 0) { throw 'The approved base is not an ancestor of the approved commit' }
$historyRange = "$approvedBaseCommitSha..$approvedCommitSha"

$secretPatterns = [ordered]@{
    'github-classic-token' = 'gh[pousr]_[A-Za-z0-9_]{20,}'
    'github-fine-grained-token' = 'github_pat_[A-Za-z0-9_]{20,}'
    'openai-api-key' = 'sk-[A-Za-z0-9_-]{20,}'
    'aws-access-key-id' = 'AKIA[A-Z0-9]{16}'
    'private-key-marker' = 'BEGIN[[:space:]](RSA[[:space:]]|EC[[:space:]]|OPENSSH[[:space:]])?PRIVATE[[:space:]]KEY'
    'credential-assignment' = '(api[_-]?key|access[_-]?token|oauth|cookie|secret|password)[[:space:]]*[:=]'
    'kaggle-credential-shape' = '"(username|key)"[[:space:]]*:[[:space:]]*"[^"]+"'
    'email-address' = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    'windows-local-path' = '(^|[^A-Za-z])[A-Za-z]:[\\/]'
    'home-directory-path' = '/(home|Users)/[^/[:space:]]+'
}
$sensitivePathPatterns = [ordered]@{
    'dotenv-file' = '(^|/)\.env(\.[^/]+)?$'
    'kaggle-credentials-file' = '(^|/)kaggle\.json$'
    'private-key-file' = '(^|/)(id_(rsa|dsa|ecdsa|ed25519)|[^/]+\.(pem|key|p12|pfx|ppk))$'
}
$metadataSecretPatterns = [ordered]@{
    'github-classic-token' = 'gh[pousr]_[A-Za-z0-9_]{20,}'
    'github-fine-grained-token' = 'github_pat_[A-Za-z0-9_]{20,}'
    'openai-api-key' = 'sk-[A-Za-z0-9_-]{20,}'
    'aws-access-key-id' = 'AKIA[A-Z0-9]{16}'
    'private-key-marker' = 'BEGIN\s+(RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY'
    'credential-assignment' = '(api[_-]?key|access[_-]?token|oauth|cookie|secret|password)\s*[:=]'
    'kaggle-credential-shape' = '"(username|key)"\s*:\s*"[^"]+"'
    'email-address' = '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    'windows-local-path' = '(^|[^A-Za-z])[A-Za-z]:[\\/]'
    'home-directory-path' = '/(home|Users)/[^/\s]+'
}
function Get-RedactedFingerprint([AllowEmptyString()][string]$Value) {
    $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
    return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($bytes)).ToLowerInvariant().Substring(0, 16)
}
$worktreeFiles = @(git -c core.quotePath=false ls-files --cached --others --exclude-standard)
if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate worktree files' }
$indexFiles = @(git -c core.quotePath=false ls-files --cached)
if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate index files' }
Write-Output ("scan-summary`tindex-files-scanned`t$($indexFiles.Count)")
$historyCommits = @(git rev-list $historyRange)
if ($LASTEXITCODE -ne 0) {
    throw 'Unable to enumerate the approved history range'
}
$historyFilesByCommit = @{}
foreach ($commit in $historyCommits) {
    $historyFiles = @(git -c core.quotePath=false ls-tree -r --full-tree --name-only $commit)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate a history file set' }
    $historyFilesByCommit[$commit] = $historyFiles
}

$metadataFormats = [ordered]@{
    'author-name' = '%an'
    'author-email' = '%ae'
    'committer-name' = '%cn'
    'committer-email' = '%ce'
    'commit-message' = '%B'
}
foreach ($commit in $historyCommits) {
    foreach ($field in $metadataFormats.GetEnumerator()) {
        $rawMetadata = @(git show --no-patch ("--format=" + $field.Value) $commit) -join "`n"
        if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git metadata category: $($field.Key)" }
        if ($field.Key -eq 'commit-message') {
            foreach ($pattern in $metadataSecretPatterns.GetEnumerator()) {
                if ($rawMetadata -match $pattern.Value) {
                    Write-Output ("{0}`tcommit-message-{1}" -f $commit, $pattern.Key)
                }
            }
            continue
        }
        $fingerprint = Get-RedactedFingerprint $rawMetadata
        Write-Output ("{0}`t{1}`tsha256:{2}" -f $commit, $field.Key, $fingerprint)
    }
}

foreach ($entry in $secretPatterns.GetEnumerator()) {
    if ($worktreeFiles.Count -gt 0) {
        $locations = @(& rg -I -i -l -e $entry.Value -- $worktreeFiles)
        $searchExit = $LASTEXITCODE
        if ($searchExit -gt 1) { throw "Worktree privacy scan failed: $($entry.Key)" }
        foreach ($location in $locations) {
            Write-Output ("worktree`t$($entry.Key)`t$location")
        }
    }

    if ($indexFiles.Count -gt 0) {
        $locations = @(git -c core.quotePath=false grep --cached -I -i -l -E -e $entry.Value --)
        $searchExit = $LASTEXITCODE
        if ($searchExit -gt 1) { throw "Index privacy scan failed: $($entry.Key)" }
        foreach ($location in $locations) {
            Write-Output ("index`t$($entry.Key)`t$location")
        }
    }
    foreach ($commit in $historyCommits) {
        $locations = @(git -c core.quotePath=false grep -I -i -l -E -e $entry.Value $commit)
        $searchExit = $LASTEXITCODE
        if ($searchExit -gt 1) { throw "History privacy scan failed: $($entry.Key)" }
        foreach ($location in $locations) {
            $historyPrefix = "${commit}:"
            if (-not $location.StartsWith($historyPrefix, [StringComparison]::Ordinal)) {
                throw 'History privacy scan returned an unexpected location format'
            }
            Write-Output ("history`t$($entry.Key)`t$($location.Substring($historyPrefix.Length))")
        }
    }
}

foreach ($entry in $sensitivePathPatterns.GetEnumerator()) {
    foreach ($path in $worktreeFiles) {
        if ($path -match $entry.Value) { Write-Output ("worktree`t$($entry.Key)`t$path") }
    }
    foreach ($path in $indexFiles) {
        if ($path -match $entry.Value) { Write-Output ("index`t$($entry.Key)`t$path") }
    }
    foreach ($commit in $historyCommits) {
        foreach ($path in @($historyFilesByCommit[$commit])) {
            if ($path -match $entry.Value) { Write-Output ("history`t$($entry.Key)`t$path") }
        }
    }
}
```

将上述位置逐项归类为“保留、脱敏、排除”，敏感值只保留掩码或哈希指纹。扫描无命中也不能越过用户批准；必须先提交最终隐私清单并获得数据所有者明确批准。

#### 13.7.2 批准后才执行 F 盘镜像

以下是批准后使用的参数化模板，本次文档任务不执行它。必须填写用户批准的完整提交 SHA、功能分支、尚不存在的 F 盘绝对交付目录及其 sibling 总 ZIP；脚本拒绝占位符、相对路径、盘符根目录、非 F 盘路径、不同父目录、同一路径和既有目标。任何本地归档或 F 盘写入前，它先确认批准提交真实且精确、当前分支和本地功能分支 tip 都指向该提交、HEAD 相同且工作树干净，并预检全部目标与临时路径。它只从 `$approvedCommitSha` 创建 clean snapshot，解压到独立交付目录；目录与 Git tree 的相对路径及 SHA-256 完全一致后，才在同级以目录内部相对路径为根创建总 ZIP。随后验证总 ZIP CRC、无重复/目录/不安全成员、成员集合及逐成员 SHA-256，并复核交付目录内原有 ZIP 的 CRC。失败时只删除本次成功创建且再次通过精确路径校验的交付目录和总 ZIP，绝不删除开头已存在的目标。

```powershell
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path -LiteralPath '.').Path
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
$approvedCommitSha = '<approved-full-40-character-commit-sha>'
$featureBranch = '<approved-feature-branch>'
$approvedDeliveryRoot = '<approved-f-drive-delivery-directory>'
$deliveryZip = '<approved-f-drive-delivery-zip>'

if ($approvedCommitSha -cnotmatch '^[0-9a-fA-F]{40}$') {
    throw 'Set $approvedCommitSha to the user-approved full 40-character hexadecimal SHA'
}
git cat-file -e "${approvedCommitSha}^{commit}"
if ($LASTEXITCODE -ne 0) { throw 'The approved commit does not identify a local commit' }
$resolvedApprovedCommit = @(git rev-parse --verify "${approvedCommitSha}^{commit}")
if ($LASTEXITCODE -ne 0 -or $resolvedApprovedCommit.Count -ne 1 -or
    $resolvedApprovedCommit[0].ToLowerInvariant() -cne $approvedCommitSha.ToLowerInvariant()) {
    throw 'The approved commit does not resolve to its exact SHA'
}
$approvedCommitSha = $approvedCommitSha.ToLowerInvariant()
if ($featureBranch.Contains('<') -or $featureBranch.Contains('>')) {
    throw 'Set $featureBranch to the user-approved feature branch'
}
$validatedFeatureBranch = @(git check-ref-format --branch $featureBranch)
if ($LASTEXITCODE -ne 0 -or $validatedFeatureBranch.Count -ne 1 -or
    $validatedFeatureBranch[0] -cne $featureBranch) {
    throw 'The approved feature branch name is invalid'
}
$currentBranch = @(git branch --show-current)
if ($LASTEXITCODE -ne 0 -or $currentBranch.Count -ne 1 -or
    $currentBranch[0] -cne $featureBranch) {
    throw 'The current branch is not the approved feature branch'
}
$currentHeadSha = @(git rev-parse --verify HEAD)
if ($LASTEXITCODE -ne 0 -or $currentHeadSha.Count -ne 1 -or
    $currentHeadSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Current HEAD is not the approved commit'
}
$localFeatureSha = @(git rev-parse --verify "refs/heads/${featureBranch}^{commit}")
if ($LASTEXITCODE -ne 0 -or $localFeatureSha.Count -ne 1 -or
    $localFeatureSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'The local feature-branch tip is not the approved commit'
}
$worktreeState = @(git status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw 'Unable to verify the worktree state' }
if ($worktreeState.Count -ne 0) { throw 'The worktree must be clean before F-drive delivery' }

foreach ($approvedPath in @($approvedDeliveryRoot, $deliveryZip)) {
    if ([String]::IsNullOrWhiteSpace($approvedPath) -or
        $approvedPath.Contains('<') -or $approvedPath.Contains('>') -or
        -not [IO.Path]::IsPathRooted($approvedPath)) {
        throw 'Set both delivery targets to user-approved absolute F-drive paths'
    }
}

$deliveryRoot = [IO.Path]::GetFullPath($approvedDeliveryRoot)
$deliveryZip = [IO.Path]::GetFullPath($deliveryZip)
$deliveryParent = [IO.Path]::GetDirectoryName($deliveryRoot)
$deliveryZipParent = [IO.Path]::GetDirectoryName($deliveryZip)
$deliveryVolumeRoot = [IO.Path]::GetPathRoot($deliveryRoot)
$deliveryZipVolumeRoot = [IO.Path]::GetPathRoot($deliveryZip)
if (-not [String]::Equals($deliveryVolumeRoot, 'F:\', [StringComparison]::OrdinalIgnoreCase) -or
    -not [String]::Equals($deliveryZipVolumeRoot, 'F:\', [StringComparison]::OrdinalIgnoreCase) -or
    [String]::Equals($deliveryRoot.TrimEnd('\', '/'), $deliveryVolumeRoot.TrimEnd('\', '/'), [StringComparison]::OrdinalIgnoreCase) -or
    [String]::Equals($deliveryZip.TrimEnd('\', '/'), $deliveryZipVolumeRoot.TrimEnd('\', '/'), [StringComparison]::OrdinalIgnoreCase) -or
    [String]::Equals($deliveryRoot, $repoRoot, [StringComparison]::OrdinalIgnoreCase) -or
    [String]::Equals($deliveryZip, $repoRoot, [StringComparison]::OrdinalIgnoreCase) -or
    [String]::Equals($deliveryRoot, $deliveryZip, [StringComparison]::OrdinalIgnoreCase) -or
    -not [String]::Equals($deliveryParent, $deliveryZipParent, [StringComparison]::OrdinalIgnoreCase) -or
    -not [String]::Equals([IO.Path]::GetExtension($deliveryZip), '.zip', [StringComparison]::OrdinalIgnoreCase) -or
    -not (Test-Path -LiteralPath $deliveryParent -PathType Container)) {
    throw 'Unsafe delivery targets or parents'
}
$resolvedDeliveryParent = (Resolve-Path -LiteralPath $deliveryParent).Path
if (-not [String]::Equals(
    $resolvedDeliveryParent,
    [IO.Path]::GetFullPath($deliveryParent),
    [StringComparison]::OrdinalIgnoreCase
)) {
    throw "Delivery parent does not resolve exactly: $deliveryParent"
}
foreach ($deliveryTarget in @($deliveryRoot, $deliveryZip)) {
    if (Test-Path -LiteralPath $deliveryTarget) {
        throw "Refusing to overwrite delivery target: $deliveryTarget"
    }
}
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Existing project Python is missing: $python"
}

$approvedTreePaths = @(git -c core.quotePath=false ls-tree -r --full-tree --name-only $approvedCommitSha)
if ($LASTEXITCODE -ne 0 -or $approvedTreePaths.Count -eq 0) {
    throw 'Unable to enumerate the approved commit tree'
}
$approvedTreeSet = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
foreach ($relative in $approvedTreePaths) {
    $parts = @($relative -split '/')
    if ([String]::IsNullOrWhiteSpace($relative) -or $relative.Contains('\') -or
        [IO.Path]::IsPathRooted($relative) -or $relative -match '^[A-Za-z]:' -or
        $parts -contains '..' -or -not $approvedTreeSet.Add($relative)) {
        throw "Unsafe or duplicate approved tree path: $relative"
    }
}

$snapshotName = '.approved-snapshot-' + [guid]::NewGuid().ToString('N')
$snapshotZip = Join-Path $repoRoot ($snapshotName + '.zip')
$snapshotRoot = Join-Path $repoRoot $snapshotName
foreach ($temporaryPath in @($snapshotZip, $snapshotRoot)) {
    $expectedTemporary = [IO.Path]::GetFullPath($temporaryPath)
    if ((Split-Path -Parent $expectedTemporary) -ne $repoRoot -or
        -not [IO.Path]::GetFileName($expectedTemporary).StartsWith($snapshotName)) {
        throw "Unsafe temporary snapshot path: $expectedTemporary"
    }
    if (Test-Path -LiteralPath $expectedTemporary) {
        throw "Refusing to overwrite temporary snapshot path: $temporaryPath"
    }
}

$deliveryRootCreated = $false
$deliveryZipCreated = $false
try {
    try {
        git archive --format=zip --output=$snapshotZip $approvedCommitSha
        if ($LASTEXITCODE -ne 0) { throw 'git archive of the approved commit failed' }

        Add-Type -AssemblyName System.IO.Compression
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($snapshotZip, $snapshotRoot)
        $null = New-Item -ItemType Directory -Path $deliveryRoot
        $deliveryRootCreated = $true
        [System.IO.Compression.ZipFile]::ExtractToDirectory($snapshotZip, $deliveryRoot)

        $sourceHashes = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
        foreach ($file in Get-ChildItem -LiteralPath $snapshotRoot -Recurse -File) {
            $relative = [IO.Path]::GetRelativePath($snapshotRoot, $file.FullName).Replace('\', '/')
            $sourceHashes.Add($relative, (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant())
        }
        $deliveryHashes = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
        foreach ($file in Get-ChildItem -LiteralPath $deliveryRoot -Recurse -File) {
            $relative = [IO.Path]::GetRelativePath($deliveryRoot, $file.FullName).Replace('\', '/')
            $deliveryHashes.Add($relative, (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant())
        }
        if ($approvedTreeSet.Count -ne $sourceHashes.Count -or $sourceHashes.Count -ne $deliveryHashes.Count) {
            throw 'Approved tree, snapshot, and delivery file counts differ'
        }
        foreach ($relative in $approvedTreeSet) {
            if (-not $sourceHashes.ContainsKey($relative) -or -not $deliveryHashes.ContainsKey($relative)) {
                throw "Delivery file set differs from the approved commit tree: $relative"
            }
            if ($sourceHashes[$relative] -cne $deliveryHashes[$relative]) {
                throw "Delivery SHA-256 mismatch: $relative"
            }
        }

        $zipMembers = [string[]]@($deliveryHashes.Keys)
        [Array]::Sort($zipMembers, [StringComparer]::Ordinal)
        $deliveryZipStream = $null
        $deliveryArchive = $null
        try {
            $deliveryZipStream = [IO.File]::Open(
                $deliveryZip,
                [IO.FileMode]::CreateNew,
                [IO.FileAccess]::ReadWrite,
                [IO.FileShare]::None
            )
            $deliveryZipCreated = $true
            $deliveryArchive = [IO.Compression.ZipArchive]::new(
                $deliveryZipStream,
                [IO.Compression.ZipArchiveMode]::Create,
                $true
            )
            foreach ($relative in $zipMembers) {
                $entry = $deliveryArchive.CreateEntry(
                    $relative,
                    [IO.Compression.CompressionLevel]::Optimal
                )
                $inputStream = [IO.File]::OpenRead((Join-Path $deliveryRoot $relative.Replace('/', '\')))
                $entryStream = $entry.Open()
                try { $inputStream.CopyTo($entryStream) }
                finally {
                    $entryStream.Dispose()
                    $inputStream.Dispose()
                }
            }
        }
        finally {
            if ($null -ne $deliveryArchive) { $deliveryArchive.Dispose() }
            if ($null -ne $deliveryZipStream) { $deliveryZipStream.Dispose() }
        }

        @'
import hashlib
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

snapshot_zip = Path(sys.argv[1])
delivery_root = Path(sys.argv[2])
delivery_zip = Path(sys.argv[3])

def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def sha256_stream(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()

def require_crc(path: Path) -> None:
    with zipfile.ZipFile(path) as bundle:
        if bundle.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")

require_crc(snapshot_zip)
for nested_zip in delivery_root.rglob("*.zip"):
    require_crc(nested_zip)

directory_hashes = {
    path.relative_to(delivery_root).as_posix(): sha256_path(path)
    for path in delivery_root.rglob("*")
    if path.is_file()
}
with zipfile.ZipFile(delivery_zip) as bundle:
    if bundle.testzip() is not None:
        raise RuntimeError("Total ZIP CRC failure")
    infos = bundle.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate total ZIP member")
    for info in infos:
        name = info.filename
        pure = PurePosixPath(name)
        if (
            info.is_dir()
            or "\\" in name
            or pure.is_absolute()
            or pure.anchor
            or ".." in pure.parts
            or re.match(r"^[A-Za-z]:", name)
        ):
            raise RuntimeError("Unsafe total ZIP member")
    if set(names) != set(directory_hashes):
        raise RuntimeError("Total ZIP member set differs from delivery directory")
    for info in infos:
        with bundle.open(info) as stream:
            if sha256_stream(stream) != directory_hashes[info.filename]:
                raise RuntimeError("Total ZIP member SHA-256 mismatch")
'@ | & $python - $snapshotZip $deliveryRoot $deliveryZip
        if ($LASTEXITCODE -ne 0) { throw 'Delivery ZIP verification failed' }

        $manifestLines = foreach ($relative in $zipMembers) {
            '{0}  {1}' -f $deliveryHashes[$relative], $relative
        }
        $manifestText = ($manifestLines -join "`n") + "`n"
        $manifestBytes = [Text.Encoding]::UTF8.GetBytes($manifestText)
        $directoryManifestSha = [Convert]::ToHexString(
            [Security.Cryptography.SHA256]::HashData($manifestBytes)
        ).ToLowerInvariant()
        $deliveryZipSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $deliveryZip).Hash.ToLowerInvariant()
        Write-Output ((
            'Successful-run evidence to append to PROGRESS.md: approved_commit={0} directory_files={1} ' +
            'directory_manifest_sha256={2} delivery_zip_sha256={3} delivery_zip_crc=verified'
        ) -f $approvedCommitSha, $deliveryHashes.Count, $directoryManifestSha, $deliveryZipSha)
    }
    finally {
        foreach ($temporaryPath in @($snapshotRoot, $snapshotZip)) {
            if (Test-Path -LiteralPath $temporaryPath) {
                $resolvedTemporary = (Resolve-Path -LiteralPath $temporaryPath).Path
                $expectedTemporary = [IO.Path]::GetFullPath($temporaryPath)
                if ($resolvedTemporary -ne $expectedTemporary -or
                    (Split-Path -Parent $resolvedTemporary) -ne $repoRoot -or
                    -not [IO.Path]::GetFileName($resolvedTemporary).StartsWith($snapshotName)) {
                    throw "Refusing unsafe snapshot cleanup: $resolvedTemporary"
                }
                Remove-Item -LiteralPath $resolvedTemporary -Recurse -Force
            }
        }
    }
}
catch {
    $deliveryFailure = $_
    if ($deliveryZipCreated -and (Test-Path -LiteralPath $deliveryZip)) {
        $resolvedCreatedZip = (Resolve-Path -LiteralPath $deliveryZip).Path
        if (-not [String]::Equals($resolvedCreatedZip, $deliveryZip, [StringComparison]::OrdinalIgnoreCase) -or
            -not [String]::Equals((Split-Path -Parent $resolvedCreatedZip), $resolvedDeliveryParent, [StringComparison]::OrdinalIgnoreCase) -or
            -not [String]::Equals([IO.Path]::GetFileName($resolvedCreatedZip), [IO.Path]::GetFileName($deliveryZip), [StringComparison]::Ordinal)) {
            throw "Refusing unsafe created ZIP rollback: $resolvedCreatedZip"
        }
        Remove-Item -LiteralPath $resolvedCreatedZip -Force
    }
    if ($deliveryRootCreated -and (Test-Path -LiteralPath $deliveryRoot)) {
        $resolvedCreatedRoot = (Resolve-Path -LiteralPath $deliveryRoot).Path
        if (-not [String]::Equals($resolvedCreatedRoot, $deliveryRoot, [StringComparison]::OrdinalIgnoreCase) -or
            -not [String]::Equals((Split-Path -Parent $resolvedCreatedRoot), $resolvedDeliveryParent, [StringComparison]::OrdinalIgnoreCase) -or
            -not [String]::Equals([IO.Path]::GetFileName($resolvedCreatedRoot), [IO.Path]::GetFileName($deliveryRoot), [StringComparison]::Ordinal)) {
            throw "Refusing unsafe created directory rollback: $resolvedCreatedRoot"
        }
        Remove-Item -LiteralPath $resolvedCreatedRoot -Recurse -Force
    }
    throw $deliveryFailure
}
```

#### 13.7.3 普通 GitHub push 与 fast-forward `main`

只有最终隐私清单和完整 40 位提交 SHA 获批且远端写权限可用后，才运行以下模板；本次文档任务不执行。任何远端访问或 checkout 前，它先确认当前分支名、当前 HEAD、本地功能分支 tip 和干净工作树都精确绑定到批准对象。它没有任何 force 参数，普通推送功能分支后要求远端功能分支等于批准 SHA，再以 `pull --ff-only` 和对批准 SHA 的 `merge --ff-only` 更新 `main`；合并后的本地 `main` 和普通推送后的远端 `main` 也必须等于批准 SHA。若仓库保护规则要求 PR，应停止直接更新 `main`，改走获批的普通 PR 流程，仍禁止 force push。

```powershell
$ErrorActionPreference = "Stop"
$remoteName = 'origin'
$approvedCommitSha = '<approved-full-40-character-commit-sha>'
$featureBranch = '<approved-feature-branch>'

if ($approvedCommitSha -cnotmatch '^[0-9a-fA-F]{40}$') {
    throw 'Set $approvedCommitSha to the user-approved full 40-character hexadecimal SHA'
}
git cat-file -e "${approvedCommitSha}^{commit}"
if ($LASTEXITCODE -ne 0) { throw 'The approved commit does not identify a local commit' }
$resolvedApprovedCommit = @(git rev-parse --verify "${approvedCommitSha}^{commit}")
if ($LASTEXITCODE -ne 0 -or $resolvedApprovedCommit.Count -ne 1 -or
    $resolvedApprovedCommit[0].ToLowerInvariant() -cne $approvedCommitSha.ToLowerInvariant()) {
    throw 'The approved commit does not resolve to its exact SHA'
}
$approvedCommitSha = $approvedCommitSha.ToLowerInvariant()
if ($featureBranch.Contains('<') -or $featureBranch.Contains('>')) {
    throw 'Set $featureBranch to the user-approved feature branch'
}
$validatedFeatureBranch = @(git check-ref-format --branch $featureBranch)
if ($LASTEXITCODE -ne 0 -or $validatedFeatureBranch.Count -ne 1 -or
    $validatedFeatureBranch[0] -cne $featureBranch) {
    throw 'The approved feature branch name is invalid'
}
$currentBranch = @(git branch --show-current)
if ($LASTEXITCODE -ne 0 -or $currentBranch.Count -ne 1 -or
    $currentBranch[0] -cne $featureBranch) {
    throw 'The current branch is not the approved feature branch'
}
$currentHeadSha = @(git rev-parse --verify HEAD)
if ($LASTEXITCODE -ne 0 -or $currentHeadSha.Count -ne 1 -or
    $currentHeadSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Current HEAD is not the approved commit'
}
$localFeatureSha = @(git rev-parse --verify "refs/heads/${featureBranch}^{commit}")
if ($LASTEXITCODE -ne 0 -or $localFeatureSha.Count -ne 1 -or
    $localFeatureSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'The local feature-branch tip is not the approved commit'
}
$worktreeState = @(git status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0) { throw 'Unable to verify the worktree state' }
if ($worktreeState.Count -ne 0) { throw 'The worktree must be clean before GitHub publication' }

git push $remoteName $featureBranch
if ($LASTEXITCODE -ne 0) { throw 'Normal feature-branch push failed' }

$remoteFeatureRecord = @(git ls-remote --heads $remoteName ("refs/heads/" + $featureBranch))
if ($LASTEXITCODE -ne 0 -or $remoteFeatureRecord.Count -ne 1) {
    throw 'Unable to read the remote feature-branch SHA'
}
$remoteFeatureSha = ($remoteFeatureRecord[0] -split '\s+')[0]
if ($remoteFeatureSha.ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Remote feature-branch SHA is not the approved commit'
}

git checkout main
if ($LASTEXITCODE -ne 0) { throw 'Unable to check out main' }
git pull --ff-only $remoteName main
if ($LASTEXITCODE -ne 0) { throw 'main is not fast-forwardable from its remote' }
git merge --ff-only $approvedCommitSha
if ($LASTEXITCODE -ne 0) { throw 'The approved commit cannot fast-forward main' }
$localMainSha = @(git rev-parse --verify HEAD)
if ($LASTEXITCODE -ne 0 -or $localMainSha.Count -ne 1 -or
    $localMainSha[0].ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Local main is not the approved commit after fast-forward merge'
}
git push $remoteName main
if ($LASTEXITCODE -ne 0) { throw 'Normal main push failed' }

$remoteMainRecord = @(git ls-remote --heads $remoteName 'refs/heads/main')
if ($LASTEXITCODE -ne 0 -or $remoteMainRecord.Count -ne 1) {
    throw 'Unable to read the remote main SHA'
}
$remoteMainSha = ($remoteMainRecord[0] -split '\s+')[0]
if ($remoteMainSha.ToLowerInvariant() -cne $approvedCommitSha) {
    throw 'Remote main is not the approved commit'
}
```

每一步都把提交 SHA、文件哈希、检查结果和批准状态追加到 `PROGRESS.md`，但绝不记录真实密钥、token、邮箱或用户路径值。
