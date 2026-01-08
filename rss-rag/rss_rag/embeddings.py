"""Embedding model loading and management."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Protocol, runtime_checkable

import numpy as np

from rss_rag.config import get_config

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbeddingModel(Protocol):
    """Protocol for embedding models."""

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        ...


class SentenceTransformerEmbeddings:
    """Wrapper for sentence-transformers embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the embedding model.

        Args:
            model_name: Name of the sentence-transformers model
        """
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading sentence-transformers model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode

        Returns:
            Numpy array of shape (len(texts), dimension)
        """
        return self.model.encode(texts, convert_to_numpy=True)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text to embedding."""
        return self.encode([text])[0]


class OpenAIEmbeddings:
    """Wrapper for OpenAI embeddings."""

    def __init__(self, model_name: str = "text-embedding-3-small"):
        """Initialize OpenAI embeddings.

        Args:
            model_name: OpenAI embedding model name
        """
        from langchain_openai import OpenAIEmbeddings as LCOpenAIEmbeddings

        logger.info(f"Initializing OpenAI embeddings: {model_name}")
        self.model = LCOpenAIEmbeddings(model=model_name)
        self.model_name = model_name
        # OpenAI text-embedding-3-small is 1536 dimensions
        self._dimension_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        self.dimension = self._dimension_map.get(model_name, 1536)

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode texts to embeddings."""
        embeddings = self.model.embed_documents(texts)
        return np.array(embeddings)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text to embedding."""
        embedding = self.model.embed_query(text)
        return np.array(embedding)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformerEmbeddings | OpenAIEmbeddings:
    """Get the configured embedding model.

    Returns cached instance.
    """
    config = get_config()
    embeddings_config = config.embeddings

    if embeddings_config.provider == "sentence-transformers":
        return SentenceTransformerEmbeddings(embeddings_config.model)
    elif embeddings_config.provider == "openai":
        return OpenAIEmbeddings(embeddings_config.model)
    else:
        raise ValueError(
            f"Unsupported embedding provider: {embeddings_config.provider}"
        )


def clear_embedding_cache() -> None:
    """Clear the embedding model cache."""
    get_embedding_model.cache_clear()
