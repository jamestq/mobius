"""Tests for database module."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from rss_rag.database import (
    add_article,
    add_feed,
    add_reading_history,
    article_exists,
    deactivate_feed,
    delete_feed,
    get_all_feeds,
    get_article,
    get_article_by_link,
    get_articles_by_feed,
    get_articles_without_lightrag_id,
    get_connection,
    get_feed,
    get_feed_by_url,
    get_read_article_ids,
    get_reading_history,
    get_recent_articles,
    get_stats,
    get_unread_articles,
    init_db,
    update_article_lightrag_id,
    update_feed_last_fetched,
    update_feed_title,
)


@pytest.fixture
def db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    init_db(path)
    yield path
    path.unlink()


@pytest.fixture
def conn(db_path):
    """Create a database connection."""
    conn = get_connection(db_path)
    yield conn
    conn.close()


class TestDatabaseInit:
    """Tests for database initialization."""

    def test_init_db_creates_tables(self, db_path):
        """Test that init_db creates all required tables."""
        conn = get_connection(db_path)
        try:
            # Check feeds table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='feeds'"
            )
            assert cursor.fetchone() is not None

            # Check articles table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='articles'"
            )
            assert cursor.fetchone() is not None

            # Check reading_history table exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='reading_history'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_init_db_creates_indexes(self, db_path):
        """Test that init_db creates indexes."""
        conn = get_connection(db_path)
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row["name"] for row in cursor.fetchall()]
            assert "idx_articles_feed_id" in indexes
            assert "idx_articles_link" in indexes
            assert "idx_articles_pub_date" in indexes
        finally:
            conn.close()

    def test_init_db_idempotent(self, db_path):
        """Test that init_db can be called multiple times."""
        # Should not raise
        init_db(db_path)
        init_db(db_path)


class TestFeedCRUD:
    """Tests for feed CRUD operations."""

    def test_add_and_get_feed(self, conn):
        """Test adding and retrieving a feed."""
        feed_id = add_feed(conn, "https://example.com/feed.xml", "Example Feed")
        assert feed_id is not None
        assert feed_id > 0

        feed = get_feed(conn, feed_id)
        assert feed is not None
        assert feed["url"] == "https://example.com/feed.xml"
        assert feed["title"] == "Example Feed"
        assert feed["active"] == 1

    def test_add_feed_without_title(self, conn):
        """Test adding a feed without a title."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        feed = get_feed(conn, feed_id)
        assert feed["title"] is None

    def test_add_duplicate_feed_returns_existing(self, conn):
        """Test that adding a duplicate feed returns the existing ID."""
        feed_id1 = add_feed(conn, "https://example.com/feed.xml", "Title 1")
        feed_id2 = add_feed(conn, "https://example.com/feed.xml", "Title 2")
        assert feed_id1 == feed_id2

    def test_get_feed_by_url(self, conn):
        """Test getting a feed by URL."""
        add_feed(conn, "https://example.com/feed.xml", "Example Feed")
        feed = get_feed_by_url(conn, "https://example.com/feed.xml")
        assert feed is not None
        assert feed["title"] == "Example Feed"

    def test_get_feed_by_url_not_found(self, conn):
        """Test getting a non-existent feed by URL."""
        feed = get_feed_by_url(conn, "https://nonexistent.com/feed.xml")
        assert feed is None

    def test_get_all_feeds(self, conn):
        """Test getting all feeds."""
        add_feed(conn, "https://example1.com/feed.xml", "Feed 1")
        add_feed(conn, "https://example2.com/feed.xml", "Feed 2")

        feeds = get_all_feeds(conn)
        assert len(feeds) == 2

    def test_get_all_feeds_active_only(self, conn):
        """Test getting only active feeds."""
        feed_id1 = add_feed(conn, "https://example1.com/feed.xml", "Feed 1")
        add_feed(conn, "https://example2.com/feed.xml", "Feed 2")
        deactivate_feed(conn, feed_id1)

        active_feeds = get_all_feeds(conn, active_only=True)
        all_feeds = get_all_feeds(conn, active_only=False)

        assert len(active_feeds) == 1
        assert len(all_feeds) == 2

    def test_update_feed_last_fetched(self, conn):
        """Test updating feed last_fetched timestamp."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        feed = get_feed(conn, feed_id)
        assert feed["last_fetched"] is None

        update_feed_last_fetched(conn, feed_id)
        feed = get_feed(conn, feed_id)
        assert feed["last_fetched"] is not None

    def test_update_feed_title(self, conn):
        """Test updating feed title."""
        feed_id = add_feed(conn, "https://example.com/feed.xml", "Old Title")
        update_feed_title(conn, feed_id, "New Title")
        feed = get_feed(conn, feed_id)
        assert feed["title"] == "New Title"

    def test_deactivate_feed(self, conn):
        """Test deactivating a feed."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        deactivate_feed(conn, feed_id)
        feed = get_feed(conn, feed_id)
        assert feed["active"] == 0

    def test_delete_feed(self, conn):
        """Test deleting a feed."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        add_article(conn, feed_id, "Article", "Content", "https://example.com/1", None)
        delete_feed(conn, feed_id)

        assert get_feed(conn, feed_id) is None
        assert len(get_articles_by_feed(conn, feed_id)) == 0


class TestArticleCRUD:
    """Tests for article CRUD operations."""

    def test_add_and_get_article(self, conn):
        """Test adding and retrieving an article."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        pub_date = datetime(2025, 1, 1, 12, 0, 0)

        article_id = add_article(
            conn,
            feed_id,
            "Test Article",
            "Article content here",
            "https://example.com/article/1",
            pub_date,
        )

        assert article_id is not None

        article = get_article(conn, article_id)
        assert article is not None
        assert article["title"] == "Test Article"
        assert article["content"] == "Article content here"
        assert article["link"] == "https://example.com/article/1"
        assert article["feed_id"] == feed_id

    def test_add_article_without_content(self, conn):
        """Test adding an article without content."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        article_id = add_article(
            conn, feed_id, "Title", None, "https://example.com/1", None
        )
        article = get_article(conn, article_id)
        assert article["content"] is None

    def test_duplicate_article_link_handled(self, conn):
        """Test that duplicate article links return None."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")

        article_id1 = add_article(
            conn, feed_id, "Article 1", "Content", "https://example.com/1", None
        )
        article_id2 = add_article(
            conn, feed_id, "Article 2", "Content", "https://example.com/1", None
        )

        assert article_id1 is not None
        assert article_id2 is None

    def test_article_exists(self, conn):
        """Test checking if an article exists."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        add_article(conn, feed_id, "Article", "Content", "https://example.com/1", None)

        assert article_exists(conn, "https://example.com/1") is True
        assert article_exists(conn, "https://example.com/2") is False

    def test_get_article_by_link(self, conn):
        """Test getting an article by its link."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        add_article(
            conn, feed_id, "Test Article", "Content", "https://example.com/1", None
        )

        article = get_article_by_link(conn, "https://example.com/1")
        assert article is not None
        assert article["title"] == "Test Article"

    def test_get_articles_by_feed(self, conn):
        """Test getting articles for a specific feed."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")

        for i in range(5):
            add_article(
                conn,
                feed_id,
                f"Article {i}",
                "Content",
                f"https://example.com/{i}",
                datetime(2025, 1, i + 1),
            )

        articles = get_articles_by_feed(conn, feed_id, limit=3)
        assert len(articles) == 3

    def test_get_unread_articles(self, conn):
        """Test getting unread articles."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")

        article_id1 = add_article(
            conn, feed_id, "Article 1", "Content", "https://example.com/1", None
        )
        add_article(
            conn, feed_id, "Article 2", "Content", "https://example.com/2", None
        )

        # Mark first article as read
        add_reading_history(conn, article_id1, "read")

        unread = get_unread_articles(conn)
        assert len(unread) == 1
        assert unread[0]["title"] == "Article 2"

    def test_update_article_lightrag_id(self, conn):
        """Test updating article's LightRAG ID."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        article_id = add_article(
            conn, feed_id, "Article", "Content", "https://example.com/1", None
        )

        update_article_lightrag_id(conn, article_id, "lightrag-123")

        article = get_article(conn, article_id)
        assert article["lightrag_id"] == "lightrag-123"

    def test_get_articles_without_lightrag_id(self, conn):
        """Test getting articles without LightRAG ID."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")

        article_id1 = add_article(
            conn, feed_id, "Article 1", "Content", "https://example.com/1", None
        )
        add_article(
            conn, feed_id, "Article 2", "Content", "https://example.com/2", None
        )

        update_article_lightrag_id(conn, article_id1, "lightrag-123")

        articles = get_articles_without_lightrag_id(conn)
        assert len(articles) == 1
        assert articles[0]["title"] == "Article 2"

    def test_get_recent_articles(self, conn):
        """Test getting recent articles."""
        feed_id = add_feed(conn, "https://example.com/feed.xml", "My Feed")

        for i in range(3):
            add_article(
                conn,
                feed_id,
                f"Article {i}",
                "Content",
                f"https://example.com/{i}",
                datetime(2025, 1, i + 1),
            )

        articles = get_recent_articles(conn, limit=2)
        assert len(articles) == 2
        # Should include feed_title
        assert articles[0]["feed_title"] == "My Feed"


