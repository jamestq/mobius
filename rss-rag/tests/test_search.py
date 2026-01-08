"""Tests for search module."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from rss_rag.search import (
    search,
    QueryMode,
    SearchResult,
    _extract_sources,
    format_search_result,
)


class TestExtractSources:
    def test_extracts_urls(self):
        text = "Check out https://example.com/article1 and http://test.com/page"
        sources = _extract_sources(text)

        assert len(sources) == 2
        assert "https://example.com/article1" in sources
        assert "http://test.com/page" in sources

    def test_deduplicates_urls(self):
        text = "See https://example.com twice: https://example.com"
        sources = _extract_sources(text)

        assert len(sources) == 1

    def test_handles_no_urls(self):
        text = "No URLs here"
        sources = _extract_sources(text)

        assert sources == []


class TestFormatSearchResult:
    def test_formats_success_with_summary(self):
        result = SearchResult(
            query="test",
            mode=QueryMode.HYBRID,
            raw_response="Raw data",
            summary="Summarized answer",
            sources=["https://example.com"],
        )

        formatted = format_search_result(result)

        assert "Summary:" in formatted
        assert "Summarized answer" in formatted
        assert "Sources:" in formatted
        assert "https://example.com" in formatted

    def test_formats_error(self):
        result = SearchResult(
            query="test",
            mode=QueryMode.HYBRID,
            raw_response="",
            error="Connection failed",
        )

        formatted = format_search_result(result)

        assert "Error:" in formatted
        assert "Connection failed" in formatted

    def test_shows_raw_when_requested(self):
        result = SearchResult(
            query="test",
            mode=QueryMode.HYBRID,
            raw_response="Raw data",
            summary="Summary",
        )

        formatted = format_search_result(result, show_raw=True)

        assert "Raw Response" in formatted
        assert "Raw data" in formatted


class TestSearch:
    @patch("rss_rag.search.get_lightrag_instance")
    @patch("rss_rag.search.get_summarizer_llm")
    def test_successful_search(self, mock_llm, mock_rag):
        mock_rag_instance = MagicMock()
        mock_rag_instance.aquery = AsyncMock(return_value="Found article about topic")
        mock_rag.return_value = mock_rag_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Summary"))
        mock_llm.return_value = mock_llm_instance

        result = search("test query")

        assert result.error is None
        assert "Found article" in result.raw_response

    @patch("rss_rag.search.get_lightrag_instance")
    def test_search_without_summary(self, mock_rag):
        mock_rag_instance = MagicMock()
        mock_rag_instance.aquery = AsyncMock(return_value="Direct response")
        mock_rag.return_value = mock_rag_instance

        result = search("test query", summarize=False)

        assert result.summary is None
        assert result.raw_response == "Direct response"

    @patch("rss_rag.search.get_lightrag_instance")
    def test_search_handles_error(self, mock_rag):
        mock_rag.side_effect = Exception("Connection error")

        result = search("test query")

        assert result.error is not None
        assert "Connection error" in result.error


class TestQueryMode:
    def test_all_modes_exist(self):
        assert QueryMode.HYBRID.value == "hybrid"
        assert QueryMode.LOCAL.value == "local"
        assert QueryMode.GLOBAL.value == "global"
        assert QueryMode.NAIVE.value == "naive"
