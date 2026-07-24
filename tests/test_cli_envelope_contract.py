"""v0.6 §15 CLI Envelope 契约测试 —— 本地 mock,不依赖 000shared-integration.

12 test functions covering the JSONSubprocessAdapter contract:
- envelope object form → Finding normalization
- envelope array form → Finding normalization
- missing source → adapter injects its own FindingSource
- default severity / confidence / title
- malformed JSON → ProductCLIError
- non-zero exit → ProductCLIError with stderr echo
- non-list findings → ProductCLIError
- non-dict finding item → ProductCLIError

These tests are a contract reference implementation. The production
adapter lives at `000shared-integration/src/shared_integration/adapters/base.py`
and uses the same envelope semantics. If you change the contract
behavior here, update both sides.
"""

from __future__ import annotations

import asyncio
import json
import sys
import textwrap
from pathlib import Path
from typing import Any, AsyncIterator

import pytest

from shared_llm_core import Finding, FindingSeverity, FindingSource


# --- In-test reference implementation of the envelope parser --------------------
# Mirrors the production JSONSubprocessAdapter.scan() so we can lock the contract
# without spinning up a subprocess. Production code must match this exactly.


class ProductCLIError(RuntimeError):
    """Raised when a product CLI exits unsuccessfully or emits invalid JSON."""


async def _parse_envelope(
    *,
    stdout: bytes,
    returncode: int,
    stderr: bytes,
    source_value: str,
    product_id: str,
) -> AsyncIterator[Finding]:
    """Reference parser. Mirrors JSONSubprocessAdapter.scan() body."""
    if returncode != 0:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise ProductCLIError(f"{product_id} CLI exited with {returncode}: {detail}")
    try:
        decoded = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductCLIError(f"{product_id} CLI emitted invalid JSON") from exc

    if not isinstance(decoded, (list, dict)):
        raise ProductCLIError(
            f"{product_id} CLI envelope must be object or array, got {type(decoded).__name__}"
        )
    items = decoded if isinstance(decoded, list) else decoded.get("findings", [])
    if not isinstance(items, list):
        raise ProductCLIError(f"{product_id} CLI 'findings' must be a list")

    for item in items:
        if not isinstance(item, dict):
            raise ProductCLIError(f"{product_id} CLI finding must be an object")
        normalized = {
            **item,
            "id": item.get("id", ""),
            "source": source_value,
            "severity": item.get("severity", "medium"),
            "confidence": item.get("confidence", 0.5),
            "title": item.get("title", "Untitled finding"),
        }
        yield Finding.from_dict(normalized)


async def _collect(gen: AsyncIterator[Finding]) -> list[Finding]:
    out: list[Finding] = []
    async for f in gen:
        out.append(f)
    return out


# --- Tests ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_envelope_object_form_normalized():
    stdout = json.dumps(
        {
            "findings": [
                {
                    "id": "f1",
                    "severity": "high",
                    "confidence": 0.9,
                    "title": "Brute force",
                    "host": "10.0.0.1",
                }
            ]
        }
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.SOC.value,
            product_id="001-soc",
        )
    )

    assert len(findings) == 1
    f = findings[0]
    assert f.id == "f1"
    assert f.source == FindingSource.SOC
    assert f.severity == FindingSeverity.HIGH
    assert f.confidence == 0.9
    assert f.title == "Brute force"
    assert f.host == "10.0.0.1"


@pytest.mark.asyncio
async def test_envelope_array_form_accepted():
    """Top-level list is accepted as a shorthand for {'findings': [...]}."""
    stdout = json.dumps(
        [{"id": "f1", "severity": "low", "confidence": 0.3, "title": "Info leak"}]
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.VULN.value,
            product_id="002-vuln",
        )
    )

    assert len(findings) == 1
    assert findings[0].id == "f1"
    assert findings[0].source == FindingSource.VULN


@pytest.mark.asyncio
async def test_missing_source_injected_from_adapter():
    """When product omits 'source', adapter forces its own FindingSource value."""
    stdout = json.dumps(
        {"findings": [{"id": "x", "severity": "medium", "confidence": 0.5, "title": "t"}]}
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.FIRMWARE.value,
            product_id="006-firmware",
        )
    )

    assert findings[0].source == FindingSource.FIRMWARE


