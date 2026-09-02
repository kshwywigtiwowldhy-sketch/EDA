# Severstal EDA 工作进度与恢复点

更新时间：2026-09-01

## 已完成

- 已批准的设计规格与详细实施计划已写入 `docs/superpowers/` 并提交到本地 Git。
- 官方比赛数据已下载并解压到本机私有数据目录（公开仓库不记录绝对路径）。
- 已核验数据包包含 `train.csv`、`sample_submission.csv`、12,568 张训练图和 5,506 张测试图。
- 当前工作分支为 `eda/severstal-analysis`，原始数据保持只读且排除在 Git 之外。
- 已创建项目配置、依赖锁定清单和首组输入校验测试。
- 输入配置与数据集路径校验已按 TDD 完成，`tests/test_io.py` 为 3 项通过。
- 严格的列优先 RLE 解析、边界检查、重叠检查、面积计算与解码已完成；当前全套 12 项测试通过。
- 完整图像级标签表已完成；官方数据只读核验得到 12,568 张训练图、7,095 条正标注、6,666 张有缺陷图和 5,902 张无缺陷图，类别计数为 897/247/5,150/801；当前 17 项测试通过。
- 频率、精确标签组合、共现矩阵、条件共现、稀有排序与掩码面积分布已完成；官方全量 CSV 可完整计算，当前 22 项测试通过。
- 确定性抽样、标签频率图、组合图、共现热图和可复用掩码样本图已完成；PyParsing 锁定到兼容版本后测试无警告，当前 25 项测试通过。
- JSONL 事件日志、SHA-256 清单和失败关闭的端到端 CLI 已完成；成功/失败合成测试均通过，当前全套 29 项测试通过。
- 官方全量 EDA 已运行；9 张正式 CSV、5 张正式图、中文报告、运行摘要和 17 项 SHA-256 清单均已生成。
- Notebook 已非交互执行：14 个单元、7 个代码单元全部执行、0 错误；当前全套 31 项测试通过，清单 0 不匹配。
- `README.md` 和 `WORKFLOW.md` 已完成，包含复现、验证、故障恢复和 GitHub 隐私审批门槛。
- Windows 原子发布已修复为在最终目录创建同级临时文件后替换，避免跨沙箱身份 ACL 阻止读取；相关测试已加入。
- 已镜像到本机交付目录：清理 3 个可再生缓存目录后，9 张表、5 张图、报告和 Notebook 齐全，上一版 16 项 SHA-256 为 0 不匹配。
- 已完成上传前隐私扫描：未发现 API key、token、OAuth 查询串、私钥或凭据文件；发现本机绝对路径、F 盘路径、Git 作者邮箱元数据和 Kaggle 衍生图片，需要用户审查。
- 用户已批准保留现有 Git 身份与样例图；公开文件中的本机绝对路径已脱敏，真实数据路径只保存在被 Git 忽略的本机配置中。
- 五张 PNG 已按固定顺序整合为 `outputs/figures.zip`；ZIP CRC 校验通过，内部仅含 `figures/` 下的五张正式图。
- 最终候选文件二次隐私扫描为 0 命中：无 API key、token、OAuth 凭据、私钥、邮箱、本机用户目录或 F 盘路径。

## 当前进行中

- 最终验证、隐私审批、本地提交和本机交付目录同步均已完成。
- GitHub 远端写入暂被外部状态阻断：Git HTTPS 使用 OpenSSL 时连接被重置，改用 Windows Schannel 时 443 端口不可达；GitHub 连接器虽能读取仓库并显示 push 权限，但创建分支被 GitHub App 返回 403；本机未安装 `gh`，内置浏览器访问仓库也超时。
- 2026-09-01 再次上传前已复核：31 项测试通过、最终 44 个文件隐私扫描 0 命中、17 项 SHA-256 与五图 ZIP 校验通过。HTTPS/IPv4 无代理且访问 GitHub 超时；SSH 端口可达但账号未配置公钥；GitHub 账号身份正确，但 GitHub App 的已安装账号和可管理安装列表均为空，因此 API 写入仍不可用。
- 待网络或 GitHub App 写权限恢复后，直接普通推送 `eda/severstal-analysis` 即可；禁止强制推送，不需要重新运行 EDA。

## 后续顺序

1. 在 Codex 的 GitHub 连接中，把 GitHub App 安装到账号 `kshwywigtiwowldhy-sketch`，并授权仓库 `EDA` 的 contents/ref 写入；或恢复本机 GitHub HTTPS/SSH 凭据。
2. 普通推送 `eda/severstal-analysis` 分支。
3. 核对远端分支提交与本地 HEAD 一致，再按需要创建面向 `main` 的 PR。

## 快速恢复

仓库路径：

`<workspace>/work/EDA`

使用 PowerShell 7：

`pwsh`（PowerShell 7.6.5）

恢复时先检查：

```powershell
git status --short
git log --oneline -5
.\.venv\Scripts\python.exe -m pytest -v
```

数据不需要重新下载，也不需要重新进行 Kaggle 登录。
