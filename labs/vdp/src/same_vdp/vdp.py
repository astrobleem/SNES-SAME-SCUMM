from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .trace import Trace, TraceError, intish

VRAM_SIZE = 0x10000
CRAM_WORDS = 0x40
VSRAM_WORDS = 0x40
REGISTER_COUNT = 0x20

VRAM_READ = 0x00
VRAM_WRITE = 0x01
CRAM_WRITE = 0x03
VSRAM_READ = 0x04
VSRAM_WRITE = 0x05
CRAM_READ = 0x08


def register_word(index: int, value: int) -> int:
    if not 0 <= index < REGISTER_COUNT:
        raise ValueError("VDP register index must be 0..31")
    if not 0 <= value <= 0xFF:
        raise ValueError("VDP register value must be 0..255")
    return 0x8000 | (index << 8) | value


def command_words(address: int, code: int) -> tuple[int, int]:
    """Encode a Mode-5 two-word control command.

    This is the inverse of the address/code latch behavior used by the Genesis VDP.
    """
    if not 0 <= address <= 0xFFFF:
        raise ValueError("VDP address must fit 16 bits")
    if not 0 <= code <= 0x3F:
        raise ValueError("VDP code must fit 6 bits")
    first = (address & 0x3FFF) | ((code & 0x03) << 14)
    second = ((address >> 14) & 0x03) | ((code & 0x3C) << 2)
    return first, second


def words_from_bytes(data: bytes) -> list[int]:
    if len(data) & 1:
        data += b"\x00"
    return [(data[index] << 8) | data[index + 1] for index in range(0, len(data), 2)]


def bytes_from_words(words: Iterable[int]) -> bytes:
    output = bytearray()
    for word in words:
        output.extend(((word >> 8) & 0xFF, word & 0xFF))
    return bytes(output)


def cram_bus_word(red: int, green: int, blue: int) -> int:
    """Pack 3-bit RGB as the VDP data-port form BBB0GGG0RRR0."""
    if not all(0 <= component <= 7 for component in (red, green, blue)):
        raise ValueError("Genesis CRAM components must be 0..7")
    return (blue << 9) | (green << 5) | (red << 1)


def cram_internal_from_bus(word: int) -> int:
    """Pack BBB0GGG0RRR0 into the internal 9-bit BBBGGGRRR form."""
    return ((word & 0x0E00) >> 3) | ((word & 0x00E0) >> 2) | ((word & 0x000E) >> 1)


def cram_components(internal: int) -> tuple[int, int, int]:
    red = internal & 0x07
    green = (internal >> 3) & 0x07
    blue = (internal >> 6) & 0x07
    return red, green, blue


