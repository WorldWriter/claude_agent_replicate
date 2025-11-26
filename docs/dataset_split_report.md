# DA-Code 数据集划分报告

**生成日期**: 2025-11-22
**划分策略**: 双重分层随机抽样（任务类别 × 难度）
**随机种子**: 42（可复现）

---

## 1. 概览

| 数据集 | 任务数 | 占比 | 用途 |
|--------|--------|------|------|
| **测试集** (Test) | 59 | 11.8% | Baseline测试集，最终评估 |
| **训练集** (Train) | 50 | 10.0% | 提示工程优化、策略调试 |
| **验证集** (Val) | 50 | 10.0% | 超参数调优、策略验证 |
| **保留集** (Reserved) | 341 | 68.2% | 未来扩展（Stage 3+） |
| **总计** | 500 | 100.0% | DA-Code完整数据集 |

---

## 2. 难度分布对比

### 2.1 整体难度分布

| 难度级别 | 测试集 | 训练集 | 验证集 | 可用任务池 |
|---------|--------|--------|--------|-----------|
| Easy    | 1 (1.7%) | 16 (32.0%) | 16 (32.0%) | 103 (23.4%) |
| Medium  | 14 (23.7%) | 16 (32.0%) | 16 (32.0%) | 278 (63.0%) |
| Hard    | 44 (74.6%) | 18 (36.0%) | 18 (36.0%) | 60 (13.6%) |

### 2.2 分析

**Baseline测试集特点**:
- 极度偏向Hard任务（74.6%），反映真实业务场景的复杂性
- Easy任务仅1个（1.7%），Medium占23.7%
- 当前Baseline表现：29.7%平均分，Hard任务成功率仅6.8%

**训练集/验证集设计**:
- 采用**折中难度分布**（各33%），平衡挑战性和可学习性
- 相比Baseline：增加Easy/Medium比例，便于建立基础能力
- 相比可用任务池：适度增加Hard比例，保持一定挑战
- 训练集和验证集难度分布完全一致，确保公平验证

---

## 3. 任务类别分布

### 3.1 训练集 (50个任务)

| 任务类别 | 数量 | 占比 | Easy | Medium | Hard |
|---------|------|------|------|--------|------|
| Data Wrangling | 11 | 22.0% | - | - | - |
| Data Manipulation | 10 | 20.0% | - | - | - |
| Machine Learning | 9 | 18.0% | - | - | - |
| Data Insight | 6 | 12.0% | - | - | - |
| Data Visualization | 6 | 12.0% | - | - | - |
| Statistical Analysis | 6 | 12.0% | - | - | - |
| ML Competition | 2 | 4.0% | - | - | - |

### 3.2 验证集 (50个任务)

| 任务类别 | 数量 | 占比 | Easy | Medium | Hard |
|---------|------|------|------|--------|------|
| Data Wrangling | 12 | 24.0% | - | - | - |
| Data Manipulation | 10 | 20.0% | - | - | - |
| Data Insight | 8 | 16.0% | - | - | - |
| Machine Learning | 8 | 16.0% | - | - | - |
| Data Visualization | 6 | 12.0% | - | - | - |
| Statistical Analysis | 5 | 10.0% | - | - | - |
| ML Competition | 1 | 2.0% | - | - | - |

### 3.3 Baseline测试集 (59个任务)

| 任务类别 | 数量 | 占比 | Baseline准确率 | 特点 |
|---------|------|------|---------------|------|
| Machine Learning | 19 | 32.2% | 15.8% (3/19) | Hard任务为主，成功率低 |
| Data Manipulation | 10 | 16.9% | 10.0% (1/10) | 全部Hard，极具挑战 |
| Data Visualization | 10 | 16.9% | 0.0% (0/10) | 全部Hard，当前瓶颈 |
| Statistical Analysis | 9 | 15.3% | 44.4% (4/9) | 中等难度，表现较好 |
| ML Competition | 7 | 11.9% | 0.0% (0/7) | 全部Hard，Kaggle竞赛级 |
| Data Insight | 4 | 6.8% | 100.0% (4/4) | 全部成功！ |

**关键发现**:
- Data Insight: Baseline 100% 成功，训练集/验证集适度包含
- Data Visualization: Baseline 0% 成功，训练集/验证集各占12%，需重点训练
- ML Competition: 极稀缺资源（仅13可用），训练集2个，验证集1个

---

## 4. 数据集独立性验证

### 4.1 重叠检查

