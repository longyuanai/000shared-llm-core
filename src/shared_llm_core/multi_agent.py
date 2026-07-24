"""v0.5 §7 MultiAgentOrchestrator — multi-agent mission runner.

A `Mission` runs N `AgentRole`s. Each role gets one `LLMRouter.chat`
call. Outputs flow into the next agent's context via the shared
`scratchpad`. Failures are captured per-agent (`AgentResult.error`) —
the mission continues.

Public API cheat sheet
----------------------
MultiAgentOrchestrator(router)                           # build with v0.1 router
orch.run(mission, [AgentRole.SCOUT, ...]) -> [Result]   # sequential, errors swallowed
AgentRole.{SCOUT,ANALYST,EXPLOITER,SYNTHESIZER,REVIEWER} # role enum (str)
MissionContext(task, inputs={})                          # scratchpad + metadata
AgentResult(role, output, error=None, latency_ms=0)      # one role's outcome
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from shared_llm_core.client import ChatMessage, ChatRequest
from shared_llm_core.finding import Finding
from shared_llm_core.router import LLMRouter, TaskTier


class AgentRole(str, Enum):
    """Roles in a multi-agent mission."""

    SCOUT = "scout"             # recon / gathering
    ANALYST = "analyst"         # deep analysis
    EXPLOITER = "exploiter"     # attack / validate
    SYNTHESIZER = "synthesizer"  # final synthesis
    REVIEWER = "reviewer"       # critique / fact-check


@dataclass(frozen=True)
class MissionContext:
    """The shared state for one multi-agent run."""

    task: str
    inputs: Mapping[str, Any]
    scratchpad: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    """One agent's outcome. `error` is set iff the agent failed."""

    role: AgentRole
    output: str
    findings: tuple[Finding, ...] = ()
    latency_ms: int = 0
    error: str | None = None


_TIER_BY_ROLE: dict[AgentRole, TaskTier] = {
    AgentRole.SCOUT: TaskTier.CHEAP,
    AgentRole.ANALYST: TaskTier.STANDARD,
    AgentRole.EXPLOITER: TaskTier.STANDARD,
    AgentRole.SYNTHESIZER: TaskTier.STANDARD,
    AgentRole.REVIEWER: TaskTier.PREMIUM,
}


def _build_prompt(mission: MissionContext, role: AgentRole) -> str:
    parts = [
        f"Role: {role.value}",
        f"Task: {mission.task}",
    ]
    if mission.scratchpad:
        parts.append("Scratchpad from earlier agents:")
        parts.extend(f"- {line}" for line in mission.scratchpad)
    if mission.inputs:
        parts.append("Inputs:")
        for k, v in mission.inputs.items():
            parts.append(f"- {k}: {v!r}")
    return "\n".join(parts)


class MultiAgentOrchestrator:
    """Sequential multi-agent runner.

    `run()` invokes one `router.chat()` per role, in order. Outputs are
    appended to the scratchpad and visible to subsequent agents. Agent
    failures don't abort the mission — they appear in `AgentResult.error`.
    """

    def __init__(
        self,
        router: LLMRouter,
        *,
        max_concurrency: int = 4,  # reserved; v0.5 runs sequentially
        scratchpad_size: int = 4096,
    ) -> None:
        self._router = router
        self._max_concurrency = max_concurrency
        self._scratchpad_size = scratchpad_size

    def run(
        self,
        mission: MissionContext,
        roles: Sequence[AgentRole],
    ) -> list[AgentResult]:
        """Run every role in `roles` against `mission`.

        Returns one `AgentResult` per role, in the same order. The
        scratchpad grows as agents complete.
        """
        if not roles:
            return []

        results: list[AgentResult] = []
        scratchpad = list(mission.scratchpad)

        for role in roles:
            prompt = _build_prompt(
                MissionContext(
                    task=mission.task,
                    inputs=mission.inputs,
                    scratchpad=tuple(scratchpad),
                    metadata=mission.metadata,
                ),
                role,
            )
            tier = _TIER_BY_ROLE.get(role, TaskTier.STANDARD)
            req = ChatRequest(
                model="multi-agent",
                messages=[ChatMessage(role="user", content=prompt)],
                response_format={"type": "json_object"},
            )

            t0 = time.monotonic()
            try:
                resp = self._router.chat(tier, req)
                content = resp.choices[0].message.content
                latency_ms = int((time.monotonic() - t0) * 1000)
                result = AgentResult(
                    role=role,
                    output=content,
                    latency_ms=latency_ms,
                )
                scratchpad.append(f"[{role.value}] {content}")
            except Exception as exc:  # noqa: BLE001 - capture any error
                latency_ms = int((time.monotonic() - t0) * 1000)
                result = AgentResult(
                    role=role,
                    output="",
                    latency_ms=latency_ms,
                    error=f"{type(exc).__name__}: {exc}",
                )

            results.append(result)

        return results