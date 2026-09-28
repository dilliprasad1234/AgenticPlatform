"""Module containing agent execution functionality for the Enterprise Agent Framework."""

import json

import typer
from src.cli.prompts import prompt

from agents.agent_crud import select_agent
from agents.agent_registry import AgentRegistry

from src.cli.ui import (
    info,
    success,
    render_execution_result,
)

from src.exceptions import (
    ValidationError,
    exception_handler,
)

from src.runtime.crew_runtime import (
    CrewRuntime,
)


@exception_handler("agent.execute")
def execute_agent(
    runtime: CrewRuntime,
    registry: AgentRegistry,
) -> None:
    """
    Select and execute an agent.
    """

    # -----------------------------------------
    # Select Agent
    # -----------------------------------------

    agent = select_agent(
        registry
    )

    if agent is None:
        return

    info(
        f"Executing agent: {agent.agent.name}"
    )

    # -----------------------------------------
    # Display Input Format
    # -----------------------------------------

    if agent.input_format:

        typer.echo()
        typer.echo("=" * 60)
        typer.echo("Supported Input Format")
        typer.echo("=" * 60)

        input_format = agent.input_format

        if isinstance(input_format, list):
            for item in input_format:
                typer.echo(f"\n- {item}")
        else:
            for format_name, format_definition in input_format.items():
                typer.echo(f"\n{format_name.upper()}")
                typer.echo("\nDescription:")
                typer.echo(f"  {format_definition.description}")
                typer.echo("\nSample Input:")
                sample = format_definition.sample
                if isinstance(sample, dict):
                    typer.echo(
                        "  " + json.dumps(sample, indent=2).replace("\n", "\n  ")
                    )
                else:
                    typer.echo(f"  {sample}")

    typer.echo()
    typer.echo(
        "You can press ENTER to run the agent "
        "without runtime input."
    )

    # -----------------------------------------
    # Input
    # -----------------------------------------

    user_input = prompt(
        "Enter agent input",
        default="",
        show_default=False,
    )

    # -----------------------------------------
    # No Runtime Input
    # -----------------------------------------

    if not user_input.strip():

        inputs = None

    else:

        # -----------------------------------------
        # Parse Input (JSON or Plain Text)
        # -----------------------------------------

        try:
            parsed = json.loads(
                user_input
            )
            if isinstance(parsed, dict):
                inputs = parsed
            else:
                inputs = {
                    "user_input": user_input
                }
        except (json.JSONDecodeError, TypeError):
            inputs = {
                "user_input": user_input
            }

    # -----------------------------------------
    # Execute
    # -----------------------------------------

    info(
        "Executing agent..."
    )

    result = runtime.execute(
        identifier=agent.id,
        inputs=inputs,
    )

    # -----------------------------------------
    # Result
    # -----------------------------------------

    success(
        "Agent execution completed."
    )

    render_execution_result(
        result,
        title=f"Agent Result: {agent.agent.name}",
    )