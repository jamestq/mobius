"""Tests for discovery module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile

from rss_rag.discovery import (
    Recommendation,
    DiscoveryResult,
    discover_articles,
    format_discovery_result,
)
from rss_rag.database import (
    init_db,
    get_connection,
    add_feed,
    add_article,
    add_reading_history,
)


@pytest.fixture
def db_path():
    """Create a temporary database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    init_db(path)

    # Add test data
    conn = get_connection(path)
    feed_id = add_feed(conn, "https://example.com/feed", "Test Feed")

    # Add articles
    for i in range(5):
        add_article(
            conn,
            feed_id,
            title=f"Test Article {i+1}",
            content=f"Content for article {i+1}",
            link=f"https://example.com/article{i+1}",
            pub_date=None,
        )

    # Mark some as read
    add_reading_history(conn, 1, "read")
    add_reading_history(conn, 2, "read")

    conn.close()

    yield path
    path.unlink()


class TestRecommendation:
    def test_recommendation_creation(self):
        rec = Recommendation(
            article_id=1,
            title="Test Article",
            link="https://example.com",
            explanation="Test explanation",
            score=0.9,
        )

        assert rec.article_id == 1
        assert rec.title == "Test Article"
        assert rec.score == 0.9


class TestDiscoveryResult:
    def test_empty_result(self):
        result = DiscoveryResult()

        assert result.recommendations == []
        assert result.error is None

    def test_error_result(self):
        result = DiscoveryResult(error="Test error")

        assert result.error == "Test error"


class TestFormatDiscoveryResult:
    def test_formats_recommendations(self):
        result = DiscoveryResult(
            recommendations=[
                Recommendation(
                    article_id=1,
                    title="Great Article",
                    link="https://example.com/great",
                    explanation="Based on your interests",
                )
            ],
            reading_patterns="Interested in tech and AI",
        )

        formatted = format_discovery_result(result)

        assert "Reading Patterns" in formatted
        assert "Great Article" in formatted
        assert "https://example.com/great" in formatted

    def test_formats_error(self):
        result = DiscoveryResult(error="Connection failed")

        formatted = format_discovery_result(result)

        assert "Error:" in formatted
        assert "Connection failed" in formatted

    def test_formats_no_recommendations(self):
        result = DiscoveryResult(recommendations=[])

        formatted = format_discovery_result(result)

        assert "No recommendations" in formatted


class TestDiscoverArticles:
    @patch("rss_rag.discovery.get_lightrag_instance")
    @patch("rss_rag.discovery.get_discovery_llm")
    def test_returns_recommendations(self, mock_llm, mock_rag, db_path):
        # Mock LLM
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(
            return_value=MagicMock(content="Interested in tech")
        )
        mock_llm.return_value = mock_llm_instance

        # Mock RAG
        mock_rag_instance = MagicMock()
        mock_rag_instance.aquery = AsyncMock(return_value="Related articles found")
        mock_rag.return_value = mock_rag_instance

        result = discover_articles(db_path, limit=3)

        assert result.error is None
        assert len(result.recommendations) <= 3

    def test_handles_no_reading_history(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = Path(f.name)
        init_db(path)

        # Add articles but no reading history
        conn = get_connection(path)
        feed_id = add_feed(conn, "https://example.com/feed", "Test")
        add_article(conn, feed_id, "Article", "Content", "https://example.com/1", None)
        conn.close()

        result = discover_articles(path, limit=3)

        # Should still return unread articles
        assert result.error is None

        path.unlink()
