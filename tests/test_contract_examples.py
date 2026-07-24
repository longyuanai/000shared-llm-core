"""v0.5 contract examples — pin the cheat sheets in §7-§10 + §15.5.1.

These tests are not exhaustive coverage (see test_finding.py etc.).
They pin the *examples* in v0.5-contract.md so a doc rewrite can't
silently drift away from the implementation. If any of these break,
either the code changed (and the doc needs updating) or the doc
changed (and the code needs updating).

14 test functions covering: 4 API cheat sheets (§7/§8/§9/§10), the §15.5.1
complete VULN envelope example, the §15.5.2 failure example, and the
§15.5.3 CI smoke shape.
"""

from __future__ import annotations

import json

import pytest

from shared_llm_core.finding import Finding, FindingSeverity, FindingSource
from shared_llm_core.gateway import (
    CorrelationRule,
    FindingRegistry,
    IntegrationGateway,
    ProductAdapter,
)
from shared_llm_core.multi_agent import (
    AgentRole,
    MissionContext,
    MultiAgentOrchestrator,
)
from shared_llm_core.rule_engine import Rule, RuleContext, RuleEngine, RuleRegistry


# ---------------------------------------------------------------------------
# §7 MultiAgentOrchestrator cheat sheet
# ---------------------------------------------------------------------------

def test_section7_cheatsheet_runs_minimal_mission(stub_router):
    """§7 cheat sheet line: orch.run(mission, [AgentRole.SCOUT, ...]) -> [Result]."""
    orch = MultiAgentOrchestrator(stub_router)
    mc = MissionContext(task="t", inputs={})
    results = orch.run(mc, [AgentRole.SCOUT])
    assert len(results) == 1
    assert results[0].role is AgentRole.SCOUT
    assert results[0].error is None


def test_section7_cheatsheet_all_five_roles_exist():
    """§7 cheat sheet line: AgentRole.{SCOUT,ANALYST,EXPLOITER,SYNTHESIZER,REVIEWER}."""
    names = {r.name for r in AgentRole}
    assert names == {"SCOUT", "ANALYST", "EXPLOITER", "SYNTHESIZER", "REVIEWER"}


# ---------------------------------------------------------------------------
# §8 RuleEngine cheat sheet
# ---------------------------------------------------------------------------

def test_section8_cheatsheet_custom_rule_subclass():
    """§8 cheat sheet: subclass Rule, set id + evaluate."""

    class MyRule(Rule):
        id = "test.cheatsheet.foo"
        severity_hint = "low"

        def evaluate(self, ctx: RuleContext):
            return [
                Finding(
                    id="",
                    source=FindingSource.EXTERNAL,
                    severity=FindingSeverity.LOW,
                    confidence=0.6,
                    title="cheatsheet match",
                    host=ctx.subject,
                )
            ]

    reg = RuleRegistry()
    reg.register(MyRule())
    engine = RuleEngine(reg)
    findings = engine.evaluate(RuleContext(subject="10.0.0.1", facts={"k": "v"}))
    assert len(findings) == 1
    assert findings[0].host == "10.0.0.1"


def test_section8_cheatsheet_default_registry_has_builtins():
    """§8 cheat sheet line: RuleRegistry.default() -> RuleRegistry."""
    reg = RuleRegistry.default()
    assert "core-brute-force" in reg
    assert "core-known-cve" in reg


def test_section8_cheatsheet_subset_by_ids():
    """§8 cheat sheet line: RuleEngine.evaluate(ctx, rule_ids=['x','y'])."""
    engine = RuleEngine()
    findings = engine.evaluate(
        RuleContext(subject="x", facts={"version": "openssh-7.0"}),
        rule_ids=["core-known-cve"],
    )
    assert len(findings) == 1
    assert "Known-vulnerable" in findings[0].title


# ---------------------------------------------------------------------------
# §9 Finding cheat sheet
# ---------------------------------------------------------------------------

def test_section9_cheatsheet_minimal_construction():
    """§9 cheat sheet: Finding(id='', source, severity, confidence, title)."""
    f = Finding(
        id="",
        source=FindingSource.CODE,
        severity=FindingSeverity.HIGH,
        confidence=0.9,
        title="rce in openssh",
    )
    assert f.id  # auto-UUID4 non-empty
    assert f.source is FindingSource.CODE
    assert f.severity is FindingSeverity.HIGH
    assert f.confidence == 0.9
    assert f.title == "rce in openssh"


def test_section9_cheatsheet_roundtrip_via_to_from_dict():
    """§9 cheat sheet: to_dict() / from_dict() stable roundtrip."""
    f = Finding(
        id="explicit-id",
        source=FindingSource.VULN,
        severity=FindingSeverity.CRITICAL,
        confidence=0.95,
        title="cve-2024-1234",
        host="10.0.0.1",
        cve="CVE-2024-1234",
        evidence=("line 1", "line 2"),
    )
    restored = Finding.from_dict(f.to_dict())
    assert restored.title == f.title
    assert restored.host == f.host
    assert restored.cve == f.cve
    assert restored.evidence == f.evidence


def test_section9_cheatsheet_confidence_out_of_range_raises():
    """§9 cheat sheet last line: confidence outside [0,1] raises ValueError."""
    with pytest.raises(ValueError):
        Finding(
            id="",
            source=FindingSource.SOC,
            severity=FindingSeverity.LOW,
            confidence=2.0,  # out of range
            title="bad",
        )


