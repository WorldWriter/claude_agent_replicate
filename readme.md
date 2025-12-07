# Claude Agent Replicate

> Progressive reproduction of Claude Code's agent architecture using Kimi API, demonstrating System Prompt-driven responsive agents from minimal foundation to advanced capabilities.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project Vision

**Goal**: Faithfully replicate Claude Code's agent architecture patterns while maintaining compatibility with Kimi (Moonshot) API.

**Approach**: Staged evolution mimicking Claude's core mechanisms:
- **Stage 1**: Reactive foundation (minimal agent with tool calling)
- **Stage 2**: System Prompt + Dynamic Context + Todo tracking
- **Stage 3**: Human-in-the-Loop interactions (planned)
- **Stage 4**: Self-evolution and learning (future)

**Philosophy**: Learn Claude's architectural excellence through hands-on implementation, not just reading documentation.

---

## Core Architecture Principles (from Claude)

### 1. Responsive Architecture
- **No predefined execution loops** (Plan→Execute→Reflect)
- **LLM decides next action** dynamically each turn
- **System Prompt teaches "how to think"**, not "what to do"

**Traditional Agent**:
```python
while not done:
    plan = agent.plan()      # Pre-generate complete plan
    for step in plan:
        execute(step)        # Execute predefined steps
    reflect()                # Separate reflection phase
```

**Claude-Style Agent** (This Project):
```python
for message in conversation:
    context = build_dynamic()     # Rebuild context each turn
    response = llm(
        system=workflow_prompt,   # "Planning" happens here!
        messages=context
    )
    if tool_use:
        execute_and_continue()
```

### 2. System Prompt-Driven Behavior
- Workflow guidance via comprehensive system prompts (~400 tokens)
- Dynamic context construction on every API call
- Environment awareness (time, workspace, turn number)

### 3. Todo Short-Term Memory
- Task tracking through system messages
- Progress visibility: [ ] pending, [→] in_progress, [✓] completed
- Self-management without external state files

---

## Implementation Stages

### Stage 1: Minimal Kimi Agent (Reactive Foundation)

**File**: [`minimal_kimi_agent.py`](minimal_kimi_agent.py) (423 lines)
**Status**: ✅ Production Ready

**Core Features**:
- Multi-turn conversation management
- Tool calling: ReadFile, WriteFile, RunCommand
- Workspace isolation and safety mechanisms
- Conversation logging (TXT + JSON)

**Architecture**:
```
User Input → API Call → Tool Execution → Loop
```

**Performance**: DA-Code test set 29.7% avg score, 20.3% success rate

**When to Use**: Simple to medium tasks, reliable execution, budget-conscious

**Example**:
```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("""
Read sales_data.csv and:
1. Calculate total sales by region
2. Identify top-performing product
3. Write results to summary.txt
""", max_turns=10)
```

---

### Stage 2: Dynamic Plan Agent (System Prompt + Context)

**File**: [`dynamic_plan_agent.py`](dynamic_plan_agent.py) (620 lines)
**Status**: ✅ Complete (2025-11-27)

**Key Innovations** (Claude Architecture Patterns):

**1. System Workflow Prompt** (~400 tokens)
- Core working principles (proactive tool usage, iterative execution)
- Todo management rules (when to create, status transitions)
- Thinking model (goal → info needed → action → completeness check)
- Tool usage guidelines

**2. Dynamic Context Building**
Reconstructs context on every API call:
```
[System Workflow Prompt]     ← Persistent guidance
[Environment Info]           ← Time, workspace, turn
[Conversation History]       ← User + assistant messages
[Todo State]                 ← Current task progress
```

**3. TodoUpdate Tool**
- Actions: `add`, `update_status`, `complete`
- Visual tracking: [ ] → [→] → [✓]
- Automatic task management

**4. Enhanced Logging**
- JSON logs include todos and turn count
- Full audit trail of planning and execution

**Architecture**:
```
User Input
    ↓
Build Dynamic Context (system prompts + env + history + todos)
    ↓
API Call
    ↓
Tool Execution (including TodoUpdate)
    ↓
Loop
```

**Performance Impact**: +550 tokens/call, but better completion rates

**When to Use**: Complex multi-step tasks requiring planning and tracking

**Example**:
```python
from dynamic_plan_agent import MinimalKimiAgent

agent = MinimalKimiAgent()  # Same class name, enhanced behavior!
result = agent.run("""
Analyze customer_data.csv:
1. Calculate customer lifetime value by segment
2. Identify top 10 customers
3. Create visualization showing trends
4. Write executive summary
""", max_turns=20)

# Agent will automatically:
# - Create Todo list for the 4 tasks
# - Track progress: [→] task_1, [ ] task_2, [ ] task_3, [ ] task_4
# - Update status as each completes
# - Save full todo history in logs
```

