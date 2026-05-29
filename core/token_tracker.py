"""Token usage tracker with JSONL persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.time_utils import utc_now


@dataclass
class TokenRecord:
    """A single token usage record."""

    timestamp: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TokenTracker:
    """Track and persist LLM token usage in JSONL format."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._records: list[TokenRecord] = []
        self._load()

    def record(
        self,
        provider: str,
        model: str,
        *,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Append a new token usage record."""
        rec = TokenRecord(
            timestamp=utc_now(),
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        self._records.append(rec)
        self._append_to_file(rec)

    def summary(self) -> dict[str, int]:
        """Return aggregated totals."""
        total_prompt = sum(r.prompt_tokens for r in self._records)
        total_completion = sum(r.completion_tokens for r in self._records)
        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
            "request_count": len(self._records),
        }

    def summary_by_provider(self) -> dict[str, dict[str, int]]:
        """Return usage grouped by provider."""
        groups: dict[str, list[TokenRecord]] = {}
        for r in self._records:
            groups.setdefault(r.provider, []).append(r)
        return {
            provider: {
                "total_prompt_tokens": sum(rec.prompt_tokens for rec in recs),
                "total_completion_tokens": sum(rec.completion_tokens for rec in recs),
                "total_tokens": sum(rec.total_tokens for rec in recs),
                "request_count": len(recs),
            }
            for provider, recs in groups.items()
        }

    def summary_by_model(self) -> dict[str, dict[str, int]]:
        """Return usage grouped by model."""
        groups: dict[str, list[TokenRecord]] = {}
        for r in self._records:
            groups.setdefault(r.model, []).append(r)
        return {
            model: {
                "total_prompt_tokens": sum(rec.prompt_tokens for rec in recs),
                "total_completion_tokens": sum(rec.completion_tokens for rec in recs),
                "total_tokens": sum(rec.total_tokens for rec in recs),
                "request_count": len(recs),
            }
            for model, recs in groups.items()
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Read existing records from the JSONL file."""
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            self._records.append(TokenRecord(**data))

    def _append_to_file(self, record: TokenRecord) -> None:
        """Append a single record to the JSONL file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
