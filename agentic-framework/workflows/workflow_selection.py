"""Workflow selection helpers for the Enterprise Agent Framework."""

import typer
from src.cli.prompts import prompt

from src.exceptions import (
    ValidationError,
    exception_handler,
)


PRACTICE_AREAS = [
    "Testing",
    "AI/ML",
    "API & Integration",
    "Backend Engineering",
    "Business Operations",
    "Cloud & DevOps",
    "Cross-Functional",
    "Data Engineering",
    "Experience Design",
    "Legacy Modernization",
    "Product Management",
    "Quality Engineering",
    "Security & Compliance",
    "UI Engineering",
]


GOOD_AT_OPTIONS = [
    "instruction",
    "monitoring",
    "refactor",
    "qa",
    "scheduling",
    "validation",
    "parser",
    "orchestration",
    "automation",
    "retrieval and parser",
    "retrieval",
    "UX-testing",
    "conversion",
    "generation",
    "exporter",
    "summarization",
    "embedding",
    "regex-filter",
    "classification",
    "review",
    "integration",
]


@exception_handler("workflow.selection.practice_area")
def select_practice_area() -> str:
    """Select a workflow practice area."""

    typer.echo("\nPractice Area\n")

    for index, practice_area in enumerate(
        PRACTICE_AREAS,
        start=1,
    ):
        typer.echo(
            f"{index}. {practice_area}"
        )

    choice = prompt(
        "Select Practice Area",
        default="1",
    ).strip()

    if not choice:
        return "Testing"

    if not choice.isdigit():
        raise ValidationError(
            "Practice Area selection must be a number.",
            user_message=(
                "Practice Area selection must be a number."
            ),
        )

    index = int(choice)

    if index < 1 or index > len(PRACTICE_AREAS):
        raise ValidationError(
            "Invalid Practice Area selection.",
            user_message=(
                "Invalid Practice Area selection."
            ),
        )

    return PRACTICE_AREAS[index - 1]


@exception_handler("workflow.selection.good_at")
def select_good_at() -> list[str]:
    """Select workflow capabilities."""

    typer.echo("\nGood At\n")

    for index, option in enumerate(
        GOOD_AT_OPTIONS,
        start=1,
    ):
        typer.echo(
            f"{index}. {option}"
        )

    typer.echo(
        "\nEnter multiple numbers separated by commas."
    )

    selection = prompt(
        "Select Good At",
        default="",
    ).strip()

    if not selection:
        return []

    selected = []

    for value in selection.split(","):

        value = value.strip()

        if not value.isdigit():
            raise ValidationError(
                f"Invalid Good At selection: {value}",
                user_message=(
                    f"Invalid Good At selection: {value}"
                ),
            )

        index = int(value)

        if index < 1 or index > len(GOOD_AT_OPTIONS):
            raise ValidationError(
                f"Invalid Good At selection: {index}",
                user_message=(
                    f"Invalid Good At selection: {index}"
                ),
            )

        option = GOOD_AT_OPTIONS[index - 1]

        if option not in selected:
            selected.append(option)

    return selected