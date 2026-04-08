# Claude Agent Replicate

**全网最深度的 Claude Code 源码逆向分析 + Python 复现项目。**

2026 年 3 月，Claude Code CLI 的完整 TypeScript 源码通过 npm source map 意外暴露 — 1,900+ 文件、512,000+ 行代码，覆盖了 Anthropic 最核心的 Agentic Coding 产品的全部实现细节。我们拿到了这份快照，逐模块拆解，把 Claude Code 的架构设计、工程取舍和隐藏机制全部摊开在阳光下。

> 不是泛泛而谈的"架构概览"。是逐行级别的拆解，是能指出"它为什么这样设计、而不是那样"的深度分析。

## 我们做了什么

### 1. 完整架构逆向

从 1,900 个源文件中梳理出 Claude Code 的核心骨架：

| 子系统 | 核心发现 |
| --- | --- |
| **Agent Loop** | 异步生成器驱动的"思考→工具→观察"无限循环，`QueryEngine` 是一个完整的状态机，支持 REPL 和 SDK 双模式 |
| **Context Engineering** | System Prompt 按"静态缓存区 + 动态区"分层，通过 `__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__` 标记实现 prompt caching，大幅节省 token |
| **Tool System** | Zod schema → JSON Schema 的自动转换，allow/deny/ask 三级权限模型，Feature Flag 编译期门控 |
| **Memory** | user/feedback/project/reference 四种记忆类型，Markdown + frontmatter 持久化，Sonnet 自动提取 + 相关性排序 |
| **Context Compression** | auto/micro/session 三种压缩策略，在接近上下文窗口上限时自动触发摘要 |
| **Multi-Agent** | Coordinator + SubAgent 协作模式，支持 worktree 隔离和并行执行 |
| **启动优化** | 冷启动 <135ms — MDM 读取、Keychain 预取、API 预连接三路并行，在模块加载前就开始 |

### 2. 深度研究笔记

不只是"它是什么"，更关注"它为什么这样做"：

- **[Context Engineering 全拆解](docs/1.context-engineering.md)** — System Prompt 五层组装流程、工具注册的完整 vs 延迟加载策略、Skill 系统如何注入上下文、记忆如何影响 prompt 结构
- **[Agent Loop 机制](docs/2.agent-loop.md)** — 三层结构、五阶段循环、工具并发执行、压缩管道、停止条件
- **[Agent Memory 全链路](docs/3.memory-system-deep-dive.md)** — 记忆的读、写、自动提取、相关性筛选、截断策略，以及为什么选择 Markdown 而不是向量数据库
- **[Tool 系统深度解析](docs/4.tools-system.md)** — 45 个内置工具分组、注册管道、权限系统、MCP 扩展、Skill vs Tool 的本质区别
- **[研究路线图](docs/research-plan.md)** — 从 Agent Loop 到 Compression 到 Multi-Agent 的系统性分析计划

### 3. Python 从零复现

理解了架构，下一步是自己造一个。`claude_code.py` 是一个可运行的简化版 Claude Code，保留核心架构思想：

```bash
# 单轮对话 — agent 自动调用工具完成任务
python claude_code.py chat "分析当前目录的文件结构"

# 交互式 REPL — 支持 /skill 命令
python claude_code.py repl

# 记忆管理
python claude_code.py remember "QueryEngine 使用 async generator" --type project --name "QueryEngine架构"
python claude_code.py memories --query "QueryEngine"
```

## 功能对照表

