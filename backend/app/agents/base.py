from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult

from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

# ─── Per-model cost table (USD per 1K tokens) ────────────────────────────────
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-4o":                    (0.005,   0.015),
    "gpt-4o-mini":               (0.00015, 0.0006),
    "claude-sonnet-4-5":         (0.003,   0.015),
    "gemini-2.5-pro-preview":    (0.00125, 0.005),
    "deepseek-reasoner":         (0.00055, 0.00219),
    "qwen3-235b-a22b":           (0.0,     0.0),     # self-hosted
}


def _estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = MODEL_COSTS.get(model_id, (0.0, 0.0))
    return (input_tokens / 1000 * in_rate) + (output_tokens / 1000 * out_rate)


class BaseAgent(ABC):
    """Abstract base for every Astra agent.

    Subclasses must implement:
      - name (str class attr)
      - model_id (str class attr)
      - system_prompt (str class attr)
      - _run(state, llm, memory) → dict  (returns partial state update)
    """

    name: str = ""
    model_id: str = ""
    system_prompt: str = ""
    max_retries: int = 3
    retry_delay: float = 2.0    # seconds (exponential backoff base)
    temperature: float = 0.2

    def __init__(self, llm: BaseChatModel, memory=None) -> None:
        self.llm = llm
        self.memory = memory
        self._log = logger.bind(agent=self.name, model=self.model_id)

    # ─── Public Interface ─────────────────────────────────────────────────────

    async def run(self, state: ResearchState) -> dict[str, Any]:
        """Execute agent with automatic retry and cost tracking."""
        start = time.perf_counter()
        attempt = 0

        while attempt <= self.max_retries:
            try:
                self._log.info("agent_start", attempt=attempt, job_id=state["job_id"])
                result = await self._run(state)

                # Inject standard tracking fields into every partial state update
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                result.setdefault("current_node", self.name)
                result.setdefault("completed_nodes", [self.name])
                result.setdefault("tokens_used", 0)
                result.setdefault("cost_usd", 0.0)

                self._log.info(
                    "agent_success",
                    job_id=state["job_id"],
                    latency_ms=elapsed_ms,
                    tokens=result.get("tokens_used", 0),
                )
                return result

            except Exception as exc:
                attempt += 1
                delay = self.retry_delay * (2 ** (attempt - 1))
                self._log.warning(
                    "agent_retry",
                    error=str(exc),
                    attempt=attempt,
                    next_delay=delay,
                    job_id=state["job_id"],
                )
                if attempt > self.max_retries:
                    self._log.error("agent_failed", error=str(exc), job_id=state["job_id"])
                    return {
                        "current_node": self.name,
                        "completed_nodes": [self.name],
                        "error_count": state.get("error_count", 0) + 1,
                        "last_error": f"{self.name}: {exc}",
                        "tokens_used": 0,
                        "cost_usd": 0.0,
                        "messages": [],
                    }
                await asyncio.sleep(delay)

        return {}

    @abstractmethod
    async def _run(self, state: ResearchState) -> dict[str, Any]:
        """Core logic. Must return a partial ResearchState dict."""
        ...

    # ─── Helpers for subclasses ───────────────────────────────────────────────

    async def _chat(
        self,
        human_message: str,
        system_override: str | None = None,
        *,
        parse_json: bool = False,
    ) -> tuple[str, int, int]:
        """Call the LLM and return (content, input_tokens, output_tokens)."""
        messages = [
            SystemMessage(content=system_override or self.system_prompt),
            HumanMessage(content=human_message),
        ]
        response: AIMessage = await self.llm.ainvoke(messages)
        content = response.content

        # Extract token usage from response metadata
        usage = getattr(response, "usage_metadata", None) or {}
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        return str(content), input_tokens, output_tokens

    def _track_cost(self, input_tokens: int, output_tokens: int) -> float:
        return _estimate_cost(self.model_id, input_tokens, output_tokens)
