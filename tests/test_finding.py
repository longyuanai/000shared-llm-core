"""v0.5 §9 Finding — test suite.

10 test functions covering enums, required fields, confidence
validation, UUID auto-generation, to_dict ordering, from_dict
robustness, roundtrip, immutability.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from shared_llm_core.finding import Finding, FindingSeverity, FindingSource


def _make_finding(**overrides):
    """Convenience: minimal valid Finding, fields overridable."""
    base = dict(
        id="",
        source=FindingSource.SOC,
        severity=FindingSeverity.MEDIUM,
        confidence=0.5,
        title="t",
    )
    base.update(overrides)
    return Finding(**base)


def test_finding_source_enum_values():
    assert FindingSource.SOC.value == "001"
    assert FindingSource.VULN.value == "002"
    assert FindingSource.LAB.value == "003"
    assert FindingSource.CODE.value == "004"
    assert FindingSource.REVERSE.value == "005"
    assert FindingSource.FIRMWARE.value == "006"
    assert FindingSource.EXTERNAL.value == "external"


def test_finding_severity_enum_values():
    order = [s.value for s in FindingSeverity]
    assert order == ["info", "low", "medium", "high", "critical"]


def test_finding_required_fields():
    f = _make_finding()
    assert f.title == "t"
    assert f.source == FindingSource.SOC
    assert f.severity == FindingSeverity.MEDIUM
    assert f.confidence == 0.5
    assert f.host is None
    assert f.cve is None
    assert f.ts is None
    assert f.evidence == ()
    assert f.related == ()
    assert f.tags == frozenset()


def test_finding_confidence_too_low_raises():
    with pytest.raises(ValueError):
        _make_finding(confidence=-0.0001)


def test_finding_confidence_too_high_raises():
    with pytest.raises(ValueError):
        _make_finding(confidence=1.0001)


def test_finding_confidence_boundaries_accepted():
    f0 = _make_finding(confidence=0.0)
    f1 = _make_finding(confidence=1.0)
    assert f0.confidence == 0.0
    assert f1.confidence == 1.0


def test_finding_uuid_auto_generated_when_empty():
    f1 = _make_finding()
    f2 = _make_finding()
    assert f1.id != f2.id
    assert len(f1.id) == 36  # UUID4 canonical


def test_finding_explicit_id_preserved():
    f = _make_finding(id="my-custom-id")
    assert f.id == "my-custom-id"


def test_finding_to_dict_stable_field_order():
    f = _make_finding()
    d = f.to_dict()
    expected_first_keys = [
        "id", "source", "severity", "confidence", "title",
        "description", "host", "cve", "ts", "evidence",
        "related", "tags", "metadata",
    ]
    assert list(d.keys()) == expected_first_keys


def test_finding_from_dict_ignores_unknown_fields():
    payload = _make_finding().to_dict()
    payload["__future_field__"] = "ignored"
    payload["extra_metadata"] = {"should": "be dropped"}
    f = Finding.from_dict(payload)
    assert not hasattr(f, "__future_field__")
    assert f.title == "t"


def test_finding_roundtrip_via_dict():
    original = _make_finding(
        title="rce in openssh",
        description="command injection via username",
        host="10.0.0.1",
        cve="CVE-2024-1234",
        ts=datetime(2024, 6, 1, 12, 30, tzinfo=timezone.utc),
        evidence=("log line A", "log line B"),
        related=("other-finding-id",),
        tags=frozenset({"rce", "openssh"}),
        metadata={"scan_id": "abc"},
    )
    restored = Finding.from_dict(original.to_dict())
    assert restored.title == original.title
    assert restored.source == original.source
    assert restored.severity == original.severity
    assert restored.confidence == original.confidence
    assert restored.host == original.host
    assert restored.cve == original.cve
    assert restored.ts == original.ts
    assert restored.evidence == original.evidence
    assert restored.related == original.related
    assert restored.tags == original.tags
    assert restored.metadata == original.metadata


def test_finding_immutable():
    from dataclasses import FrozenInstanceError

    f = _make_finding()
    with pytest.raises(FrozenInstanceError):
        f.title = "mutated"  # type: ignore[misc]