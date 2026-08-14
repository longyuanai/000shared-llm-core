"""v0.5 §10 IntegrationGateway — FastAPI entrypoint for the agent suite.

Exposes a uniform HTTP API for the 6 longyuanai products. Each product
plugs in via a `ProductAdapter` (subprocess or in-process). Findings
land in a shared `FindingRegistry`; correlation rules can fire per-add.

In-memory only — v1.0 will add Postgres / Redis backends.

Public API cheat sheet
----------------------
FindingRegistry()                                        # in-memory store
await registry.add(finding)                              # async publish to subscribers
registry.add_sync(finding)                               # sync variant for adapters
registry.query(source=..., severity=..., host=...) -> list  # filters, default limit 100
async for kind,item in registry.subscribe(): ...         # SSE stream
class MyAdapter(ProductAdapter):                         # source classvar required
    source = FindingSource.CODE
    async def scan(self, payload) -> AsyncIterator[Finding]
    def health(self) -> dict                              # for /v0.5/health
IntegrationGateway(products={src: adapter}).app          # FastAPI instance
IntegrationGateway(...).run(host="0.0.0.0", port=8080)   # uvicorn entrypoint
"""

from __future__ import annotations

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator, Mapping, Sequence

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from shared_llm_core.finding import Finding, FindingSeverity, FindingSource

# Subscribed stream item: ``("finding", Finding)`` or
# ``("correlation", Correlation)``. Defined as a string alias so the
# module imports even though ``Correlation`` is declared later in this
# file.
FindingStreamItem = "tuple[str, Finding] | tuple[str, Correlation]"


class FindingRegistry:
    """In-memory Finding store with bounded size + pub/sub."""

    def __init__(self, *, max_size: int = 100_000) -> None:
        self._findings: deque[Finding] = deque(maxlen=max_size)
        self._correlations: deque[Correlation] = deque(maxlen=max_size)
        self._subscribers: list[asyncio.Queue[Finding]] = []
        self._lock = asyncio.Lock()

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(self._findings)

    @property
    def correlations(self) -> tuple[Correlation, ...]:
        return tuple(self._correlations)

    async def add(self, finding: Finding) -> None:
        async with self._lock:
            self._findings.append(finding)
            for q in self._subscribers:
                if not q.full():
                    q.put_nowait(("finding", finding))

    async def add_correlation(self, correlation: Correlation) -> None:
        async with self._lock:
            self._correlations.append(correlation)
            for q in self._subscribers:
                if not q.full():
                    q.put_nowait(("correlation", correlation))

    def add_sync(self, finding: Finding) -> None:
        """Sync variant for adapters that aren't async.

        Same threading guarantees as `add`: append is bounded by the
        deque's maxlen, and the subscribe-publish hop is skipped (sync
        callers don't drive the SSE loop). Multiple sync producers
        sharing one registry are still safe because `append` on a
        `deque` is thread-safe under the GIL.
        """
        self._findings.append(finding)

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
        for f in reversed(self._findings):
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

    async def subscribe(self) -> AsyncIterator[FindingStreamItem]:
        q: asyncio.Queue[FindingStreamItem] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.append(q)
        try:
            while True:
                yield await q.get()
        finally:
            async with self._lock:
                if q in self._subscribers:
                    self._subscribers.remove(q)


@dataclass(frozen=True)
class Correlation:
    """A cross-product link between Findings."""

    rule_id: str
    findings: tuple[str, ...]
    severity: FindingSeverity
    narrative: str


class CorrelationRule(ABC):
    """Abstract: given a new Finding and existing Findings, emit Correlations."""

    id: str

    @abstractmethod
    def correlate(
        self,
        new_finding: Finding,
        existing: Sequence[Finding],
    ) -> list[Correlation]:
        ...


class ProductAdapter(ABC):
    """How a longyuanai product plugs into the gateway."""

    source: FindingSource

    @abstractmethod
    async def scan(self, payload: dict[str, Any]) -> AsyncIterator[Finding]:
        """Run the product scan, yielding Findings as they're discovered."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return a health dict for /health."""


