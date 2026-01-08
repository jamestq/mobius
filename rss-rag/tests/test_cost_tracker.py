"""Tests for cost tracker module."""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from rss_rag.cost_tracker import (
    CostTracker,
    CostSummary,
    APICall,
    format_cost_summary,
)


@pytest.fixture
def tracker():
    """Create a cost tracker with temporary storage."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = Path(f.name)
    tracker = CostTracker(path)
    yield tracker
    path.unlink(missing_ok=True)


class TestCostTracker:
    def test_record_call(self, tracker):
        cost = tracker.record_call(
            operation="test",
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost > 0
        assert len(tracker.calls) == 1
        assert tracker.calls[0].operation == "test"

    def test_get_summary(self, tracker):
        tracker.record_call("op1", "gpt-4o-mini", 1000, 500)
        tracker.record_call("op2", "gpt-4o-mini", 2000, 1000)

        summary = tracker.get_summary()

        assert summary.total_calls == 2
        assert summary.total_input_tokens == 3000
        assert summary.total_output_tokens == 1500
        assert summary.total_cost_usd > 0

    def test_summary_by_operation(self, tracker):
        tracker.record_call("ingest", "gpt-4o-mini", 1000, 500)
        tracker.record_call("search", "gpt-4o-mini", 500, 200)

        summary = tracker.get_summary()

        assert "ingest" in summary.by_operation
        assert "search" in summary.by_operation

    def test_persistence(self, tracker):
        tracker.record_call("test", "gpt-4o-mini", 1000, 500)

        # Create new tracker with same path
        tracker2 = CostTracker(tracker.storage_path)

        assert len(tracker2.calls) == 1

    def test_clear(self, tracker):
        tracker.record_call("test", "gpt-4o-mini", 1000, 500)
        tracker.clear()

        assert len(tracker.calls) == 0


class TestFormatCostSummary:
    def test_formats_summary(self):
        summary = CostSummary(
            total_calls=10,
            total_input_tokens=50000,
            total_output_tokens=10000,
            total_cost_usd=0.05,
            by_operation={"ingest": 0.03, "search": 0.02},
        )

        formatted = format_cost_summary(summary)

        assert "Total calls: 10" in formatted
        assert "Total cost: $0.0500" in formatted
        assert "ingest" in formatted
