# Agent Evolution: Progressive Claude Architecture Replication

## Overview

This document tracks the progressive evolution of agent capabilities, from minimal reactive foundation to advanced Claude-style architecture with dynamic planning and human interaction.

**Evolution Path**: Minimal (Stage 1) → Dynamic Plan (Stage 2) → Human-in-Loop (Stage 3)

## Evolution Timeline

```
Stage 1 (Minimal)       Stage 2 (Dynamic Plan)      Stage 3 (Human-in-Loop)
-----------------  →  ---------------------  →  ----------------------
14K (423 lines)        22K (620 lines)             TBD
3 tools                4 tools                      6+ tools
Reactive only          + System Prompt              + User interaction
                       + Dynamic Context            + Confirmation
                       + Todo tracking              + Debugging help
```

---

## Stage 1: Minimal Kimi Agent

**File**: `minimal_kimi_agent.py`
**Size**: 14K (423 lines)
**Status**: ✅ Production Ready

### Core Features

- **Multi-turn Conversation**: Full message history management
- **Tool Calling**: ReadFile (10K limit), WriteFile, RunCommand (60s timeout)
- **Workspace Isolation**: All operations in `agent_workspace/`
- **Safety Mechanisms**: Command blacklist, timeouts, file limits
- **Dual Logging**: `.txt` (human-readable) + `.json` (structured)

### Architecture Pattern

```
User Input → Append to messages[] → API Call → Tool Execution → Loop
```

**Characteristics**:
- ❌ No planning guidance
- ❌ No task memory
- ❌ No environmental awareness
- ✅ Simple, reliable, fast

### When to Use

- Simple to medium tasks
- Quick prototyping
- Budget-conscious scenarios
- Learning the basics

### Performance Baseline

- **DA-Code Test Set**: 29.7% avg score, 20.3% success rate (12/59 tasks)
- **Strengths**: Data insights, simple analysis, file I/O
- **Weaknesses**: Visualization, multi-step planning (8+ steps), error recovery

---

## Stage 2: Dynamic Plan Agent

**File**: `dynamic_plan_agent.py`
**Size**: 22K (620 lines)
**Status**: ✅ Complete (2025-11-27)

### What Changed

**Motivation**: Stage 1 lacked guidance for complex tasks. Agent would forget steps, lose track of progress, and make suboptimal decisions.

**Solution**: Replicate Claude's core mechanisms - System Prompt-driven workflow with dynamic context and Todo tracking.

### Key Innovations (Claude Architecture Patterns)

#### 1. System Workflow Prompt

**Purpose**: Teach the agent "how to think" instead of hard-coding execution steps.

**Content** (~400 tokens):
- **Core Working Principles**: Proactive tool usage, iterative execution
- **Todo Management Rules**: When to create (3+ steps), status transitions
- **Thinking Model**: Goal → Info needed → Action → Completeness check
- **Workspace Awareness**: Relative path resolution, large file handling
- **Tool Usage Guidelines**: When to use each tool

**Impact**: Agent makes better decisions without code changes.

#### 2. Dynamic Context Building

**Purpose**: Reconstruct complete context on every API call, not just append messages.

**Mechanism**: `_build_dynamic_messages()` constructs:

```python
[
    {role: "system", content: System Workflow Prompt},  # Persistent guidance
    {role: "system", content: Environment Info},         # Time, workspace, turn
    ...Conversation History...                           # User + assistant messages
    {role: "system", content: Todo State}                # Current task progress
]
```

**Why OpenAI Format**: Kimi API (OpenAI-compatible) doesn't support separate `system` parameter like Claude API, so we inject system prompts as messages in the array.

**Impact**: +550 tokens/call overhead, but better task completion.

#### 3. TodoUpdate Tool

**Purpose**: Short-term task memory and progress tracking.

**Operations**:
- `add(description, status="pending")` → Creates task with auto-generated ID
- `update_status(task_id, status)` → Changes pending/in_progress/completed
- `complete(task_id)` → Shortcut to mark completed

**Visual Status**:
- [ ] pending
- [→] in_progress
- [✓] completed

