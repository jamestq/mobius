"""Tests for ingestion module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rss_rag.database import add_article, add_feed, get_connection, init_db
from rss_rag.ingestion import (
    IngestionResult,
    _generate_doc_id,
    get_ingested_count,
    get_pending_count,
    ingest_article,
    reset_lightrag_instance,
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
    add_article(
        conn,
        feed_id,
        title="Test Article 1",
        content="Test content 1",
        link="https://example.com/article1",
        pub_date=None,
    )
    add_article(
        conn,
        feed_id,
        title="Test Article 2",
        content="Test content 2",
        link="https://example.com/article2",
        pub_date=None,
    )
    conn.close()

    yield path
    path.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def reset_rag():
    """Reset LightRAG instance before and after each test."""
    reset_lightrag_instance()
    yield
    reset_lightrag_instance()


class TestGenerateDocId:
    """Tests for _generate_doc_id function."""

    def test_generates_consistent_id(self):
        """Same link should generate same ID."""
        link = "https://example.com/article1"
        id1 = _generate_doc_id(link)
        id2 = _generate_doc_id(link)
        assert id1 == id2

    def test_different_links_different_ids(self):
        """Different links should generate different IDs."""
        id1 = _generate_doc_id("https://example.com/article1")
        id2 = _generate_doc_id("https://example.com/article2")
        assert id1 != id2

    def test_returns_string(self):
        """Should return a string."""
        doc_id = _generate_doc_id("https://example.com/article")
        assert isinstance(doc_id, str)
        assert len(doc_id) == 32  # MD5 hex digest length


class TestGetPendingCount:
    """Tests for get_pending_count function."""

    def test_counts_pending_articles(self, db_path):
        """Should count articles with NULL lightrag_id."""
        count = get_pending_count(db_path)
        assert count == 2

    def test_excludes_ingested_articles(self, db_path):
        """Should not count articles that have lightrag_id."""
        # Mark one as ingested
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE articles SET lightrag_id = 'test-id' WHERE id = 1")
        conn.commit()
        conn.close()

        count = get_pending_count(db_path)
        assert count == 1

    def test_returns_zero_when_all_ingested(self, db_path):
        """Should return 0 when all articles are ingested."""
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE articles SET lightrag_id = 'test-id'")
        conn.commit()
        conn.close()

        count = get_pending_count(db_path)
        assert count == 0


class TestGetIngestedCount:
    """Tests for get_ingested_count function."""

    def test_counts_ingested_articles(self, db_path):
        """Should count articles with non-NULL lightrag_id."""
        # Initially none ingested
        count = get_ingested_count(db_path)
        assert count == 0

        # Mark one as ingested
        conn = get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE articles SET lightrag_id = 'test-id' WHERE id = 1")
        conn.commit()
        conn.close()

        count = get_ingested_count(db_path)
        assert count == 1


class TestIngestArticle:
    """Tests for ingest_article function."""

    def test_successful_ingestion(self):
        """Should return success result on successful ingestion."""
        mock_rag = MagicMock()
        mock_rag.ainsert = AsyncMock()

        result = ingest_article(
            mock_rag,
            article_id=1,
            title="Test Article",
            content="Test content",
            link="https://example.com/test",
        )

        assert result.success is True
        assert result.article_id == 1
        assert result.error is None
        assert result.lightrag_id is not None
        mock_rag.ainsert.assert_called_once()

    def test_failed_ingestion(self):
        """Should return error result on failed ingestion."""
        mock_rag = MagicMock()
        mock_rag.ainsert = AsyncMock(side_effect=Exception("API Error"))

        result = ingest_article(
            mock_rag,
            article_id=1,
            title="Test Article",
            content="Test content",
            link="https://example.com/test",
        )

        assert result.success is False
        assert result.article_id == 1
        assert "API Error" in result.error

    def test_empty_content_handling(self):
        """Should handle empty content gracefully."""
        mock_rag = MagicMock()
        mock_rag.ainsert = AsyncMock()

        result = ingest_article(
            mock_rag,
            article_id=1,
            title="Test Article",
            content="",
            link="https://example.com/test",
        )

        assert result.success is True
        # Should have been called with title and URL even with empty content
        mock_rag.ainsert.assert_called_once()

    def test_none_content_handling(self):
        """Should handle None content gracefully."""
        mock_rag = MagicMock()
        mock_rag.ainsert = AsyncMock()

        result = ingest_article(
            mock_rag,
            article_id=1,
            title="Test Article",
            content=None,
            link="https://example.com/test",
        )

        assert result.success is True


class TestIngestionResult:
    """Tests for IngestionResult dataclass."""

    def test_success_result(self):
        """Should create success result correctly."""
        result = IngestionResult(
            article_id=1,
            title="Test",
            success=True,
            lightrag_id="doc-123",
        )
        assert result.article_id == 1
        assert result.title == "Test"
        assert result.success is True
        assert result.lightrag_id == "doc-123"
        assert result.error is None

    def test_error_result(self):
        """Should create error result correctly."""
        result = IngestionResult(
            article_id=1,
            title="Test",
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.lightrag_id is None