| 检查项 | 重叠任务数 | 状态 |
|--------|-----------|------|
| 训练集 ∩ 验证集 | 0 | ✓ 通过 |
| 训练集 ∩ 测试集 | 0 | ✓ 通过 |
| 验证集 ∩ 测试集 | 0 | ✓ 通过 |

### 4.2 ID范围

- **训练集任务ID示例**: `di-text-030`, `dm-csv-018`, `data-wrangling-030`, `ml-multi-007`, ...
- **验证集任务ID示例**: `di-csv-013`, `dm-csv-033`, `data-wrangling-036`, `ml-binary-022`, ...
- **测试集任务ID**: 见 `test/dataset_tasks.json` → `datasets.test.task_ids`

完整任务ID列表见: `test/dataset_tasks.json`

---

## 5. 采样方法详解

### 5.1 算法流程

```
1. 加载500个任务 (eval_all.jsonl)
2. 排除59个Baseline任务 → 441个可用任务
3. 双重分层:
   - 第一层: 7个任务类别
   - 第二层: 3个难度级别
   - 共21个层 (category × hardness)

4. 训练集抽样 (50个):
   - 目标难度: Easy 16, Medium 16, Hard 18
   - 在每个难度内，按类别比例分配配额
   - 随机抽样 + 移除已选任务

5. 验证集抽样 (50个):
   - 从剩余441-50=391个任务中抽样
   - 相同策略确保分布一致
```

### 5.2 关键参数

| 参数 | 值 | 说明 |
|------|-----|------|
| RANDOM_SEED | 42 | 确保可复现 |
| TRAIN_SIZE | 50 | 训练集大小 |
| VAL_SIZE | 50 | 验证集大小 |
| TARGET_DIFFICULTY_DIST | Easy 33%, Medium 33%, Hard 34% | 折中方案 |

---

## 6. Baseline性能回顾

### 6.1 整体表现 (59个任务)

| 指标 | 值 | 说明 |
|------|-----|------|
| 平均得分 | 29.7% | 基于评分标准 |
| 完全成功 (≥0.9分) | 12/59 (20.3%) | 高质量完成 |
| 部分成功 (0<分<0.9) | 11/59 (18.6%) | 接近正确 |
| 完全失败 (分=0) | 36/59 (61.0%) | 需改进 |

### 6.2 按类别表现

| 类别 | 任务数 | 成功率 | 难点 |
|------|--------|--------|------|
| Data Insight | 4 | 100.0% | ✓ 擅长 |
| Statistical Analysis | 9 | 44.4% | 中等 |
| Machine Learning | 19 | 15.8% | 困难 |
| Data Manipulation | 10 | 10.0% | 很困难 |
| **Data Visualization** | 10 | **0.0%** | **最大瓶颈** |
| **ML Competition** | 7 | **0.0%** | **Kaggle级挑战** |

### 6.3 按难度表现

| 难度 | 任务数 | 成功率 |
|------|--------|--------|
| Easy | 1 | 100.0% |
| Medium | 14 | 57.1% |
| Hard | 44 | 6.8% |

**关键洞察**: Hard任务成功率仅6.8%，是当前Agent的主要瓶颈

---

## 7. 训练策略建议

### 7.1 分阶段训练路径

**Phase 1: 基础能力建立** (使用训练集Easy任务)
- 目标: 100% 成功率
- 焦点: Data Insight, Statistical Analysis基础任务
- 验证: 验证集Easy任务

**Phase 2: 中等复杂度优化** (使用训练集Medium任务)
- 目标: 70%+ 成功率
- 焦点: Data Manipulation, ML基础算法
- 验证: 验证集Medium任务

**Phase 3: Hard任务攻坚** (使用训练集Hard任务)
- 目标: 30%+ 成功率（当前Baseline 6.8%）
- 焦点: Data Visualization, ML Competition
- 验证: 验证集Hard任务

**Final: 测试集评估**
- 仅在Stage 2完成后运行
- 不用于调参，仅作最终benchmark

### 7.2 优先改进方向

1. **Data Visualization** (Baseline 0% → 目标 50%+)
   - 训练集: 6个任务（2 Easy, 2 Medium, 2 Hard估计）
   - 验证集: 6个任务
   - 关键: matplotlib/seaborn工具使用、图表类型识别

2. **ML Competition** (Baseline 0% → 目标 20%+)
   - 训练集: 2个任务（稀缺资源）
   - 验证集: 1个任务
   - 关键: 特征工程、模型优化、评估指标

