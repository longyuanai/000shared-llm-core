from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from shared_llm_core.audit import AuditLog
from shared_llm_core.client import (
    ChatChoice,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatUsage,
)
from shared_llm_core.config import AuditConfig, CoreConfig, ProviderConfig
from shared_llm_core.router import LLMRouter, RouteRule, TaskTier


class RecordingSpan:
    def __init__(self, attributes: dict[str, object]) -> None:
        self.attributes = attributes

    def set_attribute(self, key: str, value: object) -> None:
        self.attributes[key] = value


class StubClient:
    def __init__(self, *, error: BaseException | None = None) -> None:
        self.provider = SimpleNamespace(name="local")
        self._error = error

    def chat(self, _request: ChatRequest) -> ChatResponse:
        if self._error is not None:
            raise self._error
        return ChatResponse(
            id="response-id",
            model="model-safe",
            created=0,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content="private response"),
                )
            ],
            usage=ChatUsage(prompt_tokens=3, completion_tokens=2, total_tokens=5),
        )

    def close(self) -> None:
        pass


def _router(*, audit: AuditLog | None = None) -> LLMRouter:
    config = CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local",
                base_url="http://local.invalid",
                api_key="credential-must-not-appear",
                default_model="model-safe",
            )
        },
        audit=AuditConfig(backend="noop"),
    )
    router = LLMRouter(
        config,
        [RouteRule(TaskTier.STANDARD, "local", "model-safe")],
        audit=audit,
    )
    router._clients["local"].close()
    router._clients["local"] = StubClient()  # type: ignore[assignment]
    return router


def _capture_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, RecordingSpan]]:
    captured: list[tuple[str, RecordingSpan]] = []

    @contextmanager
    def recording_span(
        name: str,
        *,
        attributes: dict[str, object] | None = None,
    ) -> Iterator[RecordingSpan]:
        active = RecordingSpan(dict(attributes or {}))
        captured.append((name, active))
        yield active

    monkeypatch.setattr("shared_llm_core.router.span", recording_span)
    return captured


def _request() -> ChatRequest:
    return ChatRequest(
        messages=[ChatMessage(role="user", content="private prompt")],
        extra={"credential": "must-not-appear"},
    )


def test_span_created_per_llm_call(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_spans(monkeypatch)
    router = _router()

    router.chat(TaskTier.STANDARD, _request())

    assert [name for name, _span in captured] == ["llm.call"]


def test_span_carries_model_and_tier(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_spans(monkeypatch)
    router = _router()

    router.chat(TaskTier.STANDARD, _request())

    attributes = captured[0][1].attributes
    assert attributes == {
        "llm.model": "model-safe",
        "llm.provider": "local",
        "llm.task_tier": "standard",
        "llm.prompt_tokens": 3,
        "llm.completion_tokens": 2,
        "llm.total_tokens": 5,
        "llm.latency_ms": pytest.approx(0, abs=1000),
        "llm.success": True,
    }


def test_span_never_contains_prompt_or_response(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_spans(monkeypatch)
    router = _router()

    router.chat(TaskTier.STANDARD, _request())

    serialized = json.dumps(captured[0][1].attributes, sort_keys=True)
    assert "private prompt" not in serialized
    assert "private response" not in serialized
    assert "credential-must-not-appear" not in serialized
    assert "must-not-appear" not in serialized
    assert "llm.prompt" not in captured[0][1].attributes
    assert "llm.response" not in captured[0][1].attributes


def test_audit_record_still_written_when_tracing_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SHARED_LLM_OTEL_ENABLED", raising=False)
    audit_path = tmp_path / "audit.jsonl"
    audit = AuditLog(AuditConfig(backend="jsonl", path=str(audit_path)))
    router = _router(audit=audit)

    router.chat(TaskTier.STANDARD, _request())

    record: dict[str, Any] = json.loads(audit_path.read_text(encoding="utf-8"))
    assert record["model"] == "model-safe"
    assert record["total_tokens"] == 5


def test_failed_llm_call_marks_span_unsuccessful(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _capture_spans(monkeypatch)
    router = _router()
    expected = RuntimeError("provider failure")
    router._clients["local"] = StubClient(error=expected)  # type: ignore[assignment]

    with pytest.raises(RuntimeError) as caught:
        router.chat(TaskTier.STANDARD, _request())

    assert caught.value is expected
    attributes = captured[0][1].attributes
    assert attributes["llm.success"] is False
    assert isinstance(attributes["llm.latency_ms"], int)
