# Claude Code 源码研究计划

## Context
基于 Claude Code 泄露源码（~1,900 文件，512K+ 行 TypeScript），系统性研究 Claude Agent 的核心能力和架构设计，形成对 agentic AI 系统的深入理解。

---

## 研究角度总览

### 角度 1: 上下文工程 (Context Engineering)
**核心问题**: 如何在有限 context window 中塞入最有效的信息？

**关键文件**:
- `src/constants/prompts.ts` — `getSystemPrompt()` 系统提示词构建
- `src/constants/systemPromptSections.ts` — 缓存/非缓存 section 分层
- `src/context.ts` — `getSystemContext()` / `getUserContext()` 上下文收集
- `src/utils/queryContext.ts` — `fetchSystemPromptParts()` 组装
- `src/utils/attachments.ts` — 附件和 memory 注入

**重点研究**:
- System Prompt 分层架构：静态缓存前缀 → 动态缓存段 → 每轮变化段
- Prompt Cache 优化：`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 如何分隔缓存边界
- 上下文优先级：override > coordinator > agent > custom > default 的组合逻辑
- CLAUDE.md 机制：项目级/用户级配置如何注入上下文

---

### 角度 2: Agent Loop 实现机制
**核心问题**: Agent 如何实现"思考-行动-观察"循环？

**关键文件**:
- `src/query.ts` — `queryLoop()` 主循环，`while(true)` 无限循环结构
- `src/QueryEngine.ts` — `submitMessage()` 入口，async generator 流式架构
- `src/services/tools/toolOrchestration.ts` — `runTools()` 工具分批执行
- `src/services/tools/StreamingToolExecutor.ts` — 并发工具执行管理

**重点研究**:
- 循环控制：state 对象如何跨迭代维护（messages, turnCount, toolUseContext）
- 工具调度：并发安全工具并行执行 vs 状态修改工具串行执行
- 流式架构：async generator (`yield*`) 实现增量 UI 更新
- 停止条件：何时跳出循环（无 tool_use、达到 maxTurns、abort 信号）

---

### 角度 3: Agent Memory 系统
**核心问题**: Agent 如何跨会话记忆和学习？

**关键文件**:
- `src/memdir/memdir.ts` — `loadMemoryPrompt()` 记忆加载到系统提示
- `src/memdir/memoryTypes.ts` — 四种记忆类型分类（user/feedback/project/reference）
- `src/memdir/findRelevantMemories.ts` — 用 Sonnet 做记忆相关性选择
- `src/services/extractMemories/extractMemories.ts` — 自动记忆提取
- `src/services/extractMemories/prompts.ts` — 提取提示词

**重点研究**:
- 记忆生命周期：写入（手动+自动） → 索引（MEMORY.md） → 检索（相关性筛选） → 加载（系统提示注入）
- 自动提取：query loop 结束后 forked agent 自动分析对话提取记忆
- 相关性筛选：用 Sonnet 侧查询从记忆库中选出最多 5 条相关记忆
- 截断策略：MEMORY.md 200 行 / 25KB 上限

---

### 角度 4: 上下文压缩 (Context Compaction)
**核心问题**: 当对话超长时，如何智能压缩而不丢失关键信息？

**关键文件**:
- `src/services/compact/compact.ts` — 主压缩逻辑
- `src/services/compact/microCompact.ts` — 轻量压缩
- `src/services/compact/sessionMemoryCompact.ts` — 会话内记忆压缩
- `src/services/compact/autoCompact.ts` — 自动压缩阈值

**重点研究**:
- 压缩策略：`<analysis>` + `<summary>` 两阶段语义压缩
- 自动触发：context window - output tokens - buffer tokens 的阈值计算
- 断路器：连续 3 次压缩失败后停止
- 微压缩：token 估算的轻量替代方案

---

### 角度 5: 工具系统与权限模型
**核心问题**: 如何安全地让 LLM 调用外部工具？

**关键文件**:
- `src/Tool.ts` — 工具基础接口，`buildTool()` 工厂模式
- `src/tools.ts` — `getAllBaseTools()` 工具注册表
- `src/hooks/toolPermission/PermissionContext.ts` — 权限决策流
- `src/utils/permissions/` — 24 个文件的权限子系统
- `src/tools/BashTool/bashPermissions.ts` — Bash 命令安全分类器

**重点研究**:
- 权限决策流：tool request → hasPermissionsToUseTool() → allow/deny/ask
- 权限模式：default / auto / plan / bypassPermissions 等
- Bash 分类器：用 API 分析命令危险性（两阶段：快速 + 深度思考）
- 并发安全：`isConcurrencySafe` 属性决定工具是否可并行
- Race 安全：`createResolveOnce()` 防止 classifier/hook/用户交互的竞态

---

### 角度 6: 多 Agent 协作（Sub-agent & Coordinator）
**核心问题**: 多个 Agent 如何分工协作？

**关键文件**:
- `src/tools/AgentTool/AgentTool.tsx` — Agent 生成工具
- `src/tools/AgentTool/runAgent.ts` — `runAgent()` 子 agent 运行
- `src/tools/AgentTool/agentToolUtils.ts` — 工具过滤与验证
- `src/coordinator/coordinatorMode.ts` — 协调者模式

**重点研究**:
- 递归架构：子 agent 复用同一个 `query()` 函数，通过上下文隔离而非独立实现
- 上下文隔离：`createSubagentContext()` 克隆父上下文，独立消息链（sidechain.jsonl）
- 工具过滤：`ASYNC_AGENT_ALLOWED_TOOLS` / `CUSTOM_AGENT_DISALLOWED_TOOLS`
- Coordinator 模式：主 agent 变身编排者，worker agent 自主执行，通过 `<task-notification>` 通信

---

### 角度 7: Hook 系统与可扩展性
**核心问题**: 如何让用户自定义 Agent 行为而不修改核心代码？

**关键文件**:
- `src/types/hooks.ts` — 15 种 Hook 事件定义
- `src/skills/loadSkillsDir.ts` — Skill 加载管线
- `src/plugins/builtinPlugins.ts` — 插件注册
- `src/services/mcp/` — MCP 服务器集成

**重点研究**:
- Hook 事件：PreToolUse / PostToolUse / PermissionRequest / FileChanged 等
- Skill 系统：Markdown frontmatter 定义 → 多源加载（project → user → managed → bundled）
- 插件架构：Skills + Hooks + MCP Servers 三合一扩展点
- MCP 抽象：外部 MCP 服务器透明包装为内部 Tool

---

### 角度 8: IDE 集成与远程执行（Bridge）
**核心问题**: CLI 工具如何与 IDE、远程环境双向通信？

**关键文件**:
- `src/bridge/bridgeApi.ts` — Bridge API 客户端抽象
- `src/bridge/remoteBridgeCore.ts` — 远程 Bridge 核心（退避策略、多会话）
- `src/bridge/replBridge.ts` — REPL 交互桥接
- `src/bridge/jwtUtils.ts` — JWT 认证

**重点研究**:
- 会话模型：Spawn → Poll → Shutdown 生命周期
- 消息协议：用户输入 → 查询 → 工具输出 → 完成
- 并发：容量池化支持并行查询（默认 32 并发）
- Worktree 隔离：`createAgentWorktree()` 为远程 agent 创建独立工作树

---

### 角度 9: 性能优化策略
**核心问题**: 大型 Agent 系统如何做到快速响应？

**关键文件**:
- `src/main.tsx` — 并行预取（MDM、Keychain、API 预连接）
- `src/constants/systemPromptSections.ts` — Prompt 缓存分层
- `src/services/tokenEstimation.ts` — Token 估算
- `src/cost-tracker.ts` — 成本追踪

**重点研究**:
- 启动优化：`startMdmRawRead()` / `startKeychainPrefetch()` 并行预取
- 懒加载：OpenTelemetry、gRPC、analytics 等重模块动态 `import()`
- Prompt Cache：系统提示分层确保缓存命中率
- 死代码消除：`bun:bundle` feature flags 编译时剥离未启用功能
- Token 预算：记忆相关性预取与工具执行重叠

---

## 建议研究顺序

```
1. Agent Loop（角度1）        ← 理解核心循环，后续所有角度的基础
2. 上下文工程（角度2）        ← 理解信息如何流入 Agent
3. 工具系统与权限（角度5）    ← 理解 Agent 如何安全地行动
4. 上下文压缩（角度4）        ← 理解长对话管理
5. Agent Memory（角度3）      ← 理解跨会话学习
6. 多 Agent 协作（角度6）     ← 理解 Agent 编排
7. Hook 与可扩展性（角度7）   ← 理解扩展机制
8. 性能优化（角度9）          ← 理解工程实践
9. IDE 集成（角度8）          ← 理解产品形态
```
