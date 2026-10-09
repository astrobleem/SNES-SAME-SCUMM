"""Checked SAMEPKG reads over the MSU-1's single serialized data cursor.

The MSU-1 is not treated as a file API: this layer supplies the trusted package
length and metadata, performs checked 32-bit seeks, bounds status polling, and
validates each returned range before publishing it to the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import struct
import zlib

from .errors import PackageFormatError
from .package import ENTRY_SIZE, HEADER_SIZE, MAGIC, VERSION, PackageInfo, inspect_package

MSU1_ID = b"S-MSU1"
MSU1_STATUS_DATA_BUSY = 0x80
_HEADER = struct.Struct("<8sHHHHIIII")
_ENTRY = struct.Struct("<8s4sHBBIIII")
_U32_MAX = 0xFFFFFFFF


class ReadStatus(str, Enum):
    OK = "OK"
    NO_DEVICE = "NO_DEVICE"
    BUSY_TIMEOUT = "BUSY_TIMEOUT"
    PACKAGE_IDENTITY = "PACKAGE_IDENTITY"
    PACKAGE_DIRECTORY = "PACKAGE_DIRECTORY"
    RANGE_ERROR = "RANGE_ERROR"
    DESTINATION_TOO_SMALL = "DESTINATION_TOO_SMALL"
    SECTION_CRC = "SECTION_CRC"
    DEVICE_SHORT_READ = "DEVICE_SHORT_READ"


class Msu1ReadError(PackageFormatError):
    """A checked read failed; ``status`` is stable for diagnostics/tests."""

    def __init__(self, status: ReadStatus, detail: str):
        self.status = status
        super().__init__(f"{status.value}: {detail}")


class DataPort:
    """Minimal MSU-1 data-port protocol, intentionally independent of audio."""

    def identify(self) -> bytes:
        raise NotImplementedError

    def seek(self, offset: int) -> None:
        raise NotImplementedError

    def status(self) -> int:
        raise NotImplementedError

    def read_data(self) -> int:
        raise NotImplementedError


@dataclass
class FileDataPort(DataPort):
    """Host oracle for native protocol tests; not evidence of device behavior."""

    path: Path
    present: bool = True
    busy_reads: int = 0
    busy_stuck: bool = False
    missing_id: bool = False
    cursor: int = 0
    _busy_remaining: int = 0
    _data: bytes | None = None

    def __post_init__(self) -> None:
        if self.present:
            self._data = self.path.read_bytes()

    def identify(self) -> bytes:
        if not self.present or self.missing_id:
            return b"\0" * 6
        return MSU1_ID

    def seek(self, offset: int) -> None:
        self.cursor = offset & _U32_MAX
        self._busy_remaining = self.busy_reads

    def status(self) -> int:
        if self.busy_stuck or self._busy_remaining:
            if not self.busy_stuck:
                self._busy_remaining -= 1
            return MSU1_STATUS_DATA_BUSY | 0x40  # audio busy is unrelated
        return 0x40  # proves callers mask only data-busy bit 7

    def read_data(self) -> int:
        if not self.present or self._data is None:
            raise OSError("MSU-1 peripheral absent")
        if self.cursor >= len(self._data):
            raise EOFError("host file ended before trusted package length")
        value = self._data[self.cursor]
        self.cursor = (self.cursor + 1) & _U32_MAX
        return value


@dataclass(frozen=True, slots=True)
class ReadResult:
    status: ReadStatus
    offset: int
    length: int
    crc32: int
    data: bytes


class CheckedPackageReader:
    """Synchronous reference contract with bounded chunks and atomic publish."""

    def __init__(
        self,
        port: DataPort,
        trusted: PackageInfo,
        *,
        package_length: int,
        busy_poll_limit: int = 64,
        transfer_budget: int = 256,
    ) -> None:
        if not 0 <= package_length <= _U32_MAX:
            raise ValueError("trusted package length must fit u32")
        if busy_poll_limit <= 0 or transfer_budget <= 0:
            raise ValueError("poll limit and transfer budget must be positive")
        self.port = port
        self.trusted = trusted
        self.package_length = package_length
        self.busy_poll_limit = busy_poll_limit
        self.transfer_budget = transfer_budget
        self.initialized = False
        self.last_status = ReadStatus.OK
        self.last_offset = 0
        self.bytes_transferred = 0
        self.seek_count = 0
        self._trusted_prefix = self._load_trusted_prefix(trusted)

    @staticmethod
    def _load_trusted_prefix(trusted: PackageInfo) -> bytes:
        # Re-inspection is intentionally offline/host-side. On target the same
        # checked bytes are emitted as a small compiler-owned ROM directory.
        inspected = inspect_package(trusted.path, verify=True)
        raw = trusted.path.read_bytes()
        if inspected != trusted:
            raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, "trusted package metadata changed")
        header = _HEADER.unpack_from(raw)
        count = header[3]
        directory_offset = header[5]
        directory_end = directory_offset + count * ENTRY_SIZE
        if count != len(trusted.sections) or directory_end > len(raw):
            raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, "trusted directory is invalid")
        return raw[:directory_end]

    def _wait_data_ready(self) -> None:
        for _ in range(self.busy_poll_limit):
            if not (self.port.status() & MSU1_STATUS_DATA_BUSY):
                return
        raise Msu1ReadError(ReadStatus.BUSY_TIMEOUT, "MSU data port remained busy")

    def _seek(self, offset: int) -> None:
        self.port.seek(offset)
        self.seek_count += 1

    def _read_exact(self, offset: int, length: int) -> bytes:
        self._seek(offset)
        result = bytearray()
        while len(result) < length:
            self._wait_data_ready()
            amount = min(self.transfer_budget, length - len(result))
            for _ in range(amount):
                try:
                    result.append(self.port.read_data())
                except (OSError, EOFError) as exc:
                    raise Msu1ReadError(ReadStatus.DEVICE_SHORT_READ, str(exc)) from exc
                self.bytes_transferred += 1
        return bytes(result)

    def initialize(self) -> None:
        if self.port.identify() != MSU1_ID:
            self.last_status = ReadStatus.NO_DEVICE
            raise Msu1ReadError(ReadStatus.NO_DEVICE, "MSU-1 ID is absent or invalid")
        header = self._trusted_prefix[:HEADER_SIZE]
        try:
            fields = _HEADER.unpack(header)
        except struct.error as exc:
            raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, "trusted header is truncated") from exc
        magic, version, hsize, count, esize, directory_offset, data_offset, _flags, _crc = fields
        directory_end = directory_offset + count * esize
        if (
            magic != MAGIC
            or version != VERSION
            or hsize != HEADER_SIZE
            or esize != ENTRY_SIZE
            or count != len(self.trusted.sections)
            or directory_offset < HEADER_SIZE
            or directory_end > self.package_length
            or directory_end > len(self._trusted_prefix)
            or data_offset < directory_end
            or data_offset > self.package_length
        ):
            self.last_status = ReadStatus.PACKAGE_DIRECTORY
            raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, "trusted SAMEPKG v1 header is invalid")
        actual = self._read_exact(0, len(self._trusted_prefix))
        if actual != self._trusted_prefix:
            self.last_status = ReadStatus.PACKAGE_IDENTITY
            raise Msu1ReadError(
                ReadStatus.PACKAGE_IDENTITY,
                "device package header/directory differs from trusted build identity",
            )
        self._validate_directory(actual, fields)
        self.initialized = True
        self.last_status = ReadStatus.OK

    def _validate_directory(self, raw: bytes, fields: tuple[object, ...]) -> None:
        _magic, _version, _hsize, count, esize, directory_offset, data_offset, _flags, _crc = fields
        ranges: list[tuple[int, int, str]] = []
        names: set[str] = set()
        for i in range(int(count)):
            entry_at = int(directory_offset) + i * int(esize)
            name_raw, kind_raw, flags, align_log2, reserved, offset, size, unpacked, crc = (
                _ENTRY.unpack_from(raw, entry_at)
            )
            try:
                name = name_raw.rstrip(b"\0").decode("ascii")
                kind = kind_raw.decode("ascii")
            except UnicodeDecodeError as exc:
                raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, "non-ASCII directory entry") from exc
            if (
                not name
                or not kind
                or name in names
                or reserved
                or align_log2 > 31
                or size != unpacked
                or offset < int(data_offset)
                or offset + size > self.package_length
                or offset + size > _U32_MAX + 1
                or offset & ((1 << align_log2) - 1)
            ):
                raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, f"invalid entry {i}: {name!r}")
            names.add(name)
            ranges.append((offset, offset + size, name))
            section = self.trusted.sections[i]
            if (
                name != section.name
                or kind != section.kind
                or flags != section.flags
                or size != section.size
                or crc != section.crc32
            ):
                raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, f"entry {name} is not trusted")
        ranges.sort()
        for left, right in zip(ranges, ranges[1:]):
            if left[1] > right[0]:
                raise Msu1ReadError(ReadStatus.PACKAGE_DIRECTORY, f"sections {left[2]} and {right[2]} overlap")

    def read_range(
        self,
        offset: int,
        length: int,
        destination: bytearray,
        *,
        capacity: int | None = None,
        expected_crc32: int | None = None,
    ) -> ReadResult:
        if not self.initialized:
            self.initialize()
        capacity = len(destination) if capacity is None else capacity
        if offset < 0 or length < 0 or offset > _U32_MAX or length > _U32_MAX:
            return self._fail(ReadStatus.RANGE_ERROR, offset, length, "negative or non-u32 range")
        end = offset + length
        if end > _U32_MAX + 1 or end < offset or end > self.package_length:
            return self._fail(ReadStatus.RANGE_ERROR, offset, length, "range exceeds trusted package bounds")
        if capacity < 0 or capacity > len(destination) or length > capacity:
            return self._fail(ReadStatus.DESTINATION_TOO_SMALL, offset, length, "destination capacity is insufficient")
        # A zero-byte read at EOF is legal and must not touch the data port.
        if length == 0:
            return ReadResult(ReadStatus.OK, offset, 0, 0, b"")
        try:
            staged = self._read_exact(offset, length)
        except Msu1ReadError as exc:
            self.last_status = exc.status
            raise
        crc = zlib.crc32(staged) & _U32_MAX
        if expected_crc32 is not None and crc != expected_crc32:
            return self._fail(ReadStatus.SECTION_CRC, offset, length, f"expected {expected_crc32:08x}, got {crc:08x}")
        destination[:length] = staged
        self.last_status = ReadStatus.OK
        self.last_offset = offset
        return ReadResult(ReadStatus.OK, offset, length, crc, staged)

    def read_section(self, name: str, destination: bytearray, *, capacity: int | None = None) -> ReadResult:
        section = next((item for item in self.trusted.sections if item.name == name), None)
        if section is None:
            return self._fail(ReadStatus.PACKAGE_DIRECTORY, 0, 0, f"unknown section {name!r}")
        return self.read_range(
            section.offset,
            section.size,
            destination,
            capacity=capacity,
            expected_crc32=section.crc32,
        )

    def _fail(self, status: ReadStatus, offset: int, length: int, detail: str) -> ReadResult:
        self.last_status = status
        raise Msu1ReadError(status, f"offset={offset:#010x}, length={length}: {detail}")


def trusted_package(path: Path) -> tuple[PackageInfo, int]:
    info = inspect_package(path, verify=True)
    return info, path.stat().st_size
