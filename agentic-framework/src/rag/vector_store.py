"""ChromaDB-backed vector store for RAG support."""

from pathlib import Path

from src.exceptions import RAGError, exception_handler


class VectorStore:
    """Thin wrapper around a ChromaDB persistent collection."""

    def __init__(
        self,
        persist_path: Path,
        collection_name: str = "eaf_knowledge",
    ) -> None:
        """Initialize the object with the supplied configuration."""

        try:
            import chromadb
        except ImportError as exc:
            raise RAGError(
                "Install ChromaDB with: pip install -e '.[rag]'"
            ) from exc

        self.persist_path = persist_path
        self.collection_name = collection_name

        self._client = chromadb.PersistentClient(
            path=str(persist_path)
        )

        self._collection = (
            self._client.get_or_create_collection(
                collection_name
            )
        )

    @exception_handler("rag.vector_store.add_documents")
    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict] | None = None,
        batch_size: int = 1000,
    ) -> None:
        """Execute the add documents operation in safe batches."""
        if not ids or not documents:
            return

        # Constrain batch size by ChromaDB's max_batch_size (typically 5,461 in SQLite)
        try:
            max_batch = self._client.get_max_batch_size()
        except (AttributeError, RuntimeError, ValueError):
            max_batch = 5461

        safe_batch_size = max(1, min(batch_size, max_batch - 100 if max_batch > 100 else max_batch))

        total = len(ids)
        for i in range(0, total, safe_batch_size):
            batch_ids = ids[i : i + safe_batch_size]
            batch_docs = documents[i : i + safe_batch_size]
            batch_meta = (
                metadatas[i : i + safe_batch_size]
                if metadatas is not None
                else None
            )

            try:
                self._collection.add(
                    ids=batch_ids,
                    documents=batch_docs,
                    metadatas=batch_meta,
                )
            except Exception as exc:
                raise RAGError(
                    f"Failed to add document batch ({i}..{min(i + safe_batch_size, total)}) to "
                    f"'{self.collection_name}': {exc}",
                    knowledge_base=self.collection_name,
                    user_message=(
                        f"Failed to ingest document chunks into knowledge base '{self.collection_name}'. "
                        f"Details: {exc}"
                    ),
                ) from exc

    @exception_handler("rag.vector_store.index_file")
    def index_file(
        self,
        filepath: Path,
        chunk_size: int = 800,
        overlap: int = 100,
    ) -> int:
        """Execute the index file operation."""

        from src.rag.text_extraction import extract_text

        filepath = Path(filepath)
        filename = filepath.name

        if chunk_size <= 0:
            raise RAGError(
                "Chunk size must be greater than zero."
            )

        if overlap < 0:
            raise RAGError(
                "Chunk overlap cannot be negative."
            )

        if overlap >= chunk_size:
            raise RAGError(
                "Chunk overlap must be smaller than chunk size."
            )

        text = extract_text(filepath)

        chunks: list[str] = []
        start = 0

        while start < len(text):
            chunk = text[
                start:start + chunk_size
            ].strip()

            if chunk:
                chunks.append(chunk)

            start += chunk_size - overlap

        if not chunks:
            raise RAGError(
                f"No content to index in '{filename}'."
            )

        ids = [
            f"{filename}::{i}"
            for i in range(len(chunks))
        ]

        metadatas = [
            {
                "source": filename,
                "chunk": i,
            }
            for i in range(len(chunks))
        ]

        self.add_documents(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        return len(chunks)

    @exception_handler("rag.vector_store.query")
    def query(
        self,
        text: str,
        n_results: int = 5,
    ) -> dict:
        """Execute the query operation."""

        return self._collection.query(
            query_texts=[text],
            n_results=n_results,
        )

    @exception_handler("rag.vector_store.remove_document")
    def remove_document(
        self,
        source_filename: str,
    ) -> int:
        """Execute the remove document operation."""

        existing = self._collection.get(
            where={
                "source": source_filename
            }
        )

        ids = existing.get(
            "ids",
            [],
        )

        if not ids:
            return 0

        self._collection.delete(
            ids=ids
        )

        return len(ids)

    @exception_handler("rag.vector_store.list_sources")
    def list_sources(self) -> list[str]:
        """Execute the list sources operation."""

        data = self._collection.get()

        sources = {
            metadata.get(
                "source",
                "unknown",
            )
            for metadata in (
                data.get("metadatas") or []
            )
            if metadata
        }

        return sorted(sources)

    @staticmethod
    @exception_handler("rag.vector_store.list_collections")
    def list_collections(
        persist_path: Path,
    ) -> list[str]:
        """Execute the list collections operation."""

        try:
            import chromadb
        except ImportError as exc:
            raise RAGError(
                "Install ChromaDB with: pip install -e '.[rag]'"
            ) from exc

        client = chromadb.PersistentClient(
            path=str(persist_path)
        )

        return sorted(
            collection.name
            for collection in client.list_collections()
        )

    @staticmethod
    @exception_handler("rag.vector_store.delete_collection")
    def delete_collection(
        persist_path: Path,
        collection_name: str,
    ) -> None:
        """Execute the delete collection operation."""

        try:
            import chromadb
        except ImportError as exc:
            raise RAGError(
                "Install ChromaDB with: pip install -e '.[rag]'"
            ) from exc

        client = chromadb.PersistentClient(
            path=str(persist_path)
        )

        client.delete_collection(
            collection_name
        )