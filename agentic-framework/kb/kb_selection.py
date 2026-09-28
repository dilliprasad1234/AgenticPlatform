"""Interactive selection of available RAG knowledge-base collections."""

import typer

from src.config import CHROMADB_PATH
from src.exceptions import (
    ValidationError,
    exception_handler,
)
from src.rag.vector_store import VectorStore


@exception_handler("kb.selection.select")
def select_kbs() -> list[str]:
    """Prompt the user to select existing knowledge-base collections."""

    knowledge_bases = VectorStore.list_collections(
        CHROMADB_PATH
    )

    if not knowledge_bases:
        typer.echo(
            "\nNo indexed knowledge bases are available."
        )
        typer.echo(
            "Use the Knowledge Base menu to create one first."
        )
        return []

    typer.echo(
        "\nKnowledge Base Configuration\n"
    )

    for index, kb in enumerate(
        knowledge_bases,
        start=1,
    ):
        typer.echo(
            f"{index}. {kb}"
        )

    typer.echo(
        "\nEnter KB numbers separated by commas."
    )
    typer.echo(
        "Press Enter to skip KBs."
    )

    selection = typer.prompt(
        "Select knowledge bases",
        default="",
    ).strip()

    if not selection:
        return []

    selected: list[str] = []

    for value in selection.split(","):
        value = value.strip()

        if not value.isdigit():
            raise ValidationError(
                f"Invalid KB selection: {value}",
                user_message="Invalid knowledge base selection.",
            )

        index = int(value)

        if index < 1 or index > len(knowledge_bases):
            raise ValidationError(
                f"Invalid KB selection: {index}",
                user_message="Invalid knowledge base selection.",
            )

        kb = knowledge_bases[index - 1]

        if kb not in selected:
            selected.append(kb)

    return selected