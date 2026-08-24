from __future__ import annotations

from pathlib import Path
import unittest

from same.capabilities import DEFAULT_HOST_CAPABILITIES, EngineCapability
from same.engine import EngineHost
from same.engines import default_registry
from same.errors import ResourceError, SaveFormatError
from same.profile import load_profile
from same.savegame import SaveEnvelope
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s4_conformance.json"
ROOM0_HASH = "76ea35578bf6b728b5f2c146e4f17fa82d44e76c16ac1871d2f249b56055c354"
ROOM1_HASH = "6326908ed78174b3bd747d9d822132985bcf2af3fbc6bb164cfabe9a87c78c70"
SCORE_HASH = "c428d02fd1848e55d4a5ea502f41b611d91f526267a808a612c29d7d8a675838"


def make_host(capabilities: EngineCapability = DEFAULT_HOST_CAPABILITIES) -> EngineHost:
    profile = load_profile(PROFILE)
    services = HostServices.create(profile, capabilities=capabilities)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    return host


class ScummV5AudioSaveTests(unittest.TestCase):
    def test_score_intent_is_exact_across_negotiated_backends(self) -> None:
        accelerated = make_host()
        baseline = make_host(
            DEFAULT_HOST_CAPABILITIES
            & ~EngineCapability.CHIP_AUDIO
            & ~EngineCapability.MSU1_STREAM
        )
        accelerated.tick()
        baseline.tick()
        fast = accelerated.engine.inspect_state()["audio"]
        slow = baseline.engine.inspect_state()["audio"]
        self.assertEqual(fast["backend"], "curated_tad")
        self.assertEqual(slow["backend"], "score_interpreter")
        for state in (fast, slow):
            self.assertEqual(state["music"], 7)
            self.assertEqual(state["music_position"], 1)
            self.assertEqual(state["sfx"], {9: 1})
            self.assertEqual(state["speech"], 5)
            self.assertEqual(state["speech_position"], 1)
            self.assertEqual(state["scores"]["7"]["sha256"], SCORE_HASH)
            self.assertEqual(state["scores"]["7"]["events"], 6)

        commands = accelerated.services.audio.command_history
        self.assertEqual([item["command"] for item in commands], [
            "speech_play", "music_play", "sfx_play"
        ])
        self.assertEqual(commands[1]["resource"], "score.s4")
        self.assertEqual(commands[2]["pan"], 96)
        self.assertEqual(commands[2]["priority"], 4)

    def test_complete_state_restores_across_room_transition(self) -> None:
        host = make_host()
        host.tick()
        self.assertEqual(host.services.video.surface.hash(), ROOM0_HASH)
        saved = host.save(0)
        saved_state = host.engine.inspect_state()

        host.tick()
        self.assertEqual(host.engine.inspect_state()["room"], 1)
        self.assertEqual(host.services.video.surface.hash(), ROOM1_HASH)
        self.assertEqual(host.engine.inspect_state()["audio"]["music_position"], 2)

        host.load(0)
        restored = host.engine.inspect_state()
        self.assertEqual(restored["room"], 0)
        self.assertEqual(host.services.video.surface.hash(), ROOM0_HASH)
        self.assertEqual(restored["variables"], saved_state["variables"])
        self.assertEqual(restored["scripts"], saved_state["scripts"])
        self.assertEqual(restored["camera"], saved_state["camera"])
        self.assertEqual(restored["cursor"], saved_state["cursor"])
        self.assertEqual(restored["audio"]["music_position"], 1)
        self.assertEqual(restored["audio"]["sfx"], {9: 1})
        self.assertEqual(restored["audio"]["speech_position"], 1)
        self.assertEqual(saved.schema, 2)

    def test_envelope_identity_schema_and_crc_fail_before_engine_load(self) -> None:
        host = make_host()
        host.tick()
        envelope = host.save(0)
        payload = envelope.payload
        cases = (
            SaveEnvelope("scumm_v5", "another-game", 2, payload).pack(),
            SaveEnvelope("scumm_v5", host.profile.game_id, 1, payload).pack(),
            bytes(bytearray(envelope.pack())[:-1] + bytes([envelope.pack()[-1] ^ 0xFF])),
        )
        patterns = ("belongs to game", "schema 1", "CRC mismatch")
        for slot, (raw, pattern) in enumerate(zip(cases, patterns), 10):
            host.services.saves.write(slot, raw)
            before = host.engine.inspect_state()
            with self.assertRaisesRegex(SaveFormatError, pattern):
                host.load(slot)
            self.assertEqual(host.engine.inspect_state(), before)

    def test_corrupt_score_fails_closed(self) -> None:
        raw = (ROOT / "examples/resources/scumm_v5/s4_score.json").read_bytes()
        from same.engines.scumm_v5 import SameScore
        with self.assertRaisesRegex(ResourceError, "time ordered"):
            SameScore.decode(raw.replace(b'"tick":6', b'"tick":1', 1), "bad.score")


if __name__ == "__main__":
    unittest.main()
