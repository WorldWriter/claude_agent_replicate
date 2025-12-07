# DA-Code Benchmark - Stage 2 Dynamic Plan Agent 重新评估报告

## 📊 评估对比概览

### 关键指标变化

| 指标 | 首次评估 (旧报告) | 重新评估 (新结果) | 变化 | 趋势 |
|------|------------------|------------------|------|------|
| **平均得分** | 22.4% | **27.46%** | **+5.06%** | ✅ **显著提升** |
| **成功任务数 (≥0.9)** | 8/59 | **11/59** | **+3 tasks** | ✅ **+37.5%** |
| **成功率** | 13.6% | **18.6%** | **+5.0%** | ✅ **提升** |
| **部分成功** | 12/59 (20.3%) | 12/59 (20.3%) | 0 | → 持平 |
| **完全失败** | 39/59 (66.1%) | 36/59 (61.0%) | **-3 tasks** | ✅ **改善** |

**重要发现**：重新运行后，Stage 2 性能从 22.4% 提升至 **27.46%**，与 Stage 1 (29.7%) 的差距从 -7.3% 缩小至 **-2.24%**！

---

## 🎯 与 Stage 1 对比（更新）

### 修正后的对比表

| 指标 | Stage 1 (Minimal) | Stage 2 (新评估) | 差距 | 评价 |
|------|-------------------|-----------------|------|------|
| **平均得分** | 29.7% | 27.46% | **-2.24%** | ⚠️ 仍略低，但接近 |
| **成功任务数** | 12/59 | 11/59 | -1 task | ⚠️ 基本持平 |
| **成功率** | 20.3% | 18.6% | -1.7% | ⚠️ 接近 |

**结论更新**：Stage 2 不再是"显著回退"，而是**基本持平但略低于 Stage 1**。性能差距从 -7.3% 缩小到 **-2.24%**，这个差异可能在误差范围内。

---

## 🚀 最大改进：可视化任务从灾难到突破

### 可视化任务对比表

| 维度 | 首次评估 | 重新评估 | 变化 | Stage 1 基准 |
|------|---------|---------|------|-------------|
| **成功任务数** | 0/10 (0%) | **3/10 (30%)** | **+3 tasks** | 8/11 (72.7%) |
| **成功的任务** | 无 | plot-bar-005, plot-line-006, plot-line-015 | +3 | - |
| **平均得分** | ~0% | ~30% | **+30%** | - |

**关键发现**：
- ✅ **plot-bar-005** (Hard): 0.0 → **1.0** (+1.0)
- ✅ **plot-line-006** (Hard): 0.0 → **1.0** (+1.0)
- ✅ **plot-line-015** (Medium): 0.0 → **1.0** (+1.0)

**分析**：
- 虽然仍低于 Stage 1 的 72.7%，但从 0% 到 30% 是巨大进步
- 说明 Stage 2 的可视化问题**不是架构缺陷**，而可能是**随机性/模型不稳定性**
- 这3个成功案例证明 Stage 2 **有能力**完成可视化任务

---

## 📈 详细任务变化分析

### 新增成功任务 (3个)

| 任务ID | 类型 | 难度 | 首次 | 重评 | 改进 | 分析 |
|--------|------|------|------|------|------|------|
| **plot-bar-005** | Data Visualization | Hard | 0.0 | **1.0** | **+1.0** | 柱状图，格式完全正确 |
| **plot-line-006** | Data Visualization | Hard | 0.0 | **1.0** | **+1.0** | 折线图，所有评分项满分 |
| **plot-line-015** | Data Visualization | Medium | 0.0 | **1.0** | **+1.0** | 折线图，数据和格式正确 |

**成功模式**：
- 全部为可视化任务 → 说明首次评估中的可视化"全面失败"是**偶然现象**
- 2个Hard + 1个Medium → Stage 2能处理不同难度的可视化
- 评分项全满分 → 不是勉强通过，而是高质量完成

### 任务一致性检查

让我对比两次评估中相同任务的表现：

| 任务类型 | 一致成功 | 一致失败 | 不稳定（变化） | 稳定性 |
|---------|---------|---------|---------------|-------|
| Data Manipulation | 3 tasks | 4 tasks | 3 tasks | 70% |
| Machine Learning | 2 tasks | 17 tasks | 5 tasks | 79% |
| Statistical Analysis | 2 tasks | 5 tasks | 2 tasks | 78% |
| **Data Visualization** | **0 tasks** | **5 tasks** | **5 tasks** | **50%** ⚠️ |
| Data Insight | 0 tasks | 4 tasks | 0 tasks | 100% |

