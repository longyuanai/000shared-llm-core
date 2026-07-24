"""Built-in rules shipped with shared-llm-core.

These are demo / reference rules. Real products ship domain-specific
rules in their own packages.
"""

from shared_llm_core.rules.builtin import BruteForceRule, KnownCVERule

__all__ = ["BruteForceRule", "KnownCVERule"]