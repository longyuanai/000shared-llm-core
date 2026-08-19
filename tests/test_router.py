"""Tests for the router and config loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from shared_llm_core.audit import AuditLog
from shared_llm_core.client import ChatMessage, ChatRequest, LLMClient
from shared_llm_core.config import AuditConfig, CoreConfig, ProviderConfig, load_config
from shared_llm_core.router import LLMRouter, RouteRule, TaskTier


def _stub_client(provider: ProviderConfig, replies: list[dict[str, Any]]) -> LLMClient:
    queue = list(replies)

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=queue.pop(0))

    c = LLMClient(provider)
    c._http = httpx.Client(
        base_url=provider.base_url,
        headers=c._http.headers,
        transport=httpx.MockTransport(handler),
    )
    return c


def _ok(content: str = "ok", model: str = "m") -> dict[str, Any]:
    return {
        "id": "x",
        "model": model,
        "created": 0,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _core_with_two_providers() -> CoreConfig:
    return CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local", base_url="http://l", api_key="k", default_model="m-local"
            ),
            "remote": ProviderConfig(
                name="remote", base_url="http://r", api_key="k2", default_model="m-remote"
            ),
        },
        audit=AuditConfig(backend="noop"),
    )


def test_router_resolves_tier_to_provider_model() -> None:
    core = _core_with_two_providers()
    router = LLMRouter(
        core,
        rules=[
            RouteRule(TaskTier.CHEAP, "local", "m-local"),
            RouteRule(TaskTier.STANDARD, "remote", "m-remote"),
            RouteRule(TaskTier.PREMIUM, "remote", "m-remote-premium"),
        ],
        audit=None,
    )
    client, model = router.resolve(TaskTier.CHEAP)
    assert client.provider.name == "local"
    assert model == "m-local"

    client, model = router.resolve(TaskTier.PREMIUM)
    assert client.provider.name == "remote"
    assert model == "m-remote-premium"


def test_router_unknown_tier_raises() -> None:
    core = _core_with_two_providers()
    router = LLMRouter(core, rules=[RouteRule(TaskTier.CHEAP, "local", "m")], audit=None)
    with pytest.raises(KeyError):
        router.resolve(TaskTier.PREMIUM)


def test_router_missing_provider_raises() -> None:
    core = _core_with_two_providers()
    router = LLMRouter(core, rules=[RouteRule(TaskTier.LOCAL, "missing", "m")], audit=None)
    try:
        with pytest.raises(KeyError, match="not configured"):
            router.resolve(TaskTier.LOCAL)
    finally:
        router.close()


def test_router_chat_records_audit(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.jsonl"
    core = CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local", base_url="http://l", api_key="k", default_model="m-local"
            )
        },
        audit=AuditConfig(backend="jsonl", path=str(audit_path)),
    )
    # Construct audit explicitly — LLMRouter takes the AuditLog directly,
    # not the AuditConfig.
    router = LLMRouter(
        core,
        rules=[RouteRule(TaskTier.STANDARD, "local", "m-local")],
        audit=AuditLog(core.audit),
    )
    # Patch the underlying client with a stub
    router._clients["local"] = _stub_client(core.providers["local"], [_ok("hi")])
    try:
        resp = router.chat(
            TaskTier.STANDARD, ChatRequest(messages=[ChatMessage(role="user", content="ping")])
        )
        assert resp.choices[0].message.content == "hi"
    finally:
        router.close()
    lines = audit_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["provider"] == "local"


def test_router_chat_injects_route_model() -> None:
    core = CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local", base_url="http://l", api_key="k", default_model="m-local"
            )
        },
        audit=AuditConfig(backend="noop"),
    )
    router = LLMRouter(core, rules=[RouteRule(TaskTier.STANDARD, "local", "m-route")])
    seen: dict[str, Any] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(req.content.decode("utf-8"))
        return httpx.Response(200, json=_ok("ok", model="m-route"))

    client = router._clients["local"]
    client._http = httpx.Client(
        base_url=client.provider.base_url,
        headers=client._http.headers,
        transport=httpx.MockTransport(handler),
    )
    try:
        router.chat(TaskTier.STANDARD, ChatRequest(messages=[ChatMessage(role="user", content="x")]))
        assert seen["body"]["model"] == "m-route"
    finally:
        router.close()


def test_load_config_from_yaml(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        json.dumps(
            {
                "providers": [
                    {
                        "name": "local",
                        "base_url": "http://x",
                        "default_model": "m",
                        "api_key": "k",
                    }
                ],
                "audit": {"backend": "stdout", "path": "/tmp/a.jsonl"},
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert "local" in cfg.providers
    assert cfg.providers["local"].base_url == "http://x"
    assert cfg.audit.backend == "stdout"


def test_load_config_no_providers_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDERS", raising=False)
    # Pass an existing-but-empty file so load_config reaches its own check
    # rather than its FileNotFoundError fast path. We want to assert the
    # "no providers configured" ValueError.
    empty_cfg = tmp_path / "empty.yml"
    empty_cfg.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="No providers configured"):
        load_config(empty_cfg)


def test_load_config_missing_file_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_PROVIDERS", raising=False)
    with pytest.raises(FileNotFoundError, match="Config file not found"):
        load_config(tmp_path / "missing.yml")


def test_load_config_env_provider_and_audit_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "broken,local")
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://env")
    monkeypatch.setenv("LLM_LOCAL_DEFAULT_MODEL", "m-env")
    monkeypatch.setenv("LLM_LOCAL_ENABLED", "off")
    monkeypatch.setenv("LLM_LOCAL_TIMEOUT_S", "2.5")
    monkeypatch.setenv("LLM_LOCAL_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_AUDIT_BACKEND", "noop")
    monkeypatch.setenv("LLM_AUDIT_INCLUDE_PROMPT", "false")
    monkeypatch.setenv("LLM_AUDIT_INCLUDE_RESPONSE", "true")

    cfg = load_config()

    assert set(cfg.providers) == {"local"}
    provider = cfg.providers["local"]
    assert provider.enabled is False
    assert provider.timeout_s == 2.5
    assert provider.max_retries == 4
    assert cfg.audit.backend == "noop"
    assert cfg.audit.include_prompt is False
    assert cfg.audit.include_response is True


def test_load_config_yaml_boolean_audit_options(tmp_path: Path) -> None:
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        "providers:\n"
        "  - name: local\n"
        "    base_url: http://yaml\n"
        "    default_model: m-yaml\n"
        "audit:\n"
        "  backend: noop\n"
        "  include_prompt: false\n"
        "  include_response: true\n",
        encoding="utf-8",
    )

    cfg = load_config(cfg_file)
    assert cfg.audit.include_prompt is False
    assert cfg.audit.include_response is True


def test_load_config_yaml_overrides_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "local")
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://env")
    monkeypatch.setenv("LLM_LOCAL_DEFAULT_MODEL", "m-env")
    cfg_file = tmp_path / "cfg.yml"
    cfg_file.write_text(
        "providers:\n  - name: local\n    base_url: http://yaml\n    default_model: m-yaml\n    api_key: k\n",
        encoding="utf-8",
    )
    cfg = load_config(cfg_file)
    assert cfg.providers["local"].base_url == "http://yaml"
    assert cfg.providers["local"].default_model == "m-yaml"


def test_router_context_manager_closes_clients() -> None:
    core = CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local", base_url="http://l", api_key="k", default_model="m"
            )
        },
        audit=AuditConfig(backend="noop"),
    )
    router = LLMRouter(core, rules=[RouteRule(TaskTier.CHEAP, "local", "m")])
    with router:
        client = router._clients["local"]
        assert not client._http.is_closed
    assert client._http.is_closed


def test_default_rules_use_local_when_present() -> None:
    from shared_llm_core.router import _default_rules

    core = _core_with_two_providers()
    rules = _default_rules(core)
    by_tier = {r.tier: r for r in rules}
    assert by_tier[TaskTier.CHEAP].provider == "local"
    assert by_tier[TaskTier.STANDARD].provider == "remote"
    assert by_tier[TaskTier.PREMIUM].provider == "remote"


def test_default_rules_use_local_for_all_tiers_when_only_local_exists() -> None:
    core = CoreConfig(
        providers={
            "local": ProviderConfig(
                name="local", base_url="http://l", api_key="k", default_model="m-local"
            )
        },
        audit=AuditConfig(backend="noop"),
    )
    from shared_llm_core.router import _default_rules

    rules = _default_rules(core)
    assert {rule.tier for rule in rules} == {TaskTier.CHEAP, TaskTier.STANDARD, TaskTier.PREMIUM}
    assert all(rule.provider == "local" and rule.model == "m-local" for rule in rules)


def test_router_from_env_builds_default_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDERS", "local")
    monkeypatch.setenv("LLM_LOCAL_BASE_URL", "http://local")
    monkeypatch.setenv("LLM_LOCAL_DEFAULT_MODEL", "m-local")
    monkeypatch.setenv("LLM_AUDIT_BACKEND", "noop")

    router = LLMRouter.from_env()
    try:
        client, model = router.resolve(TaskTier.STANDARD)
        assert client.provider.name == "local"
        assert model == "m-local"
    finally:
        router.close()
