from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from bagent.generator import generate_entry_sh
from bagent.models import Agent, Pipeline, merge_guardrails
from bagent.parser import load_pipeline_agents, parse_pipeline


def collect_requirements(agents: list[Agent]) -> dict[str, str]:
    """Collect all requirements from agents, prompt interactively for missing values."""
    all_requirements: dict[str, str] = {}

    for agent in agents:
        for req in agent.requirements:
            if req.name in all_requirements:
                continue
            if req.default is not None:
                value = typer.prompt(
                    f"{req.name} ({req.description})",
                    default=req.default,
                )
            else:
                value = typer.prompt(f"{req.name} ({req.description})")
            all_requirements[req.name] = value

    return all_requirements


def substitute_requirements(prompt: str, values: dict[str, str]) -> str:
    """Replace {{requirement_name}} placeholders in prompt text."""
    result = prompt
    for name, value in values.items():
        result = result.replace(f"{{{{{name}}}}}", value)
    return result


def build_pipeline(
    pipeline_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Build a self-contained pipeline directory from a pipeline config."""
    pipeline = parse_pipeline(pipeline_path)
    agents = load_pipeline_agents(pipeline, pipeline_path)

    # Determine output directory
    if output_dir is None:
        output_dir = Path("output") / pipeline.name
    output_dir = output_dir.resolve()

    if output_dir.exists():
        if not force:
            raise FileExistsError(
                f"Output directory already exists: {output_dir}\n"
                "Use --force to overwrite."
            )
        shutil.rmtree(output_dir)

    # Collect and substitute requirements
    req_values = collect_requirements(agents)

    # Create directory structure
    (output_dir / "agents").mkdir(parents=True)
    (output_dir / "schemas").mkdir(parents=True)
    (output_dir / "runs").mkdir(parents=True)

    # Write agent prompts and schemas
    for agent in agents:
        prompt = substitute_requirements(agent.prompt, req_values)
        (output_dir / "agents" / f"{agent.name}.md").write_text(prompt + "\n")

        if agent.schema:
            (output_dir / "schemas" / f"{agent.name}.json").write_text(
                json.dumps(agent.schema, indent=2) + "\n"
            )

    # Copy validate_schema.py into the output directory
    validator_src = Path(__file__).parent / "validate_schema.py"
    shutil.copy2(validator_src, output_dir / "validate_schema.py")

    # Build merged guardrails for each step
    step_guardrails = []
    agent_map = {a.name: a for a in agents}
    for step in pipeline.steps:
        agent = agent_map[step.agent]
        merged = merge_guardrails(agent.guardrails, step.guardrails)
        step_guardrails.append(merged)

    # Generate entry.sh
    entry_sh = generate_entry_sh(pipeline, agents, step_guardrails)
    entry_path = output_dir / "entry.sh"
    entry_path.write_text(entry_sh)
    entry_path.chmod(0o755)

    return output_dir
