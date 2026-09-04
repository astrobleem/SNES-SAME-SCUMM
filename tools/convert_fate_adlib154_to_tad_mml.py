#!/usr/bin/env python3
"""Flatten Fate sound 154's canonical ADL/iMUSE path into zoned TAD MML."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from extract_fate_adlib_patches import load_resource
from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedSound
from same.music import (
    InstrumentBank, SequenceIR, realize_scumm_adlib_notes,
)
from same.music.devices import (
    AdlibPatch, ScummV5AdlibDevice, extract_scumm_adlib_patches,
)
from same.music.importers import ScummImuseTimeline, import_scumm_adlib_sequence


TICKS_PER_SECOND = 125
CHANNEL_NAMES = "ABCDEFGH"
NOTE_NAMES = ("c", "c+", "d", "d+", "e", "f", "f+", "g", "g+", "a", "a+", "b")
INSTRUMENTS = (
    "fate154_ch1_low", "fate154_ch1_high", "fate154_ch2_mid",
    "fate154_ch4_mid", "fate154_ch5_high", "fate154_ch6_low",
    "fate154_ch6_high",
)
JUMP_SOURCE_US = 2_857_140
JUMP_DESTINATION_US = 148_806
JUMP_SOURCE_TICK = 1_920
ROOT = Path(__file__).resolve().parents[1]
BANK_PATH = ROOT / "audio/fate_s6/samples/fate154_adlib_manifest.json"


@dataclass(frozen=True)
class Note:
    start: int
    end: int
    midi_note: int
    volume: int
    instrument: int
    source_channel: int
    volume_changes: tuple[tuple[int, int], ...]


def instrument_for(channel: int, note: int) -> int:
    if channel == 1:
        return 0 if note < 48 else 1
    if channel == 2:
        return 2
    if channel == 4:
        return 3
    if channel == 5:
        return 4
    if channel == 6:
        return 5 if note < 48 else 6
    raise ValueError(f"sound 154 has an unreviewed melodic channel {channel}")


def tad_volume(velocity: int, cc7: int, patch: bytes) -> int:
    """Compatibility wrapper around SAME's reusable SCUMM AdLib device."""
    return ScummV5AdlibDevice().backend_volume(AdlibPatch(patch), velocity, cc7)


def adlib_patches(sound: ScummV5EmbeddedSound) -> dict[int, AdlibPatch]:
    return extract_scumm_adlib_patches(sound)


def load_instrument_bank() -> InstrumentBank:
    bank = InstrumentBank.decode(BANK_PATH.read_bytes(), str(BANK_PATH))
    if bank.source_device != ScummV5AdlibDevice.identifier:
        raise ValueError(f"sound 154 bank targets unsupported device {bank.source_device!r}")
    if tuple(zone.name for zone in bank.zones) != INSTRUMENTS:
        raise ValueError("sound 154 bank zone order differs from compiled TAD instruments")
    return bank


def canonical_sequence(
    sound: ScummV5EmbeddedSound,
    patches: dict[int, AdlibPatch],
) -> SequenceIR:
    """Normalize sound 154's taken iMUSE path into shared SAME music IR."""
    return import_scumm_adlib_sequence(
        sound, patches,
        timeline=ScummImuseTimeline(
            time_scale=TICKS_PER_SECOND,
            source_tick_start=JUMP_SOURCE_TICK,
            source_origin_us=JUMP_SOURCE_US,
            destination_origin_us=JUMP_DESTINATION_US,
            minimum_note_ticks=2,
            allow_initial_note_cleanup=True,
        ),
    )


