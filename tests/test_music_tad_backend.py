from __future__ import annotations

import unittest

from same.music import (
    ControllerEvent, InstrumentRequest, MarkerEvent, PartSpec, Provenance,
    SampledNote, ScheduledEvent, SequenceIR, TadCompileError, TadInstrument,
    TadPanPolicy, compile_tad_mml,
)


class MusicTadBackendTests(unittest.TestCase):
    @staticmethod
    def sequence(*, controller: int = 10, polyphony: int = 1) -> SequenceIR:
        source = Provenance("copyright-free.tad.fixture", track=0)
        events = [
            ScheduledEvent(0, 0, ControllerEvent(3, controller, 32 << 16), source),
        ]
        events.append(ScheduledEvent(20, 1, MarkerEvent("end"), source))
        return SequenceIR(
            125,
            (PartSpec(3, InstrumentRequest(portable_id="fixture"), polyphony),),
            tuple(events),
            20,
            source,
            loop=(2, 20),
        )

    def test_exact_loop_pan_instrument_and_automation_mml(self) -> None:
        song = compile_tad_mml(
            self.sequence(),
            (SampledNote(
                2, 18, 60, 96, "fixture_zone", 3, 7, ((10, 48),),
            ),),
            (TadInstrument("fixture_zone", "fixture_sample"),),
            title="Fixture",
        )
        self.assertEqual(song.voice_count, 1)
        self.assertEqual(song.loop, (2, 20))
        self.assertEqual(song.pan_policy, TadPanPolicy.STEREO_CC10)
        self.assertEqual(
            song.mml,
            "#Title Fixture\n"
            "#Author SAME generic sampled backend\n"
            "#Timer 64\n#ZenLen 192\n\n"
            "; SAME sampled backend; pan_policy=stereo_cc10; "
            "source=copyright-free.tad.fixture\n"
            "; tick_bias=0; one_tick_release_adjustments=none\n"
            "@0 fixture_sample\n\n"
            "A q0 r%2 L @0 V96 p32 o4 c%8 & V48 w%8 r%2\n",
        )
        mono = compile_tad_mml(
            self.sequence(),
            (SampledNote(2, 18, 60, 96, "fixture_zone", 3, 7),),
            (TadInstrument("fixture_zone", "fixture_sample"),),
            pan_policy=TadPanPolicy.MONO_CENTER,
        )
        self.assertIn(" p64 ", mono.mml)

    def test_one_tick_lead_and_internal_rest_are_explicitly_normalized(self) -> None:
        source = Provenance("copyright-free.one-tick")
        sequence = SequenceIR(
            125, (PartSpec(0, InstrumentRequest(portable_id="fixture")),),
            (ScheduledEvent(10, 0, MarkerEvent("end"), source),),
            10, source, loop=(1, 10),
        )
        song = compile_tad_mml(
            sequence,
            (
                SampledNote(1, 5, 60, 96, "fixture_zone", 0, 1),
                SampledNote(6, 10, 62, 96, "fixture_zone", 0, 2),
            ),
            (TadInstrument("fixture_zone", "fixture_sample"),),
        )
        self.assertEqual(song.tick_bias, 1)
        self.assertEqual(song.loop, (2, 11))
        self.assertEqual(song.release_adjustments, (1,))
        self.assertIn("r%2 L", song.mml)
        self.assertNotIn("%1", song.mml)

    def test_capacity_loop_controller_and_zone_fail_with_source_tick(self) -> None:
        instruments = (TadInstrument("fixture_zone", "fixture_sample"),)
        notes = tuple(
            SampledNote(2, 10, 48 + index, 96, "fixture_zone", 3, index)
            for index in range(9)
        )
        with self.assertRaisesRegex(TadCompileError, "tick 2.*voice limit 8"):
            compile_tad_mml(self.sequence(polyphony=9), notes, instruments)
        with self.assertRaisesRegex(TadCompileError, "tick 2.*crosses the loop"):
            compile_tad_mml(
                self.sequence(),
                (SampledNote(1, 10, 60, 96, "fixture_zone", 3, 0),),
                instruments,
            )
        with self.assertRaisesRegex(TadCompileError, "tick 2.*no TAD instrument"):
            compile_tad_mml(
                self.sequence(),
                (SampledNote(2, 10, 60, 96, "missing", 3, 0),),
                instruments,
            )
        with self.assertRaisesRegex(TadCompileError, "tick 0.*controller 11"):
            compile_tad_mml(
                self.sequence(controller=11),
                (SampledNote(2, 10, 60, 96, "fixture_zone", 3, 0),),
                instruments,
            )

    def test_backend_source_has_no_importer_or_game_dependency(self) -> None:
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "src/same/music/backends/tad_mml.py"
        text = path.read_text(encoding="utf-8").lower()
        for forbidden in ("scumm", "monkey", "fate", "sound.154", "same.engines"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
