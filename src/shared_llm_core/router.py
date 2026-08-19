"""Tier-based router: pick the right (provider, model) for the task.

Why tiers? Different jobs have different cost/quality trade-offs:
- classification (single-line verdict) → Haiku tier
- explanation (paragraph narrative)  → Sonnet tier
- hard reasoning (multi-step, agentic) → Opus tier

The router keeps a list of rules `tier → provider+model`. The caller decides
the tier by passing `TaskTier`, the router picks the upstream.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from shared_llm_core.audit import AuditLog
from shared_llm_core.client import ChatRequest, ChatResponse, LLMClient
from shared_llm_core.config import CoreConfig
from shared_llm_core.telemetry import span


class TaskTier(str, Enum):
    """Cost/quality ladder. Cheap = fast+cheap; Premium = best."""

    CHEAP = "cheap"          # classification, routing, single-line answers
    STANDARD = "standard"    # summaries, narratives, explanations
    PREMIUM = "premium"      # complex reasoning, multi-step agents
    LOCAL = "local"          # force local provider regardless of tier


@dataclass(frozen=True)
class RouteRule:
    tier: TaskTier
    provider: str
    model: str


class LLMRouter:
    """Holds multiple `LLMClient`s and routes requests by tier."""

    def __init__(
        self,
        cfg: CoreConfig,
        rules: list[RouteRule],
        audit: AuditLog | None = None,
    ) -> None:
        self.cfg = cfg
        self._clients: dict[str, LLMClient] = {
            name: LLMClient(p) for name, p in cfg.providers.items() if p.enabled
        }
        self._rules: dict[TaskTier, RouteRule] = {r.tier: r for r in rules}
        self.audit = audit

    @classmethod
    def from_env(
        cls,
        rules: list[RouteRule] | None = None,
        yaml_path: str | None = None,
    ) -> "LLMRouter":
        """Convenience builder that wires env/YAML config + AuditLog."""
        from shared_llm_core.config import load_config

        cfg = load_config(yaml_path)
        audit = AuditLog(cfg.audit)
        if rules is None:
            rules = _default_rules(cfg)
        return cls(cfg, rules, audit)

    def close(self) -> None:
        for c in self._clients.values():
            c.close()

    def __enter__(self) -> "LLMRouter":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def resolve(self, tier: TaskTier) -> tuple[LLMClient, str]:
        rule = self._rules.get(tier)
        if rule is None:
            raise KeyError(f"No route configured for tier {tier!r}")
        client = self._clients.get(rule.provider)
        if client is None:
            raise KeyError(f"Provider {rule.provider!r} not configured")
        return client, rule.model

    def chat(self, tier: TaskTier, req: ChatRequest) -> ChatResponse:
        """Send a chat request through the tier's route; audit it."""
        client, model = self.resolve(tier)
        if req.model is None:
            req = req.model_copy(update={"model": model})
        with span(
            "llm.call",
            attributes={
                "llm.model": req.model or model,
                "llm.provider": client.provider.name,
                "llm.task_tier": tier.value,
            },
        ) as call_span:
            t0 = time.perf_counter()
            try:
                resp = client.chat(req)
                latency_ms = int((time.perf_counter() - t0) * 1000)
                call_span.set_attribute("llm.prompt_tokens", resp.usage.prompt_tokens)
                call_span.set_attribute("llm.completion_tokens", resp.usage.completion_tokens)
                call_span.set_attribute("llm.total_tokens", resp.usage.total_tokens)
                if self.audit is not None:
                    self.audit.record(
                        request=req,
                        response=resp,
                        provider=client.provider.name,
                        latency_ms=latency_ms,
                    )
            except BaseException:
                latency_ms = int((time.perf_counter() - t0) * 1000)
                call_span.set_attribute("llm.latency_ms", latency_ms)
                call_span.set_attribute("llm.success", False)
                raise
            call_span.set_attribute("llm.latency_ms", latency_ms)
            call_span.set_attribute("llm.success", True)
            return resp


def _default_rules(cfg: CoreConfig) -> list[RouteRule]:
    """Pick a sane rule set when none given.

    Heuristic: if `local` provider exists → use it for CHEAP, fall back to
    whatever else is configured for higher tiers.
    """
    local = cfg.providers.get("local")
    remote = next((p for n, p in cfg.providers.items() if n != "local"), None)
    rules: list[RouteRule] = []
    if local:
        rules.append(RouteRule(TaskTier.CHEAP, "local", local.default_model))
    if remote:
        rules.append(RouteRule(TaskTier.STANDARD, remote.name, remote.default_model))
        rules.append(RouteRule(TaskTier.PREMIUM, remote.name, remote.default_model))
    elif local:
        rules.append(RouteRule(TaskTier.STANDARD, "local", local.default_model))
        rules.append(RouteRule(TaskTier.PREMIUM, "local", local.default_model))
    return rules
