"""Module containing tool execution functionality for the Enterprise Agent Framework."""

import json
from typing import Any

import typer
from src.cli.prompts import prompt

from src.cli.ui import (
    info,
    success,
)

from src.exceptions import (
    ArtifactNotFoundError,
    ToolError,
    ValidationError,
    exception_handler,
)

from src.observability import (
    TRACE_ID,
    end_run,
    log_event,
    start_run,
    span,
)

from tools.tool_registry import ToolRegistry


def _build_sample_input(
    inputs: list[Any],
) -> dict[str, Any]:
    """Build a representative JSON sample from tool inputs."""

    sample: dict[str, Any] = {}

    for input_definition in inputs:

        name = input_definition.name
        input_type = input_definition.type

        if input_type == "string":

            sample[name] = "example"

        elif input_type == "object":

            sample[name] = {}

        elif input_type == "boolean":

            sample[name] = True

        elif input_type == "integer":

            sample[name] = 1

        elif input_type == "number":

            sample[name] = 1

        elif input_type == "array":

            sample[name] = []

        else:

            sample[name] = "example"

    return sample


def _display_input_format(
    tool_spec,
) -> None:
    """Display tool input format using the tool specification."""

    inputs = tool_spec.inputs

    if not inputs:
        return

    typer.echo()

    typer.echo(
        "Supported Input Format: JSON"
    )

    typer.echo()

    typer.echo(
        "Description:"
    )

    typer.echo(
        "  JSON object containing the tool "
        "input parameters."
    )

    typer.echo()

    typer.echo(
        "Input Parameters:"
    )

    for input_definition in inputs:

        typer.echo(
            f"  {input_definition.name} "
            f"({input_definition.type})"
        )

        typer.echo(
            f"    {input_definition.description}"
        )

        typer.echo(
            f"    Required: "
            f"{'Yes' if input_definition.required else 'No'}"
        )

    typer.echo()

    typer.echo(
        "Sample Input:"
    )

    sample = _build_sample_input(
        inputs
    )

    typer.echo(
        json.dumps(
            sample,
            indent=2,
        )
    )

    typer.echo()


@exception_handler("tool.execute")
def execute_tool(
    registry: ToolRegistry,
) -> None:
    """
    Select and execute a registered tool.
    """

    # -----------------------------------------
    # Select Tool
    # -----------------------------------------

    tool_id = select_tool(
        registry
    )

    if tool_id is None:
        return

    info(
        f"Executing tool: {tool_id}"
    )

    # -----------------------------------------
    # Load Tool Specification
    # -----------------------------------------

    tool_spec = registry.get_spec(
        tool_id
    )

    # -----------------------------------------
    # Load Tool Implementation
    # -----------------------------------------

    tool = registry.get(
        tool_id
    )

    # -----------------------------------------
    # Display Input Format
    # -----------------------------------------

    _display_input_format(
        tool_spec
    )

    # -----------------------------------------
    # Run Tracking
    # -----------------------------------------

    owns_run = TRACE_ID.get() == "-"

    if owns_run:

        start_run(
            run_type="tool_runtime",
            name=tool_id,
            tool_id=tool_id,
        )

    else:

        log_event(
            "INFO",
            "tool.execution_started",
            component="tool",
            message=(
                f"Tool execution started: "
                f"{tool_id}"
            ),
            tool_id=tool_id,
        )

    # -----------------------------------------
    # Input
    # -----------------------------------------

    user_input = prompt(
        "Enter tool input JSON"
    )

    if not user_input.strip():

        raise ValidationError(
            "Tool input cannot be empty.",
            user_message=(
                "Tool input cannot be empty."
            ),
        )

    # -----------------------------------------
    # Validate JSON
    # -----------------------------------------

    try:

        arguments = json.loads(
            user_input
        )

    except json.JSONDecodeError as exc:

        raise ValidationError(
            f"Invalid JSON input: {exc}",
            user_message=(
                "Invalid JSON input."
            ),
        ) from exc

    if not isinstance(
        arguments,
        dict,
    ):

        raise ValidationError(
            "Tool input must be a JSON object.",
            user_message=(
                "Tool input must be a JSON object."
            ),
        )

    # -----------------------------------------
    # Validate Tool
    # -----------------------------------------

    if not hasattr(
        tool,
        "execute",
    ):

        raise ToolError(
            f"Tool '{tool_id}' does not provide "
            "an execute() method.",
            user_message=(
                f"Tool '{tool_id}' cannot be executed."
            ),
        )

    # -----------------------------------------
    # Execute
    # -----------------------------------------

    info(
        "Executing tool..."
    )

    try:

        with span(
            "tool.runtime_execute",
            component="tool",
            tool_id=tool_id,
        ):

            result = tool.execute(
                **arguments
            )

    except Exception:

        # The exception handler decorator is
        # responsible for centralized logging.
        #
        # This block only manages execution
        # lifecycle state.

        if owns_run:

            end_run(
                status="failed",
                run_type="tool_runtime",
                tool_id=tool_id,
            )

        raise

    # -----------------------------------------
    # Complete Run
    # -----------------------------------------

    if owns_run:

        end_run(
            status="success",
            run_type="tool_runtime",
            tool_id=tool_id,
        )

    else:

        log_event(
            "INFO",
            "tool.execution_completed",
            component="tool",
            message=(
                f"Tool execution completed: "
                f"{tool_id}"
            ),
            tool_id=tool_id,
        )

    # -----------------------------------------
    # Result
    # -----------------------------------------

    success(
        "Tool execution completed."
    )

    typer.echo(
        "\nTool Result:"
    )

    typer.echo(
        result
    )

    typer.echo()


def select_tool(
    registry: ToolRegistry,
) -> str | None:
    """
    Display available tools and return the selected tool ID.
    """

    # -----------------------------------------
    # Discover Tools
    # -----------------------------------------

    registry.discover_tools()

    tools = registry.list_tools()

    if not tools:

        info(
            "No tools found."
        )

        return None

    # -----------------------------------------
    # Display Tools
    # -----------------------------------------

    typer.echo(
        "\nAvailable Tools:"
    )

    for index, tool_id in enumerate(
        tools,
        start=1,
    ):

        try:

            spec = registry.get_spec(
                tool_id
            )

            display_name = spec.name

        except ArtifactNotFoundError:

            display_name = tool_id

        typer.echo(
            f"{index}. {display_name}"
        )

    typer.echo()

    # -----------------------------------------
    # Select Tool
    # -----------------------------------------

    choice = prompt(
        "Select a tool",
        type=int,
    )

    if (
        choice < 1
        or choice > len(tools)
    ):

        raise ValidationError(
            "Invalid tool selection.",
            user_message=(
                "Invalid tool selection."
            ),
        )

    return tools[
        choice - 1
    ]