# Severstal 建模交接 V2 整合设计

## 目标

在不重做、不移动现有 EDA 工程的前提下，把已校验的建模交接包、数据审计材料和最终冻结 V2 划分整合进 `EDA` 仓库，并生成可直接交付给建模同学的独立 F 盘目录与压缩包。

## 已确认的输入

- 原始交接包：`severstal_modeling_handoff_v2_20260902.zip`。
- 原始交接包 SHA-256：`72faab26d057529de6d9d16b13ea13de0a7ae5dd4e40a1cea575649d59b32922`。
- 包内清单：55 个文件，SHA-256 不一致项为 0。
- 冻结训练划分：10,054 个唯一图片 ID。
- 冻结验证划分：2,514 个唯一图片 ID。
- 两个集合交集为 0，并集为 12,568。
- `train_ids.csv` SHA-256：`4bd175ac3399a433f3f8164fa523e7eb982a40a0eff7b23ac731414bc1a84b0b`。
- `valid_ids.csv` SHA-256：`4f08d19ac713e179b5bb566e4819cf55e10a8c04b2a5fb0f8733f12b83eeef5f`。
- 交接包内 `02_eda` 的正式文件与仓库现有 EDA 成果一致；只存在不应交付的缓存、虚拟环境产物和本地配置差异。

## 采用的目录方案

保留仓库现有根目录中的 EDA 源码、测试、Notebook、报告和输出，不把它们整体移动到 `02_eda/`。新增材料按以下结构放置：

```text
EDA/
  README.md
  README_建模交接必读.md
  01_data_audit/
    EDA交接说明.md
    severstal_data_audit_report.md
  03_final_split_v2/
    split_report.md
    splits/
      train_ids.csv
      valid_ids.csv
    evidence/
      split_v2_changes.json
      split_v2_verification.json
  deliverables/
    severstal_modeling_handoff_v2_20260902.zip
    severstal_modeling_handoff_v2_20260902.zip.sha256
    severstal_handoff_images_v2_20260902.zip
    severstal_handoff_images_v2_20260902.zip.sha256
```

`README.md` 将明确：现有根目录对应正式 EDA，建模必须使用 `03_final_split_v2/splits/`，两份 CSV 无表头，5,902 张无标注图片必须构造四通道全零掩码，类别只能称为 `class_1`～`class_4`。

## 图片处理

新增交接图片不在 GitHub 中散落展开，而是统一放入 `deliverables/severstal_handoff_images_v2_20260902.zip`。图片 ZIP 保留来源相对路径，覆盖：

- 数据审计图；
- V2 划分分布与掩码面积图；
- V1 跨集合近重复证据图；
- 现有正式 EDA 的五张输出图。

完整原始交接 ZIP 仍原样保留，便于建模同学一次下载和核对上游清单。仓库中展开的报告、CSV 和 JSON 负责可审阅性；完整 ZIP 负责原始交付完整性。

## 数据流

1. 校验用户提供 ZIP 的外部 SHA-256。
2. 校验包内 `MANIFEST.sha256`。
3. 从已校验解压目录复制数据审计报告、V2 报告、冻结划分和机器验证 JSON。
4. 原样复制完整交接 ZIP 与 `.sha256` 到 `deliverables/`。
5. 从包内收集全部 PNG，按来源相对路径生成图片 ZIP 及 SHA-256 文件。
6. 更新仓库入口文档、复现说明和工作留痕。
7. 运行自动化测试及交接专项验证。
8. 生成独立 F 盘交付目录与总 ZIP。
9. 完成隐私清单审查后，普通推送并合并到 GitHub `main`，禁止强制推送。

## 验证与失败处理

实现交接专项测试或验证脚本，至少覆盖：

- 根 README 和 `split_report.md` 存在；
- 冻结 CSV 没有表头；
- 行数、唯一数、交集和并集满足 10,054 / 2,514 / 0 / 12,568；
- 两份 CSV 哈希与冻结值完全一致；
- `split_v2_verification.json` 的关键计数与 CSV 一致；
- 图片 ZIP 仅包含预期 PNG、没有路径穿越项、所有成员 CRC 正常；
- 完整交接 ZIP 哈希与用户提供值一致；
- 项目原有测试全部通过；
- Git 跟踪文件不含 API Key、OAuth Token、私钥、Kaggle 凭据、本地私密配置或微信目录绝对路径。

任一校验失败时停止打包、F 盘同步和 GitHub 上传；不尝试自动改写冻结划分。

## 隐私与发布边界

- 不上传 Kaggle API Key、GitHub Token、OAuth 回调参数、密码、验证码或私钥。
- 不上传原始 Kaggle 训练图、测试图或原始比赛数据。
- 不上传 `.venv`、`.idea`、缓存、本地路径配置或微信文件目录。
- 报告中的上游数据路径 `D:/kagllee/dataset` 属于待审查的本机路径信息；GitHub 上传前在隐私清单中明确列出并决定是否脱敏。
- 图片 ID、匿名类别编号、统计数值和 V2 置换记录属于比赛交接内容，不视为个人隐私，但仍列入发布内容摘要。
- F 盘交付目录为 `F:\eda\severstal_modeling_handoff_v2_20260902\`，总 ZIP 为 `F:\eda\severstal_modeling_handoff_v2_20260902.zip`。

## 完成标准

- 仓库保留现有 EDA 工程路径且原有测试通过。
- 新增报告、冻结划分、验证证据和两个交付 ZIP 均可核验。
- F 盘独立目录和总 ZIP 内容一致。
- 用户批准最终隐私清单。
- GitHub `main` 与本地最终提交 SHA 一致。