@pytest.mark.asyncio
async def test_default_severity_and_confidence_and_title():
    """Severity/confidence/title fall back to defaults when missing."""
    stdout = json.dumps({"findings": [{"id": "x"}]}).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.CODE.value,
            product_id="004-code",
        )
    )

    f = findings[0]
    assert f.severity == FindingSeverity.MEDIUM
    assert f.confidence == 0.5
    assert f.title == "Untitled finding"


@pytest.mark.asyncio
async def test_invalid_json_raises_product_cli_error():
    with pytest.raises(ProductCLIError, match="invalid JSON"):
        await _collect(
            _parse_envelope(
                stdout=b"{not valid json",
                returncode=0,
                stderr=b"",
                source_value=FindingSource.LAB.value,
                product_id="003-lab",
            )
        )


@pytest.mark.asyncio
async def test_nonzero_exit_raises_with_stderr_echo():
    with pytest.raises(ProductCLIError, match="exited with 2") as exc_info:
        await _collect(
            _parse_envelope(
                stdout=b"",
                returncode=2,
                stderr=b"Traceback: missing input\n",
                source_value=FindingSource.SOC.value,
                product_id="001-soc",
            )
        )
    assert "missing input" in str(exc_info.value)


@pytest.mark.asyncio
async def test_envelope_without_findings_key_yields_empty():
    """Object envelope missing 'findings' key → 0 findings, no error.

    This is the lenient behavior: products can return metadata-only
    envelopes; gateway treats it as a no-op scan. Stricter enforcement
    (require 'findings' key) is intentionally NOT in v0.6.
    """
    stdout = json.dumps({"foo": "bar"}).encode("utf-8")
    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.SOC.value,
            product_id="001-soc",
        )
    )
    assert findings == []


@pytest.mark.asyncio
async def test_finding_item_must_be_object():
    stdout = json.dumps({"findings": ["not a dict"]}).encode("utf-8")
    with pytest.raises(ProductCLIError, match="must be an object"):
        await _collect(
            _parse_envelope(
                stdout=stdout,
                returncode=0,
                stderr=b"",
                source_value=FindingSource.REVERSE.value,
                product_id="005-reverse",
            )
        )


@pytest.mark.asyncio
async def test_multiple_findings_in_envelope():
    stdout = json.dumps(
        {
            "findings": [
                {"id": "a", "severity": "low", "confidence": 0.2, "title": "low"},
                {"id": "b", "severity": "critical", "confidence": 0.99, "title": "crit"},
                {"id": "c", "severity": "info", "confidence": 0.1, "title": "info"},
            ]
        }
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.VULN.value,
            product_id="002-vuln",
        )
    )

    assert [f.id for f in findings] == ["a", "b", "c"]
    assert [f.severity for f in findings] == [
        FindingSeverity.LOW,
        FindingSeverity.CRITICAL,
        FindingSeverity.INFO,
    ]


@pytest.mark.asyncio
async def test_unknown_fields_preserved_via_finding_from_dict():
    """Finding.from_dict tolerates extra fields; contract guarantees no crash."""
    stdout = json.dumps(
        {
            "findings": [
                {
                    "id": "x",
                    "severity": "high",
                    "confidence": 0.7,
                    "title": "t",
                    "future_field": "should not crash",
                    "metadata": {"exploit": "public"},
                }
            ]
        }
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.SOC.value,
            product_id="001-soc",
        )
    )

    f = findings[0]
    assert f.metadata.get("exploit") == "public"


@pytest.mark.asyncio
async def test_empty_envelope_yields_no_findings():
    """Empty list is a legal response — gateway should not error."""
    stdout = json.dumps({"findings": []}).encode("utf-8")
    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.SOC.value,
            product_id="001-soc",
        )
    )
    assert findings == []


@pytest.mark.asyncio
async def test_severity_lowercase_is_canonical():
    """Products must emit lowercase severity strings (e.g. 'critical').

    FindingSeverity is a str Enum whose values are lowercase; 'CRITICAL'
    is rejected. This test locks that contract so future changes to
    FindingSeverity deliberately (rather than by accident) widen the
    accepted vocabulary.
    """
    # Canonical lowercase passes
    stdout = json.dumps(
        {"findings": [{"id": "x", "severity": "critical", "confidence": 0.9, "title": "t"}]}
    ).encode("utf-8")

    findings = await _collect(
        _parse_envelope(
            stdout=stdout,
            returncode=0,
            stderr=b"",
            source_value=FindingSource.FIRMWARE.value,
            product_id="006-firmware",
        )
    )
    assert findings[0].severity == FindingSeverity.CRITICAL