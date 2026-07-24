# Codex 派活指令 · 005-CONTRACT · v0.5 §7-§10 实现 + 冻结

> **派活方**: Claude(派活审计)
> **接收方**: Codex(执行)
> **派活日期**: 2026-07-24
> **优先级**: 🔴 **硬阻塞** — 6 个产品 v0.5 升级全部等这个完工

---

## ⚠️ 背景(必读)

`000shared-llm-core` 当前是 **v0.1.0**:
- `__version__ = "0.1.0"`
- `src/shared_llm_core/` 只有 6 个文件:`__init__.py / audit.py / client.py / config.py / demo.py / router.py / templates.py`(共 7 个 .py,1 个 `__init__`)
- v0.5 设计的 §7-§10(**MultiAgentOrchestrator / RuleEngine / Finding / IntegrationGateway**)只有设计文档,实现代码 0 行

**下游 6 个产品 v0.5 升级派活指令已就位**,全部需要 `from shared_llm_core import RuleEngine, Finding, ...` —— 这些符号不存在,派活无法开工。

**本任务产出**: `__version__ = "0.5.0"` + §7-§10 完整实现 + 测试全过 = 冻结,解锁 6 个产品并行升级。

---

## 必读文档(开工前 Read 全部 5 个)

1. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.1-contract.md` — §1-§6 冻结,**你不能动现有任何符号 / 字段 / 方法签名**
2. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\docs\v0.5-contract.md` — §7-§10 设计,你**严格按 schema 实现**
3. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\src\shared_llm_core\__init__.py` — **append-only**,保留所有 v0.1 现有导出
4. `E:\001项目\000开发\003AI+网络安全\000shared-llm-core\pyproject.toml` — 加 `fastapi`, `uvicorn`, `httpx>=0.27,<0.28` 依赖
5. `E:\001项目\000开发\003AI+网络安全\AUDIT\CONTRACT-COMPLIANCE.md` — 看 v0.1 当前合规基线

---

## 工作目录

```
E:\001项目\000开发\003AI+网络安全\000shared-llm-core
```

---

## Python 环境

- **解释器**: `C:\Users\15072\AppData\Local\Programs\Python\Python314\python.exe`(已实测,可用)
- **包管理器**: poetry(项目已有 `pyproject.toml`)
- **测试运行**: `python -m pytest tests/ --basetemp=.pytest-tmp`
- **当前基线**: **24 passed**(v0.1 测试,Codex 必须保证这 24 个仍全过)

---

## 4 个 ISSUE(每个 1 个 commit,顺序执行)

### ISSUE 1 · §7 MultiAgentOrchestrator

**新建** `src/shared_llm_core/multi_agent.py`:

```python
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence
from shared_llm_core.router import LLMRouter, TaskTier


class AgentRole(str, Enum):
    SCOUT = "scout"
    ANALYST = "analyst"
    EXPLOITER = "exploiter"
    SYNTHESIZER = "synthesizer"
    REVIEWER = "reviewer"


@dataclass(frozen=True)
class MissionContext:
    task: str
    inputs: Mapping[str, Any]
    scratchpad: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AgentResult:
    role: AgentRole
    output: str
    findings: tuple["Finding", ...] = ()  # forward ref,见 §9
    latency_ms: int = 0
    error: str | None = None


class MultiAgentOrchestrator:
    def __init__(
        self,
        router: LLMRouter,
        *,
        max_concurrency: int = 4,
        scratchpad_size: int = 4096,
    ) -> None:
        self._router = router
        self._max_concurrency = max_concurrency
        self._scratchpad_size = scratchpad_size

    def run(
        self,
        mission: MissionContext,
        roles: Sequence[AgentRole],
    ) -> list[AgentResult]:
        """顺序调度 agents(每个 role 跑一次,scratchpad 累积)。

        - 第 1 个 agent: inputs=mission.inputs, scratchpad=mission.scratchpad
        - 后续 agent: inputs 包含前面所有 AgentResult.output 拼成的临时 scratchpad
        - SYNTHESIZER 通常放最后,collect 所有结果
        - 任一 agent 失败 → AgentResult.error 不为空,**不** raise(整体 mission 继续)
        """
