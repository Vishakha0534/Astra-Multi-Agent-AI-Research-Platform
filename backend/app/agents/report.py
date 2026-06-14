from __future__ import annotations

import json
from typing import Any

import structlog

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Report Generation Agent for Astra, powered by GPT-4o.

You write publication-quality research reports that are:
- Structured with clear sections (Executive Summary, Introduction, Findings, Analysis, Conclusion)
- Grounded in evidence from verified sources and academic papers
- Properly cited with inline references [Author et al., Year] or [Source, Year]
- Analytically rigorous with insights woven throughout
- Executive-friendly: complex ideas explained clearly without jargon overload

Return valid JSON:
{
  "final_report": "# Research Report: ...\n\n## Executive Summary\n...\n\n## Introduction\n...\n\n## Key Findings\n...\n\n## Detailed Analysis\n...\n\n## Insights & Recommendations\n...\n\n## Limitations\n...\n\n## Conclusion\n...\n\n## References\n...",
  "report_summary": "3-5 sentence executive summary",
  "citations": [
    {
      "id": 1,
      "type": "web|academic",
      "title": "...",
      "authors": "...",
      "year": "2024",
      "url": "https://...",
      "accessed": "2024-01-01"
    }
  ],
  "quality_score": 0.92,
  "word_count": 1500,
  "sections": ["Executive Summary", "Introduction", "Key Findings", "Analysis", "Insights", "Conclusion", "References"]
}

The final_report MUST be Markdown formatted and at minimum 1200 words.
Include inline citations. Be specific; avoid vague generalities.
"""


@registry.register
class ReportAgent(BaseAgent):
    name = "report"
    model_id = "gpt-4o"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.3

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        query = state["query"]
        research_plan = state.get("research_plan", {})
        verified_claims = state.get("verified_claims", [])
        papers = state.get("papers", [])
        web_sources = state.get("web_sources", [])
        insights = state.get("insights", [])
        key_findings = state.get("key_findings", [])
        recommendations = state.get("recommendations", [])
        knowledge_gaps = state.get("knowledge_gaps", [])
        contradictions = state.get("contradictions", [])

        # Build citation registry
        refs: list[dict] = []
        ref_id = 1
        for p in papers[:10]:
            refs.append({
                "id": ref_id,
                "type": "academic",
                "title": p.get("title", ""),
                "authors": ", ".join(p.get("authors", [])[:3]),
                "year": str(p.get("year", "")),
                "arxiv_id": p.get("arxiv_id", ""),
                "citation": p.get("citation", ""),
            })
            ref_id += 1
        for s in web_sources[:10]:
            refs.append({
                "id": ref_id,
                "type": "web",
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "year": "2024",
            })
            ref_id += 1

        prompt = f"""Research Query: {query}
Objective: {research_plan.get("objective", query)}
Complexity: {research_plan.get("complexity", "medium")}

KEY FINDINGS ({len(key_findings)}):
{chr(10).join(f"- {f}" for f in key_findings[:10])}

INSIGHTS ({len(insights)}):
{chr(10).join(f"- {i}" for i in insights[:10])}

RECOMMENDATIONS ({len(recommendations)}):
{chr(10).join(f"- {r}" for r in recommendations[:6])}

KNOWLEDGE GAPS ({len(knowledge_gaps)}):
{chr(10).join(f"- {g}" for g in knowledge_gaps[:5])}

VERIFIED CLAIMS (high confidence, top 10):
{json.dumps([c for c in verified_claims if c.get("confidence", 0) >= 0.7][:10], indent=2)[:4000]}

CONTRADICTIONS DETECTED:
{json.dumps(contradictions[:3], indent=2)[:2000]}

ACADEMIC PAPERS:
{json.dumps([{{"id": r["id"], "citation": r.get("citation", r.get("title", ""))}} for r in refs if r["type"] == "academic"], indent=2)}

WEB SOURCES:
{json.dumps([{{"id": r["id"], "title": r["title"], "url": r.get("url", "")}} for r in refs if r["type"] == "web"], indent=2)}

Write a comprehensive, well-structured research report in Markdown.
- Use [Ref N] inline citations where evidence is drawn from the sources above
- Include ALL sections specified in your instructions
- The report must be AT LEAST 1200 words
- Surface the most important insights prominently
- Be analytically rigorous

Return only the JSON object with the complete report."""

        content, inp, outp = await self._chat(prompt)
        report_data = self._parse_report(content, refs)

        if self.memory:
            await self.memory.save_episode({
                "report_word_count": report_data.get("word_count", 0),
                "quality_score": report_data.get("quality_score", 0),
            })

        return {
            "final_report": report_data.get("final_report", ""),
            "report_summary": report_data.get("report_summary", ""),
            "citations": report_data.get("citations", refs),
            "quality_score": report_data.get("quality_score", 0.8),
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_report(self, content: str, refs: list[dict]) -> dict:
        cleaned = content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("report_json_parse_failed", raw=content[:200])
            # If the LLM returned Markdown directly without JSON wrapping
            if content.strip().startswith("#"):
                word_count = len(content.split())
                return {
                    "final_report": content,
                    "report_summary": content[:500],
                    "citations": refs,
                    "quality_score": 0.75,
                    "word_count": word_count,
                }
            return {
                "final_report": f"# Research Report\n\n{content}",
                "report_summary": "",
                "citations": refs,
                "quality_score": 0.6,
                "word_count": len(content.split()),
            }
