"""SQLite database for article metadata and state tracking."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from sqlite3 import Connection, IntegrityError
from typing import Iterator

# SQL schema for database initialization
SCHEMA = """
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    last_fetched TIMESTAMP,
    fetch_interval INTEGER DEFAULT 3600,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    link TEXT UNIQUE NOT NULL,
    pub_date TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lightrag_id TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);

CREATE TABLE IF NOT EXISTS reading_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_duration INTEGER,
    FOREIGN KEY (article_id) REFERENCES articles(id)
);

CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id);
CREATE INDEX IF NOT EXISTS idx_articles_link ON articles(link);
CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON articles(pub_date);
CREATE INDEX IF NOT EXISTS idx_reading_history_article_id ON reading_history(article_id);
"""


def init_db(db_path: Path) -> None:
    """Initialize the database with schema.

    Args:
        db_path: Path to the SQLite database file.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_connection(db_path: Path) -> Connection:
    """Get a connection to the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLite connection with row factory set.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_connection(db_path: Path) -> Iterator[Connection]:
    """Context manager for database connections.

    Args:
        db_path: Path to the SQLite database file.

    Yields:
        SQLite connection that will be closed on exit.
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


# ============================================================================
# Feed CRUD Operations
# ============================================================================


def add_feed(conn: Connection, url: str, title: str | None = None) -> int:
    """Add a new feed to the database.

    Args:
        conn: Database connection.
        url: Feed URL.
        title: Optional feed title.

    Returns:
        The feed ID (existing or newly created).
    """
    try:
        cursor = conn.execute(
            "INSERT INTO feeds (url, title) VALUES (?, ?)",
            (url, title),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore
    except IntegrityError:
        # Feed already exists, return existing ID
        existing = get_feed_by_url(conn, url)
        if existing:
            return existing["id"]
        raise


def get_feed(conn: Connection, feed_id: int) -> dict | None:
    """Get a feed by ID.

    Args:
        conn: Database connection.
        feed_id: Feed ID.

    Returns:
        Feed data as dict, or None if not found.
    """
    cursor = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_feed_by_url(conn: Connection, url: str) -> dict | None:
    """Get a feed by URL.

    Args:
        conn: Database connection.
        url: Feed URL.

    Returns:
        Feed data as dict, or None if not found.
    """
    cursor = conn.execute("SELECT * FROM feeds WHERE url = ?", (url,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_feeds(conn: Connection, active_only: bool = True) -> list[dict]:
    """Get all feeds.

    Args:
        conn: Database connection.
        active_only: If True, only return active feeds.

    Returns:
        List of feed dicts.
    """
    if active_only:
        cursor = conn.execute("SELECT * FROM feeds WHERE active = 1")
    else:
        cursor = conn.execute("SELECT * FROM feeds")
    return [dict(row) for row in cursor.fetchall()]


def update_feed_last_fetched(conn: Connection, feed_id: int) -> None:
    """Update the last_fetched timestamp for a feed.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
    """
    conn.execute(
        "UPDATE feeds SET last_fetched = CURRENT_TIMESTAMP WHERE id = ?",
        (feed_id,),
    )
    conn.commit()


def update_feed_title(conn: Connection, feed_id: int, title: str) -> None:
    """Update the title of a feed.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
        title: New title.
    """
    conn.execute(
        "UPDATE feeds SET title = ? WHERE id = ?",
        (title, feed_id),
    )
    conn.commit()


def deactivate_feed(conn: Connection, feed_id: int) -> None:
    """Deactivate a feed.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
    """
    conn.execute("UPDATE feeds SET active = 0 WHERE id = ?", (feed_id,))
    conn.commit()


def activate_feed(conn: Connection, feed_id: int) -> None:
    """Activate a feed.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
    """
    conn.execute("UPDATE feeds SET active = 1 WHERE id = ?", (feed_id,))
    conn.commit()


def delete_feed(conn: Connection, feed_id: int) -> None:
    """Delete a feed and its articles.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
    """
    # First delete reading history for articles from this feed
    conn.execute(
        """
        DELETE FROM reading_history 
        WHERE article_id IN (SELECT id FROM articles WHERE feed_id = ?)
        """,
        (feed_id,),
    )
    # Then delete articles
    conn.execute("DELETE FROM articles WHERE feed_id = ?", (feed_id,))
    # Finally delete the feed
    conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    conn.commit()


# ============================================================================
# Article CRUD Operations
# ============================================================================


def add_article(
    conn: Connection,
    feed_id: int,
    title: str,
    content: str | None,
    link: str,
    pub_date: datetime | None,
) -> int | None:
    """Add a new article to the database.

    Args:
        conn: Database connection.
        feed_id: ID of the feed this article belongs to.
        title: Article title.
        content: Article content (can be None).
        link: Article URL (must be unique).
        pub_date: Publication date.

    Returns:
        The article ID, or None if article already exists.
    """
    try:
        cursor = conn.execute(
            """
            INSERT INTO articles (feed_id, title, content, link, pub_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (feed_id, title, content, link, pub_date),
        )
        conn.commit()
        return cursor.lastrowid
    except IntegrityError:
        # Article with this link already exists
        return None


def get_article(conn: Connection, article_id: int) -> dict | None:
    """Get an article by ID.

    Args:
        conn: Database connection.
        article_id: Article ID.

    Returns:
        Article data as dict, or None if not found.
    """
    cursor = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_article_by_link(conn: Connection, link: str) -> dict | None:
    """Get an article by its link.

    Args:
        conn: Database connection.
        link: Article URL.

    Returns:
        Article data as dict, or None if not found.
    """
    cursor = conn.execute("SELECT * FROM articles WHERE link = ?", (link,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_articles_by_feed(conn: Connection, feed_id: int, limit: int = 50) -> list[dict]:
    """Get articles for a specific feed.

    Args:
        conn: Database connection.
        feed_id: Feed ID.
        limit: Maximum number of articles to return.

    Returns:
        List of article dicts, ordered by pub_date descending.
    """
    cursor = conn.execute(
        """
        SELECT * FROM articles 
        WHERE feed_id = ? 
        ORDER BY pub_date DESC 
        LIMIT ?
        """,
        (feed_id, limit),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_unread_articles(conn: Connection, limit: int = 50) -> list[dict]:
    """Get articles that haven't been read.

    Args:
        conn: Database connection.
        limit: Maximum number of articles to return.

    Returns:
        List of unread article dicts, ordered by pub_date descending.
    """
    cursor = conn.execute(
        """
        SELECT a.* FROM articles a
        LEFT JOIN reading_history rh ON a.id = rh.article_id AND rh.action = 'read'
        WHERE rh.id IS NULL
        ORDER BY a.pub_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_recent_articles(conn: Connection, limit: int = 50) -> list[dict]:
    """Get most recent articles across all feeds.

    Args:
        conn: Database connection.
        limit: Maximum number of articles to return.

    Returns:
        List of article dicts, ordered by pub_date descending.
    """
    cursor = conn.execute(
        """
        SELECT a.*, f.title as feed_title FROM articles a
        JOIN feeds f ON a.feed_id = f.id
        ORDER BY a.pub_date DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


def update_article_lightrag_id(
    conn: Connection, article_id: int, lightrag_id: str
) -> None:
    """Update the LightRAG ID for an article.

    Args:
        conn: Database connection.
        article_id: Article ID.
        lightrag_id: LightRAG document ID.
    """
    conn.execute(
        "UPDATE articles SET lightrag_id = ? WHERE id = ?",
        (lightrag_id, article_id),
    )
    conn.commit()


def article_exists(conn: Connection, link: str) -> bool:
    """Check if an article with the given link exists.

    Args:
        conn: Database connection.
        link: Article URL.

    Returns:
        True if article exists, False otherwise.
    """
    cursor = conn.execute("SELECT 1 FROM articles WHERE link = ? LIMIT 1", (link,))
    return cursor.fetchone() is not None


def get_articles_without_lightrag_id(conn: Connection, limit: int = 100) -> list[dict]:
    """Get articles that haven't been indexed in LightRAG.

    Args:
        conn: Database connection.
        limit: Maximum number of articles to return.

    Returns:
        List of article dicts without lightrag_id.
    """
    cursor = conn.execute(
        """
        SELECT * FROM articles 
        WHERE lightrag_id IS NULL 
        ORDER BY pub_date DESC 
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# Reading History Operations
# ============================================================================


def add_reading_history(
    conn: Connection,
    article_id: int,
    action: str,
    read_duration: int | None = None,
) -> int:
    """Add a reading history entry.

    Args:
        conn: Database connection.
        article_id: Article ID.
        action: Action type (e.g., 'read', 'skipped', 'saved').
        read_duration: Optional reading duration in seconds.

    Returns:
        The reading history entry ID.
    """
    cursor = conn.execute(
        """
        INSERT INTO reading_history (article_id, action, read_duration)
        VALUES (?, ?, ?)
        """,
        (article_id, action, read_duration),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore


def get_reading_history(conn: Connection, article_id: int) -> list[dict]:
    """Get reading history for an article.

    Args:
        conn: Database connection.
        article_id: Article ID.

    Returns:
        List of reading history entries.
    """
    cursor = conn.execute(
        """
        SELECT * FROM reading_history 
        WHERE article_id = ? 
        ORDER BY timestamp DESC
        """,
        (article_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_read_article_ids(conn: Connection) -> list[int]:
    """Get IDs of all articles that have been read.

    Args:
        conn: Database connection.

    Returns:
        List of article IDs that have been read.
    """
    cursor = conn.execute(
        """
        SELECT DISTINCT article_id FROM reading_history 
        WHERE action = 'read'
        """
    )
    return [row["article_id"] for row in cursor.fetchall()]


def get_all_reading_history(conn: Connection, limit: int = 100) -> list[dict]:
    """Get all reading history entries.

    Args:
        conn: Database connection.
        limit: Maximum number of entries to return.

    Returns:
        List of reading history entries with article info.
    """
    cursor = conn.execute(
        """
        SELECT rh.*, a.title as article_title, a.link as article_link
        FROM reading_history rh
        JOIN articles a ON rh.article_id = a.id
        ORDER BY rh.timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


# ============================================================================
# Statistics
# ============================================================================


def get_stats(conn: Connection) -> dict:
    """Get database statistics.

    Args:
        conn: Database connection.

    Returns:
        Dict with various statistics.
    """
    stats = {}

    # Feed stats
    cursor = conn.execute("SELECT COUNT(*) as count FROM feeds WHERE active = 1")
    stats["active_feeds"] = cursor.fetchone()["count"]

    cursor = conn.execute("SELECT COUNT(*) as count FROM feeds")
    stats["total_feeds"] = cursor.fetchone()["count"]

    # Article stats
    cursor = conn.execute("SELECT COUNT(*) as count FROM articles")
    stats["total_articles"] = cursor.fetchone()["count"]

    cursor = conn.execute(
        "SELECT COUNT(*) as count FROM articles WHERE lightrag_id IS NOT NULL"
    )
    stats["indexed_articles"] = cursor.fetchone()["count"]

    # Reading stats
    cursor = conn.execute(
        "SELECT COUNT(DISTINCT article_id) as count FROM reading_history WHERE action = 'read'"
    )
    stats["read_articles"] = cursor.fetchone()["count"]

    # Unread count
    stats["unread_articles"] = stats["total_articles"] - stats["read_articles"]

    return stats
