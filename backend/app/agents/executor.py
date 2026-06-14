from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import ResearchState, initial_state
from app.agents.workflow import build_workflow

logger = structlog.get_logger(__name__)


class AgentExecutor:
    """Runs the multi-agent LangGraph workflow for a research job.

    Responsibilities:
    - Build the workflow with per-job memory
    - Execute synchronously (ainvoke) or stream node-by-node (astream)
    - Persist job progress to DB and Redis
    - Emit structured audit events
    """

    def __init__(
        self,
        db: AsyncSession | None = None,
        redis_client=None,
    ) -> None:
        self._db = db
        self._redis = redis_client

    # ─── Primary Execution Methods ────────────────────────────────────────────

    async def run(
        self,
        query: str,
        org_id: str,
        user_id: str,
        *,
        job_id: str | None = None,
    ) -> ResearchState:
        """Execute the full pipeline and return the final state.

        Args:
            query:   Research query string.
            org_id:  Organisation ID (multi-tenancy).
            user_id: Requesting user ID.
            job_id:  Optional existing job ID (for retry flows).

        Returns:
            Final ResearchState with report, insights, citations, etc.
        """
        job_id = job_id or str(uuid.uuid4())
        log = logger.bind(job_id=job_id, query=query[:80])
        log.info("research_job_start")

        state = initial_state(job_id=job_id, query=query, org_id=org_id, user_id=user_id)

        workflow = build_workflow(redis_client=self._redis, job_id=job_id)

        start = time.perf_counter()
        try:
            final_state: ResearchState = await workflow.ainvoke(state)

            elapsed = round(time.perf_counter() - start, 2)
            log.info(
                "research_job_complete",
                elapsed_s=elapsed,
                tokens=final_state.get("tokens_used", 0),
                cost_usd=round(final_state.get("cost_usd", 0.0), 4),
                nodes_completed=final_state.get("completed_nodes", []),
                quality_score=final_state.get("quality_score"),
            )

            await self._persist_result(final_state)
            return final_state

        except Exception as exc:
            log.error("research_job_failed", error=str(exc))
            raise

    async def stream(
        self,
        query: str,
        org_id: str,
        user_id: str,
        *,
        job_id: str | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream partial state updates as each agent completes.

        Yields dicts of the form:
            {"node": "research", "state_patch": {...}}

        Useful for real-time UI updates via SSE or WebSocket.
        """
        job_id = job_id or str(uuid.uuid4())
        log = logger.bind(job_id=job_id)
        log.info("research_stream_start")

        state = initial_state(job_id=job_id, query=query, org_id=org_id, user_id=user_id)
        workflow = build_workflow(redis_client=self._redis, job_id=job_id)

        async for node_name, patch in workflow.astream(state, stream_mode="updates"):
            log.debug("node_complete", node=node_name)
            yield {
                "job_id": job_id,
                "node": node_name,
                "completed_nodes": patch.get("completed_nodes", []),
                "error_count": patch.get("error_count", 0),
                "tokens_used": patch.get("tokens_used", 0),
                "cost_usd": patch.get("cost_usd", 0.0),
            }

    # ─── Persistence ──────────────────────────────────────────────────────────

    async def _persist_result(self, state: ResearchState) -> None:
        """Write final results to DB tables (agent_logs, audit_logs, reports)."""
        if not self._db:
            return
        try:
            # Persist agent execution summary to agent_logs table
            # (Requires AgentLog model — placeholder for full DB integration)
            logger.debug(
                "persist_result_stub",
                job_id=state.get("job_id"),
                tokens=state.get("tokens_used"),
                report_len=len(state.get("final_report", "")),
            )
        except Exception as e:
            logger.warning("persist_result_error", error=str(e))

    # ─── Convenience class methods ────────────────────────────────────────────

    @classmethod
    def from_request(cls, db: AsyncSession, redis_client) -> "AgentExecutor":
        """FastAPI dependency-friendly constructor."""
        return cls(db=db, redis_client=redis_client)
