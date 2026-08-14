from __future__ import annotations

import re
import tomllib
from pathlib import Path

from shared_llm_core import __version__


ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def _package_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["poetry"]["version"]


def test_core_version_matches_contract() -> None:
    assert _package_version() == __version__ == "0.6.0"


def test_version_is_valid_semver() -> None:
    assert SEMVER.fullmatch(_package_version())