def collect(
    sound: ScummV5EmbeddedSound,
    patches: dict[int, bytes | AdlibPatch] | None = None,
    bank: InstrumentBank | None = None,
) -> list[Note]:
    patches = adlib_patches(sound) if patches is None else patches
    normalized_patches = {
        channel: patch if isinstance(patch, AdlibPatch) else AdlibPatch(patch)
        for channel, patch in patches.items()
    }
    bank = load_instrument_bank() if bank is None else bank
    sequence = canonical_sequence(sound, normalized_patches)
    resolved = realize_scumm_adlib_notes(sequence, normalized_patches, bank)
    notes = []
    for item in resolved:
        instrument = INSTRUMENTS.index(item.zone_name)
        if instrument != instrument_for(item.part_id, item.midi_note):
            raise ValueError(
                f"sound 154 channel {item.part_id} pitch {item.midi_note} "
                f"resolved to unexpected {item.zone_name}"
            )
        notes.append(Note(
            item.start, item.end, item.midi_note, item.volume, instrument,
            item.part_id, item.volume_changes,
        ))
    return notes


def allocate(notes: list[Note]) -> list[list[Note]]:
    voices: list[list[Note]] = []
    for note in notes:
        lane = next((voice for voice in voices if voice[-1].end <= note.start), None)
        if lane is None:
            if len(voices) >= 8:
                raise ValueError("canonical sound 154 exceeds eight S-DSP voices")
            lane = []
            voices.append(lane)
        lane.append(note)
    return voices


def note_token(note: int) -> tuple[int, str]:
    return note // 12 - 1, NOTE_NAMES[note % 12]


def render(sound: ScummV5EmbeddedSound) -> str:
    bank = load_instrument_bank()
    patches = adlib_patches(sound)
    # Resolve every zone by commercial-data-independent patch fingerprint before
    # compiling. A new title can reuse an accepted zone without cue-specific bytes.
    notes = collect(sound, patches, bank)
    voices = allocate(notes)
    final_tick = round(
        (sound.duration_us - JUMP_SOURCE_US + JUMP_DESTINATION_US)
        * TICKS_PER_SECOND / 1_000_000
    )
    lines = [
        "#Title Fate demo sound 154 canonical AdLib arrangement",
        "#Game Indiana Jones and the Fate of Atlantis interactive demo",
        "#Author SAME isolated Nuked-OPL zone conversion", "#Timer 64", "#ZenLen 192", "",
        "; Canonical ADL path: unconditional $30 jump at 148806 us to beat 5.",
        "; All 26 post-jump attacks and the five active $10 timbres are retained.",
    ]
    lines.extend(f"@{index} {name}" for index, name in enumerate(INSTRUMENTS))
    lines.append("")
    for lane_index, voice in enumerate(voices):
        cursor = 0
        current_instrument = current_volume = current_octave = None
        tokens = ["q0"]
        for note in voice:
            if note.start > cursor:
                tokens.append(f"r%{note.start - cursor}")
            if note.instrument != current_instrument:
                tokens.append(f"@{note.instrument}")
                current_instrument = note.instrument
            if note.volume != current_volume:
                tokens.append(f"V{note.volume}")
                current_volume = note.volume
            octave, pitch = note_token(note.midi_note)
            if octave != current_octave:
                tokens.append(f"o{octave}")
                current_octave = octave
            if note.volume_changes:
                first_tick = note.volume_changes[0][0]
                tokens.extend((f"{pitch}%{first_tick - note.start}", "&"))
                for index, (tick, volume) in enumerate(note.volume_changes):
                    next_tick = note.volume_changes[index + 1][0] if index + 1 < len(note.volume_changes) else note.end
                    tokens.extend((f"V{volume}", f"w%{next_tick - tick}"))
                    current_volume = volume
            else:
                tokens.append(f"{pitch}%{note.end - note.start}")
            cursor = note.end
        if cursor < final_tick:
            tokens.append(f"r%{final_tick - cursor}")
        lines.append(f"{CHANNEL_NAMES[lane_index]} " + " ".join(tokens))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sound = ScummV5EmbeddedSound.decode(
        load_resource(args.archive.resolve(), 154), "sound.154",
        rendition_order=(b"ADL ",),
    )
    text = render(sound)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    notes = collect(sound)
    print(f"{args.output}: {len(notes)} attacks, {len(allocate(notes))} voices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
