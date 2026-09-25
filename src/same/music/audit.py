"""Canonical, source-neutral audit encoding for the symbolic sequencer IR."""

from __future__ import annotations

from dataclasses import dataclass, fields
import json
from typing import Mapping, Sequence

from .backends import SampledNote
from .model import (
    ControllerEvent, InstrumentRequest, MarkerEvent, NoteOffEvent, NoteOnEvent,
    PartSpec, Provenance, ScheduledEvent, SequenceIR,
)
from .timing import (
    TimeScaleNormalization, TimeScalePolicy, normalize_sequence_time_scale,
)


class SequenceAuditError(ValueError):
    def __init__(self, code: str, path: str, detail: str) -> None:
        self.code = code
        self.path = path
        super().__init__(f"music sequence audit {code} at {path}: {detail}")


@dataclass(frozen=True, slots=True)
class SequenceAudit:
    imported: SequenceIR
    normalized: SequenceIR
    timing: TimeScaleNormalization
    realization: tuple[SampledNote, ...]


def _object(value: object, path: str, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SequenceAuditError("invalid_type", path, "expected an object")
    observed = set(value)
    if observed != keys:
        raise SequenceAuditError(
            "invalid_fields", path,
            f"missing {sorted(keys - observed)}, unknown {sorted(observed - keys)}",
        )
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SequenceAuditError("invalid_type", path, "expected an integer")
    return value


def _optional_integer(value: object, path: str) -> int | None:
    return None if value is None else _integer(value, path)


def _provenance_from(value: object, path: str) -> Provenance:
    names = {field.name for field in fields(Provenance)}
    item = _object(value, path, names)
    source = item["source"]
    if not isinstance(source, str):
        raise SequenceAuditError("invalid_type", f"{path}.source", "expected a string")
    try:
        return Provenance(source, **{
            name: _optional_integer(item[name], f"{path}.{name}")
            for name in names if name != "source"
        })
    except ValueError as exc:
        raise SequenceAuditError("invalid_provenance", path, str(exc)) from exc


def _instrument(value: object, path: str) -> InstrumentRequest:
    names = {field.name for field in fields(InstrumentRequest)}
    item = _object(value, path, names)
    strings = ("portable_id", "synth_type", "synth_name", "instrument_name", "patch_fingerprint")
    for name in strings:
        if item[name] is not None and not isinstance(item[name], str):
            raise SequenceAuditError("invalid_type", f"{path}.{name}", "expected string or null")
    try:
        return InstrumentRequest(
            portable_id=item["portable_id"], synth_type=item["synth_type"],
            synth_name=item["synth_name"], instrument_name=item["instrument_name"],
            instrument_number=_optional_integer(item["instrument_number"], f"{path}.instrument_number"),
            gm_fallback=_optional_integer(item["gm_fallback"], f"{path}.gm_fallback"),
            patch_fingerprint=item["patch_fingerprint"],
        )
    except ValueError as exc:
        raise SequenceAuditError("invalid_instrument", path, str(exc)) from exc


def decode_canonical_sequence_ir(value: object, *, path: str = "sequence") -> SequenceIR:
    """Strictly reconstruct canonical IR; model invariants remain authoritative."""
    item = _object(value, path, {
        "source_time_scale", "end_tick", "loop", "provenance", "diagnostics",
        "parts", "events",
    })
    raw_parts = item["parts"]
    if not isinstance(raw_parts, list):
        raise SequenceAuditError("invalid_type", f"{path}.parts", "expected an array")
    parts = []
    for index, raw_part in enumerate(raw_parts):
        owner = f"{path}.parts[{index}]"
        part = _object(raw_part, owner, {
            "part_id", "instrument", "requested_polyphony",
            "typical_polyphony_q16", "percussion", "provenance",
        })
        if not isinstance(part["percussion"], bool):
            raise SequenceAuditError("invalid_type", f"{owner}.percussion", "expected boolean")
        provenance = None if part["provenance"] is None else _provenance_from(
            part["provenance"], f"{owner}.provenance",
        )
        parts.append(PartSpec(
            _integer(part["part_id"], f"{owner}.part_id"),
            _instrument(part["instrument"], f"{owner}.instrument"),
            _integer(part["requested_polyphony"], f"{owner}.requested_polyphony"),
            _integer(part["typical_polyphony_q16"], f"{owner}.typical_polyphony_q16"),
            part["percussion"], provenance,
        ))
    raw_events = item["events"]
    if not isinstance(raw_events, list):
        raise SequenceAuditError("invalid_type", f"{path}.events", "expected an array")
    events = []
    for index, raw_scheduled in enumerate(raw_events):
        owner = f"{path}.events[{index}]"
        scheduled = _object(raw_scheduled, owner, {
            "tick", "source_order", "event", "provenance",
        })
        raw_event = scheduled["event"]
        if not isinstance(raw_event, dict) or not isinstance(raw_event.get("type"), str):
            raise SequenceAuditError("invalid_type", f"{owner}.event", "expected typed event object")
        kind = raw_event["type"]
        if kind == "note_on":
            event = _object(raw_event, f"{owner}.event", {"type", "part_id", "note_id", "pitch_q8_8", "velocity"})
            payload = NoteOnEvent(*(_integer(event[name], f"{owner}.event.{name}") for name in ("part_id", "note_id", "pitch_q8_8", "velocity")))
        elif kind == "note_off":
            event = _object(raw_event, f"{owner}.event", {"type", "part_id", "note_id", "release_velocity"})
            payload = NoteOffEvent(*(_integer(event[name], f"{owner}.event.{name}") for name in ("part_id", "note_id", "release_velocity")))
        elif kind == "controller":
            event = _object(raw_event, f"{owner}.event", {"type", "part_id", "controller", "value_q16"})
            payload = ControllerEvent(*(_integer(event[name], f"{owner}.event.{name}") for name in ("part_id", "controller", "value_q16")))
        elif kind == "marker":
            event = _object(raw_event, f"{owner}.event", {"type", "marker", "value"})
            if not isinstance(event["marker"], str):
                raise SequenceAuditError("invalid_type", f"{owner}.event.marker", "expected string")
            payload = MarkerEvent(event["marker"], _integer(event["value"], f"{owner}.event.value"))
        else:
            raise SequenceAuditError("unknown_event", f"{owner}.event.type", repr(kind))
        events.append(ScheduledEvent(
            _integer(scheduled["tick"], f"{owner}.tick"),
            _integer(scheduled["source_order"], f"{owner}.source_order"),
            payload, _provenance_from(scheduled["provenance"], f"{owner}.provenance"),
        ))
    raw_loop = item["loop"]
    loop = None
    if raw_loop is not None:
        if not isinstance(raw_loop, list) or len(raw_loop) != 2:
            raise SequenceAuditError("invalid_type", f"{path}.loop", "expected null or two integers")
        loop = tuple(_integer(value, f"{path}.loop[{index}]") for index, value in enumerate(raw_loop))
    diagnostics = item["diagnostics"]
    if not isinstance(diagnostics, list) or not all(isinstance(value, str) for value in diagnostics):
        raise SequenceAuditError("invalid_type", f"{path}.diagnostics", "expected string array")
    try:
        return SequenceIR(
            _integer(item["source_time_scale"], f"{path}.source_time_scale"),
            tuple(parts), tuple(events), _integer(item["end_tick"], f"{path}.end_tick"),
            _provenance_from(item["provenance"], f"{path}.provenance"),
            loop, tuple(diagnostics),
        )
    except ValueError as exc:
        raise SequenceAuditError("invalid_sequence", path, str(exc)) from exc


def _provenance(value: Provenance | None) -> dict[str, object] | None:
    if value is None:
        return None
    return {field.name: getattr(value, field.name) for field in fields(Provenance)}


def canonical_sequence_ir(sequence: SequenceIR) -> dict[str, object]:
    """Return the complete stable semantic/provenance representation of an IR."""
    parts = []
    for part in sequence.parts:
        instrument = {
            field.name: getattr(part.instrument, field.name)
            for field in fields(part.instrument)
        }
        parts.append({
            "part_id": part.part_id, "instrument": instrument,
            "requested_polyphony": part.requested_polyphony,
            "typical_polyphony_q16": part.typical_polyphony_q16,
            "percussion": part.percussion,
            "provenance": _provenance(part.provenance),
        })
    events = []
    for scheduled in sequence.events:
        payload = scheduled.payload
        if isinstance(payload, NoteOnEvent):
            event = {
                "type": "note_on", "part_id": payload.part_id,
                "note_id": payload.note_id, "pitch_q8_8": payload.pitch_q8_8,
                "velocity": payload.velocity,
            }
        elif isinstance(payload, NoteOffEvent):
            event = {
                "type": "note_off", "part_id": payload.part_id,
                "note_id": payload.note_id,
                "release_velocity": payload.release_velocity,
            }
        elif isinstance(payload, ControllerEvent):
            event = {
                "type": "controller", "part_id": payload.part_id,
                "controller": payload.controller, "value_q16": payload.value_q16,
            }
        elif isinstance(payload, MarkerEvent):
            event = {
                "type": "marker", "marker": payload.marker,
                "value": payload.value,
            }
        else:  # pragma: no cover - SequenceIR owns the closed payload union.
            raise TypeError(f"unsupported sequence payload {type(payload)!r}")
        events.append({
            "tick": scheduled.tick, "source_order": scheduled.source_order,
            "event": event, "provenance": _provenance(scheduled.provenance),
        })
    return {
        "source_time_scale": sequence.source_time_scale,
        "end_tick": sequence.end_tick,
        "loop": list(sequence.loop) if sequence.loop is not None else None,
        "provenance": _provenance(sequence.provenance),
        "diagnostics": list(sequence.diagnostics),
        "parts": parts, "events": events,
    }


def encode_sequence_audit(
    imported: SequenceIR,
    normalized: SequenceIR,
    timing: TimeScaleNormalization,
    *,
    realization: Sequence[Mapping[str, object]],
) -> bytes:
    """Encode one importer→normalizer→realizer transaction deterministically."""
    if timing.sequence != normalized:
        raise ValueError("timing evidence does not own the normalized sequence")
    document = {
        "schema": "same_music_sequence_audit_v1",
        "imported": canonical_sequence_ir(imported),
        "normalized": canonical_sequence_ir(normalized),
        "timing": {
            "policy": timing.policy.value,
            "source_time_scale": timing.source_time_scale,
            "target_time_scale": timing.target_time_scale,
            "max_error_numerator": timing.max_error_numerator,
            "error_denominator": timing.error_denominator,
            "duration_error_numerator": timing.duration_error_numerator,
        },
        "realization": [dict(item) for item in realization],
    }
    return (json.dumps(
        document, indent=2, sort_keys=True, ensure_ascii=False,
    ) + "\n").encode("utf-8")


def decode_sequence_audit(raw: bytes) -> SequenceAudit:
    """Decode and semantically re-prove one canonical sequencer transaction."""
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SequenceAuditError("invalid_json", "root", str(exc)) from exc
    document = _object(decoded, "root", {
        "schema", "imported", "normalized", "timing", "realization",
    })
    if document["schema"] != "same_music_sequence_audit_v1":
        raise SequenceAuditError("unsupported_schema", "root.schema", repr(document["schema"]))
    try:
        imported = decode_canonical_sequence_ir(document["imported"], path="root.imported")
        normalized = decode_canonical_sequence_ir(document["normalized"], path="root.normalized")
    except SequenceAuditError:
        raise
    except (TypeError, ValueError) as exc:
        raise SequenceAuditError("invalid_sequence", "root", str(exc)) from exc
    timing_item = _object(document["timing"], "root.timing", {
        "policy", "source_time_scale", "target_time_scale",
        "max_error_numerator", "error_denominator", "duration_error_numerator",
    })
    policy_value = timing_item["policy"]
    if not isinstance(policy_value, str):
        raise SequenceAuditError("invalid_type", "root.timing.policy", "expected string")
    try:
        observed = normalize_sequence_time_scale(
            imported,
            _integer(timing_item["target_time_scale"], "root.timing.target_time_scale"),
            policy=TimeScalePolicy(policy_value),
        )
    except (ValueError, KeyError) as exc:
        raise SequenceAuditError("invalid_timing", "root.timing", str(exc)) from exc
    recorded = (
        _integer(timing_item["source_time_scale"], "root.timing.source_time_scale"),
        _integer(timing_item["max_error_numerator"], "root.timing.max_error_numerator"),
        _integer(timing_item["error_denominator"], "root.timing.error_denominator"),
        _integer(timing_item["duration_error_numerator"], "root.timing.duration_error_numerator"),
    )
    expected = (
        observed.source_time_scale, observed.max_error_numerator,
        observed.error_denominator, observed.duration_error_numerator,
    )
    if recorded != expected or normalized != observed.sequence:
        raise SequenceAuditError(
            "timing_mismatch", "root.timing",
            "recorded normalized IR or rational evidence differs from recomputation",
        )
    raw_realization = document["realization"]
    if not isinstance(raw_realization, list):
        raise SequenceAuditError("invalid_type", "root.realization", "expected array")
    realization = []
    for index, raw_note in enumerate(raw_realization):
        owner = f"root.realization[{index}]"
        note = _object(raw_note, owner, {
            "start", "end", "midi_note", "volume", "zone_name", "part_id",
            "note_id", "volume_changes",
        })
        if not isinstance(note["zone_name"], str):
            raise SequenceAuditError("invalid_type", f"{owner}.zone_name", "expected string")
        changes = note["volume_changes"]
        if not isinstance(changes, list):
            raise SequenceAuditError("invalid_type", f"{owner}.volume_changes", "expected array")
        decoded_changes = []
        for change_index, change in enumerate(changes):
            if not isinstance(change, list) or len(change) != 2:
                raise SequenceAuditError("invalid_type", f"{owner}.volume_changes[{change_index}]", "expected integer pair")
            decoded_changes.append(tuple(
                _integer(value, f"{owner}.volume_changes[{change_index}][{value_index}]")
                for value_index, value in enumerate(change)
            ))
        try:
            realization.append(SampledNote(
                *(_integer(note[name], f"{owner}.{name}") for name in ("start", "end", "midi_note", "volume")),
                note["zone_name"],
                *(_integer(note[name], f"{owner}.{name}") for name in ("part_id", "note_id")),
                tuple(decoded_changes),
            ))
        except ValueError as exc:
            raise SequenceAuditError("invalid_realization", owner, str(exc)) from exc
    return SequenceAudit(imported, normalized, observed, tuple(realization))
