from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict

from langchain_core.messages import BaseMessage


class ResearchState(TypedDict):
    """Complete LangGraph state passed between all agents."""

    # ─── Job Identity ─────────────────────────────────────────────────────────
    job_id: str
    query: str
    org_id: str
    user_id: str

    # ─── Planner Output ───────────────────────────────────────────────────────
    research_plan: NotRequired[dict[str, Any]]   # structured plan from planner
    sub_queries: NotRequired[list[str]]           # decomposed search queries
    search_terms: NotRequired[list[str]]          # extracted key terms
    task_priority: NotRequired[list[str]]         # ordered task list

    # ─── Research Output (parallel write → use operator.add) ──────────────────
    web_sources: Annotated[list[dict[str, Any]], operator.add]

    # ─── Literature Output (parallel write → use operator.add) ────────────────
    papers: Annotated[list[dict[str, Any]], operator.add]

    # ─── Verification Output ──────────────────────────────────────────────────
    verified_claims: NotRequired[list[dict[str, Any]]]
    contradictions: NotRequired[list[dict[str, Any]]]
    claim_scores: NotRequired[dict[str, float]]
    unverifiable_claims: NotRequired[list[str]]

    # ─── Insight Output ───────────────────────────────────────────────────────
    insights: NotRequired[list[str]]
    key_findings: NotRequired[list[str]]
    recommendations: NotRequired[list[str]]
    knowledge_gaps: NotRequired[list[str]]

    # ─── Report Output ────────────────────────────────────────────────────────
    final_report: NotRequired[str]
    report_summary: NotRequired[str]
    citations: NotRequired[list[dict[str, Any]]]
    quality_score: NotRequired[float]

    # ─── Control Flow ─────────────────────────────────────────────────────────
    current_node: str
    completed_nodes: Annotated[list[str], operator.add]
    error_count: int
    last_error: NotRequired[str]

    # ─── Accumulated Metrics (parallel-safe via operator.add) ─────────────────
    messages: Annotated[list[BaseMessage], operator.add]
    tokens_used: Annotated[int, operator.add]
    cost_usd: Annotated[float, operator.add]


def initial_state(
    job_id: str,
    query: str,
    org_id: str,
    user_id: str,
) -> ResearchState:
    """Return a valid initial state for a new research job."""
    return ResearchState(
        job_id=job_id,
        query=query,
        org_id=org_id,
        user_id=user_id,
        current_node="planner",
        completed_nodes=[],
        web_sources=[],
        papers=[],
        messages=[],
        tokens_used=0,
        cost_usd=0.0,
        error_count=0,
    )
