"""Search interface using LightRAG hybrid retrieval."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from rss_rag.config import get_config
from rss_rag.ingestion import get_lightrag_instance
from rss_rag.llm import get_summarizer_llm

logger = logging.getLogger(__name__)


class QueryMode(str, Enum):
    """LightRAG query modes."""

    HYBRID = "hybrid"
    LOCAL = "local"
    GLOBAL = "global"
    NAIVE = "naive"


@dataclass
class SearchResult:
    """Result of a search query."""

    query: str
    mode: QueryMode
    raw_response: str
    summary: str | None = None
    sources: list[str] = field(default_factory=list)
    error: str | None = None


async def search_async(
    query: str,
    mode: QueryMode = QueryMode.HYBRID,
    summarize: bool = True,
) -> SearchResult:
    """Search the knowledge graph using LightRAG.

    Args:
        query: Search query
        mode: Query mode (hybrid, local, global, naive)
        summarize: Whether to run summarizer LLM on results

    Returns:
        SearchResult with response and optional summary
    """
    try:
        rag = get_lightrag_instance()

        # Query LightRAG
        logger.info(f"Searching with mode={mode.value}: {query[:50]}...")

        # LightRAG query API
        response = await rag.aquery(
            query,
            param={"mode": mode.value},
        )

        logger.debug(f"Raw response: {response[:200]}...")

        # Extract sources from response if present (URLs in response)
        sources = _extract_sources(response)

        # Optionally summarize
        summary = None
        if summarize and response:
            summary = await _summarize_response(query, response)

        return SearchResult(
            query=query,
            mode=mode,
            raw_response=response,
            summary=summary,
            sources=sources,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return SearchResult(
            query=query,
            mode=mode,
            raw_response="",
            error=str(e),
        )


def search(
    query: str,
    mode: QueryMode = QueryMode.HYBRID,
    summarize: bool = True,
) -> SearchResult:
    """Sync wrapper for search."""
    return asyncio.run(search_async(query, mode, summarize))


def _extract_sources(response: str) -> list[str]:
    """Extract URLs from response text."""
    import re

    # Match URLs in the response
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, response)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


async def _summarize_response(query: str, response: str) -> str:
    """Summarize the search response using LLM.

    Args:
        query: Original query
        response: Raw response from LightRAG

    Returns:
        Summarized response
    """
    try:
        llm = get_summarizer_llm()

        prompt = f"""Summarize the following search results for the query: "{query}"

Search Results:
{response}

Provide a concise, informative summary that directly answers the query. Include key points and any relevant source URLs mentioned."""

        result = await llm.ainvoke(prompt)
        return result.content

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return response  # Return raw response on failure


def format_search_result(result: SearchResult, show_raw: bool = False) -> str:
    """Format search result for display.

    Args:
        result: SearchResult to format
        show_raw: Whether to include raw response

    Returns:
        Formatted string for CLI output
    """
    lines = []

    if result.error:
        lines.append(f"Error: {result.error}")
        return "\n".join(lines)

    # Show summary or raw response
    if result.summary:
        lines.append("Summary:")
        lines.append(result.summary)
    else:
        lines.append("Response:")
        lines.append(result.raw_response)

    # Show raw if requested
    if show_raw and result.summary:
        lines.append("\n--- Raw Response ---")
        lines.append(result.raw_response)

    # Show sources
    if result.sources:
        lines.append("\nSources:")
        for i, source in enumerate(result.sources[:5], 1):
            lines.append(f"  {i}. {source}")

    return "\n".join(lines)
