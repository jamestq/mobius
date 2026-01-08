# RSS-RAG Architecture

## Project Overview
A Python-based newsletter aggregation and discovery system using LightRAG for knowledge graph-based retrieval and personalized recommendations.

---

## Technology Stack

### Core Dependencies
- **Package Manager:** Poetry
- **CLI Framework:** Typer
- **RAG System:** LightRAG
- **RSS Parsing:** feedparser
- **Embeddings:** sentence-transformers (default), OpenAI (optional)
- **Database:** SQLite
- **LLM Loader:** llmloader (LangChain wrappers)

---

## Architecture Components

### 1. Feed Management
- Read RSS feed URLs from text file
- Fetch feeds via feedparser
- Parse articles (title, content, link, pub_date)
- Store feed metadata in SQLite (url, last_fetched, active status)

### 2. Article Ingestion (LightRAG)
- Extract full article content
- LightRAG entity extraction (uses LLM via llmloader)
- Build knowledge graph (entities + relationships)
- Generate embeddings (sentence-transformers default, OpenAI optional)
- Store in LightRAG working directory (graph + vectors)
- Log article metadata to SQLite (id, feed_url, title, link, pub_date, ingested_at)

### 3. Search Interface
- User provides search query
- LightRAG hybrid retrieval (vector search + graph traversal)
- Retrieve relevant articles/context
- Summarizer LLM (via llmloader) synthesizes results
- Return summarized answer with source links

### 4. Discovery Agent
- Query SQLite for reading history (read vs unread articles)
- Get read article IDs
- Query LightRAG with reading patterns
- Discovery LLM (via llmloader) analyzes:
  - Graph connections between read/unread articles
  - Topic clusters user engages with
  - Novel connections across newsletters
- Generate personalized recommendations with explanations
- Return top N unread articles

### 5. Reading History Tracker
- User marks articles as read (CLI command or implicit)
- Log to SQLite (article_id, action, timestamp)
- Track interactions for discovery agent

### 6. Storage Layer
- **LightRAG working directory:** Graph structure, embeddings, entity index
- **SQLite database:**
  - `feeds` table (feed metadata)
  - `articles` table (article metadata, links to LightRAG)
  - `reading_history` table (user interactions)

### 7. Configuration
- YAML/TOML config file:
  - Embedding provider (sentence-transformers/openai) + model
  - Entity extraction LLM (via llmloader)
  - Discovery agent LLM (via llmloader)
  - Summarizer LLM (via llmloader)
  - LightRAG working directory path
  - SQLite database path

### 8. CLI Commands (Typer)
- `init`: Setup directories, download models, create DB schema
- `add-feeds <file>`: Import RSS feed URLs
- `fetch`: Pull new articles, ingest into LightRAG
- `search <query> [--mode hybrid|local|global]`: Query with summarization
- `discover [--limit N]`: Get personalized recommendations
- `mark-read <article-id>`: Log reading interaction
- `stats`: Show feed/article counts, graph metrics

---

## Data Flow

```
RSS Feeds (feedparser)
    ↓
Article Extraction
    ↓
LightRAG Ingestion
    ├── Entity Extraction (LLM via llmloader)
    ├── Graph Construction
    └── Embedding Generation (sentence-transformers/OpenAI)
    ↓
Storage
    ├── LightRAG Working Directory (graph + vectors)
    └── SQLite (metadata + reading history)
    ↓
Retrieval
    ├── Search: LightRAG Query → Summarizer LLM → Results
    └── Discovery: Reading History → LightRAG → Discovery Agent LLM → Recommendations
```

---

## Database Schema (SQLite)

### feeds
```sql
CREATE TABLE feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    last_fetched TIMESTAMP,
    fetch_interval INTEGER DEFAULT 3600,
    active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### articles
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    link TEXT UNIQUE NOT NULL,
    pub_date TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lightrag_id TEXT,
    FOREIGN KEY (feed_id) REFERENCES feeds(id)
);
```

### reading_history
```sql
CREATE TABLE reading_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- 'opened', 'read', 'starred', 'dismissed'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_duration INTEGER, -- seconds spent reading
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

---

## Configuration File (config.yaml)

```yaml
# Paths
storage:
  lightrag_dir: "./lightrag_storage"
  sqlite_db: "./rss_rag.db"
  feeds_file: "./feeds.txt"

# Embeddings
embeddings:
  provider: "sentence-transformers"  # or "openai"
  model: "all-MiniLM-L6-v2"  # or "text-embedding-3-small" for OpenAI

