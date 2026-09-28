"""Module containing workflow execution functionality for the Enterprise Agent Framework."""

import json

import typer
from src.cli.prompts import prompt

from workflows.workflow_registry import (
    WorkflowRegistry,
)

from workflows.workflow_crud import (
    select_workflow,
)

from workflows.workflow_runtime import (
    WorkflowRuntime,
)

from src.cli.ui import (
    info,
    success,
    render_execution_result,
)

from src.exceptions import (
    ValidationError,
    exception_handler,
)


def _get_first_agent_id(workflow) -> str | None:
    """Get the first executable agent from a workflow."""

    # Graph workflow
    if (
        workflow.execution is not None
        and workflow.execution.type == "graph"
    ):

        for step in workflow.execution.steps:

            if (
                step.type == "agent"
                and step.agent
            ):
                return step.agent

    # Sequential workflow
    if workflow.agents:
        return workflow.agents[0]

    return None


def _display_input_format(
    runtime: WorkflowRuntime,
    workflow,
) -> None:
    """Display workflow input format from its first agent."""

    first_agent_id = _get_first_agent_id(
        workflow
    )

    if first_agent_id is None:
        return

    first_agent = runtime.agent_registry.get(
        first_agent_id
    )

    if not first_agent.input_format:
        return

    typer.echo()

    input_format = first_agent.input_format

    if isinstance(input_format, list):
        typer.echo("Supported Input Format:")
        for item in input_format:
            typer.echo(f"  - {item}")
        typer.echo()
        return

    for format_name, format_definition in input_format.items():

        typer.echo(
            f"Supported Input Format: "
            f"{format_name.upper()}"
        )

        typer.echo()
        typer.echo("Description:")
        typer.echo(f"  {format_definition.description}")
        typer.echo()
        typer.echo("Sample Input:")

        sample = format_definition.sample
        if isinstance(sample, dict):
            typer.echo(json.dumps(sample, indent=2))
        else:
            typer.echo(f"  {sample}")

        typer.echo()


@exception_handler("workflow.execute")
def execute_workflow(
    runtime: WorkflowRuntime,
    workflows: WorkflowRegistry,
    workflow=None,
):
    """Execute the execute workflow operation."""

    # -----------------------------------------
    # Select Workflow
    # -----------------------------------------

    if workflow is None:

        workflow = select_workflow(
            workflows
        )

        if workflow is None:
            return

    info(
        f"Executing workflow: {workflow.name}"
    )

    # -----------------------------------------
    # Display Input Format
    # -----------------------------------------

    _display_input_format(
        runtime,
        workflow,
    )

    typer.echo()
    typer.echo(
        "You can press ENTER to run the workflow "
        "without runtime input."
    )

    # -----------------------------------------
    # Input
    # -----------------------------------------

    user_input = prompt(
        "Enter workflow input",
        default="",
        show_default=False,
    )

    if not user_input.strip():
        user_input = "Execute the workflow using default parameters."

    # -----------------------------------------
    # Execute
    # -----------------------------------------

    info(
        "Executing workflow agents..."
    )

    result = runtime.execute(
        workflow_id=workflow.id,
        user_input=user_input,
    )

    # -----------------------------------------
    # Result
    # -----------------------------------------

    success(
        "Workflow execution completed."
    )

    render_execution_result(
        result,
        title=f"Workflow Result: {workflow.name}",
    )