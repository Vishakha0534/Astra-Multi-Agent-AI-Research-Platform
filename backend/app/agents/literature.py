from __future__ import annotations

import json
from typing import Any

import arxiv
import structlog

from app.agents.base import BaseAgent
from app.agents.registry import registry
from app.agents.state import ResearchState

logger = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are the Literature Review Agent for Astra — a specialist in academic research analysis.

You have deep expertise in:
- Identifying seminal and state-of-the-art papers
- Summarizing methodologies, datasets, and results
- Extracting proper academic citations
- Detecting research trends and consensus positions

Given academic papers and search terms, produce a structured literature analysis as JSON:
{
  "papers": [
    {
      "arxiv_id": "2401.12345",
      "title": "...",
      "authors": ["Author 1", "Author 2"],
      "year": 2024,
      "abstract_summary": "...",
      "methodology": "...",
      "key_contributions": ["...", "..."],
      "limitations": ["...", "..."],
      "citation": "Author et al. (2024). Title. arXiv:2401.12345",
      "relevance_score": 0.92,
      "paper_type": "empirical|theoretical|survey|benchmark"
    }
  ],
  "research_consensus": "...",
  "emerging_trends": ["trend 1", "trend 2"],
  "foundational_papers": ["arXiv ID 1", "arXiv ID 2"],
  "open_problems": ["problem 1", "problem 2"]
}

Be precise. Do not fabricate paper details. If uncertain, lower relevance_score.
"""


async def _search_arxiv(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Async wrapper around the arxiv library."""
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        results = []
        for paper in search.results():
            results.append({
                "arxiv_id": paper.entry_id.split("/")[-1],
                "title": paper.title,
                "authors": [str(a) for a in paper.authors[:5]],
                "published": str(paper.published.date()),
                "abstract": paper.summary[:1000],
                "pdf_url": paper.pdf_url,
                "categories": paper.categories,
            })
        return results
    except Exception as e:
        logger.warning("arxiv_search_error", query=query, error=str(e))
        return []


@registry.register
class LiteratureAgent(BaseAgent):
    name = "literature"
    model_id = "claude-sonnet-4-5"
    system_prompt = _SYSTEM_PROMPT
    temperature = 0.1

    async def _run(self, state: ResearchState) -> dict[str, Any]:
        search_terms: list[str] = state.get("search_terms", [])
        sub_queries: list[str] = state.get("sub_queries", [state["query"]])

        # Build arxiv search queries from search terms + sub-queries
        arxiv_queries = []
        if search_terms:
            arxiv_queries.append(" AND ".join(search_terms[:5]))
        for q in sub_queries[:3]:
            arxiv_queries.append(q)

        # Fetch papers from arXiv (parallel conceptually, sequential here for simplicity)
        all_papers: list[dict] = []
        seen_ids: set[str] = set()
        for aq in arxiv_queries[:4]:
            papers = await _search_arxiv(aq, max_results=5)
            for p in papers:
                if p["arxiv_id"] not in seen_ids:
                    seen_ids.add(p["arxiv_id"])
                    all_papers.append(p)

        # Have Claude analyze and structure the papers
        prompt = f"""Research Query: {state["query"]}
Search Terms Used: {json.dumps(search_terms[:10])}

Academic Papers Retrieved from arXiv:
{json.dumps(all_papers, indent=2, default=str)[:14000]}

Perform a comprehensive literature review:
1. Analyze each paper's relevance to the query
2. Summarize methodologies and key contributions
3. Identify research consensus and open problems
4. Extract proper citations for each paper

Return the structured JSON analysis as specified in your instructions."""

        content, inp, outp = await self._chat(prompt)
        analysis = self._parse_analysis(content, all_papers)

        papers = analysis.get("papers", [])

        if self.memory:
            await self.memory.save_episode({"papers_analyzed": len(papers)})
            await self.memory.share("papers_count", len(papers))

        return {
            "papers": papers,
            "tokens_used": inp + outp,
            "cost_usd": self._track_cost(inp, outp),
            "messages": [],
        }

    def _parse_analysis(self, content: str, raw_papers: list[dict]) -> dict:
        cleaned = content.strip()
        for fence in ["```json", "```"]:
            if cleaned.startswith(fence):
                cleaned = cleaned[len(fence):]
        cleaned = cleaned.rstrip("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("literature_json_parse_failed", raw=content[:300])
            # Minimal fallback
            return {
                "papers": [
                    {
                        "arxiv_id": p.get("arxiv_id", ""),
                        "title": p.get("title", ""),
                        "authors": p.get("authors", []),
                        "year": p.get("published", "")[:4],
                        "abstract_summary": p.get("abstract", "")[:300],
                        "methodology": "",
                        "key_contributions": [],
                        "limitations": [],
                        "citation": f"{', '.join(p.get('authors', [])[:2])} ({p.get('published', '')[:4]}). {p.get('title', '')}",
                        "relevance_score": 0.7,
                        "paper_type": "empirical",
                    }
                    for p in raw_papers
                ],
                "research_consensus": "",
                "emerging_trends": [],
                "foundational_papers": [],
                "open_problems": [],
            }
