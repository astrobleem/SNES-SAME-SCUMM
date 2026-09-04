"""Strict big-endian QuickTime Music Architecture event importer."""

from __future__ import annotations

from dataclasses import dataclass

from ..model import (
    ControllerEvent, InstrumentRequest, MarkerEvent, NoteOffEvent, NoteOnEvent,
    PartSpec, Provenance, ScheduledEvent, SequenceIR,
)
from ..segmented import SegmentedByteSource, SegmentedSourceError


class QtmaDecodeError(ValueError):
    def __init__(self, code: str, source: str, word_offset: int, detail: str) -> None:
        self.code = code
        self.source = source
        self.word_offset = word_offset
        self.byte_offset = word_offset * 4
        super().__init__(
            f"QTMA {source!r} {code} at word {word_offset} "
            f"(byte {self.byte_offset}): {detail}"
        )


def _pascal(raw: bytes, source: str, word_offset: int, name: str) -> str:
    length = raw[0]
    if length > len(raw) - 1:
        raise QtmaDecodeError(
            "invalid_note_request", source, word_offset,
            f"{name} Pascal string length {length} exceeds {len(raw) - 1}",
        )
    return raw[1 : 1 + length].decode("mac_roman")


def _note_request(
    payload: bytes, part_id: int, source: str, word_offset: int,
    provenance: Provenance,
) -> PartSpec:
    if len(payload) != 84:
        raise QtmaDecodeError(
            "invalid_note_request", source, word_offset,
            f"NoteRequest payload must be 84 bytes, got {len(payload)}",
        )
    flags = payload[0]
    midi_assignment = payload[1]
    polyphony = int.from_bytes(payload[2:4], "big")
    typical = int.from_bytes(payload[4:8], "big", signed=True)
    synth_type = payload[8:12].decode("mac_roman").rstrip("\0")
    synth_name = _pascal(payload[12:44], source, word_offset, "synthesizer name")
    instrument_name = _pascal(payload[44:76], source, word_offset, "instrument name")
    instrument_number = int.from_bytes(payload[76:80], "big", signed=True)
    gm_number = int.from_bytes(payload[80:84], "big", signed=True)
    if flags & ~0x07:
        raise QtmaDecodeError(
            "unsupported_required_feature", source, word_offset,
            f"NoteRequest flags {flags:#04x} are unsupported",
        )
    if midi_assignment and not (0x81 <= midi_assignment <= 0x90):
        raise QtmaDecodeError(
            "invalid_note_request", source, word_offset,
            f"MIDI assignment {midi_assignment:#04x} is invalid",
        )
    if polyphony < 1 or typical < 0:
        raise QtmaDecodeError(
            "invalid_note_request", source, word_offset,
            "polyphony must be positive and typical polyphony nonnegative",
        )
    percussion = 0x4001 <= gm_number <= 0x4080
    if 1 <= gm_number <= 128:
        gm_fallback = gm_number - 1
    elif percussion:
        gm_fallback = gm_number - 0x4001
    else:
        gm_fallback = None
    try:
        request = InstrumentRequest(
            synth_type=synth_type or None,
            synth_name=synth_name or None,
            instrument_name=instrument_name or None,
            instrument_number=instrument_number if instrument_number else None,
            gm_fallback=gm_fallback,
        )
    except ValueError as exc:
        raise QtmaDecodeError(
            "invalid_note_request", source, word_offset, str(exc),
        ) from exc
    return PartSpec(
        part_id, request, requested_polyphony=polyphony,
        typical_polyphony_q16=typical, percussion=percussion,
        provenance=provenance,
    )


