"""Article ingestion into LightRAG knowledge graph."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Iterator

from rss_rag.config import get_config
from rss_rag.database import (
    get_connection,
    update_article_lightrag_id,
)

logger = logging.getLogger(__name__)

# Module-level cache for LightRAG instance
_rag_instance = None


@dataclass
class IngestionResult:
    """Result of ingesting a single article."""

    article_id: int
    title: str
    success: bool
    lightrag_id: str | None = None
    error: str | None = None


def _generate_doc_id(link: str) -> str:
    """Generate a unique document ID from the article link.

    Args:
        link: Article URL.

    Returns:
        MD5 hash of the link as document ID.
    """
    return hashlib.md5(link.encode()).hexdigest()


def get_lightrag_instance():
    """Get or create LightRAG instance with current config.

    LightRAG needs:
    - working_dir: Where to store graph and embeddings
    - llm_model_func: Function for LLM calls
    - embedding_func: EmbeddingFunc for embeddings

    Returns:
        LightRAG instance configured according to rss_rag config.
    """
    global _rag_instance

    if _rag_instance is not None:
        return _rag_instance

    from lightrag import LightRAG
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed

    config = get_config()

    # Create working directory if it doesn't exist
    working_dir = config.storage.lightrag_dir
    working_dir.mkdir(parents=True, exist_ok=True)

    # Initialize LightRAG with OpenAI functions
    _rag_instance = LightRAG(
        working_dir=str(working_dir),
        llm_model_func=openai_complete_if_cache,
        llm_model_name=config.llm.entity_extraction.model,
        embedding_func=openai_embed,
        chunk_token_size=config.lightrag.chunk_size,
        chunk_overlap_token_size=config.lightrag.chunk_overlap,
    )

    logger.info(f"Initialized LightRAG with working_dir: {working_dir}")

    return _rag_instance


def reset_lightrag_instance() -> None:
    """Reset the cached LightRAG instance.

    Useful for testing or when config changes.
    """
    global _rag_instance
    _rag_instance = None


async def ingest_article_async(
    rag,
    article_id: int,
    title: str,
    content: str,
    link: str,
) -> IngestionResult:
    """Ingest a single article into LightRAG.

    Args:
        rag: LightRAG instance
        article_id: Database article ID
        title: Article title
        content: Article content (HTML or text)
        link: Article URL

    Returns:
        IngestionResult with success status
    """
    try:
        # Prepare document text
        doc_text = f"Title: {title}\n\nURL: {link}\n\n{content or ''}"

        # Generate unique document ID from link
        doc_id = _generate_doc_id(link)

        # Insert into LightRAG (async)
        # Using ids parameter to track which document was inserted
        await rag.ainsert(doc_text, ids=[doc_id], file_paths=[link])

        logger.info(f"Ingested article {article_id}: {title[:50]}...")

        return IngestionResult(
            article_id=article_id,
            title=title,
            success=True,
            lightrag_id=doc_id,
        )

    except Exception as e:
        logger.error(f"Failed to ingest article {article_id}: {e}")
        return IngestionResult(
            article_id=article_id,
            title=title,
            success=False,
            error=str(e),
        )


def ingest_article(
    rag,
    article_id: int,
    title: str,
    content: str,
    link: str,
) -> IngestionResult:
    """Sync wrapper for article ingestion.

    Args:
        rag: LightRAG instance
        article_id: Database article ID
        title: Article title
        content: Article content
        link: Article URL

    Returns:
        IngestionResult with success status
    """
    return asyncio.run(ingest_article_async(rag, article_id, title, content, link))


async def ingest_pending_articles_async(
    db_path: Path,
    limit: int | None = None,
) -> AsyncIterator[IngestionResult]:
    """Ingest all articles that haven't been ingested yet.

    Articles with NULL lightrag_id are considered pending.

    Args:
        db_path: Path to SQLite database
        limit: Maximum number of articles to ingest

    Yields:
        IngestionResult for each article
    """
    rag = get_lightrag_instance()

    # Get pending articles (no lightrag_id)
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        query = """
            SELECT id, title, content, link 
            FROM articles 
            WHERE lightrag_id IS NULL
            ORDER BY pub_date DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        articles = cursor.fetchall()
    finally:
        conn.close()

    logger.info(f"Found {len(articles)} articles to ingest")

    for article in articles:
        article_id = article["id"]
        title = article["title"]
        content = article["content"]
        link = article["link"]

        result = await ingest_article_async(
            rag,
            article_id=article_id,
            title=title,
            content=content or "",
            link=link,
        )

        # Update database with lightrag reference if successful
        if result.success and result.lightrag_id:
            conn = get_connection(db_path)
            try:
                update_article_lightrag_id(conn, article_id, result.lightrag_id)
            finally:
                conn.close()

        yield result


def ingest_pending_articles(
    db_path: Path,
    limit: int | None = None,
) -> Iterator[IngestionResult]:
    """Sync iterator for pending article ingestion.

    Args:
        db_path: Path to SQLite database
        limit: Maximum number of articles to ingest

    Yields:
        IngestionResult for each article
    """

    async def collect():
        results = []
        async for result in ingest_pending_articles_async(db_path, limit):
            results.append(result)
        return results

    results = asyncio.run(collect())
    yield from results


def get_pending_count(db_path: Path) -> int:
    """Get count of articles pending ingestion.

    Args:
        db_path: Path to SQLite database

    Returns:
        Number of articles with NULL lightrag_id
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles WHERE lightrag_id IS NULL")
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_ingested_count(db_path: Path) -> int:
    """Get count of articles already ingested.

    Args:
        db_path: Path to SQLite database

    Returns:
        Number of articles with non-NULL lightrag_id
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM articles WHERE lightrag_id IS NOT NULL")
        return cursor.fetchone()[0]
    finally:
        conn.close()
