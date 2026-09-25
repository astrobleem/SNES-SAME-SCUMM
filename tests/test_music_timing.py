from __future__ import annotations

from pathlib import Path
import unittest

from same.music import (
    InstrumentRequest, MarkerEvent, NoteOffEvent, NoteOnEvent, PartSpec,
    Provenance, ScheduledEvent, SequenceIR, TimeScaleError,
    normalize_sequence_time_scale,
)
from same.music.importers import decode_qtma_events


ROOT = Path(__file__).resolve().parents[1]
QTMA = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m2_fixture.hex").read_text("ascii")
)


class MusicTimingTests(unittest.TestCase):
    def test_equal_scale_is_exact_and_byte_path_neutral(self) -> None:
        sequence = decode_qtma_events(QTMA, time_scale=125)
        result = normalize_sequence_time_scale(sequence, 125, policy="exact")
        self.assertIs(result.sequence, sequence)
        self.assertEqual((result.max_error_numerator, result.duration_error_numerator), (0, 0))

    def test_600_hz_uses_absolute_nearest_timing_without_drift(self) -> None:
        sequence = decode_qtma_events(QTMA, time_scale=600)
        with self.assertRaises(TimeScaleError) as caught:
            normalize_sequence_time_scale(sequence, 125, policy="exact")
        self.assertEqual((caught.exception.code, caught.exception.source_tick), ("inexact_tick", 150))

        result = normalize_sequence_time_scale(
            sequence, 125, policy="nearest_absolute",
        )
        self.assertEqual(result.sequence.end_tick, 125)
        self.assertEqual(result.duration_error_numerator, 0)
        self.assertEqual(
            (result.max_error_numerator, result.error_denominator), (300, 600),
        )
        self.assertEqual(
            [event.tick for event in result.sequence.events],
            [0, 0, 0, 0, 0, 31, 52, 63, 63, 63, 94, 125, 125],
        )
        self.assertEqual(
            [event.provenance.source_tick for event in result.sequence.events],
            [0, 0, 0, 0, 0, 150, 250, 300, 300, 300, 450, 600, 600],
        )
        self.assertTrue(all(
            event.provenance.source_time_scale == 600
            for event in result.sequence.events
        ))
        at_63 = [
            type(event.payload).__name__
            for event in result.sequence.events if event.tick == 63
        ]
        self.assertEqual(
            at_63, ["NoteOffEvent", "ControllerEvent", "NoteOnEvent"],
        )

    def test_nondivisible_scale_rounds_absolute_positions_not_deltas(self) -> None:
        source = Provenance("time.sevenths")
        part = PartSpec(0, InstrumentRequest(gm_fallback=0))
        sequence = SequenceIR(
            7, (part,), (
                ScheduledEvent(1, 10, NoteOnEvent(0, 1, 60 << 8, 100), source),
                ScheduledEvent(2, 11, NoteOffEvent(0, 1), source),
                ScheduledEvent(3, 12, MarkerEvent("third"), source),
                ScheduledEvent(4, 13, MarkerEvent("fourth"), source),
                ScheduledEvent(7, 14, MarkerEvent("end"), source),
            ), 7, source,
        )
        result = normalize_sequence_time_scale(
            sequence, 3, policy="nearest_absolute",
        )
        self.assertEqual(
            [event.tick for event in result.sequence.events], [0, 1, 1, 2, 3],
        )
        self.assertEqual(result.sequence.end_tick, 3)
        self.assertEqual(result.duration_error_numerator, 0)
        self.assertLessEqual(
            result.max_error_numerator * 2, result.error_denominator,
        )

    def test_quantization_cannot_silently_collapse_a_note(self) -> None:
        source = Provenance("time.collapse")
        part = PartSpec(0, InstrumentRequest(gm_fallback=0))
        sequence = SequenceIR(
            1000, (part,), (
                ScheduledEvent(1, 0, NoteOnEvent(0, 1, 60 << 8, 100), source),
                ScheduledEvent(2, 1, NoteOffEvent(0, 1), source),
                ScheduledEvent(2, 2, MarkerEvent("end"), source),
            ), 2, source,
        )
        with self.assertRaises(TimeScaleError) as caught:
            normalize_sequence_time_scale(
                sequence, 1, policy="nearest_absolute",
            )
        self.assertEqual(caught.exception.code, "collapsed_note")


if __name__ == "__main__":
    unittest.main()
