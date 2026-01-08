# RSS-RAG

Newsletter aggregation and discovery system using LightRAG.

## Installation

```bash
poetry install
```

## Usage

```bash
poetry run python -m rss_rag.cli
```

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black rss_rag tests

# Lint code
poetry run ruff check rss_rag tests
```

## Configuration

Copy `config.yaml` and customize settings for:
- LightRAG storage paths
- Embedding model configuration
- LLM providers for different tasks
- Feed fetching parameters
