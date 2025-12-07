# Claude Agent 复刻

> 使用 Kimi API 渐进式复刻 Claude Code 的 Agent 架构，展示从最小基础到高级能力的系统提示词驱动响应式 Agent。

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 项目愿景

**目标**: 忠实复刻 Claude Code 的 Agent 架构模式，同时保持与 Kimi (月之暗面) API 的兼容性。

**方法**: 分阶段演进，模仿 Claude 的核心机制：
- **Stage 1**: 响应式基础（最小 Agent 与工具调用）
- **Stage 2**: 系统提示词 + 动态上下文 + Todo 追踪
- **Stage 3**: Human-in-the-Loop 交互（计划中）
- **Stage 4**: 自我演进与学习（未来）

**理念**: 通过动手实现掌握 Claude Agent 架构精髓，而非仅仅阅读文档。

---

## Claude 核心架构原则

### 1. 响应式架构
- **无预定义执行循环**（Plan→Execute→Reflect）
- **LLM 动态决定下一步行动**
- **系统提示词教"如何思考"**，而非"做什么"

**传统 Agent**：
```python
while not done:
    plan = agent.plan()      # 预生成完整计划
    for step in plan:
        execute(step)        # 执行预定义步骤
    reflect()                # 单独的反思阶段
```

**Claude 风格 Agent**（本项目）：
```python
for message in conversation:
    context = build_dynamic()     # 每回合重建上下文
    response = llm(
        system=workflow_prompt,   # "规划"发生在这里！
        messages=context
    )
    if tool_use:
        execute_and_continue()
```

### 2. 系统提示词驱动行为
- 通过全面系统提示词（~400 tokens）提供工作流指导
- 每次 API 调用时动态构建上下文
- 环境感知（时间、工作区、回合数）

### 3. Todo 短期记忆
- 通过系统消息进行任务追踪
- 进度可见性：[ ] pending, [→] in_progress, [✓] completed
- 无需外部状态文件的自我管理

---

## 实现阶段

### Stage 1: 最小 Kimi Agent（响应式基础）

**文件**: [`minimal_kimi_agent.py`](minimal_kimi_agent.py)（423 行）
**状态**: ✅ 生产就绪

**核心特性**：
- 多轮对话管理
- 工具调用：ReadFile、WriteFile、RunCommand
- 工作区隔离和安全机制
- 对话日志记录（TXT + JSON）

**架构**：
```
用户输入 → API 调用 → 工具执行 → 循环
```

**性能**：DA-Code 测试集 29.7% 平均得分，20.3% 成功率

**适用场景**：简单到中等任务，可靠执行，预算敏感

**示例**：
```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("""
读取 sales_data.csv 并：
1. 计算各地区销售总额
2. 识别表现最佳的产品
3. 将结果写入 summary.txt
""", max_turns=10)
```

---

### Stage 2: 动态规划 Agent（系统提示词 + 上下文）

**文件**: [`dynamic_plan_agent.py`](dynamic_plan_agent.py)（620 行）
**状态**: ✅ 完成（2025-11-27）

**关键创新**（Claude 架构模式）：

**1. 系统工作流提示词**（~400 tokens）
- 核心工作原则（主动工具使用，迭代执行）
- Todo 管理规则（何时创建，状态转换）
- 思维模型（目标 → 所需信息 → 行动 → 完整性检查）
- 工具使用指南

**2. 动态上下文构建**
每次 API 调用时重建上下文：
```
[系统工作流提示词]     ← 持久指导
[环境信息]             ← 时间、工作区、回合
[对话历史]             ← 用户 + 助手消息
[Todo 状态]            ← 当前任务进度
```

**3. TodoUpdate 工具**
- 操作：`add`、`update_status`、`complete`
- 可视追踪：[ ] → [→] → [✓]
- 自动任务管理

**4. 增强日志记录**
- JSON 日志包含 todos 和回合计数
- 规划和执行的完整审计跟踪

**架构**：
```
用户输入
    ↓
构建动态上下文（系统提示词 + 环境 + 历史 + todos）
    ↓
API 调用
    ↓
工具执行（包括 TodoUpdate）
    ↓
循环
```

