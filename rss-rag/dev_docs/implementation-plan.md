# RSS-RAG Implementation Plan

## Step 1: Project Scaffold
- [ ] Create Poetry project with dependencies (`typer`, `feedparser`, `lightrag`, `sentence-transformers`, `llmloader`, `pyyaml`, `pytest`, `black`, `ruff`)
- [ ] Create directory structure: `rss_rag/{cli,feed_manager,ingestion,search,discovery,database,config}/`
- [ ] Setup `.gitignore`, example `config.yaml`, example `feeds.txt`

## Step 2: Configuration & Database Layer
- [ ] `config.py`: Load YAML config with validation
- [ ] `database.py`: SQLite schema (feeds, articles, reading_history) + CRUD operations
- [ ] Unit tests for database operations

## Step 3: Feed Manager
- [ ] `feed_manager.py`: Parse `feeds.txt`, fetch via `feedparser`, extract metadata (title, content, link, pub_date)
- [ ] Store feeds/articles in SQLite with error handling for malformed feeds
- [ ] Unit tests for feed parsing

## Step 4: CLI Foundation
- [ ] `cli.py`: Typer app with commands: `init`, `add-feeds`, `stats`
- [ ] Basic logging configuration
- [ ] Tests for CLI commands

## Step 5: LLM & Embedding Setup
- [ ] Configure `sentence-transformers` embeddings (OpenAI optional)
- [ ] Configure `llmloader` for entity extraction LLM (GPT-4o-mini default)
- [ ] Verify connectivity with sample text

## Step 6: Ingestion Pipeline
- [ ] `ingestion.py`: Extract content → LightRAG entity extraction → build knowledge graph → store embeddings → link to SQLite
- [ ] `fetch` CLI command with progress indicators
- [ ] Test with 5-10 articles

## Step 7: Search Interface
- [ ] `search.py`: LightRAG hybrid retrieval (vector + graph), query modes (hybrid/local/global)
- [ ] Summarizer LLM for result synthesis, format with source links
- [ ] `search` CLI command with `--mode` and `--limit` flags

## Step 8: Reading History & Discovery
- [ ] Add reading history tracking to `database.py`
- [ ] `mark-read` CLI command (track: opened, read, starred, dismissed)
- [ ] `discovery.py`: Analyze reading patterns, generate recommendations with explanations
- [ ] `discover` CLI command with `--limit` flag

## Step 9: Polish & Harden
- [ ] Comprehensive error handling + retry logic for API/feed failures
- [ ] Structured logging (file + console), `--verbose` flag
- [ ] API cost tracking

## Step 10: Documentation & Testing
- [ ] README: installation, config guide, CLI reference, examples, cost estimates
- [ ] >80% test coverage, integration tests, performance tests (1000+ articles)

---

## Future Enhancements
- Export/import reading history
- Full-text extraction beyond RSS content
- Web interface (FastAPI)
- Email digest, multi-user, feed tagging, sentiment analysis

---

## Success Metrics
- Ingest 100+ articles from 10+ feeds
- Search accuracy >80%, discovery relevance >50%
- API costs <$40/month, CLI response <2s

## Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| LightRAG issues | Fallback to ChromaDB |
| High API costs | Local LLMs for extraction |
| Feed failures | Robust error handling, skip malformed |
