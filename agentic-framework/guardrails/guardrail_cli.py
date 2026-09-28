"""
Guardrail management CLI commands.
"""

from __future__ import annotations

import ast
import json

import typer
from src.cli.prompts import prompt, reset_navigation_notice, confirm
from src.cli.navigation import CLIBack, CLIExit

from src.config import (
    GUARDRAIL_DEFINITIONS_DIR,
    GUARDRAIL_IMPLEMENTATIONS_DIR,
)

from src.llm.gateway import LLMGateway

from src.cli.ui import (
    error,
    menu,
    info,
)

from guardrails import (
    GuardrailCommands,
    GuardrailRegistry,
)

from guardrails.guardrail_factory import (
    GuardrailFactory,
)


def guardrail_menu():
    """Display guardrail management menu."""

    commands = GuardrailCommands()

    while True:

        menu(
            "Guardrails",
            [
                "1. Create Guardrail",
                "2. View Guardrail",
                "3. List Guardrails",
                "4. Edit a Guardrail",
                "5. Delete a Guardrail",
            ],
            breadcrumb="Home > Guardrails",
            subtitle="Choose an action. Use B to go back one screen or 0 to exit.",
            module_navigation=True
        )

        choice = prompt("Select an option", navigation=False).strip()

        try:

            if choice == "1":
                create_guardrail_cmd(commands)

            elif choice == "2":
                view_guardrail_cmd(commands)

            elif choice == "3":
                list_guardrails_cmd(commands)

            elif choice == "4":
                update_guardrail_cmd(commands)

            elif choice == "5":
                delete_guardrail_cmd(commands)

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
        except typer.Abort:

            typer.secho(
                "\nAborted!",
                fg=typer.colors.RED,
            )

        except Exception as exc:

            error(str(exc))


def list_guardrails_cmd(
    commands: GuardrailCommands,
):
    """List all guardrails."""

    guardrail_ids = commands.list()

    if not guardrail_ids:

        typer.echo(
            "No guardrails found."
        )

        return

    typer.echo(
        "\nGuardrails:"
    )

    for guardrail_id in guardrail_ids:

        typer.echo(
            f"  - {guardrail_id}"
        )

    typer.echo(
        "\nDetails:"
    )

    registry = GuardrailRegistry()

    for guardrail_id in guardrail_ids:

        spec = registry.get_spec(
            guardrail_id
        )

        typer.echo(
            f"\n{spec.id}:"
        )

        typer.echo(
            f"  Name: {spec.name}"
        )

        typer.echo(
            f"  Type: {spec.type}"
        )

        typer.echo(
            f"  Action: {spec.action}"
        )

        typer.echo(
            f"  Enabled: {spec.enabled}"
        )

        typer.echo(
            f"  Description: {spec.description}"
        )

        typer.echo(
            f"  Implementation: "
            f"{spec.implementation_file}"
        )


def view_guardrail_cmd(
    commands: GuardrailCommands,
):
    """View a guardrail selected by its visible list number."""

    guardrail_ids = commands.list()
    if not guardrail_ids:
        info("No guardrails are available.")
        return

    typer.echo("\nSelect a guardrail:\n")
    registry = GuardrailRegistry()
    for index, guardrail_id in enumerate(guardrail_ids, start=1):
        try:
            spec = registry.get_spec(guardrail_id)
            typer.echo(f"  {index}. {spec.name}")
        except KeyError:
            typer.echo(f"  {index}. {guardrail_id}")

    selection = prompt("Enter number").strip()
    if not selection.isdigit():
        raise ValueError("Please enter the number shown for the guardrail.")
    index = int(selection)
    if not 1 <= index <= len(guardrail_ids):
        raise ValueError(f"Please choose a number from 1 to {len(guardrail_ids)}.")

    guardrail_id = guardrail_ids[index - 1]

    try:

        spec = commands.get(
            guardrail_id
        )

        typer.echo(
            f"\nGuardrail: {spec.id}"
        )

        typer.echo(
            f"Name: {spec.name}"
        )

        typer.echo(
            f"Description: {spec.description}"
        )

        typer.echo(
            f"Type: {spec.type}"
        )

        typer.echo(
            f"Action: {spec.action}"
        )

        typer.echo(
            f"Implementation: "
            f"{spec.implementation_file}"
        )

        typer.echo(
            f"Enabled: {spec.enabled}"
        )

        typer.echo(
            f"Configuration: "
            f"{spec.configuration}"
        )

    except FileNotFoundError:

        error(
            f"Guardrail '{guardrail_id}' could not be loaded."
        )


