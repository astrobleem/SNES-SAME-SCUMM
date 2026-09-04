import hashlib
import json
from pathlib import Path
import unittest

from same.errors import ResourceError
from same.music import (
    ControllerEvent,
    InstrumentBank,
    InstrumentRequest,
    MarkerEvent,
    NoteOffEvent,
    NoteOnEvent,
    PartSpec,
    Provenance,
    ScheduledEvent,
    SequenceIR,
)
from same.music.devices import AdlibCaptureCalibration, AdlibPatch, ScummV5AdlibDevice


class MusicArchitectureTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    def test_sequence_distinguishes_part_note_and_voice_demand(self) -> None:
        source = Provenance("fixture.qtma", track=0)
        part = PartSpec(7, InstrumentRequest(gm_fallback=11), requested_polyphony=2)
        sequence = SequenceIR(
            source_time_scale=600,
            parts=(part,),
            events=(
                ScheduledEvent(0, 0, NoteOnEvent(7, 10, 60 << 8, 96), source),
                ScheduledEvent(0, 1, NoteOnEvent(7, 11, 64 << 8, 80), source),
                ScheduledEvent(300, 2, NoteOffEvent(7, 10), source),
                ScheduledEvent(300, 3, NoteOffEvent(7, 11), source),
                ScheduledEvent(300, 4, MarkerEvent("end"), source),
            ),
            end_tick=300,
            provenance=source,
        )
        self.assertEqual(sequence.peak_polyphony(), 2)
        self.assertEqual(sequence.parts[0].part_id, 7)

    def test_sequence_rejects_unknown_parts_and_unterminated_notes(self) -> None:
        source = Provenance("fixture")
        with self.assertRaisesRegex(ValueError, "unknown part"):
            SequenceIR(
                60, (),
                (ScheduledEvent(0, 0, ControllerEvent(1, 7, 100 << 16), source),),
                1, source,
            )
        with self.assertRaisesRegex(ValueError, "unterminated"):
            SequenceIR(
                60, (PartSpec(1, InstrumentRequest(portable_id="tone")),),
                (ScheduledEvent(0, 0, NoteOnEvent(1, 0, 60 << 8, 64), source),),
                1, source,
            )

    @staticmethod
    def velocity_insensitive_patch() -> AdlibPatch:
        data = bytearray(30)
        data[1] = 11
        data[6] = 63
        data[10] = 8
        return AdlibPatch(bytes(data))

    def test_scumm_adlib_device_preserves_zero_sensitivity_velocity(self) -> None:
        patch = self.velocity_insensitive_patch()
        device = ScummV5AdlibDevice()
        self.assertEqual(device.backend_volume(patch, 1, 47), 14)
        self.assertEqual(device.backend_volume(patch, 127, 47), 14)
        self.assertEqual(patch.fingerprint, hashlib.sha256(patch.data).hexdigest())

    def test_scumm_adlib_calibration_is_explicit(self) -> None:
        patch = self.velocity_insensitive_patch()
        device = ScummV5AdlibDevice(AdlibCaptureCalibration(100, 127, 192))
        self.assertEqual(device.backend_volume(patch, 1, 47), 29)

    def test_instrument_bank_resolves_one_reviewed_patch_zone(self) -> None:
        patch = self.velocity_insensitive_patch()
        sample_hash = hashlib.sha256(b"sample").hexdigest()
        raw = json.dumps({
            "schema": "same_instrument_bank_v1",
            "name": "fixture",
            "source_device": "scumm_v5_adlib",
            "capture_velocity": 100,
            "capture_cc7": 127,
            "reference_volume": 96,
            "zones": [{
                "name": "high", "patch_sha256": patch.fingerprint,
                "sample_resource": "high.wav", "sha256": sample_hash,
                "root_pitch": 84, "first_pitch": 72, "last_pitch": 95,
                "loop_point": 256, "loop_samples": 2048,
                "review_status": "accepted",
            }],
        }).encode()
        bank = InstrumentBank.decode(raw, "fixture.bank")
        self.assertEqual(bank.resolve(patch.fingerprint, 91).name, "high")
        with self.assertRaisesRegex(ResourceError, "0 accepted zones"):
            bank.resolve(patch.fingerprint, 60)

    def test_fate_reviewed_bank_pins_every_sample_identity(self) -> None:
        manifest = self.ROOT / "audio/fate_s6/samples/fate154_adlib_manifest.json"
        bank = InstrumentBank.decode(manifest.read_bytes(), str(manifest))
        self.assertEqual(bank.source_device, "scumm_v5_adlib")
        self.assertEqual(len(bank.zones), 7)
        for zone in bank.zones:
            sample = self.ROOT / zone.sample_resource
            self.assertTrue(sample.is_file())
            self.assertEqual(hashlib.sha256(sample.read_bytes()).hexdigest(), zone.sample_sha256)

    def test_monkey_church_bank_reuses_exact_reviewed_mi_samples(self) -> None:
        manifest = self.ROOT / "audio/monkey_v5/monkey154_church_bank.json"
        bank = InstrumentBank.decode(manifest.read_bytes(), str(manifest))
        self.assertEqual(bank.source_device, "scumm_v5_adlib")
        self.assertEqual(
            [zone.name for zone in bank.zones],
            ["monkey154_organ_low", "monkey154_organ_main"],
        )
        patch = "625b3bfe1a9b2253828cd5c4179a02e2cf18e3aa15d98178d5a3fe597420992b"
        self.assertEqual(bank.resolve(patch, 57).name, "monkey154_organ_low")
        self.assertEqual(bank.resolve(patch, 58).name, "monkey154_organ_main")
        for zone in bank.zones:
            sample = self.ROOT / zone.sample_resource
            self.assertEqual(hashlib.sha256(sample.read_bytes()).hexdigest(), zone.sample_sha256)


if __name__ == "__main__":
    unittest.main()
