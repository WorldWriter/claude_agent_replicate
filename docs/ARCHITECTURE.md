# Agent Architecture Deep Dive

This document provides a detailed technical explanation of the architectural patterns implemented in this project, comparing different agent approaches and explaining design decisions.

## Table of Contents

- [Overview](#overview)
- [Agent Execution Flows](#agent-execution-flows)
- [Architecture Comparison](#architecture-comparison)
- [Tool Execution Pipeline](#tool-execution-pipeline)
- [Workspace Isolation](#workspace-isolation)
- [Safety Mechanisms](#safety-mechanisms)
- [Key Design Decisions](#key-design-decisions)
- [Data Flow: DA-Code Integration](#data-flow-da-code-integration)

---

## Overview

This project implements three distinct agent architectures, each demonstrating different approaches to AI agent design:

1. **MinimalKimiAgent**: Reactive execution with tool calling
2. **PlanKimiAgent**: Proactive planning with adaptive execution
3. **SimpleClaudeAgent**: Educational reference showing Claude's patterns

All three share common foundations (tool calling, multi-turn conversation) but differ significantly in their planning and decision-making strategies.

---

## Agent Execution Flows

### MinimalKimiAgent: Reactive Loop

The minimal agent operates on a simple reactive pattern - no upfront planning, just respond to each situation as it arises.

```
┌─────────────────────┐
│   User Request      │
│  "Analyze data.csv" │
└──────────┬──────────┘
           │
           ▼
┌───────────────────────────────┐
│ Build API Request             │
│ - System prompt (agent role)  │
│ - Message history             │
│ - Tool definitions            │
└──────────┬────────────────────┘
           │
           ▼
┌───────────────────────────────┐
│ Send to Kimi API              │
│ (OpenAI-compatible endpoint)  │
└──────────┬────────────────────┘
           │
           ▼
     ┌─────────────┐
     │ API Returns │
     └──────┬──────┘
            │
    ┌───────▼──────────┐
    │ Text response    │◄─── No tool calls
    │   OR             │       │
    │ Tool call list   │       │
    └───────┬──────────┘       │
            │                  │
       Yes (tools)             │
            │                  │
            ▼                  │
┌──────────────────────────┐   │
│ Execute Each Tool:       │   │
│                          │   │
│ - ReadFile               │   │
│ - WriteFile              │   │
│ - RunCommand             │   │
│                          │   │
│ Collect results          │   │
└──────────┬───────────────┘   │
           │                   │
           ▼                   │
┌──────────────────────────┐   │
│ Add Tool Results to      │   │
│ Message History          │   │
└──────────┬───────────────┘   │
           │                   │
           ▼                   │
    ┌──────────────┐           │
    │ Turn++ < Max?│           │
    └──────┬───────┘           │
      Yes  │   No              │
           │    │              │
    ┌──────▼────▼──────┐       │
    │  Loop or Finish  │◄──────┘
    └──────────────────┘
```

**Key Characteristics**:
- **No Planning**: Agent doesn't pre-plan steps, just reacts to current state
- **Tool-Driven**: LLM decides which tools to call based on conversation history
- **Memory**: Full message history provides context for each decision
- **Stopping**: Ends when no tool calls returned or max turns reached

---

### PlanKimiAgent: Plan-Based Execution

The planning agent adds a structured planning phase before execution, maintaining a persistent plan file throughout the task.

```
┌─────────────────────┐
│   User Request      │
│  "Build ML model"   │
└──────────┬──────────┘
           │
           ▼
┌────────────────────────────┐
│ System Prompt Instructs:   │
│ "First create a plan"      │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ LLM Calls CreatePlan Tool  │
└──────────┬─────────────────┘
           │
           ▼
┌────────────────────────────┐
│ plan.md Created:           │
│                            │
│ # Task: Build ML Model     │
│ ## Steps                   │
│ - [ ] Load data            │
│ - [ ] Preprocess           │
│ - [ ] Train model          │
│ - [ ] Evaluate             │
│ - [ ] Save results         │
└──────────┬─────────────────┘
           │
           │  [Execution Loop]
           ▼
    ┌──────────────────┐
    │ Read Current Plan│
    └──────┬───────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Execute Next Step:   │
    │ - ReadFile           │
    │ - RunCommand         │
    │ - etc.               │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────────┐
    │ Update Plan:         │
    │ - Mark step complete │
    │ - Add execution log  │
    │ - Adjust if needed   │
    └──────┬───────────────┘
           │
           ▼
    ┌──────────────────┐
    │ All steps done?  │
    └──────┬───────────┘
      No   │   Yes
           │    │
    ┌──────▼────▼──┐
    │ Loop or Done │
    └──────────────┘
```

**Key Characteristics**:
- **Upfront Planning**: Creates structured plan before executing
- **Plan Persistence**: plan.md file tracks progress (human-readable)
- **Adaptive**: Can modify plan based on intermediate results
- **Visibility**: Users can inspect plan.md to see agent's strategy
- **Three Plan Tools**: CreatePlan, UpdatePlan, ReadPlan

**Example plan.md**:
```markdown
# Task: Build ML classification model

## Steps
- [x] Load train.csv and test.csv (1000 rows, 20 features)
- [x] Preprocess data (filled 50 missing values, encoded 3 categories)
- [~] Train Random Forest model (in progress - fitting...)
- [ ] Evaluate model performance
- [ ] Save predictions to predictions.csv

## Execution Log
[2025-11-26 14:30] Step 1 complete - data loaded successfully
[2025-11-26 14:32] Step 2 complete - preprocessing done
[2025-11-26 14:35] Step 3 started - training model with 100 trees
```

---

### SimpleClaudeAgent: Reference Pattern

Educational implementation showing how Claude agents work conceptually. Not production-ready but useful for understanding architectural decisions.

```
Traditional Agent Pattern:
  ┌──────────┐
  │   Plan   │  (Generate full plan upfront)
  └─────┬────┘
        │
        ▼
  ┌──────────┐
  │ Execute  │  (Follow plan rigidly)
  └─────┬────┘
        │
        ▼
  ┌──────────┐
  │ Reflect  │  (Evaluate results)
  └─────┬────┘
        │
        ▼
  ┌──────────┐
  │  Update  │  (Modify plan)
  └─────┬────┘
        │
        └──► Loop

Claude-Style Agent Pattern:
  ┌──────────────┐
  │ User Message │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────┐
  │ Build Dynamic Context:   │
  │ - System prompt          │
  │ - Recent messages        │
  │ - Todo short-term memory │
  │ - Environment info       │
  └──────┬───────────────────┘
         │
         ▼
  ┌──────────────────┐
  │ API Call         │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Response:        │
  │ Text or Tools?   │
  └──────┬───────────┘
         │
    ┌────▼────┐
    │  Tools? │
    └────┬────┘
    Yes  │  No
         │   └──► Final Response
         ▼
  ┌──────────────────┐
  │ Execute Tools    │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Add to History   │
  └──────┬───────────┘
         │
         └──► Loop (dynamic decision each turn)
```

**Key Differences from Traditional**:
- **No Fixed Plan**: Decisions made fresh each turn based on current context
- **Dynamic System Prompts**: Evolve based on task state
- **Todo-Based Memory**: Lightweight task tracking vs. heavyweight plans
- **Responsive**: Adapts immediately to unexpected results

---

## Architecture Comparison

Detailed comparison across multiple dimensions:

| Aspect | MinimalKimiAgent | PlanKimiAgent | SimpleClaudeAgent |
|--------|------------------|---------------|-------------------|
| **Planning** | None (reactive) | Upfront + adaptive | None (responsive) |
| **Memory Model** | Message history | Message history + plan.md | Message + Todo list |
| **Decision Making** | LLM per turn | Plan-guided LLM | System prompt-driven |
| **Visibility** | Logs only | Logs + plan.md | Logs + todo state |
| **Complexity** | Low (423 lines) | Medium (654 lines) | Medium (527 lines) |
| **Best For** | Simple tasks | Multi-step workflows | Educational reference |
| **Production Ready** | Yes | Yes | No (simplified) |
| **Tool Count** | 3 (Read, Write, Run) | 6 (+ 3 plan tools) | 5 (+ Todo, SubAgent) |
| **Max Turns** | 20 | 30 | 10 (example only) |
| **API** | Kimi (OpenAI-compat) | Kimi | Claude (Anthropic) |

---

## Tool Execution Pipeline

How tools are defined, called, and executed across all agent implementations:

```
┌─────────────────────────────────────────┐
│ 1. Tool Definition (JSON Schema)        │
│                                          │
│ {                                        │
│   "type": "function",                    │
│   "function": {                          │
│     "name": "ReadFile",                  │
│     "description": "Read file content",  │
│     "parameters": {                      │
│       "type": "object",                  │
│       "properties": {                    │
│         "file_path": {                   │
│           "type": "string",              │
│           "description": "Path to file"  │
│         }                                │
│       },                                 │
│       "required": ["file_path"]          │
│     }                                    │
│   }                                      │
│ }                                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 2. LLM Receives Tools + Message         │
│                                          │
│ System: "You are a data analysis agent" │
│ User: "Read data.csv and analyze it"    │
│ Tools: [ReadFile, WriteFile, RunCommand]│
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 3. LLM Returns Tool Call Request        │
│                                          │
│ {                                        │
│   "id": "call_abc123",                   │
│   "type": "function",                    │
│   "function": {                          │
│     "name": "ReadFile",                  │
│     "arguments": {                       │
│       "file_path": "data.csv"            │
│     }                                    │
│   }                                      │
│ }                                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 4. Agent Dispatcher Executes             │
│                                          │
│ if tool_name == "ReadFile":              │
│     return self._execute_read_file(args) │
│ elif tool_name == "WriteFile":           │
│     return self._execute_write_file(args)│
│ elif tool_name == "RunCommand":          │
│     return self._execute_run_command(args│
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 5. Tool Execution with Safety           │
│                                          │
│ def _execute_read_file(file_path):      │
│     # Resolve to workspace               │
│     full_path = workspace_path(file_path)│
│     # Limit size                         │
│     if size > 10000:                     │
│         content = truncate(content)      │
│     return content                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 6. Result Formatted and Returned        │
│                                          │
│ {                                        │
│   "tool_call_id": "call_abc123",         │
│   "role": "tool",                        │
│   "name": "ReadFile",                    │
│   "content": "col1,col2,col3\n1,2,3..."  │
│ }                                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ 7. Added to Message History              │
│                                          │
│ messages = [                             │
│     {...previous messages...},           │
│     {"role": "assistant",                │
│      "tool_calls": [...]},               │
│     {"role": "tool",                     │
│      "content": "col1,col2..."}          │
│ ]                                        │
└──────────────┬──────────────────────────┘
               │
               ▼
      ┌────────────────┐
      │ Continue Loop  │
      └────────────────┘
```

---

## Workspace Isolation

All agent file operations are isolated to `agent_workspace/` for safety and clarity.

```
Project Root:
/Users/user/claude_agent_replicate/
├── minimal_kimi_agent.py       ← Stage 1: Agent code (safe from agent)
├── dynamic_plan_agent.py       ← Stage 2: Agent code (safe from agent)
├── test/                        ← Test code (safe from agent)
│
└── agent_workspace/             ← AGENT OPERATES HERE ONLY
    ├── data.csv                 ← Agent can read/write
    ├── output/                  ← Agent can create dirs
    │   └── plot.png             ← Agent can save outputs
    ├── temp_script.py           ← Agent can generate code
    └── da-code/                 ← DA-Code benchmark
```

**Path Resolution Logic**:

```python
def resolve_path(user_path: str) -> str:
    """
    Convert user-provided paths to workspace-scoped paths.

    - Relative paths → workspace/relative_path
    - Absolute paths → preserved (but validated)
    """
    if os.path.isabs(user_path):
        # Absolute path - validate it's safe
        if not user_path.startswith(SAFE_DIRS):
            raise SecurityError("Access outside safe directories")
        return user_path
    else:
        # Relative path - scope to workspace
        return os.path.join(WORKSPACE_DIR, user_path)

# Examples:
# "data.csv" → "agent_workspace/data.csv"
# "output/plot.png" → "agent_workspace/output/plot.png"
# "/tmp/file.txt" → "/tmp/file.txt" (if /tmp is safe)
```

**Benefits**:
1. **Safety**: Can't accidentally modify project code
2. **Clarity**: Clear boundary between agent and infrastructure
3. **Testing**: Easy cleanup (`rm -rf agent_workspace/output_dir/*`)
4. **Debugging**: All agent artifacts in one place

---

## Safety Mechanisms

Multiple layers of safety to prevent accidental or malicious operations:

### 1. Command Blacklist

```python
DANGEROUS_COMMANDS = [
    'rm -rf',           # Recursive force delete
    'sudo',             # Privilege escalation
    'shutdown',         # System shutdown
    'reboot',           # System reboot
    'mkfs',             # Format filesystem
    'dd',               # Disk destroyer
    ':(){ :|:& };:',    # Fork bomb
    'mv /* ',           # Move root files
    'chmod -R 777',     # Overly permissive permissions
]

def is_safe_command(cmd: str) -> bool:
    """Check if command is safe to execute."""
    cmd_lower = cmd.lower().strip()
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in cmd_lower:
            return False
    return True
```

### 2. Execution Timeout

```python
def run_command(cmd: str, timeout_sec: int = 60) -> str:
    """
    Execute command with timeout protection.
    Prevents infinite loops or hung processes.
    """
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,  # 60-second limit
            cwd=WORKSPACE_DIR      # Execute in workspace
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return f"Error: Command exceeded {timeout_sec}s timeout"
```

### 3. File Size Limits

```python
def read_file(file_path: str, max_chars: int = 10000) -> str:
    """
    Read file with size limit to prevent memory issues.
    """
    full_path = resolve_path(file_path)

    with open(full_path, 'r') as f:
        content = f.read(max_chars + 1)

    if len(content) > max_chars:
        return (
            content[:max_chars] +
            f"\n\n[Truncated - file exceeds {max_chars} chars]"
        )

    return content
```

### 4. Turn Limits

```python
def run(task: str, max_turns: int = 20) -> str:
    """
    Execute task with maximum turn limit.
    Prevents infinite agent loops.
    """
    for turn in range(max_turns):
        response = self._call_api(messages)

        if no_tool_calls(response):
            return extract_text(response)

        # Execute tools, continue...

    return "Error: Exceeded maximum turns without completion"
```

---

## Key Design Decisions

### Why OpenAI-Compatible API (Kimi)?

**Decision**: Use Moonshot Kimi API via OpenAI SDK rather than Claude directly for production agent.

**Rationale**:
- **Model Swapping**: Can easily switch models (Kimi, GPT-4, local models) without changing code
- **Cost Efficiency**: Kimi offers competitive pricing for development
- **Multi-Turn Support**: Handles long conversations (16+ turns) reliably
- **China Access**: Better network performance and support in China
- **Future Flexibility**: Not locked into single provider

**Trade-offs**:
- Not using Claude despite studying Claude patterns (SimpleClaudeAgent shows how)
- Kimi-specific quirks may differ from GPT-4 behavior
- Community/support smaller than OpenAI or Anthropic

---

### Why Dual Logging Format?

**Decision**: Log conversations in both human-readable (TXT) and structured (JSON) formats.

**TXT Format** (for humans):
```
=== Turn 1 ===
[User]
Analyze the sales data in data.csv

[Assistant - Tool Call]
ReadFile(file_path="data.csv")

[Tool Result]
col1,col2,col3
100,200,300
...

[Assistant]
I've analyzed the data. Total sales: $600
```

**JSON Format** (for machines):
```json
{
  "timestamp": "2025-11-26T14:30:00",
  "task": "Analyze sales data",
  "messages": [
    {"role": "user", "content": "Analyze the sales..."},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool", "content": "col1,col2,col3..."}
  ],
  "turns": 3,
  "outcome": "success"
}
```

**Benefits**:
- TXT: Easy debugging, human review, portfolio demonstrations
- JSON: Automated analysis, metrics extraction, replay testing
- Together: Best of both worlds for development

---

## Data Flow: DA-Code Integration

How the DA-Code benchmark integrates with the agent architecture:

```
┌────────────────────────────────┐
│ DA-Code Dataset (500 tasks)    │
│                                 │
│ Categories:                     │
│ - Data Insight                  │
│ - Data Manipulation             │
│ - Data Visualization            │
│ - Machine Learning              │
│ - Statistical Analysis          │
│ - NLP                           │
│ - GCP Specific                  │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Dataset Split (stratified)     │
│                                 │
│ - Train: 50 tasks               │
│ - Validation: 50 tasks          │
│ - Test: 59 tasks (baseline)     │
│                                 │
│ Balanced by difficulty:         │
│ Easy/Medium/Hard ~33% each      │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Task Configuration (JSONL)     │
│                                 │
│ {                               │
│   "id": "task_123",             │
│   "category": "visualization",  │
│   "difficulty": "hard",         │
│   "description": "...",         │
│   "data_file": "sales.csv",     │
│   "gold_file": "expected.png"   │
│ }                               │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Agent Execution                 │
│                                 │
│ agent.run(task["description"])  │
│   ↓                             │
│ Multi-turn conversation         │
│   ↓                             │
│ Tool calls (Read/Write/Run)     │
│   ↓                             │
│ Output files generated          │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Official Evaluator              │
│                                 │
│ da_agent.evaluators.evaluate()  │
│   ↓                             │
│ Compare output vs gold answer   │
│   ↓                             │
│ Score: 0.0 to 1.0 (partial      │
│ credit for partially correct)   │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Results Aggregation             │
│                                 │
│ {                               │
│   "overall_avg": 0.297,         │
│   "overall_success": 0.203,     │
│   "by_category": {...},         │
│   "by_difficulty": {...},       │
│   "task_details": [...]         │
│ }                               │
└──────────┬─────────────────────┘
           │
           ▼
┌────────────────────────────────┐
│ Logs Saved                      │
│                                 │
│ logs/eval_2025-11-26.json       │
│ logs/eval_2025-11-26.txt        │
└─────────────────────────────────┘
```

**Evaluation Metrics**:
- **Avg Score**: Average of all task scores (0.0 to 1.0), allows partial credit
- **Success Rate**: Percentage of tasks with score = 1.0 (perfect)
- **By Category**: Performance breakdown across 7 task categories
- **By Difficulty**: Easy/Medium/Hard performance comparison

---

## Further Reading

- **Implementation Details**: See [`CLAUDE.md`](../CLAUDE.md) for API configuration, running agents, and development stages
- **Runnable Examples**: See [`examples/`](../examples/) for practical demonstrations
- **Evaluation Framework**: See [`test/README.md`](../test/README.md) for benchmark testing procedures
- **Dataset Analysis**: See [`dataset_split_report.md`](dataset_split_report.md) for detailed dataset statistics

---

**Last Updated**: 2025-11-26
