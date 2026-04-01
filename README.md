# Claude Agent Replicate

> 通过解析 Claude Code CLI 源码，学习其架构设计，并用 Python 从零复现一个简化版 Agent 系统。

## 项目目标

1. **源码研读** — 深入分析 Claude Code（TypeScript）的核心架构：Agent Loop、Context Engineering、Tool System、Memory、Permission 等子系统
2. **Python 复现** — 基于理解逐步实现 Python 版本，重点复现核心机制而非 1:1 移植
3. **研究输出** — 将分析过程整理为可复用的研究笔记

## 当前进度

| 模块 | 状态 | 说明 |
| --- | --- | --- |
| 架构分析 | ✅ 完成 | 见 `docs/` 下研究笔记 |
| Context Engineering | ✅ 完成 | 系统提示分层、动态边界、缓存策略 |
| Agent Memory | ✅ 完成 | 四种记忆类型、自动提取、相关性筛选 |
| Python 基础框架 | 🚧 进行中 | `claude_code.py` — 已实现 Agent Loop / Tool / Memory / Context 骨架 |
| Tool System | 📋 计划中 | 权限模型、Zod→JSON Schema、并发安全 |
| Context Compression | 📋 计划中 | auto/micro/session 压缩策略 |
| Multi-Agent | 📋 计划中 | Coordinator + SubAgent 协作 |

## 项目结构

```text
.
├── README.md              # 本文件
├── CLAUDE.md              # Claude Code 上下文提示（供 LLM 辅助分析用）
├── claude_code.py         # Python 复现主文件
├── docs/
│   ├── research-plan.md   # 研究路线图
│   ├── context-engineering.md  # System Prompt 分层与工具注册分析
│   └── agent-memory.md    # 记忆系统分析
└── README_old.md          # 原始快照说明（存档）
```

## 原始架构要点（来自源码分析）

Claude Code 的核心架构可概括为：

- **Agent Loop**（`query.ts` / `QueryEngine.ts`）— 异步生成器驱动的"思考→工具→观察"循环
- **Context Engineering**（`context.ts` / `prompts.ts`）— System Prompt 分为静态缓存区与动态区，通过边界标记降低 token 开销
- **Tool System**（`tools/` / `Tool.ts`）— Zod schema 定义输入、权限三级模型（allow/deny/ask）、Feature Flag 门控
- **Memory**（`memdir/`）— user / feedback / project / reference 四种类型，Markdown + frontmatter 持久化
- **Compression**（`services/compact/`）— 上下文接近窗口上限时自动触发摘要压缩

详细分析见 `docs/` 目录。

## Python 复现思路

`claude_code.py` 当前实现了最小可运行骨架：

```bash
# 运行 Agent Loop
python claude_code.py chat "分析 QueryEngine 的状态机设计"

# 存储记忆
python claude_code.py remember "QueryEngine 使用 async generator yield 增量更新" --type project

# 查看记忆
python claude_code.py memories --query "QueryEngine"

# 列出工具
python claude_code.py tools
```

后续将逐步加入：真实 LLM 调用、流式输出、权限系统、上下文压缩等。

## 研究笔记

建议阅读顺序：

1. `docs/research-plan.md` — 研究路线总览
2. `docs/context-engineering.md` — System Prompt 与工具注册
3. `docs/agent-memory.md` — 记忆系统全链路

## 免责声明

本项目的源码分析基于公开暴露的 npm source map 快照，仅用于教育与安全研究。Claude Code 版权归 Anthropic 所有。请勿用于商业目的。
