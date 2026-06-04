from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Verification Agent for Astra, powered by DeepSeek-R1.

Your job is DEEP LOGICAL REASONING and FACT VERIFICATION. You:
1. Extract all factual claims from web sources and academic papers
2. Cross-check claims across sources to find consensus or contradiction
3. Score each claim by confidence based on source count and authority
4. Flag contradictions and explain which source is more credible and why

Apply chain-of-thought reasoning (think step by step) before scoring.

Return ONLY valid JSON:
{
  "verified_claims": [
    {
      "claim": "...",
      "verdict": "confirmed|probable|disputed|unverifiable",
      "confidence": 0.95,
      "supporting_sources": ["url1", "url2"],
      "contradicting_sources": ["url3"],
      "reasoning": "Brief reasoning for verdict",
      "category": "statistical|methodological|causal|definitional"
    }
  ],
  "contradictions": [
    {
      "topic": "...",
      "position_a": "...",
      "source_a": "url1",
      "position_b": "...",
      "source_b": "url2",
      "resolution": "...",
      "credibility_winner": "a|b|neither"
    }
  ],
  "claim_scores": {
    "<claim hash>": 0.85
  },
  "unverifiable_claims": ["claim 1", "claim 2"],
  "overall_reliability": 0.85,
  "verification_notes": "..."
}

Be rigorous. A claim without 2+ corroborating sources gets max confidence 0.6.
"""


@registry.register
class VerificationAgent(BaseAgent):
    name = "verification"
    model_id = "deepseek-reasoner"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.0   # deterministic for fact-checking

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        web_sources = state.get("web_sources", [])
        papers = state.get("papers", [])
        query = state["query"]

        # Compile all factual content for verification
        source_snippets = [
            {"url": s.get("url", ""), "facts": s.get("key_facts", []), "snippet": s.get("snippet", "")[:400]}
            for s in web_sources[:15]
        ]
        paper_claims = [
            {"title": p.get("title", ""), "contributions": p.get("key_contributions", [])}
            for p in papers[:10]
        ]

        prompt = f"""Research Query: {query}

Web Sources to Verify ({len(source_snippets)} sources):
{json.dumps(source_snippets, indent=2)[:8000]}

Academic Paper Claims ({len(paper_claims)} papers):
{json.dumps(paper_claims, indent=2)[:4000]}

Instructions:
1. <think> through each claim carefully before scoring (DeepSeek reasoning mode)
2. Cross-reference facts across web sources AND academic papers
3. For every factual claim, check: is it present in multiple independent sources?
4. Identify any direct contradictions between sources
5. Return the complete JSON verification report

Return ONLY the JSON object."""

        content, inp, outp = await self._chat(prompt)
        report = self._parse_report(content)

        if self.memory:
            verified = report.get("verified_claims", [])
            await self.memory.save_episode({"verified_claims": len(verified)})
            await self.memory.share("overall_reliability", report.get("overall_reliability", 0))

        return {
            "verified_claims": report.get("verified_claims", []),
            "contradictions": report.get("contradictions", []),
            "claim_scores": report.get("claim_scores", {}),
            "unverifiable_claims": report.get("unverifiable_claims", []),
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_report(self, content: str) -> dict:
        # DeepSeek-R1 often wraps reasoning in <think>...</think> tags
        if "<think>" in content and "</think>" in content:
            end = content.rfind("</think>")
            content = content[end + len("</think>"):].strip()

        cleaned = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("verification_json_parse_failed", raw=content[:300])
            return {
                "verified_claims": [],
                "contradictions": [],
                "claim_scores": {},
                "unverifiable_claims": [],
                "overall_reliability": 0.5,
                "verification_notes": "Parse error; raw LLM output could not be decoded",
            }
