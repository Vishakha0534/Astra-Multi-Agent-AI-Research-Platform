from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.factory import AgentFactory
from app.agents.state import ResearchState

# ─── Import agents so registry.register decorator fires ──────────────────────
import app.agents.planner       # noqa: F401
import app.agents.research      # noqa: F401
import app.agents.literature    # noqa: F401
import app.agents.verification  # noqa: F401
import app.agents.insight       # noqa: F401
import app.agents.report        # noqa: F401


def build_workflow(redis_client=None, job_id: str = "") -> Any:
    """Compile and return the LangGraph research workflow.

    Pipeline:
        planner
           ├──► research     (parallel fan-out)
           └──► literature   (parallel fan-out)
                    ↓
               verification  (fan-in: waits for BOTH research + literature)
                    ↓
                insight
                    ↓
                report
                    ↓
                  END

    Args:
        redis_client:  Async Redis client injected for AgentMemory.
        job_id:        Research job ID for memory namespacing.

    Returns:
        Compiled LangGraph runnable.
    """
    agents = AgentFactory.create_all(redis_client=redis_client, job_id=job_id)

    # ─── Node wrappers ────────────────────────────────────────────────────────

    async def planner_node(state: ResearchState) -> dict[str, Any]:
        return await agents["planner"].run(state)

    async def research_node(state: ResearchState) -> dict[str, Any]:
        return await agents["research"].run(state)

    async def literature_node(state: ResearchState) -> dict[str, Any]:
        return await agents["literature"].run(state)

    async def verification_node(state: ResearchState) -> dict[str, Any]:
        return await agents["verification"].run(state)

    async def insight_node(state: ResearchState) -> dict[str, Any]:
        return await agents["insight"].run(state)

    async def report_node(state: ResearchState) -> dict[str, Any]:
        return await agents["report"].run(state)

    # ─── Error gate: skip to END if too many errors ───────────────────────────

    def should_continue(state: ResearchState) -> str:
        if state.get("error_count", 0) >= 5:
            return END
        return "insight"

    # ─── Build graph ──────────────────────────────────────────────────────────

    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("literature", literature_node)
    graph.add_node("verification", verification_node)
    graph.add_node("insight", insight_node)
    graph.add_node("report", report_node)

    # Entry point
    graph.set_entry_point("planner")

    # Parallel fan-out after planner: both research AND literature run concurrently
    graph.add_edge("planner", "research")
    graph.add_edge("planner", "literature")

    # Fan-in: verification waits for both research and literature to complete
    graph.add_edge("research", "verification")
    graph.add_edge("literature", "verification")

    # Sequential pipeline
    graph.add_conditional_edges(
        "verification",
        should_continue,
        {"insight": "insight", END: END},
    )
    graph.add_edge("insight", "report")
    graph.add_edge("report", END)

    return graph.compile()
