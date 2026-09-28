"""Module containing workflow commands functionality for the Enterprise Agent Framework."""

import typer

from agents.agent_registry import AgentRegistry
from src.cli.ui import (
    error,
    menu,
)
from src.config import (
    AGENTS_DIR,
    TOOLS_DIR,
    WORKFLOWS_DIR,
)
from src.exceptions import FrameworkError
from tools.tool_registry import ToolRegistry
from workflows.workflow_crud import (
    create_workflow,
    delete_workflow,
    edit_workflow,
    list_workflows,
)
from workflows.workflow_execution import (
    execute_workflow,
)
from workflows.workflow_registry import (
    WorkflowRegistry,
)
from workflows.workflow_runtime import (
    WorkflowRuntime,
)
from workflows.workflow_search import (
    search_workflows,
)


def workflow_menu() -> None:
    # """Execute the workflow menu operation."""
    # -----------------------------------------
    # Registries
    # -----------------------------------------
    agents = AgentRegistry(
        AGENTS_DIR
    )

    workflows = WorkflowRegistry(
        WORKFLOWS_DIR
    )

    tools = ToolRegistry(
        TOOLS_DIR
    )

    tools.discover_tools()

    # -----------------------------------------
    # Runtime
    # -----------------------------------------

    runtime = WorkflowRuntime(
        agents,
        workflows,
        tools,
    )

    # -----------------------------------------
    # Menu
    # -----------------------------------------

    while True:

        menu(
            "Workflow Management",
            [
                "1. Create Workflow",
                "2. Edit Workflow",
                "3. Delete Workflow",
                "4. List Workflows",
                "5. Execute Workflow",
                "6. Search Workflows",
                "7. Back to Main Menu",
            ],
        )

        choice = typer.prompt(
            "Select an option"
        ).strip()

        try:

            if choice == "1":

                create_workflow(
                    agents,
                    workflows,
                )

            elif choice == "2":

                edit_workflow(
                    workflows
                )

            elif choice == "3":

                delete_workflow(
                    workflows
                )

            elif choice == "4":

                list_workflows(
                    workflows
                )

            elif choice == "5":

                execute_workflow(
                    runtime,
                    workflows,
                )

            elif choice == "6":

                search_workflows(
                    runtime,
                    workflows,
                )

            elif choice == "7":

                return

            else:

                error(
                    "Please select 1, 2, 3, 4, 5, 6, or 7."
                )

        except FrameworkError as exc:

            error(
                exc.format_display()
            )

        except Exception:

            error(
                "An unexpected error occurred. "
                "Please check the logs for details."
            )