# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is a **read-only research archive** of the Claude Code CLI source snapshot (exposed via npm source maps on 2026-03-31). It is maintained for educational and defensive security research. There is no build system, test suite, or runnable application — this is a static TypeScript source snapshot for analysis only.

## Key Facts

- **Language**: TypeScript (strict)
- **Runtime**: Bun (uses `bun:bundle` feature flags for dead code elimination)
- **Terminal UI**: React + Ink (custom fork in `src/ink/`)
- **CLI Parsing**: Commander.js
- **Scale**: ~1,900 files, 512,000+ lines across `src/`

## Architecture

### Entry Point & Startup

`src/main.tsx` is the entrypoint (~800K lines, heavily bundled). Startup is optimized with parallel prefetch side-effects that fire before module evaluation: MDM settings read, keychain prefetch, and API preconnect run concurrently to achieve <135ms startup overhead.

### Core Engine

- **`src/QueryEngine.ts`** — Standalone state machine encapsulating a conversation lifecycle. Uses async generators to yield incremental UI updates. Designed for both REPL and SDK use. Manages `mutableMessages`, token usage tracking, and turn-scoped discovery.
- **`src/query.ts`** (~69K lines) — Query pipeline orchestration layer above QueryEngine.
- **`src/context.ts`** — Collects system/user context (cwd, git status, CLAUDE.md files) for dynamic system prompt assembly.

### Tool System (`src/tools/`, `src/Tool.ts`, `src/tools.ts`)

Each tool is a self-contained module with input schema (Zod), permission model, and execution logic. Tools are registered with `isEnabled()` checks (environment-aware) and organized into presets. Lazy `require()` is used for circular dependencies (e.g., TeamCreateTool). Feature flags (`feature('FLAG_NAME')` from `bun:bundle`) gate tool availability at compile time.

### Command System (`src/commands/`, `src/commands.ts`)

Slash commands (`/commit`, `/review`, etc.) registered with conditional imports based on feature flags. Commands use lazy loading — heavy implementations are dynamically imported only when invoked.

### Permission System (`src/hooks/toolPermission/`)

Denial-based tracking with three rule categories: `alwaysAllowRules`, `alwaysDenyRules`, `alwaysAskRules`. Mode hierarchy: `bypassPermissions` > `auto` > `plan` > `default`.

### System Prompt Assembly

The system prompt is composed from 5 layers: tool schemas (cached), core directives, memory/self-correction rules, dynamic context, and formatting rules. A cache boundary (`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`) separates static sections from per-turn dynamics to reduce token cost.

### Service Layer (`src/services/`)

- `api/` — Anthropic API client with bootstrap and file API
- `mcp/` — MCP server connection with deduplication and policy filtering
- `oauth/` — OAuth 2.0 flows with JWT auth
- `compact/` — Context compression for long conversations
- `extractMemories/` — Auto-extraction of memories from conversations via forked agent
- `analytics/` — GrowthBook-based feature flags

### Bridge System (`src/bridge/`)

Bidirectional IDE communication layer (VS Code, JetBrains). Handles message protocol, permission callbacks, JWT auth, and session management.

### Memory System (`src/memdir/`)

Four memory types: user, feedback, project, reference. Stored as markdown files with frontmatter. MEMORY.md serves as an index (200-line/25KB limit). Auto-extraction runs post-query via Sonnet, selecting max 5 relevant memories.

### Other Subsystems

- `src/coordinator/` — Multi-agent orchestration
- `src/skills/` — Reusable workflow system
- `src/plugins/` — Plugin loader
- `src/state/` — State management
- `src/ink/` — Custom Ink fork with layout engine, event system, and terminal rendering

## Feature Flags

Compile-time flags via `bun:bundle` that strip dead code: `PROACTIVE`, `KAIROS`, `BRIDGE_MODE`, `DAEMON`, `VOICE_MODE`, `AGENT_TRIGGERS`, `MONITOR_TOOL`, `COORDINATOR_MODE`, `WORKFLOW_SCRIPTS`.

## Research Notes

- No `package.json`, `tsconfig.json`, or build config exists — this is extracted source only
- Large files like `main.tsx` (800K), `query.ts` (69K), `QueryEngine.ts` (47K), `interactiveHelpers.tsx` (57K) are bundled artifacts
- The `src/ink/` directory is a substantially modified fork of the Ink terminal UI library
- The `docs/` directory contains research notes on context engineering, agent memory, and analysis plans