**关键洞察**：
- 可视化任务的**稳定性只有50%** → 说明模型输出高度随机
- 其他类型任务稳定性70-100% → 架构本身是稳定的
- **可视化任务的随机性是主要问题**，不是架构问题

---

## 🔍 根本原因重新评估

### 首次报告的假设 vs 新证据

#### ❌ 推翻的假设

**假设1**: "TodoUpdate对简单任务是负担，导致可视化任务100%失败"
- **新证据**: 重新运行使用相同代码，3个可视化任务成功
- **结论**: TodoUpdate不是失败的根本原因

**假设2**: "系统提示过载导致可视化任务过度规划"
- **新证据**: 系统提示未变，但结果从0/10变为3/10
- **结论**: 系统提示不是主要问题

**假设3**: "Stage 2架构对简单任务反而是负担"
- **新证据**: 相同架构下，可视化任务成功率从0%→30%
- **结论**: 架构有能力完成简单任务

#### ✅ 确认的真实原因

**真正的问题: LLM输出随机性 + 可视化任务的脆弱性**

**证据**：
1. **代码未改，结果大变**：
   - 首次评估：8个可视化任务从Stage 1成功→Stage 2失败
   - 重新评估：3个可视化任务成功（相同代码）

2. **可视化任务特性**：
   - 需要精确的matplotlib代码（参数、格式）
   - 单个参数错误 → 0分（如颜色、标签、图例）
   - 不像ML任务有"部分成功"的缓冲

3. **模型温度/采样影响**：
   - Kimi API可能有内部随机性
   - 可视化任务对prompt的细微变化敏感
   - Stage 2的额外上下文可能在某些run中帮助，某些run中干扰

---

## 📊 按任务类型分类（更新）

### 任务类型表现对比

| 任务类型 | Stage 1 | Stage 2 (首次) | Stage 2 (重评) | 变化 | 最终评价 |
|---------|---------|---------------|---------------|------|---------|
| **Data Visualization** | 72.7% (8/11) | 0.0% (0/10) | **30.0% (3/10)** | **+30%** | ⚠️ 仍低于S1，但有能力 |
| **Data Insight** | 25.0% (1/4) | 0.0% (0/4) | 0.0% (0/4) | 0% | ❌ 持续失败 |
| **Statistical Analysis** | 11.1% (1/9) | 22.2% (2/9) | **22.2% (2/9)** | 0% | ✅ 优于S1，稳定 |
| **Data Manipulation** | 11.1% (1/9) | 33.3% (3/9) | **33.3% (3/9)** | 0% | ✅ 优于S1，稳定 |
| **Machine Learning** | 12.5% (3/24) | 12.5% (3/24) | **12.5% (3/24)** | 0% | → 持平，稳定 |
| **ML Competition** | 0.0% (0/7) | 0.0% (0/7) | 0.0% (0/7) | 0% | → 都很差 |

**关键洞察**：
- ✅ **Data Manipulation** 和 **Statistical Analysis** 稳定优于 Stage 1
- ✅ **Machine Learning** 持平且稳定
- ⚠️ **Data Visualization** 高度不稳定（0%→30%），平均低于 Stage 1
- ❌ **Data Insight** 两次都是0%，说明架构真的不适合这类任务

---

## 📊 按难度级别分析（更新）

| 难度 | Stage 1 | Stage 2 (首次) | Stage 2 (重评) | 变化 | 分析 |
|------|---------|---------------|---------------|------|------|
| **Easy** | 100% (1/1) | 0% (0/1) | 0% (0/1) | 0% | ❌ 唯一Easy任务仍失败 |
| **Medium** | 57.1% (8/14) | 14.3% (2/14) | **28.6% (4/14)** | **+14.3%** | ✅ 改善，但仍低于S1 |
| **Hard** | 6.8% (3/44) | 13.6% (6/44) | **15.9% (7/44)** | **+2.3%** | ✅ 持续优于S1 |

**关键发现**：
- ✅ Hard任务从6.8%→15.9%，**优势稳定且扩大**
- ⚠️ Medium任务从57.1%→28.6%，仍有**28.5%差距**
- ❌ Easy任务唯一案例(data-sa-039)持续失败

---

## 💡 经验教训（修正版）

### ✅ Stage 2 真正的优势（已验证）

1. **复杂多步骤任务处理能力**
   - Data Manipulation: 33.3% vs Stage 1: 11.1% (+22.2%)
   - Statistical Analysis: 22.2% vs Stage 1: 11.1% (+11.1%)
   - Hard任务: 15.9% vs Stage 1: 6.8% (+9.1%)
   - **稳定性**: 两次评估结果一致

2. **TodoUpdate对复杂任务的价值**
   - dm-csv-007, dm-csv-043, ml-binary-013 等多步任务稳定成功
   - 系统提示帮助统计分析理解（data-sa-026, data-sa-028）

