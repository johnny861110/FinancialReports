"""Text embedding for question-directed chunk retrieval.

sentence-transformers ships in the optional `vector` extra, so this module must
import cleanly without it: CI installs only the dev group, and the API answers
section-filtered requests whether or not a model is present. The model is
loaded lazily on first use and cached.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

logger = logging.getLogger(__name__)

# Chinese-capable model at 768 dimensions, matching VECTOR(768) in schema.sql.
# Changing either without the other silently breaks inserts, so the dimension
# is asserted at encode time.
DEFAULT_MODEL = "BAAI/bge-base-zh-v1.5"
EMBEDDING_DIM = 768


def model_name() -> str:
    return os.getenv("FR_EMBEDDING_MODEL", DEFAULT_MODEL)


def is_available() -> bool:
    """True when sentence-transformers is installed."""
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


@lru_cache(maxsize=1)
def _load_model(name: str) -> Any:
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model %s", name)
    return SentenceTransformer(name)


def encode(texts: list[str], *, batch_size: int = 64) -> list[list[float]]:
    """Embed texts, returning L2-normalised vectors.

    Normalising means cosine distance and inner product agree, which keeps the
    pgvector index (vector_cosine_ops) consistent with the scores reported to
    callers.
    """
    if not texts:
        return []
    if not is_available():
        raise RuntimeError(
            "sentence-transformers is not installed. Install the vector extra: "
            "uv sync --extra vector"
        )

    model = _load_model(model_name())
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    if vectors.shape[1] != EMBEDDING_DIM:
        raise RuntimeError(
            f"model {model_name()!r} produces {vectors.shape[1]} dimensions, "
            f"but the schema stores VECTOR({EMBEDDING_DIM})"
        )
    return [vector.tolist() for vector in vectors]


def encode_question(question: str) -> list[float] | None:
    """Embed one question, or return None when embedding is unavailable.

    Returning None rather than raising lets the API degrade to importance
    ordering instead of failing a request outright. Both degraded paths log at
    warning: this used to return None on the first line with no message at all,
    so the common failure -- the optional `vector` extra simply not installed --
    left no trace anywhere, and a caller could not tell a semantic search from
    a question that was silently ignored. The caller reports the same condition
    to the consumer; see APIRepository.uses_semantic_ranking.
    """
    if not question:
        return None
    if not is_available():
        logger.warning(
            "sentence-transformers is not installed, so the question was not "
            "embedded and retrieval fell back to importance ordering. Install "
            "the vector extra (uv sync --extra vector) to enable semantic search."
        )
        return None
    try:
        return encode([question])[0]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Question embedding failed, falling back: %s", exc)
        return None
