# Codex 派活指令 · 005-INTEG · 新建 shared-integration 集成层

> **派活方**: Claude
> **接收方**: Codex
> **前提**: 005-CONTRACT 已完工 + 6 个产品 S3/S4 已完工(或部分完工)
> **优先级**: 🟢 Week 11

---

## ⚠️ 必读(开工前 Read 全部 4 个)

1. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md` §10 IntegrationGateway
2. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\src\shared_llm_core\__init__.py`
3. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\src\shared_llm_core\gateway.py`(参考实现)
4. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\7-PRODUCT-UNLOCK-ORDER.md`

---

## 工作目录

```
新建:E:\001项目\000开发\003AI+网络安全\000shared-integration
```

## Python 环境

- 解释器: `C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`
- 测试运行: `python -m pytest tests/ --basetemp=.pytest-tmp`
- 依赖: shared-llm-core v0.5 path dep

---

## 4 个 ISSUE(每个 1 个 commit)

### ISSUE 1 · 仓库初始化

仿照 `000shared-llm-core` 布局,新建:

```
000shared-integration/
├── pyproject.toml
├── README.md
├── src/
│   └── shared_integration/
│       ├── __init__.py
│       ├── gateway.py           # FastAPI 入口
│       ├── registry.py          # Finding in-memory store
│       ├── correlations.py      # 跨产品关联规则
│       └── adapters/
│           ├── __init__.py
│           ├── base.py          # ProductAdapter ABC
│           ├── soc.py           # 001 adapter
│           ├── vuln.py          # 002 adapter
│           ├── lab.py           # 003 adapter
│           ├── code.py          # 004 adapter
│           ├── reverse.py       # 005 adapter
│           └── firmware.py      # 006 adapter
└── tests/
    ├── conftest.py
    ├── test_registry.py
    ├── test_correlations.py
    └── test_adapters.py
```

**pyproject.toml**:

```toml
[tool.poetry]
name = "shared-integration"
version = "0.5.0"
description = "Integration gateway for longyuanai AI Security Agent suite"
authors = ["longyuanai"]
license = "MIT"

[tool.poetry.dependencies]
python = "^3.11"
shared-llm-core = {path = "../000shared-llm-core", develop = true}
fastapi = "^0.115.0"
uvicorn = "^0.30.0"
httpx = ">=0.27,<0.28"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2.0"
pytest-asyncio = "^0.23.7"
pytest-mock = "^3.14.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "--basetemp=.pytest-tmp"
```

---

### ISSUE 2 · FindingRegistry + 6 个 ProductAdapter

**src/shared_integration/registry.py**: 直接复用 shared-llm-core 的 `FindingRegistry`(从 v0.5 §10 导入)。

**src/shared_integration/adapters/base.py**:

```python
"""ProductAdapter ABC,定义统一接口。"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from shared_llm_core import Finding, FindingSource


class ProductAdapter(ABC):
    source: FindingSource

    @abstractmethod
    async def scan(self, payload: dict[str, Any]) -> AsyncIterator[Finding]:
        """通过 subprocess 调产品 CLI,不 deep import。"""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """健康检查 dict。"""
```

**6 个 adapter 示例**(`soc.py`):

```python
"""001 AI-SOC-Agent adapter。

通过 subprocess 调:
  python -m ai_soc_agent.cli --input <payload> --json

捕获 stdout JSON → 解析成 Finding 列表。
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

from shared_llm_core import Finding, FindingSource, FindingSeverity
from shared_integration.adapters.base import ProductAdapter


class SOCAdapter(ProductAdapter):
    source = FindingSource.SOC

    def __init__(self, cli_path: Path) -> None:
        self._cli = cli_path

    async def scan(self, payload: dict[str, Any]) -> AsyncIterator[Finding]:
        proc = await asyncio.create_subprocess_exec(
            "python", "-m", "ai_soc_agent.cli",
            "--input", json.dumps(payload),
            "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        for item in data.get("findings", []):
            yield Finding(
                id="",
                source=FindingSource.SOC,
                severity=FindingSeverity(item["severity"]),
                confidence=item.get("confidence", 0.5),
                title=item["title"],
                host=item.get("host"),
            )

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "source": "001-soc"}
```

**其他 5 个 adapter**(`vuln.py` / `lab.py` / `code.py` / `reverse.py` / `firmware.py`)结构相同,只需改 `source = FindingSource.VULN/LAB/CODE/REVERSE/FIRMWARE` 和 CLI 命令。

---

### ISSUE 3 · 跨产品 correlation 规则

**src/shared_integration/correlations.py**:

