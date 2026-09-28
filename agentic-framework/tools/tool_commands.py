"""Module containing tool commands functionality for the Enterprise Agent Framework."""

import typer
from src.cli.prompts import prompt
from src.cli.navigation import CLIBack, CLIExit

from src.config import (
    TOOLS_DIR,
    TOOL_DEFINITIONS_DIR,
    TOOL_IMPLEMENTATIONS_DIR,
)

from tools.tool_factory import ToolFactory
from tools.tool_registry import ToolRegistry

from tools.tool_crud import (
    create_tool,
    edit_tool,
    delete_tool,
    list_tools,
)

from tools.tool_execution import (
    execute_tool,
)

from src.llm.gateway import (
    LLMGateway,
)

from src.cli.ui import (
    error,
    menu,
)


def tool_menu():

    # -----------------------------------------
    # Directories
    # -----------------------------------------

    """Execute the tool menu operation."""
    TOOL_DEFINITIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    TOOL_IMPLEMENTATIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------
    # Tool Registry
    # -----------------------------------------

    registry = ToolRegistry(
        TOOLS_DIR
    )

    registry.discover_tools()

    # -----------------------------------------
    # Tool Factory
    # -----------------------------------------

    factory = ToolFactory(
        LLMGateway()
    )

    # -----------------------------------------
    # Menu
    # -----------------------------------------

    while True:

        menu(
            "Tools",
            [
                "1. Create Tool",
                "2. Edit Tool",
                "3. Delete Tool",
                "4. View Tools",
                "5. Run a Tool",
            ],
            breadcrumb="Home > Tools",
            subtitle="Choose an action. Use B to go back one screen or 0 to exit.",
            module_navigation=True
        )

        choice = prompt("Select an option", navigation=False).strip()

        try:

            if choice == "1":

                create_tool(
                    factory
                )

            elif choice == "2":

                edit_tool()

            elif choice == "3":

                delete_tool()

            elif choice == "4":

                list_tools()

            elif choice == "5":

                execute_tool(
                    registry
                )

            elif choice.lower() in {"b", "back"}:

                return

            elif choice.lower() in {"0", "x", "exit"}:

                raise CLIExit()

            else:

                error(
                    "Please choose one of the options above, B to go back one screen, or 0 to exit."
                )

        except CLIBack:
            return
        except CLIExit:
            raise
        except Exception as exc:
            error(str(exc))