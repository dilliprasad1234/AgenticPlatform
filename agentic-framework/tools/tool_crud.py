"""Module containing tool CRUD functionality for the Enterprise Agent Framework."""

import ast

import typer

from src.cli.ui import (
    info,
    success,
)
from src.config import (
    TOOL_DEFINITIONS_DIR,
    TOOL_IMPLEMENTATIONS_DIR,
)
from src.exceptions import (
    ArtifactNotFoundError,
    ValidationError,
    exception_handler,
)
from src.utils.editor import open_in_editor
from src.utils.slug import slugify
from tools.tool_factory import ToolFactory


@exception_handler("tool.create")
def create_tool(
    factory: ToolFactory,
) -> None:
    """
    Create a new tool definition and implementation.
    """

    # -----------------------------------------
    # Tool Description
    # -----------------------------------------

    description = typer.prompt(
        "Enter your tool requirements / functional description"
    )

    if not description.strip():
        raise ValidationError(
            "Description cannot be empty.",
            user_message="Tool description cannot be empty.",
        )

    # -----------------------------------------
    # Generate Tool Specification
    # -----------------------------------------

    info(
        "Generating tool specification..."
    )

    tool_spec = factory.generate(
        description
    )

    # -----------------------------------------
    # Definition YAML
    # -----------------------------------------

    definition_path = (
        TOOL_DEFINITIONS_DIR
        / f"{slugify(tool_spec.id)}.yaml"
    )

    # -----------------------------------------
    # Generate Python Implementation
    # -----------------------------------------

    info(
        "Generating and syntax-validating Python..."
    )

    code = factory.generate_implementation(
        tool_spec
    )

    implementation_path = (
        TOOL_IMPLEMENTATIONS_DIR
        / tool_spec.implementation_file
    )

    # -----------------------------------------
    # Existing Implementation
    # -----------------------------------------

    if implementation_path.exists():

        if not typer.confirm(
            f"{implementation_path.name} exists. Overwrite?"
        ):
            info(
                "Creation cancelled."
            )
            return

    # -----------------------------------------
    # Validate Generated Python
    # -----------------------------------------

    try:
        ast.parse(
            code,
            filename=str(implementation_path),
        )

    except SyntaxError as exc:
        raise ValidationError(
            f"Generated tool contains invalid Python: {exc}",
            user_message=(
                "The generated tool contains invalid Python."
            ),
        ) from exc

    # -----------------------------------------
    # Save YAML Definition
    # -----------------------------------------

    definition_path.write_text(
        factory.to_yaml(tool_spec),
        encoding="utf-8",
    )

    # -----------------------------------------
    # Save Python Implementation
    # -----------------------------------------

    implementation_path.write_text(
        code.rstrip() + "\n",
        encoding="utf-8",
    )

    # -----------------------------------------
    # Result
    # -----------------------------------------

    success(
        f"Tool definition created: {definition_path}"
    )

    success(
        f"Tool implementation created: {implementation_path}"
    )


def find_tool(
    name: str,
):
    """
    Find a tool implementation by name.
    """

    implementation_path = (
        TOOL_IMPLEMENTATIONS_DIR
        / f"{slugify(name)}.py"
    )

    if implementation_path.is_file():
        return implementation_path

    for path in TOOL_IMPLEMENTATIONS_DIR.glob(
        "*.py"
    ):

        if path.stem.lower() == name.lower():
            return path

    raise ArtifactNotFoundError(
        f"Tool '{name}' was not found.",
        user_message=(
            f"Tool '{name}' was not found."
        ),
    )


@exception_handler("tool.edit")
def edit_tool() -> None:
    """
    Edit an existing tool implementation.
    """

    path = select_tool()

    if path is None:
        return

    info(
        "Opened in editor."
        if open_in_editor(path)
        else f"File: {path}"
    )


@exception_handler("tool.delete")
def delete_tool() -> None:
    """
    Delete an existing tool implementation and
    its corresponding definition.
    """

    path = select_tool()

    if path is None:
        return

    definition_path = (
        TOOL_DEFINITIONS_DIR
        / f"{path.stem}.yaml"
    )

    if not typer.confirm(
        f"Delete tool '{path.stem}'?"
    ):
        info(
            "Deletion cancelled."
        )
        return

    path.unlink()

    if definition_path.exists():
        definition_path.unlink()

    success(
        f"Tool deleted successfully: {path.stem}"
    )


@exception_handler("tool.list")
def list_tools():
    """
    List all available tool implementations.
    """

    tools = list(
        TOOL_IMPLEMENTATIONS_DIR.glob(
            "*.py"
        )
    )

    if not tools:
        info(
            "No tools found."
        )
        return []

    typer.echo(
        "\nAvailable Tools:"
    )

    for index, tool in enumerate(
        tools,
        start=1,
    ):
        typer.echo(
            f"{index}. {tool.stem}"
        )

    typer.echo()

    return tools


def select_tool():
    """
    Display available tools and return the selected tool.
    """

    tools = list_tools()

    if not tools:
        return None

    choice = typer.prompt(
        "Select a tool",
        type=int,
    )

    if (
        choice < 1
        or choice > len(tools)
    ):
        raise ValidationError(
            "Invalid tool selection.",
            user_message="Invalid tool selection.",
        )

    return tools[
        choice - 1
    ]