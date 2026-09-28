"""Module containing workflow search functionality."""

import typer

from src.cli.ui import (
    menu,
)
from src.exceptions import (
    ValidationError,
    exception_handler,
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
from workflows.workflow_selection import (
    select_good_at,
    select_practice_area,
)


def _select_search_result(
    results,
    search_description: str,
):
    """Display search results and select a workflow."""

    if not results:

        typer.echo(
            f"\nNo workflows found for "
            f"{search_description}."
        )

        typer.echo()

        return None

    typer.echo(
        f"\nWorkflows matching "
        f"{search_description}:"
    )

    for index, workflow in enumerate(
        results,
        start=1,
    ):

        typer.echo(
            f"{index}. {workflow.name}"
        )

    typer.echo()

    choice = typer.prompt(
        "Select a workflow",
        type=int,
    )

    if (
        choice < 1
        or choice > len(results)
    ):

        raise ValidationError(
            "Invalid workflow search result selection.",
            user_message=(
                "Invalid workflow selection."
            ),
        )

    return results[choice - 1]


@exception_handler("workflow.search")
def search_workflows(
    runtime: WorkflowRuntime,
    workflows: WorkflowRegistry,
) -> None:
    """Display workflow search options."""

    while True:

        menu(
            "Search Workflows",
            [
                "1. Practice Area",
                "2. Good At",
                "3. Keyword",
                "4. Back",
            ],
        )

        choice = typer.prompt(
            "Select an option"
        ).strip()

        # -----------------------------------------
        # Practice Area
        # -----------------------------------------

        if choice == "1":

            selected_area = (
                select_practice_area()
            )

            results = workflows.search_workflows(
                practice_area=selected_area
            )

            selected_workflow = _select_search_result(
                results,
                f"practice area '{selected_area}'",
            )

            if selected_workflow is not None:

                execute_workflow(
                    runtime,
                    workflows,
                    workflow=selected_workflow,
                )

        # -----------------------------------------
        # Good At
        # -----------------------------------------

        elif choice == "2":

            selected_good_at = (
                select_good_at()
            )

            results = workflows.search_workflows(
                good_at=selected_good_at
            )

            good_at_label = ", ".join(
                selected_good_at
            )

            selected_workflow = _select_search_result(
                results,
                f"good at '{good_at_label}'",
            )

            if selected_workflow is not None:

                execute_workflow(
                    runtime,
                    workflows,
                    workflow=selected_workflow,
                )

        # -----------------------------------------
        # Keyword
        # -----------------------------------------

        elif choice == "3":

            keyword = typer.prompt(
                "Enter keyword"
            ).strip()

            if not keyword:

                raise ValidationError(
                    "Workflow search keyword cannot be empty.",
                    user_message=(
                        "Keyword cannot be empty."
                    ),
                )

            results = workflows.search_workflows(
                keyword=keyword
            )

            selected_workflow = _select_search_result(
                results,
                f"keyword '{keyword}'",
            )

            if selected_workflow is not None:

                execute_workflow(
                    runtime,
                    workflows,
                    workflow=selected_workflow,
                )

        # -----------------------------------------
        # Back
        # -----------------------------------------

        elif choice == "4":

            return

        # -----------------------------------------
        # Invalid Selection
        # -----------------------------------------

        else:

            raise ValidationError(
                "Invalid workflow search selection.",
                user_message=(
                    "Please select 1, 2, 3, or 4."
                ),
            )