"""Profile-to-compiled-music bundle ownership and verification."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, Mapping

from ..errors import ProfileValidationError, ResourceError
from ..profile import EngineProfile
from .build_graph import MusicBuildGraph, verify_music_build
from .catalog import CompiledMusicCatalog


_SONG_ENUM = re.compile(r"^\s*!Song_([A-Za-z0-9_]+)\s*=\s*(\d+)\s*$", re.MULTILINE)


def profile_music_owner(profile: EngineProfile) -> dict[str, object]:
    """Stable profile identity recorded into a compiled music transaction."""
    return {
        "engine_id": profile.engine_id,
        "game_id": profile.game_id,
        "variant": profile.variant,
        "profile_sha256": hashlib.sha256(profile.path.read_bytes()).hexdigest(),
    }


def load_profile_music_graph(
    profile: EngineProfile,
    *,
    dependency_reader: Callable[[str], bytes],
) -> MusicBuildGraph:
    key = profile.options.get("music_build_graph")
    if not isinstance(key, str) or not key:
        raise ProfileValidationError(
            f"profile {profile.game_id!r} has no music_build_graph option"
        )
    try:
        binding = profile.binding(key)
    except KeyError as exc:
        raise ProfileValidationError(
            f"profile {profile.game_id!r} music build graph {key!r} is unbound"
        ) from exc
    if binding.kind != "MBGR":
        raise ProfileValidationError(
            f"profile {profile.game_id!r} music build graph must have MBGR kind"
        )
    graph = MusicBuildGraph.decode(
        binding.path.read_bytes(), key, dependency_reader=dependency_reader,
    )
    if graph.profile != profile.game_id:
        raise ProfileValidationError(
            f"music graph profile {graph.profile!r} does not match {profile.game_id!r}"
        )
    return graph


@dataclass(frozen=True, slots=True)
class ProfileMusicBundle:
    directory: Path
    graph_sha256: str
    profile_sha256: str
    compiler_sha256: str
    catalog_sha256: str
    tad_binary_sha256: str
    song_count: int


def _compiled_songs(raw: str) -> Mapping[str, int]:
    songs: dict[str, int] = {}
    for name, value in _SONG_ENUM.findall(raw):
        song_id = int(value)
        if name in songs:
            raise ResourceError(f"TAD enums repeat song {name!r}")
        songs[name] = song_id
    if not songs:
        raise ResourceError("TAD enums contain no compiled songs")
    return songs


def verify_profile_music_bundle(
    profile: EngineProfile,
    graph: MusicBuildGraph,
    directory: Path,
    compiler: Path,
) -> ProfileMusicBundle:
    """Verify one inseparable profile/graph/catalog/TAD compilation bundle."""
    owner = profile_music_owner(profile)
    verify_music_build(graph, directory, compiler, owner=owner)
    catalog_raw = (directory / "catalog.json").read_bytes()
    enums_raw = (directory / "tad.inc").read_text(encoding="utf-8")
    catalog = CompiledMusicCatalog.decode(
        catalog_raw, "music.catalog", compiled_songs=_compiled_songs(enums_raw),
    )
    tad_raw = (directory / "tad.bin").read_bytes()
    compiler_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
    return ProfileMusicBundle(
        directory.resolve(), graph.sha256, str(owner["profile_sha256"]),
        compiler_hash, hashlib.sha256(catalog_raw).hexdigest(),
        hashlib.sha256(tad_raw).hexdigest(), len(catalog.entries),
    )
