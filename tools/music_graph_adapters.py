"""Engine-neutral registry for profile-selected music graph adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from same.music import MusicBuildAdapter, MusicBuildGraph


AdapterFactory = Callable[[Path | None, MusicBuildGraph], MusicBuildAdapter]


@dataclass(frozen=True, slots=True)
class MusicGraphAdapterRegistration:
    engine_id: str
    source_family: str
    requires_source_archive: bool
    factory: AdapterFactory


class MusicGraphAdapterRegistry:
    def __init__(self) -> None:
        self._registrations: dict[tuple[str, str], MusicGraphAdapterRegistration] = {}

    def register(self, registration: MusicGraphAdapterRegistration) -> None:
        key = (registration.engine_id, registration.source_family)
        if key in self._registrations:
            raise ValueError(f"music graph adapter {key!r} is already registered")
        self._registrations[key] = registration

    def resolve(self, engine_id: str, source_family: str) -> MusicGraphAdapterRegistration:
        try:
            return self._registrations[(engine_id, source_family)]
        except KeyError as exc:
            raise ValueError(
                f"no music graph adapter is registered for engine {engine_id!r} "
                f"and source family {source_family!r}"
            ) from exc


def default_music_graph_adapters() -> MusicGraphAdapterRegistry:
    # Concrete adapter imports remain here, outside the profile orchestrator.
    from build_qtma_music_graph import (
        QtmaFixtureMusicGraphAdapter, QtmaMovieMusicGraphAdapter,
    )
    from build_scumm_v5_music_graph import ScummV5MusicGraphAdapter

    registry = MusicGraphAdapterRegistry()
    registry.register(MusicGraphAdapterRegistration(
        "scumm_v5", "scumm_v5_archive_v1", True,
        lambda source, graph: ScummV5MusicGraphAdapter(_required(source), graph),
    ))
    registry.register(MusicGraphAdapterRegistration(
        "demo", "qtma_fixture_v1", False,
        lambda source, graph: QtmaFixtureMusicGraphAdapter(graph),
    ))
    registry.register(MusicGraphAdapterRegistration(
        "demo", "qtma_mov_musi_v1", False,
        lambda source, graph: QtmaMovieMusicGraphAdapter(graph),
    ))
    return registry


def _required(source: Path | None) -> Path:
    if source is None:
        raise ValueError("this music graph adapter requires a source archive")
    return source