```

**行为契约**:
- 默认顺序执行(简化版,ThreadPool 可选 `parallel=True` 参数,但 v0.5 不强制)
- scratchpad 是 tuple(append-only),任何 agent 写入触发副本
- agent 失败 → `AgentResult.error` 不为空,整体不抛
- `latency_ms` 含 LLM 调用 + 解析 + scratchpad 写入(用 `time.monotonic()`)

**新建** `tests/test_multi_agent.py`,**≥ 10 个 test function**:

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_agent_role_enum_values` | 5 个 role 值正确 |
| 2 | `test_mission_context_required_fields` | task/inputs 必填 |
| 3 | `test_mission_context_default_scratchpad_empty` | scratchpad 默认 `()` |
| 4 | `test_mission_context_immutable` | frozen=True,改字段抛 FrozenInstanceError |
| 5 | `test_agent_result_required_fields` | role/output 必填 |
| 6 | `test_agent_result_default_error_none` | error 默认 None |
| 7 | `test_orchestrator_single_agent_runs` | 1 个 role → 1 个 AgentResult |
| 8 | `test_orchestrator_multiple_agents_sequential` | 3 个 role → 3 个 AgentResult,顺序正确 |
| 9 | `test_scratchpad_appended_across_agents` | role 2 看到 role 1 输出在 scratchpad |
| 10 | `test_agent_failure_does_not_raise` | router.chat 抛异常 → AgentResult.error 非空,run 不抛 |
| 11 | `test_latency_recorded_positive` | latency_ms > 0 |

---

### ISSUE 2 · §8 RuleEngine

**新建** `src/shared_llm_core/rule_engine.py`:

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Mapping, Sequence
import sys
import uuid

from shared_llm_core.finding import Finding  # forward ref,见 §9


class Rule(ABC):
    id: str  # 子类必须定义为类属性
    severity_hint: Literal["low", "medium", "high", "critical"] = "medium"

    @abstractmethod
    def evaluate(self, ctx: "RuleContext") -> list[Finding]: ...

    def __repr__(self) -> str:
        return f"Rule({self.id})"


@dataclass(frozen=True)
class RuleContext:
    subject: str
    facts: Mapping[str, Any]
    window: tuple[datetime, datetime] | None = None
    related: tuple[Finding, ...] = ()


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[str, Rule] = {}

    def register(self, rule: Rule) -> None:
        if not rule.id:
            raise ValueError("Rule.id must be non-empty")
        if rule.id in self._rules:
            raise ValueError(f"Rule {rule.id} already registered")
        self._rules[rule.id] = rule

    def get(self, rule_id: str) -> Rule:
        if rule_id not in self._rules:
            raise KeyError(f"Rule {rule_id} not found")
        return self._rules[rule_id]

    def all(self) -> list[Rule]:
        return list(self._rules.values())

    @classmethod
    def default(cls) -> "RuleRegistry":
        from shared_llm_core.rules.builtin import BruteForceRule, KnownCVERule
        reg = cls()
        reg.register(BruteForceRule())
        reg.register(KnownCVERule())
        return reg


class RuleEngine:
    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self._registry = registry or RuleRegistry.default()

    def evaluate(
        self,
        ctx: RuleContext,
        *,
        rule_ids: Sequence[str] | None = None,
    ) -> list[Finding]:
        """跑全部(或指定)规则,返回所有 Finding。

        规则失败 → 跳过该规则,stderr warning,不 raise
        """
        target_rules = (
            [self._registry.get(rid) for rid in rule_ids] if rule_ids else self._registry.all()
        )
        results: list[Finding] = []
        for rule in target_rules:
            try:
                findings = rule.evaluate(ctx)
                results.extend(findings)
            except Exception as e:
                print(f"[rule_engine] rule {rule.id} failed: {e}", file=sys.stderr)
        return results
```

**新建** `src/shared_llm_core/rules/__init__.py`:

```python
from shared_llm_core.rules.builtin import BruteForceRule, KnownCVERule
__all__ = ["BruteForceRule", "KnownCVERule"]
```

**新建** `src/shared_llm_core/rules/builtin.py`:

```python
from __future__ import annotations
from typing import Any
from shared_llm_core.finding import Finding, FindingSource, FindingSeverity
from shared_llm_core.rule_engine import Rule, RuleContext


