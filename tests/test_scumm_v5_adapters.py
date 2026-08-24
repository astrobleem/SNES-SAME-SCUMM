from __future__ import annotations

from pathlib import Path
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import (
    LucasartsScummV5ResourceProvider,
    parse_game_policy,
)
from same.errors import ResourceError
from same.input import SnesButton
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s2_conformance.json"
RESOURCE_ROOT = ROOT / "examples/resources/scumm_v5"


class ScummV5AdapterTests(unittest.TestCase):
    def test_raw_provider_exposes_exact_stable_resources(self) -> None:
        profile = load_profile(PROFILE)
        policy = parse_game_policy(profile)
        assert policy is not None
        backing = HostServices.create(profile).resources
        provider = LucasartsScummV5ResourceProvider(backing, policy)

        self.assertIn("room.1", provider.keys())
        self.assertEqual(provider.read("room.1"), b"S2-ROOM-PAYLOAD")
        self.assertEqual(provider.read("script.1"), bytes((0x80, 0x18, 0xFC, 0xFF)))
        self.assertEqual(provider.read("script.2", 1, 2), bytes((0x2A, 0x00)))
        self.assertEqual(provider.read("sound.1"), b"S2-SOUND-PAYLOAD")
        self.assertEqual(provider.read("costume.1"), b"S2-COSTUME-PAYLOAD")
        self.assertEqual(provider.read("charset.1"), b"S2-CHARSET-PAYLOAD")
        self.assertEqual(provider.stat("script.1").kind, "SCRP")
        self.assertEqual(provider.stat("room.1").kind, "ROOM")
        self.assertIn("#SOUN[1]", provider.stat("sound.1").source)
        self.assertEqual(provider.stat("costume.1").kind, "COST")
        self.assertEqual(provider.stat("charset.1").kind, "CHAR")
        self.assertNotIn("costume.2", provider.keys())
        self.assertFalse(provider.contains("costume.2"))

    def test_raw_provider_fails_closed_on_truncated_index(self) -> None:
        profile = load_profile(PROFILE)
        policy = parse_game_policy(profile)
        assert policy is not None
        index = (RESOURCE_ROOT / "s2_index.000").read_bytes()
        data = (RESOURCE_ROOT / "s2_data.001").read_bytes()
        backing = MemoryResourceProvider(
            {"game.index": index[:-1], "game.data": data}
        )
        with self.assertRaisesRegex(ResourceError, "beyond"):
            LucasartsScummV5ResourceProvider(backing, policy)

    def test_engine_mounts_raw_provider_and_consumes_logical_events(self) -> None:
        profile = load_profile(PROFILE)
        services = HostServices.create(profile)
        host = EngineHost(profile, default_registry(), services=services)
        host.boot()
        self.assertIsInstance(host.services.resources, LucasartsScummV5ResourceProvider)

        host.tick(
            input_word=int(SnesButton.RIGHT | SnesButton.B),
            pointer=(319, 199),
            pointer_buttons=((0, True),),
            text="look",
        )
        state = host.engine.inspect_state()
        self.assertEqual(state["cursor"], [319, 199])
        self.assertEqual(
            state["input"],
            {
                "frame": 0,
                "cursor": [319, 199],
                "held_buttons": ["primary"],
                "pressed_buttons": ["primary"],
                "released_buttons": [],
                "commands": [],
                "text": ["look"],
                "quit_requested": False,
            },
        )
        # Logical SCUMM coordinates remain 320x200.  Physical projection stays
        # owned and clamped by the 256x224 video backend.
        self.assertEqual(
            [host.services.video.cursor.x, host.services.video.cursor.y], [255, 199]
        )

        host.tick(
            input_word=int(SnesButton.START),
            pointer_buttons=((0, False),),
        )
        state = host.engine.inspect_state()["input"]
        self.assertEqual(state["released_buttons"], ["primary"])
        self.assertEqual(state["commands"], ["menu"])
        self.assertEqual(state["text"], [])

        host.tick()
        state = host.engine.inspect_state()["input"]
        self.assertEqual(state["released_buttons"], [])
        self.assertEqual(state["commands"], [])


if __name__ == "__main__":
    unittest.main()
