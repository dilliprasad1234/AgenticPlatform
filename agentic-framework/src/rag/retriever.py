"""High-level retrieval interface for augmenting agent context."""

from src.exceptions import RAGError, exception_handler
from src.rag.vector_store import VectorStore


class Retriever:
    """Fetches relevant context chunks for a query before agent execution."""

    def __init__(
        self,
        store: VectorStore,
        top_k: int = 5,
    ) -> None:
        """Initialize the object with the supplied configuration."""
        self.store = store
        self.top_k = top_k

    @exception_handler("rag.retriever.retrieve")
    def retrieve(
        self,
        query: str,
    ) -> list[str]:
        """Retrieve relevant document chunks for a query."""

        if not query or not query.strip():
            raise RAGError(
                "Retrieval query must not be empty.",
                user_message="Retrieval query must not be empty.",
            )

        try:
            result = self.store.query(
                query,
                n_results=self.top_k,
            )

        except RAGError:
            raise

        except Exception as exc:
            raise RAGError(
                f"Failed to retrieve documents: {exc}",
                user_message="Failed to retrieve documents.",
            ) from exc

        documents = result.get(
            "documents",
            [[]],
        )

        if not documents:
            return []

        return documents[0]

    @exception_handler("rag.retriever.retrieve_with_sources")
    def retrieve_with_sources(
        self,
        query: str,
    ) -> list[dict]:
        """Retrieve relevant document chunks together with their sources."""

        if not query or not query.strip():
            raise RAGError(
                "Retrieval query must not be empty.",
                user_message="Retrieval query must not be empty.",
            )

        try:
            result = self.store.query(
                query,
                n_results=self.top_k,
            )

        except RAGError:
            raise

        except Exception as exc:
            raise RAGError(
                f"Failed to retrieve documents with sources: {exc}",
                user_message="Failed to retrieve documents.",
            ) from exc

        documents = result.get(
            "documents",
            [[]],
        )

        metadatas = result.get(
            "metadatas",
            [[]],
        )

        if not documents:
            return []

        docs = documents[0]

        if not metadatas:
            metas = [{} for _ in docs]
        else:
            metas = metadatas[0]

        return [
            {
                "text": document,
                "source": (metadata or {}).get(
                    "source",
                    "unknown",
                ),
            }
            for document, metadata in zip(
                docs,
                metas,
            )
        ]