"""
Example 3: Data Visualization

Demonstrates:
- Complex tool usage (running Python code)
- Matplotlib/seaborn plotting
- Output file generation
- Multi-step workflow with code execution

This example creates sample monthly data and asks the agent to generate
a visualization plot. Shows more complex RunCommand usage.
"""

import os
from minimal_kimi_agent import MinimalKimiAgent


def setup_plot_data():
    """Create sample monthly data for visualization"""
    sample_csv = """month,revenue,expenses
Jan,50000,35000
Feb,52000,36000
Mar,48000,34000
Apr,55000,37000
May,58000,38000
Jun,62000,40000
"""

    # Create agent_workspace directory if it doesn't exist
    os.makedirs("agent_workspace", exist_ok=True)

    # Write sample data
    with open("agent_workspace/monthly_data.csv", "w") as f:
        f.write(sample_csv)

    print("✓ Plot data created: agent_workspace/monthly_data.csv\n")


def main():
    print("=== Example 3: Visualization ===\n")

    # Setup sample data
    setup_plot_data()

    # Create agent
    agent = MinimalKimiAgent()

    # Run visualization task
    # Note: This may be challenging for the agent as visualization
    # is identified as a weakness (0% success in DA-Code benchmark)
    result = agent.run("""
Create a visualization from monthly_data.csv:

1. Read the CSV file
2. Create a line plot showing revenue and expenses over months
3. Use different colors for revenue (blue) and expenses (red)
4. Add proper axis labels ("Month" and "Amount ($)")
5. Add a title "Monthly Revenue vs Expenses"
6. Add a legend
7. Save the plot as 'monthly_trends.png'

Use matplotlib for plotting. You can write and execute Python code to do this.
""", max_turns=15)

    print("\n=== RESULT ===")
    print(result)

    # Check if plot was created
    plot_file = "agent_workspace/monthly_trends.png"
    if os.path.exists(plot_file):
        print(f"\n✓ Plot saved: {plot_file}")
        print("  You can open this file to view the visualization!")
    else:
        print(f"\n✗ Plot file not found at {plot_file}")
        print("  The agent may have struggled with this task.")
        print("  (Visualization is a known weak area - 0% success in benchmark)")

    print()


if __name__ == "__main__":
    main()
