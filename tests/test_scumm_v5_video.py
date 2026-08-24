from __future__ import annotations

from pathlib import Path
import unittest

from same.capabilities import DEFAULT_HOST_CAPABILITIES, EngineCapability
from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import ScummV5Charset, decode_scene
from same.errors import ResourceError
from same.profile import load_profile
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s3_conformance.json"
RESOURCE_ROOT = ROOT / "examples/resources/scumm_v5"
LOGICAL_HASH = "6d4451b55770536cde22b8b01338d5dbda06cdf0d6198d1d1066d86faf53b086"
PHYSICAL_HASH = "54ddea1f2a877e6a88fad3ea2a94987688e29705e78e8fb21fd1fb9f29e2afaf"


def host_with(capabilities: EngineCapability) -> EngineHost:
    profile = load_profile(PROFILE)
    services = HostServices.create(profile, capabilities=capabilities)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    return host


class ScummV5VideoTests(unittest.TestCase):
    @staticmethod
    def _raw_v5_charset(cooked: bytes) -> bytes:
        raw = bytearray(21)
        raw.extend((1, 8, 0, 1))  # 1bpp, height 8, 256 characters
        for index in range(256):
            offset = int.from_bytes(cooked[19 + index * 4 : 23 + index * 4], "little")
            raw.extend((0 if offset == 0 else offset - 15).to_bytes(4, "little"))
        raw.extend(cooked[1043:])
        raw[0:4] = (len(raw) - 15).to_bytes(4, "little")
        return bytes(raw)

    def test_baseline_and_accelerated_plans_have_exact_same_logical_frame(self) -> None:
        accelerated = host_with(DEFAULT_HOST_CAPABILITIES)
        baseline_capabilities = DEFAULT_HOST_CAPABILITIES & ~(
            EngineCapability.TILED_VIDEO
            | EngineCapability.SPRITE_OAM
            | EngineCapability.Z_MASK
            | EngineCapability.HDMA
            | EngineCapability.SA1_JOBS
        )
        baseline = host_with(baseline_capabilities)
        accelerated_video = accelerated.engine.inspect_state()["video"]
        baseline_video = baseline.engine.inspect_state()["video"]

        self.assertEqual(accelerated_video["mode"], "accelerated")
        self.assertEqual(baseline_video["mode"], "baseline")
        self.assertEqual(accelerated_video["logical_sha256"], LOGICAL_HASH)
        self.assertEqual(baseline_video["logical_sha256"], LOGICAL_HASH)
        self.assertEqual(accelerated.services.video.surface.hash(), PHYSICAL_HASH)
        self.assertEqual(baseline.services.video.surface.hash(), PHYSICAL_HASH)
        self.assertEqual(accelerated_video["plan"]["unique_tiles"], 63)
        self.assertEqual(accelerated_video["plan"]["oam_objects"], 2)
        self.assertEqual(accelerated_video["plan"]["z_mask_pixels"], 704)
        self.assertEqual(accelerated_video["plan"]["glyphs"], 11)

    def test_actor_z_mask_font_and_cursor_projection_are_exact(self) -> None:
        host = host_with(DEFAULT_HOST_CAPABILITIES)
        logical = host.engine._video.logical_surface
        assert logical is not None
        self.assertEqual(logical.pixels[90 * 320 + 135], 28)
        self.assertEqual(logical.pixels[90 * 320 + 142], 5)
        self.assertEqual(logical.pixels[100 * 320 + 145], 30)
        self.assertEqual(logical.pixels[16 * 320 + 50], 31)  # top of synthetic S
        self.assertEqual(logical.pixels[180 * 320 + 236], 31)  # synthetic F
        self.assertEqual((host.services.video.cursor.width, host.services.video.cursor.height), (8, 8))

        host.tick(pointer=(319, 199))
        self.assertEqual(host.engine.inspect_state()["cursor"], [319, 199])
        self.assertEqual(
            (host.services.video.cursor.x, host.services.video.cursor.y), (255, 211)
        )

    def test_scene_and_charset_decoders_fail_closed(self) -> None:
        scene = (RESOURCE_ROOT / "s3_scene.scn3").read_bytes()
        with self.assertRaisesRegex(ResourceError, "truncated"):
            decode_scene(scene[:100], key="scene.bad")
        charset = bytearray((RESOURCE_ROOT / "s3_font.char").read_bytes())
        charset[0:4] = (len(charset) + 1).to_bytes(4, "little")
        with self.assertRaisesRegex(ResourceError, "declares"):
            ScummV5Charset(bytes(charset), key="font.bad")

    def test_raw_v5_char_wrapper_uses_relative_glyph_offsets(self) -> None:
        cooked = (RESOURCE_ROOT / "s3_font.char").read_bytes()
        raw = self._raw_v5_charset(cooked)
        cooked_glyph = ScummV5Charset(cooked, key="font.cooked").glyph(ord("S"))
        raw_glyph = ScummV5Charset(raw, key="charset.1").glyph(ord("S"))
        self.assertEqual(raw_glyph, cooked_glyph)


if __name__ == "__main__":
    unittest.main()
