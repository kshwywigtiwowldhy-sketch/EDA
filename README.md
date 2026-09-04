# Severstal Steel Defect Detection EDA

这是一个可复现、可测试、带运行留痕的 Severstal 钢板缺陷探索性分析项目。范围严格限定为：

1. 标签频率；
2. 标签共现与精确组合；
3. 代表性图片和 RLE 掩码可视化；
4. 稀有标签、稀有组合与微小掩码分析。

EDA 分析代码本身不包含数据下载审计、建模、训练或提交策略。仓库另行发布的冻结 V2 建模交接契约只提供经过复核的验证划分和使用说明，不改变上述 EDA 统计口径。

## 主要成果

- 训练图片：12,568 张；
- 有缺陷图片：6,666 张；
- 无缺陷图片：5,902 张；
- 正标注：7,095 条；
- 类别 1–4 图片数：897、247、5,150、801；
- 多标签图片：427 张；
- 最稀有已出现组合 `2+4`：1 张。

详细证据见 [中文报告](reports/eda_report.md)，可执行版本见 [Notebook](notebooks/severstal_eda.ipynb)。

## 建模交接：最终冻结 V2

建模前必须先读 [README_建模交接必读.md](README_建模交接必读.md) 和 [最终划分报告](03_final_split_v2/split_report.md)，并遵守以下契约：

- 只使用 [train_ids.csv](03_final_split_v2/splits/train_ids.csv) 和 [valid_ids.csv](03_final_split_v2/splits/valid_ids.csv)；旧划分全部作废。
- 两份 CSV 都没有表头；用 Pandas 读取时必须指定 `header=None`，否则第一张图片会被误当成列名。
- 12,568 张训练图中有 5,902 张未出现在 `train.csv` 中；这些无缺陷样本必须生成四通道全零掩码。
- 类别只使用匿名名称 `class_1`～`class_4`，不得采用未经 Kaggle 官方确认的中文缺陷名。
- 冻结 V2 为训练 10,054 张、验证 2,514 张。除非出现新的明确数据泄漏证据，不得为了模型分数反复修改划分。

可下载 [完整交接包](deliverables/severstal_modeling_handoff_v2_20260902.zip) 及其 [SHA-256 sidecar](deliverables/severstal_modeling_handoff_v2_20260902.zip.sha256)，或 [12 图图片包](deliverables/severstal_handoff_images_v2_20260902.zip) 及其 [SHA-256 sidecar](deliverables/severstal_handoff_images_v2_20260902.zip.sha256)。图片不在 Markdown 中逐张嵌入，以避免页面和交付记录膨胀。

## 快速运行

使用 PowerShell 7：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
Copy-Item config\eda_config.yaml config\eda_config.local.yaml
# 编辑 local 文件中的 dataset_dir；该文件不会进入 Git
.\.venv\Scripts\python.exe -m severstal_eda.cli --config config\eda_config.local.yaml
```

五张 PNG 会额外整合为 `outputs/figures.zip`，方便单文件上传。完整配置、复现、验证、故障处理和隐私发布流程见 [WORKFLOW.md](WORKFLOW.md)。

## 主要目录

```text
config/                 运行配置
src/severstal_eda/      唯一分析逻辑来源
tests/                  合成单元和集成测试
notebooks/              已执行 Notebook
outputs/tables/         正式 CSV 表格
outputs/figures/        五张正式图
outputs/figures.zip     五张图的统一上传包
reports/                中文分析报告
logs/                   JSONL 运行事件
MANIFEST.sha256         产物 SHA-256 清单
```

原始 Kaggle 数据、压缩包、虚拟环境和任何凭据均被排除在 Git 之外。任何 GitHub 写入前必须先完成人工隐私审查并获得数据所有者明确批准。