```python
"""跨产品关联规则:同 host + 24h 时间窗 + ≥ 2 个 Finding → 自动关联。"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Sequence

from shared_llm_core import (
    Finding, Correlation, CorrelationRule, FindingSeverity,
)


class SameHostMultiSourceRule(CorrelationRule):
    id = "integ-same-host-multi-source"

    def __init__(self, window: timedelta = timedelta(hours=24)) -> None:
        self._window = window

    def correlate(
        self,
        new_finding: Finding,
        existing: Sequence[Finding],
    ) -> list[Correlation]:
        if not new_finding.host:
            return []
        related = []
        for f in existing:
            if f.host != new_finding.host:
                continue
            if f.source == new_finding.source:
                continue
            if not _within_window(new_finding, f, self._window):
                continue
            related.append(f)
        if not related:
            return []
        return [Correlation(
            rule_id=self.id,
            findings=(new_finding.id, *(r.id for r in related)),
            severity=_max_severity([new_finding, *related]),
            narrative=f"Multi-source findings on {new_finding.host}: "
                      f"{new_finding.source.value} + {[r.source.value for r in related]}",
        )]


def _within_window(a: Finding, b: Finding, window: timedelta) -> bool:
    if not a.ts or not b.ts:
        return True  # 无时间戳视为相关
    return abs((a.ts - b.ts).total_seconds()) <= window.total_seconds()


def _max_severity(findings: Sequence[Finding]) -> FindingSeverity:
    order = [FindingSeverity.INFO, FindingSeverity.LOW, FindingSeverity.MEDIUM,
             FindingSeverity.HIGH, FindingSeverity.CRITICAL]
    return max(findings, key=lambda f: order.index(f.severity)).severity
```

---

### ISSUE 4 · IntegrationGateway FastAPI

**src/shared_integration/gateway.py**:

直接组合 shared-llm-core 的 `IntegrationGateway`:

```python
from fastapi import FastAPI
from shared_llm_core import (
    FindingRegistry, IntegrationGateway, FindingSource,
)

from shared_integration.adapters.soc import SOCAdapter
from shared_integration.adapters.vuln import VulnAdapter
from shared_integration.adapters.lab import LabAdapter
from shared_integration.adapters.code import CodeAdapter
from shared_integration.adapters.reverse import ReverseAdapter
from shared_integration.adapters.firmware import FirmwareAdapter
from shared_integration.correlations import SameHostMultiSourceRule


def build_gateway() -> IntegrationGateway:
    products = {
        FindingSource.SOC: SOCAdapter(Path("../001AI-SOC-Agent")),
        FindingSource.VULN: VulnAdapter(Path("../002AI-Vulnerability-Agent")),
        FindingSource.LAB: LabAdapter(Path("../003AI Agent安全靶场")),
        FindingSource.CODE: CodeAdapter(Path("../004AI-CodeGuard 升级/004AI-CodeGuard-upgrade")),
        FindingSource.REVERSE: ReverseAdapter(Path("../005AI逆向Agent")),
        FindingSource.FIRMWARE: FirmwareAdapter(Path("../006AI-Firmware-Security-Agent")),
    }
    return IntegrationGateway(
        products=products,
        registry=FindingRegistry(),
        correlations=[SameHostMultiSourceRule()],
    )


def main() -> None:
    gateway = build_gateway()
    gateway.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
```

---

## 测试要求(≥ 30 个 test function)

### tests/test_registry.py(≥ 5)

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_registry_import_from_shared_llm_core` | FindingRegistry 从 core 导入成功 |
| 2 | `test_registry_add_and_query` | add → query 找到 |
| 3 | `test_registry_query_by_source` | source 过滤 |
| 4 | `test_registry_query_by_severity` | severity 过滤 |
| 5 | `test_registry_max_size_eviction` | max_size LRU 淘汰 |

### tests/test_correlations.py(≥ 6)

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_same_host_correlation_triggers` | 2 findings 同 host 不同 source → 1 Correlation |
| 2 | `test_same_source_no_correlation` | 同 source → 不关联 |
| 3 | `test_different_hosts_no_correlation` | 不同 host → 不关联 |
| 4 | `test_window_exceeded_no_correlation` | 跨 30 天 > 24h → 不关联 |
| 5 | `test_no_host_no_correlation` | host=None → 不关联 |
| 6 | `test_correlation_severity_is_max` | correlation.severity = max of inputs |

### tests/test_adapters.py(每个 adapter ≥ 3,合计 ≥ 18)

每个 adapter 测:
- `test_{source}_adapter_health_returns_ok` — health() 返回 {"status": "ok"}
- `test_{source}_adapter_scan_parses_stdout` — scan() 调 subprocess,解析 Finding
- `test_{source}_adapter_scan_empty_findings` — 空 JSON → 0 Finding

**总计**: 5 + 6 + 18 = **29 个 test**,目标 ≥ 30(每个 adapter 加 1 个即可)。

---

## 验收硬约束

| # | 约束 | 验证 |
|---|------|------|
| 1 | **不修改任何产品目录** | git diff 检查 |
| 2 | 只用 v0.5 §10 contract 符号 | grep |
| 3 | adapter 通过 subprocess 隔离,不 deep import 跨产品 | code review |
| 4 | pyproject.toml path dep 指向 `../000shared-llm-core` | 文件验证 |
| 5 | ≥ 30 test function | pytest 计数 |
| 6 | 每个 ISSUE 1 个 commit | git log |

---

## 回报格式

```
1. 4 个 commit hash
2. pytest 最后 5 行(显示 ≥ 30 passed)
3. curl 调用样例:
   # Health
   curl http://localhost:8080/v0.5/health
   
   # Trigger 001 scan
   curl -X POST http://localhost:8080/v0.5/001/scan \
        -H "Content-Type: application/json" \
        -d '{"host":"192.168.1.1"}'
   
   # Query findings
   curl "http://localhost:8080/v0.5/findings?severity=high&limit=10"
   
   # SSE stream
   curl -N http://localhost:8080/v0.5/stream
4. 已知问题
```

---

## 预计工时

**4-5 天**