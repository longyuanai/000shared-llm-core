from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from shared_llm_core.evaluation import EvalCase, run_eval


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