**性能影响**：每次调用 +550 tokens，但完成率更高

**适用场景**：需要规划和追踪的复杂多步骤任务

**示例**：
```python
from dynamic_plan_agent import MinimalKimiAgent

agent = MinimalKimiAgent()  # 同名类，增强行为！
result = agent.run("""
分析 customer_data.csv：
1. 按细分市场计算客户终身价值
2. 识别前 10 名客户
3. 创建显示趋势的可视化
4. 编写执行摘要
""", max_turns=20)

# Agent 将自动：
# - 为 4 个任务创建 Todo 列表
# - 追踪进度：[→] task_1, [ ] task_2, [ ] task_3, [ ] task_4
# - 随着每个完成更新状态
# - 在日志中保存完整的 todo 历史
```

**对比**：
| 方面 | Stage 1 | Stage 2 |
|------|---------|---------|
| 代码大小 | 423 行 | 620 行 |
| 工具 | 3 个 | 4 个 (+TodoUpdate) |
| 系统提示词 | 无 | ~400 tokens |
| 上下文 | 静态 | 动态 |
| 任务记忆 | 无 | Todo 追踪 |
| 适用于 | 简单任务 | 复杂多步骤任务 |

---

### Stage 3: Human-in-Loop Agent（计划中）

**文件**: `human_loop_agent.py`（未来）
**状态**: 🔄 计划中（2026 年 Q1）

**计划功能**：

**1. 关键决策确认**
- Agent 在破坏性操作前请求批准
- 用户可以审查和修改执行计划

**2. 交互式调试**
- 发生错误时，Agent 解释问题并寻求指导
- 用户可以提供提示或替代方法

**3. 工具**：
- `AskUserConfirmation(operation, context)` → yes/no/modify
- `RequestUserGuidance(problem, options)` → 用户选择
- `ShowIntermediateResult(result, next_step)` → continue/adjust

**示例流程**：
```python
# Agent: 即将删除 500 个文件
AskUserConfirmation(operation="delete_files", context={...})
# 用户批准 → Agent 继续

# Agent: 脚本失败，ModuleNotFoundError
RequestUserGuidance(problem="缺少 pandas", options=[...])
# 用户："安装 pandas" → Agent 运行 pip install
```

---

### 参考实现

**文件**: [`claude_agent_pseudocode.py`](claude_agent_pseudocode.py)（527 行）
**目的**: 展示 Claude 内部模式的教育参考

**关键见解**：
- 响应式循环（无预规划）
- 系统提示词驱动的工作流
- Todo 短期记忆
- 动态上下文构建
- SubAgent 模式用于上下文隔离

**不适用于生产** - 为学习目的有意简化。

---

## 项目结构

```
claude_agent_replicate/
├── minimal_kimi_agent.py          # Stage 1：响应式基础
├── dynamic_plan_agent.py          # Stage 2：系统提示词 + 动态上下文 + Todo
├── human_loop_agent.py            # Stage 3：Human-in-the-Loop（未来）
├── claude_agent_pseudocode.py     # 参考：Claude 架构模式
│
├── test_dynamic_plan_agent.py     # Stage 2 测试
│
├── agent_workspace/               # 隔离的执行环境
│   ├── da-code/                   # DA-Code 基准测试（500 个任务）
│   │   ├── da_code/
│   │   │   ├── source/            # 任务数据文件
│   │   │   ├── gold/              # 标准答案
│   │   │   └── configs/eval/      # 训练/验证/测试拆分
│   │   └── da_agent/
│   │       └── evaluators/        # 官方评估指标
│   └── output_dir/                # Agent 执行输出
│
├── docs/
│   ├── AGENT_EVOLUTION.md         # Stage 1→2→3 演进指南
│   ├── ARCHITECTURE_COMPARISON.md # 前后技术对比
│   ├── ARCHITECTURE.md            # 技术深度解析
│   ├── baseline_report.md         # DA-Code 评估结果
│   └── kimi_api.md                # API 配置说明
│
├── test/                          # DA-Code 评估框架
│   ├── evaluate_results.py
│   ├── run_benchmark.py
│   └── dataset_tasks.json
│
├── examples/                      # 使用演示
├── logs/                          # 对话日志（gitignored）
│
├── README.md                      # 本文件
├── README_CN.md                   # 中文版
├── CLAUDE.md                      # 技术参考
├── requirements.txt               # 依赖
└── .env.example                   # 环境模板
```

