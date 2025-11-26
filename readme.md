# Agent Architecture: Exploring AI Agent Patterns

> Multi-stage AI agent implementations exploring Claude-like patterns using Moonshot Kimi API. Includes DA-Code benchmark integration demonstrating real-world problem-solving capabilities.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This project explores different agent architecture patterns through practical implementation, progressing from a minimal viable agent to sophisticated planning-capable systems. The core goal is to understand and replicate Claude-style agent behavior while balancing user experience with task accuracy.

**Key Achievement**: Integrated with the DA-Code benchmark (500 data analysis tasks), achieving a 29.7% avg score / 20.3% success rate on complex multi-step problems, with a clear roadmap for improvement through architectural iterations.

The project demonstrates three levels of agent sophistication:
- **MinimalKimiAgent** (Stage 1): Production-ready foundation with tool calling and multi-turn conversation
- **PlanKimiAgent** (Stage 2): Advanced planning with adaptive execution
- **SimpleClaudeAgent** (Reference): Educational implementation showing Claude's architectural patterns

## Three Core Strengths

### 1. Agent Architecture Understanding

Demonstrates deep comprehension of different agent patterns and their trade-offs:

- **Traditional vs Claude-Style**: Compares pre-planned execution loops with responsive, LLM-driven decision-making
- **Progressive Complexity**: Three implementations showing architectural evolution (Minimal → Planning → Reference)
- **Tool Integration**: Clean abstraction of tool calling (ReadFile, WriteFile, RunCommand) with safety mechanisms
- **Multi-Turn Reasoning**: Proper conversation history management supporting 16+ turn interactions
- **1400+ Lines of Production Python**: Well-documented, type-hinted code demonstrating professional coding practices

### 2. Engineering Best Practices

Showcases production-grade software engineering:

- **Safety-First Design**: Command blacklist preventing destructive operations (`rm -rf`, `sudo`, `shutdown`)
- **Comprehensive Logging**: Dual-format conversation logs (human-readable `.txt` + structured `.json`)
- **Workspace Isolation**: All agent operations confined to `agent_workspace/` preventing accidental file corruption
- **DA-Code Benchmark Integration**: Official evaluation framework with 500 tasks across 7 categories
- **Dataset Methodology**: Stratified train/val/test splits (50/50/59) with balanced difficulty distribution
- **Timeout Protection**: 60-second execution limits preventing infinite loops
- **Error Handling**: Graceful degradation with informative error messages

### 3. Problem-Solving Ability

Demonstrates honest assessment of capabilities with clear improvement strategy:

| Metric | Value | Context |
|--------|-------|---------|
| **Avg Score** | 29.7% | DA-Code test set (59 complex tasks) |
| **Success Rate** | 20.3% (12/59) | Complete task success |
| **Easy Tasks** | 100% (1/1) | Simple workflows fully solved |
| **Medium Tasks** | 57% (8/14) | 4-7 step problems mostly working |
| **Hard Tasks** | 7% (3/44) | 8+ step problems, main improvement area |

**Key Insights**:
- Data Insight category: 100% success (strongest area)
- Visualization tasks: 0% success → primary improvement opportunity
- Hard task performance: 7% → needs better planning (Stage 2 focus)

**Improvement Roadmap**:
- Stage 2 (Plan Agent): Target 35% avg score through adaptive planning
- Stage 3 (Memory & Learning): Target 50%+ through prompt optimization
- Stage 4 (Auto-Evolution): Target 70%+ through self-improvement

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

## Three Agent Implementations

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

### PlanKimiAgent (Stage 2) - Advanced Planning

**File**: [`plan_kimi_agent.py`](plan_kimi_agent.py) (654 lines)

Adds dynamic planning capability with persistent plan management and adaptive execution.

**Features**:
- **Plan Creation**: Generates `plan.md` at task start with structured steps
- **Adaptive Execution**: Adjusts plan based on intermediate results
- **Plan Persistence**: Human-readable markdown plans with status tracking
- **Step Management**: Create, update, skip, complete, log steps dynamically
- **Extended Turns**: 30+ turn capacity for complex tasks
- **All Stage 1 Features**: Safety, logging, workspace isolation

**Plan Tools**:
- `CreatePlan`: Initialize structured plan file
- `UpdatePlan`: Modify plan based on execution progress
- `ReadPlan`: Review current plan state

**When to use**: Complex multi-step tasks, scenarios requiring plan visualization, adaptive workflows

