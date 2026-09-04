from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from same.engines.scumm_v5.room_visual import (
    HEADER,
    ROW,
    decode_room_visual,
    encode_room_visual,
)
from same.errors import ResourceError
from same.video import IndexedSurface, Rect


ROOT = Path(__file__).resolve().parents[1]


def identity(name: str) -> str:
    return hashlib.sha256(name.encode("ascii")).hexdigest()


def fixture(*, width: int = 13, height: int = 5, pitch: int = 17) -> bytes:
    palette = bytes((index * factor) & 0xFF for index in range(256) for factor in (3, 5, 7))
    pixels = bytearray([0xCC] * (pitch * height))
    for y in range(height):
        pixels[y * pitch:y * pitch + width] = bytes(
            (x * 11 + y * 29) & 0xFF for x in range(width)
        )
    return encode_room_visual(
        room=7, width=width, height=height, pitch=pitch,
        palette=palette, pixels=bytes(pixels), archive_sha256=identity("archive"),
        index_sha256=identity("index"), data_sha256=identity("data"),
        room_sha256=identity("room"),
    )


class ScummV5RoomVisualTests(unittest.TestCase):
    def test_source_neutral_record_round_trips_complete_pitched_surface(self) -> None:
        encoded = fixture()
        visual = decode_room_visual(encoded, expected_room=7)
        self.assertEqual((visual.width, visual.height, visual.pitch), (13, 5, 17))
        self.assertEqual(len(visual.palette), 768)
        self.assertEqual(len(visual.pixels), 85)
        self.assertEqual(visual.record_sha256, hashlib.sha256(encoded).hexdigest())
        self.assertEqual(visual.visible_row(4), bytes((x * 11 + 4 * 29) & 0xFF for x in range(13)))
        self.assertEqual(visual.pixels[13:17], b"\xCC" * 4)

    def test_record_is_an_ordinary_indexed_source_not_a_precomposed_screen(self) -> None:
        visual = decode_room_visual(fixture(), expected_room=7)
        palette = [tuple(visual.palette[i:i + 3]) for i in range(0, 768, 3)]
        source = IndexedSurface.wrap(
            visual.width, visual.height, visual.pitch, visual.pixels, palette=palette,
        )
        target = IndexedSurface(8, 7)
        target.fill(0)
        changed = target.blit_surface(source, source_rect=Rect(2, 1, 8, 4), x=-1, y=2)
        self.assertEqual(changed, Rect(0, 2, 7, 4))
        for row in range(4):
            expected = bytes(((x + 3) * 11 + (row + 1) * 29) & 0xFF for x in range(7))
            self.assertEqual(target.visible_bytes()[(row + 2) * 8:(row + 3) * 8][:7], expected)
        self.assertTrue(source.readonly)
        with self.assertRaisesRegex(TypeError, "read-only"):
            source.fill(1)

    def test_schema_rejects_wrong_identity_format_and_room(self) -> None:
        encoded = fixture()
        with self.assertRaises(ResourceError):
            decode_room_visual(b"BAD" + encoded[3:])
        with self.assertRaises(ResourceError):
            decode_room_visual(encoded, expected_room=8)
        malformed = bytearray(encoded)
        struct.pack_into("<H", malformed, 12, 99)  # pixel format
        with self.assertRaises(ResourceError):
            decode_room_visual(bytes(malformed))

    def test_schema_rejects_truncated_and_malformed_rows_transactionally(self) -> None:
        encoded = fixture()
        with self.assertRaises(ResourceError):
            decode_room_visual(encoded[:-1])
        values = HEADER.unpack_from(encoded)
        row_directory_offset = values[11]
        malformed = bytearray(encoded)
        offset, _length = ROW.unpack_from(malformed, row_directory_offset)
        ROW.pack_into(malformed, row_directory_offset, offset, 12)
        malformed[HEADER.size - 32:HEADER.size] = bytes(32)
        malformed[HEADER.size - 32:HEADER.size] = hashlib.sha256(malformed).digest()
        with self.assertRaisesRegex(ResourceError, "row directory"):
            decode_room_visual(bytes(malformed))

    def test_encoder_validation_fails_before_producing_a_record(self) -> None:
        common = dict(
            room=7, width=2, height=2, pitch=2, palette=bytes(768), pixels=bytes(4),
            archive_sha256=identity("a"), index_sha256=identity("i"),
            data_sha256=identity("d"), room_sha256=identity("r"),
        )
        for replacement in (
            {"width": 0}, {"height": 0}, {"pitch": 1}, {"palette": bytes(767)},
            {"pixels": bytes(3)}, {"archive_sha256": "not-a-hash"},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ResourceError):
                encode_room_visual(**(common | replacement))

    def test_scumm_target_integration_is_hardware_blind(self) -> None:
        integration = (ROOT / "runtime/snes/engines/scumm_v5_visual.pasm").read_text()
        facade = (ROOT / "runtime/snes/services/video_surface.pasm").read_text()
        self.assertIn("Same_VideoSurface_ComposeRoom_Far", integration)
        for forbidden in (
            "BGMODE", "BG1SC", "BG12NBA", "VMADD", "CGRAM", "OAM", "DMAP7",
            "$402000", "$410000", "$41E000", "SAME_BWRAM_SURFACE_BASE",
        ):
            self.assertNotIn(forbidden, integration)
        self.assertIn("SAME_BWRAM_SURFACE_BASE", facade)
        self.assertNotIn("cmp #$31", facade)

    def test_target_generator_segments_complete_rows_without_crossing_banks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = fixture(width=320, height=224, pitch=328)
            (root / "room-7.sc5v").write_bytes(record)
            manifest = {
                "records": [{"room": 7, "visual": {
                    "output": "room-7.sc5v", "record_sha256": hashlib.sha256(record).hexdigest(),
                }}]
            }
            (root / "manifest.json").write_text(json.dumps(manifest))
            output, report = root / "visuals.inc.pasm", root / "report.json"
            subprocess.run(
                ["python3", str(ROOT / "tools/generate_snes_room_visuals.py"),
                 "--manifest", str(root / "manifest.json"), "--output", str(output),
                 "--binary-dir", str(root / "segments"), "--report", str(report),
                 "--first-bank", "16"],
                cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                check=True, capture_output=True, text=True,
            )
            generated = json.loads(report.read_text())
            self.assertEqual(generated["records"][0]["row_pointers"][0], [0x8000, 16])
            self.assertEqual(generated["records"][0]["row_pointers"][-1][1], 18)
            self.assertEqual(sum(item["bytes"] for item in generated["emitted"]), 328 * 224)
            self.assertTrue(all(item["bytes"] <= 0x8000 for item in generated["emitted"]))
            source = output.read_text()
            self.assertIn("SCUMM_V5_ROOM_VISUAL_DESCRIPTOR_MAGIC", source)
            self.assertIn(".word $00E0,$0300", source)


if __name__ == "__main__":
    unittest.main()
