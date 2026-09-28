"""Interactive selection of guardrails for agent definitions."""

import typer

from guardrails.guardrail_registry import GuardrailRegistry
from src.exceptions import ValidationError, exception_handler


@exception_handler("guardrail.selection.select")
def select_guardrails() -> list[str]:
    """Prompt the user to select available guardrail definition IDs."""

    registry = GuardrailRegistry()
    guardrails = registry.list_specs()

    typer.echo("\nGuardrails Configuration\n")

    if not guardrails:
        typer.echo("No guardrail definitions are available.")
        return []

    typer.echo("Available Guardrails:\n")

    for index, guardrail_id in enumerate(guardrails, start=1):
        spec = registry.get_spec(guardrail_id)

        typer.echo(
            f"{index}. {spec.name} "
            f"({guardrail_id}, type={spec.type})"
        )

    typer.echo("\nEnter guardrail numbers separated by commas.")
    typer.echo("Press Enter to skip guardrails.")

    selection = typer.prompt(
        "Select guardrails",
        default="",
    ).strip()

    if not selection:
        return []

    selected: list[str] = []

    for value in selection.split(","):
        value = value.strip()

        if not value.isdigit():
            raise ValidationError(
                f"Invalid guardrail selection: {value}",
                user_message="Invalid guardrail selection.",
            )

        index = int(value)

        if index < 1 or index > len(guardrails):
            raise ValidationError(
                f"Invalid guardrail selection: {index}",
                user_message="Invalid guardrail selection.",
            )

        guardrail_id = guardrails[index - 1]

        if guardrail_id not in selected:
            selected.append(guardrail_id)

    return selected