class BruteForceRule(Rule):
    id = "core-brute-force"
    severity_hint = "high"

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        failed = ctx.facts.get("failed_logins", 0)
        if not isinstance(failed, int) or failed <= 5:
            return []
        return [Finding(
            id="",  # auto-gen
            source=FindingSource.EXTERNAL,
            severity=FindingSeverity.HIGH,
            confidence=min(1.0, failed / 20.0),
            title=f"Brute force detected on {ctx.subject}",
            host=ctx.subject,
            evidence=(f"failed_logins={failed}",),
            tags=frozenset(["brute-force", "auth"]),
        )]


class KnownCVERule(Rule):
    id = "core-known-cve"
    severity_hint = "critical"

    # Demo only - real impl 接 NVD
    _KNOWN_VULN_VERSIONS = {"openssh-7.0", "apache-2.2.0", "nginx-0.6.0"}

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        version = ctx.facts.get("version", "")
        if version not in self._KNOWN_VULN_VERSIONS:
            return []
        return [Finding(
            id="",
            source=FindingSource.EXTERNAL,
            severity=FindingSeverity.CRITICAL,
            confidence=0.9,
            title=f"Known vulnerable version: {version}",
            host=ctx.subject,
            evidence=(f"version={version}",),
            tags=frozenset(["known-cve"]),
        )]
```

**新建** `tests/test_rule_engine.py`,**≥ 8 个 test function**:

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_rule_abstract_cannot_instantiate` | Rule(...) 直接抛 TypeError |
| 2 | `test_rule_registry_register_and_get` | register + get 往返 |
| 3 | `test_rule_registry_duplicate_raises` | 同 id 重复注册 ValueError |
| 4 | `test_rule_registry_default_has_builtins` | default() 含 BruteForceRule + KnownCVERule |
| 5 | `test_rule_engine_evaluate_all` | RuleContext → findings |
| 6 | `test_rule_engine_evaluate_subset_by_ids` | rule_ids=["core-brute-force"] 只跑该规则 |
| 7 | `test_rule_engine_silent_on_rule_failure` | rule.evaluate 抛异常 → engine 不抛,stderr 有 warn |
| 8 | `test_brute_force_rule_threshold` | failed_logins=3 不触发,=6 触发 |
| 9 | `test_known_cve_rule_match` | version="openssh-7.0" 触发 |

---

### ISSUE 3 · §9 Finding 统一 schema

**新建** `src/shared_llm_core/finding.py`:

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Mapping


class FindingSource(str, Enum):
    SOC = "001"
    VULN = "002"
    LAB = "003"
    CODE = "004"
    REVERSE = "005"
    FIRMWARE = "006"
    EXTERNAL = "external"


class FindingSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Finding:
    id: str
    source: FindingSource
    severity: FindingSeverity
    confidence: float
    title: str
    description: str = ""
    host: str | None = None
    cve: str | None = None
    ts: datetime | None = None
    evidence: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence}")
        if not self.id:
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        """稳定字段顺序(按 dataclass 字段定义顺序)"""
        d = asdict(self)
        d["source"] = self.source.value
        d["severity"] = self.severity.value
        if self.ts is not None:
            d["ts"] = self.ts.isoformat()
        # frozenset/tuple → list(可 JSON)
        d["evidence"] = list(self.evidence)
        d["related"] = list(self.related)
        d["tags"] = sorted(self.tags)
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Finding":
        """容忍未知字段(忽略,不抛错)"""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in known}
        # 类型还原
        if "source" in clean and isinstance(clean["source"], str):
            clean["source"] = FindingSource(clean["source"])
        if "severity" in clean and isinstance(clean["severity"], str):
            clean["severity"] = FindingSeverity(clean["severity"])
        if "ts" in clean and isinstance(clean["ts"], str):
            clean["ts"] = datetime.fromisoformat(clean["ts"])
        if "evidence" in clean:
            clean["evidence"] = tuple(clean["evidence"])
        if "related" in clean:
            clean["related"] = tuple(clean["related"])
        if "tags" in clean:
            clean["tags"] = frozenset(clean["tags"])
        return cls(**clean)
