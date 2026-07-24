"""v0.5 §8 RuleEngine — rule abstraction layer.

A Rule is a pure function `(ctx) -> list[Finding]`. RuleEngine runs all
(or selected) rules, swallows failures per rule so one bad rule doesn't
break the scan, and aggregates Findings.

Public API cheat sheet
----------------------
class MyRule(Rule):                                      # subclass; set id + evaluate
    id = "my.product.find-foo"
    def evaluate(self, ctx: RuleContext) -> list[Finding]
RuleRegistry.default() -> RuleRegistry                   # builtin rules pre-loaded
RuleRegistry().register(rule) / .get(id) / .all()        # CRUD
RuleEngine(registry=None).evaluate(ctx) -> list[Finding] # errors → stderr, no raise
RuleEngine.evaluate(ctx, rule_ids=["x","y"])             # subset by id, in reg order
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping, Sequence

from shared_llm_core.finding import Finding


class Rule(ABC):
    """Base class for all rules.

    Subclasses MUST define `id` as a class attribute. `evaluate` is the
    only required method; everything else has safe defaults.
    """

    id: str  # subclasses must override
    severity_hint: Literal["low", "medium", "high", "critical"] = "medium"

    @abstractmethod
    def evaluate(self, ctx: "RuleContext") -> list[Finding]:
        """Run the rule. MUST be pure: do not mutate ctx."""

    def __repr__(self) -> str:
        return f"Rule({self.id})"


@dataclass(frozen=True)
class RuleContext:
    """Inputs to a Rule.

    `subject` is the entity being analysed (an IP, user, CVE, file path,
    binary blob, etc). `facts` is the bag of evidence the rule decides
    on. `window` optionally limits the time scope. `related` carries
    Findings already discovered by earlier rules in the same scan, so a
    rule can correlate without re-running detection.
    """

    subject: str
    facts: Mapping[str, Any]
    window: tuple[datetime, datetime] | None = None
    related: tuple[Finding, ...] = ()


class RuleRegistry:
    """In-process collection of rules. Lookup by `id`."""

    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if not rule.id:
            raise ValueError("Rule.id must be non-empty")
        if rule.id in self._rules:
            raise ValueError(f"Rule {rule.id!r} already registered")
        self._rules[rule.id] = rule

    def unregister(self, rule_id: str) -> None:
        self._rules.pop(rule_id, None)

    def get(self, rule_id: str) -> Rule:
        if rule_id not in self._rules:
            raise KeyError(f"Rule {rule_id!r} not found")
        return self._rules[rule_id]

    def all(self) -> list[Rule]:
        return list(self._rules.values())

    def __contains__(self, rule_id: str) -> bool:
        return rule_id in self._rules

    def __len__(self) -> int:
        return len(self._rules)

    @classmethod
    def default(cls) -> "RuleRegistry":
        """Registry pre-loaded with shared_llm_core built-in rules."""
        from shared_llm_core.rules.builtin import BruteForceRule, KnownCVERule

        reg = cls()
        reg.register(BruteForceRule())
        reg.register(KnownCVERule())
        return reg


class RuleEngine:
    """Run rules against a RuleContext, collect Findings."""

    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry or RuleRegistry.default()

    @property
    def registry(self) -> RuleRegistry:
        return self._registry

    def evaluate(
        self,
        ctx: RuleContext,
        *,
        rule_ids: Sequence[str] | None = None,
    ) -> list[Finding]:
        """Run rules sequentially. Failures are skipped (logged to stderr).

        `rule_ids=None` means "run every registered rule". Otherwise run
        only the named subset (in registration order).
        """
        if rule_ids is None:
            targets = self._registry.all()
        else:
            targets = [self._registry.get(rid) for rid in rule_ids]

        results: list[Finding] = []
        for rule in targets:
            try:
                findings = rule.evaluate(ctx)
                if findings:
                    results.extend(findings)
            except Exception as exc:  # noqa: BLE001 - we want broad except
                print(
                    f"[rule_engine] rule {rule.id!r} failed: {exc}",
                    file=sys.stderr,
                )
        return results