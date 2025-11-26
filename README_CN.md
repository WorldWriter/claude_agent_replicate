# Agent 架构：Claude 启发的战略-战术模式

> 通过实际实现探索响应式代理架构，将 Claude 的系统提示驱动理念与战略-战术分离相结合，用于复杂任务执行。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 概述

本项目展示了如何构建像 Claude 一样思考的 AI 代理：**响应式、LLM 驱动的决策制定**，而不是硬编码的执行循环。核心创新在于将 Claude 的架构原则与战略-战术分离模式相结合，用于处理复杂的多步骤任务。

### 两大关键架构见解

**1. Claude 的响应式理念**（vs 传统代理）

传统代理遵循固定周期：
```
规划 → 执行 → 反思 → 循环
```

Claude 风格的代理动态响应：
```
消息 → LLM 决策 → 工具（如需要）→ 继续
```

**区别**：系统提示告诉 LLM *如何思考*，而不是*执行什么步骤*。

**2. 战略-战术分离**

对于复杂任务，我们引入双层模式：

- **战略层**：高级规划、用户交互、任务分解（通过系统提示指导）
- **战术层**：专注执行，隔离上下文（通过子代理模式）

这反映了人类处理复杂问题的方式：战略思考 + 战术执行，**而不是将这种分离硬编码**为两个类。

### 三个代理实现

- **MinimalKimiAgent**（阶段 1）：展示核心响应式机制的基础实现
- **PlanKimiAgent**（阶段 2）：**战略-战术架构**，带有动态规划
- **SimpleClaudeAgent**（参考）：Claude 模式的教育性实现

## 架构理念

### 1. 响应式优于预定义

**核心原则**：让 LLM 决定，不要硬编码工作流。

### 2. 工程最佳实践

展示生产级软件工程：

- **安全优先设计**：命令黑名单防止破坏性操作（`rm -rf`、`sudo`、`shutdown`）
- **全面日志记录**：双格式对话日志（人类可读的 `.txt` + 结构化的 `.json`）
- **工作区隔离**：所有代理操作都限制在 `agent_workspace/` 内，防止意外文件损坏
- **DA-Code 基准测试集成**：官方评估框架，包含 7 个类别共 500 个任务
- **数据集方法**：分层训练/验证/测试分割（50/50/59），难度分布均衡
- **超时保护**：60 秒执行限制，防止无限循环
- **错误处理**：优雅降级，提供信息丰富的错误消息

### 3. 问题解决能力

展示对能力的诚实评估，并提供明确的改进策略：

| 指标 | 数值 | 上下文 |
|--------|-------|---------|
| **平均得分** | 29.7% | DA-Code 测试集（59 个复杂任务） |
| **成功率** | 20.3% (12/59) | 完全任务成功 |
| **简单任务** | 100% (1/1) | 简单工作流完全解决 |
| **中等任务** | 57% (8/14) | 4-7 步问题大部分正常工作 |
| **困难任务** | 7% (3/44) | 8+ 步问题，主要改进领域 |

**关键见解**：
- 数据洞察类别：100% 成功（最强领域）
- 可视化任务：0% 成功 → 主要改进机会
- 困难任务表现：7% → 需要更好的规划（阶段 2 重点）

**改进路线图**：
- 阶段 2（计划代理）：通过自适应规划达到 35% 平均得分
- 阶段 3（记忆与学习）：通过提示优化达到 50%+ 平均得分
- 阶段 4（自动进化）：通过自我改进达到 70%+ 平均得分

## 快速开始

### 先决条件

