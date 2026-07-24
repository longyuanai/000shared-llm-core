"""Prompt templates and a versioned registry.

Templates live in YAML files inside the `prompts/` directory, each tagged with
a semantic version. The registry resolves `name@version` → rendered string.
The point is to keep prompts out of code so they can be reviewed and rolled
back without a redeploy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined, select_autoescape

from shared_llm_core.client import ChatMessage


@dataclass(frozen=True)
class PromptTemplate:
    """One versioned prompt template."""

    name: str
    version: str
    system: str
    user: str
    description: str = ""

    def render(self, **vars: Any) -> list[ChatMessage]:
        env = Environment(undefined=StrictUndefined, autoescape=select_autoescape())
        messages: list[ChatMessage] = []
        if self.system:
            messages.append(ChatMessage(role="system", content=env.from_string(self.system).render(**vars)))
        messages.append(ChatMessage(role="user", content=env.from_string(self.user).render(**vars)))
        return messages


class TemplateRegistry:
    """Loads templates from a directory tree: `prompts/<name>/<version>.yml`."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self._cache: dict[tuple[str, str], PromptTemplate] = {}

    def get(self, name: str, version: str = "latest") -> PromptTemplate:
        if version == "latest":
            version = self._latest_version(name)
        key = (name, version)
        if key not in self._cache:
            self._cache[key] = self._load(name, version)
        return self._cache[key]

    def _latest_version(self, name: str) -> str:
        d = self.root / name
        if not d.is_dir():
            raise FileNotFoundError(f"Template directory not found: {d}")
        versions = sorted(p.stem for p in d.glob("*.yml"))
        if not versions:
            raise FileNotFoundError(f"No versions found for template {name!r}")
        return versions[-1]

    def _load(self, name: str, version: str) -> PromptTemplate:
        path = self.root / name / f"{version}.yml"
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return PromptTemplate(
            name=name,
            version=version,
            system=raw.get("system", ""),
            user=raw["user"],
            description=raw.get("description", ""),
        )