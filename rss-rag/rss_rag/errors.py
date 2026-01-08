"""Custom exceptions for RSS-RAG."""

from __future__ import annotations


class RSSRAGError(Exception):
    """Base exception for RSS-RAG."""

    pass


class ConfigError(RSSRAGError):
    """Configuration error."""

    pass


class DatabaseError(RSSRAGError):
    """Database operation error."""

    pass


class FeedError(RSSRAGError):
    """RSS feed fetching/parsing error."""

    pass


class IngestionError(RSSRAGError):
    """Article ingestion error."""

    pass


class SearchError(RSSRAGError):
    """Search operation error."""

    pass


class LLMError(RSSRAGError):
    """LLM API error."""

    pass


class EmbeddingError(RSSRAGError):
    """Embedding generation error."""

    pass


def handle_api_error(func):
    """Decorator to wrap API calls with retry and error handling."""
    import functools
    import time
    import logging

    logger = logging.getLogger(__name__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()

                # Retryable errors
                if any(x in error_str for x in ["rate limit", "timeout", "503", "429"]):
                    if attempt < max_retries - 1:
                        delay = retry_delay * (2**attempt)
                        logger.warning(f"Retrying {func.__name__} in {delay}s: {e}")
                        time.sleep(delay)
                        continue

                # Non-retryable or max retries reached
                logger.error(f"{func.__name__} failed: {e}")
                raise LLMError(str(e)) from e

        raise LLMError(f"Max retries ({max_retries}) exceeded")

    return wrapper


def handle_api_error_async(func):
    """Async version of handle_api_error."""
    import functools
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 1.0

        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()

                # Retryable errors
                if any(x in error_str for x in ["rate limit", "timeout", "503", "429"]):
                    if attempt < max_retries - 1:
                        delay = retry_delay * (2**attempt)
                        logger.warning(f"Retrying {func.__name__} in {delay}s: {e}")
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable or max retries reached
                logger.error(f"{func.__name__} failed: {e}")
                raise LLMError(str(e)) from e

        raise LLMError(f"Max retries ({max_retries}) exceeded")

    return wrapper