3. **Data Manipulation** (Baseline 10% → 目标 40%+)
   - 训练集: 10个任务
   - 验证集: 10个任务
   - 关键: pandas复杂操作、数据清洗、变换

---

## 8. 使用指南

### 8.1 配置文件路径

```bash
# 训练集 (50个任务)
agent_workspace/da-code/da_code/configs/eval/eval_train.jsonl

# 验证集 (50个任务)
agent_workspace/da-code/da_code/configs/eval/eval_val.jsonl

# 测试集 (59个任务) - 使用现有baseline
agent_workspace/da-code/da_code/configs/eval/eval_baseline.jsonl  # 配置

# 统一数据集配置文件
test/dataset_tasks.json  # 包含所有数据集的任务ID、统计信息和元数据
```

### 8.2 评估脚本使用

```bash
# 运行训练集评估（开发阶段）
python test/evaluate_dacode_official.py --dataset train

# 运行验证集评估（验证改进）
python test/evaluate_dacode_official.py --dataset val

# 运行测试集评估（最终benchmark）
python test/evaluate_dacode_official.py --dataset test
# 或
python test/evaluate_dacode_official.py  # 默认使用test
```

### 8.3 重新生成数据集

如需调整参数重新生成:

```bash
# 编辑参数
vim test/create_train_val_split.py
# 修改 RANDOM_SEED, TRAIN_SIZE, VAL_SIZE, TARGET_DIFFICULTY_DIST

# 重新运行
python test/create_train_val_split.py
```

---

## 9. 数据集质量保证

### 9.1 完整性

- ✓ 所有500个任务均有source数据
- ✓ 所有500个任务均有gold标准答案
- ✓ 所有任务均有完整的config元数据

### 9.2 一致性

- ✓ 训练集/验证集/测试集三者无交集
- ✓ 训练集与验证集难度分布一致（各33%）
- ✓ 类别覆盖全面（7大类别均有覆盖）

### 9.3 可复现性

- ✓ 固定随机种子 (seed=42)
- ✓ 完整记录抽样参数
- ✓ 保存所有任务ID到dataset_tasks.json

---

## 10. 附录

### 10.1 分层统计详情 (441可用任务)

| 任务类别 × 难度 | 可用数量 | 训练集抽样 | 验证集抽样 | 剩余 |
|----------------|---------|----------|----------|------|
| Data Wrangling × Easy | 20 | ~3 | ~3 | 14 |
| Data Wrangling × Medium | 64 | ~5 | ~6 | 53 |
| Data Wrangling × Hard | 16 | ~3 | ~3 | 10 |
| Data Insight × Easy | 11 | ~2 | ~3 | 6 |
| Data Insight × Medium | 59 | ~3 | ~4 | 52 |
| Data Insight × Hard | 5 | ~1 | ~1 | 3 |
| Data Visualization × Easy | 13 | ~2 | ~2 | 9 |
| Data Visualization × Medium | 48 | ~3 | ~3 | 42 |
| Data Visualization × Hard | 7 | ~1 | ~1 | 5 |
| Data Manipulation × Easy | 17 | ~3 | ~3 | 11 |
| Data Manipulation × Medium | 31 | ~4 | ~4 | 23 |
| Data Manipulation × Hard | 15 | ~3 | ~3 | 9 |
| Machine Learning × Easy | 29 | ~5 | ~4 | 20 |
| Machine Learning × Medium | 25 | ~2 | ~3 | 20 |
| Machine Learning × Hard | 7 | ~2 | ~1 | 4 |
| Statistical Analysis × Easy | 10 | ~2 | ~2 | 6 |
| Statistical Analysis × Medium | 45 | ~3 | ~2 | 40 |
| Statistical Analysis × Hard | 6 | ~1 | ~1 | 4 |
| ML Competition × Easy | 3 | ~1 | ~0 | 2 |
| ML Competition × Medium | 6 | ~1 | ~1 | 4 |
| ML Competition × Hard | 4 | ~1 | ~0 | 3 |

### 10.2 参考资料

- DA-Code论文: [https://arxiv.org/abs/xxx](需补充)
- 数据集下载: Google Drive (2.1GB)
- Baseline报告: `docs/baseline_report_20251120.md`
- 评估代码: `test/evaluate_dacode_official.py`

---

**报告生成**: `test/create_train_val_split.py`
**最后更新**: 2025-11-22
**版本**: v1.0