- Python 3.8 或更高版本
- Moonshot Kimi API 密钥 ([在此获取](https://platform.moonshot.cn/))
- （可选）用于 SimpleClaudeAgent 参考实现的 Anthropic API 密钥

### 安装

```bash
# 克隆仓库
git clone <your-repo-url>
cd agent_architecture

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 上使用: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env
# 编辑 .env 并添加您的 MOONSHOT_API_KEY
```

### 首次运行（2 分钟）

```python
from minimal_kimi_agent import MinimalKimiAgent

# 创建代理实例
agent = MinimalKimiAgent()

# 运行简单任务
result = agent.run(
    "什么是云计算？用 3 句话解释。",
    max_turns=5
)

print(result)
```

请参阅 `examples/` 目录获取更多综合性演示，包括数据分析和可视化任务。

## 架构

### 代理执行循环

```
┌─────────────────┐
│   用户输入      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ 发送到 API              │
│ (消息 + 工具定义)       │
└────────┬────────────────┘
         │
         ▼
    ┌────────────┐
    │ API 输出   │
    └────┬───────┘
         │
    ┌────▼──────────────┐
    │ 工具调用？        │
    └────┬──────┬───────┘
    是   │      │ 否
    ┌────▼───┐  │
    │执行工具│  │
    └────┬───┘  │
         │      │
    ┌────▼──────▼──────┐
    │添加到历史记录    │
    └────┬─────────────┘
         │
         └──► 继续或返回响应
```

### 传统 vs Claude 风格代理

| 方面 | 传统代理 | Claude 风格代理（本项目） |
|--------|-------------------|----------------------------------|
| **规划** | 预定义步骤 | 动态每轮 |
| **记忆** | 基于状态 | 消息历史 |
| **决策制定** | 基于规则 | LLM 驱动 |
| **迭代** | 固定周期（规划→执行→反思） | 响应式循环（消息→工具→继续） |
| **适应性** | 低（遵循计划） | 高（根据结果调整） |

请参阅 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 获取详细技术分析。

## 三个代理实现

### MinimalKimiAgent（阶段 1）- 生产就绪

**文件**：[`minimal_kimi_agent.py`](minimal_kimi_agent.py)（423 行）

基础实现，展示了具有生产级安全和日志记录的核心代理机制。

**特性**：
- **多轮对话**：完整的消息历史管理，支持 16+ 轮交互
- **三个工具**：ReadFile（10K 字符限制）、WriteFile、RunCommand（60 秒超时）
- **工作区隔离**：所有操作在 `agent_workspace/` 中，路径自动解析
- **安全机制**：命令黑名单、超时、文件大小限制
- **自动日志记录**：双格式对话日志（`.txt` + `.json`）
- **错误处理**：优雅降级，提供信息丰富的消息

**使用场景**：生产部署、可靠的工具调用、预算敏感场景

**示例**：
```python
agent = MinimalKimiAgent()
result = agent.run("""
读取 CSV 文件 sales_data.csv 并：
1. 按地区计算总销售额
2. 识别表现最佳的产品
3. 将结果写入 summary.txt
""", max_turns=10)
```

**性能**：DA-Code 测试集 29.7% 平均得分 / 20.3% 成功率

---

### PlanKimiAgent（阶段 2）- 高级规划

**文件**：[`plan_kimi_agent.py`](plan_kimi_agent.py)（654 行）

添加了动态规划能力，具有持久化计划管理和自适应执行。

**特性**：
- **计划创建**：在任务开始时生成带有结构化步骤的 `plan.md`
- **自适应执行**：根据中间结果调整计划
- **计划持久化**：人类可读的 markdown 计划，带状态跟踪
- **步骤管理**：动态创建、更新、跳过、完成、记录步骤
- **扩展轮次**：30+ 轮容量，适用于复杂任务
- **所有阶段 1 特性**：安全、日志记录、工作区隔离

**计划工具**：
- `CreatePlan`：初始化结构化计划文件
- `UpdatePlan`：根据执行进度修改计划
- `ReadPlan`：查看当前计划状态

**使用场景**：复杂多步骤任务、需要计划可视化的场景、自适应工作流

**示例计划文件**：
```markdown
# 任务：分析销售数据并创建可视化

## 步骤
- [x] 读取 sales_data.csv
- [~] 计算区域统计数据
- [ ] 创建 matplotlib 可视化
- [ ] 保存到 output/sales_chart.png

## 执行日志
[2025-01-26 10:30] 步骤 1 完成 - 找到 1000 条记录
[2025-01-26 10:32] 步骤 2 进行中 - 计算中...
```

**状态**：开发中，目标在 DA-Code 任务上达到 35% 平均得分

---

### SimpleClaudeAgent - 参考架构

**文件**：[`claude_agent_pseudocode.py`](claude_agent_pseudocode.py)（527 行）

教育性实现，展示 Claude 的架构模式，不用于生产环境。

**架构见解**：
- **响应式循环**：无预规划，每轮动态决策
- **系统提示驱动**：工作流由不断发展的系统提示控制
- **待办短期记忆**：通过系统消息跟踪任务
- **动态上下文构建**：每轮从历史构建上下文
- **工具多样性**：ReadFile、WriteFile、BashCommand、TodoUpdate、SubAgent

**ASCII 架构比较**（来自代码注释）：
```
传统:           Claude 风格:
Plan()                 用户输入
  ↓                        ↓
Execute()              API 调用 + 动态上下文
  ↓                        ↓
Reflect()              响应（文本或工具调用）
  ↓                        ↓
Update Plan            执行工具（如需要）
  ↓                        ↓
Loop                   添加到历史 → 循环
```

**使用场景**：了解 Claude 代理内部结构、架构参考、教育目的

**注意**：为清晰起见有意简化 - 缺少生产安全检查

## 基准测试性能

### DA-Code 测试集（59 个任务）

在需要多步推理、数据操作、可视化和机器学习的复杂数据分析任务上的综合评估。

| 难度 | 数量 | 平均得分 | 成功率 | 状态 |
|------------|-------|-----------|--------------|--------|
| **简单** (1-3 步) | 1 | 100% | 100% (1/1) | ✓ 完成 |
| **中等** (4-7 步) | 14 | 57% | 57% (8/14) | 进行中 |
| **困难** (8+ 步) | 44 | 18% | 7% (3/44) | 进行中 |
| **总体** | **59** | **29.7%** | **20.3% (12/59)** | **基准** |

### 按类别性能

| 类别 | 任务数 | 平均得分 | 成功率 | 关键挑战 |
|----------|-------|-----------|--------------|---------------|
| 数据洞察 | 4 | 100% | 100% (4/4) | ✓ 已解决 |
| 数据操作 | 9 | 11% | 0% (0/9) | 复杂 pandas |
| 数据可视化 | 11 | 0% | 0% (0/11) | **主要差距** |
| 机器学习 | 14 | 21% | 14% (2/14) | 模型选择 |
| 统计分析 | 9 | 44% | 33% (3/9) | 进展良好 |
| 自然语言处理 | 7 | 29% | 14% (1/7) | 文本处理 |
| GCP 特定 | 5 | 40% | 40% (2/5) | 云计费 |

### 关键见解

1. **数据洞察卓越**：100% 成功率 (4/4 任务)
   - 代理在查询制定和洞察提取方面表现出色
   - 展示了对结构化问题的强大推理能力

2. **可视化差距**：0% 成功率 (0/11 任务)
   - 代理在 matplotlib/seaborn 语法方面存在困难
   - 计划在阶段 2 添加可视化工具知识
   - 将创建专门的可视化示例

3. **困难任务挑战**：仅 7% 成功率 (3/44)
   - 多步规划需要改进
   - PlanKimiAgent（阶段 2）专门针对这一点
   - 动态规划应改进任务分解

4. **部分学分系统**：29.7% 平均得分 vs 20.3% 成功率
   - 许多任务部分解决（某些步骤正确）
   - 表明代理理解任务但执行失败
   - 错误恢复是关键改进领域

## 项目结构

```
agent_architecture/
├── minimal_kimi_agent.py          # 阶段 1：生产代理（423 行）
├── plan_kimi_agent.py              # 阶段 2：规划代理（654 行）
├── claude_agent_pseudocode.py      # 参考：Claude 模式（527 行）
│
├── agent_workspace/                # 隔离执行环境
│   ├── da-code/                    # DA-Code 基准测试（500 任务）
│   │   ├── da_code/
│   │   │   ├── source/             # 任务数据文件（2.1GB，单独下载）
│   │   │   ├── gold/               # 标准答案（59 任务）
│   │   │   └── configs/eval/       # 训练/验证/测试分割
│   │   └── da_agent/
│   │       └── evaluators/         # 官方评估指标
│   └── output_dir/                 # 代理执行输出
│
├── test/                           # 评估框架
│   ├── test_dacode.py              # 代理测试工具
│   ├── evaluate_dacode_official.py # 官方 DA-Code 指标
│   ├── dataset_tasks.json          # 测试集配置
│   └── create_train_val_split.py   # 数据集分割生成
│
├── docs/                           # 文档
│   ├── ARCHITECTURE.md             # 技术深度分析
│   ├── dataset_split_report.md     # 数据集分析
│   └── kimi_api.md                 # API 配置说明
│
├── examples/                       # 可运行演示
│   ├── 1_basic_qa.py               # 简单问答示例
│   ├── 2_data_analysis.py          # 多步分析
│   └── 3_visualization.py          # 绘图演示
│
├── logs/                           # 对话日志（gitignored）
├── CLAUDE.md                       # 详细技术参考
├── README.md                       # 本文档
├── requirements.txt                # Python 依赖
├── LICENSE                         # MIT 许可证
└── .env.example                    # 环境模板
```

## 运行评估

该项目包含与官方 DA-Code 基准测试评估框架的集成。

### 数据集分割

| 数据集 | 任务数 | 配置文件 | 用途 |
|---------|-------|-------------|---------|
| **训练集** | 50 | `configs/eval/eval_train.jsonl` | 提示工程、策略开发 |
| **验证集** | 50 | `configs/eval/eval_val.jsonl` | 超参数调优、验证 |
| **测试集** | 59 | `configs/eval/eval_baseline.jsonl` | 最终基准测试（报告指标） |

使用分层抽样创建分割，以平衡难度级别（seed=42 以确保可重现性）。

### 运行测试

```bash
# 快速验证（5 个代表性任务，约 5 分钟）
python test/evaluate_dacode_official.py --dataset quick

# 完整测试集（59 个任务，约 1.5-2 小时）
python test/evaluate_dacode_official.py --dataset test

# 训练集（50 个任务，用于开发）
python test/evaluate_dacode_official.py --dataset train

# 验证集（50 个任务，用于调优）
python test/evaluate_dacode_official.py --dataset val
```

结果保存在 `logs/` 中，包含详细的 JSON 分析和每个任务的细分。

## 常见模式

### 数据分析任务
```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("""
分析 CSV 文件 monthly_sales.csv：
1. 加载并探索数据结构
2. 计算每个地区的汇总统计
3. 按收入识别前 3 名产品
4. 将发现写入 analysis_report.txt
""", max_turns=15)
```

### 可视化任务
```python
agent = MinimalKimiAgent()
result = agent.run("""
从 customer_data.csv 创建可视化：
1. 读取 CSV 文件
2. 创建显示按类别销售额的柱状图
3. 添加适当的标签和标题
4. 保存为 'sales_by_category.png'
使用 matplotlib 或 seaborn。
""", max_turns=15)
```

### 机器学习任务
```python
from plan_kimi_agent import PlanKimiAgent  # 更适合复杂任务

agent = PlanKimiAgent()
result = agent.run("""
构建分类模型：
1. 加载 train.csv 和 test.csv
2. 预处理数据（处理缺失值，编码类别）
3. 训练随机森林分类器
4. 在测试集上评估
5. 将预测保存到 predictions.csv
""", max_turns=30)
```

## 技术栈

**核心**：
- Python 3.8+
- OpenAI Python SDK（用于 Kimi API 兼容性）
- python-dotenv（环境管理）

**代理能力**（在工作区中执行）：
- **数据**：pandas、numpy
- **可视化**：matplotlib、seaborn
- **机器学习**：scikit-learn、xgboost
- **测试**：pytest

**API**：
- Moonshot Kimi（主要，通过 OpenAI 兼容接口）
- Anthropic Claude（仅参考实现）

## 关键设计决策

### 为什么选择 Moonshot Kimi API？

- **OpenAI 兼容性**：使用 OpenAI SDK 即插即用替代，轻松切换模型
- **强大的多轮支持**：可靠处理 16+ 轮对话
- **合理定价**：开发和测试成本效益高
- **中国存在**：项目起源于中国，Kimi 有良好的本地支持

### 为什么采用工作区隔离？

所有代理操作限制在 `agent_workspace/` 内：
- **安全**：防止意外损坏项目文件
- **清晰**：代理代码和执行环境之间的明确边界
- **测试**：运行之间易于清理和重置
- **路径解析**：相对路径自动解析到工作区

### 为什么选择 DA-Code 基准测试？

- **真实任务**：实际数据分析问题，非玩具示例
- **全面性**：跨 7 个类别 500 个任务，难度各异
- **官方指标**：标准化评估，公平比较
- **挑战性**：29.7% 平均得分显示有很大改进空间
- **教育性**：通过诚实评估学习什么有效，什么无效

## 常见问题

**问：我可以用 Claude 代替 Kimi 吗？**

答：当然可以！`SimpleClaudeAgent` 展示了这种模式。要创建生产版本的 Claude 版本：
1. 用 Anthropic 的 `Anthropic` 客户端替换 `OpenAI` 客户端
2. 调整消息格式（Claude 使用略有不同的格式）
3. 保持相同的工具定义和执行逻辑

**问：如何提高代理的性能？**

答：迭代开发方法：
1. 从训练集开始（50 个任务），识别失败模式
2. 优化系统提示和工具使用
3. 在验证集上测试（50 个任务）以避免过拟合
4. 在测试集上进行最终基准测试（59 个任务）

**问：为什么可视化准确率为 0%？**

答：当前代理在 matplotlib 语法和绘图配置方面存在困难。计划改进：
- 向系统提示添加可视化示例
- 为常见绘图类型创建专门工具
- 改进调试绘图代码的错误消息

**问：我可以添加自定义工具吗？**

答：当然可以！请参阅代理文件中的 `_get_tools()` 方法：
1. 定义工具模式（名称、描述、参数）
2. 添加处理方法（例如，`_execute_new_tool()`）
3. 在工具调度程序中注册

**问：阶段 1 和阶段 2 有什么区别？**

答：
- **阶段 1（最小）**：反应式执行，无显式规划，更轻量
- **阶段 2（计划）**：主动规划，plan.md 持久化，自适应执行

简单任务或速度重要时选择阶段 1。复杂多步问题时使用阶段 2。

## 开发路线图

- [x] **阶段 1：最小代理**（完成）
  - 核心工具调用机制
  - 多轮对话支持
  - 生产级安全和日志记录
  - DA-Code 基准：29.7% 平均得分 / 20.3% 成功率

- [ ] **阶段 2：计划代理**（进行中）
  - 具有 plan.md 持久化的动态规划
  - 基于结果的自适应执行
  - 目标：DA-Code 任务平均得分 35%+
  - 改进的可视化能力

- [ ] **阶段 3：记忆与学习**（计划中）
  - 从成功任务模式中学习
  - 基于历史的提示优化
  - 工具使用模式识别
  - 目标：50%+ 平均得分

- [ ] **阶段 4：自动进化**（计划中）
  - 自我评估和错误分析
  - 多轮提示优化
  - 自动工具知识扩展
  - 目标：70%+ DA-Code 基准测试

## 参考文献

- **DA-Code 基准测试**：[arXiv:2410.07331](https://arxiv.org/abs/2410.07331) - "DA-Code: Agent Data Science Code Generation Benchmark"
- **Claude 文档**：[Anthropic Docs](https://docs.anthropic.com) - 代理模式和工具使用
- **Moonshot AI**：[平台](https://platform.moonshot.cn/) - Kimi API 文档

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 致谢

- DA-Code 基准测试团队提供的全面评估框架
- Anthropic 提供的 Claude 代理架构见解
- Moonshot AI 提供的 Kimi API 访问

---

**构建重点**：干净的架构、诚实的指标、持续改进

**最后更新**：2025-11-26