"""Engine-neutral compiled-music lifecycle policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ..abi import AudioOpcode, EngineOpcode
from ..errors import ResourceError
from .catalog import CompiledMusicCatalog


class MusicLifecycleStatus(IntEnum):
    IDLE = 0
    PENDING = 1
    PLAYING = 2
    COMPLETED = 3
    STOPPED = 4
    FAILED = 255


@dataclass(frozen=True, slots=True)
class MusicLifecycleAction:
    audio: AudioOpcode | None = None
    response: EngineOpcode | None = None
    logical_id: int = 0


class CompiledMusicLifecycle:
    """Reference policy mirrored by the opt-in SNES lifecycle coordinator."""

    def __init__(
        self, catalog: CompiledMusicCatalog, *, tick_hz: int = 60,
        start_frames: int = 15,
    ) -> None:
        if tick_hz < 1 or start_frames < 0:
            raise ValueError("music lifecycle timing must be nonnegative")
        self.catalog = catalog
        self.tick_hz = tick_hz
        self.start_frames = start_frames
        self.status = MusicLifecycleStatus.IDLE
        self.logical_id = 0
        self.duration_frames = 0
        self.deadline = 0

    def play(self, logical_id: int, frame: int) -> tuple[MusicLifecycleAction, ...]:
        self.logical_id = int(logical_id)
        try:
            entry = self.catalog.resolve(self.logical_id)
        except ResourceError:
            self.status = MusicLifecycleStatus.FAILED
            return (MusicLifecycleAction(
                response=EngineOpcode.FAILED, logical_id=self.logical_id,
            ),)
        self.logical_id = entry.logical_id
        self.duration_frames = (
            0 if entry.loop_start is not None
            else entry.duration_frames(self.tick_hz, self.catalog.time_scale)
        )
        self.deadline = int(frame) + self.start_frames
        self.status = MusicLifecycleStatus.PENDING
        return (MusicLifecycleAction(AudioOpcode.MUSIC_PLAY, None, entry.logical_id),)

    def stop(self) -> tuple[MusicLifecycleAction, ...]:
        self.status = MusicLifecycleStatus.STOPPED
        return (
            MusicLifecycleAction(AudioOpcode.MUSIC_STOP, None, self.logical_id),
            MusicLifecycleAction(None, EngineOpcode.STOPPED, self.logical_id),
        )

    def tick(self, frame: int) -> tuple[MusicLifecycleAction, ...]:
        frame = int(frame)
        if self.status is MusicLifecycleStatus.PENDING and frame >= self.deadline:
            self.status = MusicLifecycleStatus.PLAYING
            if self.duration_frames:
                self.deadline = frame + self.duration_frames
            return (MusicLifecycleAction(
                None, EngineOpcode.READY, self.logical_id,
            ),)
        if (
            self.status is MusicLifecycleStatus.PLAYING
            and self.duration_frames and frame >= self.deadline
        ):
            self.status = MusicLifecycleStatus.COMPLETED
            return (
                MusicLifecycleAction(AudioOpcode.MUSIC_STOP, None, self.logical_id),
                MusicLifecycleAction(None, EngineOpcode.STOPPED, self.logical_id),
            )
        return ()
