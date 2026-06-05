"""Tests for core.token_tracker."""

from __future__ import annotations

from pathlib import Path

from core.token_tracker import TokenTracker


class TestTokenTracker:
    def test_token_tracker_records_usage(self, tmp_path: Path) -> None:
        """Record two entries and verify summary totals."""
        tracker = TokenTracker(tmp_path / "usage.jsonl")
        tracker.record("openai", "gpt-4o", prompt_tokens=100, completion_tokens=50)
        tracker.record("openai", "gpt-4o", prompt_tokens=200, completion_tokens=80)

        s = tracker.summary()
        assert s["total_prompt_tokens"] == 300
        assert s["total_completion_tokens"] == 130
        assert s["total_tokens"] == 430
        assert s["request_count"] == 2

    def test_token_tracker_persists_across_instances(self, tmp_path: Path) -> None:
        """Records survive across separate tracker instances."""
        path = tmp_path / "usage.jsonl"
        t1 = TokenTracker(path)
        t1.record("anthropic", "claude-3", prompt_tokens=120, completion_tokens=60)

        t2 = TokenTracker(path)
        s = t2.summary()
        assert s["total_prompt_tokens"] == 120
        assert s["total_completion_tokens"] == 60
        assert s["request_count"] == 1

    def test_token_tracker_groups_by_provider(self, tmp_path: Path) -> None:
        """Records from different providers are correctly grouped."""
        tracker = TokenTracker(tmp_path / "usage.jsonl")
        tracker.record("openai", "gpt-4o", prompt_tokens=100, completion_tokens=50)
        tracker.record("anthropic", "claude-3", prompt_tokens=200, completion_tokens=80)

        by_prov = tracker.summary_by_provider()
        assert set(by_prov.keys()) == {"openai", "anthropic"}
        assert by_prov["openai"]["total_tokens"] == 150
        assert by_prov["anthropic"]["total_tokens"] == 280

    def test_token_tracker_empty_state(self, tmp_path: Path) -> None:
        """A fresh tracker with no records returns zeros."""
        tracker = TokenTracker(tmp_path / "usage.jsonl")
        s = tracker.summary()
        assert s["total_prompt_tokens"] == 0
        assert s["total_completion_tokens"] == 0
        assert s["total_tokens"] == 0
        assert s["request_count"] == 0

    def test_token_tracker_summary_by_model(self, tmp_path: Path) -> None:
        """Records for different models are correctly grouped."""
        tracker = TokenTracker(tmp_path / "usage.jsonl")
        tracker.record("openai", "gpt-4o", prompt_tokens=100, completion_tokens=50)
        tracker.record(
            "openai", "gpt-3.5-turbo", prompt_tokens=200, completion_tokens=80
        )

        by_model = tracker.summary_by_model()
        assert set(by_model.keys()) == {"gpt-4o", "gpt-3.5-turbo"}
        assert by_model["gpt-4o"]["total_tokens"] == 150
        assert by_model["gpt-4o"]["request_count"] == 1
        assert by_model["gpt-3.5-turbo"]["total_tokens"] == 280
        assert by_model["gpt-3.5-turbo"]["request_count"] == 1
