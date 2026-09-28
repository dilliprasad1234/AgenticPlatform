"""Module containing app functionality for the Enterprise Agent Framework."""

import sys
import json
from dotenv import load_dotenv
from src.config import (
    AGENTS_DIR,
    TOOLS_DIR,
)
from agents.agent_registry import AgentRegistry
from tools.tool_registry import ToolRegistry
from src.runtime.crew_runtime import (
    CrewRuntime,
)


def main():

    """Execute the main operation."""
    load_dotenv()

    # -----------------------------------------
    # Agent ID
    # -----------------------------------------

    if len(sys.argv) < 2:

        print(
            "Usage: "
            "python -m enterprise_agent_framework.app <agent_id>"
        )

        return

    agent_id = sys.argv[1]

    # -----------------------------------------
    # Runtime input
    # -----------------------------------------

    print("\nEnter input (JSON or plain text).")
    print("Press Enter if no input is required.")
    print("> ", end="")

    user_input = input().strip()
    if user_input:
        try:
            parsed = json.loads(user_input)
            if isinstance(parsed, dict):
                inputs = parsed
            else:
                inputs = {"user_input": user_input}
        except (json.JSONDecodeError, TypeError):
            inputs = {"user_input": user_input}
    else:
        inputs = {}
    # -----------------------------------------
    # Registries
    # -----------------------------------------
    agent_registry = AgentRegistry(
        AGENTS_DIR
    )
    tool_registry = ToolRegistry(
        TOOLS_DIR
    )
    tool_registry.discover_tools()

    # -----------------------------------------
    # Runtime
    # -----------------------------------------
    runtime = CrewRuntime(
        agent_registry,
        tool_registry,
    )
    # -----------------------------------------
    # Execute agent
    # -----------------------------------------
    result = runtime.execute(
        identifier=agent_id,
        inputs=inputs,
    )
    # -----------------------------------------
    # Result
    # -----------------------------------------
    print("\n===================================")
    print("Execution Completed")
    print("===================================\n")
    print(result)

if __name__ == "__main__":
    main()