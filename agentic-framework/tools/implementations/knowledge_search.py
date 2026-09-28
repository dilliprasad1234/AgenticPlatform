"""Search a named RAG knowledge base collection for context relevant to a question."""

from typing import Any
from tools.base import BaseTool
from src import config


class KnowledgeSearchTool(BaseTool):
    """Retrieves the most relevant indexed document chunks for a question,
    from a specific named collection (multiple isolated knowledge bases
    can coexist, each in its own collection)."""

    def execute(self, question: str, collection: str = "eaf_knowledge", top_k: int = 5) -> list[dict[str, Any]]:
        """Search a knowledge base collection for context relevant to *question*.

        Args:
            question: The question to search the knowledge base for.
            collection: Name of the collection to search. Must match the
                --collection name used when the documents were indexed via
                `eaf index-document`. Defaults to "eaf_knowledge".
            top_k: Number of matching chunks to return.

        Returns:
            A list of {"text": ..., "source": ...} dicts, or a single
            informational entry if the collection is empty/missing.
        """
        from src.rag.vector_store import VectorStore
        from src.rag.retriever import Retriever
        from src.exceptions import RAGError

        if not question or not question.strip():
            raise ValueError("question must not be empty.")
        if not collection or not collection.strip():
            collection = "eaf_knowledge"

        try:
            store = VectorStore(persist_path=config.CHROMADB_PATH, collection_name=collection)
        except RAGError as exc:
            return [{"text": f"RAG is not available: {exc}", "source": "system"}]

        retriever = Retriever(store=store, top_k=top_k)
        results = retriever.retrieve_with_sources(question)

        if not results:
            return [{"text": f"No relevant documents found in collection '{collection}'.", "source": "system"}]
        return results