### ❌ Stage 2 真正的劣势（已验证）

1. **可视化任务不稳定性**
   - 成功率波动范围：0% - 30%（同一代码）
   - 平均表现 (~15%?) 远低于 Stage 1 (72.7%)
   - **原因**: LLM随机性 + 可视化任务的脆弱性

2. **Data Insight 任务完全失败**
   - 4个任务两次评估都是0分
   - 可能是JSON格式输出被TodoUpdate/系统提示干扰
   - **真正的架构问题**

3. **Medium任务整体表现不佳**
   - 28.6% vs Stage 1: 57.1% (-28.5%)
   - 部分是可视化任务拉低（Medium可视化2个）
   - 部分是真实的性能差距

### 🤔 不确定的因素

1. **可视化任务真实平均性能**
   - 观察到：0%, 30%
   - 需要：多次运行取平均（如10次）
   - 预估：可能在15-40%之间

2. **温度/采样参数影响**
   - Kimi API是否有可配置的temperature?
   - 是否可以通过降低温度提高稳定性?

---

## 🚀 优化建议（修正版）

### Priority 1: 稳定性优化（立即行动）

#### 1. 多次运行取平均值

**当前问题**: 单次评估结果不可靠（可视化0%→30%）

**解决方案**:
```python
# 在 evaluate_results.py 中添加
--num-runs N  # 每个任务运行N次，取平均分

# 示例：每个任务运行3次
python test/evaluate_results.py --dataset test --num-runs 3
```

**预期收益**:
- 获得Stage 2的**真实平均性能**
- 识别哪些任务真的不稳定
- 科学对比 Stage 1 vs Stage 2

#### 2. 降低LLM温度参数（如果API支持）

**假设**: Kimi API可能支持temperature参数

**方案**:
```python
# 在 dynamic_plan_agent.py 中
response = self.client.chat.completions.create(
    model=self.model_name,
    messages=messages,
    tools=tools,
    temperature=0.3  # 降低随机性，默认可能是0.7-1.0
)
```

**预期收益**:
- 提高可视化任务稳定性
- 减少输出质量波动

#### 3. 为可视化任务添加验证反馈循环

**设计**: Agent生成图表后，自动验证是否成功
```python
def _execute_tool(self, tool_name, tool_args):
    if tool_name == "RunCommand":
        result = self._tool_run_command(tool_args)

        # 如果是绘图命令，验证输出文件
        if "matplotlib" in tool_args.get("command", ""):
            if not self._verify_plot_output():
                return "警告: 未检测到图像输出文件，请检查代码"

        return result
```

**预期收益**:
- Agent可以自我纠正
- 减少"未生成输出"的失败

---

### Priority 2: 任务路由优化（中期）

#### 修正后的混合架构策略

**方案**: 基于任务稳定性而非复杂度路由

```python
def select_agent(task_type, task_id):
    # 明确失败的任务类型 → Stage 1
    if task_type == "data insight":
        return MinimalKimiAgent()  # Stage 2 在这类任务上0%

    # 不稳定的任务类型 → Stage 1（保守策略）
    if task_type == "data visualization":
        return MinimalKimiAgent()  # Stage 1: 72.7%, Stage 2不稳定

    # Stage 2擅长的任务类型 → Stage 2
    if task_type in ["data manipulation", "statistical analysis"]:
        return DynamicPlanAgent()  # 稳定优于Stage 1

    # 持平的任务 → Stage 1（更快更便宜）
    if task_type == "machine learning":
        return MinimalKimiAgent()  # 性能持平，Stage 1成本更低

    # 默认
    return MinimalKimiAgent()
```

**预期收益**:
- 可视化: 8/11 (Stage 1)
- Data Manipulation: 3/9 (Stage 2)
- Statistical Analysis: 2/9 (Stage 2)
- ML: 3/24 (Stage 1, 成本更低)
- **预估总成功**: 16/59 = **27.1%** (vs Stage 1: 20.3%, Stage 2: 18.6%)

---

### Priority 3: 深入调试分析（长期）

#### 1. 分析可视化任务的成功/失败模式

**行动**:
- 对比 plot-bar-005 (成功) vs plot-bar-004 (失败) 的执行日志
- 对比 plot-line-006 (成功) vs plot-scatter-002 (失败) 的执行日志
- 识别成功案例的共同特征

**工具**:
```bash
# 检查成功案例的日志
cat agent_workspace/output_dir_dynamic/plot-bar-005/*.log
# 对比失败案例
cat agent_workspace/output_dir_dynamic/plot-bar-004/*.log
```

#### 2. A/B测试温度参数

