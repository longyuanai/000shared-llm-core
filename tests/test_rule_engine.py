"""v0.5 §8 RuleEngine — test suite.

9 test functions covering: Rule ABC instantiation guard, registry CRUD,
default registry has builtins, engine evaluation (all / subset), rule
failure isolation, BruteForceRule threshold behavior, KnownCVERule
matching.
"""

from __future__ import annotations

import pytest

from shared_llm_core.finding import FindingSeverity
from shared_llm_core.rule_engine import (
    Rule,
    RuleContext,
    RuleEngine,
    RuleRegistry,
)
from shared_llm_core.rules.builtin import BruteForceRule, KnownCVERule


def test_rule_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        Rule()  # type: ignore[abstract]


def test_rule_registry_register_and_get():
    reg = RuleRegistry()
    rule = BruteForceRule()
    reg.register(rule)
    assert reg.get("core-brute-force") is rule


def test_rule_repr_and_registry_lifecycle():
    reg = RuleRegistry()
    rule = BruteForceRule()
    assert repr(rule) == "Rule(core-brute-force)"
    reg.register(rule)
    assert reg.all() == [rule]
    assert "core-brute-force" in reg
    assert len(reg) == 1
    reg.unregister(rule.id)
    assert rule.id not in reg
    assert len(reg) == 0


def test_rule_registry_rejects_empty_id():
    class EmptyRule(Rule):
        id = ""

        def evaluate(self, ctx):
            return []

    with pytest.raises(ValueError, match="non-empty"):
        RuleRegistry().register(EmptyRule())


def test_rule_engine_registry_property():
    registry = RuleRegistry()
    assert RuleEngine(registry).registry is registry


def test_rule_registry_duplicate_raises():
    reg = RuleRegistry()
    reg.register(BruteForceRule())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(BruteForceRule())


def test_rule_registry_unknown_get_raises():
    reg = RuleRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")


def test_rule_registry_default_has_builtins():
    reg = RuleRegistry.default()
    assert "core-brute-force" in reg
    assert "core-known-cve" in reg
    assert len(reg) == 2


def test_rule_engine_evaluate_all():
    engine = RuleEngine()
    ctx = RuleContext(
        subject="10.0.0.5",
        facts={"failed_logins": 20, "version": "openssh-7.0"},
    )
    findings = engine.evaluate(ctx)
    # BruteForce + KnownCVE both match
    assert len(findings) >= 2
    titles = [f.title for f in findings]
    assert any("Brute force" in t for t in titles)
    assert any("Known-vulnerable" in t for t in titles)


def test_rule_engine_evaluate_subset_by_ids():
    engine = RuleEngine()
    ctx = RuleContext(subject="x", facts={"version": "openssh-7.0"})
    findings = engine.evaluate(ctx, rule_ids=["core-known-cve"])
    assert len(findings) == 1
    assert "Known-vulnerable" in findings[0].title


def test_rule_engine_silent_on_rule_failure(capsys):
    class BrokenRule(Rule):
        id = "broken"
        severity_hint = "low"

        def evaluate(self, ctx):
            raise RuntimeError("boom")

    reg = RuleRegistry()
    reg.register(BrokenRule())
    reg.register(KnownCVERule())
    engine = RuleEngine(reg)

    ctx = RuleContext(subject="x", facts={"version": "openssh-7.0"})
    findings = engine.evaluate(ctx)

    # Broken rule didn't crash engine; KnownCVE still produced a finding
    assert any("Known-vulnerable" in f.title for f in findings)
    captured = capsys.readouterr()
    assert "broken" in captured.err
    assert "boom" in captured.err


def test_brute_force_rule_threshold():
    rule = BruteForceRule(threshold=5)
    ctx_low = RuleContext(subject="x", facts={"failed_logins": 3})
    ctx_hi = RuleContext(subject="x", facts={"failed_logins": 100})
    assert rule.evaluate(ctx_low) == []
    findings = rule.evaluate(ctx_hi)
    assert len(findings) == 1
    # 100 / (5*4) = 5.0, clamped to 1.0
    assert findings[0].confidence == 1.0


def test_known_cve_rule_match():
    rule = KnownCVERule()
    miss = rule.evaluate(RuleContext(subject="x", facts={"version": "safe-1.0"}))
    hit = rule.evaluate(RuleContext(subject="x", facts={"version": "openssh-7.0"}))
    assert miss == []
    assert len(hit) == 1
    assert hit[0].severity == FindingSeverity.CRITICAL