def decode_qtma_events(
    raw: bytes | SegmentedByteSource,
    *,
    source: str = "qtma-events",
    time_scale: int = 600,
    track: int | None = None,
    sample: int | None = None,
) -> SequenceIR:
    """Decode the strict first-slice QTMA event families into ``SequenceIR``."""
    segmented = raw if isinstance(raw, SegmentedByteSource) else None
    data = segmented.data if segmented is not None else raw
    error_source = segmented.provenance.source if segmented is not None else source
    source = error_source
    if len(data) % 4:
        raise QtmaDecodeError(
            "truncated_event", error_source, len(data) // 4,
            f"event buffer has {len(data) % 4} trailing bytes",
        )
    words = tuple(
        int.from_bytes(data[offset : offset + 4], "big")
        for offset in range(0, len(data), 4)
    )
    parts: dict[int, PartSpec] = {}
    events: list[ScheduledEvent] = []
    cursor = 0
    note_id = 0
    offset = 0
    end_seen = False

    def provenance(word_offset: int, word_length: int) -> Provenance:
        if segmented is not None:
            try:
                return segmented.resolve(
                    word_offset * 4, word_length * 4,
                    word_offset=word_offset,
                )
            except SegmentedSourceError as exc:
                raise QtmaDecodeError(
                    exc.code, error_source, word_offset, str(exc),
                ) from exc
        return Provenance(
            source, track=track, sample=sample,
            byte_offset=word_offset * 4, word_offset=word_offset,
        )

    while offset < len(words):
        head = words[offset]
        length_code = head >> 30
        if length_code < 2:
            event_type = (head >> 29) & 0x7
            event_length = 1
        elif length_code == 2:
            event_type = (head >> 28) & 0xF
            event_length = 2
        else:
            event_type = (head >> 28) & 0xF
            event_length = head & 0xFFFF
            if event_length < 2:
                raise QtmaDecodeError(
                    "invalid_general_length", source, offset,
                    f"general length {event_length} is below two words",
                )
        if offset + event_length > len(words):
            raise QtmaDecodeError(
                "truncated_event", source, offset,
                f"{event_length}-word event exceeds {len(words) - offset} remaining words",
            )
        order = offset * 2
        prov = provenance(offset, event_length)
        if event_type == 0:
            cursor += head & 0xFFFFFF
        elif event_type == 1:
            part_id = (head >> 24) & 0x1F
            if part_id not in parts:
                raise QtmaDecodeError(
                    "unknown_part", source, offset,
                    f"note references undeclared part {part_id}",
                )
            pitch = ((head >> 18) & 0x3F) + 32
            velocity = (head >> 11) & 0x7F
            duration = head & 0x7FF
            if duration == 0:
                raise QtmaDecodeError(
                    "unsupported_required_feature", source, offset,
                    "zero-duration standard notes have no first-slice policy",
                )
            if velocity:
                events.extend((
                    ScheduledEvent(
                        cursor, order,
                        NoteOnEvent(part_id, note_id, pitch << 8, velocity), prov,
                    ),
                    ScheduledEvent(
                        cursor + duration, order + 1,
                        NoteOffEvent(part_id, note_id), prov,
                    ),
                ))
                note_id += 1
        elif event_type == 2:
            part_id = (head >> 24) & 0x1F
            if part_id not in parts:
                raise QtmaDecodeError(
                    "unknown_part", source, offset,
                    f"controller references undeclared part {part_id}",
                )
            controller = (head >> 16) & 0xFF
            signed_q8_8 = int.from_bytes((head & 0xFFFF).to_bytes(2, "big"), "big", signed=True)
            events.append(ScheduledEvent(
                cursor, order,
                ControllerEvent(part_id, controller, signed_q8_8 << 8), prov,
            ))
        elif event_type == 3:
            subtype = (head >> 16) & 0xFF
            value = head & 0xFFFF
            if subtype == 0 and value == 0:
                events.append(ScheduledEvent(
                    cursor, order, MarkerEvent("end"), prov,
                ))
                end_seen = True
            else:
                marker = {0: "end_ignored", 1: "beat", 2: "tempo"}.get(
                    subtype, f"qtma_marker_{subtype}"
                )
                events.append(ScheduledEvent(cursor, order, MarkerEvent(marker, value), prov))
        elif event_type == 15:
            tail = words[offset + event_length - 1]
            tail_length = tail & 0xFFFF
            subtype = (tail >> 16) & 0x3FFF
            part_id = (head >> 16) & 0xFFF
            if tail >> 30 != 3 or tail_length != event_length:
                raise QtmaDecodeError(
                    "mismatched_general_tail", source, offset,
                    f"head length {event_length} and tail {tail_length} disagree",
                )
            if subtype != 1:
                raise QtmaDecodeError(
                    "unsupported_required_feature", source, offset,
                    f"general subtype {subtype} is not supported",
                )
            if part_id in parts:
                raise QtmaDecodeError(
                    "invalid_note_request", source, offset,
                    f"part {part_id} has more than one NoteRequest",
                )
            payload = data[(offset + 1) * 4 : (offset + event_length - 1) * 4]
            parts[part_id] = _note_request(
                payload, part_id, error_source, offset, prov,
            )
        else:
            raise QtmaDecodeError(
                "unsupported_required_feature", source, offset,
                f"event type {event_type} is not supported",
            )
        offset += event_length
        if end_seen:
            if offset != len(words):
                raise QtmaDecodeError(
                    "trailing_event", source, offset,
                    f"{len(words) - offset} words follow the End marker",
                )
            break
    if not end_seen:
        raise QtmaDecodeError(
            "missing_end", source, len(words), "event buffer has no End marker",
        )
    ordered = tuple(sorted(events, key=lambda item: (item.tick, item.source_order)))
    end_tick = max((event.tick for event in ordered), default=cursor)
    sequence_source = (
        segmented.provenance if segmented is not None
        else Provenance(source, track=track, sample=sample)
    )
    return SequenceIR(
        source_time_scale=time_scale,
        parts=tuple(parts[key] for key in sorted(parts)),
        events=ordered,
        end_tick=end_tick,
        provenance=sequence_source,
    )