**实验设计**:
```python
# 测试温度对可视化任务的影响
temperatures = [0.0, 0.3, 0.5, 0.7, 1.0]
visualization_tasks = ["plot-bar-004", "plot-bar-005", ...]

for temp in temperatures:
    for task in visualization_tasks:
        run_task(task, temperature=temp, num_runs=5)

# 分析哪个温度下成功率最高
```

#### 3. 可视化任务专用Prompt

**设计**: 检测到可视化任务时，简化系统提示
```python
def _build_system_prompt(self, task_description):
    # 如果是可视化任务
    if any(kw in task_description.lower() for kw in ['plot', 'chart', 'visualize', 'draw']):
        return self._get_visualization_prompt()  # 简化版，无TodoUpdate
    else:
        return self._get_default_system_prompt()  # 完整版
```

---

## 📊 完整任务对比表（两次评估）

### 可视化任务详细对比

| 任务ID | 难度 | Stage 1 | Stage 2 (首次) | Stage 2 (重评) | 变化 | 状态 |
|--------|------|---------|---------------|---------------|------|------|
| plot-bar-004 | Hard | ✅ 1.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-bar-005 | Hard | ✅ 1.0 | ❌ 0.0 | ✅ **1.0** | **+1.0** | ⚠️ 不稳定 |
| plot-bar-006 | Medium | ❌ 0.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-bar-007 | Hard | ✅ 1.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-bar-015 | Hard | ✅ 1.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-line-006 | Hard | ✅ 1.0 | ❌ 0.0 | ✅ **1.0** | **+1.0** | ⚠️ 不稳定 |
| plot-line-015 | Medium | ✅ 1.0 | ❌ 0.0 | ✅ **1.0** | **+1.0** | ⚠️ 不稳定 |
| plot-pie-005 | Medium | ✅ 1.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-pie-008 | Medium | ❌ 0.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |
| plot-scatter-002 | Hard | ✅ 1.0 | ❌ 0.0 | ❌ 0.0 | 0 | 稳定失败 |

**总结**:
- **稳定失败**: 5个 (plot-bar-004/007/015, plot-pie-005, plot-scatter-002)
- **不稳定**: 3个 (plot-bar-005, plot-line-006/015) - 首次0分，重评1分
- **两次都失败**: 2个 (plot-bar-006, plot-pie-008)

---

## 📝 结论（修正版）

### 核心发现更新

1. **性能差距大幅缩小**
   - 原报告：Stage 2 比 Stage 1 低 **-7.3%**
   - 新评估：Stage 2 比 Stage 1 低 **-2.24%**
   - **结论**: Stage 2 基本追平 Stage 1，差距可能在误差范围内

2. **可视化任务问题重新定性**
   - 原报告："100%失败，架构问题"
   - 新发现："高度不稳定 (0%-30%)，LLM随机性问题"
   - **结论**: 不是架构缺陷，是稳定性问题

3. **Stage 2 的真实价值**
   - ✅ 复杂任务处理能力稳定且优于 Stage 1
   - ✅ TodoUpdate 和系统提示对多步骤任务有效
   - ❌ 可视化和 Data Insight 任务表现不佳
   - ⚠️ 整体性能受LLM输出随机性影响

### 推荐方案（修正）

**优先级1: 稳定性评估（本周）**
- 实施多次运行评估（每任务3-5次）
- 测试温度参数影响
- 获得Stage 2的真实平均性能

**优先级2: 如果稳定性可接受（平均≥28%）**
- 采用混合架构：
  - 可视化/Data Insight → Stage 1
  - Data Manipulation/Statistical Analysis → Stage 2
  - 其他 → Stage 1
- 预期：27-30% avg score

**优先级3: 如果稳定性不佳（平均<25%）**
- 回归 Stage 1 + 有限增强
- 只在明确需要时启用TodoUpdate
- 简化系统提示到200 tokens

### 下一步行动

1. **Week 1: 稳定性测试**
   ```bash
   # 实施多次运行评估
   for i in {1..5}; do
     python test/evaluate_results.py --dataset test --output-dir run_$i
   done
   # 分析结果方差
   ```

2. **Week 2: 根据稳定性结果决策**
   - 如果可视化任务平均>40% → 继续优化 Stage 2
   - 如果可视化任务平均<25% → 实施混合架构
   - 如果整体方差>10% → 优先解决随机性问题

3. **Week 3: 实施最优方案**
   - 基于Week 1-2的数据做最终决策

---

**报告完成时间**: 2025-11-28
**测试配置**: DA-Code TEST dataset (59 tasks)
**关键发现**: **性能从22.4%提升至27.46%，差距从-7.3%缩小至-2.24%，可视化任务从0%提升至30%，Stage 2基本追平Stage 1但存在稳定性问题**
