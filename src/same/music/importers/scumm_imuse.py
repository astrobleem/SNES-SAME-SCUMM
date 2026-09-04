"""Normalize one linear SCUMM iMUSE AdLib path into canonical music IR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from ..devices import AdlibPatch
from ..model import (
    ControllerEvent, InstrumentRequest, MarkerEvent, NoteOffEvent, NoteOnEvent,
    PartSpec, Provenance, ScheduledEvent, SequenceIR,
)


class ScummImuseImportError(ValueError):
    def __init__(self, source: str, event_index: int | None, detail: str) -> None:
        self.source = source
        self.event_index = event_index
        location = "end of track" if event_index is None else f"source event {event_index}"
        super().__init__(f"SCUMM iMUSE {source!r} {location}: {detail}")


@dataclass(frozen=True, slots=True)
class ScummImuseTimeline:
    """Explicitly select and rebase a linear path through an iMUSE track."""

    time_scale: int = 125
    source_tick_start: int = 0
    source_origin_us: int = 0
    destination_origin_us: int = 0
    minimum_note_ticks: int = 1
    allow_initial_note_cleanup: bool = False
    loop_source_ticks: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if self.time_scale <= 0:
            raise ValueError("SCUMM iMUSE time scale must be positive")
        if self.source_tick_start < 0 or self.source_origin_us < 0:
            raise ValueError("SCUMM iMUSE source origins cannot be negative")
        if self.destination_origin_us < 0 or self.minimum_note_ticks < 1:
            raise ValueError("SCUMM iMUSE destination timing is invalid")
        if self.loop_source_ticks is not None:
            start, end = self.loop_source_ticks
            if not self.source_tick_start <= start < end:
                raise ValueError("SCUMM iMUSE source loop is invalid")

    def tick(self, time_us: int) -> int:
        return max(0, round(
            (int(time_us) - self.source_origin_us + self.destination_origin_us)
            * self.time_scale / 1_000_000
        ))


def import_scumm_adlib_sequence(
    sound: object,
    patches: Mapping[int, AdlibPatch],
    *,
    timeline: ScummImuseTimeline | None = None,
) -> SequenceIR:
    """Import a selected single-track path without any cue-number policy."""
    timeline = timeline or ScummImuseTimeline()
    tracks = tuple(getattr(sound, "tracks", ()))
    if len(tracks) != 1:
        raise ValueError("SCUMM iMUSE importer requires one selected linear track")
    source_name = str(getattr(sound, "key", "scumm-imuse"))
    source = Provenance(source_name, track=0)
    polyphony = {int(channel): 0 for channel in patches}
    active_counts = {int(channel): 0 for channel in patches}
    for event in tracks[0].events:
        if int(event.tick) < timeline.source_tick_start:
            continue
        command, channel = int(event.status) & 0xF0, int(event.status) & 0x0F
        if channel not in patches:
            continue
        if command == 0x90 and len(event.data) > 1 and int(event.data[1]):
            active_counts[channel] += 1
            polyphony[channel] = max(polyphony[channel], active_counts[channel])
        elif command == 0x80 or (
            command == 0x90 and len(event.data) > 1 and not int(event.data[1])
        ):
            active_counts[channel] = max(0, active_counts[channel] - 1)
    parts = tuple(
        PartSpec(
            int(channel),
            InstrumentRequest(
                portable_id=f"adlib-sha256:{patch.fingerprint}",
                synth_type="OPL2",
                patch_fingerprint=patch.fingerprint,
            ),
            requested_polyphony=max(1, polyphony[int(channel)]),
        )
        for channel, patch in sorted(patches.items())
    )
    events: list[ScheduledEvent] = []
    active: dict[tuple[int, int], list[tuple[int, int]]] = {}
    note_id = 0
    source_order = 0
    for event_index, event in enumerate(tracks[0].events):
        if int(event.tick) < timeline.source_tick_start:
            continue
        command, channel = int(event.status) & 0xF0, int(event.status) & 0x0F
        provenance = Provenance(source_name, track=0, sample=event_index)
        is_note_off = command == 0x80 or (
            command == 0x90 and len(event.data) > 1 and not int(event.data[1])
        )
        if (
            is_note_off
            and channel not in patches
            and timeline.allow_initial_note_cleanup
            and int(event.tick) == timeline.source_tick_start
        ):
            # A selected branch may begin with cleanup for a voice started on
            # the discarded path.  Keep the exception at the exact boundary;
            # later traffic on an unpatched channel remains an import error.
            continue
        if command in (0x80, 0x90, 0xB0, 0xD0, 0xE0) and channel not in patches:
            raise ScummImuseImportError(
                source_name, event_index, f"channel {channel} has no AdLib patch",
            )
        if command == 0xB0 and int(event.data[0]) in (7, 10) and channel in patches:
            events.append(ScheduledEvent(
                timeline.tick(event.time_us), source_order,
                ControllerEvent(
                    channel, int(event.data[0]), int(event.data[1]) << 16,
                ),
                provenance,
            ))
            source_order += 1
        elif command == 0x90 and int(event.data[1]) and channel in patches:
            start = timeline.tick(max(int(event.time_us), timeline.source_origin_us))
            active.setdefault((channel, int(event.data[0])), []).append((note_id, start))
            events.append(ScheduledEvent(
                start, source_order,
                NoteOnEvent(
                    channel, note_id, int(event.data[0]) << 8, int(event.data[1]),
                ),
                provenance,
            ))
            note_id += 1
            source_order += 1
        elif command in (0x80, 0x90) and channel in patches:
            stack = active.get((channel, int(event.data[0])))
            if not stack:
                if (
                    timeline.allow_initial_note_cleanup
                    and int(event.tick) == timeline.source_tick_start
                ):
                    continue
                raise ScummImuseImportError(
                    source_name, event_index, "note-off has no matching note-on",
                )
            stopped_id, start = stack.pop(0)
            events.append(ScheduledEvent(
                max(start + timeline.minimum_note_ticks, timeline.tick(event.time_us)),
                source_order,
                NoteOffEvent(channel, stopped_id, int(event.data[1])), provenance,
            ))
            source_order += 1
        elif command == 0xB0:
            raise ScummImuseImportError(
                source_name, event_index,
                f"controller {int(event.data[0])} is unsupported",
            )
        elif command in (0xA0, 0xD0, 0xE0):
            raise ScummImuseImportError(
                source_name, event_index,
                f"MIDI command {command:#04x} is unsupported",
            )
        elif command not in (0xC0, 0xF0):
            raise ScummImuseImportError(
                source_name, event_index,
                f"event status {int(event.status):#04x} is unsupported",
            )
    if any(active.values()):
        raise ScummImuseImportError(
            source_name, None, "selected path has unterminated notes",
        )
    duration_us = max(int(getattr(sound, "duration_us", 0)), timeline.source_origin_us)
    final_tick = max(
        [event.tick for event in events] + [timeline.tick(duration_us)],
    )
    events.append(ScheduledEvent(
        final_tick, source_order, MarkerEvent("end"), source,
    ))
    loop = None
    if timeline.loop_source_ticks is not None:
        start, end = timeline.loop_source_ticks
        track = tracks[0]
        division = int(getattr(sound, "division", 0))
        if not division or not hasattr(track, "time_at_tick"):
            raise ValueError("SCUMM iMUSE source loop requires a timed MIDI track")
        if end > int(getattr(track, "duration_ticks", -1)):
            raise ValueError("SCUMM iMUSE source loop exceeds the selected track")
        loop = (
            timeline.tick(track.time_at_tick(start, division)),
            timeline.tick(track.time_at_tick(end, division)),
        )
    return SequenceIR(
        source_time_scale=timeline.time_scale,
        parts=parts,
        events=tuple(sorted(events, key=lambda item: (item.tick, item.source_order))),
        end_tick=final_tick,
        provenance=source,
        loop=loop,
    )