**Comparison**:
| Aspect | Stage 1 | Stage 2 |
|--------|---------|---------|
| Code Size | 423 lines | 620 lines |
| Tools | 3 | 4 (+TodoUpdate) |
| System Prompt | None | ~400 tokens |
| Context | Static | Dynamic |
| Task Memory | None | Todo tracking |
| Best For | Simple tasks | Complex multi-step tasks |

---

### Stage 3: Human-in-Loop Agent (Planned)

**File**: `human_loop_agent.py` (Future)
**Status**: 🔄 Planned (Q1 2026)

**Planned Features**:

**1. Key Decision Confirmation**
- Agent requests approval before destructive operations
- User can review and modify execution plan

**2. Interactive Debugging**
- When errors occur, agent explains issue and asks for guidance
- User can provide hints or alternative approaches

**3. Tools**:
- `AskUserConfirmation(operation, context)` → yes/no/modify
- `RequestUserGuidance(problem, options)` → user choice
- `ShowIntermediateResult(result, next_step)` → continue/adjust

**Example Flow**:
```python
# Agent: About to delete 500 files
AskUserConfirmation(operation="delete_files", context={...})
# User approves → Agent proceeds

# Agent: Script failed with ModuleNotFoundError
RequestUserGuidance(problem="Missing pandas", options=[...])
# User: "Install pandas" → Agent runs pip install
```

---

### Reference Implementation

**File**: [`claude_agent_pseudocode.py`](claude_agent_pseudocode.py) (527 lines)
**Purpose**: Educational reference showing Claude's internal patterns

**Key Insights**:
- Responsive loop (no pre-planning)
- System Prompt-driven workflow
- Todo short-term memory
- Dynamic context construction
- SubAgent pattern for context isolation

**Not for production** - intentionally simplified for learning.

---

## Project Structure

```
claude_agent_replicate/
├── minimal_kimi_agent.py          # Stage 1: Reactive foundation
├── dynamic_plan_agent.py          # Stage 2: System Prompt + Dynamic Context + Todo
├── human_loop_agent.py            # Stage 3: Human-in-the-Loop (future)
├── claude_agent_pseudocode.py     # Reference: Claude architecture patterns
│
├── test_dynamic_plan_agent.py     # Tests for Stage 2
│
├── agent_workspace/               # Isolated execution environment
│   ├── da-code/                   # DA-Code benchmark (500 tasks)
│   │   ├── da_code/
│   │   │   ├── source/            # Task data files
│   │   │   ├── gold/              # Standard answers
│   │   │   └── configs/eval/      # Train/val/test splits
│   │   └── da_agent/
│   │       └── evaluators/        # Official metrics
│   └── output_dir/                # Agent execution outputs
│
├── docs/
│   ├── AGENT_EVOLUTION.md         # Stage 1→2→3 evolution guide
│   ├── ARCHITECTURE_COMPARISON.md # Before/after technical comparison
│   ├── ARCHITECTURE.md            # Technical deep dive
│   ├── baseline_report.md         # DA-Code evaluation results
│   └── kimi_api.md                # API configuration notes
│
├── test/                          # DA-Code evaluation framework
│   ├── evaluate_results.py
│   ├── run_benchmark.py
│   └── dataset_tasks.json
│
├── examples/                      # Usage demos
├── logs/                          # Conversation logs (gitignored)
│
├── README.md                      # This file
├── README_CN.md                   # Chinese version
├── CLAUDE.md                      # Technical reference
├── requirements.txt               # Dependencies
└── .env.example                   # Environment template
```

---

## Key Differences from Claude Code

| Feature | Claude Code | This Project |
|---------|-------------|--------------|
| **API** | Anthropic Claude API | Moonshot Kimi API (OpenAI-compatible) |
| **System Prompts** | Separate `system` parameter | Injected in message array |
| **Message Format** | Anthropic format | OpenAI format |
| **Tools** | Native Claude tools | OpenAI function calling |
| **Language** | TypeScript/Python | Python only |
| **Scope** | Full IDE integration | Standalone agent framework |

**Why This Matters**: Understanding how to adapt Claude's architecture to different APIs teaches the core principles, not just the implementation details.

---

## Quick Start

### Prerequisites

