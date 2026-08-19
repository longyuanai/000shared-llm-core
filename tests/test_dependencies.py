"""Keep declared runtime dependencies aligned with source imports."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
IMPORT_NAMES = {
    "python-dotenv": "dotenv",
    "pyyaml": "yaml",
}


def _source_imports() -> set[str]:
    imported: set[str] = set()
    for source in SOURCE_ROOT.rglob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "import_module"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                imported.add(node.args[0].value.split(".")[0])
    return imported


def test_declared_dependencies_are_used() -> None:
    configuration: dict[str, Any] = tomllib.loads(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies: dict[str, Any] = configuration["tool"]["poetry"]["dependencies"]
    runtime_dependencies = {
        name
        for name, declaration in dependencies.items()
        if name != "python"
        and not (isinstance(declaration, dict) and declaration.get("optional") is True)
    }
    imported = _source_imports()
    missing = {
        dependency: IMPORT_NAMES.get(dependency, dependency.replace("-", "_"))
        for dependency in sorted(runtime_dependencies)
        if IMPORT_NAMES.get(dependency, dependency.replace("-", "_")) not in imported
    }

    assert missing == {}, f"declared runtime dependencies without source imports: {missing}"
