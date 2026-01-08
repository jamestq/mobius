"""Tests for error handling module."""

import pytest
from unittest.mock import MagicMock, patch
import asyncio

from rss_rag.errors import (
    RSSRAGError,
    ConfigError,
    DatabaseError,
    LLMError,
    handle_api_error,
    handle_api_error_async,
)


class TestCustomExceptions:
    def test_base_exception(self):
        with pytest.raises(RSSRAGError):
            raise RSSRAGError("Test error")

    def test_config_error(self):
        with pytest.raises(RSSRAGError):
            raise ConfigError("Invalid config")

    def test_database_error(self):
        with pytest.raises(RSSRAGError):
            raise DatabaseError("DB error")


class TestHandleApiError:
    def test_successful_call(self):
        @handle_api_error
        def success_func():
            return "success"

        assert success_func() == "success"

    def test_retries_on_rate_limit(self):
        attempts = []

        @handle_api_error
        def rate_limited():
            attempts.append(1)
            if len(attempts) < 2:
                raise Exception("Rate limit exceeded")
            return "success"

        with patch("time.sleep"):  # Skip actual sleep
            result = rate_limited()

        assert result == "success"
        assert len(attempts) == 2

    def test_raises_after_max_retries(self):
        @handle_api_error
        def always_fails():
            raise Exception("Rate limit exceeded")

        with patch("time.sleep"):
            with pytest.raises(LLMError):
                always_fails()

    def test_non_retryable_error(self):
        @handle_api_error
        def auth_error():
            raise Exception("Authentication failed")

        with pytest.raises(LLMError, match="Authentication failed"):
            auth_error()