# LLMs (via llmloader)
llm:
  entity_extraction:
    provider: "openai"
    model: "gpt-4o-mini"
    temperature: 0.0
  
  discovery_agent:
    provider: "anthropic"
    model: "claude-sonnet-4"
    temperature: 0.7
  
  summarizer:
    provider: "openai"
    model: "gpt-4o-mini"
    temperature: 0.3

# LightRAG settings
lightrag:
  chunk_size: 1200
  chunk_overlap: 100
  max_graph_depth: 3

# Feed fetching
feeds:
  fetch_interval: 3600  # seconds
  max_articles_per_fetch: 50
```

---

## Feeds Input File (feeds.txt)

```
# TLDR Newsletters
https://tldr.tech/tech/rss
https://tldr.tech/ai/rss
https://tldr.tech/crypto/rss

# Substack Examples
https://example.substack.com/feed
https://another.substack.com/feed

# Comments are supported
# Add your RSS feeds here
```

---

## Implementation Phases

### Phase 1: Core Infrastructure
- Setup Poetry project structure
- Implement CLI with Typer
- Create SQLite schema
- RSS feed fetching with feedparser
- Basic article storage

### Phase 2: LightRAG Integration
- Configure LightRAG with llmloader
- Implement entity extraction pipeline
- Setup embedding generation (sentence-transformers default)
- Test graph construction with sample articles

### Phase 3: Search & Retrieval
- Implement search command with LightRAG queries
- Integrate summarizer LLM
- Support multiple query modes (hybrid/local/global)
- Add source linking

### Phase 4: Discovery Agent
- Reading history tracking
- Discovery agent implementation
- Recommendation generation
- Personalization based on reading patterns

### Phase 5: Polish & Documentation
- Error handling
- Logging
- Cost tracking (API calls)
- Comprehensive README
- Example configurations

---

## Key Design Decisions

### Why LightRAG over ChromaDB?
- Built-in knowledge graph for topic connections
- Hybrid retrieval (vector + graph traversal)
- Better for discovery use case
- Experiment with graph-based RAG

### Why sentence-transformers as default?
- Free and local (privacy-first)
- No API costs
- Works offline
- Good quality embeddings
- OpenAI available as premium option

### Why dual LLM setup?
- Discovery agent needs reasoning (expensive/smart model)
- Summarizer needs speed (cheap/fast model)
- Cost optimization through tiered approach

### Why SQLite for metadata?
- Simple, no server needed
- Good enough for personal use
- Easy to query reading history
- LightRAG handles graph/vector storage

---

## Cost Considerations

### Free (Default Setup)
- sentence-transformers embeddings (local)
- Local LLM for entity extraction (optional)
- Storage (disk space only)

### Paid (API Usage)
- Entity extraction: ~$0.01-0.05 per article (GPT-4o-mini)
- Discovery agent: ~$0.10-0.50 per run (Claude Sonnet)
- Summarizer: ~$0.001-0.01 per search (GPT-4o-mini)
- OpenAI embeddings: ~$0.02 per 1M tokens

### Estimated Monthly Cost (100 articles/week)
- Entity extraction: ~$2-20
- Discovery (daily): ~$3-15
- Search (10/day): ~$0.30-3
- **Total: ~$5-40/month** depending on model choices

---

## Development Environment

### Setup with Poetry
```bash
poetry new rss-rag
cd rss-rag
poetry add typer feedparser lightrag sentence-transformers llmloader pyyaml
poetry add --group dev pytest black ruff
```

### Project Structure
```
rss-rag/
├── pyproject.toml
├── README.md
├── feeds.txt
├── config.yaml
├── rss_rag/
│   ├── __init__.py
│   ├── cli.py           # Typer CLI commands
│   ├── feed_manager.py  # RSS fetching
│   ├── ingestion.py     # LightRAG integration
│   ├── search.py        # Search interface
│   ├── discovery.py     # Discovery agent
│   ├── database.py      # SQLite operations
│   └── config.py        # Configuration loading
└── tests/
    └── ...
```

---

## Notes & Caveats

- LightRAG is experimental (smaller community than ChromaDB)
- Entity extraction costs scale with article count
- Graph quality depends on LLM entity extraction performance
- First ingestion will be slow (entity extraction per article)
- Model downloads (~400MB for sentence-transformers)
- Requires Python 3.9+
- GPU optional but speeds up local embeddings significantly