**Example Workflow**:
```python
# User: "Analyze GCP data - find top 5 resources, plot trends, generate report"

# Turn 1: Agent recognizes multi-step task
TodoUpdate(action="add", description="Read and analyze GCP data")
TodoUpdate(action="add", description="Identify top 5 resources")
TodoUpdate(action="add", description="Plot trends")
TodoUpdate(action="add", description="Generate report")

# Turn 2-5: Agent executes and tracks
TodoUpdate(action="complete", task_id="task_1")  # After reading data
TodoUpdate(action="update_status", task_id="task_2", status="in_progress")
# ... continues until all completed
```

#### 4. Enhanced Logging

**JSON Log Enhancement**:
```json
{
  "messages": [...],
  "todos": {
    "tasks": [
      {"id": "task_1", "description": "...", "status": "completed", ...}
    ]
  },
  "timestamp": "2025-11-27_14-23-15",
  "turns": 5
}
```

**Benefit**: Full audit trail of task planning and execution.

### Architecture Comparison: Stage 1 vs Stage 2

| Aspect | Stage 1 (Minimal) | Stage 2 (Dynamic Plan) |
|--------|-------------------|------------------------|
| **Code Size** | 14K (423 lines) | 22K (620 lines) |
| **Tools** | 3 (Read, Write, Run) | 4 (+TodoUpdate) |
| **System Prompt** | None | Comprehensive (~400 tokens) |
| **Context Building** | Static (append only) | Dynamic (rebuild each turn) |
| **Planning** | None | System Prompt-guided |
| **Task Memory** | None | Todo tracking |
| **Turn Tracking** | No | Yes |
| **Token Overhead** | Baseline | +550/call |
| **Best For** | Simple tasks | Complex multi-step tasks |

### Performance Impact

**Token Usage**:
- System Workflow Prompt: ~400 tokens
- Environment Info: ~50 tokens
- Todo State: ~100 tokens (when active)
- **Total Overhead**: ~550 tokens/call

**Expected Outcome**:
- Higher completion rates for complex tasks
- Fewer wasted turns (better guidance)
- Net positive: overhead offset by efficiency

### Migration Guide

**From Stage 1 to Stage 2**:

```python
# Stage 1 (Minimal)
from minimal_kimi_agent import MinimalKimiAgent
agent = MinimalKimiAgent()
result = agent.run("Complex task...")

# Stage 2 (Dynamic Plan) - Same class name!
from dynamic_plan_agent import MinimalKimiAgent
agent = MinimalKimiAgent()
result = agent.run("Complex task...")  # Now with System Prompt + Todo

# The agent is backward compatible - simple tasks still work the same way
```

**When to Upgrade**:
- Task has 3+ distinct steps
- Requires planning and tracking
- Previous attempts lost progress mid-execution
- Need better decision-making guidance

### Testing Results

**Verification Tests** (`test_dynamic_plan_agent.py`):
- ✅ Dynamic context construction
- ✅ System workflow prompt injection
- ✅ Todo operations (add/update/complete)
- ✅ Enhanced logging with todos
- ✅ All tools registered correctly

**Integration**: Ready for DA-Code benchmark testing (expected improvement over Stage 1 baseline).

---

## Stage 3: SubAgent Pattern (Context Isolation)

**File**: `dynamic_plan_agent.py` (Extended from Stage 2)
**Status**: ✅ Complete (2025-12-17)
**Size**: ~900 lines (+150 lines from Stage 2)

### Motivation

Stage 2 handles complex tasks well, but struggles with:
- **Context Pollution**: Subtasks generating massive intermediate outputs clutter main context
- **Parallel Analysis**: Need to analyze multiple independent files/datasets
- **Error Isolation**: Subtask failures shouldn't abort the entire workflow
- **Token Efficiency**: Long contexts waste tokens on irrelevant information

**Solution**: SubAgent pattern - spawn independent agent instances for isolated subtask execution.

### Key Innovation: SubAgent Tool

#### 1. Complete Context Isolation