**Example Plan File**:
```markdown
# Task: Analyze sales data and create visualization

## Steps
- [x] Read sales_data.csv
- [~] Calculate regional statistics
- [ ] Create matplotlib visualization
- [ ] Save to output/sales_chart.png

## Execution Log
[2025-01-26 10:30] Step 1 complete - found 1000 records
[2025-01-26 10:32] Step 2 in progress - calculating...
```

**Status**: In development, targeting 35% avg score on DA-Code tasks

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

## Benchmark Performance

### DA-Code Test Set (59 tasks)

Comprehensive evaluation on complex data analysis tasks requiring multi-step reasoning, data manipulation, visualization, and machine learning.

| Difficulty | Count | Avg Score | Success Rate | Status |
|------------|-------|-----------|--------------|--------|
| **Easy** (1-3 steps) | 1 | 100% | 100% (1/1) | ✓ Complete |
| **Medium** (4-7 steps) | 14 | 57% | 57% (8/14) | Working |
| **Hard** (8+ steps) | 44 | 18% | 7% (3/44) | In Progress |
| **Overall** | **59** | **29.7%** | **20.3% (12/59)** | **Baseline** |

### Performance by Category

| Category | Tasks | Avg Score | Success Rate | Key Challenge |
|----------|-------|-----------|--------------|---------------|
| Data Insight | 4 | 100% | 100% (4/4) | ✓ Solved |
| Data Manipulation | 9 | 11% | 0% (0/9) | Complex pandas |
| Data Visualization | 11 | 0% | 0% (0/11) | **Primary gap** |
| Machine Learning | 14 | 21% | 14% (2/14) | Model selection |
| Statistical Analysis | 9 | 44% | 33% (3/9) | Good progress |
| NLP | 7 | 29% | 14% (1/7) | Text processing |
| GCP Specific | 5 | 40% | 40% (2/5) | Cloud billing |

### Key Insights

1. **Data Insight Excellence**: 100% success (4/4 tasks)
   - Agent excels at query formulation and insight extraction
   - Demonstrates strong reasoning for structured questions

2. **Visualization Gap**: 0% success (0/11 tasks)
   - Agent struggles with matplotlib/seaborn syntax
   - Plan to add visual tool knowledge in Stage 2
   - Will create specialized visualization examples

3. **Hard Task Challenge**: Only 7% success rate (3/44)
   - Multi-step planning needs improvement
   - PlanKimiAgent (Stage 2) specifically targets this
   - Dynamic planning should improve task breakdown

4. **Partial Credit System**: 29.7% avg score vs 20.3% success
   - Many tasks partially solved (some steps correct)
   - Shows agent understands tasks but execution falters
   - Error recovery is key improvement area

## Project Structure

```
agent_architecture/
├── minimal_kimi_agent.py          # Stage 1: Production agent (423 lines)
├── plan_kimi_agent.py              # Stage 2: Planning agent (654 lines)
├── claude_agent_pseudocode.py      # Reference: Claude patterns (527 lines)
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

### Why Moonshot Kimi API?

- **OpenAI Compatibility**: Drop-in replacement using OpenAI SDK, easy model swapping
- **Strong Multi-Turn Support**: Handles 16+ turn conversations reliably
- **Reasonable Pricing**: Cost-effective for development and testing
- **China Presence**: Project originated in China, Kimi has good local support

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
- **Challenging**: 29.7% avg score shows significant room for improvement
- **Educational**: Learn what works and what doesn't through honest assessment

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

**Q: What's the difference between Stage 1 and Stage 2?**

A:
- **Stage 1 (Minimal)**: Reactive execution, no explicit planning, lighter weight
- **Stage 2 (Plan)**: Proactive planning, plan.md persistence, adaptive execution

Choose Stage 1 for simple tasks or when speed matters. Use Stage 2 for complex multi-step problems.

## Development Roadmap

- [x] **Stage 1: Minimal Agent** (Complete)
  - Core tool calling mechanics
  - Multi-turn conversation support
  - Production-grade safety and logging
  - DA-Code baseline: 29.7% avg score / 20.3% success

- [ ] **Stage 2: Plan Agent** (In Progress)
  - Dynamic planning with plan.md persistence
  - Adaptive execution based on results
  - Target: 35%+ avg score on DA-Code tasks
  - Improved visualization capability

- [ ] **Stage 3: Memory & Learning** (Planned)
  - Learn from successful task patterns
  - Prompt optimization based on history
  - Tool usage pattern recognition
  - Target: 50%+ avg score

- [ ] **Stage 4: Auto-Evolution** (Planned)
  - Self-evaluation and error analysis
  - Multi-epoch prompt refinement
  - Automatic tool knowledge expansion
  - Target: 70%+ DA-Code benchmark

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
