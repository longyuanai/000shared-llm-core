"""End-to-end smoke test for the shared LLM core.

Run with: `python -m shared_llm_core.demo`
Requires a live provider (vLLM / OpenAI / Claude proxy). For local vLLM:

    docker compose up -d vllm
    python -m shared_llm_core.demo

For a CI smoke test that does not need a real LLM, see tests/test_router.py.
"""

from __future__ import annotations

import os

from shared_llm_core import (
    ChatMessage,
    ChatRequest,
    LLMRouter,
    PromptTemplate,
    TemplateRegistry,
)
from shared_llm_core.router import TaskTier


def main() -> None:
    prompts_root = os.getenv("LLM_PROMPTS_ROOT", "./prompts")
    registry = TemplateRegistry(prompts_root)

    template = registry.get("hello", "v1")
    messages = template.render(name="longyuanai")

    # Router picks provider/model by tier. All audit goes to ./audit.jsonl.
    with LLMRouter.from_env() as router:
        req = ChatRequest(
            messages=messages,
            temperature=0.3,
            max_tokens=128,
        )
        resp = router.chat(TaskTier.STANDARD, req)
        print("--- model:", resp.model)
        print("--- tokens:", resp.usage.total_tokens)
        print("--- reply:")
        print(resp.choices[0].message.content)


if __name__ == "__main__":
    main()