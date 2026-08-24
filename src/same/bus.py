"""Target-defined foreign address spaces.

SAME CPU cores do not know about Genesis, Taito X, or Black Tiger hardware. They
read and write a GuestBus. Targets map RAM, ROM, and device portals into that bus;
the portals translate hardware traffic into SAME service packets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Iterable

from .errors import SameError


class BusError(SameError):
    pass


class Endianness(str, Enum):
    LITTLE = "little"
    BIG = "big"


ReadCallback = Callable[[int], int]
WriteCallback = Callable[[int, int], None]
TraceCallback = Callable[[dict[str, int | str]], None]


@dataclass(slots=True)
class Region:
    name: str
    start: int
    size: int
    readable: bool = True
    writable: bool = True
    backing: bytearray | bytes | None = None
    read_callback: ReadCallback | None = None
    write_callback: WriteCallback | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("region name is required")
        if self.start < 0 or self.size <= 0:
            raise ValueError("region start and size must be positive")
        if self.backing is not None and len(self.backing) != self.size:
            raise ValueError(
                f"region {self.name}: backing is {len(self.backing)} bytes, expected {self.size}"
            )
        if self.backing is None and self.read_callback is None and self.write_callback is None:
            raise ValueError(f"region {self.name}: no backing or device callback")
        if isinstance(self.backing, bytes) and self.writable:
            raise ValueError(f"region {self.name}: immutable bytes cannot be writable")

    @property
    def end(self) -> int:
        return self.start + self.size

    def contains(self, address: int) -> bool:
        return self.start <= address < self.end

    def read8(self, address: int) -> int:
        if not self.readable:
            raise BusError(f"read from write-only region {self.name} at 0x{address:X}")
        offset = address - self.start
        if self.read_callback is not None:
            value = int(self.read_callback(offset))
        elif self.backing is not None:
            value = int(self.backing[offset])
        else:
            raise BusError(f"region {self.name} has no read implementation")
        if not 0 <= value <= 0xFF:
            raise BusError(f"region {self.name} returned non-byte value {value}")
        return value

    def write8(self, address: int, value: int) -> None:
        if not self.writable:
            raise BusError(f"write to read-only region {self.name} at 0x{address:X}")
        if not 0 <= value <= 0xFF:
            raise BusError(f"write value {value} does not fit a byte")
        offset = address - self.start
        if self.write_callback is not None:
            self.write_callback(offset, value)
        elif isinstance(self.backing, bytearray):
            self.backing[offset] = value
        else:
            raise BusError(f"region {self.name} has no write implementation")


class GuestBus:
    def __init__(
        self,
        *,
        address_bits: int,
        endianness: Endianness | str,
        trace: TraceCallback | None = None,
    ) -> None:
        if address_bits <= 0 or address_bits > 32:
            raise ValueError("address_bits must be in 1..32")
        self.address_bits = address_bits
        self.address_mask = (1 << address_bits) - 1
        self.endianness = Endianness(endianness)
        self.trace = trace
        self._regions: list[Region] = []

    @property
    def regions(self) -> tuple[Region, ...]:
        return tuple(self._regions)

    def map(self, region: Region) -> None:
        if region.end - 1 > self.address_mask:
            raise BusError(
                f"region {region.name} ends at 0x{region.end - 1:X}, outside "
                f"{self.address_bits}-bit bus"
            )
        for current in self._regions:
            if region.start < current.end and current.start < region.end:
                raise BusError(
                    f"region {region.name} [0x{region.start:X},0x{region.end:X}) overlaps "
                    f"{current.name} [0x{current.start:X},0x{current.end:X})"
                )
        self._regions.append(region)
        self._regions.sort(key=lambda item: item.start)

    def map_ram(self, name: str, start: int, size: int, initial: bytes | None = None) -> bytearray:
        backing = bytearray(size)
        if initial is not None:
            if len(initial) > size:
                raise BusError(f"initial image for {name} exceeds RAM region")
            backing[: len(initial)] = initial
        self.map(Region(name, start, size, backing=backing))
        return backing

    def map_rom(self, name: str, start: int, data: bytes) -> bytes:
        self.map(Region(name, start, len(data), writable=False, backing=data))
        return data

    def map_device(
        self,
        name: str,
        start: int,
        size: int,
        *,
        read: ReadCallback | None = None,
        write: WriteCallback | None = None,
    ) -> None:
        self.map(
            Region(
                name,
                start,
                size,
                readable=read is not None,
                writable=write is not None,
                read_callback=read,
                write_callback=write,
            )
        )

    def _address(self, address: int) -> int:
        if address < 0 or address > self.address_mask:
            raise BusError(
                f"address 0x{address:X} is outside {self.address_bits}-bit guest bus"
            )
        return address

    def _region(self, address: int) -> Region:
        address = self._address(address)
        for region in self._regions:
            if region.contains(address):
                return region
        raise BusError(f"unmapped guest address 0x{address:X}")

    def read8(self, address: int) -> int:
        address = self._address(address)
        region = self._region(address)
        value = region.read8(address)
        if self.trace:
            self.trace({"op": "read", "width": 1, "address": address, "value": value, "region": region.name})
        return value

    def write8(self, address: int, value: int) -> None:
        address = self._address(address)
        region = self._region(address)
        region.write8(address, value)
        if self.trace:
            self.trace({"op": "write", "width": 1, "address": address, "value": value, "region": region.name})

    def read(self, address: int, width: int) -> int:
        if width not in (1, 2, 4):
            raise ValueError("bus width must be 1, 2, or 4 bytes")
        values = [self.read8(address + offset) for offset in range(width)]
        return int.from_bytes(bytes(values), self.endianness.value)

    def write(self, address: int, value: int, width: int) -> None:
        if width not in (1, 2, 4):
            raise ValueError("bus width must be 1, 2, or 4 bytes")
        if value < 0 or value >= 1 << (width * 8):
            raise BusError(f"value 0x{value:X} does not fit {width} bytes")
        raw = value.to_bytes(width, self.endianness.value)
        # Validate the complete access before producing device side effects.
        regions = [self._region(address + offset) for offset in range(width)]
        if any(not region.writable for region in regions):
            bad = next(region for region in regions if not region.writable)
            raise BusError(f"write crosses read-only region {bad.name}")
        for offset, byte in enumerate(raw):
            self.write8(address + offset, byte)

    def read16(self, address: int) -> int:
        return self.read(address, 2)

    def read32(self, address: int) -> int:
        return self.read(address, 4)

    def write16(self, address: int, value: int) -> None:
        self.write(address, value, 2)

    def write32(self, address: int, value: int) -> None:
        self.write(address, value, 4)

    def describe(self) -> list[dict[str, int | str | bool]]:
        return [
            {
                "name": region.name,
                "start": region.start,
                "end": region.end,
                "size": region.size,
                "readable": region.readable,
                "writable": region.writable,
                "device": region.backing is None,
            }
            for region in self._regions
        ]
