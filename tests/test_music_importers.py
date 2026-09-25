import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from same.music import (
    ControllerEvent, InstrumentBank, InstrumentZone, realize_scumm_adlib_notes,
    sequence_trace,
)
from same.music.devices import (
    AdlibPatch, ScummV5AdlibDevice, extract_scumm_adlib_patches,
)
from same.music.importers import (
    QtmaDecodeError, ScummImuseImportError, ScummImuseTimeline, decode_qtma_events,
    import_scumm_adlib_sequence,
)


ROOT = Path(__file__).resolve().parents[1]
# Copyright-free fixture authored for SAME from the QuickTime 7.6.6
# QuickTimeMusic.h packing macros. It has two NoteRequests, controllers, a
# chord, a percussion note crossing a rest, a melody note, and an End marker.
QTMA_FIXTURE = bytes.fromhex(
    (ROOT / "examples/resources/music/qtma_m2_fixture.hex").read_text(encoding="ascii")
)


def midi_event(tick: int, time_us: int, status: int, *data: int) -> SimpleNamespace:
    return SimpleNamespace(tick=tick, time_us=time_us, status=status, data=data)


class MusicImporterTests(unittest.TestCase):
    ROOT = ROOT

    @staticmethod
    def synthetic_patch() -> AdlibPatch:
        data = bytearray(30)
        data[1] = 11
        data[6] = 63
        data[10] = 8
        return AdlibPatch(bytes(data))

    @classmethod
    def synthetic_bank(cls, patch: AdlibPatch) -> InstrumentBank:
        return InstrumentBank(
            "copyright-free AdLib fixture", ScummV5AdlibDevice.identifier,
            100, 127, 96,
            (InstrumentZone(
                "fixture_mid", patch.fingerprint, "fixture-cycle.wav", "0" * 64,
                60, 48, 71, 0, 16, "accepted",
            ),),
        )

    def test_second_scumm_cue_uses_shared_importer_device_and_bank(self) -> None:
        patch = self.synthetic_patch()
        sound = SimpleNamespace(
            key="copyright-free.scumm-adlib-2",
            duration_us=750_000,
            tracks=(SimpleNamespace(events=(
                midi_event(0, 0, 0xB2, 7, 100),
                midi_event(0, 0, 0x92, 60, 64),
                midi_event(120, 250_000, 0xB2, 7, 50),
                midi_event(240, 500_000, 0x82, 60, 64),
                midi_event(240, 500_000, 0x92, 64, 96),
                midi_event(360, 750_000, 0x82, 64, 64),
            )),),
        )
        sequence = import_scumm_adlib_sequence(
            sound, {2: patch}, timeline=ScummImuseTimeline(time_scale=1000),
        )
        notes = realize_scumm_adlib_notes(
            sequence, {2: patch}, self.synthetic_bank(patch),
        )
        self.assertEqual(sequence.peak_polyphony(), 1)
        self.assertEqual(sequence.parts[0].requested_polyphony, 1)
        self.assertEqual(
            [(event.payload.controller, event.payload.value_q16)
             for event in sequence.events
             if isinstance(event.payload, ControllerEvent)],
            [(7, 100 << 16), (7, 50 << 16)],
        )
        self.assertEqual(
            [(note.start, note.end, note.midi_note, note.zone_name) for note in notes],
            [(0, 500, 60, "fixture_mid"), (500, 750, 64, "fixture_mid")],
        )
        device = ScummV5AdlibDevice()
        self.assertEqual(notes[0].volume, device.backend_volume(patch, 64, 100))
        self.assertEqual(
            notes[0].volume_changes,
            ((250, device.backend_volume(patch, 64, 50)),),
        )
        self.assertEqual(sequence_trace(sequence)[-1]["event"], "marker")

        unsupported = SimpleNamespace(
            key="copyright-free.scumm-unsupported", duration_us=0,
            tracks=(SimpleNamespace(events=(midi_event(0, 0, 0xB2, 11, 64),)),),
        )
        with self.assertRaises(ScummImuseImportError) as caught:
            import_scumm_adlib_sequence(unsupported, {2: patch})
        self.assertEqual(caught.exception.source, "copyright-free.scumm-unsupported")
        self.assertEqual(caught.exception.event_index, 0)
        self.assertIn("controller 11", str(caught.exception))

    def test_scumm_pan_and_explicit_source_loop_survive_import(self) -> None:
        patch = self.synthetic_patch()

        class Track:
            duration_ticks = 480
            events = (
                midi_event(0, 0, 0xB0, 10, 32),
                midi_event(0, 0, 0x90, 60, 100),
                midi_event(240, 500_000, 0x90, 64, 100),
                midi_event(480, 1_000_000, 0x80, 60, 64),
                midi_event(480, 1_000_000, 0x80, 64, 64),
            )

            @staticmethod
            def time_at_tick(tick: int, division: int) -> int:
                return tick * 1_000_000 // division

        sound = SimpleNamespace(
            key="copyright-free.scumm-loop", division=480,
            duration_us=1_000_000, tracks=(Track(),),
        )
        sequence = import_scumm_adlib_sequence(
            sound, {0: patch},
            timeline=ScummImuseTimeline(
                time_scale=120, loop_source_ticks=(0, 480),
            ),
        )
        self.assertEqual(sequence.loop, (0, 120))
        self.assertEqual(sequence.parts[0].requested_polyphony, 2)
        pan = sequence.events[0].payload
        self.assertIsInstance(pan, ControllerEvent)
        self.assertEqual((pan.controller, pan.value_q16), (10, 32 << 16))

    def test_scumm_patch_extraction_rejects_missing_and_changed_identity(self) -> None:
        patch = self.synthetic_patch()
        record = SimpleNamespace(command=16, values=(2, *patch.data))
        sound = SimpleNamespace(key="patch.fixture", imuse_events=((record, record),))
        self.assertEqual(extract_scumm_adlib_patches(sound), {2: patch})
        changed = bytearray(patch.data)
        changed[0] ^= 1
        conflict = SimpleNamespace(command=16, values=(2, *changed))
        with self.assertRaisesRegex(ValueError, "changes channel 2 patch identity"):
            extract_scumm_adlib_patches(SimpleNamespace(
                key="patch.conflict", imuse_events=((record, conflict),),
            ))
        with self.assertRaisesRegex(ValueError, "no complete patches"):
            extract_scumm_adlib_patches(SimpleNamespace(
                key="patch.missing", imuse_events=((),),
            ))

    def test_qtma_fixture_decodes_to_exact_source_neutral_trace(self) -> None:
        self.assertEqual(len(QTMA_FIXTURE), 232)
        self.assertEqual(
            hashlib.sha256(QTMA_FIXTURE).hexdigest(),
            "1a595217e6ef5e05e3f15c193a92d364243db7c308c179ff48109e1456e2b0c0",
        )
        sequence = decode_qtma_events(QTMA_FIXTURE, source="m2.qtma")
        self.assertEqual(sequence.source_time_scale, 600)
        self.assertEqual(sequence.end_tick, 600)
        self.assertEqual(sequence.peak_polyphony(), 3)
        self.assertEqual(
            [
                (part.part_id, part.instrument.gm_fallback, part.percussion,
                 part.requested_polyphony, part.typical_polyphony_q16)
                for part in sequence.parts
            ],
            [(0, 11, False, 4, 2 << 16), (1, 0, True, 2, 1 << 16)],
        )
        trace = sequence_trace(sequence)
        golden = json.loads(
            (self.ROOT / "examples/resources/music/qtma_m2_trace.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(list(trace), golden)
        self.assertEqual(trace, sequence_trace(decode_qtma_events(QTMA_FIXTURE, source="m2.qtma")))

    def test_qtma_malformed_data_fails_with_offsets(self) -> None:
        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(QTMA_FIXTURE[:20], source="short.qtma")
        self.assertEqual(caught.exception.code, "truncated_event")
        self.assertEqual(caught.exception.word_offset, 0)
        self.assertEqual(caught.exception.byte_offset, 0)

        bad_tail = bytearray(QTMA_FIXTURE)
        bad_tail[91] ^= 1
        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(bytes(bad_tail), source="tail.qtma")
        self.assertEqual(caught.exception.code, "mismatched_general_tail")

        undeclared_note = bytes.fromhex("2073012c60000000")
        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(undeclared_note, source="part.qtma")
        self.assertEqual(caught.exception.code, "unknown_part")
        self.assertIn("word 0", str(caught.exception))

        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(QTMA_FIXTURE + bytes.fromhex("00000001"))
        self.assertEqual(caught.exception.code, "trailing_event")

        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(bytes.fromhex("9000000080000000"), source="xnote.qtma")
        self.assertEqual(caught.exception.code, "unsupported_required_feature")
        self.assertEqual(caught.exception.word_offset, 0)

        with self.assertRaises(QtmaDecodeError) as caught:
            decode_qtma_events(bytes.fromhex("f0000001"), source="length.qtma")
        self.assertEqual(caught.exception.code, "invalid_general_length")

    def test_generic_music_path_contains_no_cue_number(self) -> None:
        paths = (
            self.ROOT / "src/same/music/importers/scumm_imuse.py",
            self.ROOT / "src/same/music/realize.py",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("sound 154", text.lower())
            self.assertNotIn("sound.154", text.lower())


if __name__ == "__main__":
    unittest.main()
