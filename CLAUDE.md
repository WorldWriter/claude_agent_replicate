# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent replication project implementing Claude Code's architecture patterns using Moonshot Kimi API. Demonstrates progressive enhancement from minimal agent (Stage 1) through system prompt-driven dynamic planning (Stage 2) to human-in-the-loop interaction (Stage 3, planned). Uses DA-Code benchmark for objective evaluation.

## Running the Agent

```bash
# Ensure .env has MOONSHOT_API_KEY set
python minimal_kimi_agent.py
```

The agent runs example tasks defined in `example_simple()` or `example_multi_step()` functions. Modify these or call the agent programmatically:

```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("Your task description", max_turns=20)
```

## Architecture

### Three Implementations

**MinimalKimiAgent** (`minimal_kimi_agent.py`) - Stage 1: Responsive Foundation
- Moonshot Kimi API via OpenAI-compatible client
- Multi-turn conversation with full history
- Three tools: ReadFile (10k char limit), WriteFile, RunCommand
- Automatic conversation logging
- Baseline: 29.7% DA-Code average score

**DynamicPlanAgent** (`dynamic_plan_agent.py`) - Stage 2: System Prompt + Dynamic Context
- Same class name `MinimalKimiAgent` for easy migration
- System workflow prompt (~400 tokens) teaching "how to think"
- Dynamic context building (rebuilds context every API call)
- TodoUpdate tool for task tracking with visual progress
- Enhanced logging with todos and turn count
- +550 tokens/call but higher completion rate

**SimpleClaudeAgent** (`claude_agent_pseudocode.py`) - Reference/Educational
- Demonstrates Claude agent patterns (responsive loop, dynamic context)
- Key architectural difference from traditional Plan→Execute→Reflect pattern
- System Prompt-driven workflow with todo short-term memory
- Not for production - educational purposes only

### Tool Execution Flow

1. Agent sends message history + tool definitions to API
2. API returns either text (task complete) or tool_calls
3. Tools execute in workspace context with results added to history
4. Loop continues until no tool calls or max_turns reached

## Key Conventions

### Workspace Isolation
- All agent operations occur in `agent_workspace/` directory
- Path resolution: relative paths → workspace, absolute paths → preserved
- RunCommand executes with `cwd=agent_workspace/`

### Logging
- Dual format: `.txt` (human-readable) + `.json` (raw messages)
- Location: `logs/{YYYY-MM-DD_HH-MM-SS}.{txt|json}`
- Large content truncated at 500 chars in txt logs

### Safety
- RunCommand blacklist: `rm -rf`, `sudo`, `shutdown`, `reboot`, `mkfs`, `dd`, etc.
- 60-second timeout for command execution
- ReadFile truncates at 10,000 characters (~2-3k tokens)

## Data Context

### DA-Code Benchmark Dataset

**Location**: `agent_workspace/da-code/da_code/`

**Current Status**:
- ✅ Git clone includes: 100 sample tasks + 59 Gold answers
- ⚠️ Full dataset requires download: 500+ tasks, 2.1GB source data

**Download Full Dataset**:
```bash
pip install gdown
gdown "https://drive.google.com/uc?id=1eM_FVT1tlY4XXp6b7TrKzgTWOvskrjTs" -O source.zip
unzip source.zip -d agent_workspace/da-code/da_code/
```

**Structure**:
- `source/` - Task data files (2.1GB when full, currently 100 samples)
- `gold/` - Standard answers (59 tasks included in git)
- `configs/` - Task metadata and evaluation configs

**Baseline Test**: 59 tasks, 23.7% accuracy (see `docs/baseline_report.md`)

Common pattern: pandas for data manipulation, matplotlib/seaborn for visualization

## Development Stages

| Stage | Status | Focus |
|-------|--------|-------|
| 1 | ✅ Complete (2025-11-20) | Minimal Agent - tool calling, multi-turn, logging |
| 2 | ✅ Complete (2025-11-27) | Dynamic Plan - system prompt + context + todos |
| 3 | 🔄 Planned (2026 Q1) | Human-in-Loop - key decision confirmation, interactive debugging |
| 4 | 📋 Future | Memory & Learning - prompt-based optimization |

**Key Files**:
- `minimal_kimi_agent.py` - Stage 1 implementation
- `dynamic_plan_agent.py` - Stage 2 implementation
- `claude_agent_pseudocode.py` - Reference architecture
- `docs/AGENT_EVOLUTION.md` - Detailed evolution guide

## Environment Configuration

Required in `.env`:
```
MOONSHOT_API_KEY=sk-...
LLM_MODEL=kimi-k2-turbo-preview  # optional, this is default
```

Optional for reference implementation:
```
ANTHROPIC_API_KEY=sk-ant-...
```
