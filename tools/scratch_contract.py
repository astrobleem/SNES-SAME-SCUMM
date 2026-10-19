"""Executable ownership contract for the existing room-pending scratch.

This is a host model for native ticket/ownership transitions, not another
resource layer. ProgramUnit cache pages remain independent and unavailable to
actor pixels.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import zlib


class Busy(RuntimeError):
    pass


class Owner(Enum):
    NONE = 0
    ACTOR = 1
    ROOM = 2


class Phase(Enum):
    FREE = 0
    READING = 1
    READY = 2


@dataclass(frozen=True)
class Ticket:
    serial: int
    room_epoch: int
    costume_epoch: int
    length: int
    crc32: int


class Scratch:
    def __init__(self, capacity: int = 3132):
        if capacity < 2048:
            raise ValueError("scratch must fit the established 2-KiB transfer")
        self.capacity = capacity
        self.owner = Owner.NONE
        self.phase = Phase.FREE
        self.serial = 0
        self.room_requested = False
        self.ticket: Ticket | None = None
        self.payload = b""
        self.discard = False

    def request_actor(self, *, room_epoch: int, costume_epoch: int,
                      length: int, crc32: int, provider_idle: bool,
                      room_idle: bool) -> Ticket:
        if (self.owner is not Owner.NONE or self.room_requested
                or not provider_idle or not room_idle):
            raise Busy("room/provider/scratch owns the resource boundary")
        if not 1 <= length <= min(2048, self.capacity) or not 0 <= crc32 <= 0xFFFFFFFF:
            raise ValueError("invalid checked actor chunk")
        self.serial += 1
        self.ticket = Ticket(self.serial, room_epoch, costume_epoch, length, crc32)
        self.owner, self.phase = Owner.ACTOR, Phase.READING
        self.discard = False
        self.payload = b""
        return self.ticket

    def request_room(self) -> bool:
        """Signal room priority without overwriting an in-flight actor read."""
        self.room_requested = True
        if self.owner is Owner.ACTOR:
            if self.phase is Phase.READING:
                self.discard = True
                return False
            self._release()
        return self.owner is Owner.NONE

    def complete_actor(self, ticket: Ticket, payload: bytes, *,
                       current_room_epoch: int, current_costume_epoch: int) -> bool:
        if (self.owner is not Owner.ACTOR or self.phase is not Phase.READING
                or ticket != self.ticket):
            raise ValueError("stale or foreign provider completion")
        valid = (len(payload) == ticket.length
                 and (zlib.crc32(payload) & 0xFFFFFFFF) == ticket.crc32
                 and ticket.room_epoch == current_room_epoch
                 and ticket.costume_epoch == current_costume_epoch
                 and not self.discard and not self.room_requested)
        if not valid:
            self._release()
            return False
        self.payload = bytes(payload)
        self.phase = Phase.READY
        return True

    def consume_actor(self, ticket: Ticket, *, surface_writable: bool) -> bytes | None:
        if (ticket != self.ticket or self.owner is not Owner.ACTOR
                or self.phase is not Phase.READY):
            raise ValueError("actor has no matching READY scratch")
        if not surface_writable:
            return None
        data = self.payload
        self._release()
        return data

    def claim_room(self) -> None:
        if self.owner is not Owner.NONE:
            raise Busy("cannot reuse in-flight actor storage")
        self.owner = Owner.ROOM
        self.phase = Phase.READING

    def release_room(self) -> None:
        if self.owner is not Owner.ROOM:
            raise ValueError("room does not own scratch")
        self._release()
        self.room_requested = False

    def _release(self) -> None:
        self.owner = Owner.NONE
        self.phase = Phase.FREE
        self.ticket = None
        self.payload = b""
        self.discard = False
