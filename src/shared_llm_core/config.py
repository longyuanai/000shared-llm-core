"""Configuration loading for shared-llm-core.

Reads from environment variables and an optional YAML config. Resolution order:
1. Explicit overrides (passed to `load_config`)
2. YAML config file (if path provided)
3. Environment variables (LLM_* prefix)

The intent is "12-factor": every value can be overridden by env, so the same
codebase runs locally (vLLM), on staging (Claude), and in production without
code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProviderConfig:
    """A single upstream LLM endpoint speaking the OpenAI Chat Completions protocol."""

    name: str
    base_url: str
    api_key: str
    default_model: str
    timeout_s: float = 60.0
    max_retries: int = 3
    enabled: bool = True


@dataclass(frozen=True)
class AuditConfig:
    """Where to persist audit records."""

    backend: str = "jsonl"  # "jsonl" | "stdout" | "noop"
    path: str = "./audit.jsonl"
    include_prompt: bool = True
    include_response: bool = True


@dataclass(frozen=True)
class CoreConfig:
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    audit: AuditConfig = field(default_factory=AuditConfig)


def _coerce_bool(value: str | bool | None, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _build_provider_from_env(name: str, prefix: str) -> ProviderConfig | None:
    base_url = os.getenv(f"{prefix}_BASE_URL")
    api_key = os.getenv(f"{prefix}_API_KEY", "no-key-required")
    default_model = os.getenv(f"{prefix}_DEFAULT_MODEL")
    if not (base_url and default_model):
        return None
    return ProviderConfig(
        name=name,
        base_url=base_url,
        api_key=api_key,
        default_model=default_model,
        timeout_s=float(os.getenv(f"{prefix}_TIMEOUT_S", "60")),
        max_retries=int(os.getenv(f"{prefix}_MAX_RETRIES", "3")),
        enabled=_coerce_bool(os.getenv(f"{prefix}_ENABLED"), True),
    )


def _build_provider_from_yaml(raw: dict[str, Any]) -> ProviderConfig:
    return ProviderConfig(
        name=raw["name"],
        base_url=raw["base_url"],
        api_key=raw.get("api_key", "no-key-required"),
        default_model=raw["default_model"],
        timeout_s=float(raw.get("timeout_s", 60.0)),
        max_retries=int(raw.get("max_retries", 3)),
        enabled=bool(raw.get("enabled", True)),
    )


def load_config(yaml_path: str | Path | None = None) -> CoreConfig:
    """Load config from YAML + env. YAML wins when present for the same key."""
    providers: dict[str, ProviderConfig] = {}

    # 1. env providers (LLM_<NAME>_BASE_URL etc.)
    env_names = os.getenv("LLM_PROVIDERS", "")
    for name in [n.strip() for n in env_names.split(",") if n.strip()]:
        prefix = f"LLM_{name.upper()}"
        pc = _build_provider_from_env(name, prefix)
        if pc:
            providers[name] = pc

    # 2. YAML overrides
    if yaml_path is not None:
        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in raw.get("providers", []):
            pc = _build_provider_from_yaml(entry)
            providers[pc.name] = pc
        audit_raw = raw.get("audit", {})
        audit = AuditConfig(
            backend=audit_raw.get("backend", "jsonl"),
            path=audit_raw.get("path", "./audit.jsonl"),
            include_prompt=_coerce_bool(audit_raw.get("include_prompt"), True),
            include_response=_coerce_bool(audit_raw.get("include_response"), True),
        )
    else:
        audit = AuditConfig(
            backend=os.getenv("LLM_AUDIT_BACKEND", "jsonl"),
            path=os.getenv("LLM_AUDIT_PATH", "./audit.jsonl"),
            include_prompt=_coerce_bool(os.getenv("LLM_AUDIT_INCLUDE_PROMPT"), True),
            include_response=_coerce_bool(os.getenv("LLM_AUDIT_INCLUDE_RESPONSE"), True),
        )

    if not providers:
        raise ValueError(
            "No providers configured. Set LLM_PROVIDERS=local,claude and "
            "LLM_LOCAL_BASE_URL / LM_LOCAL_DEFAULT_MODEL, or pass a YAML config."
        )

    return CoreConfig(providers=providers, audit=audit)