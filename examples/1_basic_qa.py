"""
Example 1: Basic Question Answering

Demonstrates:
- Single-turn agent capability
- Simple tool calling (or no tools if question is straightforward)
- Fast execution (~1-2 minutes)

This example shows the most basic agent usage - asking a simple question
and getting a text response.
"""

from minimal_kimi_agent import MinimalKimiAgent


def main():
    print("=== Example 1: Basic Q&A ===\n")

    # Create agent instance
    agent = MinimalKimiAgent()

    # Run a simple task
    # The agent may or may not use tools depending on the question
    result = agent.run(
        "What is cloud computing? Explain in 3 sentences.",
        max_turns=3
    )

    print("\n=== RESULT ===")
    print(result)
    print()


if __name__ == "__main__":
    main()
