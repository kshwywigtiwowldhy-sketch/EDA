# Severstal EDA 工作进度与恢复点

更新时间：2026-09-01

## 已完成

- 已批准的设计规格与详细实施计划已写入 `docs/superpowers/` 并提交到本地 Git。
- 官方比赛数据已下载并解压到 `F:/eda/dataset/severstal-steel-defect-detection`。
- 已核验数据包包含 `train.csv`、`sample_submission.csv`、12,568 张训练图和 5,506 张测试图。
- 当前工作分支为 `eda/severstal-analysis`，原始数据保持只读且排除在 Git 之外。
- 已创建项目配置、依赖锁定清单和首组输入校验测试。
- 输入配置与数据集路径校验已按 TDD 完成，`tests/test_io.py` 为 3 项通过。
- 严格的列优先 RLE 解析、边界检查、重叠检查、面积计算与解码已完成；当前全套 12 项测试通过。
- 完整图像级标签表已完成；官方数据只读核验得到 12,568 张训练图、7,095 条正标注、6,666 张有缺陷图和 5,902 张无缺陷图，类别计数为 897/247/5,150/801；当前 17 项测试通过。
- 频率、精确标签组合、共现矩阵、条件共现、稀有排序与掩码面积分布已完成；官方全量 CSV 可完整计算，当前 22 项测试通过。
- 确定性抽样、标签频率图、组合图、共现热图和可复用掩码样本图已完成；PyParsing 锁定到兼容版本后测试无警告，当前 25 项测试通过。

## 当前进行中

- 项目虚拟环境的核心测试依赖已可用；其余绘图与 Notebook 依赖正在补齐。
- 下一步是按 TDD 实现 SHA-256/JSONL 溯源、产物清单和一次性端到端 CLI，并用它生成五张正式图和全部表格。

## 后续顺序

1. 按 TDD 完成 RLE、标签表、统计、可视化、溯源和 CLI。
2. 对 F 盘官方全量数据运行 EDA。
3. 生成并执行 Notebook，生成中文报告与 `WORKFLOW.md`。
4. 运行全量测试、核对产物清单及哈希。
5. 将已验证成果同步到 `F:/eda`，提交本地 Git，并尝试推送 GitHub。

## 快速恢复

仓库路径：

`C:/Users/A/Documents/Codex/2026-08-31/github-plugin-github-openai-curated-remote/work/EDA`

使用 PowerShell 7：

`C:/Users/A/Documents/Codex/PowerShell/7.6.5/pwsh.exe`

恢复时先检查：

```powershell
git status --short
git log --oneline -5
.\.venv\Scripts\python.exe -m pytest -v
```

数据不需要重新下载，也不需要重新进行 Kaggle 登录。
