"""Optional OpenTelemetry tracing with a silent no-op fallback."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from importlib import import_module
from typing import Any

_ENABLED_ENV = "SHARED_LLM_OTEL_ENABLED"
_TRACER_NAME = "shared_llm_core"
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class _NoOpSpan:
    def set_attribute(self, _key: str, _value: object) -> None:
        return None

    def record_exception(self, _error: BaseException) -> None:
        return None


class _NoOpSpanManager:
    def __enter__(self) -> _NoOpSpan:
        return _NOOP_SPAN

    def __exit__(
        self,
        _error_type: type[BaseException] | None,
        _error: BaseException | None,
        _traceback: object,
    ) -> bool:
        return False


class _NoOpTracer:
    def start_as_current_span(self, _name: str, **_kwargs: object) -> _NoOpSpanManager:
        return _NoOpSpanManager()


_NOOP_SPAN = _NoOpSpan()
_NOOP_TRACER = _NoOpTracer()


class _SafeSpan:
    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def set_attribute(self, key: str, value: object) -> None:
        with suppress(Exception):
            self._delegate.set_attribute(key, value)


def _enabled() -> bool:
    return os.getenv(_ENABLED_ENV, "").strip().lower() in _TRUE_VALUES


def get_tracer() -> Any:
    """Return the configured OTel tracer, or a silent no-op tracer."""

    if not _enabled():
        return _NOOP_TRACER
    try:
        trace = import_module("opentelemetry.trace")
        return trace.get_tracer(_TRACER_NAME)
    except Exception:
        return _NOOP_TRACER


def _parent_context() -> object | None:
    traceparent = os.getenv("traceparent")  # noqa: SIM112 - W3C carrier key
    if not _enabled() or not traceparent:
        return None
    try:
        propagate = import_module("opentelemetry.propagate")
        return propagate.extract({"traceparent": traceparent})
    except Exception:
        return None


@contextmanager
def span(
    name: str,
    *,
    attributes: Mapping[str, object] | None = None,
) -> Iterator[Any]:
    """Create a span without allowing telemetry failures to affect callers."""

    tracer = get_tracer()
    kwargs: dict[str, object] = {
        "record_exception": False,
        "set_status_on_exception": False,
    }
    parent_context = _parent_context()
    if parent_context is not None:
        kwargs["context"] = parent_context
    try:
        manager = tracer.start_as_current_span(name, **kwargs)
        active_span = manager.__enter__()
    except Exception:
        manager = _NoOpSpanManager()
        active_span = manager.__enter__()

    safe_span = _SafeSpan(active_span)
    for key, value in (attributes or {}).items():
        safe_span.set_attribute(key, value)

    try:
        yield safe_span
    except BaseException as error:
        with suppress(Exception):
            active_span.record_exception(error)
        with suppress(Exception):
            manager.__exit__(type(error), error, error.__traceback__)
        raise
    else:
        with suppress(Exception):
            manager.__exit__(None, None, None)


def trace_context_environment() -> dict[str, str]:
    """Return W3C trace context suitable for a child-process environment."""

    if not _enabled():
        return {}
    carrier: dict[str, str] = {}
    try:
        propagate = import_module("opentelemetry.propagate")
        propagate.inject(carrier)
    except Exception:
        return {}
    traceparent = carrier.get("traceparent")
    return {"traceparent": traceparent} if traceparent else {}


def current_trace_id() -> str | None:
    """Return the active trace id as 32 lowercase hex digits when available."""

    if not _enabled():
        return None
    try:
        trace = import_module("opentelemetry.trace")
        context = trace.get_current_span().get_span_context()
        if not context.is_valid:
            return None
        return f"{context.trace_id:032x}"
    except Exception:
        return None


__all__ = ["current_trace_id", "get_tracer", "span", "trace_context_environment"]
