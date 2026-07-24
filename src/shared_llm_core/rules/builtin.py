"""Demo rules. Real longyuanai products ship their own; these are for
shared-llm-core self-test and as copy-paste templates.
"""

from __future__ import annotations

from typing import Any

from shared_llm_core.finding import Finding, FindingSeverity, FindingSource
from shared_llm_core.rule_engine import Rule, RuleContext


class BruteForceRule(Rule):
    """Trigger when `facts['failed_logins']` exceeds a threshold."""

    id = "core-brute-force"
    severity_hint = "high"

    def __init__(self, threshold: int = 5) -> None:
        self._threshold = threshold

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        failed: Any = ctx.facts.get("failed_logins", 0)
        if not isinstance(failed, int) or failed <= self._threshold:
            return []
        confidence = min(1.0, failed / (self._threshold * 4))
        return [
            Finding(
                id="",
                source=FindingSource.EXTERNAL,
                severity=FindingSeverity.HIGH,
                confidence=confidence,
                title=f"Brute force suspected on {ctx.subject}",
                host=ctx.subject,
                evidence=(f"failed_logins={failed}", f"threshold={self._threshold}"),
                tags=frozenset({"brute-force", "auth"}),
            )
        ]


class KnownCVERule(Rule):
    """Trigger when the asset version matches a known-vulnerable string.

    The version list is a demo set. Real products should swap in a live
    feed (NVD, KEV, vendor advisories).
    """

    id = "core-known-cve"
    severity_hint = "critical"

    _KNOWN_VULN: frozenset[str] = frozenset({
        "openssh-7.0",
        "apache-2.2.0",
        "nginx-0.6.0",
    })

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        version = ctx.facts.get("version", "")
        if version not in self._KNOWN_VULN:
            return []
        return [
            Finding(
                id="",
                source=FindingSource.EXTERNAL,
                severity=FindingSeverity.CRITICAL,
                confidence=0.9,
                title=f"Known-vulnerable version detected: {version}",
                host=ctx.subject,
                evidence=(f"version={version}",),
                tags=frozenset({"known-cve", "vulnerable-version"}),
            )
        ]