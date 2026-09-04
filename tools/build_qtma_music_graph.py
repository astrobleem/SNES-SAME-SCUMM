#!/usr/bin/env python3
"""Copyright-free QTMA fixture adapter for SAME's generic music graph."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import struct
import subprocess
import wave

from same.music import (
    ControllerEvent, MusicBuildGraph, NoteOffEvent, NoteOnEvent, SampledNote,
    TadInstrument, TadPanPolicy, compile_tad_mml,
    decode_sequence_audit, encode_sequence_audit, normalize_sequence_time_scale,
)
from same.music.importers.qtma import decode_qtma_events
from same.music.importers.qtma_mov import extract_qtma_movie


ROOT = Path(__file__).resolve().parents[1]


def _sampled_notes(sequence) -> tuple[SampledNote, ...]:
    """Resolve QTMA note lifetimes and CC7 without source-family code in TAD."""
    controls = {part.part_id: 127 for part in sequence.parts}
    active: dict[int, list[object]] = {}
    output: list[SampledNote] = []

    def volume(velocity: int, control: int) -> int:
        return (velocity * control * 255 + 8064) // 16129

    for scheduled in sequence.events:
        event = scheduled.payload
        if isinstance(event, ControllerEvent) and event.controller == 7:
            controls[event.part_id] = max(0, min(127, event.value_q16 >> 16))
            for entry in active.values():
                if int(entry[3]) != event.part_id:
                    continue
                if scheduled.tick == int(entry[0]):
                    entry[4] = controls[event.part_id]
                else:
                    entry[5].append((
                        scheduled.tick,
                        volume(int(entry[2]), controls[event.part_id]),
                    ))
        elif isinstance(event, NoteOnEvent):
            if event.pitch_q8_8 & 0xFF:
                raise ValueError("QTMA TAD fixture requires integer MIDI pitch")
            active[event.note_id] = [
                scheduled.tick, event.pitch_q8_8 >> 8, event.velocity,
                event.part_id, controls[event.part_id], [],
            ]
        elif isinstance(event, NoteOffEvent):
            start, pitch, velocity, part_id, initial_control, changes = active.pop(event.note_id)
            percussion = next(part.percussion for part in sequence.parts if part.part_id == part_id)
            initial_volume = volume(int(velocity), int(initial_control))
            cleaned: list[tuple[int, int]] = []
            current_volume = initial_volume
            for tick, changed_volume in changes:
                if int(start) < int(tick) < scheduled.tick and changed_volume != current_volume:
                    cleaned.append((int(tick), int(changed_volume)))
                    current_volume = int(changed_volume)
            output.append(SampledNote(
                start, scheduled.tick, 36 if percussion else pitch,
                initial_volume,
                "qtma_drum" if percussion else "qtma_marimba",
                int(part_id), event.note_id, tuple(cleaned),
            ))
    if active:
        raise ValueError("QTMA sequence ended with active notes")
    return tuple(output)


def _wav(path: Path, samples: list[int], rate: int = 32000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


def _generated_samples(stage: Path) -> None:
    # Deterministic, repository-owned integer waveforms: a decaying struck tone
    # and a short LFSR noise burst. No external sound bank enters this proof.
    marimba: list[int] = []
    for index in range(12000):
        phase = index % 122
        triangle = phase if phase < 61 else 122 - phase
        centered = triangle * 2 - 61
        envelope = 12000 - index
        marimba.append(centered * envelope // 24)
    state = 0xACE1
    drum: list[int] = []
    for index in range(5008):
        state = (state >> 1) ^ (0xB400 if state & 1 else 0)
        envelope = 5008 - index
        drum.append(((state & 0xFFFF) - 32768) * envelope // 11000)
    _wav(stage / "qtma_marimba.wav", marimba)
    _wav(stage / "qtma_drum.wav", drum)


class QtmaFixtureMusicGraphAdapter:
    """A second engine family using only SAME's checked-in QTMA fixture."""

    def __init__(self, graph: MusicBuildGraph) -> None:
        self.graph = graph
        self.dependencies = {
            dependency.name: ROOT / dependency.path for dependency in graph.dependencies
        }
        self._audits: dict[int, bytes] = {}

    def audit(self, node) -> bytes:
        try:
            return self._audits[node.logical_id]
        except KeyError as exc:
            raise ValueError(
                f"QTMA rendition {node.logical_id} has no sequence audit"
            ) from exc

    def read_source(self, node) -> bytes:
        dependency = node.policy.get("fixture_dependency")
        if not isinstance(dependency, str) or dependency not in self.dependencies:
            raise ValueError("QTMA rendition has no fixture dependency")
        return bytes.fromhex(self.dependencies[dependency].read_text(encoding="ascii"))

    def render(self, node, source: bytes) -> bytes:
        if node.importer != "qtma_events_v1":
            raise ValueError(f"unsupported QTMA music importer {node.importer!r}")
        sequence = decode_qtma_events(
            source, source=node.source_resource, time_scale=self.graph.time_scale,
        )
        return self._render_sequence(node, sequence)

    def _render_sequence(self, node, sequence, sampled_notes=None) -> bytes:
        # CC64 is consumed here: QTMA note durations already carry this fixture's
        # intended lifetimes. The backend receives only its supported CC7/CC10 set.
        backend_sequence = replace(sequence, events=tuple(
            scheduled for scheduled in sequence.events
            if not isinstance(scheduled.payload, ControllerEvent)
            or scheduled.payload.controller in (7, 10)
        ))
        song = compile_tad_mml(
            backend_sequence,
            _sampled_notes(sequence) if sampled_notes is None else sampled_notes,
            (
                TadInstrument("qtma_marimba", "qtma_marimba"),
                TadInstrument("qtma_drum", "qtma_drum"),
            ),
            title=str(node.policy["title"]), author=str(node.policy["author"]),
            pan_policy=TadPanPolicy(str(node.policy["pan"])),
            voice_limit=int(node.policy["voice_limit"]),
        )
        return song.mml.encode("utf-8")

    def replay_audit(self, node, raw: bytes) -> bytes:
        """Realize canonical normalized IR without invoking a source importer."""
        audit = decode_sequence_audit(raw)
        expected = _sampled_notes(audit.normalized)
        if audit.realization != expected:
            raise ValueError("sequence audit realization differs from normalized IR")
        if audit.normalized.source_time_scale != self.graph.time_scale:
            raise ValueError("sequence audit target time scale differs from graph")
        if audit.normalized.end_tick != node.duration:
            raise ValueError("sequence audit duration differs from graph")
        return self._render_sequence(
            node, audit.normalized, sampled_notes=audit.realization,
        )

    def finalize(self, graph, stage: Path, rendered, compiler: Path) -> None:
        _generated_samples(stage)
        project = {
            "_about": {
                "file_type": "Terrific Audio Driver project file",
                "version": "0.2.0-beta.2",
                "_comment": "Generated from SAME's copyright-free QTMA fixture.",
            },
            "instruments": [
                {
                    "name": "qtma_marimba", "source": "qtma_marimba.wav",
                    "freq": 261.625565, "loop": "none", "evaluator": "default",
                    "ignore_gaussian_overflow": False, "first_octave": 2,
                    "last_octave": 5, "envelope": "adsr 15 2 0 0",
                },
                {
                    "name": "qtma_drum", "source": "qtma_drum.wav",
                    "freq": 65.406391, "loop": "none", "evaluator": "default",
                    "ignore_gaussian_overflow": False, "first_octave": 2,
                    "last_octave": 2, "envelope": "adsr 15 1 0 0",
                },
            ],
            "samples": [], "sound_effects": [],
            "songs": [
                {"name": node.compiled_song, "source": node.output}
                for node in graph.nodes
            ],
        }
        project_path = stage / graph.project_output
        project_path.write_text(
            json.dumps(project, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        subprocess.run((
            str(compiler), "asar-export", "--lorom",
            "--output-asm", str(stage / "tad.asm"),
            "--output-bin", str(stage / "tad.bin"),
            "--output-inc", str(stage / "tad.inc"), str(project_path),
        ), check=True)
        enums = (stage / "tad.inc").read_text(encoding="utf-8")
        for node in graph.nodes:
            match = re.search(
                rf"^\s*!Song_{re.escape(node.compiled_song)}\s*=\s*(\d+)\s*$",
                enums, re.MULTILINE,
            )
            if match is None or int(match.group(1)) != node.compiled_song_id:
                raise RuntimeError(f"compiled enum differs for {node.compiled_song!r}")


class QtmaMovieMusicGraphAdapter(QtmaFixtureMusicGraphAdapter):
    """Container adapter terminating at the unchanged QTMA event importer."""

    def read_source(self, node) -> bytes:
        dependency = node.policy.get("movie_dependency")
        if not isinstance(dependency, str) or dependency not in self.dependencies:
            raise ValueError("QTMA movie rendition has no movie dependency")
        return bytes.fromhex(self.dependencies[dependency].read_text(encoding="ascii"))

    def render(self, node, source: bytes) -> bytes:
        if node.importer != "qtma_mov_musi_v1":
            raise ValueError(f"unsupported QTMA movie importer {node.importer!r}")
        music_track = node.policy.get("music_track", 0)
        if isinstance(music_track, bool) or not isinstance(music_track, int):
            raise ValueError("QTMA movie music_track must be an integer")
        extracted = extract_qtma_movie(
            source, source=node.source_resource, music_track=music_track,
        )
        source_time_scale = node.policy.get("source_time_scale")
        if (
            isinstance(source_time_scale, bool)
            or not isinstance(source_time_scale, int)
            or source_time_scale < 1
        ):
            raise ValueError("QTMA movie source_time_scale must be a positive integer")
        if extracted.time_scale != source_time_scale:
            raise ValueError(
                f"QTMA movie time scale {extracted.time_scale} differs from "
                f"declared source {source_time_scale}"
            )
        sequence = decode_qtma_events(
            extracted.event_source, time_scale=extracted.time_scale,
        )
        policy = node.policy.get("time_normalization")
        if not isinstance(policy, str):
            raise ValueError("QTMA movie time_normalization policy is required")
        normalized = normalize_sequence_time_scale(
            sequence, self.graph.time_scale, policy=policy,
        )
        if normalized.sequence.end_tick != node.duration:
            raise ValueError(
                f"normalized QTMA duration {normalized.sequence.end_tick} "
                f"differs from graph {node.duration}"
            )
        notes = _sampled_notes(normalized.sequence)
        self._audits[node.logical_id] = encode_sequence_audit(
            sequence, normalized.sequence, normalized,
            realization=tuple({
                "start": note.start, "end": note.end,
                "midi_note": note.midi_note, "volume": note.volume,
                "zone_name": note.zone_name, "part_id": note.part_id,
                "note_id": note.note_id,
                "volume_changes": [list(change) for change in note.volume_changes],
            } for note in notes),
        )
        return self._render_sequence(node, normalized.sequence)