---

## Claude Code 与本项目的关键差异

| 特性 | Claude Code | 本项目 |
|------|-------------|--------|
| **API** | Anthropic Claude API | Moonshot Kimi API（OpenAI 兼容） |
| **系统提示词** | 单独的 `system` 参数 | 注入到消息数组中 |
| **消息格式** | Anthropic 格式 | OpenAI 格式 |
| **工具** | 原生 Claude 工具 | OpenAI function calling |
| **语言** | TypeScript/Python | 仅 Python |
| **范围** | 完整 IDE 集成 | 独立 Agent 框架 |

**为什么这很重要**：理解如何将 Claude 架构适配到不同 API 可以教会我们核心原则，而不仅仅是实现细节。

---

## 快速开始

### 先决条件

- Python 3.8 或更高版本
- 月之暗面 Kimi API 密钥（[在此获取](https://platform.moonshot.cn/)）
- （可选）用于 SimpleClaudeAgent 参考实现的 Anthropic API 密钥

### 安装

```bash
# 克隆仓库
git clone <your-repo-url>
cd claude_agent_replicate

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # Windows 上：venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境
cp .env.example .env
# 编辑 .env 并添加您的 MOONSHOT_API_KEY
```

### 首次运行（2 分钟）

```python
from minimal_kimi_agent import MinimalKimiAgent

# 创建 Agent 实例
agent = MinimalKimiAgent()

# 运行简单任务
result = agent.run(
    "什么是云计算？用 3 句话解释。",
    max_turns=5
)

print(result)
```

请参阅 [`docs/AGENT_EVOLUTION.md`](docs/AGENT_EVOLUTION.md) 获取更全面的使用示例。

---

## 基准测试：DA-Code 评估

我们使用 DA-Code（500 个数据分析任务）进行客观评估。使用 MinimalKimiAgent 的当前基准：

**测试集结果**（59 个复杂任务）：29.7% 平均得分，20.3% 成功率（12/59 完成）

**表现良好的方面**：
- 数据洞察提取（查询制定、结构化数据推理）
- 简单统计分析
- 文件 I/O 和基本数据操作

**需要改进的方面**：
- 可视化（matplotlib/seaborn 语法、图表配置）
- 复杂任务的多步规划（8+ 步）
- 初始方法失败时的错误恢复

**学习方法**：项目强调诚实指标而非夸大宣传。基准分数为 Stages 2-4 的架构改进建立了起点。

详细分析可在 `docs/baseline_report.md` 中找到。

## 项目结构

```
claude_agent_replicate/
├── minimal_kimi_agent.py          # Stage 1：响应式基础（423 行）
├── dynamic_plan_agent.py          # Stage 2：系统提示词 + 动态上下文 + Todo（620 行）
├── human_loop_agent.py            # Stage 3：Human-in-the-Loop（未来）
├── claude_agent_pseudocode.py     # 参考：Claude 架构模式（527 行）
├── test_dynamic_plan_agent.py     # Stage 2 测试
│
├── agent_workspace/                # 隔离的执行环境
│   ├── da-code/                    # DA-Code 基准测试（500 个任务）
│   │   ├── da_code/
│   │   │   ├── source/             # 任务数据文件（2.1GB，单独下载）
│   │   │   ├── gold/               # 标准答案（59 个任务）
│   │   │   └── configs/eval/       # 训练/验证/测试拆分
│   │   └── da_agent/
│   │       └── evaluators/         # 官方评估指标
│   └── output_dir/                 # Agent 执行输出
│
├── test/                           # 评估框架
│   ├── run_benchmark.py              # Agent 测试框架
│   ├── evaluate_results.py # 官方 DA-Code 指标
│   ├── dataset_tasks.json          # 测试集配置
│   └── setup_datasets.py   # 数据集拆分生成
│
├── docs/                           # 文档
│   ├── ARCHITECTURE.md             # 技术深度解析
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
├── README.md                       # 此文件
├── requirements.txt                # Python 依赖
├── LICENSE                         # MIT 许可证
└── .env.example                    # 环境模板
```

## 运行评估

项目包含与官方 DA-Code 基准测试评估框架的集成。

### 数据集拆分

| 数据集 | 任务数 | 配置文件 | 目的 |
|--------|--------|----------|------|
| **训练集** | 50 | `configs/eval/eval_train.jsonl` | 提示词工程、策略开发 |
| **验证集** | 50 | `configs/eval/eval_val.jsonl` | 超参数调优、验证 |
| **测试集** | 59 | `configs/eval/eval_baseline.jsonl` | 最终基准（报告指标） |

使用分层抽样创建拆分，以平衡难度级别（seed=42 确保可重复性）。

### 运行测试

```bash
# 快速验证（5 个代表性任务，约 5 分钟）
python test/evaluate_results.py --dataset quick

# 完整测试集（59 个任务，约 1.5-2 小时）
python test/evaluate_results.py --dataset test

# 训练集（50 个任务，用于开发）
python test/evaluate_results.py --dataset train

# 验证集（50 个任务，用于调优）
python test/evaluate_results.py --dataset val
```

结果保存在 `logs/` 中，包含详细的 JSON 分析和每个任务的细目分类。

## 使用示例

详细示例请参阅 [`docs/AGENT_EVOLUTION.md`](docs/AGENT_EVOLUTION.md)。

### Stage 1: 简单任务
```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("分析 sales.csv 并计算各地区总销售额", max_turns=10)
```

### Stage 2: 复杂多步骤任务
```python
from dynamic_plan_agent import MinimalKimiAgent  # 增强版！

agent = MinimalKimiAgent()
result = agent.run("""
构建完整的数据分析流程：
1. 加载并清理 customer_data.csv
2. 执行探索性数据分析
3. 创建 3 个可视化展示关键趋势
4. 编写包含建议的执行摘要
""", max_turns=25)

# Agent 将自动创建和追踪 todo 列表
```

## 技术栈

**核心**：
- Python 3.8+
- OpenAI Python SDK（用于 Kimi API 兼容性）
- python-dotenv（环境管理）

**Agent 能力**（在工作区中执行）：
- **数据**：pandas、numpy
- **可视化**：matplotlib、seaborn
- **机器学习**：scikit-learn、xgboost
- **测试**：pytest

**API**：
- 月之暗面 Kimi（主要，通过 OpenAI 兼容接口）
- Anthropic Claude（仅参考实现）

## 关键设计决策

### 为何选择系统提示词而非硬编码工作流？

**代码定义能力**（工具、记忆、上下文）
**系统提示词定义行为**（决策逻辑、规划策略、执行模式）

这种分离使得：
- 无需更改代码即可调整 Agent 行为
- 通过提示词工程实现快速迭代
- 同一代码库支持简单和复杂任务

### 为何采用动态上下文构建？

传统方法：简单地将新消息追加到历史中
Claude 方法：每次 API 调用时重建完整上下文

**优势**：
- 注入实时环境信息（时间、工作区状态）
- 更新系统提示词以反映当前阶段
- 添加进度追踪（todo 状态）
- 保持 Agent 对其情境的感知

**成本**：每次调用 +550 tokens，但任务完成率更高

### 为何采用工作区隔离？

所有 Agent 操作限制在 `agent_workspace/`：
- **安全**：防止意外损坏项目文件
- **清晰**：Agent 代码和执行环境之间的明确边界
- **测试**：运行之间易于清理和重置
- **路径解析**：相对路径自动解析到工作区

## FAQ

**问：我可以用 Claude 替代 Kimi 吗？**

答：可以！`SimpleClaudeAgent` 展示了模式。要创建生产级 Claude 版本：
1. 用 Anthropic 的 `Anthropic` 客户端替换 `OpenAI` 客户端
2. 调整消息格式（Claude 使用略有不同的格式）
3. 保持相同的工具定义和执行逻辑

**问：如何提高 Agent 的性能？**

答：迭代开发方法：
1. 从训练集（50 个任务）开始，识别失败模式
2. 优化系统提示词和工具使用
3. 在验证集（50 个任务）上测试以避免过拟合
4. 在测试集（59 个任务）上进行最终基准测试

**问：为什么可视化准确率是 0%？**

答：当前 Agent 在 matplotlib 语法和图表配置方面存在困难。计划改进：
- 向系统提示词添加可视化示例
- 为常见图表类型创建专用工具
- 改进调试图表代码的错误消息

**问：我可以添加自定义工具吗？**

答：当然！请参阅 Agent 文件中的 `_get_tools()` 方法：
1. 定义工具架构（名称、描述、参数）
2. 添加处理方法（例如，`_execute_new_tool()`）
3. 在工具调度器中注册

**问：MinimalKimiAgent 和 Dynamic Plan Agent 有什么区别？**

答：
- **Stage 1 (Minimal)**：响应式 Agent，无规划指导，无任务记忆。适合简单任务。
- **Stage 2 (Dynamic Plan)**：添加系统提示词（教"如何思考"）、动态上下文（环境感知）、Todo 追踪（任务记忆）。适合复杂多步骤任务。

两者使用相同的类名（`MinimalKimiAgent`），便于迁移。

**问：如何选择使用哪个 Stage？**

答：
- **1-2 步骤**：Stage 1（最小）
- **3-7 步骤**：Stage 2（动态规划）
- **8+ 步骤或需要人工监督**：Stage 3（未来，human-in-loop）

**问：为什么从这个项目中移除战略-战术模式？**

答：项目重点转向纯 Claude 架构复刻。战略-战术是一个偏离 Claude 方法的实验性模式。对于 Claude 风格的 Agent，系统提示词驱动的响应式架构才是核心模式。

## 开发路线图

项目遵循阶段性方法来理解和复刻 Claude Agent 架构：

- [x] **Stage 1：响应式基础**（已完成，2025-11-20）
  - 实现 Claude 的响应式循环架构
  - 工具调用与多轮对话
  - 生产安全机制（工作区隔离、命令黑名单）
  - DA-Code 基准测试的基线评估（29.7% 平均得分）

- [x] **Stage 2：动态规划 Agent**（已完成，2025-11-27）
  - 系统工作流提示词（~400 tokens）
  - 动态上下文构建（每回合重建）
  - TodoUpdate 工具（任务追踪和进度可见性）
  - 增强日志记录（todos + 回合计数）
  - 同名类便于迁移

- [ ] **Stage 3：Human-in-the-Loop**（计划中，2026 年 Q1）
  - 关键决策确认（破坏性操作前请求批准）
  - 交互式调试（错误时寻求指导）
  - 中间结果展示（用户可以调整方向）
  - 工具：AskUserConfirmation、RequestUserGuidance、ShowIntermediateResult

- [ ] **Stage 4：记忆与学习**（未来）
  - 从成功模式中学习
  - 自动系统提示词优化
  - 工具使用模式识别
  - 跨任务知识转移

## 参考文献

- **DA-Code 基准测试**：[arXiv:2410.07331](https://arxiv.org/abs/2410.07331) - "DA-Code: Agent Data Science Code Generation Benchmark"
- **Claude 文档**：[Anthropic Docs](https://docs.anthropic.com) - Agent 模式和工具使用
- **月之暗面 AI**：[平台](https://platform.moonshot.cn/) - Kimi API 文档

## 许可证

MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

## 致谢

- DA-Code 基准测试团队提供的综合评估框架
- Anthropic 提供的 Claude Agent 架构见解
- 月之暗面 AI 提供的 Kimi API 访问

---

**构建重点**：清洁架构、诚实指标、持续改进

**最后更新**：2025-11-27