**Mechanism**: Create new `DynamicPlanAgent` instance with incremented depth

```python
# Parent Agent (depth=0)
parent = DynamicPlanAgent(depth=0, max_depth=3)

# SubAgent (depth=1) - completely independent
sub_agent = DynamicPlanAgent(
    api_key=parent.client.api_key,
    depth=parent.depth + 1,
    max_depth=parent.max_depth
)
```

**Isolated State**:
- `messages[]` - Independent conversation history
- `todos` - Separate task tracking
- `_current_turn` - Independent turn counter
- `workspace` - Timestamped subdirectory (depth > 0)

#### 2. Recursion Depth Control

**Safety Mechanism**:
```python
if self.depth >= self.max_depth:
    return "❌ SubAgent创建失败: 已达到最大递归深度限制"
```

**Default Limits**:
- `max_depth=3` (configurable at initialization)
- Visual depth indicators: `┌─ 启动SubAgent (深度 1/3)`
- Workspace isolation: `output_dir_{timestamp}_depth{N}/`

#### 3. Tool Definition

```python
{
    "name": "SubAgent",
    "description": f"""启动子Agent处理独立子任务(上下文隔离)。

使用场景:
1. 需要隔离处理的独立子任务(避免污染主任务上下文)
2. 需要独立错误处理的任务(失败不影响主流程)
3. 批量处理多个独立文件/数据集

注意:
- SubAgent有独立的messages历史和todos
- SubAgent只返回最终输出字符串
- 当前递归深度: {self.depth}/{self.max_depth}
- 达到最大深度时无法创建SubAgent""",
    "parameters": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "子任务描述"},
            "max_turns": {"type": "integer", "default": 10}
        },
        "required": ["task"]
    }
}
```

### Implementation Changes

**7 Core Modifications**:

1. **`__init__()`**: Add `depth` and `max_depth` parameters
2. **Workspace Logic**: Depth-based directory creation
3. **System Workflow Prompt**: SubAgent usage guidance (+100 tokens)
4. **Environment Context**: Show recursion depth info
5. **Tool Definition**: SubAgent tool in `_get_tools()`
6. **Tool Execution**: Route to `_tool_sub_agent()`
7. **Logging**: Depth info in filenames and JSON

**`_tool_sub_agent()` Implementation**:
```python
def _tool_sub_agent(self, params: Dict) -> str:
    task = params["task"]
    max_turns = params.get("max_turns", 10)

    # Depth check
    if self.depth >= self.max_depth:
        return "❌ 已达到最大递归深度限制"

    # Create isolated SubAgent
    sub_agent = DynamicPlanAgent(
        api_key=self.client.api_key,
        depth=self.depth + 1,
        max_depth=self.max_depth
    )

    # Execute independently
    result = sub_agent.run(task, max_turns=max_turns)

    # Return only final result
    return f"[SubAgent 执行结果]\n任务: {task}\n结果: {result}"
```

### Usage Examples

#### Example 1: Multi-File Analysis
```python
agent = DynamicPlanAgent(max_depth=2)
result = agent.run("""
Analyze sales_2023.csv, sales_2024.csv, sales_2025.csv

For each file, use SubAgent to:
- Calculate total revenue
- Identify top 5 products
- Find monthly trends

Then aggregate all results in main agent.
""", max_turns=30)
```

**Execution Flow**:
```
Main Agent (depth=0)
  ├─ SubAgent A (depth=1): Analyze sales_2023.csv
  │    → Returns: "Total: $1.2M, Top: Product X, Trend: +15%"
  ├─ SubAgent B (depth=1): Analyze sales_2024.csv
  │    → Returns: "Total: $1.5M, Top: Product Y, Trend: +25%"
  └─ SubAgent C (depth=1): Analyze sales_2025.csv
       → Returns: "Total: $1.8M, Top: Product Z, Trend: +20%"

Main Agent aggregates: "3-year growth: 50%, average trend: +20%"
```

