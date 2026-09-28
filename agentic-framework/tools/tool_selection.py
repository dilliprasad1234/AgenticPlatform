"""Module containing tool selection functionality for the Enterprise Agent Framework."""

import typer

from src.exceptions import (
    ValidationError,
    exception_handler,
)
from tools.tool_registry import ToolRegistry


@exception_handler("tool.select")
def select_tools(
    registry: ToolRegistry,
    current_tools: list[str] | None = None,
    keep_current_on_empty: bool = False,
) -> list[str]:

    """Execute the select tools operation."""
    tools = registry.list_tools()

    if not tools:
        typer.echo(
            "\nNo tools available."
        )
        return []

    typer.echo(
        "\nTools Configuration\n"
    )

    typer.echo(
        "Available Tools:\n"
    )

    for index, tool_id in enumerate(
        tools,
        start=1,
    ):
        typer.echo(
            f"{index}. {tool_id}"
        )

    if current_tools:
        typer.echo(
            "\nCurrently selected tools:"
        )

        for tool_id in current_tools:
            typer.echo(
                f"- {tool_id}"
            )

    typer.echo(
        "\nEnter tool numbers separated by commas."
    )

    if keep_current_on_empty:
        typer.echo(
            "Press Enter to keep current tools."
        )
    else:
        typer.echo(
            "Press Enter to skip tools."
        )

    selection = typer.prompt(
        "Select tools",
        default="",
    ).strip()

    if not selection:
        if keep_current_on_empty and current_tools is not None:
            return current_tools.copy()

        return []

    if selection.lower() == "clear":
        return []

    selected_tools = []

    for value in selection.split(","):

        value = value.strip()

        if not value.isdigit():
            raise ValidationError(
                f"Invalid tool selection: {value}",
                user_message="Invalid tool selection.",
            )

        index = int(value)

        if index < 1 or index > len(tools):
            raise ValidationError(
                f"Invalid tool selection: {index}",
                user_message="Invalid tool selection.",
            )

        tool_id = tools[index - 1]

        if tool_id not in selected_tools:
            selected_tools.append(
                tool_id
            )

    return selected_tools

@exception_handler("tool.select_for_edit")
def select_tools_for_edit(
    registry: ToolRegistry,
    current_tools: list[str],
) -> list[str]:

    """Execute the select tools for edit operation."""
    tools = registry.list_tools()

    if not tools:
        typer.echo(
            "\nNo tools available."
        )
        return current_tools.copy()

    selected_tools = current_tools.copy()

    typer.echo(
        "\nCurrent Tools:"
    )

    if selected_tools:
        for tool_id in selected_tools:
            typer.echo(
                f"- {tool_id}"
            )
    else:
        typer.echo(
            "- No tools selected"
        )

    # -----------------------------------------
    # Remove Tools
    # -----------------------------------------

    if selected_tools:
        typer.echo(
            "\nRemove Tools"
        )

        for index, tool_id in enumerate(
            selected_tools,
            start=1,
        ):
            typer.echo(
                f"{index}. {tool_id}"
            )

        typer.echo(
            "\nEnter tool numbers to remove."
        )
        typer.echo(
            "Press Enter to remove nothing."
        )

        remove_selection = typer.prompt(
            "Remove tools",
            default="",
        ).strip()

        if remove_selection:
            remove_indexes = []

            for value in remove_selection.split(","):
                value = value.strip()

                if not value.isdigit():
                    raise ValidationError(
                        f"Invalid tool selection: {value}",
                        user_message="Invalid tool selection.",
                    )

                index = int(value)

                if index < 1 or index > len(selected_tools):
                    raise ValidationError(
                        f"Invalid tool selection: {index}",
                        user_message="Invalid tool selection.",
                    )

                if index not in remove_indexes:
                    remove_indexes.append(index)

            for index in sorted(
                remove_indexes,
                reverse=True,
            ):
                selected_tools.pop(index - 1)

    # -----------------------------------------
    # Add Tools
    # -----------------------------------------

    typer.echo(
        "\nAdd Tools"
    )

    available_tools = [
        tool_id
        for tool_id in tools
        if tool_id not in selected_tools
    ]

    if available_tools:
        for index, tool_id in enumerate(
            available_tools,
            start=1,
        ):
            typer.echo(
                f"{index}. {tool_id}"
            )

        typer.echo(
            "\nEnter tool numbers to add."
        )
        typer.echo(
            "Press Enter to add nothing."
        )

        add_selection = typer.prompt(
            "Add tools",
            default="",
        ).strip()

        if add_selection:
            for value in add_selection.split(","):
                value = value.strip()

                if not value.isdigit():
                    raise ValidationError(
                        f"Invalid tool selection: {value}",
                        user_message="Invalid tool selection.",
                    )

                index = int(value)

                if index < 1 or index > len(available_tools):
                    raise ValidationError(
                        f"Invalid tool selection: {index}",
                        user_message="Invalid tool selection.",
                    )

                tool_id = available_tools[index - 1]

                if tool_id not in selected_tools:
                    selected_tools.append(
                        tool_id
                    )
    else:
        typer.echo(
            "No additional tools available."
        )

    return selected_tools