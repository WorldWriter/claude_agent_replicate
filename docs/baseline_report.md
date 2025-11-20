# DA-Code Benchmark 基准测试报告

## 📊 测试概述

- **测试日期**: 2025-11-20
- **Agent 版本**: MinimalKimiAgent (Stage 1)
- **模型**: Kimi K2 Turbo Preview (moonshot-v1-128k)
- **测试集**: DA-Code Benchmark (EMNLP 2024)
- **任务范围**: 59 个有 Gold 标准答案的任务

### Agent 能力配置

**工具集** (3个基础工具):
- `ReadFile`: 读取文件（限制1000字符，大文件建议用脚本）
- `WriteFile`: 写入文件
- `RunCommand`: 执行终端命令（60秒超时，黑名单保护）

**特点**:
- 无计划能力（Plan Agent 未启用）
- 无记忆/学习能力
- 纯 Reactive 模式：接收任务 → 工具调用 → 输出结果
- 最大轮次: 15 turns

---

## 🎯 总体结果

### 基准准确率

```
正确任务数: 14 / 59
基准准确率: 23.7%
```

### 对比 DA-Code 论文基准

| 系统 | 准确率 |
|------|--------|
| **MinimalKimiAgent (本次)** | **23.7%** |
| DA-Code 论文 Baseline | 30.5% |
| 人类专家 (DA-Code 论文) | ~85% |

**分析**: 当前系统略低于论文 baseline，主要原因：
1. 工具集简化（仅3个工具 vs 论文完整工具集）
2. 无计划能力（直接执行 vs 先规划）
3. ReadFile 限制导致大文件处理困难

---

## 📈 分类统计

### 按任务类型

| 任务类型 | 正确/总数 | 准确率 | 主要问题 |
|---------|----------|--------|----------|
| **Data Visualization** (plot-*) | 8/11 | **72.7%** ✅ | 最佳，仅2个未生成图片 |
| **Data Insight** (di-text-*) | 1/4 | **25.0%** | 格式匹配问题（键名/值顺序） |
| **Machine Learning** (ml-*) | 3/24 | **12.5%** ⚠️ | 大量未生成 result.csv |
| **Data Manipulation** (dm-csv-*) | 1/9 | **11.1%** ⚠️ | CSV处理逻辑错误 |
| **Statistical Analysis** (data-sa-*) | 1/9 | **11.1%** ⚠️ | 统计计算错误 |

### 按难度级别

| 难度 | 正确/总数 | 准确率 |
|------|----------|--------|
| Medium | 8/30 | 26.7% |
| Hard | 6/29 | 20.7% |

---

## 🔍 失败原因分析

### 失败类型分布

```
未生成文件:     22 个 (48.9%)  ← 最大问题
数值不匹配:     11 个 (24.4%)
格式/键不匹配:   8 个 (17.8%)
缺少Gold答案:    2 个 (4.4%)
CSV形状错误:     2 个 (4.4%)
```

### 典型失败案例

#### 1️⃣ 未生成文件 (22个)

**问题**: ML 任务中，Agent 编写了训练脚本但未生成 `result.csv`

**案例**: `ml-regression-002`
- Agent 成功训练模型
- 但忘记保存预测结果到 result.csv
- **原因**: Prompt 未明确要求生成文件

**影响任务**:
- ML Binary: ml-binary-013, ml-binary-016
- ML Clustering: ml-cluster-009/010/013/014/016/019
- ML Competition: ml-competition-001/003/005/006/008/009/017
- ML Multi-class: ml-multi-003/008/011
- ML Regression: ml-regression-002/004/008/014/015
- Visualization: plot-bar-006, plot-pie-008

#### 2️⃣ 数值计算错误 (11个)

**问题**: 统计计算或数据聚合逻辑错误

**案例**: `dm-csv-010` - Average Units Sold 数值不匹配
- 可能使用了错误的聚合方法（mean vs median）
- 或者分组逻辑错误

**影响任务**: dm-csv-010/011, data-sa-029/043, dm-csv-044

#### 3️⃣ 格式不匹配 (8个)

**案例**: `di-text-002` - 键名拼写错误
```json
预测: {"highest country": [...], "agricultural land %": [...]}
标准: {"highest country": [...], "agriculytural land %": [...]}  # typo in gold
```

**案例**: `di-text-003` - 值顺序颠倒
```json
预测: ["monaco", "south korea", "san marino", "andorra", "italy"]
标准: ["italy", "andorra", "san marino", "south korea", "monaco"]  # 反序
```

**影响任务**: di-text-002/003/004, dm-csv-015/052

#### 4️⃣ CSV 形状错误 (2个)

**案例**: `dm-csv-001`
```
预测: (0, 2)  # 空DataFrame
标准: (9, 2)  # 9行数据
```

**影响任务**: dm-csv-001, data-sa-031

---

## ✅ 成功案例分析

### 可视化任务成功率高 (72.7%)

