"""
Optional vector store wrapper around ChromaDB.
Gracefully degrades when chromadb is not installed.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Return True if chromadb is installed."""
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


class VectorStore:
    """
    Thin wrapper around ChromaDB for chunk embeddings.
    All methods are no-ops when chromadb is not installed.
    """

    def __init__(self, persist_dir: str | Path = "./data/vector_db") -> None:
        self._available = is_available()
        self._client = None
        self._collection = None
        if self._available:
            try:
                import chromadb

                self._client = chromadb.PersistentClient(path=str(persist_dir))
                self._collection = self._client.get_or_create_collection(
                    name="financial_chunks",
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("VectorStore initialised at %s", persist_dir)
            except Exception as exc:
                logger.warning("VectorStore init failed: %s", exc)
                self._available = False
        else:
            logger.info("chromadb not available — VectorStore disabled")

    def add_chunk(
        self,
        chunk_id: int,
        content: str,
        embedding: list[float],
        metadata: dict | None = None,
    ) -> None:
        """Add a chunk embedding to the vector store."""
        if not self._available or self._collection is None:
            return
        try:
            self._collection.upsert(
                ids=[str(chunk_id)],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata or {}],
            )
        except Exception as exc:
            logger.warning("VectorStore.add_chunk failed: %s", exc)

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict | None = None,
    ) -> list[dict]:
        """Search for similar chunks. Returns list of {id, content, distance, metadata}."""
        if not self._available or self._collection is None:
            return []
        try:
            kwargs: dict = {"query_embeddings": [query_embedding], "n_results": n_results}
            if where:
                kwargs["where"] = where
            results = self._collection.query(**kwargs)
            output = []
            ids = results.get("ids", [[]])[0]
            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            for chunk_id, doc, dist, meta in zip(ids, docs, distances, metas):
                output.append(
                    {
                        "id": int(chunk_id),
                        "content": doc,
                        "distance": dist,
                        "metadata": meta,
                    }
                )
            return output
        except Exception as exc:
            logger.warning("VectorStore.search failed: %s", exc)
            return []

    def delete_by_filing(self, filing_key: str) -> None:
        """Remove all chunks associated with a filing."""
        if not self._available or self._collection is None:
            return
        try:
            self._collection.delete(where={"filing_key": filing_key})
        except Exception as exc:
            logger.warning("VectorStore.delete_by_filing failed: %s", exc)