#### Example 2: Recursion Depth Test
```python
agent = DynamicPlanAgent(max_depth=2)
result = agent.run("""
Test recursion limits:
1. Main Agent creates SubAgent A (depth 1)
2. SubAgent A creates SubAgent B (depth 2)
3. SubAgent B tries to create SubAgent C (depth 3) - should fail
""", max_turns=15)
```

### Architecture Comparison

**Stage 2 → Stage 3**:

```
Stage 2: Single Agent                 Stage 3: Multi-Agent Hierarchy
├── messages[]                         Root Agent (depth=0)
├── todos                                ├── messages[] (isolated)
└── tools                                ├── todos (isolated)
    ├── ReadFile                         ├── tools
    ├── WriteFile                        │   ├── ReadFile
    ├── RunCommand                       │   ├── WriteFile
    └── TodoUpdate                       │   ├── RunCommand
                                         │   ├── TodoUpdate
                                         │   └── SubAgent ← NEW
                                         ├── SubAgent A (depth=1)
                                         │   └── [isolated context]
                                         └── SubAgent B (depth=1)
                                             └── [isolated context]
```

### Performance Characteristics

**Token Usage**:
- Root Agent: ~700 tokens/call (+100 for SubAgent tool definition)
- Each SubAgent: ~600 tokens/call
- 3 SubAgents × 5 turns = 15 additional API calls

**Cost Implications** (Kimi API example):
- Stage 2 single task: ~6,000 tokens (10 turns)
- Stage 3 with 3 SubAgents: ~9,700 tokens (1 root + 3×5 sub turns)
- **60% cost increase** for context isolation benefit

**Best Practices**:
- ✅ Use for: Multi-file analysis, large intermediate outputs, independent subtasks
- ❌ Avoid for: Simple reads, single-step operations, dependent sequential tasks

### Testing & Validation

**Unit Tests** (`test_subagent.py`, 8 tests):
```bash
# Run all tests
make test-subagent

# Run integration tests (requires API key)
make test-subagent-integration
```

**Test Coverage**:
1. `test_subagent_initialization()` - Depth parameter validation
2. `test_subagent_depth_limit()` - Recursion safety
3. `test_subagent_context_isolation()` - Message history separation
4. `test_subagent_tool_definition()` - Tool schema validation
5. `test_subagent_workspace_isolation()` - Workspace directory separation
6. `test_system_prompt_includes_subagent()` - System prompt verification
7. `test_subagent_execution_simple()` - Integration test (optional)

### Future: Stage 4 (Human-in-Loop, Planned Q1 2026)

**Planned Features**:
- `AskUserConfirmation()` - Approval before destructive operations
- `RequestUserGuidance()` - Interactive debugging
- `ShowIntermediateResult()` - Milestone review

---

## Architectural Principles (from Claude)

### 1. Responsive Architecture
- No predefined execution loops (Plan→Execute→Reflect)
- LLM decides next action dynamically each turn
- System Prompt teaches "how to think", not "what to do"

### 2. System Prompt-Driven Behavior
- Workflow guidance via comprehensive prompts
- Dynamic context construction on every API call
- Environment awareness (time, workspace, turn)

### 3. Short-Term Memory
- Todo tracking for task progress
- System reminders for environmental context
- No external state dependencies

---

## Future Directions

### Stage 4: Self-Evolution (Future)

**Concepts**:
- Learn from successful execution patterns
- Automatic System Prompt optimization based on error analysis
- Tool usage pattern recognition
- Meta-learning: agent improves how it learns

---

## References

### Source Documents

- [OPTIMIZATION_SUMMARY.md](../OPTIMIZATION_SUMMARY.md) - Original Stage 2 optimization notes
- [VERSION_GUIDE.md](../VERSION_GUIDE.md) - Original version comparison guide
- [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) - Detailed before/after technical comparison

### Related Documentation

- [README.md](../README.md) - Project overview and quick start
- [CLAUDE.md](../CLAUDE.md) - Technical reference for Claude Code integration
- `claude_agent_pseudocode.py` - Reference implementation of Claude patterns

---

**Document Version**: 1.0
**Last Updated**: 2025-11-27
**Project**: Claude Agent Replicate
