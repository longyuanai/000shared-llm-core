# shared-llm-core

[![inspect](https://github.com/longyuanai/longyuanai/actions/workflows/inspect.yml/badge.svg?branch=main)](https://github.com/longyuanai/longyuanai/actions/workflows/inspect.yml)

> OpenAI-compatible LLM Gateway for the longyuanai AI Security Agent suite.
> Powers **AI-SOC-Agent**, **AI-Vulnerability-Agent**, **AI-Reverse-Agent**,
> **AI-Firmware-Security-Agent**, **AI-Agent-Security-Lab**, and the upgraded
> **AI-CodeGuard**.

> **v0.5 frozen — 2026-07-25.** See the
> [frozen contract](docs/v0.5-contract.md),
> [RFC-001](docs/rfcs/RFC-001-v0.5-freeze.md), and
> [final validation report](docs/releases/v0.5-final.md).

## Why this exists

Six agents, six stacks, one LLM call interface. Without a shared gateway we
end up rewriting the same retry loop, audit hook, and prompt template loader
in every project. This package is that gateway.

- **One protocol**: OpenAI-compatible `/v1/chat/completions` — works with
  OpenAI, Anthropic (via proxy), vLLM, Ollama, Qwen, DeepSeek.
- **Tier-based routing**: `CHEAP` → `STANDARD` → `PREMIUM` → `LOCAL` so each
  task pays for the quality it actually needs.
- **Prompt versioning**: templates live in `prompts/<name>/<version>.yml`,
  Jinja-rendered, registered by name.
- **Compliance-grade audit**: every call lands in `audit.jsonl` with prompt
  hash, response hash, tokens, latency.

## Install

```bash
poetry install
cp .env.example .env
```

## Run the demo (needs a live provider)

```bash
# Local vLLM (GPU required)
docker compose up -d vllm
poetry run python -m shared_llm_core.demo

# Claude via OpenAI-compatible proxy
export LLM_PROVIDERS=claude
export LLM_CLAUDE_BASE_URL=https://api.anthropic.com/v1
export LLM_CLAUDE_API_KEY=$ANTHROPIC_API_KEY
export LLM_CLAUDE_DEFAULT_MODEL=claude-sonnet-5-20250929
poetry run python -m shared_llm_core.demo
```

## Quick API

```python
from shared_llm_core import (
    ChatMessage, ChatRequest, LLMRouter, TemplateRegistry,
)
from shared_llm_core.router import TaskTier

registry = TemplateRegistry("./prompts")
messages = registry.get("hello", "v1").render(name="longyuanai")

with LLMRouter.from_env(yaml_path="./configs/default.yml") as router:
    resp = router.chat(
        TaskTier.STANDARD,
        ChatRequest(messages=messages, max_tokens=128),
    )
    print(resp.choices[0].message.content)
```

## Test

```bash
poetry run pytest -v
```

All tests use mocked HTTP — no real LLM call needed.

## Multi-repository compatibility CI

[`suite-lock.yml`](suite-lock.yml) records the exact repository commit and
install path for the IntegrationGateway and six product projects. The core is
fixed by the workflow's triggering SHA (`self` in the lock). The central
`suite-ci` workflow checks out that immutable set before installing or testing
anything, so an unrelated default-branch update cannot silently change the
compatibility result.

A product repository can validate a candidate commit with a `suite-ci`
`repository_dispatch` payload containing one of `integration_sha`, `soc_sha`,
`vulnerability_sha`, `lab_sha`, `code_sha`, `reverse_sha`, or `firmware_sha`.
Only dispatch runs may override a locked product commit; normal pushes, pull
requests, schedules, and manual runs use the lock unchanged.

## Repo layout

```
shared-llm-core/
├── src/shared_llm_core/
│   ├── client.py        # OpenAI-compatible chat client
│   ├── router.py        # Tier-based routing
│   ├── templates.py     # Versioned YAML prompt templates
│   ├── audit.py         # Append-only audit log
│   ├── config.py        # Env + YAML config loader
│   └── demo.py          # End-to-end smoke test
├── prompts/             # Versioned prompt templates
├── configs/             # Provider / audit YAML
├── tests/               # Pytest suite (mocked)
├── docker-compose.yml   # Local vLLM
└── pyproject.toml
```
