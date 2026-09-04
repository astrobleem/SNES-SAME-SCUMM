"""Small deterministic integer reference synthesizer for music conformance."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .model import ControllerEvent, NoteOffEvent, NoteOnEvent, PartSpec, SequenceIR
from .playback import PlaybackAction, PlaybackSession


_SEMITONE_Q48 = 298_212_349_810_582
_Q48 = 1 << 48


def _note_frequency_microhertz(note: int) -> int:
    if not 0 <= note <= 128:
        raise ValueError(f"reference synth pitch {note} lies outside MIDI range")
    frequency = 440_000_000
    if note < 69:
        for _ in range(69 - note):
            frequency = ((frequency << 48) + _SEMITONE_Q48 // 2) // _SEMITONE_Q48
    else:
        for _ in range(note - 69):
            frequency = (frequency * _SEMITONE_Q48 + _Q48 // 2) >> 48
    return frequency


def _phase_increment(pitch_q8_8: int, sample_rate: int) -> int:
    note, fraction = divmod(int(pitch_q8_8), 256)
    if not 0 <= note <= 127 or (note == 127 and fraction):
        raise ValueError("reference synth pitch lies outside MIDI range")
    low = _note_frequency_microhertz(note)
    high = _note_frequency_microhertz(note + 1)
    frequency = low + (high - low) * fraction // 256
    return (frequency << 32) // (sample_rate * 1_000_000)


@dataclass(slots=True)
class _ReferenceVoice:
    part_id: int
    velocity: int
    phase_increment: int
    percussion: bool
    phase: int = 0
    noise: int = 1


class ReferenceSynth:
    """Audible oracle, intentionally not a production instrument renderer."""

    def __init__(self, parts: tuple[PartSpec, ...], sample_rate: int) -> None:
        self.sample_rate = int(sample_rate)
        self._parts = {part.part_id: part for part in parts}
        self._volume = {part.part_id: 127 for part in parts}
        self._voices: dict[int, _ReferenceVoice] = {}
        self._pcm = bytearray()

    @property
    def pcm_s16le(self) -> bytes:
        return bytes(self._pcm)

    @property
    def active_voice_handles(self) -> tuple[int, ...]:
        return tuple(sorted(self._voices))

    def note_on(self, voice: int, event: NoteOnEvent) -> None:
        part = self._parts[event.part_id]
        self._voices[voice] = _ReferenceVoice(
            event.part_id,
            event.velocity,
            _phase_increment(event.pitch_q8_8, self.sample_rate),
            part.percussion,
            noise=((event.note_id + 1) * 0x1D3D ^ (event.part_id + 1) * 0xB4B) & 0xFFFF or 1,
        )

    def note_off(self, voice: int, event: NoteOffEvent) -> None:
        del event
        self._voices.pop(voice)

    def controller(self, event: ControllerEvent) -> None:
        if event.controller == 7:
            self._volume[event.part_id] = max(0, min(127, event.value_q16 >> 16))

    @staticmethod
    def _triangle(phase: int) -> int:
        position = (phase >> 16) & 0xFFFF
        return 32767 - (abs(position - 32768) * 65534 // 32768)

    @staticmethod
    def _noise(voice: _ReferenceVoice) -> int:
        feedback = (voice.noise ^ (voice.noise >> 1)) & 1
        voice.noise = (voice.noise >> 1) | (feedback << 15)
        return 32767 if voice.noise & 1 else -32767

    def advance(self, frames: int) -> None:
        if frames < 0:
            raise ValueError("reference synth cannot render negative frames")
        for _ in range(frames):
            mixed = 0
            for handle in sorted(self._voices):
                voice = self._voices[handle]
                voice.phase = (voice.phase + voice.phase_increment) & 0xFFFFFFFF
                waveform = self._noise(voice) if voice.percussion else self._triangle(voice.phase)
                volume = self._volume[voice.part_id]
                mixed += waveform * voice.velocity * volume // (127 * 127 * 4)
            mixed = max(-32768, min(32767, mixed))
            self._pcm.extend(struct.pack("<h", mixed))

    def stop(self) -> None:
        self._voices.clear()


def pcm_wav(pcm_s16le: bytes, sample_rate: int) -> bytes:
    """Wrap mono signed-16 PCM in a canonical 44-byte RIFF/WAVE header."""
    if len(pcm_s16le) % 2:
        raise ValueError("signed-16 PCM byte count must be even")
    byte_rate = int(sample_rate) * 2
    return b"".join((
        b"RIFF", struct.pack("<I", 36 + len(pcm_s16le)), b"WAVE",
        b"fmt ", struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, byte_rate, 2, 16),
        b"data", struct.pack("<I", len(pcm_s16le)), pcm_s16le,
    ))


@dataclass(frozen=True, slots=True)
class ReferenceRender:
    sample_rate: int
    frames: int
    pcm_s16le: bytes
    wav: bytes
    actions: tuple[PlaybackAction, ...]


def render_reference(
    sequence: SequenceIR,
    *,
    sample_rate: int = 24_000,
    voice_limit: int = 8,
) -> ReferenceRender:
    synth = ReferenceSynth(sequence.parts, sample_rate)
    session = PlaybackSession(
        sequence, synth, sample_rate=sample_rate, voice_limit=voice_limit,
    )
    session.finish()
    pcm = synth.pcm_s16le
    return ReferenceRender(
        sample_rate, len(pcm) // 2, pcm, pcm_wav(pcm, sample_rate), session.actions,
    )

