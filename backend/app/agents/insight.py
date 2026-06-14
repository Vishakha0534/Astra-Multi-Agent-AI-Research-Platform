from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Insight Generation Agent for Astra, powered by GPT-4o.

You synthesize verified research findings into high-value strategic insights.

Your thinking process:
1. Look for PATTERNS across web sources and academic papers
2. Identify CAUSAL relationships, not just correlations
3. Find NON-OBVIOUS connections between different sources of evidence
4. Generate ACTIONABLE recommendations based on evidence
5. Surface KNOWLEDGE GAPS that suggest future research directions

Return structured JSON only:
{
  "insights": [
    "Insight 1: [Evidence-based insight with source reference]",
    "Insight 2: ..."
  ],
  "key_findings": [
    "Finding 1: [Specific, factual finding with supporting evidence]",
    "Finding 2: ..."
  ],
  "recommendations": [
    "Recommendation 1: [Actionable recommendation with rationale]",
    "Recommendation 2: ..."
  ],
  "knowledge_gaps": [
    "Gap 1: [What we don't know yet and why it matters]",
    "Gap 2: ..."
  ],
  "confidence_in_synthesis": 0.88,
  "novel_connections": [
    "Connection between X and Y not obvious from individual sources"
  ],
  "executive_summary": "2-3 sentence synthesis of the most important findings"
}

Generate at minimum: 5 insights, 5 key findings, 3 recommendations, 3 knowledge gaps.
Base EVERYTHING on the verified claims and paper evidence provided. Do not hallucinate.
"""


@registry.register
class InsightAgent(BaseAgent):
    name = "insight"
    model_id = "gpt-4o"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.5   # slightly more creative for insight generation

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        query = state["query"]
        verified_claims = state.get("verified_claims", [])
        papers = state.get("papers", [])
        web_sources = state.get("web_sources", [])
        contradictions = state.get("contradictions", [])
        research_plan = state.get("research_plan", {})

        # Curate high-confidence verified claims for synthesis
        high_conf_claims = [
            c for c in verified_claims
            if c.get("confidence", 0) >= 0.7 and c.get("verdict") in ("confirmed", "probable")
        ]

        paper_contributions = [
            {
                "title": p.get("title"),
                "key_contributions": p.get("key_contributions", []),
                "abstract_summary": p.get("abstract_summary", ""),
            }
            for p in papers[:8]
        ]

        source_topics = [
            {"title": s.get("title"), "key_facts": s.get("key_facts", [])[:3]}
            for s in web_sources[:10]
        ]

        prompt = f"""Research Query: {query}
Research Objective: {research_plan.get("objective", query)}

High-Confidence Verified Claims ({len(high_conf_claims)}):
{json.dumps(high_conf_claims, indent=2)[:6000]}

Academic Paper Contributions ({len(paper_contributions)}):
{json.dumps(paper_contributions, indent=2)[:4000]}

Source Topics ({len(source_topics)}):
{json.dumps(source_topics, indent=2)[:3000]}

Detected Contradictions ({len(contradictions)}):
{json.dumps(contradictions[:5], indent=2)[:2000]}

Based on ALL the evidence above, generate deep strategic insights.
Look for patterns that cross multiple sources. Surface non-obvious connections.
Focus on insights that directly answer the research query.

Return only the JSON object."""

        content, inp, outp = await self._chat(prompt)
        synthesis = self._parse_synthesis(content)

        if self.memory:
            await self.memory.save_episode({
                "insights_count": len(synthesis.get("insights", [])),
                "executive_summary": synthesis.get("executive_summary", ""),
            })

        return {
            "insights": synthesis.get("insights", []),
            "key_findings": synthesis.get("key_findings", []),
            "recommendations": synthesis.get("recommendations", []),
            "knowledge_gaps": synthesis.get("knowledge_gaps", []),
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_synthesis(self, content: str) -> dict:
        cleaned = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("insight_json_parse_failed", raw=content[:300])
            # Attempt to extract text lists as fallback
            lines = [l.strip("- •") for l in content.split("\n") if l.strip().startswith(("-", "•", "*"))]
            return {
                "insights": lines[:5],
                "key_findings": lines[5:10],
                "recommendations": [],
                "knowledge_gaps": [],
                "confidence_in_synthesis": 0.5,
                "novel_connections": [],
                "executive_summary": "",
            }
