import hashlib
import json
import os
from pathlib import Path
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]


class Phase6KTests(unittest.TestCase):
    def _host(self, program: bytes) -> EngineHost:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": program}, kinds={"script.boot": "SCRP"}
        )
        host = EngineHost(
            profile,
            default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        return host

    def test_far_dispatch_reuses_the_single_c25_handler(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        start = source.index("ScummV5_ColdOpcode_FarEntry:")
        body = source[start:source.index("ScummV5_ColdOpcode_FarEntry__unknown:", start)]
        self.assertIn("cmp #$4C", body)
        # The handler lives in bank zero while this dispatcher is far/cold;
        # preserve the production long jump rather than a same-bank JMP.
        self.assertIn("jml ScummV5_Op_SoundKludge", body)
        self.assertNotIn("Phase6K_Flush", source)
        self.assertEqual(
            (ROOT / "runtime/snes/engines/scumm_v5.pasm").read_text().count(
                "ScummV5_Op_SoundKludge:"
            ),
            1,
        )

    def test_empty_direct_minus_one_flush_is_exact(self) -> None:
        host = self._host(bytes.fromhex("4c 01 ff ff ff 00"))
        host.tick()
        self.assertEqual(host.engine.state.scripts[0].pc, 6)
        self.assertEqual(host.engine.inspect_state()["sound_kludge"]["queue"], [])
        self.assertEqual(
            [item["command"] for item in host.services.audio.command_history],
            ["flush"],
        )

    def test_authentic_lscr_bytes_and_following_instruction(self) -> None:
        archive_name = os.environ.get("SAME_FATE_DEMO_ARCHIVE")
        if not archive_name:
            self.skipTest(
                "optional Fate demo integration: set SAME_FATE_DEMO_ARCHIVE to run"
            )
        archive = Path(archive_name).expanduser().resolve()
        if not archive.is_file():
            self.fail(f"explicit SAME_FATE_DEMO_ARCHIVE does not exist: {archive}")
        path = ROOT / "build/m23a-rooms/authentic/room-49.sc5c"
        if not path.is_file():
            self.fail("explicit Fate integration requires generated authentic room 49")
        manifest_path = path.parent / "manifest.json"
        if not manifest_path.is_file():
            self.fail("authentic room 49 has no source identity manifest")
        manifest = json.loads(manifest_path.read_text())
        expected_archive = manifest.get("source", {}).get("archive_sha256")
        actual_archive = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual(actual_archive, expected_archive,
                         "generated room 49 came from a different Fate archive")
        from same.engines.scumm_v5.cooked_room import decode_cooked_room

        record = decode_cooked_room(path.read_bytes(), expected_room=49)
        program = next(item.program for item in record.scripts if item.number == 211)
        self.assertEqual(program[0x2D9:0x2DE], bytes.fromhex("4c 01 ff ff ff"))
        self.assertEqual(
            program[0x2DE:0x2E6], bytes.fromhex("24 53 03 3f ff ff ff ff")
        )


if __name__ == "__main__":
    unittest.main()
