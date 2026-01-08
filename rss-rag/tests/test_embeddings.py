"""Tests for embeddings module."""

import pytest
from unittest.mock import patch, MagicMock
import numpy as np

from rss_rag.embeddings import (
    SentenceTransformerEmbeddings,
    OpenAIEmbeddings,
    get_embedding_model,
    clear_embedding_cache,
)
from rss_rag.config import Config, EmbeddingsConfig, set_config


class TestSentenceTransformerEmbeddings:
    @patch("sentence_transformers.SentenceTransformer")
    def test_initialization(self, mock_st):
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        embeddings = SentenceTransformerEmbeddings("all-MiniLM-L6-v2")

        assert embeddings.model_name == "all-MiniLM-L6-v2"
        assert embeddings.dimension == 384

    @patch("sentence_transformers.SentenceTransformer")
    def test_encode(self, mock_st):
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])
        mock_st.return_value = mock_model

        embeddings = SentenceTransformerEmbeddings()
        result = embeddings.encode(["text1", "text2"])

        assert result.shape == (2, 384)


class TestOpenAIEmbeddings:
    @patch("langchain_openai.OpenAIEmbeddings")
    def test_initialization(self, mock_openai):
        mock_model = MagicMock()
        mock_openai.return_value = mock_model

        embeddings = OpenAIEmbeddings("text-embedding-3-small")

        assert embeddings.model_name == "text-embedding-3-small"
        assert embeddings.dimension == 1536


class TestGetEmbeddingModel:
    @patch("sentence_transformers.SentenceTransformer")
    def test_get_sentence_transformers_model(self, mock_st):
        clear_embedding_cache()
        config = Config(embeddings=EmbeddingsConfig(provider="sentence-transformers"))
        set_config(config)

        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_st.return_value = mock_model

        model = get_embedding_model()

        assert isinstance(model, SentenceTransformerEmbeddings)

        clear_embedding_cache()

    @patch.object(EmbeddingsConfig, "__init__", lambda self, **kwargs: None)
    def test_unsupported_provider_raises(self):
        """Test that unsupported provider raises ValueError."""
        clear_embedding_cache()

        # Create a config with mocked unsupported provider
        config = MagicMock()
        config.embeddings = MagicMock()
        config.embeddings.provider = "unsupported"

        with patch("rss_rag.embeddings.get_config", return_value=config):
            with pytest.raises(ValueError, match="Unsupported embedding provider"):
                get_embedding_model()

        clear_embedding_cache()
