"""Foreign guest adapter interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .bus import GuestBus


@dataclass(frozen=True, slots=True)
class StepResult:
    units: int
    halted: bool = False
    yielded: bool = False
    fault: str | None = None

    def __post_init__(self) -> None:
        if self.units < 0:
            raise ValueError("step units cannot be negative")
        if self.fault and not self.halted:
            raise ValueError("faulted guest must be halted")


@runtime_checkable
class GuestAdapter(Protocol):
    """The contract MC68000, Z80, and bytecode interpreters implement."""

    name: str
    bus: GuestBus

    def reset(self) -> None: ...

    def step(self, budget: int) -> StepResult: ...

    def save_state(self) -> bytes: ...

    def load_state(self, state: bytes) -> None: ...


class ScriptedGuest:
    """Tiny deterministic guest used to prove bus and scheduler plumbing."""

    name = "scripted"

    def __init__(self, bus: GuestBus, operations: list[tuple[str, int, int, int]]) -> None:
        self.bus = bus
        self.operations = operations
        self.pc = 0
        self.halted = False

    def reset(self) -> None:
        self.pc = 0
        self.halted = False

    def step(self, budget: int) -> StepResult:
        if budget < 0:
            raise ValueError("budget cannot be negative")
        if self.halted:
            return StepResult(0, halted=True)
        consumed = 0
        while consumed < budget and self.pc < len(self.operations):
            op, address, value, width = self.operations[self.pc]
            if op == "write":
                self.bus.write(address, value, width)
            elif op == "read":
                observed = self.bus.read(address, width)
                if observed != value:
                    self.halted = True
                    return StepResult(
                        consumed + 1,
                        halted=True,
                        fault=(
                            f"read mismatch at operation {self.pc}: expected 0x{value:X}, "
                            f"observed 0x{observed:X}"
                        ),
                    )
            else:
                raise ValueError(f"unknown scripted operation {op!r}")
            self.pc += 1
            consumed += 1
        if self.pc >= len(self.operations):
            self.halted = True
        return StepResult(consumed, halted=self.halted, yielded=not self.halted)

    def save_state(self) -> bytes:
        return self.pc.to_bytes(4, "little") + bytes([self.halted])

    def load_state(self, state: bytes) -> None:
        if len(state) != 5:
            raise ValueError("scripted guest state must be 5 bytes")
        self.pc = int.from_bytes(state[:4], "little")
        self.halted = bool(state[4])
        if self.pc > len(self.operations):
            raise ValueError("scripted guest state PC is outside operation list")
