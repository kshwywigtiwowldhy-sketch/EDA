# Severstal EDA 可复用工作流程

本文记录本项目从环境准备到最终交付的完整流程，便于以后在新电脑、新数据路径或新分支上复现。所有命令均以 PowerShell 7 为准。

## 1. 工作范围

本流程只回答四类问题：

- 每个类别在全部训练图片中出现多少次、占比多少；
- 哪些类别会在同一张图片上共现，精确标签组合有多少；
- 代表性、无缺陷、多标签和稀有样本的图像与掩码是什么样；
- 哪些类别、组合和微小掩码最稀有。

验证集设计、模型结构、训练、调参和比赛提交不属于本流程。

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
