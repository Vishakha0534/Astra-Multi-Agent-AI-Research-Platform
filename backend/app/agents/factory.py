from __future__ import annotations

from typing import Any

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from app.agents.base import BaseAgent
from app.agents.memory import AgentMemory
from app.agents.registry import registry
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ─── LLM factory helpers ──────────────────────────────────────────────────────

def _make_gpt4o(temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        max_retries=0,           # retries handled by BaseAgent
        request_timeout=120,
    )


def _make_claude_sonnet(temperature: float = 0.1) -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=temperature,
        api_key=settings.ANTHROPIC_API_KEY,
        max_retries=0,
        timeout=120,
    )


def _make_gemini_pro(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-pro-preview-05-06",
        temperature=temperature,
        google_api_key=settings.GOOGLE_API_KEY,
        max_retries=0,
        request_timeout=180,
    )


def _make_deepseek_r1(temperature: float = 0.0) -> ChatOpenAI:
    """DeepSeek R1 via OpenAI-compatible endpoint."""
    return ChatOpenAI(
        model="deepseek-reasoner",
        temperature=temperature,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        max_retries=0,
        request_timeout=300,   # reasoning models can be slow
    )


def _make_qwen3(temperature: float = 0.1) -> ChatOpenAI:
    """Qwen 3 via DashScope OpenAI-compatible endpoint (fallback agent)."""
    return ChatOpenAI(
        model="qwen3-235b-a22b",
        temperature=temperature,
        api_key=settings.QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        max_retries=0,
        request_timeout=120,
    )


# ─── Model assignment per agent ───────────────────────────────────────────────

_AGENT_MODEL_MAP: dict[str, Any] = {
    "planner":      _make_gpt4o,
    "research":     _make_gemini_pro,
    "literature":   _make_claude_sonnet,
    "verification": _make_deepseek_r1,
    "insight":      _make_gpt4o,
    "report":       _make_gpt4o,
    # Fallback model for all agents when primary fails
    "__fallback__": _make_qwen3,
}


class AgentFactory:
    """Creates fully configured agent instances from the registry."""

    @staticmethod
    def create(
        agent_name: str,
        redis_client=None,
        job_id: str = "",
        *,
        use_fallback: bool = False,
    ) -> BaseAgent:
        """Instantiate a registered agent with its designated LLM.

        Args:
            agent_name:    Name registered in AgentRegistry.
            redis_client:  Async Redis client for AgentMemory.
            job_id:        Research job ID for memory namespacing.
            use_fallback:  If True, substitutes Qwen 3 as the model.
        """
        agent_cls = registry.get(agent_name)

        if use_fallback:
            llm_factory = _AGENT_MODEL_MAP["__fallback__"]
        else:
            llm_factory = _AGENT_MODEL_MAP.get(agent_name, _AGENT_MODEL_MAP["__fallback__"])

        llm = llm_factory(temperature=agent_cls.temperature)

        memory = None
        if redis_client and job_id:
            memory = AgentMemory(redis_client, job_id, agent_name)

        logger.info(
            "agent_created",
            agent=agent_name,
            model=agent_cls.model_id,
            fallback=use_fallback,
        )
        return agent_cls(llm=llm, memory=memory)

    @staticmethod
    def create_all(
        redis_client=None,
        job_id: str = "",
    ) -> dict[str, BaseAgent]:
        """Create every registered agent. Used by the workflow executor."""
        return {
            name: AgentFactory.create(name, redis_client=redis_client, job_id=job_id)
            for name in registry.all_names()
        }
