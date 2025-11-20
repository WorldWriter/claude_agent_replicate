# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent architecture research project studying various agent patterns using GCP Cloud Billing cost data combined with industrial implementation experience. Currently implements a staged development approach progressing from minimal viable agent to sophisticated capabilities.

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

### Two Implementations

**MinimalKimiAgent** (`minimal_kimi_agent.py`) - Production Stage 1
- Moonshot Kimi API via OpenAI-compatible client
- Multi-turn conversation with full history
- Three tools: ReadFile (10k char limit), WriteFile, RunCommand
- Automatic conversation logging

**SimpleClaudeAgent** (`claude_agent_pseudocode.py`) - Reference/Educational
- Demonstrates Claude agent patterns (responsive loop, dynamic context)
- Key architectural difference from traditional Plan→Execute→Reflect pattern
- System Prompt-driven workflow with todo short-term memory

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

**Dataset**: `agent_workspace/data/full_gcp_data.csv`
- 124,275 rows, 15 columns of GCP Cloud Billing data
- Spans 2022-2023, includes Resource ID, Service Name, Usage Quantity, Costs, CPU/Memory utilization

**Analysis Scripts** in `agent_workspace/`:
- `validate_cost_calculation.py` - Verifies: Usage Quantity × Cost per Quantity = Unrounded Cost
- `analyze_top_resource_usage.py` - Top N resource usage trends
- `count_resource_ids.py` - Unique resource statistics

Common pattern: pandas for data manipulation, matplotlib/seaborn for visualization

## Development Stages

| Stage | Status | Focus |
|-------|--------|-------|
| 1 | Complete | Minimal Agent - tool calling, multi-turn, logging |
| 2 | Planned | Plan Agent - adaptive planning based on history |
| 3 | Planned | Memory & Learning - prompt-based optimization |

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
