from __future__ import annotations

from types import SimpleNamespace

import pytest

from shared_llm_core import telemetry


def test_noop_tracer_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SHARED_LLM_OTEL_ENABLED", raising=False)
    monkeypatch.setattr(
        telemetry,
        "import_module",
        lambda _name: pytest.fail("disabled tracing must not import OTel"),
    )

    assert telemetry.get_tracer() is telemetry._NOOP_TRACER


def test_noop_tracer_when_otel_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_LLM_OTEL_ENABLED", "true")
    monkeypatch.setattr(
        telemetry,
        "import_module",
        lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
    )

    assert telemetry.get_tracer() is telemetry._NOOP_TRACER


def test_span_context_manager_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenTracer:
        def start_as_current_span(self, _name: str, **_kwargs: object) -> object:
            raise RuntimeError("telemetry backend failed")

    monkeypatch.setattr(telemetry, "get_tracer", lambda: BrokenTracer())

    with telemetry.span("test", attributes={"key": "value"}):
        pass


def test_enabled_by_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = object()
    monkeypatch.setenv("SHARED_LLM_OTEL_ENABLED", "1")
    monkeypatch.setattr(
        telemetry,
        "import_module",
        lambda name: SimpleNamespace(get_tracer=lambda tracer_name: expected)
        if name == "opentelemetry.trace"
        else pytest.fail(f"unexpected import: {name}"),
    )

    assert telemetry.get_tracer() is expected


def test_span_records_exception_without_reraising_differently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[BaseException] = []

    class RecordingSpan:
        def set_attribute(self, _key: str, _value: object) -> None:
            pass

        def record_exception(self, error: BaseException) -> None:
            recorded.append(error)

    class RecordingManager:
        def __enter__(self) -> RecordingSpan:
            return RecordingSpan()

        def __exit__(self, *_args: object) -> bool:
            return False

    class RecordingTracer:
        def start_as_current_span(self, _name: str, **_kwargs: object) -> RecordingManager:
            return RecordingManager()

    monkeypatch.setattr(telemetry, "get_tracer", lambda: RecordingTracer())
    expected = ValueError("application error")

    with pytest.raises(ValueError) as caught, telemetry.span("test"):
        raise expected

    assert caught.value is expected
    assert recorded == [expected]


def test_trace_context_environment_uses_w3c_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SHARED_LLM_OTEL_ENABLED", "yes")

    def inject(carrier: dict[str, str]) -> None:
        carrier["traceparent"] = "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"

    monkeypatch.setattr(
        telemetry,
        "import_module",
        lambda _name: SimpleNamespace(inject=inject),
    )

    assert telemetry.trace_context_environment() == {
        "traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    }


def test_span_extracts_traceparent_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class Manager:
        def __enter__(self) -> telemetry._NoOpSpan:
            return telemetry._NOOP_SPAN

        def __exit__(self, *_args: object) -> bool:
            return False

    class Tracer:
        def start_as_current_span(self, _name: str, **kwargs: object) -> Manager:
            captured.update(kwargs)
            return Manager()

    parent = object()
    monkeypatch.setenv("SHARED_LLM_OTEL_ENABLED", "on")
    monkeypatch.setenv(
        "traceparent",
        "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01",
    )
    monkeypatch.setattr(telemetry, "get_tracer", lambda: Tracer())
    monkeypatch.setattr(
        telemetry,
        "import_module",
        lambda _name: SimpleNamespace(extract=lambda _carrier: parent),
    )

    with telemetry.span("child"):
        pass

    assert captured["context"] is parent
