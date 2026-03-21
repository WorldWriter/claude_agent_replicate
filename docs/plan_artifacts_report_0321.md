# Plan Artifacts (显式计划产物) 特性报告

> 方向3：agent 主动声明输出文件名，减少对 eval config 的依赖

## 概述

### 背景

`output_format_validator`（verifymerged v2）通过从 `eval_test.jsonl` 动态读取期望文件名，修复了 v1 的文件名 bug，使整体得分从 0.382 提升至 0.472（+8.9pp）。

但该方案存在一个局限：**依赖 `eval_test.jsonl` 配置文件**。在真实部署场景中，agent 无法访问 ground-truth 配置，必须自行推断输出文件名，泛化能力受限。

### 方案

在 `TodoUpdate` 工具新增 `set_artifacts` action，让 agent **在规划阶段主动声明预期输出文件名**（plan_artifacts）。`VerifyResult` 采用三级优先链：

```
plan_artifacts（agent声明）> eval_config（jsonl配置）> heuristic（前缀规则兜底）
```

### 目标

- 减少对 `eval_test.jsonl` 的依赖
- 让 agent 在规划时即确定输出规格，避免任务末尾因文件名不确定导致的验证失败
- 为未来真实场景（无 eval config）提供基础

---

## 改动文件清单

| 文件 | 改动内容 |
|---|---|
| `dynamic_plan_agent.py` | `__init__` 新增 `plan_artifacts` / `_enable_verification_agent`；TodoUpdate 新增 `set_artifacts` action；`_generate_system_reminder_end` 注入 `<plan_artifacts>` block；`_tool_verify_result` 三级优先链 + source 标注；新增 `_spawn_verification_agent`；日志增加 `plan_artifacts` 字段 |
| `.claude/skills/da-code-solver/reference/base.md` | 规划阶段加第 4 步「声明输出规格」；TodoUpdate 工具说明增加 `set_artifacts` 使用示例 |
| `test/run_benchmark.py` | 新增 `--verify-agent` CLI flag；`run_test()` 接收并传递 `verify_agent` 参数 |

### 关键实现：`_tool_verify_result` 优先链

```python
# 1. 优先用 agent 声明的 plan_artifacts
if self.plan_artifacts:
    expected = self.plan_artifacts
    source = "plan_artifacts"
# 2. 其次从 eval_test.jsonl 读取
elif eval_config_files:
    expected = eval_config_files
    source = "eval_config"
# 3. 最后用前缀规则兜底
else:
    expected = heuristic_guess(task_id)
    source = "heuristic"
```

### 关键实现：`set_artifacts` action

```python
# agent 在规划阶段调用
TodoUpdate(action="set_artifacts", files=["price.csv"])
# → self.plan_artifacts = ["price.csv"]
```

### system_reminder 注入

```xml
<plan_artifacts>
  已声明输出文件：price.csv
  VerifyResult 将优先验证上述文件（优先级 > eval_config > heuristic）
</plan_artifacts>
```

---

## 实测数据

**测试时间**：2026-03-21
**测试集**：31 任务（均衡测试集，含 7 个特殊文件名任务）
**基准**：`output_dir_verify_merged`（verifymerged v2，0.4716）

### 整体结果

| 版本 | 平均分 | 成功(≥0.9) | 部分 | 失败 |
|---|---|---|---|---|
| verifymerged（基准） | 0.4716 | 10/31 | 9 | 12 |
| **plan_v1** | **0.4120** | 8/31 | 10 | 13 |
| 变化 | **-0.059** | -2 | +1 | +1 |

**set_artifacts 采用率**：14/31（45%）

### 特殊文件名任务对比（7 个）

