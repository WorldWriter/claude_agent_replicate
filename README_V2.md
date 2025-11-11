# Agent架构 V2 - 严格遵循伪代码实现

## 核心改进

完全重写，严格实现以下伪代码架构：

```python
while not task.done:
    plan = agent.plan(context)      # 生成多步计划
    for step in plan.steps:
        if step.requires_subagent:
            subagent = agent.spawn_subagent(step.config)
            result = subagent.run(step.input)
        elif step.requires_tool:
            result = agent.use_tool(step.tool, step.input)
        else:
            result = agent.think(step.input)
        agent.reflect(result)       # 双层反思
```

## 代码统计

```
llm_client.py: 47行   - LLM接口封装
tools.py:      79行   - 工具函数集
agent.py:      301行  - Agent核心逻辑
main.py:       32行   - 程序入口
---
总计:          459行
```

## 核心特性

### 1. 完整计划生成
- ✅ LLM一次生成3-8步完整计划
- ✅ 自适应规划：根据任务复杂度决定步数
- ✅ 支持三种步骤类型：tool/think/subagent

### 2. 双层反思机制

**微观反思**（每步后）：
- 评估步骤是否成功
- 检查输出是否符合预期
- 判断是否有错误
- 决定是否可以继续

**宏观反思**（阶段后）：
- 对比原始任务要求
- 检查是否偏离核心需求
- 评估质量是否达标
- 建议下一步方向

### 3. SubAgent机制
- 处理复杂子任务
- 独立的context和执行循环
- 继承父Agent的工具能力
- 迭代次数可配置（默认3轮）

### 4. 完整日志

```
[PLAN] LLM生成的完整计划
[STEP N/M] 当前执行第几步
[EXECUTE TOOL/THINK/SUBAGENT] 执行细节
[RESULT] 执行结果
[MICRO-REFLECT] 微观反思评估
[MACRO-REFLECT] 宏观反思评估
[COMPLETE] 任务完成确认
```

## 使用方法

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API密钥（.env文件）
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here

# 3. 运行Agent
python main.py
```

## 架构设计

### Plan类
```python
@dataclass
class Plan:
    steps: List[Step]
    summary: str
```

### Step类
```python
@dataclass
class Step:
    type: str  # "tool", "think", "subagent"
    reasoning: str
    tool: Optional[str]
    args: Optional[Dict]
    subagent_task: Optional[str]
    thought: Optional[str]
```

### SimpleAgent类
- `plan()`: 生成多步执行计划
- `execute_step()`: 根据类型分发执行
- `use_tool()`: 调用工具
- `think()`: LLM推理
- `spawn_subagent()`: 创建子Agent
- `reflect()`: 双层反思
- `run()`: 主循环

## 与V1对比

| 特性 | V1（237行） | V2（459行） |
|-----|-----------|-----------|
| Plan生成 | ❌ 单步 | ✅ 多步完整计划 |
| Reflect机制 | ❌ 简单判断 | ✅ 双层反思+对比原始任务 |
| SubAgent | ❌ 无 | ✅ 完整支持 |
| 步骤类型 | 仅Tool | Tool/Think/SubAgent |
| 日志详细度 | 基础 | 完整分层 |
| 架构符合度 | 30% | 100% |

## 测试任务

默认分析GCP成本数据：
1. 读取数据基本信息
2. 成本异常检测
3. 多维度归因分析
4. 生成可视化图表

Agent将自主规划步骤，调用工具，并通过双层反思确保满足需求。
