"""Tests for LLM module."""

import pytest
from unittest.mock import patch, MagicMock

from rss_rag.llm import get_llm


class TestGetLLM:
    @patch("langchain_openai.ChatOpenAI")
    def test_get_openai_llm(self, mock_openai):
        mock_openai.return_value = MagicMock()

        llm = get_llm("openai", "gpt-4o-mini", temperature=0.5)

        mock_openai.assert_called_once_with(
            model="gpt-4o-mini",
            temperature=0.5,
        )

    @patch("langchain_anthropic.ChatAnthropic")
    def test_get_anthropic_llm(self, mock_anthropic):
        mock_anthropic.return_value = MagicMock()

        llm = get_llm("anthropic", "claude-sonnet-4", temperature=0.7)

        mock_anthropic.assert_called_once_with(
            model="claude-sonnet-4",
            temperature=0.7,
        )

    def test_unsupported_provider_raises(self):
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            get_llm("unsupported", "model")
