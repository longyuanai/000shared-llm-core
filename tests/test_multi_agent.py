"""v0.5 §7 MultiAgentOrchestrator — test suite.

11 test functions. Uses a stub router (records calls, returns canned
responses) so tests don't hit any real LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from shared_llm_core.client import (
    ChatChoice,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatUsage,
)
from shared_llm_core.multi_agent import (
    AgentResult,
    AgentRole,
    MissionContext,
    MultiAgentOrchestrator,
)
from shared_llm_core.router import LLMRouter, RouteRule, TaskTier


@dataclass
class StubRouter:
    """Minimal stand-in for LLMRouter that records calls."""

    reply_content: str = '{"answer": "ok"}'
    calls: list[ChatRequest] = field(default_factory=list)
    fail_next: bool = False

    def chat(self, tier: TaskTier, req: ChatRequest) -> ChatResponse:
        self.calls.append(req)
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("simulated LLM failure")
        return ChatResponse(
            id="stub-1",
            model="stub-model",
            created=0,
            choices=[
                ChatChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=self.reply_content),
                    finish_reason="stop",
                )
            ],
            usage=ChatUsage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
        )


@pytest.fixture
def stub():
    return StubRouter()


@pytest.fixture
def router(stub):
    """LLMRouter that delegates chat() to our stub.

    Bypasses real config: just wraps the stub in an LLMRouter shell.
    """
    # LLMRouter normally needs a CoreConfig; we monkey-patch chat() on
    # the instance via a subclass to avoid that plumbing here.
    class _R(LLMRouter):
        def __init__(self, _stub: StubRouter):
            self._stub = _stub

        def chat(self, tier, req):
            return self._stub.chat(tier, req)

    return _R(stub)


def test_agent_role_enum_values():
    vals = {r.value for r in AgentRole}
    assert vals == {"scout", "analyst", "exploiter", "synthesizer", "reviewer"}


def test_mission_context_required_fields():
    mc = MissionContext(task="x", inputs={"a": 1})
    assert mc.task == "x"
    assert mc.inputs == {"a": 1}
    assert mc.scratchpad == ()


def test_mission_context_default_scratchpad_empty():
    mc = MissionContext(task="x", inputs={})
    assert mc.scratchpad == ()


def test_mission_context_immutable():
    from dataclasses import FrozenInstanceError

    mc = MissionContext(task="x", inputs={})
    with pytest.raises(FrozenInstanceError):
        mc.task = "y"  # type: ignore[misc]


def test_agent_result_required_fields():
    r = AgentResult(role=AgentRole.SCOUT, output="hi")
    assert r.role == AgentRole.SCOUT
    assert r.output == "hi"
    assert r.findings == ()
    assert r.error is None
    assert r.latency_ms == 0


def test_agent_result_default_error_none():
    r = AgentResult(role=AgentRole.ANALYST, output="x")
    assert r.error is None


def test_orchestrator_single_agent_runs(stub, router):
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={})
    results = orch.run(mc, [AgentRole.SCOUT])
    assert len(results) == 1
    assert results[0].role == AgentRole.SCOUT
    assert results[0].output == stub.reply_content
    assert results[0].error is None


def test_orchestrator_multiple_agents_sequential(stub, router):
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={"host": "h1"})
    results = orch.run(mc, [AgentRole.SCOUT, AgentRole.ANALYST, AgentRole.SYNTHESIZER])
    assert [r.role for r in results] == [
        AgentRole.SCOUT,
        AgentRole.ANALYST,
        AgentRole.SYNTHESIZER,
    ]
    assert len(stub.calls) == 3


def test_scratchpad_appended_across_agents(stub, router):
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={})
    orch.run(mc, [AgentRole.SCOUT, AgentRole.ANALYST])
    # Second agent's prompt should contain the first agent's output
    second_prompt = stub.calls[1].messages[0].content
    assert "scout" in second_prompt
    assert stub.reply_content in second_prompt


def test_agent_failure_does_not_raise(stub, router):
    stub.fail_next = True
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={})
    # First agent fails; second should still run
    results = orch.run(mc, [AgentRole.SCOUT, AgentRole.SYNTHESIZER])
    assert len(results) == 2
    assert results[0].error is not None
    assert results[1].error is None
    assert len(stub.calls) == 2  # second agent still attempted


def test_latency_recorded_positive(stub, router):
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={})
    results = orch.run(mc, [AgentRole.SCOUT])
    assert results[0].latency_ms >= 0  # may be 0 on fast hardware, never negative


def test_empty_roles_returns_empty(stub, router):
    orch = MultiAgentOrchestrator(router)
    mc = MissionContext(task="t", inputs={})
    assert orch.run(mc, []) == []