def create_guardrail_cmd(
    commands: GuardrailCommands,
):
    """
    Create a guardrail using LLM-generated
    specification and Python implementation.
    """

    requirement = prompt(
        "\nEnter your guardrail requirement / functional description"
    ).strip()

    if not requirement:

        raise ValueError(
            "Guardrail requirement cannot be empty."
        )

    # -----------------------------------------
    # Directories
    # -----------------------------------------

    GUARDRAIL_DEFINITIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    GUARDRAIL_IMPLEMENTATIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------
    # LLM Factory
    # -----------------------------------------

    factory = GuardrailFactory(
        LLMGateway()
    )

    # -----------------------------------------
    # Generate specification
    # -----------------------------------------

    typer.echo(
        "\nGenerating guardrail specification..."
    )

    spec = factory.generate(
        requirement
    )

    typer.echo(
        f"\nGenerated Guardrail:"
    )

    typer.echo(
        f"  ID: {spec.id}"
    )

    typer.echo(
        f"  Name: {spec.name}"
    )

    typer.echo(
        f"  Type: {spec.type}"
    )

    typer.echo(
        f"  Action: {spec.action}"
    )

    typer.echo(
        f"  Description: {spec.description}"
    )

    # -----------------------------------------
    # Generate implementation
    # -----------------------------------------

    typer.echo(
        "\nGenerating Python implementation..."
    )

    code = factory.generate_implementation(
        spec
    )

    # -----------------------------------------
    # Paths
    # -----------------------------------------

    implementation_path = (
        GUARDRAIL_IMPLEMENTATIONS_DIR
        / spec.implementation_file
    )

    definition_path = (
        GUARDRAIL_DEFINITIONS_DIR
        / f"{spec.id}.yaml"
    )

    # -----------------------------------------
    # Validate Python
    # -----------------------------------------

    typer.echo(
        "Validating generated Python..."
    )

    try:

        ast.parse(
            code,
            filename=str(
                implementation_path
            ),
        )

    except SyntaxError as exc:

        raise ValueError(
            "Generated guardrail Python "
            f"contains invalid syntax: {exc}"
        )

    # -----------------------------------------
    # Existing implementation
    # -----------------------------------------

    if implementation_path.exists():

        if not confirm(
            f"{implementation_path.name} "
            "already exists. Overwrite?"
        ):

            typer.echo(
                "Creation cancelled."
            )

            return

    # -----------------------------------------
    # Existing definition
    # -----------------------------------------

    if definition_path.exists():

        if not confirm(
            f"{definition_path.name} "
            "already exists. Overwrite?"
        ):

            typer.echo(
                "Creation cancelled."
            )

            return

    # -----------------------------------------
    # Save YAML
    # -----------------------------------------

    definition_path.write_text(
        factory.to_yaml(spec),
        encoding="utf-8",
    )

    # -----------------------------------------
    # Save Python
    # -----------------------------------------

    implementation_path.write_text(
        code.rstrip() + "\n",
        encoding="utf-8",
    )

    # -----------------------------------------
    # Success
    # -----------------------------------------

    typer.secho(
        "\n✓ Guardrail definition created:",
        fg=typer.colors.GREEN,
    )

    typer.echo(
        f"  {definition_path}"
    )

    typer.secho(
        "\n✓ Guardrail implementation created:",
        fg=typer.colors.GREEN,
    )

    typer.echo(
        f"  {implementation_path}"
    )

    typer.secho(
        f"\n✓ Guardrail '{spec.id}' "
        "created successfully!",
        fg=typer.colors.GREEN,
    )


def update_guardrail_cmd(
    commands: GuardrailCommands,
):
    """Update an existing guardrail."""

    while True:
        guardrail_id = prompt(
            "Enter guardrail ID to update"
        ).strip()

        try:

            current_spec = commands.get(
                guardrail_id
            )

            typer.echo(
                f"\nUpdating guardrail: "
                f"{guardrail_id}"
            )

            typer.echo(
                "(Press Enter to keep the current value)"
            )

            name = prompt(
                f"Name [{current_spec.name}]",
                default=current_spec.name,
            ).strip()

            description = prompt(
                f"Description [{current_spec.description}]",
                default=current_spec.description,
            ).strip()

            guardrail_type = prompt(
                f"Type [{current_spec.type}]",
                default=current_spec.type,
            ).strip()

            action = prompt(
                f"Action [{current_spec.action}]",
                default=current_spec.action,
            ).strip()

            enabled_str = prompt(
                f"Enabled [{current_spec.enabled}]",
                default=str(
                    current_spec.enabled
                ).lower(),
            ).strip().lower()

            enabled = enabled_str in (
                "true",
                "yes",
                "1",
                "y",
            )

            config_str = prompt(
                "Configuration (JSON, blank to keep current)",
                default="",
            ).strip()

            if config_str:

                try:

                    configuration = json.loads(
                        config_str
                    )

                except json.JSONDecodeError:

                    error(
                        "Invalid JSON for configuration."
                    )

                    return

            else:

                configuration = (
                    current_spec.configuration
                )

            commands.update(
                guardrail_id=guardrail_id,
                name=name,
                description=description,
                guardrail_type=guardrail_type,
                implementation_file=(
                    current_spec.implementation_file
                ),
                action=action,
                configuration=configuration,
                enabled=enabled,
            )

            typer.secho(
                f"\nGuardrail '{guardrail_id}' "
                "updated successfully!",
                fg=typer.colors.GREEN,
            )

        except FileNotFoundError:

            error(
                f"Guardrail '{guardrail_id}' "
                "not found."
            )

        except CLIBack:
            info("Back to guardrail selection.")
            continue

def delete_guardrail_cmd(
    commands: GuardrailCommands,
):
    """Delete a guardrail."""

    guardrail_id = prompt(
        "Enter guardrail ID to delete"
    ).strip()

    confirm = confirm(
        f"Are you sure you want to delete "
        f"'{guardrail_id}'?"
    )

    if not confirm:

        typer.echo(
            "Deletion cancelled."
        )

        return

    try:

        commands.delete(
            guardrail_id
        )

        typer.secho(
            f"Guardrail '{guardrail_id}' "
            "deleted successfully!",
            fg=typer.colors.GREEN,
        )

    except FileNotFoundError:

        error(
            f"Guardrail '{guardrail_id}' "
            "not found."
        )