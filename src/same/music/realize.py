"""Source-neutral realization helpers for canonical music sequences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .devices import AdlibCaptureCalibration, AdlibPatch, ScummV5AdlibDevice
from .instruments import InstrumentBank
from .model import ControllerEvent, NoteOffEvent, NoteOnEvent, SequenceIR


@dataclass(frozen=True, slots=True)
class ResolvedAdlibNote:
    start: int
    end: int
    midi_note: int
    volume: int
    zone_name: str
    part_id: int
    note_id: int
    volume_changes: tuple[tuple[int, int], ...]


def realize_scumm_adlib_notes(
    sequence: SequenceIR,
    patches: Mapping[int, AdlibPatch],
    bank: InstrumentBank,
) -> tuple[ResolvedAdlibNote, ...]:
    """Resolve patch identities, dynamics, and zones without cue knowledge."""
    if bank.source_device != ScummV5AdlibDevice.identifier:
        raise ValueError(f"instrument bank targets unsupported device {bank.source_device!r}")
    part_fingerprints = {
        part.part_id: part.instrument.patch_fingerprint for part in sequence.parts
    }
    for part_id, fingerprint in part_fingerprints.items():
        patch = patches.get(part_id)
        if patch is None or fingerprint != patch.fingerprint:
            raise ValueError(f"SCUMM AdLib part {part_id} patch identity differs")
    device = ScummV5AdlibDevice(AdlibCaptureCalibration(
        bank.capture_velocity, bank.capture_cc7, bank.reference_volume,
    ))
    controls = {part.part_id: 127 for part in sequence.parts}
    active: dict[int, list[object]] = {}
    output: list[ResolvedAdlibNote] = []
    for scheduled in sequence.events:
        payload = scheduled.payload
        if isinstance(payload, ControllerEvent) and payload.controller == 7:
            controls[payload.part_id] = payload.value_q16 >> 16
            for entry in active.values():
                if int(entry[4]) == payload.part_id:
                    patch = patches[payload.part_id]
                    entry[5].append((
                        scheduled.tick,
                        device.backend_volume(
                            patch, int(entry[1]), controls[payload.part_id],
                        ),
                    ))
        elif isinstance(payload, NoteOnEvent):
            part_id = payload.part_id
            patch = patches[part_id]
            midi_note = payload.pitch_q8_8 >> 8
            if payload.pitch_q8_8 & 0xFF:
                raise ValueError("sampled SCUMM AdLib realization requires integer pitch")
            zone = bank.resolve(patch.fingerprint, midi_note)
            active[payload.note_id] = [
                scheduled.tick, payload.velocity, controls[part_id], zone.name,
                part_id, [], midi_note,
            ]
        elif isinstance(payload, NoteOffEvent):
            start, velocity, initial_cc7, zone_name, part_id, changes, midi_note = (
                active.pop(payload.note_id)
            )
            patch = patches[int(part_id)]
            initial_volume = device.backend_volume(
                patch, int(velocity), int(initial_cc7),
            )
            cleaned: list[tuple[int, int]] = []
            current = initial_volume
            for tick, changed in changes:
                tick = max(int(start), min(scheduled.tick, int(tick)))
                if int(start) < tick < scheduled.tick and int(changed) != current:
                    cleaned.append((tick, int(changed)))
                    current = int(changed)
            output.append(ResolvedAdlibNote(
                int(start), scheduled.tick, int(midi_note), initial_volume,
                str(zone_name), int(part_id), payload.note_id, tuple(cleaned),
            ))
    if active:
        raise ValueError("SCUMM AdLib realization ended with active notes")
    return tuple(sorted(
        output, key=lambda note: (note.start, note.midi_note, note.end, note.note_id),
    ))


def sequence_trace(sequence: SequenceIR) -> tuple[dict[str, object], ...]:
    """Stable backend-facing trace; deliberately contains no importer fields."""
    trace: list[dict[str, object]] = []
    for event in sequence.events:
        payload = event.payload
        record: dict[str, object] = {
            "tick": event.tick,
            "order": event.source_order,
        }
        if isinstance(payload, NoteOnEvent):
            record.update({
                "event": "note_on", "part": payload.part_id,
                "note_id": payload.note_id, "pitch_q8_8": payload.pitch_q8_8,
                "velocity": payload.velocity,
            })
        elif isinstance(payload, NoteOffEvent):
            record.update({
                "event": "note_off", "part": payload.part_id,
                "note_id": payload.note_id,
                "release_velocity": payload.release_velocity,
            })
        elif isinstance(payload, ControllerEvent):
            record.update({
                "event": "controller", "part": payload.part_id,
                "controller": payload.controller, "value_q16": payload.value_q16,
            })
        else:
            record.update({"event": "marker", "marker": payload.marker, "value": payload.value})
        trace.append(record)
    return tuple(trace)
