"""Built-in SAME engine modules."""

from __future__ import annotations

from ..engine import EngineRegistry
from .agi import AgiEngine
from .scumm_v5 import ScummV5Engine


def default_registry() -> EngineRegistry:
    registry = EngineRegistry()
    registry.register(ScummV5Engine)
    registry.register(AgiEngine)
    return registry


__all__ = ["AgiEngine", "ScummV5Engine", "default_registry"]
