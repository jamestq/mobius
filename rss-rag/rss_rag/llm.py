"""LLM loading and management using LangChain."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from langchain_core.language_models import BaseChatModel

from rss_rag.config import LLMConfig, get_config

logger = logging.getLogger(__name__)


def get_llm(
    provider: str,
    model: str,
    temperature: float = 0.0,
) -> BaseChatModel:
    """Get an LLM instance based on provider.

    Args:
        provider: LLM provider (openai, anthropic)
        model: Model name
        temperature: Sampling temperature

    Returns:
        LangChain chat model instance
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_entity_extraction_llm() -> BaseChatModel:
    """Get the LLM configured for entity extraction."""
    config = get_config()
    llm_config = config.llm.entity_extraction
    return get_llm(
        provider=llm_config.provider,
        model=llm_config.model,
        temperature=llm_config.temperature,
    )


def get_discovery_llm() -> BaseChatModel:
    """Get the LLM configured for discovery agent."""
    config = get_config()
    llm_config = config.llm.discovery_agent
    return get_llm(
        provider=llm_config.provider,
        model=llm_config.model,
        temperature=llm_config.temperature,
    )


def get_summarizer_llm() -> BaseChatModel:
    """Get the LLM configured for summarization."""
    config = get_config()
    llm_config = config.llm.summarizer
    return get_llm(
        provider=llm_config.provider,
        model=llm_config.model,
        temperature=llm_config.temperature,
    )


async def test_llm_connection(llm: BaseChatModel) -> tuple[bool, str]:
    """Test if an LLM connection works.

    Returns:
        Tuple of (success, message)
    """
    try:
        response = await llm.ainvoke("Say 'OK' if you can read this.")
        return True, f"Connection successful: {response.content[:50]}"
    except Exception as e:
        return False, f"Connection failed: {e}"
