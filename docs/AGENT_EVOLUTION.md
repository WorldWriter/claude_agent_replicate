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

## Stage 3: Human-in-Loop Agent (Planned)

**File**: `human_loop_agent.py` (Future)
**Status**: 🔄 Planned (Q1 2026)

### Motivation

- **Trust**: Critical decisions need human oversight
- **Error Recovery**: Human guidance speeds up debugging
- **Transparency**: Users want visibility into agent reasoning
- **Safety**: Prevent destructive operations without confirmation

### Planned Features

#### 1. Key Decision Confirmation

**Trigger**: Before destructive or irreversible operations

**Tool**: `AskUserConfirmation(operation: str, context: dict) → yes/no/modify`

**Example**:
```
Agent: About to delete 500 files matching "*.tmp"
AskUserConfirmation(
    operation="delete_files",
    context={"pattern": "*.tmp", "count": 500, "size": "2.3GB"}
)
User: yes → Agent proceeds
User: no → Agent skips operation
User: modify → Agent asks for new pattern
```

#### 2. Interactive Debugging

**Trigger**: When errors occur or agent is uncertain

**Tool**: `RequestUserGuidance(problem: str, options: list) → user_choice`

**Example**:
```
Agent: Python script failed with "ModuleNotFoundError: pandas"
RequestUserGuidance(
    problem="Missing pandas library",
    options=[
        "Install pandas using pip",
        "Rewrite code without pandas",
        "Skip this step"
    ]
)
User: Install pandas → Agent runs pip install
```

#### 3. Intermediate Result Review

**Trigger**: After major steps in long-running tasks

**Tool**: `ShowIntermediateResult(result: str, next_step: str) → continue/adjust`

**Example**:
```
Agent: Completed data analysis, found 5 anomalies
ShowIntermediateResult(
    result="Anomaly summary: ...",
    next_step="Generate visualization of anomalies"
)
User: continue → Agent proceeds
User: adjust → Agent asks how to modify
```

### Architecture Pattern

```
User Input
    ↓
Dynamic Context Building (from Stage 2)
    ↓
API Call
    ↓
Decision Point:
  - If critical_operation → AskUserConfirmation → Wait
  - If error_occurred → RequestUserGuidance → Adjust
  - If major_milestone → ShowIntermediateResult → Review
    ↓
Tool Execution
    ↓
Loop
```

### Implementation Considerations

**Async Communication**:
- Agent pauses execution, waits for user input
- Timeout mechanism (e.g., 5 minutes)
- Queue system for multi-user scenarios

**State Management**:
- Save agent state before confirmation request
- Resume from exact point after user response
- Handle "cancel" scenario gracefully

**User Experience**:
- Clear, concise prompts
- Provide context for decisions
- Offer sensible default options

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
