# Agent Architecture Comparison: Before vs After Optimization

## Overview

This document compares the architecture of `minimal_kimi_agent.py` before and after integrating Claude Agent patterns.

## Architecture Diagrams

### Before Optimization (Original)

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Append to messages[] list                       │
│              (Simple array accumulation)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Kimi API Call                              │
│                                                              │
│   client.chat.completions.create(                           │
│       messages=self.messages,  ← Static history             │
│       tools=[ReadFile, WriteFile, RunCommand]               │
│   )                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Process Response                                │
│   • Text → Task Complete                                    │
│   • Tool Calls → Execute Tools → Append Results             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Loop Again?  │
                  └──────┬───────┘
                         │
                    Yes  │  No
                    ◄────┴────► [Done]
```

**Characteristics:**
- ❌ No guidance on how to think
- ❌ No task awareness or tracking
- ❌ Static message history only
- ❌ No environmental context
- ✅ Simple and straightforward


### After Optimization (Claude Pattern)

```
┌─────────────────────────────────────────────────────────────┐
│                      User Input                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Append to messages[] list                       │
│              _current_turn++                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         Build Dynamic Context (Every Turn!)                  │
│                                                              │
│   full_messages = [                                         │
│       ┌──────────────────────────────────────────┐         │
│       │ 1. System Workflow Prompt                │         │
│       │    • Core working principles             │         │
│       │    • Todo management rules                │         │
│       │    • Thinking model                       │         │
│       │    • Tool usage guidelines                │         │
│       │    (~400 tokens)                          │         │
│       └──────────────────────────────────────────┘         │
│                                                              │
│       ┌──────────────────────────────────────────┐         │
│       │ 2. System Reminder: Environment          │         │
│       │    • Current time                         │         │
│       │    • Workspace path                       │         │
│       │    • Turn number                          │         │
│       │    • Available tools                      │         │
│       │    (~50 tokens)                           │         │
│       └──────────────────────────────────────────┘         │
│                                                              │
│       ┌──────────────────────────────────────────┐         │
│       │ 3. Conversation History                  │         │
│       │    self.messages (original history)      │         │
│       └──────────────────────────────────────────┘         │
│                                                              │
│       ┌──────────────────────────────────────────┐         │
│       │ 4. System Reminder: Todo State (if any)  │         │
│       │    [→] task_1: Read data                 │         │
│       │    [ ] task_2: Analyze trends            │         │
│       │    [ ] task_3: Generate report           │         │
│       │    (~100 tokens)                          │         │
│       └──────────────────────────────────────────┘         │
│   ]                                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Kimi API Call                              │
│                                                              │
│   client.chat.completions.create(                           │
│       messages=full_messages,  ← Dynamic context!           │
│       tools=[ReadFile, WriteFile, RunCommand, TodoUpdate]   │
│   )                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Process Response                                │
│   • Text → Task Complete                                    │
│   • Tool Calls → Execute Tools (including TodoUpdate)       │
│                → Update self.todos state                     │
│                → Append Results                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Loop Again?  │
                  └──────┬───────┘
                         │
                    Yes  │  No
                    ◄────┴────► [Done + Save Logs with Todos]
```

**Characteristics:**
- ✅ System prompt guides thinking
- ✅ Task awareness via Todo tracking
- ✅ Dynamic context on every turn
- ✅ Environmental awareness (time, turn, workspace)
- ✅ Self-managing (Agent decides when to use Todo)

## Key Architectural Changes

### 1. Message Construction

**Before:**
```python
def _call_kimi(self):
    response = self.client.chat.completions.create(
        messages=self.messages,  # Direct, static
        tools=self._get_tools()
    )
```

**After:**
```python
def _call_kimi(self):
    full_messages = self._build_dynamic_messages()  # Dynamic!
    response = self.client.chat.completions.create(
        messages=full_messages,  # Includes system prompts + context
        tools=self._get_tools()
    )
```

### 2. Context Awareness

**Before:**
- No awareness of environment
- No guidance on decision making
- Simple reactive loop

**After:**
- Knows current time, workspace, turn number
- Has explicit working principles and thinking model
- Can track multi-step tasks via Todo
- Makes informed decisions based on context

### 3. Tool Ecosystem

**Before:**
```
ReadFile → WriteFile → RunCommand
```

**After:**
```
ReadFile → WriteFile → RunCommand → TodoUpdate
                                         ↓
                                   Task Tracking
                                   Short-term Memory
```

### 4. Decision Making Flow

**Before:**
```
User: "Do complex task"
   ↓
Agent: [Calls tools randomly]
   ↓
[May lose track of progress]
   ↓
[May forget steps]
```

**After:**
```
User: "Do complex task"
   ↓
Agent reads System Workflow Prompt
   ↓
Agent: "This is 3+ steps → Create Todo"
   ↓
