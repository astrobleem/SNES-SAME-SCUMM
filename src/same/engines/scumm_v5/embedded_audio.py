"""Strict SCUMM v5 SOU/ROL MIDI playback and deterministic PCM synthesis."""

from __future__ import annotations

from dataclasses import dataclass
from bisect import bisect_left
import hashlib
import math
import struct
from typing import Callable

from ...capabilities import EngineCapability
from ...engine import EngineContext
from ...errors import ResourceError, SaveFormatError
from ...music import CompiledMusicCatalog

_RENDITIONS = (b"ROL ", b"ADL ", b"SPK ")
_DEFAULT_TEMPO = 500_000
_MAX_TRACKS = 120
_MAX_EVENTS = 1_000_000


@dataclass(slots=True)
class _DeferredImuseCommand:
    owner_sound: int
    owner_generation: int
    marker: int
    payload: tuple[int, ...]
    installation_order: int
    consumed: bool = False


@dataclass(slots=True)
class _LogicalCompiledOwner:
    state: str
    generation: int
    priority: int = 128
    speed: int = 128
    volume: int = 127
    fade_target: int | None = None
    fade_remaining: int = 0


def _vlq(data: bytes, offset: int, end: int, owner: str) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        if offset >= end:
            raise ResourceError(f"{owner} variable-length value is truncated")
        item = data[offset]
        offset += 1
        value = (value << 7) | (item & 0x7F)
        if not item & 0x80:
            return value, offset
    raise ResourceError(f"{owner} variable-length value exceeds four bytes")


@dataclass(frozen=True, slots=True)
class EmbeddedMidiEvent:
    tick: int
    time_us: int
    status: int
    data: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class EmbeddedMidiTrack:
    duration_us: int
    duration_ticks: int
    events: tuple[EmbeddedMidiEvent, ...]
    tempo_map: tuple[tuple[int, int, int], ...]

    def time_at_tick(self, tick: int, division: int) -> int:
        """Map an iMUSE fixed-tick jump target onto this track's tempo map."""
        if tick < 0:
            raise ValueError("negative MIDI tick")
        point_tick, point_us, tempo = self.tempo_map[0]
        for candidate in self.tempo_map[1:]:
            if candidate[0] > tick:
                break
            point_tick, point_us, tempo = candidate
        return point_us + (tick - point_tick) * tempo // division


