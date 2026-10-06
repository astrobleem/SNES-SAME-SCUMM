"""Pure-Python model of the proposed resident ProgramUnit binding contract.

This is an analysis/test model only. It is not connected to the SNES runtime.
"""

from __future__ import annotations

from collections import Counter


class ResidencyExhausted(RuntimeError):
    """Every selector is pinned; replacing a binding would be unsafe."""


class ResidentBindingSimulator:
    """Small deterministic model for binding, pinning, and safe reuse."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("resident selector capacity must be positive")
        self.capacity = capacity
        self._unit_to_selector: dict[str, int] = {}
        self._selector_to_unit: dict[int, str] = {}
        self._pins: dict[str, Counter[str]] = {}
        self._next_selector = 0

    def resolve(self, program_unit: str) -> int:
        """Return a selector, evicting only an unpinned cache binding."""
        current = self._unit_to_selector.get(program_unit)
        if current is not None:
            return current
        selector = next((value for value in range(self.capacity)
                         if value not in self._selector_to_unit), None)
        if selector is None:
            evictable = sorted(
                (unit, value) for unit, value in self._unit_to_selector.items()
                if not self._pins.get(unit)
            )
            if not evictable:
                raise ResidencyExhausted(
                    "all resident selectors are pinned; defer/fail resolution without reuse"
                )
            old_unit, selector = evictable[0]
            del self._unit_to_selector[old_unit]
            del self._selector_to_unit[selector]
        self._unit_to_selector[program_unit] = selector
        self._selector_to_unit[selector] = program_unit
        self._next_selector += 1
        return selector

    def pin(self, program_unit: str, reason: str) -> int:
        selector = self.resolve(program_unit)
        pins = self._pins.setdefault(program_unit, Counter())
        pins[reason] += 1
        return selector

    def unpin(self, program_unit: str, reason: str) -> None:
        pins = self._pins.get(program_unit)
        if not pins or pins[reason] <= 0:
            raise ValueError(f"no {reason!r} pin for {program_unit}")
        pins[reason] -= 1
        if pins[reason] == 0:
            del pins[reason]
        if not pins:
            del self._pins[program_unit]

    def pins_for(self, program_unit: str) -> dict[str, int]:
        return dict(sorted(self._pins.get(program_unit, {}).items()))

    def unit_for_selector(self, selector: int) -> str | None:
        return self._selector_to_unit.get(selector)

    def snapshot(self) -> dict[str, object]:
        return {
            "capacity": self.capacity,
            "bindings": dict(sorted(self._unit_to_selector.items())),
            "pins": {unit: dict(sorted(reasons.items()))
                     for unit, reasons in sorted(self._pins.items())},
        }
