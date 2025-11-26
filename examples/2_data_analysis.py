"""
Example 2: Multi-Step Data Analysis

Demonstrates:
- File operations (ReadFile, WriteFile)
- Multi-turn reasoning
- Data analysis workflow
- CSV data handling

This example creates sample sales data, asks the agent to analyze it,
and writes the results to a file. Shows multi-turn conversation and
tool usage.
"""

import os
from minimal_kimi_agent import MinimalKimiAgent


def setup_sample_data():
    """Create sample CSV file for analysis"""
    sample_csv = """product,sales,region
Widget A,1200,North
Widget B,800,South
Widget C,1500,East
Widget A,900,West
Widget B,1100,North
Widget C,950,South
Widget A,1050,East
Widget B,1200,West
"""

    # Create agent_workspace directory if it doesn't exist
    os.makedirs("agent_workspace", exist_ok=True)

    # Write sample data
    with open("agent_workspace/sample_sales.csv", "w") as f:
        f.write(sample_csv)

    print("✓ Sample data created: agent_workspace/sample_sales.csv\n")


def main():
    print("=== Example 2: Data Analysis ===\n")

    # Setup sample data
    setup_sample_data()

    # Create agent
    agent = MinimalKimiAgent()

    # Run multi-step analysis task
    result = agent.run("""
Analyze the sales data in sample_sales.csv:

1. Read the file
2. Calculate total sales by product
3. Calculate total sales by region
4. Identify the top-selling product
5. Identify the top-selling region
6. Write a summary to analysis_result.txt

The summary should include:
- Total sales for each product
- Total sales for each region
- Which product sold best
- Which region had highest sales
""", max_turns=10)

    print("\n=== RESULT ===")
    print(result)

    # Show the output file if it was created
    output_file = "agent_workspace/analysis_result.txt"
    if os.path.exists(output_file):
        print("\n=== OUTPUT FILE ===")
        with open(output_file, 'r') as f:
            print(f.read())
    else:
        print("\n(Note: Output file not found - agent may have used different filename)")

    print()


if __name__ == "__main__":
    main()
