# Agent 精简重构报告 (2026-03-22)

## 背景

`dynamic_plan_agent.py` 经过多次迭代已达 1078 行，积累了大量 benchmark 专用逻辑：
- **VerifyResult 工具**（~270行）：硬编码的文件存在性、列名、行数、NaN、精度验证
- **output_plan 体系**（~45行）：TodoUpdate `plan` action + output_plan 状态 + system reminder 注入
- **任务类型检测/prompt 注入**（~44行）：agent 内部检测 `类型:` 行并注入策略 prompt
- **Verification Agent**（~40行）：spawn 独立 agent 做二次验证

这些逻辑与核心 agent 循环耦合，增加了维护成本和每次 API 调用的 token 消耗。

## 修改内容

### 从 agent 删除（-439行）

| 模块 | 行数 | 说明 |
|------|------|------|
| VerifyResult + Verification Agent | -270 | 删除 `_tool_verify_result()`、`_spawn_verification_agent()`、工具定义 |
| output_plan + plan action | -45 | 删除 `self.output_plan`、TodoUpdate `plan` 枚举、system reminder 中的 output_plan 块 |
| 任务类型检测 | -44 | 删除 `_detect_task_type()`、`_get_task_hint()`、`_load_prompt()`、`self.task_type` |
| Examples 合并 | -60 | 4 个 example 函数合并为 1 个 |
| system_reminder 清理 | -2 | 删除冗余的 `可用工具:` 行 |

### 迁移到 runner（run_benchmark.py）

- 新增 `load_task_strategy(task_type, task_id)` 函数：根据任务类型加载对应 `.md` 策略文件
- 替换 66 行 inline `type_hints` dict 为 `load_task_strategy()` 调用
- 删除 `--verify-agent` CLI 参数

### 更新 base.md 系统 prompt

- 删除"强制验证规则"章节（VerifyResult 引用）
- 删除 Plan 阶段第4步（plan action 引用）
- 新增简短验证指令："完成前用 RunCommand 验证输出文件存在且格式正确"

## 结果

**代码量**: 1078 → 639 行（-40.7%）

**工具数**: 5 → 4（ReadFile, WriteFile, RunCommand, TodoUpdate）

### Benchmark 对比（test 集 31 tasks, kimi-k2.5）

| 指标 | 精简前 (plan_v1) | 精简后 (slim_v1) |
|------|-----------------|-----------------|
| 平均得分 | ~0.42 | 0.4261 |
| 成功率 (≥0.9) | ~29% | 29.0% (9/31) |
| 完成率 | 100% | 100% |

**结论**: 删除 ~40% 代码后得分持平，说明硬编码验证逻辑对最终得分贡献极小，LLM 自身能力是决定因素。

### 各类型表现

| 类型 | 成功 | 部分 | 失败 | 备注 |
|------|------|------|------|------|
| ML | 5 | 4 | 0 | 强项，9/10 有分 |
| DM | 2 | 1 | 0 | 稳定 |
| Data Wrangling | 1 | 2 | 0 | |
| SA | 1 | 0 | 2 | |
| DI | 0 | 0 | 4 | 答案匹配严格 |
| Plot | 0 | 0 | 8 | 全灭，后处理 pipeline 问题 |
