"""Tests for the template registry."""

from __future__ import annotations

from pathlib import Path

import pytest
from jinja2 import UndefinedError

from shared_llm_core.templates import PromptTemplate, TemplateRegistry


@pytest.fixture
def prompts_root(tmp_path: Path) -> Path:
    (tmp_path / "greet").mkdir()
    (tmp_path / "greet" / "v1.yml").write_text(
        "system: Be brief.\nuser: Say hi to {{ name }}.\n",
        encoding="utf-8",
    )
    (tmp_path / "greet" / "v2.yml").write_text(
        "description: shorter\nsystem: |-\n  You are terse.\nuser: Hi {{ name }}.\n",
        encoding="utf-8",
    )
    (tmp_path / "report").mkdir()
    (tmp_path / "report" / "v1.yml").write_text(
        "user: |-\n  Summarize:\n  {{ body }}\n",
        encoding="utf-8",
    )
    return tmp_path


def test_get_specific_version(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    tpl = reg.get("greet", "v1")
    assert isinstance(tpl, PromptTemplate)
    msgs = tpl.render(name="alice")
    assert msgs[0].role == "system"
    assert msgs[0].content == "Be brief."
    assert msgs[1].role == "user"
    assert msgs[1].content == "Say hi to alice."


def test_get_latest_returns_highest_version(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    tpl = reg.get("greet", "latest")
    assert tpl.version == "v2"
    assert "terse" in tpl.system
    msgs = tpl.render(name="bob")
    assert msgs[1].content == "Hi bob."


def test_missing_template_raises(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    with pytest.raises(FileNotFoundError):
        reg.get("nope", "v1")


def test_missing_template_directory_raises_when_latest_is_requested(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Template directory not found"):
        TemplateRegistry(tmp_path).get("nope")


def test_missing_version_raises(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    with pytest.raises(FileNotFoundError):
        reg.get("greet", "v9")


def test_empty_template_directory_raises(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(FileNotFoundError, match="No versions found"):
        TemplateRegistry(tmp_path).get("empty")


def test_strict_jinja_raises_on_undefined_var(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    tpl = reg.get("report", "v1")
    with pytest.raises(UndefinedError):
        tpl.render()  # body missing


def test_cache_returns_same_instance(prompts_root: Path) -> None:
    reg = TemplateRegistry(prompts_root)
    assert reg.get("greet", "v1") is reg.get("greet", "v1")
