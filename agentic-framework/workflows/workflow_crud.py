"""Module containing workflow crud functionality for the Enterprise Agent Framework."""

import typer

from agents.agent_registry import AgentRegistry
from src.cli.ui import (
    info,
    success,
)
from src.exceptions import (
    ValidationError,
    exception_handler,
)
from src.utils.editor import (
    open_in_editor,
)
from src.utils.slug import (
    slugify,
)
from workflows.workflow import (
    WorkflowSpec,
)
from workflows.workflow_builder import (
    WorkflowBuilder,
)
from workflows.workflow_registry import (
    WorkflowRegistry,
)
from workflows.workflow_selection import (
    select_good_at,
    select_practice_area,
)


@exception_handler("workflow.create")
def create_workflow(
    agents: AgentRegistry,
    workflows: WorkflowRegistry,
):
    """Execute the create workflow operation."""

    # -----------------------------------------
    # Workflow Information
    # -----------------------------------------

    name = typer.prompt(
        "Workflow Name"
    )

    description = typer.prompt(
        "Description"
    )

    practice_area = select_practice_area()

    good_at = select_good_at()

    # -----------------------------------------
    # Build Execution Plan
    # -----------------------------------------

    builder = WorkflowBuilder(
        agents
    )

    execution = builder.build()

    # -----------------------------------------
    # Collect Agent IDs
    # -----------------------------------------

    agent_ids = []

    for step in execution.steps:

        if (
            step.agent
            and step.agent not in agent_ids
        ):
            agent_ids.append(
                step.agent
            )

    # -----------------------------------------
    # Validate Agents
    # -----------------------------------------

    if not agent_ids:

        raise ValidationError(
            "Workflow must contain at least one agent.",
            user_message=(
                "Workflow must contain at least one agent."
            ),
        )

    # -----------------------------------------
    # Create Workflow Specification
    # -----------------------------------------

    spec = WorkflowSpec(
        id=slugify(name),
        name=name,
        description=description,
        practice_area=practice_area,
        good_at=good_at,
        agents=agent_ids,
        execution=execution,
    )

    # -----------------------------------------
    # Save Workflow
    # -----------------------------------------

    path = workflows.save(
        spec
    )

    success(
        f"Workflow created: {path}"
    )

    # -----------------------------------------
    # Open Workflow
    # -----------------------------------------

    if open_in_editor(path):

        info(
            "Workflow file opened in editor."
        )

    else:

        info(
            f"Edit manually: {path}"
        )


def select_workflow(
    workflows: WorkflowRegistry,
):
    """Execute the select workflow operation."""

    workflow_list = (
        workflows.list_workflows()
    )

    if not workflow_list:

        info(
            "No workflows found."
        )

        return None

    typer.echo(
        "\nAvailable Workflows:"
    )

    for index, workflow in enumerate(
        workflow_list,
        start=1,
    ):

        typer.echo(
            f"{index}. {workflow.name}"
        )

    choice = typer.prompt(
        "Select a workflow",
        type=int,
    )

    if (
        choice < 1
        or choice > len(workflow_list)
    ):

        raise ValidationError(
            "Invalid workflow selection.",
            user_message=(
                "Invalid workflow selection."
            ),
        )

    return workflow_list[
        choice - 1
    ]


@exception_handler("workflow.edit")
def edit_workflow(
    workflows: WorkflowRegistry,
):
    """Execute the edit workflow operation."""

    workflow = select_workflow(
        workflows
    )

    if workflow is None:
        return

    path = workflows.path_for(
        workflow.id
    )

    if open_in_editor(path):

        info(
            "Workflow file opened in editor."
        )

    else:

        info(
            f"File: {path}"
        )


@exception_handler("workflow.delete")
def delete_workflow(
    workflows: WorkflowRegistry,
):
    """Execute the delete workflow operation."""

    workflow = select_workflow(
        workflows
    )

    if workflow is None:
        return

    path = workflows.path_for(
        workflow.id
    )

    if not typer.confirm(
        f"Delete '{workflow.name}'?"
    ):

        info(
            "Deletion cancelled."
        )

        return

    workflows.delete(
        workflow.id
    )

    success(
        f"Workflow deleted successfully: "
        f"{path.name}"
    )


@exception_handler("workflow.list")
def list_workflows(
    workflows: WorkflowRegistry,
):
    """Execute the list workflows operation."""

    workflow_list = (
        workflows.list_workflows()
    )

    if not workflow_list:

        info(
            "No workflows found."
        )

        return

    typer.echo(
        "\nAvailable Workflows:"
    )

    for index, workflow in enumerate(
        workflow_list,
        start=1,
    ):

        typer.echo(
            f"{index}. {workflow.name}"
        )

    typer.echo()