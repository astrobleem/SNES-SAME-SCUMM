from __future__ import annotations

from pathlib import Path
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s5_conformance.json"


class ScummV5S5BindingTests(unittest.TestCase):
    def test_two_tick_semantic_and_service_trace(self) -> None:
        host = EngineHost(load_profile(PROFILE), default_registry())
        host.boot()
        first = host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(first.operations, 4)
        self.assertTrue(first.yielded)
        self.assertEqual(state["scripts"][0]["pc"], 10)
        self.assertEqual(state["variables"], {"0": 0x1234})
        self.assertEqual(host.services.audio.music_track, 7)
        self.assertEqual(host.services.audio.sfx_history[-1]["sound"], 9)

        audio_packets = [
            packet
            for packet in host.services.packet_history
            if packet["service_name"] == "AUDIO"
        ]
        self.assertEqual(
            [(packet["opcode_name"], packet["arg0"]) for packet in audio_packets],
            [("MUSIC_PLAY", 7), ("SFX_PLAY", 9)],
        )

        second = host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(second.operations, 3)
        self.assertTrue(second.halted)
        self.assertEqual(state["scripts"][0]["pc"], 14)
        self.assertIsNone(host.services.audio.music_track)
        audio_packets = [
            packet
            for packet in host.services.packet_history
            if packet["service_name"] == "AUDIO"
        ]
        self.assertEqual(
            [(packet["opcode_name"], packet["arg0"]) for packet in audio_packets],
            [
                ("MUSIC_PLAY", 7),
                ("SFX_PLAY", 9),
                ("SFX_STOP", 9),
                ("MUSIC_STOP", 0),
            ],
        )
        self.assertEqual(host.services.events.ring.stats.dropped, 0)
        self.assertEqual(host.services.events.ring.stats.rejected, 0)


if __name__ == "__main__":
    unittest.main()
