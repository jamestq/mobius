from __future__ import annotations

from pathlib import Path

import yaml

from bagent.models import Agent, Guardrails, Pipeline, PipelineStep, Requirement


def parse_agent(path: Path) -> Agent:
    """Parse an agent .md file with YAML frontmatter delimited by ---."""
    content = path.read_text()

    if not content.startswith("---"):
        raise ValueError(f"Agent file {path} must start with YAML frontmatter (---)")

    # Split on --- delimiters: first split gives ['', frontmatter, prompt_body]
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Agent file {path} must have opening and closing --- delimiters")

    frontmatter = yaml.safe_load(parts[1])
    prompt = parts[2].strip()

    if not frontmatter:
        raise ValueError(f"Agent file {path} has empty frontmatter")

    requirements = [
        Requirement(
            name=r["name"],
            description=r.get("description", ""),
            default=r.get("default"),
        )
        for r in frontmatter.get("requirements", [])
    ]

    guardrails_data = frontmatter.get("guardrails", {})
    guardrails = Guardrails(
        max_tokens=guardrails_data.get("max_tokens"),
        timeout=guardrails_data.get("timeout"),
        max_retries=guardrails_data.get("max_retries", 3),
        banned_patterns=guardrails_data.get("banned_patterns", []),
        required_patterns=guardrails_data.get("required_patterns", []),
    )

    return Agent(
        name=frontmatter["name"],
        description=frontmatter.get("description", ""),
        model=frontmatter.get("model", "sonnet"),
        schema=frontmatter.get("schema"),
        tools=frontmatter.get("tools", []),
        requirements=requirements,
        guardrails=guardrails,
        prompt=prompt,
    )


def parse_pipeline(path: Path) -> Pipeline:
    """Parse a pipeline .yaml config file."""
    data = yaml.safe_load(path.read_text())

    steps = []
    for step_data in data.get("steps", []):
        step_guardrails = None
        if "guardrails" in step_data:
            g = step_data["guardrails"]
            step_guardrails = Guardrails(
                max_tokens=g.get("max_tokens"),
                timeout=g.get("timeout"),
                max_retries=g.get("max_retries", 3),
                banned_patterns=g.get("banned_patterns", []),
                required_patterns=g.get("required_patterns", []),
            )
        steps.append(PipelineStep(agent=step_data["agent"], guardrails=step_guardrails))

    return Pipeline(
        name=data["name"],
        description=data.get("description", ""),
        agents_dir=data.get("agents_dir", "./agents"),
        steps=steps,
    )


def load_pipeline_agents(pipeline: Pipeline, pipeline_path: Path) -> list[Agent]:
    """Resolve agents_dir relative to the pipeline file and load each referenced agent."""
    agents_dir = (pipeline_path.parent / pipeline.agents_dir).resolve()

    agents = []
    for step in pipeline.steps:
        agent_path = agents_dir / f"{step.agent}.md"
        if not agent_path.exists():
            raise FileNotFoundError(f"Agent file not found: {agent_path}")
        agents.append(parse_agent(agent_path))

    return agents
