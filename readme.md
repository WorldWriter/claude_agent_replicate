# Agent Architecture: Claude-Inspired Strategic-Tactical Pattern

> Exploring responsive agent architectures through practical implementation, combining Claude's System Prompt-driven philosophy with strategic-tactical separation for complex task execution.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Core Architecture Philosophy

This project explores how to build AI agents that think like Claude: **responsive, LLM-driven decision-making** rather than hardcoded execution loops. The core innovation combines Claude's architectural principles with a strategic-tactical separation pattern to handle complex multi-step tasks.

---

### Two Key Architectural Innovations

**1. Responsive Architecture**

**The Problem**: Traditional agents use fixed execution cycles—regardless of task complexity, they must go through the complete Plan→Execute→Reflect→Loop flow. This leads to inefficiency for simple tasks and inflexibility for complex ones.

**The Innovation**: Let the LLM autonomously decide the next action at each moment, without predefined execution paths.

**Implementation Mechanism**: Use System Prompts to teach the agent "how to think" (when to plan? when to execute? when to reflect?), rather than hardcoding "what to do" (step 1: plan, step 2: execute...) in code.

**Execution Flow Comparison**:
```
Traditional Agent (Fixed Loop):
Plan → Execute → Reflect → Update Plan → Loop
↓ Issues: Wasted resources on simple tasks, rigid adaptation for complex tasks

Responsive Agent (Dynamic Decision):
User Message → LLM Decides → [Call Tools if needed] → Response → Continue
↓ Benefits: Direct execution for simple tasks, natural planning trigger for complex tasks
```

**Key Insight**: Code defines the agent's architectural capabilities (tools, memory, context). System Prompt defines the agent's behavioral patterns (decision-making logic). Transferring control to the LLM achieves higher adaptability.

---

**2. Strategic-Tactical Separation Pattern**

**The Problem**: Complex tasks face two challenges—① Context explosion (long history exhausts tokens); ② Planning-execution confusion (strategic thinking mixed with operational details, degrading decision quality).

**The Innovation**: Achieve hierarchical separation through **single class + dual modes**, without building two separate agent classes.

**Architecture Design**:
```
PlanKimiAgent(mode="strategic")  ←─ User interaction entry point
    ↓ Responsibilities:
    - Explore workspace, understand resource distribution
    - Decompose tasks into 3-7 step subtasks
    - Create and maintain high-level plans
    - Decide when to delegate to tactical layer
    - Request user confirmation for critical decisions
    ↓
    └─→ DelegateToTactical()
        ↓ Create new instance
        PlanKimiAgent(mode="tactical")  ←─ Isolated context
            ↓ Responsibilities:
            - Focus on executing single subtask (3-7 steps)
            - No high-level planning
            - Report blockers when encountered
            - Return result summary upon completion
```

**Context Management Strategy**:
```
Strategic Layer Context (~8K tokens):
- Workspace panorama (file tree, dataset overview)
- Current plan summary (goals, steps, progress)
- Sliding window of history (recent 10 messages)

Tactical Layer Context (<500 tokens):
- Subtask description (objective + success criteria)
- Minimal necessary context (relevant file paths, data samples)
- No history (fresh conversation)
```

**Key Insight**: Through differentiated System Prompt guidance (strategic prompts emphasize planning, tactical prompts emphasize execution) + SubAgent pattern (create new instances to isolate context), achieve hierarchical separation within a single codebase. Avoid maintaining two codebases while gaining clear responsibility division.

---

### Architecture Evolution: Progressive Understanding

This project contains three implementations, demonstrating progressive deepening of agent architecture understanding:

**Stage 1 - MinimalKimiAgent (Responsive Foundation)**
- Core mechanism: LLM-driven decision loop, multi-turn conversation management
- Toolset: ReadFile, WriteFile, RunCommand (3 basic tools)
- Production features: Workspace isolation, command blacklist, timeout protection, dual-format logging

**Stage 2 - PlanKimiAgent (Strategic-Tactical Architecture)**
- Core mechanism: Single-class dual-mode (strategic/tactical mode)
- System evolution: System Prompt-driven behavior differentiation, dynamic context building
- Tool expansion: 9 tools (+planning tools, +strategic tools, basic tools)
- Architecture pattern: SubAgent pattern for context isolation

