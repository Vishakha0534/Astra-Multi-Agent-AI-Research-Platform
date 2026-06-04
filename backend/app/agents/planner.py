from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Planner Agent for Astra, an enterprise-grade AI research platform.

Your ONLY job is to analyze a research query and produce a precise, actionable research plan.

Output MUST be valid JSON matching this exact schema:
{
  "objective": "<one sentence goal>",
  "complexity": "low|medium|high",
  "tasks": [
    {
      "id": 1,
      "title": "<task title>",
      "description": "<what to do>",
      "agent": "research|literature|verification|insight",
      "priority": 1,
      "estimated_minutes": 5
    }
  ],
  "sub_queries": [
    "<specific search query 1>",
    "<specific search query 2>"
  ],
  "search_terms": ["term1", "term2"],
  "task_priority": ["<highest priority task id>", ...],
  "scope_constraints": "<what to exclude>",
  "success_criteria": "<how to know research is complete>"
}

Rules:
- Generate 3-8 sub_queries that are specific and searchable
- Generate 5-15 search_terms for semantic search
- Order tasks logically; research and literature tasks run in PARALLEL
- Be precise; vague plans produce poor research
"""


@registry.register
class PlannerAgent(BaseAgent):
    name = "planner"
    model_id = "gpt-4o"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.2

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        query = state["query"]

        prompt = f"""Research Query: {query}

Analyze this query thoroughly and produce a complete research plan.
Consider:
- What information do we need to answer this?
- What academic literature is relevant?
- What factual claims will need verification?
- What insights can be synthesized from the data?

Return only the JSON object. No markdown fences. No explanation text."""

        content, inp, outp = await self._chat(prompt)

        # Robust JSON extraction
        plan = self._parse_json(content, query)

        if self.memory:
            await self.memory.save_episode({"research_plan": plan})
            await self.memory.share("research_plan", plan)

        return {
            "research_plan": plan,
            "sub_queries": plan.get("sub_queries", [query]),
            "search_terms": plan.get("search_terms", []),
            "task_priority": plan.get("task_priority", []),
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_json(self, content: str, fallback_query: str) -> dict[str, Any]:
        """Extract JSON from LLM output, falling back to a minimal plan."""
        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(lines)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("planner_json_parse_failed", raw=content[:200])
            # Minimal fallback plan
            return {
                "objective": fallback_query,
                "complexity": "medium",
                "tasks": [],
                "sub_queries": [fallback_query],
                "search_terms": fallback_query.split()[:10],
                "task_priority": [],
                "scope_constraints": "",
                "success_criteria": "Comprehensive answer provided",
            }
