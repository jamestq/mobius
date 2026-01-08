"""Tests for CLI module."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
import tempfile
import os

from rss_rag.cli import app
from rss_rag.database import init_db, get_connection, add_feed


runner = CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mock_config(temp_dir):
    """Mock config with temp paths."""
    from rss_rag.config import Config, StorageConfig, set_config

    config = Config(
        storage=StorageConfig(
            lightrag_dir=temp_dir / "lightrag",
            sqlite_db=temp_dir / "test.db",
            feeds_file=temp_dir / "feeds.txt",
        )
    )
    set_config(config)
    return config


class TestInitCommand:
    def test_init_creates_database(self, mock_config):
        result = runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert mock_config.storage.sqlite_db.exists()
        assert mock_config.storage.lightrag_dir.exists()
        assert "Initialization complete" in result.stdout

    def test_init_warns_existing_db(self, mock_config):
        # First init
        runner.invoke(app, ["init"])
        # Second init
        result = runner.invoke(app, ["init"])

        assert "already exists" in result.stdout

    def test_init_force_reinitializes(self, mock_config):
        runner.invoke(app, ["init"])
        result = runner.invoke(app, ["init", "--force"])

        assert result.exit_code == 0
        assert "Initialized database" in result.stdout


class TestAddFeedsCommand:
    def test_add_feeds_imports_urls(self, mock_config):
        # Setup
        runner.invoke(app, ["init"])
        feeds_file = mock_config.storage.feeds_file
        feeds_file.write_text("https://example.com/feed1\nhttps://example.com/feed2\n")

        result = runner.invoke(app, ["add-feeds"])

        assert result.exit_code == 0
        assert "Added 2 new feed" in result.stdout

    def test_add_feeds_from_custom_file(self, mock_config, temp_dir):
        runner.invoke(app, ["init"])

        custom_file = temp_dir / "custom.txt"
        custom_file.write_text("https://custom.com/feed\n")

        result = runner.invoke(app, ["add-feeds", str(custom_file)])

        assert result.exit_code == 0
        assert "Added 1 new feed" in result.stdout

    def test_add_feeds_no_db_error(self, mock_config):
        # Create feeds file but no database
        feeds_file = mock_config.storage.feeds_file
        feeds_file.write_text("https://example.com/feed\n")

        result = runner.invoke(app, ["add-feeds"])

        assert result.exit_code == 1
        assert "not initialized" in result.stdout


class TestFetchCommand:
    @patch("rss_rag.cli.fetch_and_store_feed")
    def test_fetch_single_url(self, mock_fetch, mock_config):
        from rss_rag.feed_manager import FetchResult

        runner.invoke(app, ["init"])
        mock_fetch.return_value = FetchResult(
            feed_url="https://example.com/feed",
            feed_title="Test Feed",
            articles_found=10,
            articles_new=5,
        )

        result = runner.invoke(app, ["fetch", "https://example.com/feed"])

        assert result.exit_code == 0
        assert "5 new / 10 total" in result.stdout

    def test_fetch_no_db_error(self, mock_config):
        result = runner.invoke(app, ["fetch"])

        assert result.exit_code == 1
        assert "not initialized" in result.stdout


class TestStatsCommand:
    def test_stats_shows_counts(self, mock_config):
        runner.invoke(app, ["init"])

        # Add some data
        conn = get_connection(mock_config.storage.sqlite_db)
        add_feed(conn, "https://example.com/feed", "Test Feed")
        conn.close()

        result = runner.invoke(app, ["stats"])

        assert result.exit_code == 0
        assert "Total Feeds" in result.stdout
        assert "1" in result.stdout

    def test_stats_no_db_error(self, mock_config):
        result = runner.invoke(app, ["stats"])

        assert result.exit_code == 1
        assert "not initialized" in result.stdout
