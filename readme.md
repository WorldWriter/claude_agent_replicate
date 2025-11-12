# Agent Architecture

一个渐进式的 AI Agent 实现项目，通过多个阶段逐步构建功能完善的智能代理。

## 实现路线

### Stage 1: Minimal Agent ✅ (当前)
**文件**: `minimal_kimi_agent.py`

一个精简但功能完整的 Agent，支持：
- **多轮对话**：完整的对话历史管理，支持 16+ 轮交互
- **工具调用**：ReadFile, WriteFile, RunCommand
- **工作目录隔离**：默认在 `agent_workspace/` 工作，不影响上层代码
- **日志记录**：自动保存对话日志（txt + json 格式）

能够自主完成多步骤复杂任务，如数据分析、代码生成与执行、文件操作等。

### Stage 2: Plan Agent (下一步)
能够进行任务规划，并根据历史和状态自动更新 Plan（对齐 Claude Agent），处理更复杂的任务。

### Stage 3: Memory & Learning
添加记忆功能，利用历史执行经验优化新任务（类似强化学习，但通过 Prompt 优化而非参数更新）。
