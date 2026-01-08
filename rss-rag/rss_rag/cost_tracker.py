"""API cost tracking for LLM and embedding calls."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Literal

logger = logging.getLogger(__name__)

# Approximate pricing per 1M tokens (as of 2024)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
    "text-embedding-3-large": {"input": 0.13, "output": 0.0},
}


@dataclass
class APICall:
    """Record of a single API call."""

    timestamp: str
    operation: str  # entity_extraction, summarization, discovery, embedding
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class CostSummary:
    """Summary of API costs."""

    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    by_operation: dict[str, float] = field(default_factory=dict)
    by_model: dict[str, float] = field(default_factory=dict)


class CostTracker:
    """Thread-safe API cost tracker with persistence."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize cost tracker.

        Args:
            storage_path: Path to store cost history (JSON)
        """
        self.storage_path = storage_path
        self.calls: list[APICall] = []
        self._lock = Lock()

        if storage_path and storage_path.exists():
            self._load()

    def record_call(
        self,
        operation: str,
        model: str,
        input_tokens: int,
        output_tokens: int = 0,
    ) -> float:
        """Record an API call and return estimated cost.

        Args:
            operation: Type of operation
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Estimated cost in USD
        """
        # Calculate cost
        pricing = PRICING.get(model, {"input": 0.01, "output": 0.01})
        cost = (input_tokens / 1_000_000) * pricing["input"] + (
            output_tokens / 1_000_000
        ) * pricing["output"]

        call = APICall(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        with self._lock:
            self.calls.append(call)
            self._save()

        logger.debug(
            f"API call: {operation} ({model}) - "
            f"{input_tokens} in / {output_tokens} out = ${cost:.6f}"
        )

        return cost

    def get_summary(self, since: datetime | None = None) -> CostSummary:
        """Get cost summary, optionally filtered by date.

        Args:
            since: Only include calls after this datetime

        Returns:
            CostSummary with aggregated data
        """
        summary = CostSummary()

        with self._lock:
            for call in self.calls:
                # Filter by date if specified
                if since:
                    call_time = datetime.fromisoformat(call.timestamp)
                    if call_time < since:
                        continue

                summary.total_calls += 1
                summary.total_input_tokens += call.input_tokens
                summary.total_output_tokens += call.output_tokens
                summary.total_cost_usd += call.cost_usd

                # By operation
                summary.by_operation[call.operation] = (
                    summary.by_operation.get(call.operation, 0) + call.cost_usd
                )

                # By model
                summary.by_model[call.model] = (
                    summary.by_model.get(call.model, 0) + call.cost_usd
                )

        return summary

    def _save(self) -> None:
        """Save calls to storage."""
        if not self.storage_path:
            return

        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump([asdict(c) for c in self.calls], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cost data: {e}")

    def _load(self) -> None:
        """Load calls from storage."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
            self.calls = [APICall(**c) for c in data]
        except Exception as e:
            logger.error(f"Failed to load cost data: {e}")
            self.calls = []

    def clear(self) -> None:
        """Clear all recorded calls."""
        with self._lock:
            self.calls.clear()
            self._save()


# Global cost tracker instance
_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _tracker
    if _tracker is None:
        from rss_rag.config import get_config

        config = get_config()
        storage_path = config.storage.lightrag_dir / "cost_history.json"
        _tracker = CostTracker(storage_path)
    return _tracker


def format_cost_summary(summary: CostSummary) -> str:
    """Format cost summary for display."""
    lines = [
        "💰 API Cost Summary",
        f"   Total calls: {summary.total_calls:,}",
        f"   Input tokens: {summary.total_input_tokens:,}",
        f"   Output tokens: {summary.total_output_tokens:,}",
        f"   Total cost: ${summary.total_cost_usd:.4f}",
    ]

    if summary.by_operation:
        lines.append("\n   By Operation:")
        for op, cost in sorted(summary.by_operation.items()):
            lines.append(f"     {op}: ${cost:.4f}")

    if summary.by_model:
        lines.append("\n   By Model:")
        for model, cost in sorted(summary.by_model.items()):
            lines.append(f"     {model}: ${cost:.4f}")

    return "\n".join(lines)
