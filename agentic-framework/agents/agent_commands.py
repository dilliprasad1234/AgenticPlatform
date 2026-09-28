"""Module containing agent commands functionality for the Enterprise Agent Framework."""

import typer

from agents.agent_crud import (
    create_agent,
    delete_agent,
    edit_agent,
    list_agents,
)
from agents.agent_execution import (
    execute_agent,
)
from agents.agent_factory import (
    AgentFactory,
)
from agents.agent_registry import (
    AgentRegistry,
)
from agents.agent_search import (
    search_agents,
)
from src.cli.ui import (
    error,
    menu,
)
from src.config import (
    AGENTS_DIR,
    TOOLS_DIR,
)
from src.exceptions import (
    FrameworkError,
)
from src.llm.gateway import (
    LLMGateway,
)
from src.runtime.crew_runtime import (
    CrewRuntime,
)
from tools.tool_registry import (
    ToolRegistry,
)


def agent_menu() -> None:
    """
    Display and handle the Agent Management menu.
    """

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
    # Agent Factory
    # -----------------------------------------

    factory = AgentFactory(
        LLMGateway()
    )

    # -----------------------------------------
    # Runtime
    # -----------------------------------------

    runtime = CrewRuntime(
        agent_registry,
        tool_registry,
    )

    # -----------------------------------------
    # Menu
    # -----------------------------------------

    while True:

        menu(
            "Agent Management",
            [
                "1. Create Agent",
                "2. Edit Agent",
                "3. Delete Agent",
                "4. List Agents",
                "5. Execute Agent",
                "6. Search Agents",
                "7. Back to Main Menu",
            ],
        )

        choice = typer.prompt(
            "Select an option"
        ).strip()

        try:

            if choice == "1":

                create_agent(
                    factory,
                    agent_registry,
                    tool_registry,
                )

            elif choice == "2":

                edit_agent(
                    agent_registry,
                    tool_registry,
                )

            elif choice == "3":

                delete_agent(
                    agent_registry,
                )

            elif choice == "4":

                list_agents(
                    agent_registry,
                )

            elif choice == "5":

                execute_agent(
                    runtime,
                    agent_registry,
                )

            elif choice == "6":

                search_agents(
                    runtime,
                    agent_registry,
                )

            elif choice == "7":

                return

            else:

                error(
                    "Please select 1, 2, 3, 4, 5, or 6."
                )

        except FrameworkError as exc:

            # Exception logging is handled by the
            # centralized exception_handler decorator.
            #
            # The CLI displays the formatted user message with details.

            error(
                exc.format_display()
            )

        except Exception:

            # Unexpected exceptions are already logged
            # by the centralized exception handler.
            #
            # Do not expose internal details to the user.

            error(
                "An unexpected framework error occurred. "
                "Check the logs for details."
            )