from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from shared_llm_core.evaluation import EvalCase, _check_output, _coerce_output, run_eval


def _case(*, severity: str = "high") -> EvalCase:
    return EvalCase(
        id="soc-brute-force",
        inputs={"events": ["synthetic event"]},
        expected={
            "required_fields": ["severity", "confidence", "title"],
            "severity": {
                "allowed": ["low", "medium", "high", "critical"],
                "baseline": severity,
                "max_drift": 0,
            },
            "confidence": {"min": 0.0, "max": 1.0},
        },
    )


def _fixture(root: Path, response: dict[str, Any]) -> None:
    root.mkdir(parents=True)
    (root / "soc-brute-force.json").write_text(json.dumps(response), encoding="utf-8")


def test_replay_mode_is_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = tmp_path / "fixtures"
    _fixture(fixtures, {"severity": "high", "confidence": 0.9, "title": "Detected"})
    monkeypatch.setenv("SHARED_LLM_EVAL_MODE", "replay")
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(fixtures))

    assert run_eval([_case()]) == run_eval([_case()])
    assert run_eval([_case()])[0].passed


def test_replay_mode_makes_no_network_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = tmp_path / "fixtures"
    _fixture(fixtures, {"severity": "high", "confidence": 0.8, "title": "Detected"})
    monkeypatch.setenv("SHARED_LLM_EVAL_MODE", "replay")
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(fixtures))

    def network_call(_: object) -> object:
        raise AssertionError("replay called the live invocation")

    assert run_eval([_case()], network_call)[0].passed


def test_severity_drift_is_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = tmp_path / "fixtures"
    _fixture(fixtures, {"severity": "low", "confidence": 0.8, "title": "Detected"})
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(fixtures))

    result = run_eval([_case()])[0]

    assert not result.passed
    assert any("severity drifted 2 level" in item for item in result.deviations)


def test_out_of_range_confidence_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = tmp_path / "fixtures"
    _fixture(fixtures, {"severity": "high", "confidence": 1.2, "title": "Detected"})
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(fixtures))

    result = run_eval([_case()])[0]

    assert not result.passed
    assert any("confidence" in item for item in result.deviations)


def test_missing_required_field_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixtures = tmp_path / "fixtures"
    _fixture(fixtures, {"severity": "high", "confidence": 0.8})
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(fixtures))

    result = run_eval([_case()])[0]

    assert not result.passed
    assert "missing required field: title" in result.deviations


def test_live_mode_uses_router(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_LLM_EVAL_MODE", "live")
    seen: list[object] = []

    class Router:
        def invoke(self, inputs: object) -> dict[str, object]:
            seen.append(inputs)
            return {"severity": "high", "confidence": 0.8, "title": "Detected"}

    router = Router()
    result = run_eval([_case()], router.invoke)[0]

    assert result.passed
    assert seen == [_case().inputs]


def test_eval_rejects_unknown_mode_and_missing_live_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_LLM_EVAL_MODE", "staging")
    with pytest.raises(ValueError, match="must be 'replay' or 'live'"):
        run_eval([])

    monkeypatch.setenv("SHARED_LLM_EVAL_MODE", "live")
    with pytest.raises(ValueError, match="requires an invoke callback"):
        run_eval([])


def test_eval_coerces_json_strings_models_and_chat_envelopes() -> None:
    class Output(BaseModel):
        severity: str

    assert _coerce_output(Output(severity="high")) == {"severity": "high"}
    assert _coerce_output('{"severity": "high"}') == {"severity": "high"}
    assert _coerce_output(
        {
            "choices": [
                {"message": {"content": '{"severity": "high"}'}}
            ]
        }
    ) == {"severity": "high"}
    assert _coerce_output({"choices": []}) == {"choices": []}

    with pytest.raises(TypeError, match="assistant content"):
        _coerce_output({"choices": [{"message": {"content": "[]"}}]})
    with pytest.raises(TypeError, match="JSON object"):
        _coerce_output(["not", "an", "object"])


def test_eval_reports_fixture_and_case_id_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHARED_LLM_EVAL_FIXTURES", str(tmp_path))
    result = run_eval([EvalCase(id="../escape", inputs={}, expected={})])[0]
    assert not result.passed
    assert "filename-safe" in result.deviations[0]

    missing = run_eval([EvalCase(id="missing", inputs={}, expected={})])[0]
    assert not missing.passed
    assert "evaluation failed" in missing.deviations[0]


def test_eval_reports_malformed_expectation_rules() -> None:
    deviations = _check_output(
        {"severity": "high", "confidence": 0.5},
        {
            "required_fields": "severity",
            "severity": "high",
            "confidence": "0..1",
        },
    )
    assert "required_fields" in deviations[0]
    assert "expected.severity must be an object" in deviations
    assert "expected.confidence must be an object" in deviations


def test_eval_reports_severity_rule_edge_cases() -> None:
    assert "field must be a field name" in _check_output(
        {"severity": "high"}, {"severity": {"field": 1}}
    )[0]
    assert _check_output({}, {"severity": {"baseline": "high"}}) == []
    assert "allowed must be a list of strings" in _check_output(
        {"severity": "high"}, {"severity": {"allowed": ["high", 1]}}
    )[0]
    assert "not in allowed set" in _check_output(
        {"severity": "critical"}, {"severity": {"allowed": ["high"]}}
    )[0]
    assert any(
        "canonical" in item
        for item in _check_output(
            {"severity": "urgent"}, {"severity": {"baseline": "unknown"}}
        )
    )
    assert "max_drift" in _check_output(
        {"severity": "high"}, {"severity": {"baseline": "high", "max_drift": True}}
    )[0]


def test_eval_reports_confidence_rule_edge_cases() -> None:
    assert "field must be a field name" in _check_output(
        {"confidence": 0.5}, {"confidence": {"field": None}}
    )[0]
    assert _check_output({}, {"confidence": {"min": 0, "max": 1}}) == []