**Stage 3/4 - Future Directions**
- Stage 3: Memory & Learning (learn from successful patterns, automatic prompt optimization)
- Stage 4: Self-Evolution (self-evaluation, multi-iteration improvement, automatic knowledge expansion)

---

### Engineering Principles

- **Workspace Isolation**: All agent operations confined to `agent_workspace/` directory, preventing accidental impact on project files
- **Safety-First**: Command blacklist (prohibit `rm -rf`, `sudo`, etc.) + 60-second timeout protection
- **Comprehensive Logging**: Dual-format recording (human-readable `.txt` + structured `.json`) for debugging and analysis
- **Benchmark Integration**: DA-Code evaluation framework (500 real-world data analysis tasks) for honest capability assessment

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Moonshot Kimi API key ([Get one here](https://platform.moonshot.cn/))
- (Optional) Anthropic API key for SimpleClaudeAgent reference implementation

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd agent_architecture

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your MOONSHOT_API_KEY
```

### First Run (2 minutes)

```python
from minimal_kimi_agent import MinimalKimiAgent

# Create agent instance
agent = MinimalKimiAgent()

# Run a simple task
result = agent.run(
    "What is cloud computing? Explain in 3 sentences.",
    max_turns=5
)

print(result)
```

See `examples/` directory for more comprehensive demos including data analysis and visualization tasks.

## Architecture

### Agent Execution Loop

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Send to API             │
│ (messages + tool defs)  │
└────────┬────────────────┘
         │
         ▼
    ┌────────────┐
    │ API Output │
    └────┬───────┘
         │
    ┌────▼──────────────┐
    │ Tool calls?       │
    └────┬──────┬───────┘
    Yes  │      │ No
    ┌────▼───┐  │
    │Execute │  │
    │ Tools  │  │
    └────┬───┘  │
         │      │
    ┌────▼──────▼──────┐
    │Add to History    │
    └────┬─────────────┘
         │
         └──► Continue or Return Response
```

### Traditional vs Claude-Style Agents

| Aspect | Traditional Agent | Claude-Style Agent (This Project) |
|--------|-------------------|----------------------------------|
| **Planning** | Pre-defined steps | Dynamic per turn |
| **Memory** | State-based | Message history |
| **Decision Making** | Rule-based | LLM-driven |
| **Iteration** | Fixed cycle (Plan→Execute→Reflect) | Responsive loop (Message→Tools→Continue) |
| **Adaptability** | Low (follows plan) | High (adjusts to results) |

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for detailed technical breakdown.

## Implementation Details

### MinimalKimiAgent (Stage 1) - Production Ready

**File**: [`minimal_kimi_agent.py`](minimal_kimi_agent.py) (423 lines)

The foundation implementation demonstrating core agent mechanics with production-grade safety and logging.

**Features**:
- **Multi-turn conversation**: Full message history management, supports 16+ turn interactions
- **Three tools**: ReadFile (10K char limit), WriteFile, RunCommand (60s timeout)
- **Workspace isolation**: All operations in `agent_workspace/`, paths automatically resolved
- **Safety mechanisms**: Command blacklist, timeouts, file size limits
- **Automatic logging**: Dual-format conversation logs (`.txt` + `.json`)
- **Error handling**: Graceful degradation with informative messages

**When to use**: Production deployment, reliable tool calling, budget-conscious scenarios

**Example**:
```python
agent = MinimalKimiAgent()
result = agent.run("""
Read the CSV file sales_data.csv and:
1. Calculate total sales by region
2. Identify the top-performing product
3. Write results to summary.txt
""", max_turns=10)
```

**Performance**: DA-Code test set 29.7% avg score / 20.3% success rate

---

### PlanKimiAgent (Stage 2) - Strategic-Tactical Architecture

**File**: [`plan_kimi_agent.py`](plan_kimi_agent.py) (919 lines)

Implements Claude's responsive philosophy with strategic-tactical separation for complex multi-step tasks.

**Core Architecture**:
- **Single Class, Dual Modes**: Same `PlanKimiAgent` class operates in "strategic" or "tactical" mode
- **System Prompt-Driven**: Behavior controlled by mode-specific System Prompts, not code logic
- **Dynamic Context Building**: Constructs context per turn (workspace snapshot + plan + sliding window)
- **SubAgent Pattern**: Strategic layer delegates to tactical instances for focused execution

**Nine Tools** (filtered by mode):
- **Planning Tools** (strategic only): CreatePlan, UpdatePlan, ReadPlan
- **Execution Tools** (both modes): ReadFile, WriteFile, RunCommand
- **Strategic Tools** (strategic only): ExploreWorkspace, DelegateToTactical, GetUserConfirmation

**Example - Strategic-Tactical Interaction**:
```python
# Strategic layer: High-level planning
strategic_agent = PlanKimiAgent(mode="strategic")
result = strategic_agent.run("""
Analyze customer_data.csv:
1. Calculate customer lifetime value by segment
2. Identify top 10 customers
3. Create visualization showing trends
4. Write executive summary
""", max_turns=30)

# Internally, strategic agent might:
# 1. Call ExploreWorkspace() to understand files
# 2. Call CreatePlan() to structure approach
# 3. Call DelegateToTactical() for step 1:
#    - Creates tactical agent with compressed context
#    - Tactical executes: ReadFile → RunCommand (pandas) → WriteFile
#    - Returns result summary to strategic
# 4. Continue with steps 2-4, delegating as needed
# 5. Call GetUserConfirmation() before final output
```

**When to use**: Complex multi-step tasks requiring both high-level planning and focused execution.

---

### SimpleClaudeAgent - Reference Architecture

**File**: [`claude_agent_pseudocode.py`](claude_agent_pseudocode.py) (527 lines)

Educational implementation demonstrating Claude's architectural patterns, not for production use.

**Architectural Insights**:
- **Responsive Loop**: No pre-planning, decisions made dynamically each turn
- **System Prompt-Driven**: Workflow controlled by evolving system prompts
- **Todo Short-Term Memory**: Task tracking through system messages
- **Dynamic Context Construction**: Each turn builds context from history
- **Tool Variety**: ReadFile, WriteFile, BashCommand, TodoUpdate, SubAgent

**ASCII Architecture Comparison** (from code comments):
```
Traditional:           Claude-Style:
Plan()                 User Input
  ↓                        ↓
Execute()              API Call + Dynamic Context
  ↓                        ↓
Reflect()              Response (text or tool calls)
  ↓                        ↓
Update Plan            Execute tools (if needed)
  ↓                        ↓
Loop                   Add to history → Loop
```

**When to use**: Understanding Claude agent internals, architectural reference, education

**Note**: Intentionally simplified for clarity - missing production safety checks

## Benchmark: Honest Assessment

We use DA-Code (500 data analysis tasks) for objective evaluation. Current baseline with MinimalKimiAgent:

**Test Set Results** (59 complex tasks): 29.7% avg score, 20.3% success rate (12/59 complete)

**What works well**:
- Data insight extraction (query formulation, reasoning about structured data)
- Simple statistical analysis
- File I/O and basic data manipulation

**What needs improvement**:
- Visualization (matplotlib/seaborn syntax, plot configuration)
- Multi-step planning for complex tasks (8+ steps)
- Error recovery when initial approach fails

**Learning approach**: The project emphasizes honest metrics over inflated claims. Baseline scores establish starting point for architectural improvements in Stages 2-4.

Detailed breakdown available in `docs/baseline_report.md`.

## Project Structure

```
agent_architecture/
├── minimal_kimi_agent.py          # Stage 1: Responsive foundation (423 lines)
├── plan_kimi_agent.py              # Stage 2: Strategic-tactical (919 lines)
├── claude_agent_pseudocode.py      # Reference: Claude patterns (527 lines)
├── test_strategic_tactical.py      # Tests for Stage 2 architecture
│
├── agent_workspace/                # Isolated execution environment
│   ├── da-code/                    # DA-Code benchmark (500 tasks)
│   │   ├── da_code/
│   │   │   ├── source/             # Task data files (2.1GB, download separately)
│   │   │   ├── gold/               # Standard answers (59 tasks)
│   │   │   └── configs/eval/       # Train/val/test splits
│   │   └── da_agent/
│   │       └── evaluators/         # Official evaluation metrics
│   └── output_dir/                 # Agent execution outputs
│
├── test/                           # Evaluation framework
│   ├── test_dacode.py              # Agent testing harness
│   ├── evaluate_dacode_official.py # Official DA-Code metrics
│   ├── dataset_tasks.json          # Test set configuration
│   └── create_train_val_split.py   # Dataset split generation
│
├── docs/                           # Documentation
│   ├── ARCHITECTURE.md             # Technical deep dive
│   ├── dataset_split_report.md     # Dataset analysis
│   └── kimi_api.md                 # API configuration notes
│
├── examples/                       # Runnable demos
│   ├── 1_basic_qa.py               # Simple Q&A example
│   ├── 2_data_analysis.py          # Multi-step analysis
│   └── 3_visualization.py          # Plotting demo
│
├── logs/                           # Conversation logs (gitignored)
├── CLAUDE.md                       # Detailed technical reference
├── README.md                       # This file
├── requirements.txt                # Python dependencies
├── LICENSE                         # MIT License
└── .env.example                    # Environment template
```

## Running Evaluations

The project includes integration with the official DA-Code benchmark evaluation framework.

### Dataset Splits

| Dataset | Tasks | Config File | Purpose |
|---------|-------|-------------|---------|
| **Train** | 50 | `configs/eval/eval_train.jsonl` | Prompt engineering, strategy development |
| **Validation** | 50 | `configs/eval/eval_val.jsonl` | Hyperparameter tuning, validation |
| **Test** | 59 | `configs/eval/eval_baseline.jsonl` | Final benchmark (reported metrics) |

Splits created using stratified sampling to balance difficulty levels (seed=42 for reproducibility).

### Running Tests

```bash
# Quick validation (5 representative tasks, ~5 minutes)
python test/evaluate_dacode_official.py --dataset quick

# Full test set (59 tasks, ~1.5-2 hours)
python test/evaluate_dacode_official.py --dataset test

# Training set (50 tasks, for development)
python test/evaluate_dacode_official.py --dataset train

# Validation set (50 tasks, for tuning)
python test/evaluate_dacode_official.py --dataset val
```

Results saved in `logs/` with detailed JSON analytics and per-task breakdowns.

## Common Patterns

### Data Analysis Task
```python
from minimal_kimi_agent import MinimalKimiAgent

agent = MinimalKimiAgent()
result = agent.run("""
Analyze the CSV file monthly_sales.csv:
1. Load and explore the data structure
2. Calculate summary statistics for each region
3. Identify the top 3 products by revenue
4. Write findings to analysis_report.txt
""", max_turns=15)
```

### Visualization Task
```python
agent = MinimalKimiAgent()
result = agent.run("""
Create a visualization from customer_data.csv:
1. Read the CSV file
2. Create a bar chart showing sales by category
3. Add proper labels and title
4. Save as 'sales_by_category.png'
Use matplotlib or seaborn.
""", max_turns=15)
```

### Machine Learning Task
```python
from plan_kimi_agent import PlanKimiAgent  # Better for complex tasks

agent = PlanKimiAgent()
result = agent.run("""
Build a classification model:
1. Load train.csv and test.csv
2. Preprocess data (handle missing values, encode categories)
3. Train a Random Forest classifier
4. Evaluate on test set
5. Save predictions to predictions.csv
""", max_turns=30)
```

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
- Moonshot Kimi (primary, via OpenAI-compatible interface)
- Anthropic Claude (reference implementation only)

## Key Design Decisions

### Why Responsive Architecture Over Fixed Cycles?

**Traditional agents hardcode the workflow**:
- Every task goes through: Plan → Execute → Reflect → Update
- Inefficient for simple tasks (unnecessary planning overhead)
- Rigid for complex tasks (can't adapt mid-execution)

**Responsive architecture trusts the LLM**:
- System Prompt teaches decision-making patterns
- LLM decides: "Do I need to plan?" "Should I execute now?" "Is reflection needed?"
- Simple tasks execute immediately; complex tasks trigger planning naturally
- Adapts to unexpected results without code changes

**Result**: Same agent handles "What's 2+2?" and "Build ML pipeline" efficiently.

### Why Mode Parameter Over Separate Classes?

**Could have built**: `StrategicAgent` and `TacticalAgent` as separate classes.

**Chose instead**: Single `PlanKimiAgent(mode="strategic"|"tactical")`.

**Rationale**:
- **Code reuse**: 80% of logic is identical (tool execution, message handling, logging)
- **Simpler SubAgent creation**: Just `PlanKimiAgent(mode="tactical")` instead of importing new class
- **Unified interface**: Users learn one API, mode is implementation detail
- **Easier testing**: Test mode switching logic, not two separate codebases

**The separation happens in System Prompts, not code structure.**

### Why Workspace Isolation?

All agent operations restricted to `agent_workspace/`:
- **Safety**: Prevents accidental corruption of project files
- **Clarity**: Explicit boundary between agent code and execution environment
- **Testing**: Easy cleanup and reset between runs
- **Path Resolution**: Relative paths automatically resolved to workspace

### Why DA-Code Benchmark?

- **Real-World Tasks**: Actual data analysis problems, not toy examples
- **Comprehensive**: 500 tasks across 7 categories with varying difficulty
- **Official Metrics**: Standardized evaluation for fair comparison
- **Educational**: Honest assessment reveals areas for improvement

## FAQ

**Q: Can I use this with Claude instead of Kimi?**

A: Yes! The `SimpleClaudeAgent` shows the pattern. To create a production Claude version:
1. Replace `OpenAI` client with Anthropic's `Anthropic` client
2. Adjust message format (Claude uses slightly different format)
3. Keep the same tool definitions and execution logic

**Q: How do I improve the agent's performance?**

A: Iterative development approach:
1. Start with training set (50 tasks), identify failure patterns
2. Refine system prompts and tool usage
3. Test on validation set (50 tasks) to avoid overfitting
4. Final benchmark on test set (59 tasks)

**Q: Why is visualization accuracy 0%?**

A: Current agent struggles with matplotlib syntax and plot configuration. Planned improvements:
- Add visualization examples to system prompt
- Create specialized tool for common plot types
- Improve error messages for debugging plot code

**Q: Can I add custom tools?**

A: Absolutely! See `_get_tools()` method in agent files:
1. Define tool schema (name, description, parameters)
2. Add handler method (e.g., `_execute_new_tool()`)
3. Register in tool dispatcher

**Q: What's the difference between MinimalKimiAgent and PlanKimiAgent?**

A:
- **MinimalKimiAgent**: Single responsive loop, no strategic-tactical separation. Best for simple-to-medium tasks where the LLM can handle everything in one context.
- **PlanKimiAgent**: Adds strategic-tactical separation via System Prompt guidance and SubAgent pattern. Best for complex tasks requiring high-level planning + focused execution with context management.

**Q: When should I use strategic vs tactical mode?**

A: You typically don't choose directly. Use `PlanKimiAgent(mode="strategic")` for your main task. The strategic layer will automatically create tactical SubAgents when needed via `DelegateToTactical()`. Only use `mode="tactical"` directly if you're testing tactical execution in isolation.

## Development Roadmap

The project follows a staged approach to understanding agent architectures:

- [x] **Stage 1: Responsive Foundation** (Complete)
  - Implemented Claude's responsive loop architecture
  - Tool calling with multi-turn conversation
  - Production safety mechanisms (workspace isolation, command blacklist)
  - Baseline DA-Code evaluation for honest assessment

- [x] **Stage 2: Strategic-Tactical Separation** (Complete)
  - Single-class, dual-mode architecture (`mode="strategic"|"tactical"`)
  - System Prompt-driven behavior differentiation
  - Dynamic context building (workspace snapshot + plan + sliding window)
  - SubAgent pattern for context-isolated execution
  - Nine tools with mode-based filtering

- [ ] **Stage 3: Memory & Learning** (Planned)
  - Learn from successful execution patterns across tasks
  - Automatic System Prompt optimization based on error analysis
  - Tool usage pattern recognition and refinement
  - Cross-task knowledge transfer

- [ ] **Stage 4: Self-Evolution** (Planned)
  - Agent evaluates own performance without human feedback
  - Multi-epoch prompt refinement using DA-Code train/val sets
  - Automatic tool knowledge expansion from documentation
  - Meta-learning: agent improves how it learns

## References

- **DA-Code Benchmark**: [arXiv:2410.07331](https://arxiv.org/abs/2410.07331) - "DA-Code: Agent Data Science Code Generation Benchmark"
- **Claude Documentation**: [Anthropic Docs](https://docs.anthropic.com) - Agent patterns and tool use
- **Moonshot AI**: [Platform](https://platform.moonshot.cn/) - Kimi API documentation

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- DA-Code benchmark team for the comprehensive evaluation framework
- Anthropic for Claude agent architectural insights
- Moonshot AI for Kimi API access

---

**Built with focus on**: Clean architecture, honest metrics, continuous improvement

**Last Updated**: 2025-11-26
