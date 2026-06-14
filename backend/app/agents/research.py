from __future__ import annotations

import json
from typing import Any

import structlog
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState
from app.core.config import settings

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Research Agent for Astra — an expert information gatherer.

Your mission: Execute web searches for the provided queries, collect high-quality sources, 
and synthesize them into structured findings.

For each query you MUST search the web and return sources in JSON.
Format your response as valid JSON only:
{
  "sources": [
    {
      "url": "https://...",
      "title": "...",
      "snippet": "...",
      "relevance_score": 0.95,
      "domain_authority": "high|medium|low",
      "content_type": "article|paper|blog|news|documentation",
      "key_facts": ["fact 1", "fact 2", "fact 3"],
      "query_match": "<which sub-query this answers>"
    }
  ],
  "coverage_assessment": "low|medium|high",
  "gaps_identified": ["gap 1", "gap 2"]
}

Rules:
- Search ALL provided sub-queries
- Prefer .edu, .gov, .org, peer-reviewed, and reputable news domains
- Exclude paywalled sources without meaningful snippets
- Return at most 20 sources total
- Score relevance strictly; use 0.5 only for tangentially related results
"""


def _make_search_tool() -> TavilySearchResults:
    return TavilySearchResults(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        tavily_api_key=settings.TAVILY_API_KEY,
    )


@registry.register
class ResearchAgent(BaseAgent):
    name = "research"
    model_id = "gemini-2.5-pro-preview"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.3

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        sub_queries: list[str] = state.get("sub_queries") or [state["query"]]
        research_plan = state.get("research_plan", {})

        # Execute Tavily search for each sub-query
        raw_results: list[dict] = []
        search_tool = _make_search_tool()

        for q in sub_queries[:6]:  # cap at 6 queries to control costs
            try:
                results = await search_tool.ainvoke({"query": q})
                if isinstance(results, list):
                    for r in results:
                        r["source_query"] = q
                        raw_results.append(r)
                elif isinstance(results, str):
                    raw_results.append({"content": results, "source_query": q, "url": "", "title": q})
            except Exception as e:
                logger.warning("search_tool_error", query=q, error=str(e))

        # Ask Gemini to analyze and structure the raw search results
        prompt = f"""Research Context:
Original query: {state["query"]}
Research plan objective: {research_plan.get("objective", "")}
Sub-queries searched: {json.dumps(sub_queries[:6], indent=2)}

Raw search results (from Tavily):
{json.dumps(raw_results, indent=2, default=str)[:12000]}

Analyze these results. Extract key facts from each source, score their relevance,
and identify coverage gaps. Return the structured JSON response as defined in your instructions."""

        content, inp, outp = await self._chat(prompt)
        structured = self._parse_sources(content, raw_results)

        sources = structured.get("sources", [])
        if not sources:
            sources = self._fallback_sources(raw_results)

        if self.memory:
            await self.memory.save_episode({"sources_count": len(sources)})
            await self.memory.share("web_sources_count", len(sources))

        return {
            "web_sources": sources,
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_sources(self, content: str, raw_results: list[dict]) -> dict:
        cleaned = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("research_json_parse_failed", raw=content[:300])
            return {}

    def _fallback_sources(self, raw_results: list[dict]) -> list[dict]:
        """Produce minimal source list directly from Tavily raw output."""
        return [
            {
                "url": r.get("url", ""),
                "title": r.get("title", r.get("source_query", "")),
                "snippet": r.get("content", "")[:500],
                "relevance_score": 0.7,
                "domain_authority": "medium",
                "content_type": "article",
                "key_facts": [],
                "query_match": r.get("source_query", ""),
            }
            for r in raw_results
        ]
