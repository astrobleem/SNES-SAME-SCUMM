"""Engine resource providers.

Engines address resources by stable profile keys.  A key can be backed by a
plain file, a section in a SAME package, memory supplied by a test harness, or a
composite provider.  The engine never sees the physical storage decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable, Mapping, Protocol
import zlib

from .errors import ResourceError
from .package import inspect_package
from .profile import EngineProfile, ResourceBinding


@dataclass(frozen=True, slots=True)
class ResourceStat:
    key: str
    size: int
    kind: str = "DATA"
    streamable: bool = False
    crc32: int | None = None
    source: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "size": self.size,
            "kind": self.kind,
            "streamable": self.streamable,
            "crc32": None if self.crc32 is None else f"{self.crc32:08x}",
            "source": self.source,
        }


class ResourceProvider(Protocol):
    def keys(self) -> tuple[str, ...]: ...

    def contains(self, key: str) -> bool: ...

    def stat(self, key: str) -> ResourceStat: ...

    def read(self, key: str, offset: int = 0, length: int | None = None) -> bytes: ...

    def open(self, key: str) -> BinaryIO: ...


def _slice(data: bytes, key: str, offset: int, length: int | None) -> bytes:
    if offset < 0:
        raise ResourceError(f"resource {key!r}: offset must not be negative")
    if offset > len(data):
        raise ResourceError(
            f"resource {key!r}: offset {offset} lies beyond size {len(data)}"
        )
    if length is not None and length < 0:
        raise ResourceError(f"resource {key!r}: length must not be negative")
    end = len(data) if length is None else min(len(data), offset + length)
    return data[offset:end]


class MemoryResourceProvider:
    def __init__(
        self,
        resources: Mapping[str, bytes | bytearray | memoryview],
        *,
        kinds: Mapping[str, str] | None = None,
    ) -> None:
        self._resources = {str(key): bytes(value) for key, value in resources.items()}
        self._kinds = dict(kinds or {})

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._resources))

    def contains(self, key: str) -> bool:
        return key in self._resources

    def stat(self, key: str) -> ResourceStat:
        try:
            data = self._resources[key]
        except KeyError as exc:
            raise ResourceError(f"unknown resource {key!r}") from exc
        return ResourceStat(
            key=key,
            size=len(data),
            kind=self._kinds.get(key, "DATA"),
            crc32=zlib.crc32(data) & 0xFFFFFFFF,
            source="memory",
        )

    def read(self, key: str, offset: int = 0, length: int | None = None) -> bytes:
        try:
            data = self._resources[key]
        except KeyError as exc:
            raise ResourceError(f"unknown resource {key!r}") from exc
        return _slice(data, key, offset, length)

    def open(self, key: str) -> BinaryIO:
        return BytesIO(self.read(key))


class BoundResourceProvider:
    """Provider constructed directly from an :class:`EngineProfile`.

    Package-backed resources are verified through the SAME package parser on
    first access and then cached.  Plain files are read on demand so a converter
    can rebuild an asset without recreating the host object.
    """

    def __init__(self, bindings: Iterable[ResourceBinding]) -> None:
        self._bindings: dict[str, ResourceBinding] = {}
        self._package_cache: dict[Path, tuple[bytes, object]] = {}
        for binding in bindings:
            if binding.key in self._bindings:
                raise ResourceError(f"duplicate resource binding {binding.key!r}")
            self._bindings[binding.key] = binding

    @classmethod
    def from_profile(cls, profile: EngineProfile) -> "BoundResourceProvider":
        return cls(profile.resources)

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._bindings))

    def contains(self, key: str) -> bool:
        return key in self._bindings

    def _binding(self, key: str) -> ResourceBinding:
        try:
            return self._bindings[key]
        except KeyError as exc:
            raise ResourceError(f"unknown resource {key!r}") from exc

    def _read_whole(self, binding: ResourceBinding) -> bytes:
        if binding.package_section is None:
            try:
                return binding.path.read_bytes()
            except OSError as exc:
                raise ResourceError(
                    f"cannot read resource {binding.key!r} from {binding.path}: {exc}"
                ) from exc

        package_path = binding.path.resolve()
        cached = self._package_cache.get(package_path)
        if cached is None:
            try:
                raw = package_path.read_bytes()
                info = inspect_package(package_path, verify=True)
            except (OSError, Exception) as exc:
                if isinstance(exc, ResourceError):
                    raise
                raise ResourceError(f"cannot read SAME package {package_path}: {exc}") from exc
            cached = (raw, info)
            self._package_cache[package_path] = cached
        raw, info = cached
        section = next(
            (section for section in info.sections if section.name == binding.package_section),
            None,
        )
        if section is None:
            raise ResourceError(
                f"package {package_path} has no section {binding.package_section!r} "
                f"for resource {binding.key!r}"
            )
        data = raw[section.offset : section.offset + section.size]
        actual = zlib.crc32(data) & 0xFFFFFFFF
        if actual != section.crc32:
            raise ResourceError(
                f"package section {section.name!r} CRC mismatch: "
                f"expected {section.crc32:08x}, got {actual:08x}"
            )
        return data

    def stat(self, key: str) -> ResourceStat:
        binding = self._binding(key)
        data = self._read_whole(binding)
        return ResourceStat(
            key=key,
            size=len(data),
            kind=binding.kind,
            streamable=binding.streamable,
            crc32=zlib.crc32(data) & 0xFFFFFFFF,
            source=(
                f"{binding.path}#{binding.package_section}"
                if binding.package_section is not None
                else str(binding.path)
            ),
        )

    def read(self, key: str, offset: int = 0, length: int | None = None) -> bytes:
        binding = self._binding(key)
        return _slice(self._read_whole(binding), key, offset, length)

    def open(self, key: str) -> BinaryIO:
        return BytesIO(self.read(key))


class CompositeResourceProvider:
    """Search providers in order while rejecting ambiguous keys by default."""

    def __init__(
        self, providers: Iterable[ResourceProvider], *, allow_shadowing: bool = False
    ) -> None:
        self._providers = tuple(providers)
        if not self._providers:
            raise ResourceError("composite resource provider requires at least one provider")
        self._owner: dict[str, ResourceProvider] = {}
        for provider in self._providers:
            for key in provider.keys():
                if key in self._owner and not allow_shadowing:
                    raise ResourceError(f"resource key {key!r} is provided more than once")
                self._owner.setdefault(key, provider)

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._owner))

    def contains(self, key: str) -> bool:
        return key in self._owner

    def _provider(self, key: str) -> ResourceProvider:
        try:
            return self._owner[key]
        except KeyError as exc:
            raise ResourceError(f"unknown resource {key!r}") from exc

    def stat(self, key: str) -> ResourceStat:
        return self._provider(key).stat(key)

    def read(self, key: str, offset: int = 0, length: int | None = None) -> bytes:
        return self._provider(key).read(key, offset, length)

    def open(self, key: str) -> BinaryIO:
        return self._provider(key).open(key)
