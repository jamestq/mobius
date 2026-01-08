"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from rss_rag.config import (
    Config,
    EmbeddingsConfig,
    FeedsConfig,
    LightRAGConfig,
    LLMConfig,
    LLMsConfig,
    StorageConfig,
    load_config,
    get_config,
    set_config,
    reset_config,
)


class TestDefaultConfig:
    """Tests for default configuration values."""

    def test_default_config_creates_valid_instance(self):
        """Test that default config can be created."""
        config = Config()
        assert config is not None

    def test_default_storage_config(self):
        """Test default storage paths."""
        config = Config()
        assert config.storage.lightrag_dir == Path("./lightrag_storage")
        assert config.storage.sqlite_db == Path("./rss_rag.db")
        assert config.storage.feeds_file == Path("./feeds.txt")

    def test_default_embeddings_config(self):
        """Test default embeddings settings."""
        config = Config()
        assert config.embeddings.provider == "sentence-transformers"
        assert config.embeddings.model == "all-MiniLM-L6-v2"

    def test_default_llm_config(self):
        """Test default LLM settings."""
        config = Config()
        assert config.llm.entity_extraction.provider == "openai"
        assert config.llm.entity_extraction.model == "gpt-4o-mini"
        assert config.llm.entity_extraction.temperature == 0.0

    def test_default_discovery_agent_config(self):
        """Test default discovery agent LLM settings."""
        config = Config()
        assert config.llm.discovery_agent.provider == "anthropic"
        assert config.llm.discovery_agent.model == "claude-sonnet-4"
        assert config.llm.discovery_agent.temperature == 0.7

    def test_default_summarizer_config(self):
        """Test default summarizer LLM settings."""
        config = Config()
        assert config.llm.summarizer.provider == "openai"
        assert config.llm.summarizer.temperature == 0.3

    def test_default_lightrag_config(self):
        """Test default LightRAG settings."""
        config = Config()
        assert config.lightrag.chunk_size == 1200
        assert config.lightrag.chunk_overlap == 100
        assert config.lightrag.max_graph_depth == 3

    def test_default_feeds_config(self):
        """Test default feeds settings."""
        config = Config()
        assert config.feeds.fetch_interval == 3600
        assert config.feeds.max_articles_per_fetch == 50


class TestLoadConfig:
    """Tests for loading configuration from YAML."""

    def test_load_config_nonexistent_file(self):
        """Test loading from non-existent file returns defaults."""
        config = load_config(Path("/nonexistent/config.yaml"))
        assert config == Config()

    def test_load_config_none_path(self):
        """Test loading with None path returns defaults."""
        config = load_config(None)
        assert config == Config()

    def test_load_config_from_yaml(self):
        """Test loading configuration from a YAML file."""
        yaml_content = """
storage:
  lightrag_dir: "/custom/lightrag"
  sqlite_db: "/custom/db.sqlite"
  feeds_file: "/custom/feeds.txt"

embeddings:
  provider: "openai"
  model: "text-embedding-3-small"

lightrag:
  chunk_size: 2000
  chunk_overlap: 200
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config.storage.lightrag_dir == Path("/custom/lightrag")
            assert config.storage.sqlite_db == Path("/custom/db.sqlite")
            assert config.embeddings.provider == "openai"
            assert config.embeddings.model == "text-embedding-3-small"
            assert config.lightrag.chunk_size == 2000
            assert config.lightrag.chunk_overlap == 200
            # Check defaults are still applied
            assert config.feeds.fetch_interval == 3600
        finally:
            temp_path.unlink()

    def test_load_config_empty_yaml(self):
        """Test loading from empty YAML file returns defaults."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config == Config()
        finally:
            temp_path.unlink()

    def test_load_config_partial_yaml(self):
        """Test loading partial config merges with defaults."""
        yaml_content = """
feeds:
  fetch_interval: 1800
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)
            assert config.feeds.fetch_interval == 1800
            assert config.feeds.max_articles_per_fetch == 50  # default
            assert config.storage.sqlite_db == Path("./rss_rag.db")  # default
        finally:
            temp_path.unlink()


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_embeddings_provider_validation(self):
        """Test that embeddings provider is validated."""
        # Valid providers should work
        config = EmbeddingsConfig(provider="openai")
        assert config.provider == "openai"

        config = EmbeddingsConfig(provider="sentence-transformers")
        assert config.provider == "sentence-transformers"

        # Invalid provider should raise
        with pytest.raises(Exception):
            EmbeddingsConfig(provider="invalid-provider")

    def test_temperature_validation(self):
        """Test LLM temperature values."""
        config = LLMConfig(temperature=0.5)
        assert config.temperature == 0.5

        config = LLMConfig(temperature=0.0)
        assert config.temperature == 0.0

        config = LLMConfig(temperature=1.0)
        assert config.temperature == 1.0

    def test_path_conversion(self):
        """Test that string paths are converted to Path objects."""
        config = StorageConfig(
            lightrag_dir="/some/path",  # type: ignore
            sqlite_db="./db.sqlite",  # type: ignore
        )
        assert isinstance(config.lightrag_dir, Path)
        assert isinstance(config.sqlite_db, Path)


class TestGlobalConfig:
    """Tests for global config management."""

    def setup_method(self):
        """Reset global config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset global config after each test."""
        reset_config()

    def test_set_and_get_config(self):
        """Test setting and getting global config."""
        custom_config = Config(feeds=FeedsConfig(fetch_interval=7200))
        set_config(custom_config)

        retrieved = get_config()
        assert retrieved.feeds.fetch_interval == 7200

    def test_get_config_loads_default(self):
        """Test that get_config loads config when not set."""
        # This will try to load from config.yaml or use defaults
        config = get_config()
        assert config is not None
        assert isinstance(config, Config)
