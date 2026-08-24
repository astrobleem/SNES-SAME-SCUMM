"""MSU-1-friendly SAME package files.

The format is intentionally flat: a fixed header, fixed-size directory entries,
and aligned raw sections.  An SNES target can read the directory once and seek
straight to a section without parsing JSON at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import struct
import zlib

from .errors import PackageFormatError

MAGIC = b"SAMEPKG\0"
VERSION = 1
HEADER_SIZE = 32
ENTRY_SIZE = 32
_HEADER = struct.Struct("<8sHHHHIIII")
_ENTRY = struct.Struct("<8s4sHBBIIII")
assert _HEADER.size == HEADER_SIZE
assert _ENTRY.size == ENTRY_SIZE

FLAG_EXECUTABLE = 1 << 0
FLAG_STREAMABLE = 1 << 1
FLAG_READ_ONLY = 1 << 2


@dataclass(frozen=True, slots=True)
class Section:
    name: str
    kind: str
    flags: int
    alignment: int
    offset: int
    size: int
    unpacked_size: int
    crc32: int

    def to_dict(self) -> dict[str, int | str]:
        return {
            "name": self.name,
            "kind": self.kind,
            "flags": self.flags,
            "alignment": self.alignment,
            "offset": self.offset,
            "size": self.size,
            "unpacked_size": self.unpacked_size,
            "crc32": f"{self.crc32:08x}",
        }


@dataclass(frozen=True, slots=True)
class PackageInfo:
    path: Path
    flags: int
    crc32: int
    sections: tuple[Section, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "version": VERSION,
            "flags": self.flags,
            "crc32": f"{self.crc32:08x}",
            "sections": [section.to_dict() for section in self.sections],
        }


def _alignment_log2(alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise PackageFormatError(f"alignment {alignment} is not a power of two")
    result = alignment.bit_length() - 1
    if result > 31:
        raise PackageFormatError("alignment exceeds 2 GiB")
    return result


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def _encode_name(name: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,8}", name):
        raise PackageFormatError(
            f"section name {name!r} must be 1..8 ASCII letters, digits, '.', '_' or '-'"
        )
    return name.encode("ascii").ljust(8, b"\0")


def _encode_kind(kind: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_]{4}", kind):
        raise PackageFormatError(f"section kind {kind!r} must be exactly four ASCII characters")
    return kind.encode("ascii")


def _parse_flags(values: object) -> int:
    if values is None:
        return 0
    if isinstance(values, int):
        if values < 0 or values > 0xFFFF:
            raise PackageFormatError("section flags must fit u16")
        return values
    if not isinstance(values, list):
        raise PackageFormatError("section flags must be an integer or list")
    names = {
        "executable": FLAG_EXECUTABLE,
        "streamable": FLAG_STREAMABLE,
        "read_only": FLAG_READ_ONLY,
    }
    result = 0
    for value in values:
        try:
            result |= names[str(value)]
        except KeyError as exc:
            raise PackageFormatError(f"unknown section flag {value!r}") from exc
    return result


def build_package(manifest_path: Path, output_path: Path, poppy_include: Path | None = None) -> PackageInfo:
    manifest_path = manifest_path.resolve()
    root = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageFormatError(f"cannot read package manifest {manifest_path}: {exc}") from exc
    if manifest.get("same_package") != 1:
        raise PackageFormatError("manifest must contain same_package: 1")
    raw_sections = manifest.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise PackageFormatError("manifest sections must be a non-empty list")

    names: set[str] = set()
    loaded: list[tuple[str, str, int, int, bytes]] = []
    for index, item in enumerate(raw_sections):
        if not isinstance(item, dict):
            raise PackageFormatError(f"section {index} is not an object")
        name = str(item.get("name", ""))
        _encode_name(name)
        if name in names:
            raise PackageFormatError(f"duplicate section name {name!r}")
        names.add(name)
        kind = str(item.get("kind", ""))
        _encode_kind(kind)
        flags = _parse_flags(item.get("flags"))
        alignment = int(item.get("alignment", 1))
        _alignment_log2(alignment)
        source = root / str(item.get("path", ""))
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise PackageFormatError(f"cannot read section {name} from {source}: {exc}") from exc
        loaded.append((name, kind, flags, alignment, data))

    directory_offset = HEADER_SIZE
    data_offset = _align(HEADER_SIZE + ENTRY_SIZE * len(loaded), 16)
    cursor = data_offset
    entries: list[bytes] = []
    payload = bytearray(data_offset - HEADER_SIZE - ENTRY_SIZE * len(loaded))
    sections: list[Section] = []
    data_chunks: list[tuple[int, bytes]] = []

    for name, kind, flags, alignment, data in loaded:
        offset = _align(cursor, alignment)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        section = Section(
            name=name,
            kind=kind,
            flags=flags,
            alignment=alignment,
            offset=offset,
            size=len(data),
            unpacked_size=len(data),
            crc32=crc,
        )
        sections.append(section)
        entries.append(
            _ENTRY.pack(
                _encode_name(name),
                _encode_kind(kind),
                flags,
                _alignment_log2(alignment),
                0,
                offset,
                len(data),
                len(data),
                crc,
            )
        )
        data_chunks.append((offset, data))
        cursor = offset + len(data)

    body = bytearray(cursor - HEADER_SIZE)
    directory = b"".join(entries)
    body[0 : len(directory)] = directory
    # bytes between the directory and data are already zeroed
    for offset, data in data_chunks:
        start = offset - HEADER_SIZE
        body[start : start + len(data)] = data
    package_crc = zlib.crc32(body) & 0xFFFFFFFF
    package_flags = int(manifest.get("flags", 0))
    if package_flags < 0 or package_flags > 0xFFFFFFFF:
        raise PackageFormatError("package flags must fit u32")
    header = _HEADER.pack(
        MAGIC,
        VERSION,
        HEADER_SIZE,
        len(sections),
        ENTRY_SIZE,
        directory_offset,
        data_offset,
        package_flags,
        package_crc,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(header + body)
    info = inspect_package(output_path, verify=True)
    if poppy_include is not None:
        generate_poppy_include(info, poppy_include)
    return info


def inspect_package(path: Path, verify: bool = True) -> PackageInfo:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PackageFormatError(f"cannot read {path}: {exc}") from exc
    if len(raw) < HEADER_SIZE:
        raise PackageFormatError("file is shorter than the SAME package header")
    magic, version, header_size, count, entry_size, directory_offset, data_offset, flags, package_crc = (
        _HEADER.unpack_from(raw, 0)
    )
    if magic != MAGIC:
        raise PackageFormatError(f"bad package magic {magic!r}")
    if version != VERSION:
        raise PackageFormatError(f"unsupported package version {version}")
    if header_size != HEADER_SIZE or entry_size != ENTRY_SIZE:
        raise PackageFormatError("header or directory entry size does not match version 1")
    directory_end = directory_offset + count * entry_size
    if directory_offset < HEADER_SIZE or directory_end > len(raw):
        raise PackageFormatError("directory lies outside the package")
    if data_offset < directory_end or data_offset > len(raw):
        raise PackageFormatError("data offset is invalid")
    if verify:
        actual = zlib.crc32(raw[HEADER_SIZE:]) & 0xFFFFFFFF
        if actual != package_crc:
            raise PackageFormatError(
                f"package CRC mismatch: header {package_crc:08x}, actual {actual:08x}"
            )

    sections: list[Section] = []
    names: set[str] = set()
    ranges: list[tuple[int, int, str]] = []
    for index in range(count):
        start = directory_offset + index * entry_size
        name_raw, kind_raw, section_flags, align_log2, reserved, offset, size, unpacked, crc = (
            _ENTRY.unpack_from(raw, start)
        )
        if reserved:
            raise PackageFormatError(f"section {index} has nonzero reserved byte")
        try:
            name = name_raw.rstrip(b"\0").decode("ascii")
            kind = kind_raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise PackageFormatError(f"section {index} has non-ASCII metadata") from exc
        _encode_name(name)
        _encode_kind(kind)
        if name in names:
            raise PackageFormatError(f"duplicate section name {name!r}")
        names.add(name)
        alignment = 1 << align_log2
        if offset % alignment:
            raise PackageFormatError(f"section {name} is not aligned to {alignment}")
        end = offset + size
        if offset < data_offset or end > len(raw):
            raise PackageFormatError(f"section {name} lies outside package data")
        if unpacked != size:
            raise PackageFormatError(
                f"section {name} requests compression, unsupported by format version 1"
            )
        if verify:
            actual = zlib.crc32(raw[offset:end]) & 0xFFFFFFFF
            if actual != crc:
                raise PackageFormatError(
                    f"section {name} CRC mismatch: directory {crc:08x}, actual {actual:08x}"
                )
        ranges.append((offset, end, name))
        sections.append(
            Section(name, kind, section_flags, alignment, offset, size, unpacked, crc)
        )
    for (left_start, left_end, left_name), (right_start, _, right_name) in zip(
        sorted(ranges), sorted(ranges)[1:]
    ):
        if left_end > right_start:
            raise PackageFormatError(f"sections {left_name} and {right_name} overlap")
    return PackageInfo(path=path, flags=flags, crc32=package_crc, sections=tuple(sections))


def extract_package(path: Path, output_dir: Path) -> PackageInfo:
    info = inspect_package(path, verify=True)
    raw = path.read_bytes()
    output_dir.mkdir(parents=True, exist_ok=True)
    for section in info.sections:
        (output_dir / section.name).write_bytes(
            raw[section.offset : section.offset + section.size]
        )
    (output_dir / "manifest.json").write_text(
        json.dumps(info.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return info


def _symbol(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", name).upper()


def generate_poppy_include(info: PackageInfo, path: Path) -> None:
    lines = [
        "; Generated by `same package build`; do not edit by hand.",
        f"SAME_PACKAGE_SECTION_COUNT               = ${len(info.sections):04X}",
        f"SAME_PACKAGE_CRC32                       = ${info.crc32:08X}",
        "",
    ]
    for index, section in enumerate(info.sections):
        prefix = f"SAME_PKG_{_symbol(section.name)}"
        lines.extend(
            [
                f"{prefix + '_INDEX':<40} = ${index:04X}",
                f"{prefix + '_OFFSET':<40} = ${section.offset:08X}",
                f"{prefix + '_SIZE':<40} = ${section.size:08X}",
                f"{prefix + '_CRC32':<40} = ${section.crc32:08X}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
