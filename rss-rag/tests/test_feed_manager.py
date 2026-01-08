"""Tests for feed_manager module."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
import tempfile

from rss_rag.feed_manager import (
    parse_feeds_file,
    parse_pub_date,
    extract_content,
    fetch_feed,
    fetch_and_store_feed,
    import_feeds_from_file,
    Article,
)
from rss_rag.database import (
    init_db,
    get_connection,
    get_all_feeds,
    get_articles_by_feed,
)


@pytest.fixture
def temp_feeds_file():
    """Create a temporary feeds file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("# Comment line\n")
        f.write("https://example.com/feed1.xml\n")
        f.write("\n")  # Empty line
        f.write("https://example.com/feed2.xml\n")
        f.write("# Another comment\n")
        path = Path(f.name)
    yield path
    path.unlink()


@pytest.fixture
def db_path():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    init_db(path)
    yield path
    path.unlink()


class TestParseFeedsFile:
    def test_parses_valid_file(self, temp_feeds_file):
        urls = parse_feeds_file(temp_feeds_file)
        assert len(urls) == 2
        assert "https://example.com/feed1.xml" in urls
        assert "https://example.com/feed2.xml" in urls

    def test_ignores_comments(self, temp_feeds_file):
        urls = parse_feeds_file(temp_feeds_file)
        assert not any(url.startswith("#") for url in urls)

    def test_handles_missing_file(self):
        urls = parse_feeds_file(Path("/nonexistent/path.txt"))
        assert urls == []


class TestParsePubDate:
    def test_parses_published_parsed(self):
        entry = MagicMock()
        entry.get = lambda k, d=None: (
            (2024, 1, 15, 12, 0, 0, 0, 0, 0) if k == "published_parsed" else None
        )
        result = parse_pub_date(entry)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_handles_missing_date(self):
        entry = MagicMock()
        entry.get = lambda k, d=None: None
        result = parse_pub_date(entry)
        assert result is None


class TestExtractContent:
    def test_extracts_from_content_field(self):
        entry = {"content": [{"type": "text/html", "value": "<p>Hello</p>"}]}
        result = extract_content(entry)
        assert result == "<p>Hello</p>"

    def test_fallback_to_summary(self):
        entry = {"summary": "Summary text"}
        result = extract_content(entry)
        assert result == "Summary text"

    def test_fallback_to_description(self):
        entry = {"description": "Description text"}
        result = extract_content(entry)
        assert result == "Description text"

    def test_returns_none_if_no_content(self):
        entry = {}
        result = extract_content(entry)
        assert result is None


class TestFetchFeed:
    @patch("rss_rag.feed_manager.feedparser.parse")
    def test_fetches_and_parses_articles(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=False,
            feed={"title": "Test Feed"},
            entries=[
                {
                    "title": "Article 1",
                    "link": "https://example.com/article1",
                    "summary": "Content 1",
                    "published_parsed": (2024, 1, 1, 12, 0, 0, 0, 0, 0),
                },
                {
                    "title": "Article 2",
                    "link": "https://example.com/article2",
                    "summary": "Content 2",
                },
            ],
        )

        title, articles, error = fetch_feed("https://example.com/feed")

        assert title == "Test Feed"
        assert len(articles) == 2
        assert articles[0].title == "Article 1"
        assert articles[0].link == "https://example.com/article1"
        assert error is None

    @patch("rss_rag.feed_manager.feedparser.parse")
    def test_handles_bozo_error(self, mock_parse):
        mock_parse.return_value = MagicMock(
            bozo=True,
            bozo_exception=Exception("Parse error"),
            feed={},
            entries=[],
        )

        title, articles, error = fetch_feed("https://example.com/bad-feed")

        assert title is None
        assert len(articles) == 0
        assert error is not None


class TestFetchAndStoreFeed:
    @patch("rss_rag.feed_manager.feedparser.parse")
    def test_stores_articles_in_database(self, mock_parse, db_path):
        mock_parse.return_value = MagicMock(
            bozo=False,
            feed={"title": "Test Feed"},
            entries=[
                {
                    "title": "Article 1",
                    "link": "https://example.com/article1",
                    "summary": "Content 1",
                },
            ],
        )

        result = fetch_and_store_feed(db_path, "https://example.com/feed")

        assert result.articles_found == 1
        assert result.articles_new == 1
        assert result.feed_title == "Test Feed"

        # Verify in database
        conn = get_connection(db_path)
        feeds = get_all_feeds(conn)
        assert len(feeds) == 1
        assert feeds[0]["title"] == "Test Feed"

        articles = get_articles_by_feed(conn, feeds[0]["id"])
        assert len(articles) == 1
        assert articles[0]["title"] == "Article 1"
        conn.close()

    @patch("rss_rag.feed_manager.feedparser.parse")
    def test_skips_duplicate_articles(self, mock_parse, db_path):
        mock_parse.return_value = MagicMock(
            bozo=False,
            feed={"title": "Test Feed"},
            entries=[
                {
                    "title": "Article 1",
                    "link": "https://example.com/article1",
                    "summary": "Content 1",
                },
            ],
        )

        # Fetch twice
        result1 = fetch_and_store_feed(db_path, "https://example.com/feed")
        result2 = fetch_and_store_feed(db_path, "https://example.com/feed")

        assert result1.articles_new == 1
        assert result2.articles_new == 0  # Already exists


class TestImportFeedsFromFile:
    def test_imports_feeds(self, temp_feeds_file, db_path):
        count = import_feeds_from_file(db_path, temp_feeds_file)

        assert count == 2

        conn = get_connection(db_path)
        feeds = get_all_feeds(conn)
        assert len(feeds) == 2
        conn.close()

    def test_skips_existing_feeds(self, temp_feeds_file, db_path):
        count1 = import_feeds_from_file(db_path, temp_feeds_file)
        count2 = import_feeds_from_file(db_path, temp_feeds_file)

        assert count1 == 2
        assert count2 == 0  # All already exist
