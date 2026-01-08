"""Feed management: parsing, fetching, and storing RSS feeds."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import mktime
from typing import Iterator

import feedparser
from feedparser import FeedParserDict

from rss_rag.database import (
    add_article,
    add_feed,
    article_exists,
    get_all_feeds,
    get_connection,
    get_feed_by_url,
    update_feed_last_fetched,
)
from rss_rag.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class Article:
    """Parsed article from RSS feed."""

    title: str
    content: str | None
    link: str
    pub_date: datetime | None
    feed_url: str


@dataclass
class FetchResult:
    """Result of fetching a single feed."""

    feed_url: str
    feed_title: str | None
    articles_found: int
    articles_new: int
    error: str | None = None


def parse_feeds_file(feeds_file: Path) -> list[str]:
    """Parse feeds.txt file and return list of feed URLs.

    Lines starting with # are comments.
    Empty lines are ignored.
    """
    if not feeds_file.exists():
        logger.warning(f"Feeds file not found: {feeds_file}")
        return []

    urls = []
    with open(feeds_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)

    logger.info(f"Parsed {len(urls)} feed URLs from {feeds_file}")
    return urls


def parse_pub_date(entry: FeedParserDict) -> datetime | None:
    """Extract publication date from feed entry."""
    # Try published_parsed first, then updated_parsed
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime.fromtimestamp(mktime(parsed))
        except (ValueError, OverflowError):
            pass
    return None


def extract_content(entry: FeedParserDict) -> str | None:
    """Extract article content from feed entry."""
    # Try content field first (full content)
    if "content" in entry and entry["content"]:
        # content is a list, get first HTML content
        for content in entry["content"]:
            if content.get("type", "").startswith("text/html") or content.get("value"):
                return content.get("value")

    # Fallback to summary
    if "summary" in entry:
        return entry["summary"]

    # Fallback to description
    if "description" in entry:
        return entry["description"]

    return None


def fetch_feed(
    feed_url: str, max_articles: int = 50
) -> tuple[str | None, list[Article], str | None]:
    """Fetch and parse a single RSS feed.

    Returns:
        Tuple of (feed_title, articles, error_message)
    """
    logger.info(f"Fetching feed: {feed_url}")

    try:
        feed = feedparser.parse(feed_url)

        # Check for parsing errors
        if feed.bozo and feed.bozo_exception:
            error_msg = str(feed.bozo_exception)
            # Some bozo exceptions are recoverable
            if not feed.entries:
                logger.error(f"Failed to parse feed {feed_url}: {error_msg}")
                return None, [], error_msg
            logger.warning(f"Feed {feed_url} has issues but is usable: {error_msg}")

        feed_title = feed.feed.get("title")
        articles = []

        for entry in feed.entries[:max_articles]:
            link = entry.get("link")
            if not link:
                continue

            article = Article(
                title=entry.get("title", "Untitled"),
                content=extract_content(entry),
                link=link,
                pub_date=parse_pub_date(entry),
                feed_url=feed_url,
            )
            articles.append(article)

        logger.info(f"Fetched {len(articles)} articles from {feed_url}")
        return feed_title, articles, None

    except Exception as e:
        error_msg = f"Error fetching {feed_url}: {e}"
        logger.error(error_msg)
        return None, [], error_msg


def fetch_and_store_feed(
    db_path: Path, feed_url: str, max_articles: int = 50
) -> FetchResult:
    """Fetch a feed and store its articles in the database.

    Creates feed entry if it doesn't exist.
    Skips articles that already exist (by link).
    """
    feed_title, articles, error = fetch_feed(feed_url, max_articles)

    if error and not articles:
        return FetchResult(
            feed_url=feed_url,
            feed_title=None,
            articles_found=0,
            articles_new=0,
            error=error,
        )

    conn = get_connection(db_path)
    try:
        # Get or create feed
        existing_feed = get_feed_by_url(conn, feed_url)
        if existing_feed:
            feed_id = existing_feed["id"]
            # Update title if we now have one
            if feed_title and not existing_feed.get("title"):
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE feeds SET title = ? WHERE id = ?", (feed_title, feed_id)
                )
                conn.commit()
        else:
            feed_id = add_feed(conn, feed_url, feed_title)

        # Store articles
        new_count = 0
        for article in articles:
            if not article_exists(conn, article.link):
                add_article(
                    conn,
                    feed_id=feed_id,
                    title=article.title,
                    content=article.content,
                    link=article.link,
                    pub_date=article.pub_date,
                )
                new_count += 1

        # Update last fetched
        update_feed_last_fetched(conn, feed_id)

        return FetchResult(
            feed_url=feed_url,
            feed_title=feed_title,
            articles_found=len(articles),
            articles_new=new_count,
            error=error,  # May have partial error
        )
    finally:
        conn.close()


def fetch_all_feeds(
    db_path: Path, feeds_file: Path | None = None, max_articles_per_feed: int = 50
) -> Iterator[FetchResult]:
    """Fetch all feeds and yield results as they complete.

    If feeds_file provided, imports new feeds from it first.
    Then fetches all active feeds from database.
    """
    config = get_config()

    # Import feeds from file if provided
    if feeds_file:
        urls = parse_feeds_file(feeds_file)
        conn = get_connection(db_path)
        try:
            for url in urls:
                if not get_feed_by_url(conn, url):
                    add_feed(conn, url)
                    logger.info(f"Added new feed: {url}")
        finally:
            conn.close()

    # Get all active feeds
    conn = get_connection(db_path)
    try:
        feeds = get_all_feeds(conn, active_only=True)
    finally:
        conn.close()

    # Fetch each feed
    for feed in feeds:
        result = fetch_and_store_feed(db_path, feed["url"], max_articles_per_feed)
        yield result


def import_feeds_from_file(db_path: Path, feeds_file: Path) -> int:
    """Import feeds from a file into the database.

    Returns number of new feeds added.
    """
    urls = parse_feeds_file(feeds_file)
    new_count = 0

    conn = get_connection(db_path)
    try:
        for url in urls:
            if not get_feed_by_url(conn, url):
                add_feed(conn, url)
                new_count += 1
                logger.info(f"Added new feed: {url}")
            else:
                logger.debug(f"Feed already exists: {url}")
    finally:
        conn.close()

    return new_count
