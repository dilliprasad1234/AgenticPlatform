"""Individual action handlers for Knowledge Base (RAG collection) management."""

import shutil
from pathlib import Path

import typer

from src import config
from src.cli.ui import console, error, info, success
from src.exceptions import (
    RAGError,
    exception_handler,
    translate_runtime_error,
    validate_rag_file_size,
)
from src.rag.vector_store import VectorStore


def _add_documents_loop(
    collection: str,
    dest_dir: Path,
) -> int:
    """Internal helper for adding and indexing documents."""

    dest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    indexed = 0

    while True:
        filepath = (
            typer.prompt("Path to document")
            .strip()
            .strip('"')
        )

        src = Path(filepath)
        dest = dest_dir / src.name

        try:
            # Pre-flight validation: existence, file type, non-empty, and size limit
            validate_rag_file_size(
                src,
                max_size_mb=config.MAX_RAG_FILE_SIZE_MB,
                knowledge_base=collection,
            )

            shutil.copy2(
                src,
                dest,
            )

            store = VectorStore(
                persist_path=config.CHROMADB_PATH,
                collection_name=collection,
            )

            n = store.index_file(dest)

            info(
                f"Indexed '{src.name}' "
                f"({n} chunk(s))"
            )

            indexed += 1

        except RAGError as exc:
            dest.unlink(missing_ok=True)
            error(
                f"Could not index "
                f"'{src.name}': {exc.user_message}"
            )

        except OSError as exc:
            dest.unlink(missing_ok=True)
            error(
                f"Could not copy or access "
                f"'{src.name}': {exc}"
            )

        except Exception as exc:  # noqa: BLE001
            dest.unlink(missing_ok=True)
            translated = translate_runtime_error(exc)
            error(
                f"Failed to process '{src.name}': {translated}"
            )

        if not typer.confirm(
            "Add another document?",
            default=True,
        ):
            break

    return indexed


@exception_handler("rag.create")
def create() -> None:
    """Execute the create operation."""

    collection = typer.prompt(
        "New collection name"
    ).strip()

    if not collection:
        raise RAGError(
            "Knowledge base collection name is empty.",
            user_message="Collection name must not be empty.",
        )

    existing = _list_collection_names()

    if collection in existing:
        raise RAGError(
            f"Knowledge base '{collection}' already exists.",
            user_message=(
                f"'{collection}' already exists. "
                "Use 'Add Document to Knowledge Base' "
                "instead to add more to it."
            ),
        )

    dest_dir = (
        config.PROJECT_ROOT
        / "inputs"
        / "rag"
        / collection
    )

    indexed = _add_documents_loop(
        collection,
        dest_dir,
    )

    if indexed == 0:
        raise RAGError(
            f"No documents were indexed for '{collection}'.",
            user_message=(
                f"No documents were indexed. "
                f"'{collection}' was not created."
            ),
        )

    success(
        f"'{collection}' is added. "
        f"({indexed} document(s) indexed, "
        f"saved to {dest_dir})"
    )


@exception_handler("rag.add_document")
def add_document() -> None:
    """Execute the add document operation."""

    existing = _list_collection_names()

    if not existing:
        raise RAGError(
            "No knowledge bases exist.",
            user_message=(
                "No knowledge bases exist yet. "
                "Use 'Create Knowledge Base' first."
            ),
        )

    console.print(
        "[bold]Existing knowledge bases:[/bold] "
        + ", ".join(existing)
    )

    collection = typer.prompt(
        "Which collection do you want to add documents to?"
    ).strip()

    if collection not in existing:
        raise RAGError(
            f"Knowledge base '{collection}' does not exist.",
            user_message=(
                f"'{collection}' does not exist. "
                "Use 'Create Knowledge Base' to make a new one."
            ),
        )

    dest_dir = (
        config.PROJECT_ROOT
        / "inputs"
        / "rag"
        / collection
    )

    indexed = _add_documents_loop(
        collection,
        dest_dir,
    )

    if indexed == 0:
        info("No documents were added.")
        return

    success(
        f"Added {indexed} document(s) "
        f"to '{collection}'."
    )


def _list_collection_names() -> list[str]:
    """Internal helper for retrieving collection names."""

    return VectorStore.list_collections(
        config.CHROMADB_PATH
    )


@exception_handler("rag.list")
def list_all() -> None:
    """Execute the list all operation."""

    names = VectorStore.list_collections(
        config.CHROMADB_PATH
    )

    if not names:
        info("No knowledge bases found.")
        return

    for name in names:
        store = VectorStore(
            persist_path=config.CHROMADB_PATH,
            collection_name=name,
        )

        sources = store.list_sources()

        console.print(
            f"[bold]{name}[/bold]  "
            f"({len(sources)} document(s): "
            f"{', '.join(sources) or '—'})"
        )


@exception_handler("rag.remove_document")
def remove_document() -> None:
    """Execute the remove document operation."""

    collection = typer.prompt(
        "Collection name",
        default="eaf_knowledge",
    ).strip()

    filename = typer.prompt(
        "Document filename to remove"
    ).strip()

    store = VectorStore(
        persist_path=config.CHROMADB_PATH,
        collection_name=collection,
    )

    n = store.remove_document(filename)

    if n == 0:
        raise RAGError(
            f"No chunks found for '{filename}' "
            f"in collection '{collection}'.",
            user_message=(
                f"No chunks found for '{filename}' "
                f"in collection '{collection}'."
            ),
        )

    success(
        f"Removed {n} chunk(s) for "
        f"'{filename}' from '{collection}'."
    )


@exception_handler("rag.delete")
def delete() -> None:
    """Execute the delete operation."""

    collection = typer.prompt(
        "Collection name to delete"
    ).strip()

    if not typer.confirm(
        f"Delete '{collection}' and ALL its documents? "
        "This cannot be undone."
    ):
        info("Cancelled.")
        return

    VectorStore.delete_collection(
        config.CHROMADB_PATH,
        collection,
    )

    success(
        f"'{collection}' deleted."
    )