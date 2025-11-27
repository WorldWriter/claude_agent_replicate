# Agent Examples

Three runnable examples demonstrating agent capabilities, from simple Q&A to complex data visualization.

## Prerequisites

1. **Configure Environment**:
   ```bash
   cp ../.env.example ../.env
   # Edit ../.env and add your MOONSHOT_API_KEY
   ```

2. **Install Dependencies**:
   ```bash
   cd ..
   pip install -r requirements.txt
   ```

3. **Verify Agent Files**:
   - Ensure `minimal_kimi_agent.py` is in parent directory
   - Examples import from parent: `from minimal_kimi_agent import MinimalKimiAgent`

## Examples

### 1. Basic Q&A (`1_basic_qa.py`)

**Runtime**: ~1-2 minutes
**Demonstrates**: Single-turn capability, simple text generation

Simple question-answering showing the agent can handle basic queries without file operations.

```bash
python examples/1_basic_qa.py
```

**Expected Output**:
```
=== Example 1: Basic Q&A ===

Starting agent...
[Agent processes request]

=== RESULT ===
Cloud computing is...
```

---

### 2. Data Analysis (`2_data_analysis.py`)

**Runtime**: ~3-5 minutes
**Demonstrates**: Multi-turn reasoning, file operations, data analysis

Multi-step workflow where the agent reads CSV data, performs calculations, and writes results to file.

```bash
python examples/2_data_analysis.py
```

**What It Does**:
1. Creates sample sales data CSV
2. Agent reads the file
3. Agent calculates sales by region and product
4. Agent writes analysis summary to text file

**Expected Output**:
```
=== Example 2: Data Analysis ===

✓ Sample data created: agent_workspace/sample_sales.csv

Starting agent...
[Agent reads file, analyzes data, writes results]

=== RESULT ===
Analysis complete. Results saved to analysis_result.txt

=== OUTPUT FILE ===
Total Sales by Product:
- Widget C: 1500
- Widget A: 2100
...
```

---

### 3. Data Visualization (`3_visualization.py`)

**Runtime**: ~5-10 minutes
**Demonstrates**: Complex tool usage, matplotlib plotting, file generation

More complex workflow involving data visualization with matplotlib.

```bash
python examples/3_visualization.py
```

**What It Does**:
1. Creates sample monthly revenue/expense data
2. Agent reads the CSV
3. Agent generates matplotlib line plot
4. Agent saves plot as PNG file

**Expected Output**:
```
=== Example 3: Visualization ===

✓ Plot data created: agent_workspace/monthly_data.csv

Starting agent...
[Agent creates visualization code, executes it]

=== RESULT ===
Visualization created successfully

✓ Plot saved: agent_workspace/monthly_trends.png
```

## Troubleshooting

**Error: "ModuleNotFoundError: No module named 'minimal_kimi_agent'"**
- Run examples from the examples/ directory: `python examples/1_basic_qa.py`
- Or run from parent directory: `python -m examples.1_basic_qa`

**Error: "API key not found"**
- Ensure `.env` file exists in parent directory
- Verify `MOONSHOT_API_KEY` is set in `.env`

**Error: "No such file or directory: 'agent_workspace'"**
- The agent will create this automatically on first run
- Alternatively: `mkdir -p agent_workspace`

**Example Takes Too Long**
- Check max_turns parameter (lower = faster but may not complete)
- Check your network connection to Kimi API
- View logs in `logs/` directory to see what agent is doing

## Modifying Examples

Feel free to modify these examples to test different scenarios:

**Change the Task**:
```python
# In any example file
result = agent.run(
    "Your custom task here",
    max_turns=15
)
```

**Adjust Verbosity**:
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Use Dynamic Plan Agent for Complex Tasks**:
```python
# For complex multi-step tasks, use Stage 2
from dynamic_plan_agent import MinimalKimiAgent

agent = MinimalKimiAgent()  # Same class name, enhanced behavior!
# Agent will automatically create and track todos
```

## Expected Files After Running

```
agent_workspace/
├── sample_sales.csv           # From example 2
├── analysis_result.txt         # From example 2
├── monthly_data.csv            # From example 3
└── monthly_trends.png          # From example 3

logs/
├── 2025-11-26_14-30-45.txt    # Human-readable log
└── 2025-11-26_14-30-45.json   # Structured log
```

## Next Steps

After running these examples:

1. **Review Logs**: Check `logs/` to see how the agent reasoned through tasks
2. **Try Custom Tasks**: Modify examples with your own data analysis tasks
3. **Run Benchmark**: Test against DA-Code: `python test/evaluate_dacode_official.py --dataset quick`
4. **Read Architecture**: Understand how it works: [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)

---

**Note**: These examples use the Minimal Agent (Stage 1). For more complex multi-step tasks, consider using the Dynamic Plan Agent (Stage 2) by importing `MinimalKimiAgent` from `dynamic_plan_agent` instead. See [`docs/AGENT_EVOLUTION.md`](../docs/AGENT_EVOLUTION.md) for details.
