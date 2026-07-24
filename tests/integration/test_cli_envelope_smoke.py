"""Cross-repository smoke tests for the frozen §15 CLI envelope contract.

These tests execute the six real product CLIs in subprocesses. They intentionally
exercise repository boundaries instead of importing product internals.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

CORE_ROOT = Path(__file__).resolve().parents[2]
SUITE_ROOT = CORE_ROOT.parent


@dataclass(frozen=True)
class ProductCase:
    source: str
    repository: Path
    module: str
    payload: dict[str, Any]
    extra_pythonpath: tuple[Path, ...] = ()


CASES = (
    ProductCase(
        source="001",
        repository=SUITE_ROOT / "001AI-SOC-Agent",
        module="ai_soc_agent.cli",
        payload={
            "source": "sshd",
            "events": [
                {
                    "ts": "2026-07-24T10:00:00Z",
                    "user": "root",
                    "src_ip": "1.2.3.4",
                    "event": "Failed password",
                }
            ],
        },
    ),
    ProductCase(
        source="002",
        repository=SUITE_ROOT / "002AI-Vulnerability-Agent",
        module="ai_vuln_agent.cli",
        payload={
            "scanner": "qualys",
            "csv_content": "IP,CVE,Severity\n10.0.0.1,CVE-2024-1234,High",
        },
    ),
    ProductCase(
        source="003",
        repository=SUITE_ROOT / "003AI Agent安全靶场",
        module="ai_agent_lab.cli",
        payload={
            "agent": "echo_agent",
            "attack": "indirect_injection",
            "iterations": 1,
        },
    ),
    ProductCase(
        source="004",
        repository=SUITE_ROOT / "004AI代码审计" / "004AI-CodeGuard-upgrade",
        module="codeguard.cli",
        payload={"repo_path": ".", "languages": ["python"]},
        extra_pythonpath=(
            SUITE_ROOT / "004AI代码审计" / "004AI-CodeGuard-upgrade" / ".python-deps",
        ),
    ),
    ProductCase(
        source="005",
        repository=SUITE_ROOT / "005AI逆向Agent",
        module="ai_reverse_agent.cli",
        payload={
            "binary_path": "samples/mini_binaries/mini_x64_pe.exe",
            "arch": "x64",
        },
    ),
    ProductCase(
        source="006",
        repository=SUITE_ROOT / "006AI-Firmware-Security-Agent",
        module="ai_firmware_agent.cli",
        payload={"firmware_path": "tests/fixtures/sample.bin"},
    ),
)


def _pythonpath(case: ProductCase) -> str:
    paths = [
        case.repository / "src",
        *case.extra_pythonpath,
        CORE_ROOT / "src",
    ]
    current = os.environ.get("PYTHONPATH")
    if current:
        paths.extend(Path(part) for part in current.split(os.pathsep) if part)
    return os.pathsep.join(str(path) for path in paths)


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.source)
def test_product_cli_emits_valid_envelope(case: ProductCase) -> None:
    if not case.repository.is_dir():
        pytest.skip(f"sibling product repository not available: {case.repository}")

    process = subprocess.run(
        [
            sys.executable,
            "-m",
            case.module,
            "scan",
            "--input",
            json.dumps(case.payload, ensure_ascii=False),
            "--json",
        ],
        cwd=case.repository,
        env={**os.environ, "PYTHONPATH": _pythonpath(case)},
        capture_output=True,
        timeout=120,
        check=False,
    )

    stdout = process.stdout.decode("utf-8", errors="replace").strip()
    stderr = process.stderr.decode("utf-8", errors="replace").strip()
    assert process.returncode == 0, stderr[-1000:]
    assert stdout, f"{case.source} emitted empty stdout; stderr={stderr[-500:]}"

    envelope = json.loads(stdout)
    findings = envelope.get("findings") if isinstance(envelope, dict) else envelope
    assert isinstance(findings, list)
    for finding in findings:
        assert isinstance(finding, dict)
        assert finding.get("source", case.source) == case.source
        assert isinstance(finding.get("title"), str)
        assert finding.get("severity") in {"info", "low", "medium", "high", "critical"}
        assert 0.0 <= float(finding.get("confidence", 0.5)) <= 1.0

