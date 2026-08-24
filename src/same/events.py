"""Deterministic fixed-capacity event queues."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from .abi import Endpoint, Packet, PacketFlag
from .errors import QueueFullError


@dataclass(slots=True)
class QueueStats:
    pushed: int = 0
    popped: int = 0
    rejected: int = 0
    dropped: int = 0
    high_water: int = 0


class EventRing:
    """A fail-closed FIFO matching the intended 65816 ring behavior.

    Nothing is overwritten silently.  A packet marked DROP_OK may be discarded and
    counted; every other overflow raises QueueFullError so a target cannot continue
    after losing a semantically required command.
    """

    def __init__(self, capacity: int = 32) -> None:
        if capacity <= 0 or capacity > 0xFFFF:
            raise ValueError("capacity must be in 1..65535")
        self.capacity = capacity
        self._slots: list[Packet | None] = [None] * capacity
        self._head = 0
        self._tail = 0
        self._count = 0
        self.stats = QueueStats()

    def __len__(self) -> int:
        return self._count

    @property
    def free(self) -> int:
        return self.capacity - self._count

    def push(self, packet: Packet) -> bool:
        if self._count == self.capacity:
            if int(packet.flags) & int(PacketFlag.DROP_OK):
                self.stats.dropped += 1
                return False
            self.stats.rejected += 1
            raise QueueFullError(
                f"SAME event ring is full ({self.capacity} records); "
                f"rejected {packet.service_name}/{packet.opcode_name}"
            )
        self._slots[self._tail] = packet
        self._tail = (self._tail + 1) % self.capacity
        self._count += 1
        self.stats.pushed += 1
        self.stats.high_water = max(self.stats.high_water, self._count)
        return True

    def pop(self) -> Packet | None:
        if not self._count:
            return None
        packet = self._slots[self._head]
        self._slots[self._head] = None
        self._head = (self._head + 1) % self.capacity
        self._count -= 1
        self.stats.popped += 1
        assert packet is not None
        return packet

    def drain(self, maximum: int | None = None) -> Iterator[Packet]:
        remaining = self._count if maximum is None else min(maximum, self._count)
        for _ in range(remaining):
            packet = self.pop()
            assert packet is not None
            yield packet

    def clear(self) -> None:
        while self.pop() is not None:
            pass

    def snapshot(self) -> list[Packet]:
        result: list[Packet] = []
        index = self._head
        for _ in range(self._count):
            packet = self._slots[index]
            assert packet is not None
            result.append(packet)
            index = (index + 1) % self.capacity
        return result


class EventBus:
    """Sequence-numbering wrapper around EventRing."""

    def __init__(self, capacity: int = 32) -> None:
        self.ring = EventRing(capacity)
        self._sequence = 0

    @property
    def next_sequence(self) -> int:
        return self._sequence

    def emit(
        self,
        *,
        service: int,
        opcode: int,
        arg0: int = 0,
        arg1: int = 0,
        flags: int = 0,
        source: int = Endpoint.TARGET,
        destination: int = Endpoint.KERNEL,
    ) -> Packet:
        packet = Packet(
            service=service,
            opcode=opcode,
            arg0=arg0,
            arg1=arg1,
            flags=flags,
            source=source,
            destination=destination,
            sequence=self._sequence,
        )
        accepted = self.ring.push(packet)
        if accepted:
            self._sequence = (self._sequence + 1) & 0xFFFF
        return packet

    def extend(self, packets: Iterable[Packet]) -> None:
        for packet in packets:
            self.ring.push(packet)
