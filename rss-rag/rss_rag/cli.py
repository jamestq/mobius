"""RSS-RAG Command Line Interface."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from rss_rag.config import get_config, load_config, set_config
from rss_rag.cost_tracker import get_cost_tracker, format_cost_summary
from rss_rag.database import (
    init_db,
    get_connection,
    get_stats,
    add_reading_history,
    get_article,
)
from rss_rag.discovery import discover_articles, format_discovery_result
from rss_rag.feed_manager import (
    import_feeds_from_file,
    fetch_all_feeds,
    fetch_and_store_feed,
)
from rss_rag.ingestion import ingest_pending_articles, get_pending_count
from rss_rag.logging_config import setup_logging
from rss_rag.search import search, QueryMode, format_search_result


app = typer.Typer(
    name="rss-rag",
    help="Newsletter aggregation and discovery system using LightRAG",
    add_completion=False,
)

console = Console()
logger = logging.getLogger(__name__)


@app.callback()
def main(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """RSS-RAG: Newsletter aggregation with knowledge graph retrieval."""
    setup_logging(verbose=verbose)

    if config_file:
        config = load_config(config_file)
        set_config(config)


@app.command()
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="Reinitialize existing database"
    ),
) -> None:
    """Initialize RSS-RAG: create database and directories."""
    config = get_config()

    # Create storage directories
    lightrag_dir = config.storage.lightrag_dir
    lightrag_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓[/green] Created LightRAG directory: {lightrag_dir}")

    # Initialize database
    db_path = config.storage.sqlite_db
    if db_path.exists() and not force:
        console.print(f"[yellow]![/yellow] Database already exists: {db_path}")
        console.print("  Use --force to reinitialize")
    else:
        if db_path.exists():
            db_path.unlink()
        init_db(db_path)
        console.print(f"[green]✓[/green] Initialized database: {db_path}")

    # Check for feeds file
    feeds_file = config.storage.feeds_file
    if not feeds_file.exists():
        console.print(f"[yellow]![/yellow] No feeds file found at: {feeds_file}")
        console.print("  Create one and run 'rss-rag add-feeds' to import")
    else:
        console.print(f"[green]✓[/green] Found feeds file: {feeds_file}")

    console.print("\n[bold green]Initialization complete![/bold green]")


@app.command("add-feeds")
def add_feeds(
    file: Optional[Path] = typer.Argument(
        None, help="Path to feeds file (default: from config)"
    ),
) -> None:
    """Import RSS feed URLs from a file."""
    config = get_config()

    feeds_file = file or config.storage.feeds_file
    if not feeds_file.exists():
        console.print(f"[red]Error:[/red] Feeds file not found: {feeds_file}")
        raise typer.Exit(1)

    db_path = config.storage.sqlite_db
    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    count = import_feeds_from_file(db_path, feeds_file)

    if count > 0:
        console.print(f"[green]✓[/green] Added {count} new feed(s)")
    else:
        console.print("[yellow]![/yellow] No new feeds to add (all already exist)")


@app.command()
def fetch(
    feed_url: Optional[str] = typer.Argument(None, help="Fetch specific feed URL"),
    max_articles: int = typer.Option(50, "--max", "-m", help="Max articles per feed"),
) -> None:
    """Fetch new articles from RSS feeds."""
    config = get_config()
    db_path = config.storage.sqlite_db

    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    if feed_url:
        # Fetch single feed
        with console.status(f"Fetching {feed_url}..."):
            result = fetch_and_store_feed(db_path, feed_url, max_articles)

        if result.error:
            console.print(f"[red]✗[/red] {result.feed_url}: {result.error}")
        else:
            console.print(
                f"[green]✓[/green] {result.feed_title or result.feed_url}: "
                f"{result.articles_new} new / {result.articles_found} total"
            )
    else:
        # Fetch all feeds
        feeds_file = config.storage.feeds_file

        total_new = 0
        total_found = 0
        errors = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching feeds...", total=None)

            for result in fetch_all_feeds(db_path, feeds_file, max_articles):
                if result.error:
                    errors += 1
                    progress.update(task, description=f"[red]✗[/red] {result.feed_url}")
                else:
                    total_new += result.articles_new
                    total_found += result.articles_found
                    progress.update(
                        task,
                        description=f"[green]✓[/green] {result.feed_title or result.feed_url}",
                    )

        console.print()
        console.print(f"[bold]Fetch complete:[/bold]")
        console.print(f"  New articles: {total_new}")
        console.print(f"  Total found: {total_found}")
        if errors:
            console.print(f"  [red]Errors: {errors}[/red]")


@app.command()
def ingest(
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Max articles to ingest"
    ),
) -> None:
    """Ingest fetched articles into LightRAG knowledge graph."""
    config = get_config()
    db_path = config.storage.sqlite_db

    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    pending = get_pending_count(db_path)
    if pending == 0:
        console.print("[yellow]![/yellow] No articles pending ingestion")
        return

    to_process = min(limit, pending) if limit else pending
    console.print(f"Ingesting {to_process} of {pending} pending articles...")

    success_count = 0
    error_count = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Ingesting...", total=to_process)

        for result in ingest_pending_articles(db_path, limit):
            if result.success:
                success_count += 1
                progress.update(
                    task,
                    advance=1,
                    description=f"[green]✓[/green] {result.title[:40]}...",
                )
            else:
                error_count += 1
                progress.update(
                    task,
                    advance=1,
                    description=f"[red]✗[/red] {result.title[:40]}: {result.error}",
                )

    console.print()
    console.print("[bold]Ingestion complete:[/bold]")
    console.print(f"  Successful: {success_count}")
    if error_count:
        console.print(f"  [red]Errors: {error_count}[/red]")


@app.command()
def stats() -> None:
    """Show database statistics."""
    config = get_config()
    db_path = config.storage.sqlite_db

    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    conn = get_connection(db_path)
    try:
        db_stats = get_stats(conn)
    finally:
        conn.close()

    table = Table(title="RSS-RAG Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Feeds", str(db_stats.get("total_feeds", 0)))
    table.add_row("Active Feeds", str(db_stats.get("active_feeds", 0)))
    table.add_row("Total Articles", str(db_stats.get("total_articles", 0)))
    table.add_row("Read Articles", str(db_stats.get("read_articles", 0)))
    table.add_row("Unread Articles", str(db_stats.get("unread_articles", 0)))

    # Show ingested count if available
    ingested = db_stats.get("ingested_articles", 0)
    if ingested > 0:
        table.add_row("Ingested to LightRAG", str(ingested))

    console.print(table)


@app.command()
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    mode: str = typer.Option(
        "hybrid", "--mode", "-m", help="Query mode: hybrid, local, global, naive"
    ),
    no_summary: bool = typer.Option(
        False, "--no-summary", help="Skip LLM summarization"
    ),
    raw: bool = typer.Option(False, "--raw", "-r", help="Show raw response"),
) -> None:
    """Search the knowledge graph."""
    config = get_config()

    # Validate mode
    try:
        query_mode = QueryMode(mode.lower())
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid mode '{mode}'. Use: hybrid, local, global, naive"
        )
        raise typer.Exit(1)

    # Check if lightrag directory exists
    if not config.storage.lightrag_dir.exists():
        console.print(
            "[red]Error:[/red] LightRAG not initialized. Run 'rss-rag init' and 'rss-rag ingest' first."
        )
        raise typer.Exit(1)

    with console.status(f"Searching ({query_mode.value} mode)..."):
        result = search(query, mode=query_mode, summarize=not no_summary)

    if result.error:
        console.print(f"[red]Error:[/red] {result.error}")
        raise typer.Exit(1)

    console.print()
    console.print(format_search_result(result, show_raw=raw))


@app.command("mark-read")
def mark_read(
    article_id: int = typer.Argument(..., help="Article ID to mark as read"),
    action: str = typer.Option(
        "read", "--action", "-a", help="Action type: opened, read, starred, dismissed"
    ),
) -> None:
    """Mark an article as read in reading history."""
    config = get_config()
    db_path = config.storage.sqlite_db

    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    valid_actions = ["opened", "read", "starred", "dismissed"]
    if action not in valid_actions:
        console.print(
            f"[red]Error:[/red] Invalid action. Use: {', '.join(valid_actions)}"
        )
        raise typer.Exit(1)

    conn = get_connection(db_path)
    try:
        article = get_article(conn, article_id)
        if not article:
            console.print(f"[red]Error:[/red] Article {article_id} not found")
            raise typer.Exit(1)

        add_reading_history(conn, article_id, action)
        console.print(
            f"[green]✓[/green] Marked article {article_id} as '{action}': {article['title'][:50]}..."
        )
    finally:
        conn.close()


@app.command()
def discover(
    limit: int = typer.Option(5, "--limit", "-l", help="Number of recommendations"),
) -> None:
    """Get personalized article recommendations."""
    config = get_config()
    db_path = config.storage.sqlite_db

    if not db_path.exists():
        console.print(
            "[red]Error:[/red] Database not initialized. Run 'rss-rag init' first."
        )
        raise typer.Exit(1)

    with console.status("Analyzing reading patterns..."):
        result = discover_articles(db_path, limit)

    console.print()
    console.print(format_discovery_result(result))


@app.command()
def costs(
    clear: bool = typer.Option(False, "--clear", help="Clear cost history"),
) -> None:
    """Show API cost tracking information."""
    tracker = get_cost_tracker()

    if clear:
        tracker.clear()
        console.print("[green]✓[/green] Cost history cleared")
        return

    summary = tracker.get_summary()

    if summary.total_calls == 0:
        console.print("[yellow]![/yellow] No API calls recorded yet")
        return

    console.print(format_cost_summary(summary))


def main_cli() -> None:
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    main_cli()