@dataclass(frozen=True, slots=True)
class ScummImuseEvent:
    tick: int
    time_us: int
    command: int
    values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ScummV5EmbeddedSound:
    key: str
    rendition: str
    priority: int
    midi_format: int
    track_count: int
    division: int
    duration_us: int
    events: tuple[EmbeddedMidiEvent, ...]
    tracks: tuple[EmbeddedMidiTrack, ...]
    imuse_events: tuple[tuple[ScummImuseEvent, ...], ...]
    sha256: str

    @classmethod
    def decode(
        cls, raw: bytes, key: str, *, rendition_order: tuple[bytes, ...] = _RENDITIONS
    ) -> "ScummV5EmbeddedSound":
        if len(raw) < 16 or raw[:4] != b"SOU ":
            raise ResourceError(f"SCUMM sound {key!r} is not a SOU container")
        if int.from_bytes(raw[4:8], "big") != len(raw) - 8:
            raise ResourceError(f"SCUMM sound {key!r} SOU size differs from its resource")
        children: list[tuple[bytes, bytes]] = []
        offset = 8
        while offset < len(raw):
            if offset + 8 > len(raw):
                raise ResourceError(f"SCUMM sound {key!r} child header is truncated")
            tag = raw[offset : offset + 4]
            size = int.from_bytes(raw[offset + 4 : offset + 8], "big")
            end = offset + 8 + size
            if end > len(raw):
                raise ResourceError(f"SCUMM sound {key!r} {tag!r} child is truncated")
            children.append((tag, raw[offset + 8 : end]))
            offset = end
        selected = next(
            (tag for tag in rendition_order if any(child == tag for child, _ in children)),
            None,
        )
        if selected is None:
            raise ResourceError(f"SCUMM sound {key!r} has no supported rendition")
        payloads = [payload for tag, payload in children if tag == selected]
        if len(payloads) != 1:
            raise ResourceError(f"SCUMM sound {key!r} repeats rendition {selected!r}")
        payload = payloads[0]
        midi_offset = payload.find(b"MThd", 0, min(len(payload), 48))
        if midi_offset < 0:
            raise ResourceError(f"SCUMM sound {key!r} {selected!r} has no MIDI header")
        priority = 128
        mdhd = payload.find(b"MDhd", 0, midi_offset)
        if mdhd >= 0:
            if mdhd + 8 > len(payload):
                raise ResourceError(f"SCUMM sound {key!r} MDhd header is truncated")
            mdhd_size = int.from_bytes(payload[mdhd + 4 : mdhd + 8], "big")
            if mdhd + 8 + mdhd_size > len(payload):
                raise ResourceError(f"SCUMM sound {key!r} MDhd data is truncated")
            if mdhd_size and mdhd + 10 < len(payload):
                priority = payload[mdhd + 10]
        midi_format, track_count, division, decoded_tracks = _decode_smf(
            payload[midi_offset:], f"SCUMM sound {key!r} {selected.decode('ascii').strip()}"
        )
        events = tuple(event for event in decoded_tracks[0].events if event.status < 0xF0)
        imuse_events = tuple(
            tuple(
                decoded for event in track.events
                if event.status == 0xF0
                for decoded in (_decode_imuse_event(event, key),)
                if decoded is not None
            )
            for track in decoded_tracks
        )
        return cls(
            key=key,
            rendition=selected.decode("ascii").strip(),
            priority=priority,
            midi_format=midi_format,
            track_count=track_count,
            division=division,
            duration_us=decoded_tracks[0].duration_us,
            events=events,
            tracks=decoded_tracks,
            imuse_events=imuse_events,
            sha256=hashlib.sha256(raw).hexdigest(),
        )

    def duration_frames(self, rate: int) -> int:
        return max(1, (self.duration_us * rate + 999_999) // 1_000_000)

    def render_pcm(
        self,
        *,
        sample_rate: int = 22_050,
        start_us: int = 0,
        end_us: int | None = None,
        gain: float = 0.22,
    ) -> bytes:
        if not 8_000 <= sample_rate <= 96_000:
            raise ValueError("embedded MIDI sample rate is outside 8000..96000")
        stop_us = self.duration_us if end_us is None else min(end_us, self.duration_us)
        if not 0 <= start_us <= stop_us:
            raise ValueError("embedded MIDI render interval is reversed")
        first_sample = (start_us * sample_rate + 999_999) // 1_000_000
        last_sample = (stop_us * sample_rate + 999_999) // 1_000_000
        active: dict[tuple[int, int], tuple[int, int]] = {}
        event_index = 0
        while event_index < len(self.events) and self.events[event_index].time_us < start_us:
            _apply_midi_event(active, self.events[event_index], sample_rate)
            event_index += 1
        output = bytearray((last_sample - first_sample) * 2)
        for output_index, sample_index in enumerate(range(first_sample, last_sample)):
            now_us = sample_index * 1_000_000 // sample_rate
            while event_index < len(self.events) and self.events[event_index].time_us <= now_us:
                _apply_midi_event(active, self.events[event_index], sample_rate)
                event_index += 1
            mixed = 0.0
            for (channel, note), (velocity, note_start) in active.items():
                if channel == 9:
                    value = 1.0 if ((sample_index * 1103515245 + note * 12345) >> 15) & 1 else -1.0
                else:
                    frequency = 440.0 * 2.0 ** ((note - 69) / 12.0)
                    phase = (sample_index - note_start) * frequency / sample_rate
                    value = math.sin(phase * math.tau)
                mixed += value * velocity / 127.0
            if active:
                mixed /= max(1.0, math.sqrt(len(active)))
            value = max(-32767, min(32767, round(mixed * gain * 32767)))
            struct.pack_into("<h", output, output_index * 2, value)
        return bytes(output)

    def inspect(self) -> dict[str, object]:
        return {
            "resource": self.key,
            "rendition": self.rendition,
            "priority": self.priority,
            "format": self.midi_format,
            "tracks": self.track_count,
            "division": self.division,
            "duration_us": self.duration_us,
            "events": len(self.events),
            "imuse": {
                str(command): sum(
                    event.command == command
                    for track in self.imuse_events for event in track
                )
                for command in sorted({
                    event.command for track in self.imuse_events for event in track
                })
            },
            "sha256": self.sha256,
        }


def _decode_smf(
    midi: bytes, owner: str
) -> tuple[int, int, int, tuple[EmbeddedMidiTrack, ...]]:
    if len(midi) < 14 or midi[:4] != b"MThd":
        raise ResourceError(f"{owner} MIDI header is truncated")
    header_size = int.from_bytes(midi[4:8], "big")
    if header_size != 6 or 8 + header_size > len(midi):
        raise ResourceError(f"{owner} MIDI header size is not canonical")
    midi_format = int.from_bytes(midi[8:10], "big")
    track_count = int.from_bytes(midi[10:12], "big")
    division = int.from_bytes(midi[12:14], "big")
    if midi_format not in (0, 1, 2):
        raise ResourceError(f"{owner} MIDI format {midi_format} is unsupported")
    if not 1 <= track_count <= _MAX_TRACKS or (midi_format == 0 and track_count != 1):
        raise ResourceError(f"{owner} MIDI track count is invalid")
    if not division or division & 0x8000:
        raise ResourceError(f"{owner} MIDI SMPTE division is unsupported")
    offset = 14
    tracks: list[bytes] = []
    for track in range(track_count):
        if offset + 8 > len(midi) or midi[offset : offset + 4] != b"MTrk":
            raise ResourceError(f"{owner} MIDI track {track} header is absent")
        size = int.from_bytes(midi[offset + 4 : offset + 8], "big")
        end = offset + 8 + size
        if end > len(midi):
            raise ResourceError(f"{owner} MIDI track {track} is truncated")
        tracks.append(midi[offset + 8 : end])
        offset = end
    # iMUSE resources use SMF format 2 as alternate sequences. As ScummVM's
    # parser does, initial playback selects track zero instead of mixing them.
    return (
        midi_format, track_count, division,
        tuple(_decode_track(track, division, f"{owner} track {index}")
              for index, track in enumerate(tracks)),
    )


def _decode_track(
    track: bytes, division: int, owner: str
) -> EmbeddedMidiTrack:
    offset = tick = time_us = 0
    tempo = _DEFAULT_TEMPO
    running_status: int | None = None
    events: list[EmbeddedMidiEvent] = []
    tempo_map = [(0, 0, tempo)]
    saw_end = False
    while offset < len(track):
        delta, offset = _vlq(track, offset, len(track), owner)
        tick += delta
        time_us += delta * tempo // division
        if offset >= len(track):
            raise ResourceError(f"{owner} MIDI event is truncated")
        status = track[offset]
        if status & 0x80:
            offset += 1
            if status < 0xF0:
                running_status = status
        elif running_status is not None:
            status = running_status
        else:
            raise ResourceError(f"{owner} MIDI running status has no predecessor")
        if status == 0xFF:
            running_status = None
            if offset >= len(track):
                raise ResourceError(f"{owner} MIDI meta event is truncated")
            kind = track[offset]
            offset += 1
            size, offset = _vlq(track, offset, len(track), owner)
            end = offset + size
            if end > len(track):
                raise ResourceError(f"{owner} MIDI meta payload is truncated")
            payload = track[offset:end]
            offset = end
            if kind == 0x51:
                if size != 3 or int.from_bytes(payload, "big") == 0:
                    raise ResourceError(f"{owner} MIDI tempo event is invalid")
                tempo = int.from_bytes(payload, "big")
                tempo_map.append((tick, time_us, tempo))
            elif kind == 0x2F:
                if size:
                    raise ResourceError(f"{owner} MIDI end event has a payload")
                saw_end = True
                break
            continue
        if status in (0xF0, 0xF7):
            running_status = None
            size, offset = _vlq(track, offset, len(track), owner)
            if offset + size > len(track):
                raise ResourceError(f"{owner} MIDI SysEx payload is truncated")
            payload = tuple(track[offset : offset + size])
            offset += size
            events.append(EmbeddedMidiEvent(tick, time_us, status, payload))
            continue
        command = status & 0xF0
        size = 1 if command in (0xC0, 0xD0) else 2
        if command < 0x80 or command > 0xE0 or offset + size > len(track):
            raise ResourceError(f"{owner} MIDI channel event is invalid")
        data = tuple(track[offset : offset + size])
        if any(item & 0x80 for item in data):
            raise ResourceError(f"{owner} MIDI channel data exceeds seven bits")
        offset += size
        events.append(EmbeddedMidiEvent(tick, time_us, status, data))
        if len(events) > _MAX_EVENTS:
            raise ResourceError(f"{owner} MIDI event count is excessive")
    if not saw_end:
        raise ResourceError(f"{owner} MIDI track has no end event")
    return EmbeddedMidiTrack(
        max(1, time_us), tick, tuple(events), tuple(tempo_map)
    )


def _decode_nibbles(data: tuple[int, ...], owner: str) -> tuple[int, ...]:
    if len(data) % 2:
        raise ResourceError(f"SCUMM sound {owner!r} iMUSE nibble payload is odd")
    if any(item > 0x0F for item in data):
        raise ResourceError(f"SCUMM sound {owner!r} iMUSE nibble payload is invalid")
    return tuple((data[index] << 4) | data[index + 1]
                 for index in range(0, len(data), 2))


def _decode_imuse_event(event: EmbeddedMidiEvent, owner: str) -> ScummImuseEvent | None:
    """Decode the SCUMM manufacturer SysEx vocabulary present in Fate."""
    payload = event.data
    if not payload or payload[-1] != 0xF7:
        raise ResourceError(f"SCUMM sound {owner!r} SysEx lacks F7 termination")
    if payload[0] != 0x7D:
        return None  # Hardware-vendor setup (Roland 0x41 in the Fate demo).
    if len(payload) < 3:
        raise ResourceError(f"SCUMM sound {owner!r} iMUSE SysEx is truncated")
    command = payload[1]
    arguments = payload[2:-1]
    if command in (0, 2):
        return ScummImuseEvent(event.tick, event.time_us, command, arguments)
    if command == 16:
        # LucasArts' AdLib driver sends one instrument directly to a MIDI
        # channel. The 60 nibbles encode the complete 30-byte instrument:
        # eleven base operator fields plus the two optional eight-byte
        # modulation envelopes, their flags, and a duration byte.
        if len(arguments) not in (48, 62) or arguments[0] >= 16:
            raise ResourceError(
                f"SCUMM sound {owner!r} iMUSE AdLib instrument is invalid"
            )
        instrument = _decode_nibbles(arguments[2:], owner)
        if len(instrument) not in (23, 30):
            raise ResourceError(
                f"SCUMM sound {owner!r} iMUSE AdLib instrument size is invalid"
            )
        return ScummImuseEvent(
            event.tick, event.time_us, command, (arguments[0], *instrument)
        )
    if command == 48:
        # Early Monkey v5 resources carry one additional zero after the seven
        # nibble-encoded jump bytes. The original iMUSE decoder ignores that
        # decoded padding; accept only the observed canonical zero extension.
        if len(arguments) not in (15, 16) or (
            len(arguments) == 16 and arguments[-1] != 0
        ):
            raise ResourceError(f"SCUMM sound {owner!r} iMUSE jump size is invalid")
        decoded = _decode_nibbles(arguments[1:15], owner)
        values = (decoded[0], int.from_bytes(bytes(decoded[1:3]), "big"),
                  int.from_bytes(bytes(decoded[3:5]), "big"),
                  int.from_bytes(bytes(decoded[5:7]), "big"))
        return ScummImuseEvent(event.tick, event.time_us, command, values)
    if command == 50:
        if len(arguments) != 5:
            raise ResourceError(f"SCUMM sound {owner!r} iMUSE part-gate size is invalid")
        decoded = _decode_nibbles(arguments[1:], owner)
        return ScummImuseEvent(
            event.tick, event.time_us, command,
            (arguments[0] & 0x0F, decoded[0], decoded[1]),
        )
    if command == 64:
        if len(arguments) < 2:
            raise ResourceError(f"SCUMM sound {owner!r} iMUSE marker is truncated")
        return ScummImuseEvent(event.tick, event.time_us, command, arguments[1:])
    raise ResourceError(
        f"SCUMM sound {owner!r} iMUSE SysEx command {command} is unsupported"
    )


def _apply_midi_event(
    active: dict[tuple[int, int], tuple[int, int]],
    event: EmbeddedMidiEvent,
    sample_rate: int,
) -> None:
    command, channel = event.status & 0xF0, event.status & 0x0F
    if command == 0x90 and event.data[1]:
        active[(channel, event.data[0])] = (
            event.data[1], event.time_us * sample_rate // 1_000_000
        )
    elif command == 0x80 or (command == 0x90 and not event.data[1]):
        active.pop((channel, event.data[0]), None)
    elif command == 0xB0 and event.data[0] in (120, 123):
        for key in tuple(active):
            if key[0] == channel:
                del active[key]


class _ScummMidiPlayer:
    """Stateful Fate-era iMUSE player; all state is JSON-saveable."""

    def __init__(self, sound: ScummV5EmbeddedSound, sample_rate: int) -> None:
        self.sound = sound
        self.sample_rate = sample_rate
        self.track = 0
        self.origin_us = 0
        self.segment_sample = 0
        self.output_sample = 0
        self.event_index = 0
        self.complete = False
        self.jump_hooks = [0, 0]
        self.part_hooks = [0] * 16
        self.part_on = [True] * 16
        self.channel_volume = [127] * 16
        self.channel_expression = [127] * 16
        self.channel_program = [0] * 16
        self.pitch_bend = [8192] * 16
        self.sustain = [False] * 16
        self.sustained: set[tuple[int, int]] = set()
        self.active: dict[tuple[int, int], tuple[int, int]] = {}
        self.markers: list[int] = []
        self.branches: list[tuple[int, int, int, int]] = []

    @property
    def time_us(self) -> int:
        return self.origin_us + self.segment_sample * 1_000_000 // self.sample_rate

    def set_hook(self, cls: int, value: int, channel: int) -> bool:
        if not 0 <= value <= 0xFF:
            return False
        if cls == 0:
            if value != self.jump_hooks[0]:
                self.jump_hooks[1] = self.jump_hooks[0]
                self.jump_hooks[0] = value
            return True
        if cls == 2 and 0 <= channel <= 16:
            if channel == 16:
                self.part_hooks[:] = [value] * 16
            else:
                self.part_hooks[channel] = value
            return True
        return False

    def _jump(self, track: int, beat: int, tick: int) -> None:
        if not 0 <= track < len(self.sound.tracks) or beat < 1:
            raise ResourceError(f"SCUMM sound {self.sound.key!r} iMUSE jump target is invalid")
        target_tick = (beat - 1) * 480 + tick
        target = self.sound.tracks[track]
        if target_tick > target.duration_ticks:
            raise ResourceError(f"SCUMM sound {self.sound.key!r} iMUSE jump exceeds its track")
        self.track = track
        self.origin_us = target.time_at_tick(target_tick, self.sound.division)
        self.segment_sample = 0
        self.event_index = bisect_left(
            tuple(event.tick for event in target.events), target_tick
        )
        for channel in range(16):
            if self.sustain[channel]:
                self.sustain[channel] = False
                self._release_sustained(channel)

    def _release_sustained(self, channel: int) -> None:
        for key in tuple(self.sustained):
            if key[0] == channel:
                self.sustained.remove(key)
                self.active.pop(key, None)

    def _imuse(self, event: EmbeddedMidiEvent) -> bool:
        decoded = _decode_imuse_event(event, self.sound.key)
        if decoded is None or decoded.command == 2:
            return False
        if decoded.command == 0:
            arguments = decoded.values
            if len(arguments) >= 17:
                channel = arguments[0] & 0x0F
                setup = _decode_nibbles(arguments[1:], self.sound.key)
                self.part_on[channel] = bool(setup[0] & 1)
                self.channel_volume[channel] = setup[2]
                self.channel_program[channel] = setup[7]
            return False
        if decoded.command == 48:
            hook, track, beat, tick = decoded.values
            if hook and hook != self.jump_hooks[0]:
                return False
            if hook and hook < 0x80:
                self.jump_hooks[0], self.jump_hooks[1] = self.jump_hooks[1], 0
            old_track = self.track
            self._jump(track, beat, tick)
            self.branches.append((old_track, event.tick, track, (beat - 1) * 480 + tick))
            self.branches[:] = self.branches[-128:]
            return True
        if decoded.command == 50:
            channel, hook, enabled = decoded.values
            if hook and hook != self.part_hooks[channel]:
                return False
            if hook and hook < 0x80:
                self.part_hooks[channel] = 0
            self.part_on[channel] = bool(enabled)
            if not enabled:
                for key in tuple(self.active):
                    if key[0] == channel:
                        self.active.pop(key, None)
                        self.sustained.discard(key)
            return False
        if decoded.command == 64:
            self.markers.extend(decoded.values)
            self.markers[:] = self.markers[-128:]
            return False
        return False

    def _midi(self, event: EmbeddedMidiEvent) -> None:
        command, channel = event.status & 0xF0, event.status & 0x0F
        if command == 0x90 and event.data[1]:
            note_start = self.output_sample + (
                (event.time_us - self.time_us) * self.sample_rate // 1_000_000
            )
            self.active[(channel, event.data[0])] = (event.data[1], note_start)
            self.sustained.discard((channel, event.data[0]))
        elif command == 0x80 or (command == 0x90 and not event.data[1]):
            key = (channel, event.data[0])
            if self.sustain[channel] and key in self.active:
                self.sustained.add(key)
            else:
                self.active.pop(key, None)
        elif command == 0xB0:
            control, value = event.data
            if control == 7:
                self.channel_volume[channel] = value
            elif control == 11:
                self.channel_expression[channel] = value
            elif control == 64:
                was = self.sustain[channel]
                self.sustain[channel] = value >= 64
                if was and not self.sustain[channel]:
                    self._release_sustained(channel)
            elif control in (120, 123):
                for key in tuple(self.active):
                    if key[0] == channel:
                        self.active.pop(key, None)
                        self.sustained.discard(key)
        elif command == 0xC0:
            self.channel_program[channel] = event.data[0]
        elif command == 0xE0:
            self.pitch_bend[channel] = event.data[0] | event.data[1] << 7

    def _process_events(self) -> None:
        jumps = 0
        while not self.complete:
            track = self.sound.tracks[self.track]
            jumped = False
            while (self.event_index < len(track.events)
                   and track.events[self.event_index].time_us <= self.time_us):
                event = track.events[self.event_index]
                self.event_index += 1
                if event.status == 0xF0 and self._imuse(event):
                    jumps += 1
                    if jumps > 64:
                        raise ResourceError(
                            f"SCUMM sound {self.sound.key!r} has a zero-time iMUSE jump cycle"
                        )
                    jumped = True
                    break
                if event.status < 0xF0:
                    self._midi(event)
            if not jumped:
                return

    def render(self, samples: int, gain: float) -> bytes:
        output = bytearray()
        for _ in range(samples):
            track = self.sound.tracks[self.track]
            track_samples = (track.duration_us - self.origin_us) * self.sample_rate
            if self.segment_sample >= (track_samples + 999_999) // 1_000_000:
                self.complete = True
                break
            self._process_events()
            mixed = 0.0
            voices = 0
            for (channel, note), (velocity, note_start) in self.active.items():
                if not self.part_on[channel]:
                    continue
                if channel == 9:
                    value = (1.0 if ((self.output_sample * 1103515245
                                      + note * 12345) >> 15) & 1 else -1.0)
                else:
                    bend = (self.pitch_bend[channel] - 8192) / 8192.0 * 2.0
                    frequency = 440.0 * 2.0 ** ((note + bend - 69) / 12.0)
                    phase = (self.output_sample - note_start) * frequency / self.sample_rate
                    value = math.sin(phase * math.tau)
                level = (velocity / 127.0 * self.channel_volume[channel] / 127.0
                         * self.channel_expression[channel] / 127.0)
                mixed += value * level
                voices += 1
            if voices:
                mixed /= max(1.0, math.sqrt(voices))
            value = max(-32767, min(32767, round(mixed * gain * 32767)))
            output += struct.pack("<h", value)
            self.segment_sample += 1
            self.output_sample += 1
        track = self.sound.tracks[self.track]
        remaining = (track.duration_us - self.origin_us) * self.sample_rate
        if self.segment_sample >= (remaining + 999_999) // 1_000_000:
            self.complete = True
        return bytes(output)

    def save_state(self) -> dict[str, object]:
        return {
            "track": self.track, "origin_us": self.origin_us,
            "segment_sample": self.segment_sample, "output_sample": self.output_sample,
            "event_index": self.event_index, "complete": self.complete,
            "jump_hooks": self.jump_hooks, "part_hooks": self.part_hooks,
            "part_on": self.part_on, "volume": self.channel_volume,
            "expression": self.channel_expression, "program": self.channel_program,
            "pitch_bend": self.pitch_bend, "sustain": self.sustain,
            "sustained": [list(key) for key in sorted(self.sustained)],
            "active": [[channel, note, velocity, started]
                       for (channel, note), (velocity, started) in sorted(self.active.items())],
            "markers": self.markers, "branches": [list(item) for item in self.branches],
        }

    def load_state(self, data: object) -> None:
        if not isinstance(data, dict):
            raise SaveFormatError("SCUMM save iMUSE player state must be an object")
        try:
            track = int(data["track"])
            if not 0 <= track < len(self.sound.tracks):
                raise ValueError
            self.track = track
            self.origin_us = int(data["origin_us"])
            self.segment_sample = int(data["segment_sample"])
            self.output_sample = int(data["output_sample"])
            self.event_index = int(data["event_index"])
            self.complete = bool(data["complete"])
            arrays = {
                "jump_hooks": 2, "part_hooks": 16, "part_on": 16,
                "volume": 16, "expression": 16, "program": 16,
                "pitch_bend": 16, "sustain": 16,
            }
            for name, count in arrays.items():
                value = data[name]
                if not isinstance(value, list) or len(value) != count:
                    raise ValueError
            self.jump_hooks = [int(x) for x in data["jump_hooks"]]
            self.part_hooks = [int(x) for x in data["part_hooks"]]
            self.part_on = [bool(x) for x in data["part_on"]]
            self.channel_volume = [int(x) for x in data["volume"]]
            self.channel_expression = [int(x) for x in data["expression"]]
            self.channel_program = [int(x) for x in data["program"]]
            self.pitch_bend = [int(x) for x in data["pitch_bend"]]
            self.sustain = [bool(x) for x in data["sustain"]]
            self.sustained = {(int(x[0]), int(x[1])) for x in data["sustained"]}
            self.active = {(int(x[0]), int(x[1])): (int(x[2]), int(x[3]))
                           for x in data["active"]}
            self.markers = [int(x) for x in data["markers"]]
            self.branches = [tuple(int(y) for y in x) for x in data["branches"]]
            current = self.sound.tracks[self.track]
            if (self.origin_us < 0 or self.segment_sample < 0 or self.output_sample < 0
                    or not 0 <= self.event_index <= len(current.events)):
                raise ValueError
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise SaveFormatError("SCUMM save iMUSE player state is invalid") from exc


class ScummV5EmbeddedAudioAdapter:
    """Lazily decodes embedded SOU resources and owns logical playheads."""

    def __init__(
        self,
        context: EngineContext,
        sound_key: Callable[[int], str],
    ) -> None:
        self.context = context
        self.sound_key = sound_key
        order = context.profile.options.get("embedded_audio_renditions", ["ROL", "ADL", "SPK"])
        if not isinstance(order, list) or not order:
            raise ResourceError("SCUMM embedded_audio_renditions must be a non-empty array")
        try:
            self.rendition_order = tuple(f"{str(item):<4}".encode("ascii") for item in order)
        except UnicodeEncodeError as exc:
            raise ResourceError("SCUMM embedded audio rendition tag is not ASCII") from exc
        if any(tag not in _RENDITIONS for tag in self.rendition_order):
            raise ResourceError("SCUMM embedded audio rendition tag is unsupported")
        self.sample_rate = int(context.profile.options.get("embedded_audio_sample_rate", 22_050))
        if not 8_000 <= self.sample_rate <= 96_000:
            raise ResourceError("SCUMM embedded audio sample rate is outside 8000..96000")
        self.sounds: dict[int, ScummV5EmbeddedSound] = {}
        self.players: dict[int, _ScummMidiPlayer] = {}
        catalog_key = context.profile.options.get("compiled_music_catalog")
        self.catalog = None if catalog_key is None else CompiledMusicCatalog.decode(
            context.services.resource_read(str(catalog_key)), str(catalog_key),
            source_reader=context.services.resource_read,
        )
        self.catalog_entries = (
            {} if self.catalog is None else {
                (entry.logical_id, entry.route_kind, entry.route_value): entry
                for entry in self.catalog.entries
            }
        )
        self.section_plans = (
            {} if self.catalog is None else {
                (item.logical_id, item.route_kind, item.route_value, item.hook_value): item
                for item in self.catalog.sections
            }
        )
        self.compiled_music = False
        self.music_route = ("default", 0)
        self.music_section: dict[str, object] | None = None
        self.music_id: int | None = None
        self.music_position = 0
        self.active_sfx: dict[int, int] = {}
        self.speech_id: int | None = None
        self.speech_position = 0
        # M24R-B's bounded sound-80/82 composite keeps SCUMM ownership apart
        # from the one physical TAD song.  This is deliberately not a general
        # multi-song allocator.
        self.logical_compiled: dict[int, _LogicalCompiledOwner] = {}
        self._compiled_generation = 0
        self._trigger_owner: tuple[int, int] | None = None
        self._deferred: list[_DeferredImuseCommand] = []
        self._deferred_order = 0
        self.compiled_notifications: list[dict[str, object]] = []

    def _sound(self, sound: int) -> ScummV5EmbeddedSound:
        sound = int(sound)
        if sound not in self.sounds:
            key = self.sound_key(sound)
            self.sounds[sound] = ScummV5EmbeddedSound.decode(
                self.context.services.resource_read(key), key,
                rendition_order=self.rendition_order,
            )
        return self.sounds[sound]

    def play_music(self, sound: int) -> None:
        sound = int(sound)
        entry = self.catalog_entries.get((sound, "default", 0))
        if entry is not None and self.context.negotiated_capabilities & EngineCapability.CHIP_AUDIO:
            if self.music_id is not None:
                self.stop_music()
            self.music_id, self.music_position = sound, 0
            self.compiled_music = True
            self.music_route = (entry.route_kind, entry.route_value)
            self.music_section = None
            self._compiled_generation += 1
            self.logical_compiled[sound] = _LogicalCompiledOwner(
                "active", self._compiled_generation,
            )
            self.context.services.audio.play_music(
                sound, loop=entry.loop_start is not None,
                resource=entry.identity, backend="compiled_tad",
            )
            return
        item = self._sound(sound)
        self.music_id, self.music_position = sound, 0
        self.compiled_music = False
        self.music_route = ("default", 0)
        self.music_section = None
        if old is not None:
            self.logical_compiled.pop(old, None)
        self._invalidate_compiled_generation()
        self.players[sound] = _ScummMidiPlayer(item, self.sample_rate)
        self.context.services.audio.play_music(
            sound, loop=False, resource=item.key, backend="embedded_midi"
        )
        self.context.services.audio.start_pcm_stream(
            sound, sample_rate=self.sample_rate, resource=item.key
        )

    def stop_music(self) -> None:
        old = self.music_id
        self.music_id, self.music_position = None, 0
        self.compiled_music = False
        self.music_route = ("default", 0)
        self.music_section = None
        self.context.services.audio.stop_music()
        if old is not None and old in self.context.services.audio.pcm_stream_rates:
            self.context.services.audio.stop_pcm_stream(old)
        if old is not None:
            self.players.pop(old, None)

    def play_sfx(self, sound: int) -> None:
        sound = int(sound)
        # Sound 82 is a sequenced logical layer in the bounded Fate composite,
        # not a TAD SFX and not a second physical song.
        if sound == 82 and self.compiled_music and self.music_id == 80:
            self.logical_compiled[sound] = _LogicalCompiledOwner(
                "active", self._compiled_generation,
            )
            self.compiled_notifications.append({"event": "layer_active", "sound": sound})
            return
        if sound == 80 and 82 in self.logical_compiled and self.compiled_music:
            owner = self.logical_compiled.get(sound)
            if owner is None:
                self.logical_compiled[sound] = _LogicalCompiledOwner(
                    "active", self._compiled_generation,
                )
            else:
                owner.state, owner.speed = "active", 128
                owner.volume, owner.fade_target, owner.fade_remaining = 127, None, 0
            self.compiled_notifications.append({"event": "layer_admission", "sound": sound})
            return
        if ((int(sound), "default", 0) in self.catalog_entries
                and self.context.negotiated_capabilities & EngineCapability.CHIP_AUDIO):
            self.play_music(sound)
            return
        item = self._sound(sound)
        self.active_sfx[int(sound)] = 0
        self.players[int(sound)] = _ScummMidiPlayer(item, self.sample_rate)
        self.context.services.audio.play_sfx(
            sound, priority=item.priority, resource=item.key, backend="embedded_midi"
        )
        self.context.services.audio.start_pcm_stream(
            sound, sample_rate=self.sample_rate, resource=item.key
        )

    def stop_sfx(self, sound: int) -> None:
        if int(sound) in self.logical_compiled:
            self.logical_compiled.pop(int(sound), None)
            return
        if self.music_id == int(sound):
            self.stop_music()
            return
        self.active_sfx.pop(int(sound), None)
        self.players.pop(int(sound), None)
        self.context.services.audio.stop_sfx(sound)
        if int(sound) in self.context.services.audio.pcm_stream_rates:
            self.context.services.audio.stop_pcm_stream(sound)

    def stop_all(self) -> None:
        streams = set(self.active_sfx)
        if self.music_id is not None:
            streams.add(self.music_id)
        self.music_id, self.music_position = None, 0
        self.compiled_music = False
        self.music_route = ("default", 0)
        self.active_sfx.clear()
        self.players.clear()
        self.speech_id, self.speech_position = None, 0
        self.logical_compiled.clear()
        self._invalidate_compiled_generation()
        self.context.services.audio.stop_music()
        self.context.services.audio.stop_sfx()
        self.context.services.audio.stop_speech()
        for sound in streams:
            if sound in self.context.services.audio.pcm_stream_rates:
                self.context.services.audio.stop_pcm_stream(sound)

    def play_speech(self, sound: int) -> None:
        raise ResourceError(f"SCUMM embedded MIDI sound {sound} is not speech PCM")

    def is_running(self, sound: int) -> bool:
        owner = self.logical_compiled.get(int(sound))
        if owner is not None:
            return owner.state in ("requested", "deferred", "active", "paused", "fading")
        return int(sound) == self.music_id or int(sound) in self.active_sfx

    def _invalidate_compiled_generation(self) -> None:
        generation = self._compiled_generation
        self._deferred = [item for item in self._deferred
                          if item.owner_generation != generation]
        self._trigger_owner = None

    def set_priority(self, sound: int, value: int) -> bool:
        owner = self.logical_compiled.get(int(sound))
        if owner is None:
            return False
        owner.priority = int(value)
        return True

    def set_speed(self, sound: int, value: int) -> bool:
        owner = self.logical_compiled.get(int(sound))
        if owner is None:
            return False
        owner.speed = int(value)
        owner.state = "paused" if value == 0 else "active"
        return True

    def fade_sound(self, sound: int, target: int, duration: int) -> bool:
        owner = self.logical_compiled.get(int(sound))
        if owner is None:
            return False
        owner.fade_target = int(target)
        owner.fade_remaining = int(duration)
        owner.state = "fading"
        self.compiled_notifications.append({
            "event": "fade_begin", "sound": int(sound), "target": int(target),
            "duration": int(duration), "generation": owner.generation,
        })
        return True

    def install_trigger(self, sound: int, marker: int) -> bool:
        owner = self.logical_compiled.get(int(sound))
        if owner is None:
            return False
        self._trigger_owner = (int(sound), int(marker))
        return True

    def enqueue_deferred(self, payload: list[int]) -> bool:
        if not payload:
            return False
        if payload[0] == -1:
            # Canonical enqueue-command -1 closes the current trigger group;
            # it is not itself a deferred command.
            self._trigger_owner = None
            return True
        if self._trigger_owner is None:
            return False
        sound, marker = self._trigger_owner
        self._deferred_order += 1
        item = _DeferredImuseCommand(
            sound, self._compiled_generation, marker, tuple(int(x) for x in payload),
            self._deferred_order,
        )
        self._deferred.append(item)
        if item.payload[0] & 0xff == 8 and len(item.payload) == 2:
            target = item.payload[1]
            self.logical_compiled[target] = _LogicalCompiledOwner(
                "deferred", self._compiled_generation,
            )
        return True

    def clear_deferred(self) -> None:
        self._deferred.clear()
        self._trigger_owner = None

    def notify_compiled_marker(self, sound: int, marker: int, generation: int) -> int:
        if generation != self._compiled_generation:
            return 0
        matches = [item for item in self._deferred if not item.consumed
                   and item.owner_sound == int(sound) and item.marker == int(marker)
                   and item.owner_generation == generation]
        for item in sorted(matches, key=lambda value: value.installation_order):
            item.consumed = True
            self._execute_deferred(item.payload)
        if matches:
            self.compiled_notifications.append({
                "event": "marker", "sound": int(sound), "marker": int(marker),
                "generation": generation, "commands": len(matches),
            })
        return len(matches)

    def _execute_deferred(self, payload: tuple[int, ...]) -> None:
        encoded = payload[0] & 0xffff
        command, parameter = encoded & 0xff, encoded >> 8
        if parameter == 0 and command == 8 and len(payload) == 2:
            self.play_sfx(payload[1])
        elif parameter == 1 and command == 1 and len(payload) == 3:
            self.set_priority(payload[1], payload[2])
        elif parameter == 1 and command == 6 and len(payload) == 3:
            self.set_speed(payload[1], payload[2])
        elif parameter == 1 and command == 13 and len(payload) == 4:
            self.fade_sound(payload[1], payload[2], payload[3])
        else:
            raise ResourceError(f"deferred iMUSE command ${encoded:04X} is unsupported")

    def set_hook(self, sound: int, cls: int, value: int, channel: int) -> bool:
        if (self.compiled_music and self.music_id == int(sound) and cls == 0
                and channel == 0):
            plan = self.section_plans.get((int(sound), *self.music_route, int(value)))
            if plan is not None:
                self.music_section = {
                    "identity": plan.identity, "bank": plan.instrument_bank_sha256,
                    "route_history": [plan.route_kind, plan.route_value],
                    "current": plan.current_section, "pending_hook": plan.hook_value,
                    "boundary": plan.boundary, "boundary_token": plan.boundary_token,
                    "selected": plan.hook_section, "selector": plan.selector,
                    "consumption": "pending",
                }
                self.context.services.audio.select_music_section(
                    plan.selector, plan.boundary_token,
                    current_section=plan.current_section,
                    selected_section=plan.hook_section,
                )
                return True
            entry = self.catalog_entries.get((int(sound), "hook", int(value)))
            if entry is None:
                return False
            self.music_position = 0
            self.music_route = (entry.route_kind, entry.route_value)
            self.music_section = None
            self.context.services.audio.play_music(
                int(sound), loop=entry.loop_start is not None,
                resource=entry.identity, backend="compiled_tad_route",
                route_kind=entry.route_kind, route_value=entry.route_value,
            )
            return True
        player = self.players.get(int(sound))
        return player is not None and player.set_hook(cls, value, channel)

    def tick(self) -> None:
        for sound, owner in tuple(self.logical_compiled.items()):
            if owner.fade_remaining:
                owner.fade_remaining -= 1
                if owner.fade_remaining == 0:
                    owner.volume = owner.fade_target if owner.fade_target is not None else owner.volume
                    if owner.volume == 0:
                        owner.state = "stopped"
                        self.compiled_notifications.append({
                            "event": "fade_complete", "sound": sound,
                            "generation": owner.generation,
                        })
                    else:
                        owner.state = "active"
        if self.music_id is not None:
            if self.compiled_music:
                entry = self.catalog_entries[(self.music_id, *self.music_route)]
                self.music_position += 1
                if (self.music_section is not None
                        and self.music_section["consumption"] == "pending"):
                    boundary = (
                        int(self.music_section["boundary"]) * self.context.profile.tick_hz
                        + self.catalog.time_scale - 1
                    ) // self.catalog.time_scale
                    if self.music_position >= boundary:
                        self.music_section["current"] = self.music_section["selected"]
                        self.music_section["pending_hook"] = 0
                        self.music_section["consumption"] = "consumed"
                loop = entry.loop_frames(
                    self.context.profile.tick_hz, self.catalog.time_scale,
                )
                if loop is not None and self.music_position >= loop[1]:
                    self.music_position = loop[0]
                elif self.music_position >= entry.duration_frames(
                    self.context.profile.tick_hz, self.catalog.time_scale,
                ):
                    self.stop_music()
            else:
                self._render_frame(self.music_id, self.music_position)
                self.music_position += 1
                if self.players[self.music_id].complete:
                    self.stop_music()
        for sound, position in tuple(self.active_sfx.items()):
            self._render_frame(sound, position)
            position += 1
            if self.players[sound].complete:
                self.stop_sfx(sound)
            else:
                self.active_sfx[sound] = position

    def _render_frame(self, sound: int, position: int) -> None:
        rate = self.context.profile.tick_hz
        item = self._sound(sound)
        start_us = position * 1_000_000 // rate
        end_us = (position + 1) * 1_000_000 // rate
        first_sample = (start_us * self.sample_rate + 999_999) // 1_000_000
        last_sample = (end_us * self.sample_rate + 999_999) // 1_000_000
        self.context.services.audio.submit_pcm(
            sound,
            self.players[sound].render(
                last_sample - first_sample,
                self.context.services.audio.master_volume / 255.0 * 0.22,
            )
        )

    def save_state(self) -> dict[str, object]:
        return {
            "kind": "embedded-midi-v2",
            "music": None if self.music_id is None else [self.music_id, self.music_position],
            "sfx": [[sound, position] for sound, position in sorted(self.active_sfx.items())],
            "speech": None,
            "players": {str(sound): player.save_state()
                        for sound, player in sorted(self.players.items())},
            "compiled_music": self.compiled_music,
            "music_route": [self.music_route[0], self.music_route[1]],
            "catalog_sha256": None if self.catalog is None else self.catalog.sha256,
            "music_identity": (
                self.catalog_entries[(self.music_id, *self.music_route)].identity
                if self.compiled_music and self.music_id is not None else None
            ),
            "music_section": self.music_section,
        }

    def load_state(self, data: object) -> None:
        if not isinstance(data, dict) or data.get("kind") != "embedded-midi-v2":
            raise SaveFormatError("SCUMM save embedded audio state is invalid")
        compiled_music = bool(data.get("compiled_music", False))
        raw_route = data.get("music_route", ["default", 0])
        if (not isinstance(raw_route, list) or len(raw_route) != 2
                or not isinstance(raw_route[0], str)
                or isinstance(raw_route[1], bool) or not isinstance(raw_route[1], int)):
            raise SaveFormatError("SCUMM save compiled music route is invalid")
        music_route = (raw_route[0], raw_route[1])
        expected_catalog = None if self.catalog is None else self.catalog.sha256
        if data.get("catalog_sha256") != expected_catalog:
            raise SaveFormatError("SCUMM save compiled music catalog identity differs")
        music = self._saved(data.get("music"), nullable=True, compiled=compiled_music)
        raw_sfx = data.get("sfx")
        if not isinstance(raw_sfx, list):
            raise SaveFormatError("SCUMM save embedded SFX state must be an array")
        sfx = [self._saved(item, nullable=False, compiled=False) for item in raw_sfx]
        if data.get("speech") is not None:
            raise SaveFormatError("SCUMM save embedded audio has unsupported speech state")
        if len({item[0] for item in sfx if item is not None}) != len(sfx):
            raise SaveFormatError("SCUMM save contains duplicate embedded sounds")
        raw_players = data.get("players")
        if not isinstance(raw_players, dict):
            raise SaveFormatError("SCUMM save iMUSE players must be an object")
        expected_players = {str(item[0]) for item in sfx if item is not None}
        if music is not None and not compiled_music:
            expected_players.add(str(music[0]))
        if set(raw_players) != expected_players:
            raise SaveFormatError("SCUMM save iMUSE players differ from active sounds")
        if compiled_music:
            if music is None:
                raise SaveFormatError("SCUMM save marks absent music as compiled")
            try:
                entry = self.catalog_entries[(music[0], *music_route)]
            except KeyError as exc:
                raise SaveFormatError("SCUMM save compiled music route is unavailable") from exc
            if data.get("music_identity") != entry.identity:
                raise SaveFormatError("SCUMM save compiled music source identity differs")
            raw_section = data.get("music_section")
            if raw_section is not None:
                if not isinstance(raw_section, dict):
                    raise SaveFormatError("SCUMM save compiled section state is invalid")
                plans = [plan for key, plan in self.section_plans.items()
                         if key[:3] == (music[0], *music_route)
                         and raw_section.get("identity") == plan.identity]
                plan = plans[0] if len(plans) == 1 else None
                if (plan is None
                        or raw_section.get("bank") != plan.instrument_bank_sha256
                        or raw_section.get("consumption") not in ("pending", "consumed")):
                    raise SaveFormatError("SCUMM save compiled section identity differs")
        elif data.get("music_identity") is not None:
            raise SaveFormatError("SCUMM save has a compiled identity for source music")
        self.stop_all()
        if music is not None:
            sound, position = music
            self.music_id, self.music_position = sound, position
            self.compiled_music = compiled_music
            self.music_route = music_route if compiled_music else ("default", 0)
            self.music_section = (
                None if data.get("music_section") is None else dict(data["music_section"])
            )
            if compiled_music:
                entry = self.catalog_entries[(sound, *self.music_route)]
                self.context.services.audio.play_music(
                    sound, loop=entry.loop_start is not None, resource=entry.identity,
                    backend="compiled_tad", position=position,
                )
            else:
                item = self._sound(sound)
                self.context.services.audio.play_music(
                    sound, loop=False, resource=item.key,
                    backend="embedded_midi", position=position,
                )
                self.context.services.audio.start_pcm_stream(
                    sound, sample_rate=self.sample_rate, resource=item.key
                )
                player = _ScummMidiPlayer(item, self.sample_rate)
                player.load_state(raw_players[str(sound)])
                self.players[sound] = player
        for item in sfx:
            assert item is not None
            sound, position = item
            decoded = self._sound(sound)
            self.active_sfx[sound] = position
            self.context.services.audio.play_sfx(
                sound, priority=decoded.priority, resource=decoded.key,
                backend="embedded_midi", position=position,
            )
            self.context.services.audio.start_pcm_stream(
                sound, sample_rate=self.sample_rate, resource=decoded.key
            )
            player = _ScummMidiPlayer(decoded, self.sample_rate)
            player.load_state(raw_players[str(sound)])
            self.players[sound] = player

    def _saved(
        self, value: object, *, nullable: bool, compiled: bool = False,
    ) -> tuple[int, int] | None:
        if value is None and nullable:
            return None
        if not isinstance(value, list) or len(value) != 2:
            raise SaveFormatError("SCUMM save embedded playhead must contain id and frame")
        sound, position = int(value[0]), int(value[1])
        try:
            if compiled:
                candidates = [
                    entry for (logical, _kind, _value), entry in self.catalog_entries.items()
                    if logical == sound
                ]
                if not candidates:
                    raise KeyError(sound)
                duration = max(entry.duration_frames(
                    self.context.profile.tick_hz, self.catalog.time_scale,
                ) for entry in candidates)
            else:
                duration = self._sound(sound).duration_frames(self.context.profile.tick_hz)
        except (KeyError, ResourceError) as exc:
            raise SaveFormatError(f"SCUMM save embedded sound is unavailable: {exc}") from exc
        if not 0 <= position < duration:
            raise SaveFormatError("SCUMM save embedded playhead lies outside its sound")
        return sound, position

    def inspect(self) -> dict[str, object]:
        return {
            "backend": "compiled_tad" if self.compiled_music else "embedded_imuse",
            "sample_rate": self.sample_rate,
            "music": self.music_id,
            "music_position": self.music_position,
            "music_route": list(self.music_route),
            "music_section": self.music_section,
            "sfx": dict(sorted(self.active_sfx.items())),
            "speech": None,
            "speech_position": 0,
            "logical_compiled": {
                str(sound): {
                    "state": owner.state, "generation": owner.generation,
                    "priority": owner.priority, "speed": owner.speed,
                    "volume": owner.volume, "fade_remaining": owner.fade_remaining,
                }
                for sound, owner in sorted(self.logical_compiled.items())
            },
            "deferred": [
                {"owner": item.owner_sound, "generation": item.owner_generation,
                 "marker": item.marker, "payload": list(item.payload),
                 "order": item.installation_order, "consumed": item.consumed}
                for item in self._deferred
            ],
            "compiled_notifications": list(self.compiled_notifications),
            "catalog": None if self.catalog is None else {
                "key": self.catalog.key,
                "sha256": self.catalog.sha256,
                "entries": len(self.catalog.entries),
            },
            "decoded": {
                str(sound): item.inspect() for sound, item in sorted(self.sounds.items())
            },
            "imuse": {
                str(sound): {
                    "track": player.track,
                    "tick_us": player.time_us,
                    "hooks": list(player.jump_hooks),
                    "markers": list(player.markers),
                    "branches": [list(item) for item in player.branches],
                    "parts": [index for index, enabled in enumerate(player.part_on) if enabled],
                }
                for sound, player in sorted(self.players.items())
            },
        }
