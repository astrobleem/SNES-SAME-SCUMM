from __future__ import annotations

from pathlib import Path
import json
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.agi import AgiEngine
from same.errors import EngineExecutionError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PICTURE = (ROOT / "examples/resources/agi/picture0.agip").read_bytes()


def logic_resource(bytecode: bytes) -> bytes:
    return struct.pack("<H", len(bytecode)) + bytecode


class AgiEngineTests(unittest.TestCase):
    def _host(self, bytecode: bytes) -> EngineHost:
        profile = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        services = HostServices.create(
            profile,
            resources=MemoryResourceProvider(
                {"logic.0": logic_resource(bytecode), "picture.0": PICTURE}
            ),
        )
        host = EngineHost(profile, default_registry(), services=services)
        host.boot()
        return host

    def test_logic_resource_message_table(self) -> None:
        raw = (ROOT / "examples/resources/agi/logic0.bin").read_bytes()
        logic = AgiEngine.parse_logic(raw)
        self.assertEqual(logic.bytecode, bytes([0x01, 0x14, 0x0C, 0x28, 0x00]))
        self.assertEqual(logic.messages, ("SAME AGI CONFORMANCE",))

    def test_bundled_logic_runs_each_tick(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        host = EngineHost(profile, default_registry())
        host.boot()
        for _ in range(4):
            host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"20": 4})
        self.assertEqual(state["flags"], [40])

    def test_variable_and_flag_subset(self) -> None:
        # assignn v1=7; assignv v2=v1; addn v2+=3; set f5; return
        host = self._host(bytes([0x03, 1, 7, 0x04, 2, 1, 0x05, 2, 3, 0x0C, 5, 0]))
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"1": 7, "2": 10})
        self.assertEqual(state["flags"], [5])

    def test_corrupt_save_payload_fails_closed(self) -> None:
        host = self._host(bytes([0x00]))
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["flags"] = [256]
        with self.assertRaises(SaveFormatError):
            host.engine.load_state(
                host.context, json.dumps(payload).encode("utf-8")
            )

    def test_stop_sound_routes_normalized_audio(self) -> None:
        host = self._host(bytes([0x64, 0x00]))
        host.tick()
        self.assertEqual(
            host.services.audio.command_history[-1],
            {"command": "sfx_stop", "sound": None},
        )
        self.assertEqual(host.services.events.ring.stats.rejected, 0)

    def test_unknown_opcode_fails_loudly(self) -> None:
        host = self._host(bytes([0xFF]))
        with self.assertRaises(EngineExecutionError):
            host.tick()


if __name__ == "__main__":
    unittest.main()