```

**新建** `tests/test_finding.py`,**≥ 8 个 test function**:

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_finding_source_enum_values` | 7 个 source 值正确 |
| 2 | `test_finding_severity_enum_values` | 5 个 severity 值正确 |
| 3 | `test_finding_required_fields` | 必填字段校验 |
| 4 | `test_finding_confidence_too_low_raises` | confidence=-0.1 → ValueError |
| 5 | `test_finding_confidence_too_high_raises` | confidence=1.1 → ValueError |
| 6 | `test_finding_uuid_auto_generated_when_empty` | id="" → 自动 UUID4 非空 |
| 7 | `test_finding_to_dict_stable_field_order` | dict 键顺序 = dataclass 字段顺序 |
| 8 | `test_finding_from_dict_ignores_unknown_fields` | 多余字段被丢弃,不抛错 |
| 9 | `test_finding_roundtrip_via_dict` | to_dict → from_dict → 等值 |
| 10 | `test_finding_immutable` | frozen=True,改字段抛 FrozenInstanceError |

---

### ISSUE 4 · §10 IntegrationGateway(核心)

**新建** `src/shared_llm_core/gateway.py`:

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Mapping, Sequence
import asyncio
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from shared_llm_core.finding import Finding, FindingSource, FindingSeverity


class FindingRegistry:
    """进程内内存版 Finding 注册表(v0.5),v1.0 才上 DB"""

    def __init__(self, *, max_size: int = 100_000) -> None:
        self._findings: deque[Finding] = deque(maxlen=max_size)
        self._subscribers: list[asyncio.Queue[Finding]] = []
        self._lock = asyncio.Lock()

    async def add(self, finding: Finding) -> None:
        async with self._lock:
            self._findings.append(finding)
            # 推给所有订阅者(非阻塞,满了就丢)
            for q in self._subscribers:
                try:
                    q.put_nowait(finding)
                except asyncio.QueueFull:
                    pass

    def query(
        self,
        *,
        source: FindingSource | None = None,
        severity: FindingSeverity | None = None,
        host: str | None = None,
        cve: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[Finding]:
        results: list[Finding] = []
        for f in reversed(self._findings):  # 最新的优先
            if source is not None and f.source != source:
                continue
            if severity is not None and f.severity != severity:
                continue
            if host is not None and f.host != host:
                continue
            if cve is not None and f.cve != cve:
                continue
            if since is not None and f.ts is not None and f.ts < since:
                continue
            results.append(f)
            if len(results) >= limit:
                break
        return results

    async def subscribe(self) -> AsyncIterator[Finding]:
        q: asyncio.Queue[Finding] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                finding = await q.get()
                yield finding
        finally:
            async with self._lock:
                self._subscribers.remove(q)


@dataclass(frozen=True)
class Correlation:
    rule_id: str
    findings: tuple[str, ...]
    severity: FindingSeverity
    narrative: str


class CorrelationRule(ABC):
    id: str

    @abstractmethod
    def correlate(
        self,
        new_finding: Finding,
        existing: Sequence[Finding],
    ) -> list[Correlation]: ...


class ProductAdapter(ABC):
    source: FindingSource

    @abstractmethod
    async def scan(self, payload: dict[str, Any]) -> AsyncIterator[Finding]: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...


class IntegrationGateway:
    def __init__(
        self,
        *,
        products: Mapping[FindingSource, ProductAdapter],
        registry: FindingRegistry | None = None,
        correlations: Sequence[CorrelationRule] = (),
    ) -> None:
        self._products = products
        self._registry = registry or FindingRegistry()
        self._correlations = list(correlations)

    @property
    def app(self) -> FastAPI:
        app = FastAPI(title="shared-llm-core IntegrationGateway v0.5")

        @app.get("/v0.5/health")
        async def health():
            return {
                "status": "ok",
                "version": "0.5.0",
                "products": list(self._products.keys()),
                "findings_count": len(self._registry._findings),
            }

        @app.get("/v0.5/findings")
        async def list_findings(
            source: str | None = Query(None),
            severity: str | None = Query(None),
            host: str | None = Query(None),
            cve: str | None = Query(None),
            limit: int = Query(100, ge=1, le=1000),
        ):
            src = FindingSource(source) if source else None
            sev = FindingSeverity(severity) if severity else None
            findings = self._registry.query(
                source=src, severity=sev, host=host, cve=cve, limit=limit
            )
            return {"findings": [f.to_dict() for f in findings], "count": len(findings)}

        @app.post("/v0.5/{source}/scan")
        async def scan(source: str, payload: dict[str, Any]):
            try:
                src_enum = FindingSource(source)
            except ValueError:
                raise HTTPException(404, f"unknown source {source}")
            if src_enum not in self._products:
                raise HTTPException(404, f"product {source} not registered")
            adapter = self._products[src_enum]
            collected: list[Finding] = []
            async for finding in adapter.scan(payload):
                await self._registry.add(finding)
                collected.append(finding)
            return {"source": source, "count": len(collected), "findings": [f.to_dict() for f in collected]}

        @app.get("/v0.5/stream")
        async def stream():
            async def event_gen():
                async for finding in self._registry.subscribe():
                    yield f"data: {json.dumps(finding.to_dict())}\n\n"
            return StreamingResponse(event_gen(), media_type="text/event-stream")

        return app

    def run(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
```

**新建** `tests/test_gateway.py`,**≥ 10 个 test function**:

| # | test 名 | 验证 |
|---|---------|------|
| 1 | `test_finding_registry_add_and_query` | add → query 找到 |
| 2 | `test_finding_registry_query_by_source` | source 过滤 |
| 3 | `test_finding_registry_query_by_severity` | severity 过滤 |
| 4 | `test_finding_registry_query_by_host` | host 过滤 |
| 5 | `test_finding_registry_max_size_eviction` | max_size=3,加 5 个,只剩最新 3 个 |
| 6 | `test_correlation_rule_abstract` | CorrelationRule(...) 直接抛 TypeError |
| 7 | `test_product_adapter_abstract` | ProductAdapter(...) 直接抛 TypeError |
| 8 | `test_gateway_health_endpoint` | httpx.AsyncClient → /v0.5/health 200 |
| 9 | `test_gateway_findings_endpoint` | /v0.5/findings 返回 list |
| 10 | `test_gateway_scan_endpoint` | /v0.5/{EXTERNAL}/scan 注册 finding |
| 11 | `test_gateway_scan_unknown_source_404` | 不存在 source → 404 |
| 12 | `test_gateway_stream_sse_format` | /v0.5/stream media_type=text/event-stream |

**测试示例**(`test_gateway.py` 顶部 fixtures):

```python
import pytest
from httpx import ASGITransport, AsyncClient

from shared_llm_core.finding import Finding, FindingSource, FindingSeverity
from shared_llm_core.gateway import FindingRegistry, IntegrationGateway, ProductAdapter


class FakeProduct(ProductAdapter):
    source = FindingSource.EXTERNAL

    async def scan(self, payload):
        for i in range(2):
            yield Finding(
                id="", source=FindingSource.EXTERNAL,
                severity=FindingSeverity.MEDIUM, confidence=0.5,
                title=f"fake-{i}", host=payload.get("host", "x"),
            )

    def health(self):
        return {"status": "ok"}


@pytest.fixture
def gateway():
    return IntegrationGateway(products={FindingSource.EXTERNAL: FakeProduct()})


@pytest.fixture
async def client(gateway):
    async with AsyncClient(
        transport=ASGITransport(app=gateway.app),
        base_url="http://test",
    ) as c:
        yield c
```

---

## 最后:更新 `src/shared_llm_core/__init__.py`

**append-only**,在现有 12 个 v0.1 导出之后追加 v0.5 符号。最终内容:

```python
"""shared-llm-core: OpenAI-compatible LLM Gateway for the longyuanai agent suite."""

# v0.1 (existing - DO NOT MODIFY)
from shared_llm_core.audit import AuditLog, AuditRecord
from shared_llm_core.client import (
    ChatChoice,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatUsage,
    LLMClient,
)
from shared_llm_core.router import LLMRouter, RouteRule, TaskTier
from shared_llm_core.templates import PromptTemplate, TemplateRegistry

# v0.5 (new)
from shared_llm_core.finding import Finding, FindingSeverity, FindingSource
from shared_llm_core.gateway import (
    Correlation,
    CorrelationRule,
    FindingRegistry,
    IntegrationGateway,
    ProductAdapter,
)
from shared_llm_core.multi_agent import (
    AgentResult,
    AgentRole,
    MissionContext,
    MultiAgentOrchestrator,
)
from shared_llm_core.rule_engine import Rule, RuleContext, RuleEngine, RuleRegistry
from shared_llm_core.rules import BruteForceRule, KnownCVERule

__version__ = "0.5.0"

__all__ = [
    # v0.1
    "AuditLog", "AuditRecord",
    "ChatChoice", "ChatMessage", "ChatRequest", "ChatResponse", "ChatUsage",
    "LLMClient", "LLMRouter", "PromptTemplate", "RouteRule", "TaskTier",
    "TemplateRegistry",
    # v0.5
    "Finding", "FindingSeverity", "FindingSource",
    "Correlation", "CorrelationRule", "FindingRegistry",
    "IntegrationGateway", "ProductAdapter",
    "AgentResult", "AgentRole", "MissionContext", "MultiAgentOrchestrator",
    "Rule", "RuleContext", "RuleEngine", "RuleRegistry",
    "BruteForceRule", "KnownCVERule",
    "__version__",
]
```

---

## 验收硬约束(Codex 必须逐项验证)

| # | 约束 | 验证方式 |
|---|------|---------|
| 1 | v0.1 现有 **24 个 test** 必须仍全过 | `python -m pytest tests/ --basetemp=.pytest-tmp` |
| 2 | v0.5 新增 **≥ 36 个 test**(§7≥10 + §8≥8 + §9≥8 + §10≥10) | pytest 计数 |
| 3 | `__init__.py` append-only,**v0.1 12 个导出全保留** | grep 验证 |
| 4 | `__version__ = "0.5.0"` | import 验证 |
| 5 | 不用 pydantic,全用 dataclass + typing | 已禁止 |
| 6 | pyproject.toml 新增: `fastapi`, `uvicorn`, `httpx>=0.27,<0.28` | 文件验证 |
| 7 | 每个 ISSUE 1 个 commit | git log |
| 8 | **总测试数 ≥ 60 passed**(24 v0.1 + ≥36 v0.5) | pytest summary |
| 9 | 不破坏 §1-§6 符号 / 字段 / 行为 | import 验证 + 现有 test 全过 |

---

## 回报格式

完工后回报 5 项:

```
1. 4 个 commit hash:
   ISSUE 1 (multi_agent):  <hash>
   ISSUE 2 (rule_engine): <hash>
   ISSUE 3 (finding):     <hash>
   ISSUE 4 (gateway):     <hash>

2. pytest 输出最后 5 行:
   (粘贴 pytest 输出的最后 5 行,必须显示 60+ passed)

3. grep 验证 v0.1 符号未删:
   python -c "import shared_llm_core; print(sorted([x for x in dir(shared_llm_core) if not x.startswith('_')]))"
   (粘贴输出,确认 12 个 v0.1 符号都在)

4. 已知问题:
   (如有 NIT / 遗留 issue,列出)

5. v0.5 §14 冻结 checklist 自检:
   [x] §7-§10 设计文档
   [x] §7-§10 实现代码 + tests
   [ ] 6 个产品接入 v0.5 至少 1 个新组件  ← 等 Phase 1
   [ ] IntegrationGateway 跑通 6 个产品 e2e ← 等 Phase 2
   [x] CI 全绿(v0.1 24 + v0.5 36+,本任务完成后前 3 项勾选)
```

---

## 预计工时

**3-4 天**

---

## 完工后我会做的事(Claude 端)

1. 二审:对照 §14 checklist 逐项验证
2. 解锁:派 6 个产品 v0.5 升级(001-S3 / 002-S3 / 003-S3 / 004-S3 / 005-S3 / 006-S4)
3. 跟踪:STAGES-v0.5.md 跟踪表更新 005-CONTRACT 完成日