| 原始 Claude Code 功能 | 简化版 | 说明 |
|---|---|---|
| **Agent Loop (while-true + 停止条件)** | ✅ | 思考→行动→观察循环，直到无 tool_use |
| **LLM API 调用 (Anthropic)** | ✅ | 通过 `anthropic` SDK，支持 tool_use |
| **System Prompt 组装 (静态/动态分界)** | ✅ | 3层结构 + DYNAMIC_BOUNDARY |
| **外挂 Context 文件** | ✅ | CLAUDE.md + --context 自定义文件 |
| **核心工具: Read/Write/Edit** | ✅ | 文件读写三件套 |
| **核心工具: Bash** | ✅ | Shell 命令执行 |
| **核心工具: Glob/Grep** | ✅ | 文件搜索 + 内容搜索 |
| **Memory 系统 (4 类型)** | ✅ | Markdown frontmatter + MEMORY.md 索引 |
| **工具并行执行** | ✅ | partitionToolCalls 分批：read-only 并发，写入串行 |
| **MCP 外部工具** | ✅ | stdio 传输，mcp\_\_server\_\_tool 命名空间 |
| **Skill 系统** | ✅ | .claude/skills/*.md，REPL 中 /skill 触发 |
| 流式输出 (async generator) | ❌ | 同步等待完整响应 |
| 5级压缩管道 | ❌ | 依赖模型 context window |
| Permission 系统 | ❌ | 简化 |
| Agent 子代理 | ❌ | — |
| Bridge (IDE 集成) | ❌ | — |
| Feature Flags | ❌ | — |
| 多代理协作 | ❌ | — |
| 自动记忆抽取 | ❌ | 仅手动 |
| Task / Plan Mode | ❌ | — |
| Deferred Tool (ToolSearch) | ❌ | 全量注册 |

## 项目结构

```text
.
├── claude_code.py              # Python 复现 (~550 行)
├── docs/
│   ├── 1.context-engineering.md
│   ├── 2.agent-loop.md
│   ├── 3.memory-system-deep-dive.md
│   ├── 4.tools-system.md
│   └── research-plan.md
├── CLAUDE.md                   # 架构速查（供 LLM 辅助分析）
└── README_old.md               # 原始快照说明（存档）
```

## 快速开始

```bash
# 安装依赖
pip install anthropic

# 设置 API key
export ANTHROPIC_API_KEY=sk-ant-...

# 开始使用
python claude_code.py chat "帮我分析这个项目的架构"
python claude_code.py repl
```

### MCP 配置

在 `.claude/mcp_servers.json` 中配置外部工具服务器：

```json
{
  "servers": {
    "my-server": {
      "command": "npx",
      "args": ["-y", "@my/mcp-server"]
    }
  }
}
```

### Skill 配置

在 `.claude/skills/` 目录下创建 Markdown 文件：

```yaml
---
name: commit
description: 分析 staged changes 并生成 commit
allowed-tools: [Bash, Read, Grep]
---

# 指令
分析 git staged changes，生成规范的 commit message...
```

## 谁适合读这个项目

- 想了解**顶级 AI 产品真实工程实现**的开发者 — 不是 demo，是 production code
- 在做 **Agentic AI / Tool Use / Context Engineering** 方向的研究者
- 想用 Python **从零搭建 Agent 系统**、需要一个经过验证的参考架构的工程师

## 当前进度

| 模块 | 状态 |
| --- | --- |
| 架构逆向 & 研究笔记 | ✅ 完成 |
| Context Engineering 分析 | ✅ 完成 |
| Agent Loop 分析 | ✅ 完成 |
| Agent Memory 分析 | ✅ 完成 |
| Tool 系统分析 | ✅ 完成 |
| Python 核心框架 (Agent Loop + 6 工具) | ✅ 完成 |
| Memory 系统 (Markdown + 索引) | ✅ 完成 |
| 工具并行执行 | ✅ 完成 |
| MCP 外部工具 | ✅ 完成 |
| Skill 系统 | ✅ 完成 |
| 流式输出 | 📋 计划中 |
| Context Compression | 📋 计划中 |
| Multi-Agent 协作 | 📋 计划中 |

## 免责声明

本项目的源码分析基于公开暴露的 npm source map 快照，仅用于教育与安全研究。Claude Code 版权归 Anthropic 所有。请勿用于商业目的。
