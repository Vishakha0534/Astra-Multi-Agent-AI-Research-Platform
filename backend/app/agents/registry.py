from __future__ import annotations

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from app.agents.base import BaseAgent


class AgentRegistry:
    """Singleton registry mapping agent names → agent classes."""

    _instance: "AgentRegistry | None" = None
    _agents: dict[str, Type["BaseAgent"]]

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents = {}
        return cls._instance

    # ─── Registration ─────────────────────────────────────────────────────────

    def register(self, cls: Type["BaseAgent"]) -> Type["BaseAgent"]:
        """Class decorator to register an agent by its `name` attribute."""
        if not cls.name:
            raise ValueError(f"Agent class {cls.__name__} must define a `name` attribute")
        self._agents[cls.name] = cls
        return cls

    def get(self, name: str) -> Type["BaseAgent"]:
        if name not in self._agents:
            raise KeyError(f"No agent registered under name '{name}'")
        return self._agents[name]

    def all_names(self) -> list[str]:
        return list(self._agents.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._agents


# ─── Module-level singleton ───────────────────────────────────────────────────
registry = AgentRegistry()
