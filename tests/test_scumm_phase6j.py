from pathlib import Path
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.engines.scumm_v5.engine import ActorState
from same.engines.scumm_v5.room import decode_room
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]


class Phase6JTests(unittest.TestCase):
    def test_authentic_destination_uses_actor_adjustment(self) -> None:
        path = ROOT / "build/m23a-rooms/authentic/room-49.sc5c"
        if not path.is_file():
            self.skipTest("user-generated authentic room record unavailable")
        record = decode_cooked_room(path.read_bytes(), expected_room=49)
        room = decode_room(record.room_payload, key="room.49")
        self.assertEqual(room.adjust_actor_point_v5(28, 38), ((31, 38), 1))

    def test_target_dispatches_complete_family_to_one_shared_walker(self) -> None:
        source = (ROOT / "runtime/snes/engines/scumm_v5_matrix_far.pasm").read_text()
        self.assertIn("and #$1F\n    cmp #$1E", source)
        self.assertIn("ScummV5_WalkActorTo_FarEntry:", source)
        self.assertIn("jsr ScummV5_Movement_StartNormalized_Far", source)
        self.assertEqual(source.count("ScummV5_Movement_UpdateActor_Far:"), 1)
        body = source[
            source.index("ScummV5_WalkActorTo_FarEntry:"):
            source.index("ScummV5_WalkActorToObject_FarEntry:")
        ]
        for forbidden in ("room 49", "LSCR 211", "#28", "#38"):
            self.assertNotIn(forbidden, body)

    def test_host_uses_word_coordinate_decoder(self) -> None:
        source = (ROOT / "src/same/engines/scumm_v5/engine.py").read_text()
        start = source.index("def _op_walk_actor_to(")
        body = source[start:source.index("def _op_walk_actor_to_object(", start)]
        self.assertEqual(body.count("_word_for_flags"), 2)
        self.assertNotIn("_byte_operand_for_flags(slot, flags, 0x40)", body)
        self.assertNotIn("_byte_operand_for_flags(slot, flags, 0x20)", body)

    def test_authentic_host_walk_and_wait_oracle(self) -> None:
        path = ROOT / "build/m23a-rooms/authentic/room-49.sc5c"
        if not path.is_file():
            self.skipTest("user-generated authentic room record unavailable")
        record = decode_cooked_room(path.read_bytes(), expected_room=49)
        program = bytes.fromhex("9e 01 00 1c 00 26 00 ae 81 01 00 00")
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": program, "room.0": record.room_payload},
            kinds={"script.boot": "SCRP", "room.0": "ROOM"},
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.engine.state.variables[1] = 1
        host.engine.state.actors[1] = ActorState(
            room=0, position=(57, 46), walkbox=1, facing=270,
        )
        trace = []
        for _ in range(5):
            host.tick()
            actor = host.engine.state.actors[1]
            trace.append((actor.position, actor.walkbox, actor.moving, actor.facing))
        self.assertEqual(trace, [
            ((50, 44), 1, 10, 270),
            ((44, 42), 1, 10, 270),
            ((37, 40), 1, 10, 270),
            ((31, 38), 1, 0, 270),
            ((31, 38), 1, 0, 270),
        ])
        self.assertEqual(host.engine.state.scripts[0].pc, len(program))


if __name__ == "__main__":
    unittest.main()
