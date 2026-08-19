from __future__ import annotations

from typing import Any

from shared_llm_core import ChatMessage, ChatResponse, ChatUsage, demo


def test_demo_main_uses_template_and_router(monkeypatch, capsys) -> None:
    calls: dict[str, Any] = {}

    class StubTemplate:
        def render(self, **kwargs: Any) -> list[ChatMessage]:
            calls["render"] = kwargs
            return [ChatMessage(role="user", content="hello")]

    class StubRegistry:
        def __init__(self, root: str) -> None:
            calls["root"] = root

        def get(self, name: str, version: str) -> StubTemplate:
            calls["template"] = (name, version)
            return StubTemplate()

    class StubRouter:
        @classmethod
        def from_env(cls) -> StubRouter:
            calls["from_env"] = True
            return cls()

        def __enter__(self) -> StubRouter:
            return self

        def __exit__(self, *_: object) -> None:
            calls["closed"] = True

        def chat(self, tier: Any, request: Any) -> ChatResponse:
            calls["chat"] = (tier, request)
            return ChatResponse(
                id="demo-response",
                model="demo-model",
                created=0,
                choices=[
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "demo reply"},
                        "finish_reason": "stop",
                    }
                ],
                usage=ChatUsage(total_tokens=3),
            )

    monkeypatch.setattr(demo, "TemplateRegistry", StubRegistry)
    monkeypatch.setattr(demo, "LLMRouter", StubRouter)
    demo.main()

    assert calls["root"] == "./prompts"
    assert calls["template"] == ("hello", "v1")
    assert calls["render"] == {"name": "longyuanai"}
    assert calls["from_env"] is True
    assert calls["closed"] is True
    output = capsys.readouterr().out
    assert "demo-model" in output
    assert "3" in output
    assert "demo reply" in output
