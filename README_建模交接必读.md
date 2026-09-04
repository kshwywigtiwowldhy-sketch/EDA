# Severstal 数据审计、EDA 与建模交接包

版本：2026-09-02 · 最终验证划分：v2（冻结）

## 1. 交接结论

本包整合了数据审计、正式 EDA 和建模前验证集复核。建模必须使用 `03_final_split_v2/splits/` 中的最终划分：

- 训练集：10,054 张；
- 验证集：2,514 张；
- 两者交集、重复 ID、遗漏和未知 ID 均为 0；
- 覆盖全部 12,568 张训练图片；
- 在本次强近重复规则下，跨训练/验证近重复边为 0。

旧 V1 划分不要继续用于新的训练实验。

## 2. 本次补充和修改了什么

### 新增

- 建模前验证集最终复核；
- 训练/验证掩码面积分布比较；
- 全部训练图片的感知哈希近重复筛查；
- V1 → V2 的置换记录和最终验证结果；
- 最终冻结划分的 SHA-256；
- 无表头 CSV 的正确读取方式。

### 修改

- V1 中发现 19 条跨训练/验证的强近重复边，涉及 18 个近重复组；
- 将 18 张相关验证图移到训练集，并用 18 张标签组合相同、掩码面积尽量接近且不属于强近重复边的训练图进行置换；
- V2 的训练/验证数量及每种精确标签组合计数与 V1 完全相同；
- 删除了未经 Kaggle 官方确认的“麻点、夹杂、划痕、其他”等类别名称，统一使用 `class_1`～`class_4`；
- 更新了“划分尚未同步”等过时说明和三张相关图。

### 没有修改

- EDA 同学的核心统计逻辑和结论没有被推翻；
- 原始 `train.csv`、`sample_submission.csv` 和图片没有被修改；
- 标签频率、组合、共现、掩码面积等正式 EDA 结果保持不变。

## 3. 目录说明

```text
01_data_audit/
  severstal_data_audit_report.md   更新后的数据审计报告
  EDA交接说明.md                    更新后的阶段交接说明
  class_distribution.png          匿名类别版本的分布图
  defect_examples.png             匿名类别版本的掩码示例

02_eda/
  reports/eda_report.md            正式 EDA 报告
  outputs/tables/                  EDA 全部统计表
  outputs/figures/                 EDA 全部图形
  notebooks/severstal_eda.ipynb    已执行 Notebook
  src/、tests/                     分析代码和测试
  WORKFLOW.md                      复现说明

03_final_split_v2/
  splits/train_ids.csv             最终训练 ID
  splits/valid_ids.csv             最终验证 ID
  split_report.md                  最终划分方法和复核报告
  figures/                         最终划分与面积分布图
  evidence/                        V1 候选图、置换记录和机器校验结果
```

## 4. 建模同学如何使用

1. 从 Kaggle 获取比赛数据，不要使用本包替代原始数据。
2. 在自己的电脑上配置数据目录，保证包含 `train.csv`、`train_images/`、`test_images/` 和 `sample_submission.csv`。
3. 只读取本包 `03_final_split_v2/splits/` 下的最终划分。
4. 划分 CSV 没有表头，必须显式使用 `header=None`。

```python
import pandas as pd

train_ids = pd.read_csv(
    "03_final_split_v2/splits/train_ids.csv",
    header=None,
    names=["ImageId"],
)
valid_ids = pd.read_csv(
    "03_final_split_v2/splits/valid_ids.csv",
    header=None,
    names=["ImageId"],
)
```

5. 不在 `train.csv` 中的 5,902 张训练图是无缺陷样本，使用四通道全零掩码。
6. RLE 是 1-based、列优先编码，掩码尺寸为 256×1600。
7. 模型输出应为四个独立通道，因为一张图片可能包含多个类别。
8. 验证指标应按比赛的每个 `ImageId × ClassId` Dice 口径实现，并正确处理真实和预测都为空的情况。

## 5. 建模阶段必须关注

- `class_3` 最常见，`class_2` 最稀有，存在明显类别不平衡；
- `class_1`、`class_2` 掩码通常较小，缩放和裁剪时要避免小目标消失；
- 约 46.96% 的训练图片无缺陷，控制假阳性非常重要；
- 本地 `sample_submission.csv` 是简化占位结构，提交前必须重新核对 Kaggle 要求；
- 验证划分已经冻结，不应为了提高验证分数反复调整。

## 6. 冻结文件哈希

```text
train_ids.csv  4bd175ac3399a433f3f8164fa523e7eb982a40a0eff7b23ac731414bc1a84b0b
valid_ids.csv  4f08d19ac713e179b5bb566e4819cf55e10a8c04b2a5fb0f8733f12b83eeef5f
```

建模实验记录中建议同时保存这两个哈希，以证明不同成员使用的是同一份划分。

## 7. 使用边界

- 感知哈希只能识别当前阈值下的强视觉近重复，不能替代缺失的钢卷或生产批次 ID；
- 不要把 `class_1`～`class_4` 擅自翻译成具体工业缺陷名称；
- 不要在群里发送 Kaggle 凭据、`.venv`、PyCharm `.idea`、缓存或账号信息；
- 是否允许转发原始比赛数据应遵守 Kaggle 竞赛规则。本包不包含原始图片。
