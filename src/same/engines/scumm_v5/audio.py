"""Backend-neutral SCUMM v5 audio intent and deterministic playheads."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from ...capabilities import EngineCapability
from ...engine import EngineContext
from ...errors import ResourceError, SaveFormatError

_MANIFEST_SCHEMA = "same_scumm_audio_v1"
_SCORE_SCHEMA = "same_score_v1"
_EVENT_KINDS = {"note_on", "note_off", "program", "control", "marker"}


def _object(raw: bytes, key: str) -> Mapping[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResourceError(f"SCUMM audio resource {key!r} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ResourceError(f"SCUMM audio resource {key!r} must contain an object")
    return value


def _integer(value: object, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ResourceError(f"SCUMM audio {name} must be in {low}..{high}")
    return value


@dataclass(frozen=True, slots=True)
class ScoreEvent:
    tick: int
    kind: str
    voice: int
    a: int
    b: int


@dataclass(frozen=True, slots=True)
class SameScore:
    key: str
    ticks_per_second: int
    length: int
    loop_start: int
    loop_end: int
    events: tuple[ScoreEvent, ...]
    sha256: str

    @classmethod
    def decode(cls, raw: bytes, key: str) -> "SameScore":
        data = _object(raw, key)
        if data.get("schema") != _SCORE_SCHEMA:
            raise ResourceError(f"SCUMM score {key!r} has an unsupported schema")
        rate = _integer(data.get("ticks_per_second"), "score rate", 1, 1000)
        length = _integer(data.get("length"), "score length", 1, 0x7FFFFFFF)
        loop = data.get("loop")
        if not isinstance(loop, list) or len(loop) != 2:
            raise ResourceError(f"SCUMM score {key!r} loop must contain two ticks")
        loop_start = _integer(loop[0], "loop start", 0, length - 1)
        loop_end = _integer(loop[1], "loop end", loop_start + 1, length)
        raw_events = data.get("events")
        if not isinstance(raw_events, list):
            raise ResourceError(f"SCUMM score {key!r} events must be an array")
        events: list[ScoreEvent] = []
        previous = -1
        for index, item in enumerate(raw_events):
            if not isinstance(item, dict):
                raise ResourceError(f"SCUMM score {key!r} event {index} is not an object")
            tick = _integer(item.get("tick"), f"event {index} tick", 0, length - 1)
            if tick < previous:
                raise ResourceError(f"SCUMM score {key!r} events are not time ordered")
            previous = tick
            kind = str(item.get("kind", ""))
            if kind not in _EVENT_KINDS:
                raise ResourceError(f"SCUMM score {key!r} event {index} has bad kind {kind!r}")
            events.append(
                ScoreEvent(
                    tick,
                    kind,
                    _integer(item.get("voice", 0), f"event {index} voice", 0, 255),
                    _integer(item.get("a", 0), f"event {index} a", 0, 65535),
                    _integer(item.get("b", 0), f"event {index} b", 0, 65535),
                )
            )
        return cls(
            key, rate, length, loop_start, loop_end, tuple(events),
            hashlib.sha256(raw).hexdigest(),
        )


@dataclass(frozen=True, slots=True)
class AudioAsset:
    logical_id: int
    resource: str
    duration: int
    loop: bool = False
    pan: int = 128
    priority: int = 0
    tad_song: int | None = None
    msu_track: int | None = None


class ScummV5AudioAdapter:
    """Keeps SCUMM audio state independent of SPC/TAD/MSU realization."""

    def __init__(self, context: EngineContext, manifest_key: str) -> None:
        self.context = context
        self.manifest_key = manifest_key
        manifest = _object(context.services.resource_read(manifest_key), manifest_key)
        if manifest.get("schema") != _MANIFEST_SCHEMA:
            raise ResourceError(f"SCUMM audio manifest {manifest_key!r} has unsupported schema")
        self.music = self._assets(manifest.get("music"), "music")
        self.sfx = self._assets(manifest.get("sfx"), "sfx")
        self.speech = self._assets(manifest.get("speech"), "speech")
        self.scores: dict[int, SameScore] = {}
        for logical_id, asset in self.music.items():
            self.scores[logical_id] = SameScore.decode(
                context.services.resource_read(asset.resource), asset.resource
            )
            score = self.scores[logical_id]
            if score.ticks_per_second != context.profile.tick_hz:
                raise ResourceError(
                    f"SCUMM score {asset.resource!r} rate {score.ticks_per_second} "
                    f"does not match profile rate {context.profile.tick_hz}"
                )
            if asset.duration != score.length:
                raise ResourceError(
                    f"SCUMM music {logical_id} duration does not match its score"
                )
        self.music_id: int | None = None
        self.music_position = 0
        self.active_sfx: dict[int, int] = {}
        self.speech_id: int | None = None
        self.speech_position = 0
        self.backend = self._choose_backend()

    def _assets(self, value: object, family: str) -> dict[int, AudioAsset]:
        if not isinstance(value, dict):
            raise ResourceError(f"SCUMM audio manifest {family} must be an object")
        result: dict[int, AudioAsset] = {}
        for raw_id, raw_asset in value.items():
            try:
                logical_id = int(raw_id)
            except ValueError as exc:
                raise ResourceError(f"SCUMM audio {family} id {raw_id!r} is invalid") from exc
            _integer(logical_id, f"{family} id", 0, 65535)
            if not isinstance(raw_asset, dict):
                raise ResourceError(f"SCUMM audio {family}.{logical_id} must be an object")
            resource = raw_asset.get("resource")
            if not isinstance(resource, str) or not resource:
                raise ResourceError(f"SCUMM audio {family}.{logical_id} has no resource")
            if not self.context.services.resources.contains(resource):
                raise ResourceError(f"SCUMM audio {family}.{logical_id} resource {resource!r} is absent")
            result[logical_id] = AudioAsset(
                logical_id=logical_id,
                resource=resource,
                duration=_integer(raw_asset.get("duration"), f"{family} duration", 1, 0x7FFFFFFF),
                loop=bool(raw_asset.get("loop", False)),
                pan=_integer(raw_asset.get("pan", 128), f"{family} pan", 0, 255),
                priority=_integer(raw_asset.get("priority", 0), f"{family} priority", 0, 255),
                tad_song=(None if raw_asset.get("tad_song") is None else _integer(raw_asset["tad_song"], "TAD song", 0, 65535)),
                msu_track=(None if raw_asset.get("msu_track") is None else _integer(raw_asset["msu_track"], "MSU track", 0, 65535)),
            )
        return result

    def _choose_backend(self) -> str:
        available = self.context.negotiated_capabilities
        order = self.context.profile.options.get(
            "audio_backend_order", ["chip_audio", "msu1_stream", "score_interpreter"]
        )
        if not isinstance(order, list):
            raise ResourceError("SCUMM audio_backend_order must be an array")
        for backend in map(str, order):
            if backend == "chip_audio" and available & EngineCapability.CHIP_AUDIO:
                return "curated_tad"
            if backend == "msu1_stream" and available & EngineCapability.MSU1_STREAM:
                return "msu1_stream"
            if backend == "score_interpreter":
                return backend
        raise ResourceError("SCUMM audio profile has no usable backend")

    def play_music(self, logical_id: int) -> None:
        try:
            asset = self.music[int(logical_id)]
        except KeyError as exc:
            raise ResourceError(f"SCUMM music {logical_id} has no manifest entry") from exc
        self.music_id = asset.logical_id
        self.music_position = 0
        self.context.services.audio.play_music(
            asset.logical_id, loop=asset.loop, resource=asset.resource, backend=self.backend
        )

    def stop_music(self) -> None:
        self.music_id = None
        self.music_position = 0
        self.context.services.audio.stop_music()

    def play_sfx(self, logical_id: int) -> None:
        try:
            asset = self.sfx[int(logical_id)]
        except KeyError as exc:
            raise ResourceError(f"SCUMM SFX {logical_id} has no manifest entry") from exc
        self.active_sfx[asset.logical_id] = 0
        self.context.services.audio.play_sfx(
            asset.logical_id, pan=asset.pan, priority=asset.priority,
            resource=asset.resource, backend=self.backend,
        )

    def stop_sfx(self, logical_id: int) -> None:
        self.active_sfx.pop(int(logical_id), None)
        self.context.services.audio.stop_sfx(logical_id)

    def play_speech(self, logical_id: int) -> None:
        try:
            asset = self.speech[int(logical_id)]
        except KeyError as exc:
            raise ResourceError(f"SCUMM speech {logical_id} has no manifest entry") from exc
        self.speech_id = asset.logical_id
        self.speech_position = 0
        self.context.services.audio.play_speech(
            asset.logical_id, resource=asset.resource,
            backend="msu1_stream" if self.context.negotiated_capabilities & EngineCapability.MSU1_STREAM else "pcm_stream",
        )

    def tick(self) -> None:
        if self.music_id is not None:
            asset = self.music[self.music_id]
            score = self.scores[self.music_id]
            self.music_position += 1
            if self.music_position >= score.loop_end:
                self.music_position = score.loop_start if asset.loop else score.length
                if not asset.loop:
                    self.stop_music()
        for logical_id, position in tuple(self.active_sfx.items()):
            position += 1
            if position >= self.sfx[logical_id].duration:
                self.stop_sfx(logical_id)
            else:
                self.active_sfx[logical_id] = position
        if self.speech_id is not None:
            self.speech_position += 1
            if self.speech_position >= self.speech[self.speech_id].duration:
                self.speech_id = None
                self.speech_position = 0
                self.context.services.audio.stop_speech()

    def save_state(self) -> dict[str, object]:
        return {
            "music": None if self.music_id is None else [self.music_id, self.music_position],
            "sfx": [[logical_id, position] for logical_id, position in sorted(self.active_sfx.items())],
            "speech": None if self.speech_id is None else [self.speech_id, self.speech_position],
        }

    def load_state(self, data: object) -> None:
        if not isinstance(data, dict):
            raise SaveFormatError("SCUMM save audio state must be an object")
        music = self._saved_pair(data.get("music"), self.music, "music", nullable=True)
        sfx_raw = data.get("sfx")
        if not isinstance(sfx_raw, list):
            raise SaveFormatError("SCUMM save SFX state must be an array")
        sfx = [self._saved_pair(item, self.sfx, "SFX", nullable=False) for item in sfx_raw]
        speech = self._saved_pair(data.get("speech"), self.speech, "speech", nullable=True)
        if len({item[0] for item in sfx if item is not None}) != len(sfx):
            raise SaveFormatError("SCUMM save contains duplicate SFX playheads")
        if music is not None and music[1] >= self.scores[music[0]].length:
            raise SaveFormatError("SCUMM save music playhead lies outside its score")
        if any(item is not None and item[1] >= self.sfx[item[0]].duration for item in sfx):
            raise SaveFormatError("SCUMM save SFX playhead lies outside its resource")
        if speech is not None and speech[1] >= self.speech[speech[0]].duration:
            raise SaveFormatError("SCUMM save speech playhead lies outside its resource")
        self.context.services.audio.stop_music()
        self.context.services.audio.stop_sfx()
        self.context.services.audio.stop_speech()
        self.music_id = None
        self.active_sfx.clear()
        self.speech_id = None
        if music is not None:
            logical_id, position = music
            asset = self.music[logical_id]
            self.music_id, self.music_position = logical_id, position
            self.context.services.audio.play_music(
                logical_id, loop=asset.loop, resource=asset.resource,
                backend=self.backend, position=position,
            )
        for item in sfx:
            assert item is not None
            logical_id, position = item
            asset = self.sfx[logical_id]
            self.active_sfx[logical_id] = position
            self.context.services.audio.play_sfx(
                logical_id, pan=asset.pan, priority=asset.priority,
                resource=asset.resource, backend=self.backend, position=position,
            )
        if speech is not None:
            logical_id, position = speech
            asset = self.speech[logical_id]
            self.speech_id, self.speech_position = logical_id, position
            self.context.services.audio.play_speech(
                logical_id, resource=asset.resource,
                backend="msu1_stream" if self.context.negotiated_capabilities & EngineCapability.MSU1_STREAM else "pcm_stream",
                position=position,
            )

    @staticmethod
    def _saved_pair(value: object, assets: Mapping[int, AudioAsset], family: str, *, nullable: bool) -> tuple[int, int] | None:
        if value is None and nullable:
            return None
        if not isinstance(value, list) or len(value) != 2:
            raise SaveFormatError(f"SCUMM save {family} playhead must contain id and position")
        logical_id, position = int(value[0]), int(value[1])
        if logical_id not in assets or position < 0:
            raise SaveFormatError(f"SCUMM save {family} playhead is invalid")
        return logical_id, position

    def inspect(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "music": self.music_id,
            "music_position": self.music_position,
            "sfx": dict(sorted(self.active_sfx.items())),
            "speech": self.speech_id,
            "speech_position": self.speech_position,
            "scores": {
                str(logical_id): {
                    "resource": score.key,
                    "sha256": score.sha256,
                    "events": len(score.events),
                    "loop": [score.loop_start, score.loop_end],
                }
                for logical_id, score in sorted(self.scores.items())
            },
            "renditions": {
                str(logical_id): {
                    "score_interpreter": asset.resource,
                    "curated_tad": asset.tad_song,
                    "msu1_stream": asset.msu_track,
                }
                for logical_id, asset in sorted(self.music.items())
            },
        }
