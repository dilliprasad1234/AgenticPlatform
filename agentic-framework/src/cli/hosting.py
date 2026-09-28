"""Module containing hosting functionality for the Enterprise Agent Framework."""

import typer


def select_hosting() -> str:

    """Execute the select hosting operation."""
    typer.echo(
        "\n============================================================="
    )

    typer.echo(
        "                    Hosting Selection"
    )

    typer.echo(
        "============================================================="
    )

    typer.echo(
        "\n1. Run Local Python Project"
    )

    typer.echo(
        "2. Run Docker Image"
    )

    typer.echo(
        "3. Exit"
    )

    while True:

        choice = typer.prompt(
            "\nSelect hosting option"
        ).strip()

        if choice == "1":
            return "python"

        if choice == "2":
            return "docker"

        if choice == "3":
            return "exit"

        typer.echo(
            "Please select 1, 2, or 3."
        )