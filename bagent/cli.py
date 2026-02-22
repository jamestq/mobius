from pathlib import Path

import typer

from bagent.builder import build_pipeline

app = typer.Typer(help="bagent - Build agentic coding pipelines", invoke_without_command=True)


@app.callback()
def main():
    """bagent - Build agentic coding pipelines."""


@app.command("build")
def build(
    pipeline_yaml: Path = typer.Argument(..., help="Path to pipeline .yaml config"),
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing output directory"),
):
    """Build a self-contained pipeline from a YAML config."""
    if not pipeline_yaml.exists():
        typer.echo(f"Error: Pipeline file not found: {pipeline_yaml}", err=True)
        raise typer.Exit(1)

    try:
        result_dir = build_pipeline(pipeline_yaml, output_dir=output_dir, force=force)
    except FileExistsError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
    except (FileNotFoundError, ValueError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(f"\nPipeline built successfully!")
    typer.echo(f"  Output: {result_dir}")
    typer.echo(f"  Run:    {result_dir}/entry.sh \"<your task>\"")
