"""v0.5 §9 Finding unified schema.

Cross-product Finding dataclass so SOC / Vuln / Lab / Code / Reverse /
Firmware can share correlation, deduplication, and presentation.

Backward compatible: v0.1 imports continue to work (this module is
additive). `to_dict` / `from_dict` give a stable JSON shape.

Public API cheat sheet
----------------------
Finding(id="", source, severity, confidence, title)      # id auto-UUIDs if empty
Finding.to_dict() -> dict                                # stable field-order JSON
Finding.from_dict(data) -> Finding                       # tolerant of unknown keys
Finding.confidence = 0.7  # raises ValueError if outside [0,1]
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping


class FindingSource(str, Enum):
    """Where the Finding originated. 6 longyuanai products + external."""

    SOC = "001"
    VULN = "002"
    LAB = "003"
    CODE = "004"
    REVERSE = "005"
    FIRMWARE = "006"
    EXTERNAL = "external"


class FindingSeverity(str, Enum):
    """Standard 5-step severity ladder."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Finding:
    """A single security finding, normalised across all longyuanai products.

    `id` is auto-generated as UUID4 when empty. `confidence` must be in
    [0.0, 1.0]. All container fields are immutable (tuple / frozenset /
    frozen dataclass) so Findings are safe to share across threads.
    """

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

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0,1], got {self.confidence!r}")
        if not self.id:
            # frozen dataclass: must use object.__setattr__
            object.__setattr__(self, "id", str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        """Stable JSON shape.

        Field order matches the dataclass declaration so tests can assert
        on key order. Enum values are stringified; datetime → ISO format;
        tuple/frozenset → list (JSON-friendly).
        """
        d = asdict(self)
        d["source"] = self.source.value
        d["severity"] = self.severity.value
        if self.ts is not None:
            d["ts"] = self.ts.isoformat()
        d["evidence"] = list(self.evidence)
        d["related"] = list(self.related)
        d["tags"] = sorted(self.tags)
        return d

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Finding":
        """Reconstruct a Finding from `to_dict` output.

        Unknown keys are silently ignored so older clients can read newer
        payloads without crashing. Enum / datetime / tuple / frozenset
        fields are coerced back to their typed forms.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}
        clean: dict[str, Any] = {k: v for k, v in data.items() if k in known}

        if "source" in clean and isinstance(clean["source"], str):
            clean["source"] = FindingSource(clean["source"])
        if "severity" in clean and isinstance(clean["severity"], str):
            clean["severity"] = FindingSeverity(clean["severity"])
        if "ts" in clean and isinstance(clean["ts"], str):
            clean["ts"] = datetime.fromisoformat(clean["ts"])
        if "evidence" in clean and isinstance(clean["evidence"], list):
            clean["evidence"] = tuple(clean["evidence"])
        if "related" in clean and isinstance(clean["related"], list):
            clean["related"] = tuple(clean["related"])
        if "tags" in clean and isinstance(clean["tags"], list):
            clean["tags"] = frozenset(clean["tags"])

        return cls(**clean)