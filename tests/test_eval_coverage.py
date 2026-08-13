from __future__ import annotations

import ast
import configparser
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

CORE_ROOT = Path(__file__).resolve().parents[1]
NON_PRODUCT_KEYS = frozenset({"core", "integration", "web_ui"})
EVAL_GATE_EXEMPTIONS: dict[str, dict[str, str]] = {
    "lab": {
        "reason": (
            "003 is pinned at suite-lock HEAD 3862acf and has protected local "
            "changes; its attack-detection and judge outputs also need a "
            "product-specific evaluation schema."
        ),
        "followup": "012",
    }
}


def _read_suite_lock(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    repositories = payload.get("repositories")
    if not isinstance(repositories, list):
        raise AssertionError("suite-lock.yml must contain a repositories list")
    return payload


def _suite_root() -> Path:
    configured = os.getenv("SUITE_DIR")
    return Path(configured).resolve() if configured else CORE_ROOT.parent


def _product_entries(lock: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    repositories = lock.get("repositories", [])
    return [
        entry
        for entry in repositories
        if isinstance(entry, Mapping) and entry.get("key") not in NON_PRODUCT_KEYS
    ]


def _validate_exemptions(
    entries: list[Mapping[str, Any]],
    exemptions: Mapping[str, Mapping[str, str]],
) -> None:
    known_keys = {entry.get("key") for entry in entries}
    unknown = sorted(set(exemptions) - known_keys)
    if unknown:
        raise AssertionError(f"eval-gate exemptions reference unknown repositories: {unknown}")
    for key, exemption in exemptions.items():
        reason = exemption.get("reason", "").strip()
        followup = exemption.get("followup", "").strip()
        if not reason or not followup:
            raise AssertionError(
                f"eval-gate exemption {key!r} requires both reason and followup"
            )


def _resolve_product_root(suite_root: Path, entry: Mapping[str, Any]) -> Path | None:
    relative = entry.get("path")
    if not isinstance(relative, str) or not relative:
        raise AssertionError(f"suite-lock repository has invalid path: {entry!r}")
    candidate = suite_root / relative
    if not candidate.is_dir():
        return None
    if (candidate / "src").is_dir():
        return candidate

    # The Windows development workspace stores 004 inside a container folder,
    # while suite CI checks the same repository out directly at its lock path.
    nested = [
        child
        for child in candidate.iterdir()
        if child.is_dir() and (child / "src").is_dir() and (child / "tests").is_dir()
    ]
    if len(nested) == 1:
        return nested[0]
    repository = entry.get("repository")
    if isinstance(repository, str):
        expected_name = repository.rstrip("/").removesuffix(".git").split("/")[-1]
        matching = [child for child in nested if _git_origin_name(child) == expected_name]
        if len(matching) == 1:
            return matching[0]
    raise AssertionError(f"could not resolve one product root beneath {candidate}")


def _git_origin_name(repository_root: Path) -> str | None:
    config_path = repository_root / ".git" / "config"
    if not config_path.is_file():
        return None
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    url = parser.get('remote "origin"', "url", fallback="")
    if not url:
        return None
    return url.rstrip("/").removesuffix(".git").split("/")[-1]


def _python_imports_llm_router(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(
            alias.name == "LLMRouter" for alias in node.names
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name.endswith("LLMRouter") for alias in node.names
        ):
            return True
    return False


def _imports_llm_router(product_root: Path) -> bool:
    source_root = product_root / "src"
    for path in source_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".py" and _python_imports_llm_router(path):
            return True
        if path.suffix in {".ts", ".tsx"} and "LLMRouter" in path.read_text(
            encoding="utf-8"
        ):
            return True
    return False


def test_every_llm_product_has_an_eval_gate_or_exemption() -> None:
    suite_root = _suite_root()
    lock = _read_suite_lock(CORE_ROOT / "suite-lock.yml")
    entries = _product_entries(lock)
    _validate_exemptions(entries, EVAL_GATE_EXEMPTIONS)

    for entry in entries:
        product_root = _resolve_product_root(suite_root, entry)
        if product_root is None:
            pytest.skip(
                f"suite repository {entry.get('key')!r} is not checked out at "
                f"{suite_root / str(entry.get('path'))}"
            )
        if not _imports_llm_router(product_root):
            continue
        key = str(entry.get("key"))
        if key in EVAL_GATE_EXEMPTIONS:
            continue
        gate = product_root / "tests" / "test_eval_gate.py"
        fixtures = product_root / "evals" / "fixtures"
        assert gate.is_file(), f"{key}: missing tests/test_eval_gate.py"
        fixture_count = len(list(fixtures.glob("*.json"))) if fixtures.is_dir() else 0
        assert fixture_count >= 6, f"{key}: expected >= 6 eval fixtures, got {fixture_count}"


def test_coverage_guard_reads_suite_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "suite-lock.yml"
    lock_path.write_text(
        json.dumps({"repositories": [{"key": "sentinel", "path": "sentinel"}]}),
        encoding="utf-8",
    )

    lock = _read_suite_lock(lock_path)

    assert lock["repositories"][0]["key"] == "sentinel"


def test_every_exemption_has_reason_and_followup() -> None:
    lock = _read_suite_lock(CORE_ROOT / "suite-lock.yml")
    entries = _product_entries(lock)
    _validate_exemptions(entries, EVAL_GATE_EXEMPTIONS)

    for missing_field in ("reason", "followup"):
        incomplete = {
            key: {field: value for field, value in exemption.items() if field != missing_field}
            for key, exemption in EVAL_GATE_EXEMPTIONS.items()
        }
        with pytest.raises(AssertionError, match="requires both reason and followup"):
            _validate_exemptions(entries, incomplete)


def test_exemption_for_unknown_repo_is_rejected() -> None:
    lock = _read_suite_lock(CORE_ROOT / "suite-lock.yml")
    exemptions = {
        **EVAL_GATE_EXEMPTIONS,
        "removed-product": {"reason": "stale exemption", "followup": "012"},
    }

    with pytest.raises(AssertionError, match="unknown repositories"):
        _validate_exemptions(_product_entries(lock), exemptions)
