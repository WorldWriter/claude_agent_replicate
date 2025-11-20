# DA-Code Benchmark 测试说明

## 文件说明

- **test_dacode.py** - 主测试脚本，支持增量测试和多种模式
- **evaluate_dacode.py** - 评估脚本，比较 Agent 输出与 Gold 标准答案
- **baseline_tasks.json** - Baseline 59 个任务配置（基于 git clone 的 DA-Code 仓库）

## 测试模式

### 1. Quick 模式 ⚡

测试 **5 个**快速验证任务（每类任务各1个）

```bash
python test/test_dacode.py --mode quick
```

**任务列表**:
- `di-text-001` - Data Insight
- `dm-csv-050` - Data Manipulation
- `ml-regression-011` - Machine Learning
- `data-sa-001` - Statistical Analysis
- `plot-bar-005` - Data Visualization

**特点**:
- ✅ **预期准确率**: 100% (5/5) - 这5个任务在baseline测试中全部成功
- ⚡ **执行时间**: ~5-10 分钟
- 🎯 **用途**: 快速验证 Agent 改进是否有明显退化

**适用场景**:
- 开发调试时的快速反馈
- 验证 Agent 修改后是否仍能完成基础任务
- CI/CD 自动化测试的 smoke test
- 演示 Agent 基本能力

### 2. Baseline 模式（默认）

测试 **59 个** baseline 任务（git clone 时包含的 gold 任务）

```bash
python test/test_dacode.py
# 或
python test/test_dacode.py --mode baseline
```

**特点**:
- 📊 **Baseline 准确率**: 23.7% (14/59)
- ⏱️ **执行时间**: ~1.5-2 小时
- 📁 **无需额外下载**: 使用 git clone 自带的数据

**适用场景**:
- 建立基准性能
- 完整验证 Agent 改进效果
- 准备技术报告的标准测试集
- 不需要下载完整数据集（2.1GB）

### 3. All 模式

测试**所有**有 gold 答案的任务（需要先下载完整数据集）

```bash
python test/test_dacode.py --mode all
```

**前置条件**:
1. 下载完整 source 数据集（500+ 任务，2.1GB）
   ```bash
   # 使用 gdown 下载
   pip install gdown
   gdown "https://drive.google.com/uc?id=1eM_FVT1tlY4XXp6b7TrKzgTWOvskrjTs" -O source.zip
   unzip source.zip -d agent_workspace/da-code/da_code/
   ```

2. 替换原有的 source 目录

**适用场景**:
- 全面评估 Agent 性能
- 准备论文/报告的完整数据
- 对比不同模型在大规模数据集上的表现

## 命令行参数

```bash
python test/test_dacode.py [OPTIONS]

Options:
  --mode {quick,baseline,all}  测试模式 (默认: baseline)
                                - quick: 5个快速验证任务 (~5-10分钟)
                                - baseline: 59个基准任务 (~1.5-2小时)
                                - all: 所有有gold的任务 (~8-10小时)
  --max-turns MAX_TURNS        每个任务的最大轮次 (默认: 15)
  -h, --help                   显示帮助信息
```

### 示例

```bash
# 1. 快速测试（5个任务，推荐用于开发调试）
python test/test_dacode.py --mode quick

# 2. 默认 baseline 测试（59个任务）
python test/test_dacode.py
python test/test_dacode.py --mode baseline

# 3. 增加最大轮次到 20
python test/test_dacode.py --mode quick --max-turns 20

# 4. 测试所有任务（需要完整数据集）
python test/test_dacode.py --mode all

# 5. All 模式 + 最大轮次 25
python test/test_dacode.py --mode all --max-turns 25
```

### 模式对比

| 模式 | 任务数 | 预期准确率 | 执行时间 | 适用场景 |
|------|--------|-----------|----------|----------|
| **quick** | 5 | 100% | ~5-10分钟 | 快速验证、调试开发 |
| **baseline** | 59 | 23.7% | ~1.5-2小时 | 性能基准、完整验证 |
| **all** | 500+ | 待测 | ~8-10小时 | 全面评估、论文数据 |

## 增量测试

测试脚本会自动：
1. 扫描已有的测试结果（`logs/dacode_test_*.json`）
2. 跳过已测试的任务
3. 只测试剩余任务
4. 合并新旧结果

**示例**:
```bash
# 第一次运行：测试 59 个任务中的 30 个
python test/test_dacode.py --mode baseline

# 第二次运行：自动跳过已测试的 30 个，测试剩余 29 个
python test/test_dacode.py --mode baseline
```

## 评估结果

测试完成后，运行评估脚本：

```bash
python test/evaluate_dacode.py
```

评估脚本会：
1. 自动使用最新的测试结果文件
2. 比较 Agent 输出与 Gold 标准答案
3. 输出详细的评估报告

## 输出文件

### 测试结果

保存在 `logs/` 目录：

- `dacode_test_{timestamp}.json` - 本次新测试的结果
- `dacode_test_merged_{timestamp}.json` - 合并后的完整结果

### 工作目录

每个任务的执行目录：`agent_workspace/dacode_{task_id}/`

**注意**: 工作目录已在 `.gitignore` 中排除，不会提交到 git。

## Baseline 任务列表（59个）

当前 baseline 包含的 59 个任务：

### Data Insight (4)
- di-text-001, di-text-002, di-text-003, di-text-004

### Data Manipulation (9)
- dm-csv-001, dm-csv-007, dm-csv-009, dm-csv-010, dm-csv-011
- dm-csv-015, dm-csv-043, dm-csv-044, dm-csv-050, dm-csv-052

### Machine Learning (24)
- **Binary**: ml-binary-009, ml-binary-013, ml-binary-016
- **Clustering**: ml-cluster-009, ml-cluster-010, ml-cluster-013, ml-cluster-014, ml-cluster-016, ml-cluster-019
- **Competition**: ml-competition-001, ml-competition-003, ml-competition-005, ml-competition-006, ml-competition-008, ml-competition-009, ml-competition-017
- **Multi-class**: ml-multi-003, ml-multi-008, ml-multi-011
- **Regression**: ml-regression-002, ml-regression-004, ml-regression-008, ml-regression-011, ml-regression-012, ml-regression-014, ml-regression-015

### Statistical Analysis (9)
- data-sa-001, data-sa-004, data-sa-026, data-sa-028, data-sa-029
- data-sa-031, data-sa-039, data-sa-043, data-sa-061

### Data Visualization (11)
- **Bar**: plot-bar-004, plot-bar-005, plot-bar-006, plot-bar-007, plot-bar-015
- **Line**: plot-line-006, plot-line-015
- **Pie**: plot-pie-005, plot-pie-008
- **Scatter**: plot-scatter-002

## 常见问题

### Q: 为什么有些任务没有数据文件？

A: DA-Code git 仓库只包含 100 个示例任务的 source 数据。完整的 500+ 任务需要额外下载（见上文"All 模式"说明）。

### Q: 如何只重新测试失败的任务？

A: 目前脚本会自动跳过已完成的任务。如果要重测失败任务，需要手动删除对应的测试结果或修改代码。

### Q: 可以并行测试多个任务吗？

A: 当前版本是串行测试。并行测试需要额外的进程管理和资源控制，可在后续版本添加。

### Q: 测试结果文件很大怎么办？

A: 测试结果和对话日志已在 `.gitignore` 中排除。可以定期清理 `logs/` 目录的旧文件。

## 相关文档

- [DA-Code 论文](https://arxiv.org/abs/2410.07331)
- [DA-Code GitHub](https://github.com/dacodedev/da-code)
- [Baseline 测试报告](../docs/baseline_report.md)