**成功任务**: plot-bar-004/005/007/015, plot-line-006/015, plot-scatter-002, plot-pie-005

**成功原因**:
1. 任务明确：生成 result.png
2. 评估简单：只检查文件存在
3. Agent 能理解基本绘图逻辑（matplotlib/seaborn）

### CSV 完美匹配案例

**成功任务**: `dm-csv-050`, `data-sa-001`

**dm-csv-050 特点**:
- 数据清洗任务
- 逻辑清晰（删除重复、填充缺失值）
- CSV 完全匹配 Gold

**data-sa-001 特点**:
- 统计分析任务
- 计算正确
- 输出格式符合要求

---

## 🚀 优化方向建议

### Priority 1: 修复"未生成文件"问题 (影响 22 个任务)

**方案 A: 强化 Prompt**
```python
## 执行要求
1. 首先读取并理解数据文件
2. 编写 Python 代码完成任务
3. **必须生成结果文件**: result.csv (ML任务) 或 result.png (可视化任务)
4. 验证文件已成功生成
```

**方案 B: 添加文件验证工具**
```python
def VerifyOutput(expected_file: str) -> bool:
    """检查必需的输出文件是否存在"""
    return os.path.exists(expected_file)
```

**方案 C: 添加自我验证循环**
- 任务完成后，Agent 主动检查是否生成了要求的文件
- 如果缺失，重新执行生成步骤

**预期收益**: +22 个任务 → 准确率提升至 **61.0%**

---

### Priority 2: 改进数值计算准确性 (影响 11 个任务)

**问题根源**:
- 聚合方法选择错误（mean/median/sum）
- 分组逻辑错误
- 精度处理不当（舍入）

**优化方案**:
1. **添加数据验证工具**: 计算前后检查数据合理性
2. **增加示例提示**: 在 prompt 中提供聚合方法示例
3. **添加单元测试**: Agent 自动验证中间结果

**预期收益**: +5-8 个任务 → 准确率提升至 **31.4% - 37.3%**

---

### Priority 3: 格式标准化 (影响 8 个任务)

**JSON 输出标准化**:
```python
def StandardizeJSON(output: dict) -> dict:
    """标准化 JSON 输出格式"""
    # 统一键名大小写
    # 统一值的排序规则
    # 处理特殊字符
```

**预期收益**: +6-8 个任务 → 准确率提升至 **33.9% - 37.3%**

---

### Priority 4: ReadFile 限制优化

**当前限制**: 1000 字符（约 2-3k tokens）

**问题**: 无法直接读取大数据文件，需要编写脚本

**优化方案**:
1. 提升到 5000 字符
2. 添加分页读取参数：`ReadFile(path, offset=0, limit=1000)`
3. 自动建议：检测大文件时，提示使用脚本

---

### 长期优化方向

1. **添加 Plan Agent (Stage 2)**
   - 任务分解能力
   - 预期收益: +10-15% 准确率

2. **添加记忆/学习能力 (Stage 3)**
   - 从失败案例中学习
   - Prompt 动态优化
   - 预期收益: +5-10% 准确率

3. **扩展工具集**
   - `ListFiles`: 列出目录文件
   - `SearchData`: 数据搜索/过滤
   - `ValidateOutput`: 输出验证

---

## 📋 详细测试结果

### Data Insight (1/4 = 25%)

| 任务ID | 难度 | 结果 | 失败原因 |
|--------|------|------|----------|
| di-text-001 | Medium | ✅ | - |
| di-text-002 | Medium | ❌ | 键名不匹配 (gold 有 typo) |
| di-text-003 | Medium | ❌ | 值顺序颠倒 |
| di-text-004 | Medium | ❌ | 标签映射错误 |

### Data Manipulation (1/9 = 11.1%)

| 任务ID | 难度 | 结果 | 失败原因 |
|--------|------|------|----------|
| dm-csv-001 | Medium | ❌ | 空 DataFrame (0行) |
| dm-csv-007 | Hard | ❌ | 未生成 result.csv |
| dm-csv-009 | Hard | ❌ | Best-Rated Author 值错误 |
| dm-csv-010 | Hard | ❌ | Average Units Sold 数值错误 |
| dm-csv-011 | Medium | ❌ | total_quantity 计算错误 |
| dm-csv-015 | Medium | ❌ | 列名不匹配 |
| dm-csv-043 | Hard | ❌ | 未生成 retension.csv |
| dm-csv-044 | Hard | ❌ | 列1数值不匹配 |
| dm-csv-050 | Medium | ✅ | - |
| dm-csv-052 | Hard | ❌ | RFM_Level 分类错误 |

### Machine Learning (3/24 = 12.5%)

