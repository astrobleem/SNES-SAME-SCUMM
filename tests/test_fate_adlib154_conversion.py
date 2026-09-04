from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from convert_fate_adlib154_to_tad_mml import (
    JUMP_DESTINATION_US, Note, allocate, canonical_sequence, collect,
    instrument_for, tad_volume,
)
from build_fate_adlib_samples import add_phase_correct_attack
from same.music import (
    ControllerEvent, InstrumentBank, InstrumentZone, MarkerEvent, NoteOffEvent,
    NoteOnEvent,
)
from same.music.devices import AdlibPatch


def event(tick, time_us, status, *data):
    return SimpleNamespace(tick=tick, time_us=time_us, status=status, data=data)


class FateAdlib154ConversionTests(unittest.TestCase):
    @staticmethod
    def velocity_insensitive_patch() -> bytes:
        patch = bytearray(30)
        patch[1] = 11
        patch[6] = 63
        patch[10] = 8  # FM: only the carrier controls output level.
        return bytes(patch)

    @staticmethod
    def bank_for(patch: bytes) -> InstrumentBank:
        fingerprint = AdlibPatch(patch).fingerprint
        return InstrumentBank(
            "sound-154-test", "scumm_v5_adlib", 100, 127, 96,
            (InstrumentZone(
                "fate154_ch2_mid", fingerprint, "fixture.wav", "0" * 64,
                60, 48, 71, 0, 16, "accepted",
            ),),
        )

    def test_jump_target_rounding_keeps_first_attacks_and_ignores_skipped_cleanup(self) -> None:
        sound = SimpleNamespace(tracks=(SimpleNamespace(events=(
            # Cleanup for a note that existed only on the skipped linear path.
            event(1920, 2_857_136, 0x81, 48, 64),
            event(1920, 2_857_136, 0xB2, 7, 100),
            event(1920, 2_857_136, 0x92, 60, 64),
            event(2016, 3_000_000, 0xB2, 7, 50),
            event(2256, 3_357_140, 0x82, 60, 64),
        )),))
        patch = self.velocity_insensitive_patch()
        notes = collect(sound, {2: patch}, self.bank_for(patch))
        self.assertEqual(len(notes), 1)
        note = notes[0]
        self.assertEqual(note.start, round(JUMP_DESTINATION_US * 125 / 1_000_000))
        self.assertEqual(note.instrument, 2)
        self.assertEqual(note.volume, tad_volume(64, 100, patch))
        changed_tick = round((3_000_000 - 2_857_140 + JUMP_DESTINATION_US) * 125 / 1_000_000)
        self.assertEqual(
            note.volume_changes,
            ((changed_tick, tad_volume(64, 50, patch)),),
        )

        sequence = canonical_sequence(sound, {2: AdlibPatch(patch)})
        self.assertEqual(sequence.peak_polyphony(), 1)
        self.assertEqual([part.part_id for part in sequence.parts], [2])
        self.assertEqual(
            [type(item.payload) for item in sequence.events],
            [ControllerEvent, NoteOnEvent, ControllerEvent, NoteOffEvent,
             MarkerEvent],
        )

    def test_zero_sensitivity_preserves_quiet_velocity_fanfare(self) -> None:
        patch = self.velocity_insensitive_patch()
        self.assertEqual(tad_volume(1, 47, patch), 14)
        self.assertEqual(tad_volume(127, 47, patch), 14)
        self.assertGreater(tad_volume(1, 47, patch), 1)

    def test_channel_and_octave_zones_are_explicit(self) -> None:
        self.assertEqual(instrument_for(1, 36), 0)
        self.assertEqual(instrument_for(1, 62), 1)
        self.assertEqual(instrument_for(6, 43), 5)
        self.assertEqual(instrument_for(6, 65), 6)
        with self.assertRaisesRegex(ValueError, "unreviewed melodic channel"):
            instrument_for(9, 60)

    def test_ninth_simultaneous_note_fails_closed(self) -> None:
        notes = [Note(0, 10, 60 + i, 100, 2, 2, ()) for i in range(9)]
        with self.assertRaisesRegex(ValueError, "exceeds eight"):
            allocate(notes)

    def test_phase_correct_attack_is_aligned_and_preserves_loop(self) -> None:
        loop = [index - 256 for index in range(512)]
        source = add_phase_correct_attack(loop, 256)
        self.assertEqual(len(source), 768)
        self.assertEqual(source[256:], loop)
        self.assertEqual(source[0], 0)
        self.assertEqual(source[255], 255)


if __name__ == "__main__":
    unittest.main()
