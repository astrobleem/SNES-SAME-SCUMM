from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from convert_fate_sound_to_tad_mml import (
    allocate_voices, collect_notes, quantize_notes, reduce_polyphony, render_mml,
    virtualize_polyphony,
)


def event(tick, time_us, status, *data):
    return SimpleNamespace(tick=tick, time_us=time_us, status=status, data=data)


class FateTadConversionTests(unittest.TestCase):
    def test_active_note_cc7_is_preserved_without_retrigger(self) -> None:
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=(
                event(0, 0, 0xC0, 50),
                event(0, 0, 0x90, 60, 127),
                event(96, 100_000, 0xB0, 7, 64),
                event(192, 200_000, 0xB0, 7, 0),
                event(288, 300_000, 0x80, 60, 64),
                # Controller movement after key-off must not attach to the note.
                event(289, 301_000, 0xB0, 7, 127),
            )),),
        )
        source = collect_notes(sound)
        self.assertEqual(
            source[0].volume_changes,
            ((100_000, 64), (200_000, 0)),
        )
        quantized = quantize_notes(99, source)
        self.assertEqual(quantized[0].volume, 192)
        self.assertEqual(quantized[0].volume_changes, ((12, 97), (25, 0)))
        mml = render_mml(99, sound)
        self.assertIn("Preserved 2 active-note CC7 fine-volume changes", mml)
        self.assertIn("c%12 & V97 w%13 V0 w%13", mml)

    def test_virtualization_slices_keep_cc7_envelope_and_attack_identity(self) -> None:
        events = []
        for channel, (program, note) in enumerate(((50, 64), (50, 67), (50, 72))):
            events.extend((
                event(0, 0, 0xC0 | channel, program),
                event(0, 0, 0x90 | channel, note, 16),
            ))
        events.append(event(48, 50_000, 0xB2, 7, 64))
        for channel, note in enumerate(range(48, 54), start=3):
            events.extend((
                event(96, 100_000, 0xC0 | channel, 57),
                event(96, 100_000, 0x90 | channel, note, 64),
                event(192, 200_000, 0x80 | channel, note, 64),
            ))
        for channel, note in enumerate((64, 67, 72)):
            events.append(event(288, 300_000, 0x80 | channel, note, 64))
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        arranged, _decisions = virtualize_polyphony(
            18, quantize_notes(18, collect_notes(sound)),
        )
        high_bed = [
            note for note in arranged if note.program == 50 and note.midi_note == 72
        ]
        self.assertEqual([(note.start, note.end) for note in high_bed], [(0, 12), (25, 38)])
        self.assertEqual(high_bed[0].volume_changes, ((6, 12),))
        self.assertFalse(high_bed[1].attack)

    def test_programs_polyphony_and_zone_boundary_are_preserved(self) -> None:
        events = (
            event(0, 0, 0xC0, 50),
            event(0, 0, 0x90, 60, 64),
            event(0, 0, 0x90, 67, 32),
            event(240, 250_000, 0xC1, 57),
            event(240, 250_000, 0x91, 63, 80),
            event(360, 375_000, 0x81, 63, 64),
            event(360, 375_000, 0x91, 64, 80),
            event(480, 500_000, 0x80, 60, 64),
            event(480, 500_000, 0x80, 67, 64),
            event(480, 500_000, 0x81, 64, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=500_000,
            tracks=(SimpleNamespace(events=events),),
        )
        self.assertEqual(len(collect_notes(sound)), 4)
        mml = render_mml(99, sound)
        self.assertIn("@2", mml)  # flute-low through D#4 / MIDI 63
        self.assertIn("@3", mml)  # flute-mid from E4 / MIDI 64
        self.assertIn("A q0", mml)
        self.assertIn("B q0", mml)  # overlapping pad notes require polyphony

    def test_unreviewed_program_fails_closed(self) -> None:
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=(
                event(0, 0, 0xC0, 99),
                event(0, 0, 0x90, 60, 64),
                event(96, 100_000, 0x80, 60, 64),
            )),),
        )
        with self.assertRaisesRegex(ValueError, "no reviewed SNES role"):
            render_mml(99, sound)

    def test_sound_154_bass_program_crosses_to_explicit_pad_band(self) -> None:
        events = (
            event(0, 0, 0xC0, 36),
            event(0, 0, 0x90, 36, 64),
            event(96, 100_000, 0x80, 36, 64),
            event(96, 100_000, 0x90, 60, 8),
            event(192, 200_000, 0x80, 60, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=200_000,
            tracks=(SimpleNamespace(events=events),),
        )
        notes = quantize_notes(154, collect_notes(sound))
        self.assertEqual([note.instrument for note in notes], [5, 0])

    def test_sound_78_uses_zoned_flute_over_two_pad_layers(self) -> None:
        events = (
            event(0, 0, 0xC0, 73), event(0, 0, 0x90, 72, 64),
            event(0, 0, 0x90, 91, 64),
            event(0, 0, 0xC1, 82), event(0, 0, 0x91, 36, 64),
            event(0, 0, 0xC2, 91), event(0, 0, 0x92, 68, 64),
            event(96, 100_000, 0x80, 72, 64), event(96, 100_000, 0x80, 91, 64),
            event(96, 100_000, 0x81, 36, 64), event(96, 100_000, 0x82, 68, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        notes = quantize_notes(78, collect_notes(sound))
        self.assertEqual([note.instrument for note in notes], [0, 0, 3, 4])
        self.assertEqual(len(allocate_voices(notes)), 4)

    def test_sound_78_fails_outside_explicit_program_bands(self) -> None:
        for program, note in ((73, 71), (82, 72), (91, 72)):
            sound = SimpleNamespace(
                track_count=1, duration_us=100_000,
                tracks=(SimpleNamespace(events=(
                    event(0, 0, 0xC0, program), event(0, 0, 0x90, note, 64),
                    event(96, 100_000, 0x80, note, 64),
                )),),
            )
            with self.assertRaisesRegex(ValueError, "no reviewed SNES band"):
                render_mml(78, sound)

    def test_sound_81_merges_only_identical_mapped_pad_pitches(self) -> None:
        events = []
        for channel, (program, note, velocity) in enumerate((
            (92, 67, 1), (90, 67, 64), (0, 38, 64), (32, 47, 64),
            (32, 60, 64), (82, 59, 64), (92, 58, 64), (90, 72, 64),
            (92, 80, 64),
        )):
            events.extend((
                event(0, 0, 0xC0 | channel, program),
                event(0, 0, 0x90 | channel, note, velocity),
                event(96, 100_000, 0x80 | channel, note, 64),
            ))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        arranged, decisions = virtualize_polyphony(
            81, quantize_notes(81, collect_notes(sound)),
        )
        self.assertEqual(len(allocate_voices(arranged)), 8)
        self.assertEqual(
            [(decision.action, decision.program, decision.peer_program) for decision in decisions],
            [("MERGE", 92, 90)],
        )
        self.assertEqual(
            sorted({note.instrument for note in arranged}), [0, 1, 5, 6],
        )

    def test_sound_81_fails_if_distinct_pitches_still_exceed_capacity(self) -> None:
        events = [event(0, 0, 0xC0, 92)]
        events.extend(event(0, 0, 0x90, note, 64) for note in range(60, 69))
        events.extend(event(96, 100_000, 0x80, note, 64) for note in range(60, 69))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        with self.assertRaisesRegex(ValueError, "after identical-pitch merging"):
            virtualize_polyphony(81, quantize_notes(81, collect_notes(sound)))

    def test_sound_153_maps_high_glint_and_preserves_new_attacks(self) -> None:
        events = []
        voices = (
            (0, 46, 8), (32, 59, 8), (32, 60, 8), (50, 24, 8),
            (50, 36, 8), (92, 67, 8), (97, 95, 8), (97, 96, 8),
        )
        for channel, (program, note, velocity) in enumerate(voices):
            events.extend((
                event(0, 0, 0xC0 | channel, program),
                event(0, 0, 0x90 | channel, note, velocity),
            ))
        # A stronger duplicate and three distinct attacks arrive at capacity.
        for channel, note in enumerate((67, 68, 69, 70), start=8):
            events.extend((
                event(96, 100_000, 0xC0 | channel, 92),
                event(96, 100_000, 0x90 | channel, note, 64),
                event(192, 200_000, 0x80 | channel, note, 64),
            ))
        for channel, (_program, note, _velocity) in enumerate(voices):
            events.append(event(288, 300_000, 0x80 | channel, note, 64))
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        quantized = quantize_notes(153, collect_notes(sound))
        self.assertEqual(
            [note.instrument for note in quantized[:8]], [5, 0, 6, 5, 0, 0, 4, 7],
        )
        arranged, decisions = virtualize_polyphony(153, quantized)
        self.assertEqual(len({note.source_index for note in arranged}), 12)
        self.assertLessEqual(len(allocate_voices(arranged)), 8)
        self.assertTrue(any(decision.action == "MERGE" for decision in decisions))
        self.assertTrue(any(decision.action.startswith("DUCK") for decision in decisions))

    def test_sound_153_fails_if_new_attacks_alone_exceed_capacity(self) -> None:
        events = [event(0, 0, 0xC0, 92)]
        events.extend(event(0, 0, 0x90, note, 64) for note in range(60, 69))
        events.extend(event(96, 100_000, 0x80, note, 64) for note in range(60, 69))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        with self.assertRaisesRegex(ValueError, "simultaneous protected attacks"):
            virtualize_polyphony(153, quantize_notes(153, collect_notes(sound)))

    def test_sound_150_maps_marimba_bass_and_split_pad_roles(self) -> None:
        events = (
            event(0, 0, 0xC0, 0), event(0, 0, 0x90, 43, 64),
            event(0, 0, 0xC1, 56), event(0, 0, 0x91, 26, 64),
            event(0, 0, 0xC2, 33), event(0, 0, 0x92, 59, 64),
            event(0, 0, 0x92, 60, 64),
            event(0, 0, 0xC3, 36), event(0, 0, 0x93, 38, 64),
            event(0, 0, 0x93, 60, 64),
            event(0, 0, 0xC4, 92), event(0, 0, 0x94, 69, 64),
            event(96, 100_000, 0x80, 43, 64),
            event(96, 100_000, 0x81, 26, 64),
            event(96, 100_000, 0x82, 59, 64), event(96, 100_000, 0x82, 60, 64),
            event(96, 100_000, 0x83, 38, 64), event(96, 100_000, 0x83, 60, 64),
            event(96, 100_000, 0x84, 69, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        self.assertEqual(
            [note.instrument for note in quantize_notes(150, collect_notes(sound))],
            [5, 5, 6, 5, 0, 0, 0],
        )

    def test_sound_150_terminal_hold_fades_without_shortening_source_timing(self) -> None:
        sound = SimpleNamespace(
            track_count=1, duration_us=95_000_000,
            tracks=(SimpleNamespace(events=(
                event(0, 11_000_000, 0xC0, 92),
                event(0, 11_000_000, 0x90, 60, 64),
                event(12, 12_000_000, 0xB0, 7, 64),
                event(96, 95_000_000, 0x80, 60, 64),
            )),),
        )
        mml = render_mml(150, sound)
        self.assertIn("Terminal interactive hold", mml)
        self.assertIn("c%124 & V49 w%579 Vs-49,256 w%9797", mml)

    def test_sounds_91_and_117_split_bass_from_wide_effect_tone(self) -> None:
        for sound_id, program in ((91, 32), (117, 121)):
            events = (
                event(0, 0, 0xC0, program),
                event(0, 0, 0x90, 40, 64), event(0, 0, 0x90, 48, 64),
                event(0, 0, 0x90, 107, 64),
                event(96, 10_000, 0x80, 40, 64), event(96, 10_000, 0x80, 48, 64),
                event(96, 10_000, 0x80, 107, 64),
            )
            sound = SimpleNamespace(
                track_count=1, duration_us=10_000,
                tracks=(SimpleNamespace(events=events),),
            )
            notes = quantize_notes(sound_id, collect_notes(sound))
            self.assertEqual([note.instrument for note in notes], [5, 7, 7])
            self.assertTrue(all(note.end - note.start >= 2 for note in notes))
            mml = render_mml(sound_id, sound)
            self.assertIn("@7 fate_tone", mml)
            self.assertIn("two-tick minimum key-off quantum", mml)

    def test_wide_effect_cues_fail_outside_explicit_ranges(self) -> None:
        for sound_id, program, note in ((91, 32, 108), (117, 121, 108)):
            sound = SimpleNamespace(
                track_count=1, duration_us=100_000,
                tracks=(SimpleNamespace(events=(
                    event(0, 0, 0xC0, program), event(0, 0, 0x90, note, 64),
                    event(96, 100_000, 0x80, note, 64),
                )),),
            )
            with self.assertRaisesRegex(ValueError, "no reviewed SNES band"):
                render_mml(sound_id, sound)

    def test_sound_specific_program_outside_reviewed_band_fails_closed(self) -> None:
        events = (
            event(0, 0, 0xC0, 32),
            event(0, 0, 0x90, 96, 64),
            event(96, 100_000, 0x80, 96, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        with self.assertRaisesRegex(ValueError, "no reviewed SNES band"):
            render_mml(154, sound)

    def test_sound_83_reduction_omits_quietest_highest_tie(self) -> None:
        events = [event(0, 0, 0xC0, 92)]
        for note in range(48, 57):
            velocity = 1 if note in (48, 56) else 8
            events.append(event(0, 0, 0x90, note, velocity))
        for note in range(48, 57):
            events.append(event(96, 100_000, 0x80, note, 64))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        retained, omitted = reduce_polyphony(83, quantize_notes(83, collect_notes(sound)))
        self.assertEqual([note.midi_note for note in omitted], [56])
        self.assertEqual(len(retained), 8)
        self.assertEqual(len(allocate_voices(retained)), 8)
        mml = render_mml(83, sound)
        self.assertIn("OMIT program 92 MIDI 56", mml)

    def test_sound_18_ducks_and_restores_background_bed(self) -> None:
        events = []
        for channel, (program, note) in enumerate(((50, 64), (50, 67), (50, 72))):
            events.extend((event(0, 0, 0xC0 | channel, program), event(0, 0, 0x90 | channel, note, 16)))
        for channel, note in enumerate(range(48, 54), start=3):
            events.extend((
                event(96, 100_000, 0xC0 | channel, 57),
                event(96, 100_000, 0x90 | channel, note, 64),
                event(192, 200_000, 0x80 | channel, note, 64),
            ))
        for channel, note in enumerate((64, 67, 72)):
            events.append(event(288, 300_000, 0x80 | channel, note, 64))
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        arranged, decisions = virtualize_polyphony(
            18, quantize_notes(18, collect_notes(sound)),
        )
        self.assertLessEqual(len(allocate_voices(arranged)), 8)
        self.assertEqual(
            [(decision.action, decision.program, decision.midi_note) for decision in decisions],
            [("DUCK", 50, 72)],
        )
        high_bed = [note for note in arranged if note.program == 50 and note.midi_note == 72]
        self.assertEqual([(note.start, note.end) for note in high_bed], [(0, 12), (25, 38)])
        mml = render_mml(18, sound)
        self.assertIn("DUCK program 50 MIDI 72 at 0.096s for 0.104s", mml)

    def test_sound_18_merges_identical_pad_pitch_into_foreground(self) -> None:
        events = (
            event(0, 0, 0xC0, 50), event(0, 0, 0x90, 64, 16),
            event(96, 100_000, 0xC1, 92), event(96, 100_000, 0x91, 64, 64),
            event(192, 200_000, 0x81, 64, 64),
            event(288, 300_000, 0x80, 64, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=events),),
        )
        arranged, decisions = virtualize_polyphony(
            18, quantize_notes(18, collect_notes(sound)),
        )
        self.assertEqual(
            [(note.program, note.start, note.end) for note in arranged],
            [(50, 0, 12), (92, 12, 25), (50, 25, 38)],
        )
        self.assertEqual(
            [(decision.action, decision.program, decision.peer_program) for decision in decisions],
            [("MERGE", 50, 92)],
        )

    def test_sound_18_fails_when_foreground_alone_exceeds_capacity(self) -> None:
        events = [event(0, 0, 0xC0, 57)]
        events.extend(event(0, 0, 0x90, note, 64) for note in range(48, 57))
        events.extend(event(96, 100_000, 0x80, note, 64) for note in range(48, 57))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        with self.assertRaisesRegex(ValueError, "outside its duckable bed"):
            virtualize_polyphony(18, quantize_notes(18, collect_notes(sound)))

    def test_sound_185_uses_reviewed_marimba_for_program_zero(self) -> None:
        events = (
            event(0, 0, 0xC0, 0),
            event(0, 0, 0x90, 38, 100), event(0, 0, 0x90, 69, 60),
            event(96, 100_000, 0x80, 38, 64), event(96, 100_000, 0x80, 69, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        notes = quantize_notes(185, collect_notes(sound))
        self.assertEqual([note.instrument for note in notes], [6, 6])
        self.assertIn("@6 mt32_marimba", render_mml(185, sound))

    def test_program_zero_marimba_family_includes_complete_c2_b5_range(self) -> None:
        events = (
            event(0, 0, 0xC0, 0),
            event(0, 0, 0x90, 36, 64), event(0, 0, 0x90, 83, 64),
            event(96, 100_000, 0x80, 36, 64), event(96, 100_000, 0x80, 83, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        for sound_id in (141, 185, 201, 202, 207):
            self.assertEqual(
                [note.instrument for note in quantize_notes(sound_id, collect_notes(sound))],
                [6, 6],
            )

    def test_program_zero_marimba_family_fails_above_b5(self) -> None:
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=(
                event(0, 0, 0xC0, 0), event(0, 0, 0x90, 84, 64),
                event(96, 100_000, 0x80, 84, 64),
            )),),
        )
        with self.assertRaisesRegex(ValueError, "no reviewed SNES band"):
            render_mml(202, sound)

    def test_sound_183_protects_outer_pitches_and_strongest_attacks(self) -> None:
        events = [event(0, 0, 0xC0, 0)]
        for note in range(36, 44):
            velocity = 1 if note in (36, 40) else note
            events.append(event(0, 0, 0x90, note, velocity))
        for note in range(44, 48):
            events.append(event(96, 100_000, 0x90, note, 1))
        events.extend(event(192, 200_000, 0x80, note, 64) for note in range(44, 48))
        events.extend(event(288, 300_000, 0x80, note, 64) for note in range(36, 44))
        sound = SimpleNamespace(
            track_count=1, duration_us=300_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        arranged, decisions = virtualize_polyphony(
            183, quantize_notes(183, collect_notes(sound)),
        )
        retained_pitches = {note.midi_note for note in arranged}
        self.assertIn(36, retained_pitches)
        self.assertIn(47, retained_pitches)
        self.assertEqual(retained_pitches, set(range(36, 48)))
        self.assertEqual(len(allocate_voices(arranged)), 8)
        self.assertEqual(len(decisions), 4)
        self.assertTrue(all(decision.action == "DUCK_RESTORE" for decision in decisions))
        mml = render_mml(183, sound)
        self.assertIn("RESTORE at 0.192s", mml)
        self.assertIn("two-tick minimum key-off quantum", mml)

    def test_sound_183_fails_if_new_attacks_alone_exceed_capacity(self) -> None:
        events = [event(0, 0, 0xC0, 0)]
        events.extend(event(0, 0, 0x90, note, 64) for note in range(36, 45))
        events.extend(event(96, 100_000, 0x80, note, 64) for note in range(36, 45))
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=tuple(events)),),
        )
        with self.assertRaisesRegex(ValueError, "simultaneous protected attacks"):
            virtualize_polyphony(183, quantize_notes(183, collect_notes(sound)))

    def test_program_zero_impact_family_splits_bass_and_marimba(self) -> None:
        events = (
            event(0, 0, 0xC0, 0),
            event(0, 0, 0x90, 24, 80), event(0, 0, 0x90, 58, 76),
            event(96, 100_000, 0x80, 24, 64), event(96, 100_000, 0x80, 58, 64),
        )
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=events),),
        )
        for sound_id in (190, 192):
            notes = quantize_notes(sound_id, collect_notes(sound))
            self.assertEqual([note.instrument for note in notes], [5, 6])

    def test_program_zero_impact_family_fails_outside_explicit_ranges(self) -> None:
        sound = SimpleNamespace(
            track_count=1, duration_us=100_000,
            tracks=(SimpleNamespace(events=(
                event(0, 0, 0xC0, 0), event(0, 0, 0x90, 84, 64),
                event(96, 100_000, 0x80, 84, 64),
            )),),
        )
        with self.assertRaisesRegex(ValueError, "no reviewed SNES band"):
            render_mml(190, sound)


if __name__ == "__main__":
    unittest.main()
