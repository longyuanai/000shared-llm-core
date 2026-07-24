"""shared-llm-core: OpenAI-compatible LLM Gateway for the longyuanai agent suite."""

# v0.1 (frozen — DO NOT MODIFY)
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

# v0.5 (additive)
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
    # v0.1 (frozen)
    "AuditLog",
    "AuditRecord",
    "ChatChoice",
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "ChatUsage",
    "LLMClient",
    "LLMRouter",
    "PromptTemplate",
    "RouteRule",
    "TaskTier",
    "TemplateRegistry",
    # v0.5 (new)
    "Finding",
    "FindingSeverity",
    "FindingSource",
    "Correlation",
    "CorrelationRule",
    "FindingRegistry",
    "IntegrationGateway",
    "ProductAdapter",
    "AgentResult",
    "AgentRole",
    "MissionContext",
    "MultiAgentOrchestrator",
    "Rule",
    "RuleContext",
    "RuleEngine",
    "RuleRegistry",
    "BruteForceRule",
    "KnownCVERule",
    "__version__",
]