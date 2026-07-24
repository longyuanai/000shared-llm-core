"""Tests for the audit log backends."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from shared_llm_core.audit import AuditLog
from shared_llm_core.client import ChatChoice, ChatMessage, ChatRequest, ChatResponse, ChatUsage
from shared_llm_core.config import AuditConfig


def _sample_response() -> ChatResponse:
    return ChatResponse(
        id="r1",
        model="m",
        created=0,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content="ok"),
                finish_reason="stop",
            )
        ],
        usage=ChatUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5),
    )


def test_jsonl_backend_writes_records(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(AuditConfig(backend="jsonl", path=str(path)))
    audit.record(
        request=ChatRequest(messages=[ChatMessage(role="user", content="hi")]),
        response=_sample_response(),
        provider="local",
        latency_ms=42,
    )
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["provider"] == "local"
    assert rec["latency_ms"] == 42
    assert rec["total_tokens"] == 5
    assert rec["prompt_excerpt"] == "hi"
    assert "prompt_hash" in rec and len(rec["prompt_hash"]) == 64


def test_noop_backend_writes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(AuditConfig(backend="noop", path=str(path)))
    audit.record(
        request=ChatRequest(messages=[ChatMessage(role="user", content="hi")]),
        response=_sample_response(),
        provider="local",
        latency_ms=1,
    )
    assert not path.exists()


def test_stdout_backend_prints(monkeypatch: pytest.MonkeyPatch) -> None:
    buf = io.StringIO()
    monkeypatch.setattr("sys.stdout", buf)
    audit = AuditLog(AuditConfig(backend="stdout", path="ignored"))
    audit.record(
        request=ChatRequest(messages=[ChatMessage(role="user", content="hi")]),
        response=_sample_response(),
        provider="local",
        latency_ms=1,
    )
    out = buf.getvalue().strip()
    assert json.loads(out)["provider"] == "local"


def test_excerpt_truncation(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    audit = AuditLog(
        AuditConfig(
            backend="jsonl",
            path=str(path),
            include_prompt=True,
            include_response=True,
        )
    )
    long = "x" * 5000
    audit.record(
        request=ChatRequest(messages=[ChatMessage(role="user", content=long)]),
        response=_sample_response(),
        provider="local",
        latency_ms=1,
    )
    rec = json.loads(path.read_text("utf-8").strip())
    assert rec["prompt_chars"] == 5000
    assert len(rec["prompt_excerpt"]) == 512