- Python 3.8+
- Moonshot Kimi API key ([Get one here](https://platform.moonshot.cn/))
- (Optional) Anthropic API key for reference implementation

### Installation

```bash
# Clone repository
git clone <your-repo-url>
cd claude_agent_replicate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your MOONSHOT_API_KEY
```

### First Run (2 minutes)

```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run(
    "What is cloud computing? Explain in 3 sentences.",
    max_turns=5
)
print(result)
```

See [`docs/AGENT_EVOLUTION.md`](docs/AGENT_EVOLUTION.md) for detailed usage examples.

---

## Benchmark: DA-Code Evaluation

We use DA-Code (500 data analysis tasks) for objective evaluation.

**Stage 1 (Minimal Agent) - Baseline**:
- Test Set: 29.7% avg score, 20.3% success rate (12/59 tasks)
- **Strengths**: Data insights, simple analysis, file I/O
- **Weaknesses**: Visualization, multi-step planning (8+ steps), error recovery

**Stage 2 (Dynamic Plan Agent)**:
- Expected: Improved completion rate due to System Prompt guidance and Todo tracking
- Testing: In progress

**Philosophy**: Honest metrics over inflated claims. Baseline scores establish starting point for architectural improvements.

Detailed breakdown: [`docs/baseline_report.md`](docs/baseline_report.md)

---

## Running Evaluations

### Dataset Splits

| Dataset | Tasks | Purpose |
|---------|-------|---------|
| **Train** | 50 | Prompt engineering, strategy development |
| **Validation** | 50 | Hyperparameter tuning, validation |
| **Test** | 59 | Final benchmark (reported metrics) |

### Quick Test

```bash
# 5 representative tasks (~5 minutes)
python test/evaluate_results.py --dataset quick

# Full test set (59 tasks, ~1.5-2 hours)
python test/evaluate_results.py --dataset test
```

---

## Development Roadmap

- [x] **Stage 1**: Reactive foundation (Complete)
- [x] **Stage 2**: System Prompt + Dynamic Context + Todo (Complete)
- [ ] **Stage 3**: Human-in-the-Loop (Planned - Q1 2026)
- [ ] **Stage 4**: Self-evolution & Learning (Future)

---

## FAQ

**Q: Why "replicate" Claude when we have Kimi?**

A: Claude Code's architecture is highly effective for agent tasks. By replicating it with Kimi API, we:
- Learn the architectural patterns (transferable knowledge)
- Use a cost-effective API for experimentation
- Understand "why" Claude works, not just "how"

**Q: Can I use this with Claude API instead of Kimi?**

A: Yes! The `claude_agent_pseudocode.py` shows the pattern. Main changes:
1. Replace `OpenAI` client with Anthropic's `Anthropic` client
2. Use separate `system` parameter instead of message array injection
3. Adjust message format (Claude uses content blocks)
4. Keep the same tool definitions and execution logic

**Q: What's the difference between Stage 1 and Stage 2?**

A:
- **Stage 1 (Minimal)**: Reactive agent, no planning guidance, no task memory. Best for simple tasks.
- **Stage 2 (Dynamic Plan)**: Adds System Prompt (teaches "how to think"), Dynamic Context (environment awareness), Todo tracking (task memory). Best for complex multi-step tasks.

Both use the same class name (`MinimalKimiAgent`) for easy migration.

**Q: How do I know which stage to use?**

A:
- **1-2 steps**: Stage 1 (minimal)
- **3-7 steps**: Stage 2 (dynamic plan)
- **8+ steps or requires human oversight**: Stage 3 (future, human-in-loop)

**Q: Why remove the strategic-tactical pattern from this project?**

A: The project's focus shifted to pure Claude architecture replication. Strategic-tactical was an experimental pattern that diverged from Claude's approach. For Claude-style agents, System Prompt-driven responsive architecture is the core pattern.

**Q: Can I add custom tools?**

A: Absolutely! See `_get_tools()` method in agent files:
```python
def _get_tools(self):
    return [
        {"type": "function", "function": {
            "name": "MyCustomTool",
            "description": "What it does",
            "parameters": {...}
        }}
    ]

def _execute_tool(self, tool_name, tool_args):
    if tool_name == "MyCustomTool":
        return self._tool_my_custom(tool_args)
```

---

## References

- **Claude Code**: [Official Documentation](https://claude.ai/code)
- **DA-Code Benchmark**: [arXiv:2410.07331](https://arxiv.org/abs/2410.07331) - "DA-Code: Agent Data Science Code Generation Benchmark"
- **Moonshot Kimi**: [API Platform](https://platform.moonshot.cn/)
- **Anthropic Claude**: [Docs](https://docs.anthropic.com) - Agent patterns and tool use

---

## Technical Stack

**Core**:
- Python 3.8+
- OpenAI Python SDK (for Kimi API compatibility)
- python-dotenv (environment management)

**Agent Capabilities** (executed in workspace):
- **Data**: pandas, numpy
- **Visualization**: matplotlib, seaborn
- **Machine Learning**: scikit-learn, xgboost
- **Testing**: pytest

**APIs**:
- Moonshot Kimi (primary, OpenAI-compatible)
- Anthropic Claude (reference implementation only)

---

## Engineering Principles

- **Workspace Isolation**: All operations in `agent_workspace/`, preventing accidental impact on project files
- **Safety-First**: Command blacklist (prohibit `rm -rf`, `sudo`, etc.) + 60s timeout protection
- **Comprehensive Logging**: Dual-format (`.txt` + `.json`) for debugging and analysis
- **Benchmark Integration**: DA-Code evaluation for honest capability assessment
- **Progressive Enhancement**: Stage-by-stage capability building

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Anthropic for Claude agent architectural insights
- DA-Code benchmark team for comprehensive evaluation framework
- Moonshot AI for Kimi API access

---

**Project Goal**: Master Claude agent architecture through progressive, hands-on implementation.

**Last Updated**: 2025-11-27
