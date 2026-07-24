"""Tests for the OpenAI-compatible client.

We don't hit a real network. The httpx transport is patched so the test
asserts request shape and parses a canned response.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from shared_llm_core.client import ChatMessage, ChatRequest, LLMClient
from shared_llm_core.config import ProviderConfig


def _client(handler: Any) -> tuple[LLMClient, ProviderConfig]:
    cfg = ProviderConfig(
        name="test",
        base_url="http://test.local/v1",
        api_key="k",
        default_model="m-test",
        timeout_s=5.0,
    )
    c = LLMClient(cfg)
    # Replace the underlying httpx client with one whose transport we control.
    c._http = httpx.Client(
        base_url=cfg.base_url,
        headers=c._http.headers,
        transport=httpx.MockTransport(handler),
    )
    return c, cfg


def _ok_response(model: str = "m-test") -> dict[str, Any]:
    return {
        "id": "resp-1",
        "model": model,
        "created": 1700000000,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "hello back"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 7, "completion_tokens": 2, "total_tokens": 9},
    }


def test_chat_sends_correct_payload_and_parses_response() -> None:
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["body"] = json.loads(req.content.decode("utf-8"))
        captured["headers"] = dict(req.headers)
        return httpx.Response(200, json=_ok_response())

    client, _ = _client(handler)
    with client:
        resp = client.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="hi")],
                temperature=0.5,
                max_tokens=32,
            )
        )

    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["headers"]["authorization"] == "Bearer k"
    body = captured["body"]
    assert body["model"] == "m-test"
    assert body["messages"] == [{"role": "user", "content": "hi"}]
    assert body["temperature"] == 0.5
    assert body["max_tokens"] == 32

    assert resp.model == "m-test"
    assert resp.choices[0].message.content == "hello back"
    assert resp.usage.total_tokens == 9
    assert resp.choices[0].finish_reason == "stop"


def test_chat_uses_request_model_override() -> None:
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content.decode("utf-8"))
        return httpx.Response(200, json=_ok_response(model="m-other"))

    client, _ = _client(handler)
    resp = client.chat(
        ChatRequest(
            model="m-other",
            messages=[ChatMessage(role="user", content="hi")],
        )
    )
    assert captured["body"]["model"] == "m-other"
    assert resp.model == "m-other"


def test_chat_retries_on_transient_error_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(503, text="boom")
        return httpx.Response(200, json=_ok_response())

    client, _ = _client(handler)
    with client:
        resp = client.chat(ChatRequest(messages=[ChatMessage(role="user", content="x")]))

    assert calls["n"] == 2
    assert resp.choices[0].message.content == "hello back"


def test_chat_passes_tools_and_response_format() -> None:
    captured: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(req.content.decode("utf-8"))
        return httpx.Response(200, json=_ok_response())

    client, _ = _client(handler)
    with client:
        client.chat(
            ChatRequest(
                messages=[ChatMessage(role="user", content="json please")],
                response_format={"type": "json_object"},
                tools=[{"type": "function", "function": {"name": "noop"}}],
            )
        )

    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["tools"] == [{"type": "function", "function": {"name": "noop"}}]


def test_stream_yields_deltas() -> None:
    chunks = [
        'data: {"choices":[{"delta":{"content":"hel"}}]}\n\n',
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
        "data: [DONE]\n\n",
    ]
    body = "".join(chunks).encode("utf-8")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    client, _ = _client(handler)
    with client:
        tokens = list(client.stream(ChatRequest(messages=[ChatMessage(role="user", content="hi")])))

    assert tokens == ["hel", "lo"]