TodoUpdate: add task_1, task_2, task_3
   ↓
Execute task_1 → TodoUpdate: complete task_1
   ↓
Execute task_2 → TodoUpdate: complete task_2
   ↓
Execute task_3 → TodoUpdate: complete task_3
   ↓
[All tasks tracked and completed]
```

## Code Structure Comparison

### Initialization

**Before:**
```python
def __init__(self):
    self.client = OpenAI(...)
    self.messages = []
    self.model = "kimi-k2-turbo-preview"
    self.workspace = "agent_workspace"
```

**After:**
```python
def __init__(self):
    self.client = OpenAI(...)
    self.messages = []
    self.todos = {"tasks": []}        # NEW
    self._current_turn = 0            # NEW
    self.model = "kimi-k2-turbo-preview"
    self.workspace = "agent_workspace"
```

### Main Loop

**Before:**
```python
def run(self, user_input):
    self.messages.append({"role": "user", "content": user_input})

    for turn in range(max_turns):
        response = self._call_kimi()
        should_stop = self._process_response(response)
        if should_stop:
            break
```

**After:**
```python
def run(self, user_input):
    self.messages.append({"role": "user", "content": user_input})

    for turn in range(max_turns):
        self._current_turn = turn + 1  # NEW: Track turn
        response = self._call_kimi()   # Uses dynamic context
        should_stop = self._process_response(response)
        if should_stop:
            break
```

## Performance Characteristics

### Token Usage

| Component | Before | After | Delta |
|-----------|--------|-------|-------|
| System Prompt | 0 | ~400 | +400 |
| Environment Info | 0 | ~50 | +50 |
| Todo State | 0 | ~100 | +100 |
| Message History | Variable | Variable | 0 |
| **Total Overhead** | **0** | **~550** | **+550** |

### Expected Outcomes

| Metric | Before | After | Reason |
|--------|--------|-------|--------|
| Tasks Completed Successfully | Baseline | ↑ Higher | Better guidance |
| Average Turns per Task | Baseline | ↓ Lower | Less confusion |
| Wasted Tool Calls | Baseline | ↓ Lower | Clear principles |
| Multi-step Task Tracking | ❌ None | ✅ Complete | Todo mechanism |
| Total Tokens per Session | Baseline | ~= Similar | Fewer wasted turns offset overhead |

## Logging Enhancement

### Before

**TXT Log:**
```
用户: Task request
助手: Response
工具结果: Result
```

**JSON Log:**
```json
[
  {"role": "user", "content": "..."},
  {"role": "assistant", "content": "...", "tool_calls": [...]}
]
```

### After

**TXT Log:** (Same format)

**JSON Log:**
```json
{
  "messages": [...],
  "todos": {
    "tasks": [
      {
        "id": "task_1",
        "description": "Read data",
        "status": "completed",
        "created_at": "2025-11-27T14:23:15"
      }
    ]
  },
  "timestamp": "2025-11-27_14-23-15",
  "turns": 5
}
```

## Real-World Example Comparison

### Scenario: "Analyze GCP data and generate report"

**Before (Potential Issues):**
```
Turn 1: Agent tries to read entire file → Truncated
Turn 2: Agent confused about what to do next
Turn 3: Agent asks user what to do
Turn 4: User clarifies
Turn 5: Agent starts analysis
Turn 6: Agent forgets to generate report
Turn 7: User reminds about report
Turn 8: Agent generates report
```
**Total: 8 turns, requires user intervention**

**After (Optimized Flow):**
```
Turn 1: System prompt guides → Create Todo (5 tasks)
        TodoUpdate: Add task_1 (read data), task_2 (analyze),
                    task_3 (identify top resources), task_4 (plot),
                    task_5 (generate report)
Turn 2: Read file → Sees truncation → Writes Python script
Turn 3: Run script → TodoUpdate: complete task_1
Turn 4: Analyze trends → TodoUpdate: complete task_2
Turn 5: Identify top resources → TodoUpdate: complete task_3
Turn 6: Plot graphs → TodoUpdate: complete task_4
Turn 7: Generate report → TodoUpdate: complete task_5
        All tasks completed!
```
**Total: 7 turns, fully autonomous, all steps tracked**

## Conclusion

The optimization successfully adapts Claude's responsive, System Prompt-driven architecture to work with Kimi's OpenAI-compatible API format while:

✅ **Maintaining Compatibility**: All existing code works unchanged
✅ **Adding Intelligence**: System prompts guide better decisions
✅ **Enabling Memory**: Todo tracking prevents lost progress
✅ **Improving Efficiency**: Fewer wasted turns despite token overhead
✅ **Enhancing Debuggability**: Complete Todo state in logs

The architecture is now **proactive** (guided by principles) rather than **reactive** (responding blindly), making it significantly more capable for complex, multi-step tasks.