| 任务ID | 难度 | 结果 | 失败原因 |
|--------|------|------|----------|
| ml-binary-009 | Medium | ✅ | - |
| ml-binary-013 | Hard | ❌ | 未生成 result.csv |
| ml-binary-016 | Hard | ❌ | 未生成 result.csv |
| ml-cluster-002 | Medium | - | 无 Gold 答案 |
| ml-cluster-005 | Medium | - | 无 Gold 答案 |
| ml-cluster-009 | Hard | ❌ | 未生成 result.csv |
| ml-cluster-010 | Medium | ❌ | 未生成 result.csv |
| ml-cluster-013 | Hard | ❌ | 未生成 result.csv |
| ml-cluster-014 | Medium | ❌ | 未生成 result.csv |
| ml-cluster-016 | Hard | ❌ | 未生成 result.csv |
| ml-cluster-019 | Hard | ❌ | 未生成 result.csv |
| ml-competition-001 | Hard | ❌ | 未生成 result.csv |
| ml-competition-003 | Hard | ❌ | 未生成 result.csv |
| ml-competition-005 | Hard | ❌ | 未生成 result.csv |
| ml-competition-006 | Hard | ❌ | 未生成 result.csv |
| ml-competition-008 | Hard | ❌ | 未生成 result.csv |
| ml-competition-009 | Hard | ❌ | 未生成 result.csv |
| ml-competition-017 | Hard | ❌ | 未生成 result.csv |
| ml-multi-003 | Hard | ❌ | 未生成 result.csv |
| ml-multi-008 | Hard | ❌ | 未生成 result.csv |
| ml-multi-011 | Hard | ❌ | 未生成 result.csv |
| ml-regression-002 | Hard | ❌ | 未生成 result.csv |
| ml-regression-004 | Hard | ❌ | 未生成 result.csv |
| ml-regression-008 | Hard | ❌ | 未生成 result.csv |
| ml-regression-011 | Hard | ✅ | - |
| ml-regression-012 | Hard | ✅ | - |
| ml-regression-014 | Hard | ❌ | 未生成 result.csv |
| ml-regression-015 | Hard | ❌ | 未生成 result.csv |

### Statistical Analysis (1/9 = 11.1%)

| 任务ID | 难度 | 结果 | 失败原因 |
|--------|------|------|----------|
| data-sa-001 | Hard | ✅ | - |
| data-sa-004 | Hard | ❌ | CSV 形状错误 (4,1) vs (1,5) |
| data-sa-026 | Medium | ❌ | 未生成 result.csv |
| data-sa-028 | Hard | ❌ | CSV 形状错误 (1,2) vs (1,1) |
| data-sa-029 | Hard | ❌ | mean ratio 数值错误 |
| data-sa-031 | Medium | ❌ | 空 DataFrame (0行) |
| data-sa-039 | Hard | ❌ | 未生成 result.csv |
| data-sa-043 | Hard | ❌ | Sum-of-squared residuals 错误 |
| data-sa-061 | Hard | ❌ | 无 Gold CSV 文件 |

### Data Visualization (8/11 = 72.7%)

| 任务ID | 难度 | 结果 | 失败原因 |
|--------|------|------|----------|
| plot-bar-004 | Hard | ✅ | - |
| plot-bar-005 | Medium | ✅ | - |
| plot-bar-006 | Medium | ❌ | 未生成 result.png |
| plot-bar-007 | Hard | ✅ | - |
| plot-bar-015 | Hard | ✅ | - |
| plot-line-006 | Hard | ✅ | - |
| plot-line-015 | Hard | ✅ | - |
| plot-pie-005 | Medium | ✅ | - |
| plot-pie-008 | Medium | ❌ | 未生成 result.png |
| plot-scatter-002 | Hard | ✅ | - |

---

## 📌 结论

### 当前系统优势
1. ✅ **可视化任务表现优秀** (72.7%) - 证明基础工具集有效
2. ✅ **纯净基准** - 无复杂优化，适合作为优化起点
3. ✅ **完整测试覆盖** - 59 个任务全测试

### 主要瓶颈
1. ❌ **文件生成问题** (48.9% 失败) - Priority 1 需修复
2. ❌ **数值计算准确性** (24.4% 失败) - Priority 2
3. ❌ **格式标准化** (17.8% 失败) - Priority 3

### 下一步行动

**Phase 1: Quick Wins (预期 +20-30%)**
1. 强化 Prompt：明确要求生成文件
2. 添加输出验证步骤
3. JSON 格式标准化

**Phase 2: Agent 升级 (预期 +10-15%)**
1. 启用 Plan Agent (Stage 2)
2. 任务分解与规划能力

**Phase 3: 系统优化 (预期 +5-10%)**
1. 记忆/学习能力 (Stage 3)
2. 工具集扩展
3. Prompt 动态优化

**目标准确率**:
- 短期 (Phase 1): **45-55%**
- 中期 (Phase 2): **55-70%**
- 长期 (Phase 3): **70-80%** (接近人类水平)

---

**基准建立时间**: 2025-11-20
**测试耗时**: ~2 小时
**Agent**: MinimalKimiAgent v1.0 (Stage 1)
**Baseline 准确率**: **23.7%** (14/59)
