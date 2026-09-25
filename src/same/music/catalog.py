"""Profile-owned identities for precompiled symbolic-music renditions."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Callable, Mapping

from ..errors import ResourceError


_SCHEMA = "same_compiled_music_catalog_v1"
_HASH = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[A-Za-z0-9_]{1,64}")


def _integer(value: object, owner: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ResourceError(f"{owner} must be in {low}..{high}")
    return value


@dataclass(frozen=True, slots=True)
class CompiledMusicEntry:
    logical_id: int
    source_resource: str
    source_sha256: str
    compiled_song: str
    compiled_song_id: int
    duration: int
    loop_start: int | None = None
    loop_end: int | None = None
    route_kind: str = "default"
    route_value: int = 0
    route_identity: str | None = None
    instrument_bank_sha256: str | None = None
    branch: tuple[int, int, int, int] | None = None

    @property
    def identity(self) -> str:
        return self.route_identity or f"{self.source_resource}@{self.source_sha256}"

    @property
    def source_identity(self) -> str:
        return f"{self.source_resource}@{self.source_sha256}"

    def duration_frames(self, tick_hz: int, time_scale: int) -> int:
        return max(1, (self.duration * tick_hz + time_scale - 1) // time_scale)

    def loop_frames(self, tick_hz: int, time_scale: int) -> tuple[int, int] | None:
        if self.loop_start is None or self.loop_end is None:
            return None
        start = self.loop_start * tick_hz // time_scale
        end = (self.loop_end * tick_hz + time_scale - 1) // time_scale
        return start, max(start + 1, end)


@dataclass(frozen=True, slots=True)
class CompiledSectionPlan:
    logical_id: int
    route_kind: str
    route_value: int
    hook_value: int
    boundary: int
    boundary_token: int
    current_section: int
    default_section: int
    hook_section: int
    selector: int
    source_branch: tuple[int, int, int, int]
    identity: str
    instrument_bank_sha256: str


@dataclass(frozen=True, slots=True)
class CompiledMusicCatalog:
    key: str
    name: str
    time_scale: int
    entries: tuple[CompiledMusicEntry, ...]
    sections: tuple[CompiledSectionPlan, ...]
    sha256: str

    @classmethod
    def decode(
        cls,
        raw: bytes,
        key: str,
        *,
        source_reader: Callable[[str], bytes] | None = None,
        compiled_songs: Mapping[str, int] | None = None,
    ) -> "CompiledMusicCatalog":
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResourceError(f"compiled music catalog {key!r} is invalid JSON: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema") != _SCHEMA:
            raise ResourceError(f"compiled music catalog {key!r} has an unsupported schema")
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ResourceError(f"compiled music catalog {key!r} has no name")
        time_scale = _integer(data.get("time_scale"), f"catalog {key!r} time scale", 1, 1_000_000_000)
        raw_entries = data.get("entries")
        if not isinstance(raw_entries, list) or not raw_entries:
            raise ResourceError(f"compiled music catalog {key!r} entries must be a non-empty array")
        entries: list[CompiledMusicEntry] = []
        route_keys: set[tuple[int, str, int]] = set()
        identities: set[str] = set()
        compiled_ids: set[int] = set()
        allow_shared = data.get("allow_shared_compiled_song", False)
        if not isinstance(allow_shared, bool):
            raise ResourceError(f"compiled music catalog {key!r} shared-song flag is invalid")
        compiled_bindings: dict[int, str] = {}
        for index, item in enumerate(raw_entries):
            owner = f"catalog {key!r} entry {index}"
            if not isinstance(item, dict):
                raise ResourceError(f"{owner} must be an object")
            logical_id = _integer(item.get("logical_id"), f"{owner} logical id", 0, 0xFFFFFFFF)
            resource = item.get("source_resource")
            source_hash = item.get("source_sha256")
            song = item.get("compiled_song")
            if not isinstance(resource, str) or not resource:
                raise ResourceError(f"{owner} has no source resource")
            if not isinstance(source_hash, str) or not _HASH.fullmatch(source_hash):
                raise ResourceError(f"{owner} has an invalid source SHA-256")
            if not isinstance(song, str) or not _NAME.fullmatch(song):
                raise ResourceError(f"{owner} has an invalid compiled song name")
            song_id = _integer(item.get("compiled_song_id"), f"{owner} compiled song id", 1, 255)
            duration = _integer(item.get("duration"), f"{owner} duration", 1, 0x7FFFFFFF)
            loop = item.get("loop")
            loop_start = loop_end = None
            if loop is not None:
                if not isinstance(loop, list) or len(loop) != 2:
                    raise ResourceError(f"{owner} loop must contain two positions")
                loop_start = _integer(loop[0], f"{owner} loop start", 0, duration - 1)
                loop_end = _integer(loop[1], f"{owner} loop end", loop_start + 1, duration)
            route = item.get("route")
            route_kind, route_value = "default", 0
            route_identity = bank_hash = None
            branch = None
            if route is not None:
                if not isinstance(route, dict):
                    raise ResourceError(f"{owner} route must be an object")
                route_kind = route.get("kind")
                if not isinstance(route_kind, str) or not _NAME.fullmatch(route_kind):
                    raise ResourceError(f"{owner} has an invalid route kind")
                route_value = _integer(route.get("value"), f"{owner} route value", 0, 0xFFFF)
                route_identity = route.get("identity")
                bank_hash = route.get("instrument_bank_sha256")
                if not isinstance(route_identity, str) or not _HASH.fullmatch(route_identity):
                    raise ResourceError(f"{owner} has an invalid route identity")
                if not isinstance(bank_hash, str) or not _HASH.fullmatch(bank_hash):
                    raise ResourceError(f"{owner} has an invalid instrument-bank SHA-256")
                raw_branch = route.get("branch")
                if (not isinstance(raw_branch, list) or len(raw_branch) != 4
                        or any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                               for v in raw_branch)):
                    raise ResourceError(f"{owner} has invalid branch provenance")
                branch = tuple(raw_branch)
            route_key = (logical_id, route_kind, route_value)
            identity = route_identity or f"{resource}@{source_hash}"
            if route_key in route_keys:
                if route is None:
                    raise ResourceError(
                        f"compiled music catalog {key!r} repeats logical id {logical_id}"
                    )
                raise ResourceError(f"compiled music catalog {key!r} repeats route {route_key}")
            if identity in identities:
                raise ResourceError(f"compiled music catalog {key!r} repeats source identity {identity}")
            if song_id in compiled_ids and (not allow_shared or compiled_bindings[song_id] != song):
                raise ResourceError(f"compiled music catalog {key!r} repeats compiled song id {song_id}")
            if source_reader is not None:
                observed = hashlib.sha256(source_reader(resource)).hexdigest()
                if observed != source_hash:
                    raise ResourceError(
                        f"compiled music catalog {key!r} source {resource!r} is stale: "
                        f"expected {source_hash}, observed {observed}"
                    )
            if compiled_songs is not None:
                observed_id = compiled_songs.get(song)
                if observed_id is None:
                    raise ResourceError(f"{owner} compiled song {song!r} is missing")
                if observed_id != song_id:
                    raise ResourceError(
                        f"{owner} compiled song {song!r} is id {observed_id}, not {song_id}"
                    )
            route_keys.add(route_key)
            identities.add(identity)
            compiled_ids.add(song_id)
            compiled_bindings[song_id] = song
            entries.append(CompiledMusicEntry(
                logical_id, resource, source_hash, song, song_id, duration,
                loop_start, loop_end, route_kind, route_value, route_identity,
                bank_hash, branch,
            ))
        sections = []
        section_keys = set()
        raw_sections = data.get("sections", [])
        if not isinstance(raw_sections, list):
            raise ResourceError(f"compiled music catalog {key!r} sections must be an array")
        for index, item in enumerate(raw_sections):
            owner = f"catalog {key!r} section {index}"
            if not isinstance(item, dict):
                raise ResourceError(f"{owner} must be an object")
            logical = _integer(item.get("logical_id"), f"{owner} logical id", 0, 0xffffffff)
            kind = item.get("route_kind")
            if not isinstance(kind, str) or not _NAME.fullmatch(kind):
                raise ResourceError(f"{owner} route kind is invalid")
            values = tuple(_integer(item.get(field), f"{owner} {field}", 0, high) for field, high in (
                ("route_value", 0xffff), ("hook_value", 0xff), ("boundary", 0x7fffffff),
                ("boundary_token", 0x7f), ("current_section", 0xff),
                ("default_section", 0xff), ("hook_section", 0xff), ("selector", 0xff),
            ))
            branch = item.get("source_branch")
            identity, bank = item.get("identity"), item.get("instrument_bank_sha256")
            if (not isinstance(branch, list) or len(branch) != 4
                    or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in branch)
                    or not isinstance(identity, str) or not _HASH.fullmatch(identity)
                    or not isinstance(bank, str) or not _HASH.fullmatch(bank)):
                raise ResourceError(f"{owner} provenance or identity is invalid")
            section_key = (logical, kind, values[0], values[1])
            if section_key in section_keys or (logical, kind, values[0]) not in route_keys:
                raise ResourceError(f"{owner} is duplicated or names an absent route")
            section_keys.add(section_key)
            sections.append(CompiledSectionPlan(
                logical, kind, *values, tuple(branch), identity, bank,
            ))
        entries.sort(key=lambda entry: (entry.logical_id, entry.route_kind, entry.route_value))
        sections.sort(key=lambda item: (item.logical_id, item.route_kind,
                                        item.route_value, item.hook_value))
        return cls(key, name, time_scale, tuple(entries), tuple(sections),
                   hashlib.sha256(raw).hexdigest())

    def resolve(
        self, logical_id: int, route_kind: str = "default", route_value: int = 0,
    ) -> CompiledMusicEntry:
        logical_id = int(logical_id)
        for entry in self.entries:
            if (entry.logical_id == logical_id and entry.route_kind == route_kind
                    and entry.route_value == int(route_value)):
                return entry
        raise ResourceError(
            f"compiled music catalog {self.key!r} has no route "
            f"({logical_id}, {route_kind!r}, {route_value})"
        )
