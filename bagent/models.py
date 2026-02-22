from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Requirement:
    name: str
    description: str
    default: str | None = None


@dataclass
class Guardrails:
    max_tokens: int | None = None
    timeout: int | None = None
    max_retries: int = 3
    banned_patterns: list[str] = field(default_factory=list)
    required_patterns: list[str] = field(default_factory=list)


@dataclass
class Agent:
    name: str
    description: str
    prompt: str
    model: str = "sonnet"
    schema: dict | None = None
    tools: list[str] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    guardrails: Guardrails = field(default_factory=Guardrails)


@dataclass
class PipelineStep:
    agent: str
    guardrails: Guardrails | None = None


@dataclass
class Pipeline:
    name: str
    description: str
    agents_dir: str
    steps: list[PipelineStep] = field(default_factory=list)


def merge_guardrails(agent_g: Guardrails, step_g: Guardrails | None) -> Guardrails:
    """Merge agent-level and step-level guardrails. Stricter wins for scalars, concatenate for lists."""
    if step_g is None:
        return agent_g

    def stricter_min(a: int | None, b: int | None) -> int | None:
        if a is None:
            return b
        if b is None:
            return a
        return min(a, b)

    return Guardrails(
        max_tokens=stricter_min(agent_g.max_tokens, step_g.max_tokens),
        timeout=stricter_min(agent_g.timeout, step_g.timeout),
        max_retries=min(agent_g.max_retries, step_g.max_retries),
        banned_patterns=agent_g.banned_patterns + step_g.banned_patterns,
        required_patterns=agent_g.required_patterns + step_g.required_patterns,
    )
