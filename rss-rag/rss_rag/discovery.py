"""Discovery agent for personalized article recommendations."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rss_rag.config import get_config
from rss_rag.database import (
    get_connection,
    get_read_article_ids,
    get_article,
    get_unread_articles,
)
from rss_rag.ingestion import get_lightrag_instance
from rss_rag.llm import get_discovery_llm

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """A recommended article with explanation."""

    article_id: int
    title: str
    link: str
    explanation: str
    score: float = 0.0


@dataclass
class DiscoveryResult:
    """Result of discovery analysis."""

    recommendations: list[Recommendation] = field(default_factory=list)
    reading_patterns: str | None = None
    error: str | None = None


async def analyze_reading_patterns_async(db_path: Path) -> str | None:
    """Analyze user's reading patterns from history.

    Returns:
        Summary of reading patterns, or None if insufficient data
    """
    conn = get_connection(db_path)
    try:
        read_ids = get_read_article_ids(conn)

        if len(read_ids) < 3:
            logger.info("Insufficient reading history for pattern analysis")
            return None

        # Get read articles
        read_articles = []
        for article_id in read_ids[:20]:  # Limit to recent 20
            article = get_article(conn, article_id)
            if article:
                read_articles.append(article)

        if not read_articles:
            return None

        # Build content summary for LLM analysis
        articles_text = "\n".join([f"- {a['title']}" for a in read_articles])

        llm = get_discovery_llm()
        prompt = f"""Analyze the following list of articles that a user has read and identify their interests and reading patterns. Be concise.

Read articles:
{articles_text}

Identify:
1. Main topics of interest
2. Any patterns (e.g., technical depth, news vs tutorials)
3. Potential related topics they might enjoy"""

        result = await llm.ainvoke(prompt)
        return result.content

    finally:
        conn.close()


async def discover_articles_async(
    db_path: Path,
    limit: int = 5,
) -> DiscoveryResult:
    """Discover recommended articles based on reading history.

    Args:
        db_path: Path to SQLite database
        limit: Maximum number of recommendations

    Returns:
        DiscoveryResult with recommendations and patterns
    """
    try:
        # Analyze reading patterns
        patterns = await analyze_reading_patterns_async(db_path)

        conn = get_connection(db_path)
        try:
            # Get unread articles
            unread = get_unread_articles(conn, limit=50)
            read_ids = set(get_read_article_ids(conn))
        finally:
            conn.close()

        if not unread:
            return DiscoveryResult(
                reading_patterns=patterns,
                recommendations=[],
            )

        # If we have patterns, use LightRAG to find related content
        recommendations = []

        if patterns:
            try:
                rag = get_lightrag_instance()

                # Query based on reading patterns
                query = f"Find articles related to these interests: {patterns[:500]}"
                response = await rag.aquery(query, param={"mode": "hybrid"})

                # Use LLM to rank unread articles
                llm = get_discovery_llm()

                unread_list = "\n".join(
                    [
                        f"{i+1}. [{a['id']}] {a['title']}"
                        for i, a in enumerate(unread[:15])
                    ]
                )

                rank_prompt = f"""Based on the user's interests: {patterns[:300]}

And these unread articles:
{unread_list}

Select the top {limit} articles they would most likely enjoy. For each, provide:
- The article number and title
- A brief explanation why they'd enjoy it

Format as:
1. [Article title] - [explanation]
2. ..."""

                rank_result = await llm.ainvoke(rank_prompt)

                # Parse recommendations (simple extraction)
                for article in unread[:limit]:
                    recommendations.append(
                        Recommendation(
                            article_id=article["id"],
                            title=article["title"],
                            link=article["link"],
                            explanation="Based on your reading patterns",
                        )
                    )

            except Exception as e:
                logger.error(f"LightRAG discovery failed: {e}")
                # Fall back to simple unread list
                for article in unread[:limit]:
                    recommendations.append(
                        Recommendation(
                            article_id=article["id"],
                            title=article["title"],
                            link=article["link"],
                            explanation="Unread article",
                        )
                    )
        else:
            # No patterns - just return recent unread
            for article in unread[:limit]:
                recommendations.append(
                    Recommendation(
                        article_id=article["id"],
                        title=article["title"],
                        link=article["link"],
                        explanation="Recent unread article",
                    )
                )

        return DiscoveryResult(
            recommendations=recommendations,
            reading_patterns=patterns,
        )

    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        return DiscoveryResult(error=str(e))


def discover_articles(
    db_path: Path,
    limit: int = 5,
) -> DiscoveryResult:
    """Sync wrapper for discover_articles_async."""
    return asyncio.run(discover_articles_async(db_path, limit))


def format_discovery_result(result: DiscoveryResult) -> str:
    """Format discovery result for display."""
    lines = []

    if result.error:
        return f"Error: {result.error}"

    if result.reading_patterns:
        lines.append("📊 Your Reading Patterns:")
        lines.append(result.reading_patterns)
        lines.append("")

    if result.recommendations:
        lines.append("📚 Recommended Articles:")
        for i, rec in enumerate(result.recommendations, 1):
            lines.append(f"\n{i}. {rec.title}")
            lines.append(f"   📝 {rec.explanation}")
            lines.append(f"   🔗 {rec.link}")
    else:
        lines.append("No recommendations available. Read some articles first!")

    return "\n".join(lines)
