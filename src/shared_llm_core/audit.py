"""Audit log for every LLM call.

Three backends:
- "jsonl": append to a file (default; safe, append-only)
- "stdout": print to stdout (for local dev / k8s log shipping)
- "noop": discard (for benchmarks)

The audit record is what lets the whole agent suite pass compliance reviews:
every claim can be traced back to the exact prompt + response + model + cost.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from shared_llm_core.client import ChatRequest, ChatResponse
from shared_llm_core.config import AuditConfig

Backend = Literal["jsonl", "stdout", "noop"]


@dataclass
class AuditRecord:
    ts: str
    request_id: str
    provider: str
    model: str
    prompt_hash: str
    prompt_chars: int
    response_hash: str
    response_chars: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    prompt_excerpt: str | None = None
    response_excerpt: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class AuditLog:
    """Append-only audit sink."""

    def __init__(self, cfg: AuditConfig) -> None:
        self.cfg = cfg
        if cfg.backend == "jsonl":
            self._path = Path(cfg.path)
            # Only create the file's parent. If the path is a bare filename or
            # points inside a not-yet-existing directory we trust, make sure the
            # parent exists. We do NOT touch the file itself — the first write
            # appends and creates it.
            self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        *,
        request: ChatRequest,
        response: ChatResponse,
        provider: str,
        latency_ms: int,
    ) -> AuditRecord:
        prompt_text = "\n".join(m.content for m in request.messages)
        response_text = "\n".join(c.message.content for c in response.choices)

        rec = AuditRecord(
            ts=datetime.now(UTC).isoformat(),
            request_id=request.request_id,
            provider=provider,
            model=response.model,
            prompt_hash=hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            prompt_chars=len(prompt_text),
            response_hash=hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
            response_chars=len(response_text),
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            latency_ms=latency_ms,
            prompt_excerpt=prompt_text[:512] if self.cfg.include_prompt else None,
            response_excerpt=response_text[:512] if self.cfg.include_response else None,
            extra={"request_model": request.model},
        )

        backend: Backend = self.cfg.backend  # type: ignore[assignment]
        if backend == "jsonl":
            with self._path.open("a", encoding="utf-8") as f:
                f.write(rec.to_json() + "\n")
        elif backend == "stdout":
            sys.stdout.write(rec.to_json() + "\n")
            sys.stdout.flush()
        # "noop" intentionally does nothing
        return rec