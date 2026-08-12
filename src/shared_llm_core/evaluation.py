"""Deterministic field-level regression checks for LLM outputs.

Evaluation cases describe constraints rather than exact prose.  CI replays
recorded JSON responses; an operator can opt into live mode and inject the
same product-specific invocation used to record a fixture.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_SEVERITY_ORDER = ("info", "low", "medium", "high", "critical")


@dataclass(frozen=True)
class EvalCase:
    """One input and the field constraints its LLM output must satisfy."""

    id: str
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]


@dataclass(frozen=True)
class EvalResult:
    """The deviations found while evaluating one case."""

    case_id: str
    passed: bool
    deviations: tuple[str, ...]


Invoke = Callable[[Mapping[str, Any]], Any]


def run_eval(cases: Iterable[EvalCase], invoke: Invoke | None = None) -> list[EvalResult]:
    """Evaluate cases in replay (default) or explicitly selected live mode.

    Replay fixtures are loaded from ``evals/fixtures/<case_id>.json`` beneath
    the current working directory.  ``SHARED_LLM_EVAL_FIXTURES`` may point at
    another fixture directory, which is useful for an orchestrating suite.
    The invocation callback is deliberately ignored in replay mode.
    """

    mode = os.getenv("SHARED_LLM_EVAL_MODE", "replay").strip().lower()
    if mode not in {"replay", "live"}:
        raise ValueError("SHARED_LLM_EVAL_MODE must be 'replay' or 'live'")
    if mode == "live" and invoke is None:
        raise ValueError("live evaluation mode requires an invoke callback")

    fixture_root = Path(
        os.getenv("SHARED_LLM_EVAL_FIXTURES", str(Path("evals") / "fixtures"))
    )
    results: list[EvalResult] = []
    for case in cases:
        try:
            raw = _load_fixture(fixture_root, case.id) if mode == "replay" else invoke(case.inputs)  # type: ignore[misc]
            output = _coerce_output(raw)
            deviations = _check_output(output, case.expected)
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            deviations = [f"evaluation failed: {exc}"]
        results.append(
            EvalResult(
                case_id=case.id,
                passed=not deviations,
                deviations=tuple(deviations),
            )
        )
    return results


def _load_fixture(root: Path, case_id: str) -> Any:
    if not case_id or Path(case_id).name != case_id:
        raise ValueError("case id must be a non-empty filename-safe value")
    return json.loads((root / f"{case_id}.json").read_text(encoding="utf-8"))


def _coerce_output(raw: Any) -> Mapping[str, Any]:
    if isinstance(raw, BaseModel):
        raw = raw.model_dump()
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, Mapping):
        raise TypeError("evaluation output must be a JSON object")

    # Callers may pass a ChatResponse directly.  Extract its assistant JSON
    # without making product fixtures mimic provider-specific envelopes.
    choices = raw.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping) and isinstance(message.get("content"), str):
                decoded = json.loads(message["content"])
                if not isinstance(decoded, Mapping):
                    raise TypeError("assistant content must decode to a JSON object")
                return decoded
    return raw


def _check_output(output: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    deviations: list[str] = []
    required = expected.get("required_fields", ())
    if not isinstance(required, (list, tuple)) or not all(isinstance(v, str) for v in required):
        deviations.append("expected.required_fields must be a list of field names")
    else:
        for field in required:
            present, _ = _field_value(output, field)
            if not present:
                deviations.append(f"missing required field: {field}")

    severity_rule = expected.get("severity", {})
    if not isinstance(severity_rule, Mapping):
        deviations.append("expected.severity must be an object")
    else:
        _check_severity(output, severity_rule, deviations)

    confidence_rule = expected.get("confidence", {"min": 0.0, "max": 1.0})
    if not isinstance(confidence_rule, Mapping):
        deviations.append("expected.confidence must be an object")
    else:
        _check_confidence(output, confidence_rule, deviations)
    return deviations


def _field_value(output: Mapping[str, Any], dotted_name: str) -> tuple[bool, Any]:
    current: Any = output
    for part in dotted_name.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _check_severity(
    output: Mapping[str, Any], rule: Mapping[str, Any], deviations: list[str]
) -> None:
    field = rule.get("field", "severity")
    if not isinstance(field, str):
        deviations.append("expected.severity.field must be a field name")
        return
    present, severity = _field_value(output, field)
    if not present:
        return
    allowed = rule.get("allowed", _SEVERITY_ORDER)
    if not isinstance(allowed, (list, tuple)) or not all(isinstance(v, str) for v in allowed):
        deviations.append("expected.severity.allowed must be a list of strings")
        return
    if severity not in allowed:
        deviations.append(f"severity {severity!r} is not in allowed set {list(allowed)!r}")

    baseline = rule.get("baseline")
    max_drift = rule.get("max_drift", 0)
    if baseline is None:
        return
    if baseline not in _SEVERITY_ORDER or severity not in _SEVERITY_ORDER:
        deviations.append("severity drift requires canonical info/low/medium/high/critical values")
        return
    if not isinstance(max_drift, int) or isinstance(max_drift, bool) or max_drift < 0:
        deviations.append("expected.severity.max_drift must be a non-negative integer")
        return
    drift = abs(_SEVERITY_ORDER.index(severity) - _SEVERITY_ORDER.index(baseline))
    if drift > max_drift:
        deviations.append(
            f"severity drifted {drift} level(s): expected {baseline!r}, got {severity!r}, "
            f"maximum {max_drift}"
        )


def _check_confidence(
    output: Mapping[str, Any], rule: Mapping[str, Any], deviations: list[str]
) -> None:
    field = rule.get("field", "confidence")
    if not isinstance(field, str):
        deviations.append("expected.confidence.field must be a field name")
        return
    present, value = _field_value(output, field)
    if not present:
        return
    minimum = rule.get("min", 0.0)
    maximum = rule.get("max", 1.0)
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isinstance(minimum, (int, float))
        or not isinstance(maximum, (int, float))
        or not minimum <= value <= maximum
    ):
        deviations.append(
            f"confidence {value!r} is outside allowed range [{minimum!r}, {maximum!r}]"
        )