class IntegrationGateway:
    """Composes a FastAPI app from a registry + products + correlations."""

    def __init__(
        self,
        *,
        products: Mapping[FindingSource, ProductAdapter],
        registry: FindingRegistry | None = None,
        correlations: Sequence[CorrelationRule] = (),
    ) -> None:
        self._products = dict(products)
        self._registry = registry or FindingRegistry()
        self._correlations = list(correlations)

    @property
    def registry(self) -> FindingRegistry:
        return self._registry

    @property
    def app(self) -> FastAPI:
        app = FastAPI(title="shared-llm-core IntegrationGateway", version="0.6.0")
        gw = self

        @app.get("/v0.5/health")
        async def health() -> dict[str, Any]:
            return {
                "status": "ok",
                "version": "0.5.0",
                "products": {s.value: gw._products[s].health() for s in gw._products},
                "findings_count": len(gw._registry.findings),
            }

        @app.get("/v0.5/findings")
        async def list_findings(
            source: str | None = Query(None),
            severity: str | None = Query(None),
            host: str | None = Query(None),
            cve: str | None = Query(None),
            limit: int = Query(100, ge=1, le=1000),
        ) -> dict[str, Any]:
            src = FindingSource(source) if source else None
            sev = FindingSeverity(severity) if severity else None
            findings = gw._registry.query(
                source=src, severity=sev, host=host, cve=cve, limit=limit
            )
            return {
                "count": len(findings),
                "findings": [f.to_dict() for f in findings],
            }

        @app.post("/v0.5/{source}/scan")
        async def scan(source: str, payload: dict[str, Any]) -> dict[str, Any]:
            try:
                src_enum = FindingSource(source)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=f"unknown source {source}") from exc

            adapter = gw._products.get(src_enum)
            if adapter is None:
                raise HTTPException(status_code=404, detail=f"product {source} not registered")

            collected: list[Finding] = []
            correlations: list[Correlation] = []
            existing = list(gw._registry.findings)
            async for finding in adapter.scan(payload):
                await gw._registry.add(finding)
                collected.append(finding)
                for rule in gw._correlations:
                    try:
                        emitted = rule.correlate(finding, existing)
                    except Exception as exc:  # noqa: BLE001 - isolate rules
                        print(
                            f"[gateway] correlation {rule.id!r} failed: {exc}",
                            file=sys.stderr,
                        )
                        continue
                    for corr in emitted:
                        await gw._registry.add_correlation(corr)
                        correlations.append(corr)

            return {
                "source": source,
                "count": len(collected),
                "findings": [f.to_dict() for f in collected],
                "correlations": [
                    {
                        "rule_id": c.rule_id,
                        "findings": list(c.findings),
                        "severity": c.severity.value,
                        "narrative": c.narrative,
                    }
                    for c in correlations
                ],
            }

        @app.get("/v0.5/correlations")
        async def list_correlations(limit: int = Query(100, ge=1, le=1000)) -> dict[str, Any]:
            tail = list(gw._registry.correlations)[-limit:]
            return {
                "count": len(tail),
                "correlations": [
                    {
                        "rule_id": c.rule_id,
                        "findings": list(c.findings),
                        "severity": c.severity.value,
                        "narrative": c.narrative,
                    }
                    for c in tail
                ],
            }

        @app.get("/v0.5/stream")
        async def stream() -> StreamingResponse:
            async def event_gen():
                async for kind, payload in gw._registry.subscribe():
                    if kind == "finding":
                        data = payload.to_dict()
                    else:
                        c = payload  # Correlation
                        data = {
                            "rule_id": c.rule_id,
                            "findings": list(c.findings),
                            "severity": c.severity.value,
                            "narrative": c.narrative,
                        }
                    yield f"event: {kind}\ndata: {json.dumps(data)}\n\n"

            return StreamingResponse(event_gen(), media_type="text/event-stream")

        return app

    def run(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)