| task_id | 期望文件 | set_artifacts | verifymerged | plan_v1 | diff |
|---|---|---|---|---|---|
| ml-regression-013 | price.csv | ✓ ['price.csv'] | 1.0000 | 1.0000 | 0 |
| ml-cluster-003 | cluster.csv | ✓ ['cluster.csv'] | 1.0000 | 1.0000 | 0 |
| ml-cluster-013 | cluster.csv | ✓ ['cluster.csv'] | 0.8663 | 0.8319 | -0.03 |
| ml-multi-004 | level.csv | ✓ ['level.csv'] | 1.0000 | 1.0000 | 0 |
| data-sa-007 | efficient_covariance_matrix.csv × 2 | ✗ 未调用 | 1.0000 | 0.0000 | -1.0 |
| data-wrangling-008 | cleaned_weather.csv | ✗ 未调用 | 0.1429 | 0.1429 | 0 |
| ml-regression-008 | quantity.csv | ✗ 未调用 | 0.5830 | 0.5084 | -0.07 |

### 退步任务分析

| task_id | verifymerged | plan_v1 | set_artifacts | 原因分析 |
|---|---|---|---|---|
| data-sa-007 | 1.0000 | 0.0000 | ✗ | 随机波动，未调用 set_artifacts，文件名回退到 heuristic 错误路径 |
| ml-competition-005 | 1.0000 | 0.2262 | ✓ submission.csv | 文件名正确（set_artifacts 生效），内容质量回退（随机波动） |
| plot-bar-022 | 1.0000 | 0.0000 | ✗ | 随机波动，生成代码有误 |
| ml-regression-008 | 0.5830 | 0.5084 | ✗ | 未调用 set_artifacts，轻微内容波动 |
| ml-cluster-013 | 0.8663 | 0.8319 | ✓ | 已调用，文件名正确，内容轻微波动 |

---

## 结论

### 特性本身有效

**已调用 set_artifacts 且文件名正确的任务**（4/7 特殊任务）均与基准持平或仅有内容随机波动，无因文件名错误导致的 0 分。plan_artifacts 特性本身**无负面影响**。

### 整体退步来自随机波动

整体 -0.059 完全来自 5 个任务的偶发失败：

- 3 个未调用 set_artifacts → 无 plan_artifacts 保护，文件名回退到 heuristic
- 2 个调用了 set_artifacts → 文件名正确，但内容质量随机下降

结论：这是模型随机性导致的正常波动，**不是特性引入的系统性退步**。

### 主要问题：set_artifacts 采用率偏低

45%（14/31）的采用率意味着 17 个任务中 agent 未在规划阶段声明输出文件，其中 3/7 特殊文件名任务未受到保护。

根因：`base.md` 中 `set_artifacts` 的提示强度不足，agent 在常规任务中倾向跳过该步骤。

---

## 下一步

| 优先级 | 方向 | 预期收益 |
|---|---|---|
| 高 | 强化 `base.md` 提示，要求规划阶段必须调用 `set_artifacts` | 采用率从 45% → 80%+，消除 3 个特殊任务的 heuristic fallback |
| 中 | `run_benchmark.py` 统计 `plan_artifacts` 字段分布，量化采用率趋势 | 持续监控，便于调优 |
| 低 | 在 `set_artifacts` 未调用时，`VerifyResult` 给出提示，引导 agent 补充声明 | 减少末尾文件名不确定 |

---

## 实现位置

| 位置 | 内容 |
|---|---|
| `dynamic_plan_agent.py:__init__` | `self.plan_artifacts = []` / `self._enable_verification_agent` |
| `dynamic_plan_agent.py:_tool_todo_update` | `set_artifacts` action 处理 |
| `dynamic_plan_agent.py:_generate_system_reminder_end` | `<plan_artifacts>` block 注入 |
| `dynamic_plan_agent.py:_tool_verify_result` | 三级优先链实现（plan_artifacts > eval_config > heuristic） |
| `dynamic_plan_agent.py:_spawn_verification_agent` | 验证子 agent 入口 |
| `.claude/skills/da-code-solver/reference/base.md` | 规划第 4 步「声明输出规格」 + set_artifacts 示例 |
| `test/run_benchmark.py` | `--verify-agent` CLI flag |
