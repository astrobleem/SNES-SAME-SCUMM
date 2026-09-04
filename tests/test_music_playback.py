import hashlib
import json
from pathlib import Path
import struct
import unittest

from same.music import (
    ControllerEvent,
    InstrumentRequest,
    MarkerEvent,
    NoteOffEvent,
    NoteOnEvent,
    PartSpec,
    PlaybackSession,
    Provenance,
    ReferenceSynth,
    ScheduledEvent,
    SequenceIR,
    VoiceBudgetError,
    render_reference,
)
from same.music.importers import decode_qtma_events


ROOT = Path(__file__).resolve().parents[1]
QTMA_FIXTURE = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m2_fixture.hex").read_text(encoding="ascii")
)


def qtma_sequence() -> SequenceIR:
    return decode_qtma_events(QTMA_FIXTURE, source="m3.qtma")


class MusicPlaybackTests(unittest.TestCase):
    def test_qtma_reference_render_is_exact_and_repeatable(self) -> None:
        oracle = json.loads(
            (ROOT / "examples/resources/music/qtma_m3_reference.json").read_text()
        )
        self.assertEqual(hashlib.sha256(QTMA_FIXTURE).hexdigest(), oracle["source_sha256"])
        first = render_reference(qtma_sequence())
        second = render_reference(qtma_sequence())
        self.assertEqual(first.sample_rate, oracle["sample_rate"])
        self.assertEqual(first.frames, oracle["frames"])
        self.assertEqual(len(first.wav), 48_044)
        self.assertEqual(first.wav, second.wav)
        self.assertEqual(
            hashlib.sha256(first.wav).hexdigest(),
            oracle["wav_sha256"],
        )
        self.assertEqual(hashlib.sha256(first.pcm_s16le).hexdigest(), oracle["pcm_sha256"])
        samples = struct.unpack(f"<{first.frames}h", first.pcm_s16le)
        self.assertEqual(max(map(abs, samples)), oracle["peak_absolute"])
        self.assertEqual(
            sum(sample in (-32768, 32767) for sample in samples),
            oracle["clipped_samples"],
        )

        percussion_release = next(
            action for action in first.actions
            if action.action == "note_off" and action.note_id == 2
        )
        self.assertEqual(
            (percussion_release.tick, percussion_release.voice, percussion_release.reason),
            (250, 2, "event"),
        )
        deferred = next(
            action for action in first.actions
            if action.action == "defer" and action.note_id == 0
        )
        sustained_release = next(
            action for action in first.actions
            if action.action == "note_off" and action.note_id == 0
        )
        self.assertEqual((deferred.tick, sustained_release.tick), (300, 300))
        self.assertEqual(sustained_release.reason, "sustain")

    def test_sustain_is_part_local_and_delays_only_eligible_release(self) -> None:
        source = Provenance("sustain.fixture")
        parts = (
            PartSpec(0, InstrumentRequest(gm_fallback=0)),
            PartSpec(1, InstrumentRequest(gm_fallback=1)),
        )
        sequence = SequenceIR(
            100,
            parts,
            (
                ScheduledEvent(0, 0, ControllerEvent(0, 64, 1 << 16), source),
                ScheduledEvent(0, 1, NoteOnEvent(0, 10, 60 << 8, 100), source),
                ScheduledEvent(0, 2, NoteOnEvent(1, 11, 64 << 8, 100), source),
                ScheduledEvent(10, 3, NoteOffEvent(0, 10), source),
                ScheduledEvent(10, 4, NoteOffEvent(1, 11), source),
                ScheduledEvent(20, 5, ControllerEvent(0, 64, 0), source),
                ScheduledEvent(30, 6, MarkerEvent("end"), source),
            ),
            30,
            source,
        )
        synth = ReferenceSynth(parts, 1_000)
        session = PlaybackSession(sequence, synth, sample_rate=1_000, voice_limit=2)
        session.finish()
        releases = {
            action.note_id: (action.tick, action.sample, action.reason)
            for action in session.actions if action.action == "note_off"
        }
        self.assertEqual(releases[10], (20, 200, "sustain"))
        self.assertEqual(releases[11], (10, 100, "event"))
        self.assertEqual(session.active_note_ids, ())
        self.assertEqual(synth.active_voice_handles, ())

    def test_absolute_rational_timing_and_explicit_stop_are_exact(self) -> None:
        sequence = qtma_sequence()
        synth = ReferenceSynth(sequence.parts, 22_050)
        session = PlaybackSession(sequence, synth, sample_rate=22_050)
        self.assertEqual(
            [session.sample_at_tick(tick) for tick in (1, 2, 3, 600)],
            [36, 73, 110, 22_050],
        )
        session.advance_to_tick(150)
        self.assertEqual(session.active_note_ids, (0, 1, 2))
        session.stop()
        self.assertTrue(session.stopped)
        self.assertEqual(session.active_note_ids, ())
        self.assertEqual(synth.active_voice_handles, ())

    def test_voice_budget_failure_pins_tick_and_active_notes(self) -> None:
        source = Provenance("voice-budget.fixture")
        part = PartSpec(0, InstrumentRequest(gm_fallback=0), requested_polyphony=2)
        sequence = SequenceIR(
            60,
            (part,),
            (
                ScheduledEvent(0, 0, NoteOnEvent(0, 10, 60 << 8, 100), source),
                ScheduledEvent(0, 1, NoteOnEvent(0, 11, 64 << 8, 100), source),
                ScheduledEvent(30, 2, NoteOffEvent(0, 10), source),
                ScheduledEvent(30, 3, NoteOffEvent(0, 11), source),
                ScheduledEvent(30, 4, MarkerEvent("end"), source),
            ),
            30,
            source,
        )
        synth = ReferenceSynth((part,), 24_000)
        session = PlaybackSession(sequence, synth, sample_rate=24_000, voice_limit=1)
        with self.assertRaises(VoiceBudgetError) as caught:
            session.advance_to_tick(0)
        self.assertEqual(caught.exception.tick, 0)
        self.assertEqual(caught.exception.active_note_ids, (10,))
        self.assertEqual(caught.exception.requested_note_id, 11)
        self.assertIn("active notes [10]", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
