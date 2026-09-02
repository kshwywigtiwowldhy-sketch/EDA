# Severstal Steel Defect Detection EDA

这是一个可复现、可测试、带运行留痕的 Severstal 钢板缺陷探索性分析项目。范围严格限定为：

1. 标签频率；
2. 标签共现与精确组合；
3. 代表性图片和 RLE 掩码可视化；
4. 稀有标签、稀有组合与微小掩码分析。

不包含数据下载审计、验证集划分、建模、训练或提交策略。

## 主要成果

- 训练图片：12,568 张；
- 有缺陷图片：6,666 张；
- 无缺陷图片：5,902 张；
- 正标注：7,095 条；
- 类别 1–4 图片数：897、247、5,150、801；
- 多标签图片：427 张；
- 最稀有已出现组合 `2+4`：1 张。

详细证据见 [中文报告](reports/eda_report.md)，可执行版本见 [Notebook](notebooks/severstal_eda.ipynb)。

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