class TestReadingHistory:
    """Tests for reading history operations."""

    def test_add_reading_history(self, conn):
        """Test adding reading history."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        article_id = add_article(
            conn, feed_id, "Article", "Content", "https://example.com/1", None
        )

        history_id = add_reading_history(conn, article_id, "read", 120)
        assert history_id is not None
        assert history_id > 0

    def test_get_reading_history(self, conn):
        """Test getting reading history for an article."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        article_id = add_article(
            conn, feed_id, "Article", "Content", "https://example.com/1", None
        )

        add_reading_history(conn, article_id, "read", 120)
        add_reading_history(conn, article_id, "saved")

        history = get_reading_history(conn, article_id)
        assert len(history) == 2

    def test_get_read_article_ids(self, conn):
        """Test getting IDs of read articles."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")

        article_id1 = add_article(
            conn, feed_id, "Article 1", "Content", "https://example.com/1", None
        )
        article_id2 = add_article(
            conn, feed_id, "Article 2", "Content", "https://example.com/2", None
        )
        add_article(
            conn, feed_id, "Article 3", "Content", "https://example.com/3", None
        )

        add_reading_history(conn, article_id1, "read")
        add_reading_history(conn, article_id2, "read")

        read_ids = get_read_article_ids(conn)
        assert len(read_ids) == 2
        assert article_id1 in read_ids
        assert article_id2 in read_ids

    def test_reading_history_with_duration(self, conn):
        """Test reading history with read duration."""
        feed_id = add_feed(conn, "https://example.com/feed.xml")
        article_id = add_article(
            conn, feed_id, "Article", "Content", "https://example.com/1", None
        )

        add_reading_history(conn, article_id, "read", read_duration=300)

        history = get_reading_history(conn, article_id)
        assert history[0]["read_duration"] == 300


class TestStats:
    """Tests for statistics operations."""

    def test_get_stats_empty_db(self, conn):
        """Test getting stats on empty database."""
        stats = get_stats(conn)
        assert stats["total_feeds"] == 0
        assert stats["active_feeds"] == 0
        assert stats["total_articles"] == 0
        assert stats["read_articles"] == 0
        assert stats["unread_articles"] == 0

    def test_get_stats(self, conn):
        """Test getting statistics."""
        # Add some data
        feed_id1 = add_feed(conn, "https://example1.com/feed.xml")
        feed_id2 = add_feed(conn, "https://example2.com/feed.xml")
        deactivate_feed(conn, feed_id2)

        article_id1 = add_article(
            conn, feed_id1, "Article 1", "Content", "https://example.com/1", None
        )
        article_id2 = add_article(
            conn, feed_id1, "Article 2", "Content", "https://example.com/2", None
        )
        add_article(
            conn, feed_id1, "Article 3", "Content", "https://example.com/3", None
        )

        update_article_lightrag_id(conn, article_id1, "lightrag-1")
        add_reading_history(conn, article_id2, "read")

        stats = get_stats(conn)
        assert stats["total_feeds"] == 2
        assert stats["active_feeds"] == 1
        assert stats["total_articles"] == 3
        assert stats["indexed_articles"] == 1
        assert stats["read_articles"] == 1
        assert stats["unread_articles"] == 2
