"""Configuration loading and validation."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class StorageConfig(BaseModel):
    """Storage paths configuration."""

    lightrag_dir: Path = Field(default=Path("./lightrag_storage"))
    sqlite_db: Path = Field(default=Path("./rss_rag.db"))
    feeds_file: Path = Field(default=Path("./feeds.txt"))


class EmbeddingsConfig(BaseModel):
    """Embeddings model configuration."""

    provider: Literal["sentence-transformers", "openai"] = "sentence-transformers"
    model: str = "all-MiniLM-L6-v2"


class LLMConfig(BaseModel):
    """Single LLM configuration."""

    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


class LLMsConfig(BaseModel):
    """LLM configurations for different tasks."""

    entity_extraction: LLMConfig = Field(default_factory=LLMConfig)
    discovery_agent: LLMConfig = Field(
        default_factory=lambda: LLMConfig(
            provider="anthropic", model="claude-sonnet-4", temperature=0.7
        )
    )
    summarizer: LLMConfig = Field(default_factory=lambda: LLMConfig(temperature=0.3))


class LightRAGConfig(BaseModel):
    """LightRAG-specific configuration."""

    chunk_size: int = 1200
    chunk_overlap: int = 100
    max_graph_depth: int = 3


class FeedsConfig(BaseModel):
    """Feed fetching configuration."""

    fetch_interval: int = 3600
    max_articles_per_fetch: int = 50


class Config(BaseModel):
    """Main configuration model."""

    storage: StorageConfig = Field(default_factory=StorageConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    llm: LLMsConfig = Field(default_factory=LLMsConfig)
    lightrag: LightRAGConfig = Field(default_factory=LightRAGConfig)
    feeds: FeedsConfig = Field(default_factory=FeedsConfig)


def load_config(config_path: Path | None = None) -> Config:
    """Load config from YAML file, or use defaults.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Config instance with loaded or default values.
    """
    if config_path and config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return Config.model_validate(data or {})
    return Config()


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global config instance.

    Returns:
        The global Config instance, loading from config.yaml if not set.
    """
    global _config
    if _config is None:
        _config = load_config(Path("config.yaml"))
    return _config


def set_config(config: Config) -> None:
    """Set the global config instance.

    Args:
        config: The Config instance to set as global.
    """
    global _config
    _config = config


def reset_config() -> None:
    """Reset the global config instance to None."""
    global _config
    _config = None