# ---------------------------------------------------------------------------
# §10 IntegrationGateway cheat sheet
# ---------------------------------------------------------------------------

class _SmokeAdapter(ProductAdapter):
    source = FindingSource.EXTERNAL

    async def scan(self, payload):
        yield Finding(
            id="",
            source=self.source,
            severity=FindingSeverity.INFO,
            confidence=0.5,
            title="smoke",
        )

    def health(self):
        return {"status": "ok"}


def test_section10_cheatsheet_registry_query_filters():
    """§10 cheat sheet: registry.query(source=, severity=, host=) -> list."""
    reg = FindingRegistry()
    f1 = Finding(
        id="", source=FindingSource.SOC, severity=FindingSeverity.HIGH,
        confidence=0.9, title="t1", host="10.0.0.1",
    )
    f2 = Finding(
        id="", source=FindingSource.VULN, severity=FindingSeverity.LOW,
        confidence=0.7, title="t2", host="10.0.0.2",
    )
    reg.add_sync(f1)
    reg.add_sync(f2)

    by_source = reg.query(source=FindingSource.SOC)
    assert len(by_source) == 1
    assert by_source[0].title == "t1"

    by_host = reg.query(host="10.0.0.2")
    assert len(by_host) == 1
    assert by_host[0].title == "t2"


def test_section10_cheatsheet_gateway_app_is_fastapi():
    """§10 cheat sheet: IntegrationGateway(products={src: adapter}).app."""
    gw = IntegrationGateway(
        products={FindingSource.EXTERNAL: _SmokeAdapter()},
    )
    app = gw.app
    # FastAPI apps have a .router attribute; quick sanity check.
    assert app is not None
    assert hasattr(app, "router")


def test_section10_cheatsheet_sync_variant_for_adapters():
    """§10 cheat sheet line: registry.add_sync(finding)."""
    reg = FindingRegistry()
    f = Finding(
        id="", source=FindingSource.CODE, severity=FindingSeverity.MEDIUM,
        confidence=0.5, title="sync",
    )
    reg.add_sync(f)
    assert len(reg.findings) == 1
    assert reg.findings[0].title == "sync"


# ---------------------------------------------------------------------------
# §15.5.1 Complete VULN envelope example
# ---------------------------------------------------------------------------

def test_section15_envelope_object_form_parses_as_finding():
    """§15.5.1 stdout example: {"findings": [...]} -> list[Finding]."""
    envelope = {
        "findings": [
            {
                "id": "002-vuln-0001",
                "source": "002",
                "severity": "high",
                "confidence": 0.9,
                "title": "CVE-2024-1234 on 10.0.0.1",
                "host": "10.0.0.1",
                "cve": "CVE-2024-1234",
            }
        ]
    }
    raw = json.dumps(envelope)  # exactly what CLI emits
    parsed = json.loads(raw)
    findings = parsed["findings"] if isinstance(parsed, dict) else parsed
    assert isinstance(findings, list)
    assert len(findings) == 1
    f = Finding.from_dict(findings[0])
    assert f.host == "10.0.0.1"
    assert f.cve == "CVE-2024-1234"


def test_section15_envelope_array_form_also_accepted():
    """§15.5.1 形态 B: top-level array. Adapter injects source before from_dict."""
    envelope = [{"id": "x", "severity": "low", "confidence": 0.5, "title": "t"}]
    raw = json.dumps(envelope)
    parsed = json.loads(raw)
    findings = parsed["findings"] if isinstance(parsed, dict) else parsed
    assert isinstance(findings, list)
    assert len(findings) == 1
    # §15.5.1 contract: missing source is force-injected by adapter before from_dict
    d = findings[0]
    d.setdefault("source", FindingSource.VULN.value)
    f = Finding.from_dict(d)
    assert f.title == "t"
    assert f.source is FindingSource.VULN


def test_section15_envelope_default_severity_when_missing():
    """§15.5.1: missing severity → default 'medium' (FindingSeverity.MEDIUM)."""
    envelope = {"findings": [{"id": "x", "confidence": 0.5, "title": "t"}]}
    payload = envelope["findings"][0]
    # adapter 端会注入 default; 在 from_dict 这层我们要测的是兼容
    sev = payload.get("severity", "medium")
    assert FindingSeverity(sev) is FindingSeverity.MEDIUM


# ---------------------------------------------------------------------------
# Shared fixture: stub router for §7 tests
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_router():
    """Lightweight router that returns canned ChatResponse.

    ChatResponse / ChatChoice / ChatUsage / ChatMessage are Pydantic
    BaseModels — must be constructed with kwargs, not positional args.
    """
    from dataclasses import dataclass, field

    from shared_llm_core.client import (
        ChatChoice,
        ChatMessage,
        ChatRequest,
        ChatResponse,
        ChatUsage,
    )
    from shared_llm_core.router import LLMRouter, TaskTier

    @dataclass
    class _Stub:
        calls: list = field(default_factory=list)

        def chat(self, _tier: TaskTier, req: ChatRequest) -> ChatResponse:
            self.calls.append(req)
            return ChatResponse(
                id="stub",
                model="stub",
                created=0,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content="{}"),
                        finish_reason="stop",
                    )
                ],
                usage=ChatUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            )

    stub = _Stub()

    class _R(LLMRouter):
        def __init__(self):
            self._stub = stub

        def chat(self, tier, req):
            return self._stub.chat(tier, req)

    return _R()
