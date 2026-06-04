from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_TTL_WORKING = 3600      # 1 h — active job window
_TTL_EPISODIC = 604800   # 7 days — per-job recall after completion


class AgentMemory:
    """Three-tier memory for agents.

    Tier 1 — Working:  Ephemeral per-agent context stored in Redis during execution.
    Tier 2 — Episodic: Per-job snapshots persisted in Redis after each node.
    Tier 3 — Semantic: Qdrant vector store (injected externally; placeholder here).
    """

    def __init__(self, redis_client, job_id: str, agent_name: str) -> None:
        self._redis = redis_client
        self._job_id = job_id
        self._agent_name = agent_name

    # ─── Key helpers ──────────────────────────────────────────────────────────

    def _working_key(self, key: str) -> str:
        return f"mem:working:{self._job_id}:{self._agent_name}:{key}"

    def _episodic_key(self) -> str:
        return f"mem:episodic:{self._job_id}:{self._agent_name}"

    def _job_key(self) -> str:
        return f"mem:job:{self._job_id}"

    # ─── Working Memory ───────────────────────────────────────────────────────

    async def store(self, key: str, value: Any, ttl: int = _TTL_WORKING) -> None:
        serialized = json.dumps(value, default=str)
        await self._redis.setex(self._working_key(key), ttl, serialized)

    async def recall(self, key: str) -> Any | None:
        raw = await self._redis.get(self._working_key(key))
        return json.loads(raw) if raw else None

    async def forget(self, key: str) -> None:
        await self._redis.delete(self._working_key(key))

    # ─── Episodic Memory ──────────────────────────────────────────────────────

    async def save_episode(self, data: dict[str, Any]) -> None:
        """Persist an agent's output snapshot for cross-agent reference."""
        episode = {
            "agent": self._agent_name,
            "job_id": self._job_id,
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        }
        await self._redis.setex(
            self._episodic_key(),
            _TTL_EPISODIC,
            json.dumps(episode, default=str),
        )

    async def load_episode(self, agent_name: str | None = None) -> dict[str, Any] | None:
        """Load episodic memory for this agent (or another by name)."""
        target_agent = agent_name or self._agent_name
        key = f"mem:episodic:{self._job_id}:{target_agent}"
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else None

    # ─── Job-level Shared Memory ──────────────────────────────────────────────

    async def share(self, field: str, value: Any) -> None:
        """Write a value visible to ALL agents working on this job."""
        raw = await self._redis.get(self._job_key())
        job_state: dict = json.loads(raw) if raw else {}
        job_state[field] = value
        await self._redis.setex(self._job_key(), _TTL_EPISODIC, json.dumps(job_state, default=str))

    async def read_shared(self, field: str) -> Any | None:
        raw = await self._redis.get(self._job_key())
        if not raw:
            return None
        return json.loads(raw).get(field)

    async def all_shared(self) -> dict[str, Any]:
        raw = await self._redis.get(self._job_key())
        return json.loads(raw) if raw else {}