@dataclass
class VDPState:
    """A deterministic Mode-5 register/VRAM/CRAM/VSRAM model.

    Timing, FIFO stalls, status reads, DMA scheduling, sprites and raster effects are
    deliberately outside milestone 0. Port command/address semantics and normal data
    writes are modeled so traces can later come directly from an emulator hook.
    """

    vram: bytearray = field(default_factory=lambda: bytearray(VRAM_SIZE))
    cram: list[int] = field(default_factory=lambda: [0] * CRAM_WORDS)
    vsram: list[int] = field(default_factory=lambda: [0] * VSRAM_WORDS)
    registers: bytearray = field(default_factory=lambda: bytearray(REGISTER_COUNT))
    address: int = 0
    address_latch: int = 0
    code: int = 0
    pending_control_word: bool = False
    frame_labels: list[str] = field(default_factory=list)

    def reset(self) -> None:
        self.vram[:] = b"\x00" * VRAM_SIZE
        self.cram[:] = [0] * CRAM_WORDS
        self.vsram[:] = [0] * VSRAM_WORDS
        self.registers[:] = b"\x00" * REGISTER_COUNT
        self.address = 0
        self.address_latch = 0
        self.code = 0
        self.pending_control_word = False
        self.frame_labels.clear()

    def write_control(self, word: int) -> None:
        word &= 0xFFFF
        if not self.pending_control_word:
            self.address = self.address_latch | (word & 0x3FFF)
            self.code = (self.code & 0x3C) | ((word >> 14) & 0x03)
            if (word & 0xC000) == 0x8000:
                self.write_register((word >> 8) & 0x1F, word & 0xFF)
                self.pending_control_word = False
            else:
                self.pending_control_word = bool(self.registers[1] & 0x04)
            return

        self.pending_control_word = False
        self.address_latch = (word & 0x03) << 14
        self.address = self.address_latch | (self.address & 0x3FFF)
        self.code = (self.code & 0x03) | ((word >> 2) & 0x3C)

    def write_register(self, index: int, value: int) -> None:
        self.registers[index & 0x1F] = value & 0xFF

    def write_data(self, word: int) -> None:
        self.pending_control_word = False
        word &= 0xFFFF
        destination = self.code & 0x0F
        if destination == VRAM_WRITE:
            self._write_vram_word(self.address, word)
        elif destination == CRAM_WRITE:
            self.cram[(self.address >> 1) & 0x3F] = cram_internal_from_bus(word)
        elif destination == VSRAM_WRITE:
            self.vsram[(self.address >> 1) & 0x3F] = word & 0x07FF
        else:
            raise TraceError(
                f"data write with unsupported VDP code 0x{self.code:02x} at 0x{self.address:04x}"
            )
        self.address = (self.address + self.registers[15]) & 0xFFFF

    def _write_vram_word(self, address: int, word: int) -> None:
        index = address & 0xFFFE
        high = (word >> 8) & 0xFF
        low = word & 0xFF
        if address & 1:
            high, low = low, high
        self.vram[index] = high
        self.vram[index + 1] = low

    def read_vram_word(self, address: int) -> int:
        index = address & 0xFFFE
        word = (self.vram[index] << 8) | self.vram[index + 1]
        if address & 1:
            word = ((word & 0xFF) << 8) | (word >> 8)
        return word

    @property
    def mode5(self) -> bool:
        return bool(self.registers[1] & 0x04)

    @property
    def display_enabled(self) -> bool:
        return bool(self.registers[1] & 0x40)

    @property
    def width(self) -> int:
        return 320 if (self.registers[12] & 0x01) else 256

    @property
    def height(self) -> int:
        return 240 if (self.registers[1] & 0x08) else 224

    @property
    def plane_a_base(self) -> int:
        return (self.registers[2] << 10) & 0xE000

    @property
    def plane_b_base(self) -> int:
        return (self.registers[4] << 13) & 0xE000

    @property
    def hscroll_base(self) -> int:
        return (self.registers[13] << 10) & 0xFC00

    @property
    def backdrop_index(self) -> int:
        return self.registers[7] & 0x3F

    @property
    def plane_size(self) -> tuple[int, int]:
        horizontal = {0: 32, 1: 64, 3: 128}.get(self.registers[16] & 0x03)
        vertical = {0: 32, 1: 64, 3: 128}.get((self.registers[16] >> 4) & 0x03)
        if horizontal is None or vertical is None:
            raise TraceError(f"invalid plane-size register value 0x{self.registers[16]:02x}")
        return horizontal, vertical

    def apply_event(self, event: dict[str, object]) -> None:
        op = event["op"]
        if op == "ctrl":
            self.write_control(intish(event["value"]))
        elif op == "data":
            self.write_data(intish(event["value"]))
        elif op == "data_words":
            for value in event["values"]:  # type: ignore[index]
                self.write_data(intish(value))
        elif op == "frame":
            self.frame_labels.append(str(event.get("label", f"frame{len(self.frame_labels):04d}")))
        elif op == "comment":
            return
        else:  # validated earlier, defensive for direct callers
            raise TraceError(f"unsupported operation: {op!r}")

    @classmethod
    def from_trace(cls, trace: Trace) -> "VDPState":
        state = cls()
        for event in trace.events:
            state.apply_event(event)
        if not state.mode5:
            raise TraceError("trace ended without Mode 5 enabled (register 1 bit 2)")
        return state
