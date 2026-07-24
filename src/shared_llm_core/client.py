"""OpenAI-compatible Chat Completions client.

One client per upstream. The contract is intentionally narrow — we wrap the
`/v1/chat/completions` endpoint only. Tools, JSON mode, streaming are supported
because every modern provider (OpenAI, Anthropic via proxy, vLLM, Ollama, Qwen,
DeepSeek) speaks at least this subset.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Iterator

import httpx
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from shared_llm_core.config import ProviderConfig


class ChatMessage(BaseModel):
    """One message in a conversation."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None


class ChatRequest(BaseModel):
    """Caller-side request. Provider-specific knobs can be passed via `extra`."""

    model: str | None = None
    messages: list[ChatMessage]
    temperature: float = 0.2
    max_tokens: int | None = None
    top_p: float = 1.0
    response_format: dict[str, str] | None = None  # {"type": "json_object"}
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    stop: list[str] | None = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    extra: dict[str, Any] = Field(default_factory=dict)


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatResponse(BaseModel):
    id: str
    model: str
    created: int
    choices: list[ChatChoice]
    usage: ChatUsage = ChatUsage()
    raw: dict[str, Any] = Field(default_factory=dict)


@dataclass
class LLMClient:
    """Stateless client. Holds the provider config + an httpx connection pool."""

    provider: ProviderConfig
    _http: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._http = httpx.Client(
            base_url=self.provider.base_url.rstrip("/"),
            timeout=httpx.Timeout(self.provider.timeout_s),
            headers={
                "Authorization": f"Bearer {self.provider.api_key}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LLMClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _payload(self, req: ChatRequest) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": req.model or self.provider.default_model,
            "messages": [m.model_dump(exclude_none=True) for m in req.messages],
            "temperature": req.temperature,
            "top_p": req.top_p,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        if req.response_format is not None:
            body["response_format"] = req.response_format
        if req.tools is not None:
            body["tools"] = req.tools
        if req.tool_choice is not None:
            body["tool_choice"] = req.tool_choice
        if req.stop is not None:
            body["stop"] = req.stop
        body.update(req.extra)
        return body

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    )
    def chat(self, req: ChatRequest) -> ChatResponse:
        """Non-streaming chat completion. Retries on transient transport errors."""
        resp = self._http.post("/v1/chat/completions", json=self._payload(req))
        resp.raise_for_status()
        raw = resp.json()
        return self._parse(raw)

    def stream(self, req: ChatRequest) -> Iterator[str]:
        """Stream text deltas. Yields strings; caller assembles final message."""
        body = self._payload(req) | {"stream": True}
        with self._http.stream("POST", "/v1/chat/completions", json=body) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                # Minimal SSE parse — good enough for OpenAI/vLLM streaming.
                import json

                chunk = json.loads(data)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                if "content" in delta and delta["content"]:
                    yield delta["content"]

    @staticmethod
    def _parse(raw: dict[str, Any]) -> ChatResponse:
        choices_raw = raw.get("choices", [])
        choices = [
            ChatChoice(
                index=c.get("index", i),
                message=ChatMessage(**c.get("message", {"role": "assistant", "content": ""})),
                finish_reason=c.get("finish_reason"),
            )
            for i, c in enumerate(choices_raw)
        ]
        usage_raw = raw.get("usage") or {}
        usage = ChatUsage(
            prompt_tokens=usage_raw.get("prompt_tokens", 0),
            completion_tokens=usage_raw.get("completion_tokens", 0),
            total_tokens=usage_raw.get("total_tokens", 0),
        )
        return ChatResponse(
            id=raw.get("id", str(uuid.uuid4())),
            model=raw.get("model", "unknown"),
            created=raw.get("created", int(time.time())),
            choices=choices,
            usage=usage,
            raw=raw,
        )