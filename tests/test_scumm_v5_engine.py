from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.engine import ActorState, RoomObjectState, ScriptSlot
from same.errors import EngineExecutionError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
ROOM = (ROOT / "examples/resources/scumm_v5/room0.sc5r").read_bytes()


class ScummV5EngineTests(unittest.TestCase):
    def _host(
        self,
        script: bytes,
        *,
        max_ops: int | None = None,
        scripts: dict[int, bytes] | None = None,
        resources: dict[str, bytes] | None = None,
        include_room_zero: bool = True,
    ) -> EngineHost:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        if max_ops is not None:
            profile = replace(profile, max_ops_per_tick=max_ops)
        payloads = {"script.boot": script}
        kinds = {"script.boot": "SCRP"}
        if include_room_zero:
            payloads["room.0"] = ROOM
            kinds["room.0"] = "ROOM"
        for number, program in (scripts or {}).items():
            payloads[f"script.{number}"] = program
            kinds[f"script.{number}"] = "SCRP"
        for key, data in (resources or {}).items():
            payloads[key] = data
            kinds[key] = "DATA"
        resources = MemoryResourceProvider(payloads, kinds=kinds)
        services = HostServices.create(profile, resources=resources)
        host = EngineHost(profile, default_registry(), services=services)
        host.boot()
        return host

    def test_bundled_real_opcode_loop(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/boot.scrp").read_bytes()
        host = self._host(script)
        for _ in range(5):
            host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"20": 5})
        self.assertEqual(state["room"], 0)
        self.assertEqual(host.services.audio.music_track, 1)

    def test_c22_room_zero_is_a_resource_less_null_scene_and_saves(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c22_null_room.scrp").read_bytes()
        host = self._host(
            script,
            resources={"room.1": ROOM},
            include_room_zero=False,
        )

        host.tick()
        self.assertEqual(host.engine.inspect_state()["room"], 0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["room"], 1)
        host.engine.state.room_objects[100] = RoomObjectState(100, 8, 16, 24, 32, 40, 48, 1)
        host.engine.state.object_states[100] = 1
        host.engine.state.object_draw_queue.append(100)

        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["room"], 0)
        self.assertIsNone(state["video"])
        self.assertEqual(state["room_objects"], {})
        self.assertEqual(state["object_draw_queue"], [])
        self.assertEqual(state["object_states"], {"100": 1})
        self.assertEqual(set(host.services.video.surface.pixels), {0})

        saved = host.save(0)
        host.engine.state.current_room = 77
        host.engine.state.room_objects[101] = RoomObjectState(101, 0, 0, 8, 8, 0, 0)
        host.load(0)
        restored = host.engine.inspect_state()
        self.assertEqual(restored["room"], 0)
        self.assertIsNone(restored["video"])
        self.assertEqual(restored["room_objects"], {})

    def test_c22_missing_nonzero_room_still_fails_closed(self) -> None:
        host = self._host(bytes((0x72, 2)), include_room_zero=False)
        with self.assertRaisesRegex(EngineExecutionError, "room 2 has no resource binding"):
            host.tick()

    def test_c23_print_slots_text_font_projection_and_save(self) -> None:
        font = (ROOT / "examples/resources/scumm_v5/s3_font.char").read_bytes()
        script = bytes((
            0x1A, 10, 0, 253, 0,       # v10 = actor 253 -> text slot 2
            0x14, 252,                 # direct actor -> text slot 3
            0x00, 50, 0, 16, 0,       # at(50, 16)
            0x01, 31,                  # color 31
            0x04,                      # center
            0x0F, ord("S"), 0,        # emit text
            0x94, 10, 0,              # variable actor 253
            0x00, 70, 0, 20, 0,       # configure defaults only
            0x07, 0xFF,                # overhead; saveDefault
            0xD8, 0x0F, ord("F"), 0,  # printEgo through slot 0
            0x00,
        ))
        host = self._host(script, resources={"charset.0": font})
        before = host.services.video.surface.hash()
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual([item["actor"] for item in state["print"]["messages"]], [252, 1])
        self.assertEqual(state["print"]["messages"][0]["slot"], 3)
        self.assertEqual(state["print"]["messages"][0]["position"], [50, 16])
        self.assertTrue(state["print"]["messages"][0]["center"])
        self.assertEqual(state["print"]["slots"][2]["position"], [70, 20])
        self.assertTrue(state["print"]["slots"][2]["overhead"])
        self.assertNotEqual(host.services.video.surface.hash(), before)

        assert host.context is not None
        saved = host.engine.save_state(host.context)
        host.engine.state.print_messages.clear()
        host.engine.load_state(host.context, saved)
        self.assertEqual(host.engine.inspect_state()["print"], state["print"])

    def test_c23_print_fails_closed_on_erase_and_voice(self) -> None:
        for script, message in (
            (bytes((0x14, 1, 0x03, 4, 0, 5, 0)), "print erase 4x5"),
            (bytes((0x14, 1, 0x08, 4, 0, 5, 0)), "sayVoice 4/5"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_arithmetic_subset_uses_real_opcode_numbers(self) -> None:
        script = bytes(
            [
                0x1A, 0x01, 0x00, 0x0A, 0x00,  # move v1 = 10
                0x5A, 0x01, 0x00, 0x05, 0x00,  # add v1 += 5
                0x1B, 0x01, 0x00, 0x03, 0x00,  # multiply v1 *= 3
                0x00,
            ]
        )
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["variables"], {"1": 45})

    def test_independent_core_fixture_has_exact_five_frame_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/core_conformance.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (40, 0, True, True, {"1": 12, "2": 0x1111}, 7),
            (47, 2, True, True, {"1": 13, "2": 0x1111}, 9),
            (47, 1, True, True, {"1": 13, "2": 0x1111}, 9),
            (47, 0, True, True, {"1": 13, "2": 0x1111}, 9),
            (61, 0, False, False, {"1": 13, "2": 0x1111, "3": 13}, 12),
        ]
        for pc, delay, active, yielded, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual(slot["pc"], pc)
            self.assertEqual(slot["delay"], delay)
            self.assertEqual(slot["active"], active)
            self.assertEqual(slot["yielded"], yielded)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c2_extended_fixture_has_exact_signed_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c2_extended.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (96, 2, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (96, 1, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (96, 0, True, True, {"1": 13, "2": -2, "3": 0x1111, "5": 2}, 17),
            (102, 0, False, False, {"1": 13, "2": -2, "3": 0x1111, "5": 2, "6": 13}, 19),
        ]
        for pc, delay, active, yielded, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual((slot["pc"], slot["delay"], slot["active"], slot["yielded"]), (pc, delay, active, yielded))
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c2_failure_fixtures_fail_closed(self) -> None:
        cases = {
            "unknown_opcode": r"opcode \$2F is not implemented",
            "bad_variable": "variable 2048 is outside",
            "truncated_operand": "ended at offset 1",
            "division_by_zero": "division by zero",
            "jump_escape": "jump leaves script",
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                script = (ROOT / f"examples/resources/scumm_v5/c2_{name}.scrp").read_bytes()
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        budget = (ROOT / "examples/resources/scumm_v5/c2_budget_exhaustion.scrp").read_bytes()
        with self.assertRaisesRegex(EngineExecutionError, "exhausted the per-tick opcode budget"):
            self._host(budget, max_ops=32).tick()

    def test_c2_delay_range_documents_host_24_bit_support(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c2_delay_range.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        slot = host.engine.inspect_state()["scripts"][0]
        self.assertEqual(slot["delay"], 0x10000)
        self.assertTrue(slot["yielded"])

    def test_c3_indexed_results_variable_operands_and_wrap_trace(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c3_operands.scrp").read_bytes()
        host = self._host(script)
        expected = [
            (35, True, {"0": 2, "1": -32768, "2": 1, "6": 5, "7": 0x1234}, 7),
            (41, True, {"0": 2, "1": 32767, "2": 1, "6": 5, "7": 0x1234}, 9),
            (134, False, {"0": 2, "1": 4681, "2": 1, "3": 7, "4": 255, "5": 255, "6": 6, "7": 0x1234}, 26),
        ]
        for pc, active, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            slot = state["scripts"][0]
            self.assertEqual((slot["pc"], slot["active"]), (pc, active))
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c3_bit_variable_result_is_supported(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c3_bit_variable.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], [0])

    def test_c7_cursor_command_and_bit_variables_are_exact_and_saved(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c7_cursor_bits.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["bits"], [5])
        self.assertEqual(state["variables"], {"0": 1, "1": 7, "52": 1, "53": 1})
        self.assertEqual(
            state["cursor_command"],
            {
                "state": 1,
                "user_input": 1,
                "image": [3, 4],
                "hotspot": [3, 5, 6],
                "cursor_id": 9,
                "charset_id": 7,
                "charset_colors": [10, 7],
            },
        )
        saved = host.save(0)
        host.engine.state.bit_variables[5] = False
        host.engine.state.charset_colors.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["bits"], [5])
        self.assertEqual(host.engine.inspect_state()["cursor_command"]["charset_colors"], [10, 7])

    def test_c8_string_ops_preserve_controls_copy_mutate_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c8_string_ops.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        expected_raw = [0x41, 0x5A, 0xFF, 0x04, 0x34, 0x12, 0x43, 0x00]
        self.assertEqual(state["variables"], {"0": 5, "1": 1, "2": 90, "3": 12, "4": 66, "5": 90, "6": 4})
        self.assertEqual(state["strings"]["5"]["raw"], expected_raw)
        self.assertEqual(state["strings"]["6"]["raw"], expected_raw)
        self.assertNotIn("7", state["strings"])
        self.assertEqual(
            state["strings"]["5"]["tokens"],
            [
                {"kind": "glyph", "code": 0x41},
                {"kind": "glyph", "code": 0x5A},
                {"kind": "control", "code": 4, "arguments": [0x34, 0x12]},
                {"kind": "glyph", "code": 0x43},
            ],
        )
        saved = host.save(0)
        host.engine.state.strings[5][0] = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["strings"]["5"]["raw"], expected_raw)

    def test_c8_string_ops_fail_closed_on_malformed_or_missing_state(self) -> None:
        cases = (
            ("unknown sub-op", bytes((0x27, 0x00)), r"sub-op 0 is not implemented"),
            ("identical copy", bytes((0x27, 0x02, 5, 5)), r"source and destination are identical"),
            ("missing get", bytes((0x27, 0x04, 0, 0, 5, 0)), r"string 5 does not exist"),
            ("missing set", bytes((0x27, 0x03, 5, 0, 65)), r"string 5 does not exist"),
            ("truncated control", bytes((0x27, 0x01, 5, 0xFF, 4, 0x34)), r"ended at offset 6"),
            (
                "oversized encoded string",
                bytes((0x27, 0x01, 5)) + b"A" * 255 + b"\0",
                r"encoded string exceeds 255 bytes",
            ),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c8_out_of_bounds_character_access_matches_v5(self) -> None:
        # create(5, 2), ignored set at index 2, get index 2 -> zero.
        script = bytes((0x27, 0x05, 5, 2, 0x27, 0x03, 5, 2, 90,
                        0x27, 0x04, 0, 0, 5, 2, 0x80))
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {})
        self.assertEqual(state["strings"]["5"]["raw"], [0, 0])

    def test_c9_set_var_range_byte_word_indexed_local_and_bits(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c9_set_var_range.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(
            state["variables"],
            {"0": 2, "6": 1, "7": 255, "8": 128},
        )
        self.assertEqual(state["scripts"][0]["locals"][:3], [-1, 32767, -32768])
        self.assertEqual(state["bits"], [6, 7])

    def test_c9_zero_count_assigns_256_values(self) -> None:
        script = bytes((0x26, 0x00, 0x80, 0x00)) + bytes([1]) * 256 + bytes((0x80,))
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], list(range(256)))

    def test_c9_bit_range_wraps_its_packed_index(self) -> None:
        host = self._host(bytes((0x26, 0xFF, 0x8F, 0x02, 1, 1, 0x80)))
        host.tick()
        self.assertEqual(host.engine.inspect_state()["bits"], [0, 4095])

    def test_c9_set_var_range_fails_closed_on_truncation_and_boundaries(self) -> None:
        cases = (
            ("missing count", bytes((0x26, 0x00, 0x00)), r"ended at offset 3"),
            ("truncated byte values", bytes((0x26, 0x00, 0x00, 0x02, 0x01)), r"ended at offset 5"),
            ("truncated word values", bytes((0xA6, 0x00, 0x00, 0x01, 0x34)), r"ended at offset 4"),
            ("global boundary", bytes((0x26, 0xFF, 0x07, 0x02, 1, 2)), r"variable 2048 is outside"),
            ("local boundary", bytes((0x26, 0x1F, 0x40, 0x02, 1, 2)), r"local variable 32 is outside"),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c10_room_ops_intents_palette_auxiliary_string_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c10_room_ops.scrp").read_bytes()
        host = self._host(script)
        host.engine.state.room_ops.room_width = 640
        host.tick()
        state = host.engine.inspect_state()
        room = state["room_ops"]
        self.assertEqual(room["scroll"], [160, 480])
        self.assertEqual(room["screen"], [16, 184])
        self.assertTrue(room["shake"])
        self.assertEqual(room["scale_slots"], {"1": [100, 20, 200, 180]})
        self.assertEqual(room["intensity"], [128, 128, 128, 4, 9])
        self.assertEqual(room["fade_effect"], 0x1234)
        self.assertEqual(room["rgb_intensity"], [100, 110, 120, 2, 8])
        self.assertEqual(room["shadow"], [50, 60, 70, 3, 9])
        self.assertEqual(room["transform"], [6, 2, 10, 12])
        self.assertEqual(room["cycle_delays"][2], 107)
        self.assertEqual(room["palette_overrides"], {"7": [10, 20, 30]})
        self.assertEqual(room["save_load_request"], [1, 99])
        self.assertEqual(room["auxiliary_files"], {"aux": [65, 66, 67, 0]})
        self.assertEqual(state["strings"]["5"]["raw"], [65, 66, 67, 0])
        self.assertEqual(host.services.video.surface.palette[7], (10, 20, 30))

        saved = host.save(0)
        host.engine.state.room_ops.palette_overrides.clear()
        host.engine.state.room_ops.auxiliary_files.clear()
        host.engine.state.room_ops.shake_enabled = False
        host.load(0)
        restored = host.engine.inspect_state()["room_ops"]
        self.assertTrue(restored["shake"])
        self.assertEqual(restored["auxiliary_files"], {"aux": [65, 66, 67, 0]})
        self.assertEqual(host.services.video.surface.palette[7], (10, 20, 30))
        self.assertEqual(saved.schema, 2)

        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["room_ops"]["auxiliary_files"] = {"\u2603": "00"}
        with self.assertRaises(SaveFormatError):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c10_room_ops_variable_operands(self) -> None:
        script = bytes((
            0x1A, 0x00, 0x00, 0x03, 0x00,
            0x1A, 0x01, 0x00, 0x02, 0x00,
            0x33, 0xD0, 0x00, 0x00, 0x01, 0x00,
            0x80,
        ))
        host = self._host(script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["room_ops"]["cycle_delays"][2], 107)

    def test_c10_room_ops_fail_closed(self) -> None:
        cases = (
            ("unknown", bytes((0x33, 0)), r"sub-op 0 is not implemented"),
            ("v3 room color", bytes((0x33, 2)), r"room-color is invalid for v5"),
            ("empty filename", bytes((0x33, 0x0E, 5, 0)), r"filename is empty"),
            ("missing save string", bytes((0x33, 0x0D, 5, 65, 0)), r"string 5 does not exist"),
            ("bad scale slot", bytes((0x33, 7, 1, 2, 0, 3, 4, 0, 0)), r"scale slot 0 is outside"),
            ("reversed intensity", bytes((0x33, 8, 1, 9, 4)), r"color range 9..4 is reversed"),
            ("truncated palette", bytes((0x33, 4, 1, 0)), r"ended at offset"),
        )
        for name, script, message in cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c11_random_direct_variable_inclusive_and_saved(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c11_random.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(
            {key: state["variables"][key] for key in ("0", "1", "2", "4")},
            {"0": 9, "1": 6, "2": 3, "4": 28},
        )
        self.assertNotIn("3", state["variables"])
        self.assertEqual(state["scripts"][0]["locals"][0], 4)
        self.assertEqual(state["random_state"], 0x0E27)

        replay = self._host(bytes((
            0x16, 0x01, 0x00, 10, 0x80,
            0x16, 0x02, 0x00, 10, 0x80,
        )))
        replay.tick()
        saved = replay.save(0)
        replay.tick()
        expected = replay.engine.inspect_state()
        replay.load(0)
        self.assertEqual(replay.engine.inspect_state()["random_state"], 0xE270)
        replay.tick()
        replayed = replay.engine.inspect_state()
        for key in ("variables", "scripts", "random_state", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 2)

    def test_c11_random_fails_closed_on_malformed_operands_and_state(self) -> None:
        cases = (
            (bytes((0x16, 0x01)), r"ended at offset"),
            (bytes((0x16, 0x00, 0x08, 1)), r"variable 2048 is outside"),
            (bytes((0x16, 0x01, 0x00)), r"ended at offset"),
            (bytes((0x96, 0x01, 0x00, 0x00)), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["random_state"] = 0
        with self.assertRaisesRegex(SaveFormatError, "random state"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c12_pseudo_room_maps_overwrites_resolves_and_saves(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c12_pseudo_room.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        mapper = host.engine.inspect_state()["resource_mapper"]
        self.assertEqual((mapper[0], mapper[1], mapper[2], mapper[127]), (0x12, 0x12, 0, 0x12))

        saved = host.save(0)
        host.tick()
        expected = host.engine.inspect_state()
        mapper = expected["resource_mapper"]
        self.assertEqual((mapper[0], mapper[1], mapper[2], mapper[127]), (0x12, 0x34, 0x34, 0x12))
        host.engine.state.resource_mapper[1] = 0x99
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("resource_mapper", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 2)

        resolving = self._host(bytes((0xCC, 0, 0x80, 0, 0x72, 0x80, 0)))
        resolving.tick()
        self.assertEqual(resolving.engine.inspect_state()["room"], 0)

    def test_c12_pseudo_room_fails_closed_on_unterminated_list_and_bad_state(self) -> None:
        for script in (bytes((0xCC,)), bytes((0xCC, 1)), bytes((0xCC, 1, 0x80))):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, r"ended at offset"):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        for value in ([0] * 127, [0] * 127 + [256]):
            with self.subTest(value=value[-1]):
                malformed["resource_mapper"] = value
                with self.assertRaisesRegex(SaveFormatError, "resource mapper"):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c13_resource_routines_intent_mapping_variables_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c13_resource_routines.scrp").read_bytes()
        resources = {
            "script.5": b"\x00",
            "sound.6": b"sound-six",
            "sound.8": b"sound-eight",
            "costume.7": b"costume-seven",
            "room.42": b"room-forty-two",
            "charset.1": b"charset-one",
        }
        host = self._host(fixture, resources=resources)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 32)
        self.assertEqual(
            first["resource_ops"]["loaded"],
            {
                "script": [5], "sound": [6], "costume": [7],
                "room": [42], "charset": [1],
            },
        )
        self.assertEqual(
            first["resource_ops"]["locked"],
            {"script": [5], "sound": [6], "costume": [7], "room": [42]},
        )
        saved = host.save(0)

        host.tick()
        expected = host.engine.inspect_state()
        self.assertEqual(expected["scripts"][0]["pc"], 76)
        self.assertEqual(
            expected["resource_ops"],
            {
                "loaded": {
                    "script": [], "sound": [8], "costume": [],
                    "room": [42], "charset": [],
                },
                "locked": {"script": [], "sound": [], "costume": [], "room": []},
                "last_object": [42, 0x1234],
            },
        )
        host.engine.state.resource_ops.loaded["sound"].clear()
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("resource_ops", "resource_mapper", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 2)

    def test_c13_resource_routines_fail_closed_on_operands_resources_and_state(self) -> None:
        cases = (
            (bytes((0x0C,)), r"ended at offset"),
            (bytes((0x0C, 1)), r"ended at offset"),
            (bytes((0x0C, 0)), r"sub-op 0"),
            (bytes((0x0C, 21, 0)), r"sub-op 21"),
            (bytes((0x0C, 0x81, 0x00)), r"ended at offset"),
            (bytes((0x0C, 20, 0)), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()
        with self.assertRaisesRegex(EngineExecutionError, r"unknown resource 'sound.9'"):
            self._host(bytes((0x0C, 2, 9))).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["resource_ops"]["loaded"]["sound"] = [256]
        with self.assertRaisesRegex(SaveFormatError, "resource loaded id"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c14_actor_ops_full_header_state_variables_defaults_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c14_actor_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        actor1 = first["actors"]["1"]
        self.assertEqual(actor1["costume"], 7)
        self.assertEqual(actor1["walk_speed"], [3, 4])
        self.assertEqual(actor1["sound"], 5)
        self.assertEqual(actor1["frames"], [16, 17, 18, 19, 20])
        self.assertEqual(actor1["elevation"], -2)
        self.assertEqual(actor1["palette"], {"2": 33})
        self.assertEqual(actor1["talk_color"], 34)
        self.assertEqual(actor1["name"], list(b"Actor One\0"))
        self.assertEqual((actor1["width"], actor1["scale"], actor1["box_scale"]), (35, [36, 37], 36))
        self.assertEqual((actor1["force_clip"], actor1["ignore_boxes"]), (0, False))
        self.assertEqual((actor1["animation_speed"], actor1["shadow"]), (39, 40))
        saved = host.save(0)

        host.tick()
        expected = host.engine.inspect_state()
        actor2 = expected["actors"]["2"]
        self.assertEqual(actor2["costume"], 55)
        self.assertEqual(actor2["palette"], {"3": 44})
        self.assertEqual(actor2["name"], list(b"Actor Two\0"))
        self.assertEqual(actor2["walk_speed"], [8, 2])
        self.assertEqual(actor2["frames"], [1, 2, 3, 4, 5])
        self.assertEqual((actor2["force_clip"], actor2["ignore_boxes"]), (0, False))
        host.engine.state.actors.clear()
        host.load(0)
        host.tick()
        replayed = host.engine.inspect_state()
        for key in ("actors", "scripts", "operations", "frames"):
            self.assertEqual(replayed[key], expected[key])
        self.assertEqual(saved.schema, 2)

    def test_c14_actor_ops_fail_closed_on_actor_subop_operands_and_state(self) -> None:
        cases = (
            (bytes((0x13,)), r"ended at offset"),
            (bytes((0x13, 32, 0xFF)), r"actor 32"),
            (bytes((0x13, 1)), r"ended at offset"),
            (bytes((0x13, 1, 15)), r"sub-op 15"),
            (bytes((0x13, 1, 11, 32, 0, 0xFF)), r"palette slot"),
            (bytes((0x13, 1, 13, ord("X"))), r"ended at offset"),
        )
        for script, message in cases:
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["actors"] = {"32": {}}
        with self.assertRaisesRegex(SaveFormatError, "actor entry"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["actors"] = {"1": ActorState().to_dict()}
        malformed["actors"]["1"]["ignore_boxes"] = "false"
        with self.assertRaisesRegex(SaveFormatError, "ignore-boxes"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c15_actor_follow_camera_direct_variable_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c15_actor_follow_camera.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 3)
        saved = host.save(0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 7)
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 3)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["camera_follow_actor"], 7)
        self.assertEqual(saved.schema, 2)

    def test_c15_actor_follow_camera_fails_closed(self) -> None:
        for script, message in (
            (bytes((0x52,)), "ended at offset"),
            (bytes((0x52, 32)), "actor 32"),
            (bytes((0xD2, 0x00)), "ended at offset"),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        malformed["camera_follow_actor"] = True
        with self.assertRaisesRegex(SaveFormatError, "camera-follow"):
            host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c16_set_class_direct_variable_clear_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c16_set_class.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        expected = {"42": [5], "300": [2, 5]}
        self.assertEqual(host.engine.inspect_state()["object_classes"], expected)
        saved = host.save(0)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["object_classes"], {"300": [2, 3]})
        host.engine.state.object_classes.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["object_classes"], expected)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["object_classes"], {"300": [2, 3]})
        self.assertEqual(saved.schema, 2)

    def test_c16_set_class_fails_closed_on_stream_class_capacity_and_save(self) -> None:
        for script, message in (
            (bytes((0x5D,)), "ended at offset"),
            (bytes((0x5D, 1, 0, 1, 0x80, 0)), "class 0"),
            (bytes((0x5D, 1, 0, 1, 0xA1, 0)), "class 33"),
            (bytes((0x5D, 1, 0, 1, 0x81, 0)), "ended at offset"),
            (bytes((0xDD, 0)), "ended at offset"),
        ):
            with self.subTest(script=script):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        capacity_script = bytearray()
        for object_id in range(513):
            capacity_script.extend((0x5D, object_id & 0xFF, object_id >> 8, 1, 0x81, 0, 0xFF))
        with self.assertRaisesRegex(EngineExecutionError, "512 modified objects"):
            self._host(bytes(capacity_script), max_ops=1024).tick()

        recovery_script = bytearray(capacity_script[:-7])
        recovery_script.extend((0x5D, 0, 0, 1, 0, 0, 0xFF))
        recovery_script.extend((0x5D, 0, 2, 1, 0x81, 0, 0xFF, 0x80))
        recovered = self._host(bytes(recovery_script), max_ops=1024)
        recovered.tick()
        recovered_classes = recovered.engine.inspect_state()["object_classes"]
        self.assertEqual(len(recovered_classes), 512)
        self.assertNotIn("0", recovered_classes)
        self.assertEqual(recovered_classes["512"], [1])

        host = self._host(bytes((0x80,)))
        assert host.context is not None
        for invalid in (
            {"1": []},
            {"1": [2, 1]},
            {"1": [1, 1]},
            {"1": [33]},
            {"65536": [1]},
            {"01": [1]},
        ):
            malformed = json.loads(host.engine.save_state(host.context).decode("utf-8"))
            malformed["object_classes"] = invalid
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(SaveFormatError, "object-class|object classes"):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c17_verb_ops_complete_surface_delete_new_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c17_verb_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        expected = {
            "5": {
                "color": 6, "hicolor": 7, "dimcolor": 8, "background_color": 9,
                "kind": "text", "charset": 0, "mode": 1, "save_id": 0,
                "key": ord("L"), "center": True, "position": [100, 150],
                "original_left": 100, "image_index": 0, "image_source": None,
                "name": list(b"Look\0"),
            },
            "11": {
                "color": 2, "hicolor": 0, "dimcolor": 8, "background_color": 0,
                "kind": "image", "charset": 0, "mode": 2, "save_id": 0,
                "key": 0, "center": False, "position": [0, 0],
                "original_left": 0, "image_index": 0,
                "image_source": [0, 0x2222], "name": None,
            },
        }
        self.assertEqual(host.engine.inspect_state()["verbs"], expected)
        saved = host.save(0)
        host.tick()
        self.assertEqual(
            host.engine.inspect_state()["verbs"],
            {
                "5": {
                    "color": 2, "hicolor": 0, "dimcolor": 8,
                    "background_color": 9, "kind": "image", "charset": 0,
                    "mode": 0, "save_id": 0, "key": 0, "center": False,
                    "position": [100, 150], "original_left": 100,
                    "image_index": 0x3456, "image_source": [42, 0x3456],
                    "name": list(b"Use\0"),
                }
            },
        )
        host.engine.state.verbs.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["verbs"], expected)
        host.tick()
        self.assertEqual(set(host.engine.state.verbs), {5})
        self.assertEqual(saved.schema, 2)

    def test_c17_verb_ops_fails_closed_on_stream_name_and_save(self) -> None:
        cases = (
            (bytes((0x7A,)), "ended at offset"),
            (bytes((0xFA, 0)), "ended at offset"),
            (bytes((0x7A, 1, 0x0A)), "sub-op 10"),
            (bytes((0x7A, 1, 0x09)), "ended at offset"),
            (bytes((0x7A, 1, 0x09, 0x02, ord("X"))), "ended at offset"),
            (bytes((0x7A, 1, 0x09, 0x02, *([ord("X")] * 64), 0)), "64 bytes"),
        )
        for script, message in cases:
            with self.subTest(script=script[:8]):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        absent = self._host(bytes((0x7A, 2, 0x09, 0x14, 99, 0, 0xFF, 0x80)))
        absent.tick()
        self.assertIsNone(absent.engine.inspect_state()["verbs"]["2"]["name"])

        fixture = (ROOT / "examples/resources/scumm_v5/c17_verb_ops.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        assert host.context is not None
        base = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        mutations = (
            ("01", "verb entry", lambda verb: None),
            ("5", "kind", lambda verb: verb.__setitem__("kind", "sprite")),
            ("5", "center", lambda verb: verb.__setitem__("center", 1)),
            ("5", "coordinate", lambda verb: verb.__setitem__("position", [0x8000, 0])),
            ("5", "name", lambda verb: verb.__setitem__("name", "41")),
        )
        for key, message, mutate in mutations:
            malformed = json.loads(json.dumps(base))
            if key == "01":
                malformed["verbs"][key] = malformed["verbs"].pop("5")
            else:
                mutate(malformed["verbs"][key])
            with self.subTest(key=key, message=message):
                with self.assertRaisesRegex(SaveFormatError, message):
                    host.engine.load_state(host.context, json.dumps(malformed).encode("utf-8"))

    def test_c18_expression_stack_arithmetic_nested_opcode_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c18_expression.scrp").read_bytes()
        host = self._host(fixture)
        first = host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(first.operations, 6)
        self.assertEqual(state["scripts"][0]["pc"], 53)
        self.assertEqual(
            state["variables"],
            {"0": 2, "1": 7, "2": -3, "3": -7, "6": -20536},
        )
        saved = host.save(0)

        second = host.tick()
        terminal = host.engine.inspect_state()
        self.assertEqual(second.operations, 5)
        self.assertEqual(terminal["scripts"][0]["pc"], 93)
        self.assertEqual(terminal["variables"]["0"], 9)
        self.assertEqual(terminal["variables"]["7"], -3)
        self.assertEqual(terminal["scripts"][0]["locals"][0], 13)
        self.assertEqual(terminal["bits"], [6])

        host.load(0)
        host.tick()
        replay = host.engine.inspect_state()
        replay.pop("input")
        terminal.pop("input")
        self.assertEqual(replay, terminal)
        self.assertEqual(saved.schema, 2)

    def test_c18_expression_fails_closed_on_stack_stream_and_nested_opcode(self) -> None:
        overflow = bytes((0xAC, 0, 0)) + bytes((0x01, 1, 0)) * 257 + bytes((0xFF,))
        cases = (
            (bytes((0xAC,)), "ended at offset"),
            (bytes((0xAC, 0, 0, 0x01, 1)), "ended at offset"),
            (bytes((0xAC, 0, 0, 0x02, 0xFF)), "stack underflow"),
            (bytes((0xAC, 0, 0, 0x01, 1, 0, 0x01, 0, 0, 0x05, 0xFF)), "division by zero"),
            (bytes((0xAC, 0, 0, 0x06, 0x2F, 0xFF)), "inside expression"),
            (overflow, "stack overflow"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

    def test_c19_cutscene_nested_override_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c19_cutscene.scrp").read_bytes()
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["scripts"][0]["pc"], 26)
        self.assertEqual(first["scripts"][0]["cutscene_override"], 2)
        self.assertEqual(first["cutscenes"]["stack_pointer"], 2)
        self.assertEqual([item["data"] for item in first["cutscenes"]["records"]], [0x1234, 7])
        self.assertEqual(first["cutscenes"]["records"][1]["override_pc"], 17)
        saved = host.save(0)
        host.engine.state.cutscenes.clear()
        host.engine.state.scripts[0].cutscene_override = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["cutscenes"], first["cutscenes"])
        host.tick()
        terminal = host.engine.inspect_state()
        self.assertEqual(terminal["scripts"][0]["pc"], 31)
        self.assertEqual(terminal["scripts"][0]["cutscene_override"], 0)
        self.assertEqual(terminal["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(terminal["variables"], {"0": 7, "4": 1})
        self.assertEqual(saved.schema, 2)

    def test_c19_cutscene_callbacks_and_skip_override(self) -> None:
        callback_main = bytes(
            [
                0x1A, 35, 0, 10, 0, 0x1A, 36, 0, 11, 0,
                0x1A, 1, 0, 7, 0,
                0x40, 0x01, 0x34, 0x12, 0x81, 1, 0, 0xFF,
                0xC0, 0x80,
            ]
        )
        start = bytes(
            [
                0x9A, 2, 0, 0, 0x40,
                0x9A, 3, 0, 1, 0x40,
                0x60, 1,
                0x00,
            ]
        )
        end = bytes([0x9A, 6, 0, 0, 0x40, 0x00])
        host = self._host(callback_main, scripts={10: start, 11: end})
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["variables"], {"1": 7, "2": 0x1234, "3": 7, "6": 0x1234, "35": 10, "36": 11})
        self.assertEqual(state["scripts"][0]["freeze_count"], 0)
        self.assertEqual(state["cutscenes"]["stack_pointer"], 0)

        skip_script = bytes(
            [
                0x40, 0x01, 0x34, 0x12, 0xFF,
                0x58, 1, 0x18, 8, 0,
                0x80,
                0x1A, 4, 0, 1, 0,
                0x58, 0,
                0xC0,
                0x1A, 8, 0, 9, 0,
                0x80,
            ]
        )
        host = self._host(skip_script)
        host.tick()
        self.assertEqual(host.engine.inspect_state()["scripts"][0]["pc"], 11)
        host.tick(input_word=0x0040)
        skipped = host.engine.inspect_state()
        self.assertEqual(skipped["variables"], {"8": 9})
        self.assertEqual(skipped["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(skipped["scripts"][0]["cutscene_override"], 0)

    def test_c24_zero_depth_override_sentinel_clear_skip_and_save(self) -> None:
        script = bytes((
            0x58, 1, 0x18, 8, 0,
            0x1A, 4, 0, 1, 0,
            0x80,
            0x58, 0,
            0x1A, 8, 0, 9, 0,
            0x80,
        ))
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["cutscenes"]["stack_pointer"], 0)
        self.assertEqual(
            first["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": 2, "override_slot": 0},
        )
        saved = host.save(0)
        host.engine.state.cutscene_sentinel = type(host.engine.state.cutscene_sentinel)()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["cutscenes"], first["cutscenes"])
        legacy_payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        legacy_payload.pop("cutscene_sentinel")
        host.engine.load_state(host.context, json.dumps(legacy_payload).encode("utf-8"))
        self.assertEqual(
            host.engine.inspect_state()["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": None, "override_slot": None},
        )
        host.load(0)

        host.tick(input_word=0x0040)
        skipped = host.engine.inspect_state()
        self.assertEqual(skipped["variables"], {"4": 1, "5": 1, "8": 9})
        self.assertEqual(
            skipped["cutscenes"]["sentinel"],
            {"data": 0, "override_pc": None, "override_slot": None},
        )

        clear = self._host(bytes((0x58, 0, 0x80)))
        clear.tick()
        self.assertEqual(clear.engine.inspect_state()["scripts"][0]["pc"], 3)

    def test_c25_sound_kludge_queue_flush_audio_and_save(self) -> None:
        command = lambda *values: bytes((
            0x4C,
            *(byte for value in values for byte in (0, value & 0xFF, value >> 8 & 0xFF)),
            0xFF,
        ))
        variable_command = bytes((0x4C, 0, 8, 0, 0x80, 0, 0, 0xFF))
        script = b"".join((
            bytes((0x1A, 0, 0, 7, 0)), variable_command, bytes((0x80,)),
            command(0xFFFF), bytes((0x80,)),
            command(9, 7), command(6, 64), command(11), bytes((0x80,)),
            command(0xFFFF), bytes((0x80, 0x00)),
        ))
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["sound_kludge"], {"queue": [[8, 7]], "history": [], "result": 0})
        self.assertEqual(host.services.audio.command_history, [])
        saved = host.save(0)
        host.engine.state.sound_queue.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["sound_kludge"], first["sound_kludge"])

        host.tick()
        self.assertEqual(
            [record["command"] for record in host.services.audio.command_history],
            ["sfx_play", "flush"],
        )
        host.tick()
        self.assertEqual(host.engine.inspect_state()["sound_kludge"]["queue"], [[9, 7], [6, 64], [11]])
        host.tick()
        state = host.engine.inspect_state()["sound_kludge"]
        self.assertEqual(state["queue"], [])
        self.assertEqual(state["history"], [[8, 7], [9, 7], [6, 64], [11]])
        self.assertEqual(host.services.audio.master_volume, 129)
        self.assertEqual(
            [record["command"] for record in host.services.audio.command_history],
            [
                "sfx_play", "flush", "sfx_stop", "master_volume",
                "music_stop", "sfx_stop", "speech_stop", "flush",
            ],
        )

    def test_c25_sound_kludge_fails_closed_on_stream_command_capacity_and_save(self) -> None:
        command = lambda value: bytes((0x4C, 0, value & 0xFF, value >> 8 & 0xFF, 0xFF))
        cases = (
            (bytes((0x4C, 0xFF)), "command is empty"),
            (command(12) + command(0xFFFF) + bytes((0x80,)), "command 12 is not implemented"),
            (bytes((0x4C, 0, 8, 0, 0xFF, 0x4C, 0, 0xFF)), "ended at offset"),
            (command(11) * 17 + bytes((0x80,)), "queue exceeds 16 commands"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(command(11) + bytes((0x80,)))
        host.tick()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["sound_kludge"]["queue"] = [[0x8000]]
        with self.assertRaisesRegex(SaveFormatError, "value must fit s16"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c26_save_restore_verbs_banks_replacement_delete_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c26_save_restore_verbs.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["verbs"], {})
        self.assertEqual(
            [(item["id"], item["bank"], item["verb"]["color"]) for item in first["saved_verbs"]],
            [(1, 5, 3), (2, 5, 4)],
        )
        saved = host.save(0)
        host.engine.state.saved_verbs.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["saved_verbs"], first["saved_verbs"])

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["verbs"]["1"]["color"], 3)
        self.assertEqual([(item["id"], item["bank"]) for item in second["saved_verbs"]], [(2, 5)])
        host.tick()
        third = host.engine.inspect_state()
        self.assertEqual(third["verbs"]["1"]["color"], 3)
        self.assertEqual(third["saved_verbs"], [])
        host.tick()
        self.assertTrue(host.engine.inspect_state()["scripts"][0]["active"] is False)

    def test_c26_save_restore_verbs_fails_closed_on_stream_capacity_and_save(self) -> None:
        cases = (
            (bytes((0xAB, 4, 1, 2, 3, 0x80)), "sub-op 4 is invalid"),
            (bytes((0xAB, 1, 1)), "ended at offset"),
            (bytes((0xAB, 0x81, 1, 2, 3, 0x80)), "sub-op 129 is invalid"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        define = lambda verb_id: bytes((0x7A, verb_id, 9, 0xFF))
        save = lambda verb_id: bytes((0xAB, 1, verb_id, verb_id, 1))
        host = self._host(
            b"".join(define(index) + save(index) for index in range(65)) + bytes((0x80,)),
            max_ops=200,
        )
        with self.assertRaisesRegex(EngineExecutionError, "exceeds 64 saved slots"):
            host.tick()

        valid = self._host(define(1) + save(1) + bytes((0x80,)))
        valid.tick()
        assert valid.context is not None
        payload = json.loads(valid.engine.save_state(valid.context).decode("utf-8"))
        saved_key = next(key for key in payload["verbs"] if ":" in key)
        malformed = (
            {**payload, "verbs": {"1:5:9": payload["verbs"][saved_key]}},
            {**payload, "verbs": {saved_key: {**payload["verbs"][saved_key], "save_id": 0}}},
        )
        for item in malformed:
            with self.assertRaisesRegex(SaveFormatError, "saved-verb identity is invalid"):
                valid.engine.load_state(valid.context, json.dumps(item).encode("utf-8"))

    def test_c28_animate_actor_direct_variable_and_save(self) -> None:
        fixture = (ROOT / "examples/resources/scumm_v5/c28_animate_actor.scrp").read_bytes()
        host = self._host(fixture)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(first["actors"]["10"]["animation"], 250)
        self.assertEqual(first["scripts"][0]["pc"], 4)

        saved = host.save(0)
        host.engine.state.actors[10].animation = 99
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["actors"]["10"]["animation"], 250)

        host.tick()
        second = host.engine.inspect_state()
        self.assertEqual(second["actors"]["10"]["animation"], 6)
        self.assertEqual(second["scripts"][0]["pc"], 20)
        host.tick()
        self.assertFalse(host.engine.inspect_state()["scripts"][0]["active"])

    def test_c28_animate_actor_fails_closed_on_actor_stream_and_save(self) -> None:
        for script, message in (
            (bytes((0x11, 32, 1)), "actor 32 is outside"),
            (bytes((0x11, 10)), "ended at offset"),
            (bytes((0xD1, 0, 0, 1)), "ended at offset"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes((0x11, 10, 1, 0x80)))
        host.tick()
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["actors"]["10"]["animation"] = 256
        with self.assertRaisesRegex(SaveFormatError, "actor scalar must fit u8"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c19_cutscene_fails_closed_on_stack_override_and_save(self) -> None:
        cases = (
            (bytes([0xC0]), "stack underflow"),
            (bytes([0x58, 1, 0x18]), "while reading 3 bytes"),
            (bytes([0x40, 0xFF, 0x58, 1, 0x18]), "while reading 3 bytes"),
            (bytes([0x40, 0xFF]) * 5, "stack overflow"),
            (bytes([0x40, 0xFF, 0x00]), "ended with active cutscene"),
        )
        for script, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(EngineExecutionError, message):
                    self._host(script).tick()

        host = self._host(bytes([0x40, 0xFF, 0x80]))
        host.tick()
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["cutscenes"][0]["override_pc"] = 1
        with self.assertRaisesRegex(SaveFormatError, "override is incomplete"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["cutscene_sentinel"]["override_pc"] = 1
        with self.assertRaisesRegex(SaveFormatError, "override is incomplete"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c20_do_sentence_operands_freeze_cancel_and_save(self) -> None:
        script = bytes(
            [
                0x1A, 0, 0, 7, 0,
                0x1A, 1, 0, 0x11, 0x11,
                0x1A, 2, 0, 0x22, 0x22,
                0x19, 1, 100, 0, 0, 0,
                0x39, 2, 101, 0, 0, 0,
                0x59, 3, 1, 0, 102, 0,
                0x79, 4, 1, 0, 2, 0,
                0x60, 1,
                0x80,
                0x60, 0,
                0x19, 0xFE,
                0x99, 0, 0, 103, 0, 0, 0,
                0xB9, 0, 0, 104, 0, 2, 0,
                0xD9, 0, 0, 1, 0, 105, 0,
                0xF9, 0, 0, 1, 0, 2, 0,
                0x60, 1,
                0x80,
            ]
        )
        host = self._host(script)
        host.tick()
        first = host.engine.inspect_state()
        self.assertEqual(
            first["sentences"],
            [
                {"verb": 1, "object_a": 100, "object_b": 0, "preposition": False, "freeze_count": 1},
                {"verb": 2, "object_a": 101, "object_b": 7, "preposition": True, "freeze_count": 1},
                {"verb": 3, "object_a": 0x1111, "object_b": 102, "preposition": True, "freeze_count": 1},
                {"verb": 4, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
            ],
        )
        saved = host.save(0)
        host.engine.state.sentences.clear()
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["sentences"], first["sentences"])
        host.tick(pointer_buttons=((0, True),))
        second = host.engine.inspect_state()
        self.assertEqual(
            second["sentences"],
            [
                {"verb": 7, "object_a": 103, "object_b": 0, "preposition": False, "freeze_count": 1},
                {"verb": 7, "object_a": 104, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
                {"verb": 7, "object_a": 0x1111, "object_b": 105, "preposition": True, "freeze_count": 1},
                {"verb": 7, "object_a": 0x1111, "object_b": 0x2222, "preposition": True, "freeze_count": 1},
            ],
        )
        self.assertEqual(second["input"]["pressed_buttons"], [])
        self.assertEqual(second["input"]["held_buttons"], ["primary"])
        self.assertEqual(saved.schema, 2)

    def test_c20_sentence_script_lifo_same_object_and_cancel(self) -> None:
        callback = bytes(
            [
                0x9A, 5, 0, 0, 0x40,
                0x9A, 6, 0, 1, 0x40,
                0x9A, 7, 0, 2, 0x40,
                0x00,
            ]
        )
        main = bytes(
            [
                0x1A, 33, 0, 10, 0,
                0x19, 5, 100, 0, 200, 0,
                0x80,
                0x00,
            ]
        )
        host = self._host(main, scripts={10: callback})
        host.tick()
        queued = host.engine.inspect_state()
        sentence_slots = [item for item in queued["scripts"] if item["number"] == 10]
        self.assertEqual(queued["sentences"], [])
        self.assertEqual(sentence_slots[0]["locals"][:3], [5, 100, 200])
        self.assertEqual(sentence_slots[0]["pc"], 0)
        host.tick()
        self.assertEqual(
            host.engine.inspect_state()["variables"],
            {"5": 5, "6": 100, "7": 200, "33": 10},
        )

        same_object = self._host(
            bytes([0x1A, 33, 0, 10, 0, 0x19, 5, 100, 0, 100, 0, 0x80]),
            scripts={10: callback},
        )
        same_object.tick()
        self.assertFalse(any(item["number"] == 10 for item in same_object.engine.inspect_state()["scripts"]))

        cancel = self._host(
            bytes([0x1A, 33, 0, 10, 0, 0x0A, 10, 0xFF, 0x19, 0xFE, 0x80]),
            scripts={10: bytes([0x80])},
        )
        cancel.tick(pointer_buttons=((0, True),))
        canceled = cancel.engine.inspect_state()
        self.assertFalse(any(item["number"] == 10 for item in canceled["scripts"]))
        self.assertEqual(canceled["input"]["pressed_buttons"], [])

    def test_c20_do_sentence_fails_closed_on_stream_capacity_and_save(self) -> None:
        for script in (bytes([0x19]), bytes([0x19, 1, 0]), bytes([0x99, 0])):
            with self.subTest(script=script.hex()):
                with self.assertRaisesRegex(EngineExecutionError, "ended at offset"):
                    self._host(script).tick()
        overflow = bytes([0x19, 1, 1, 0, 0, 0]) * 7
        with self.assertRaisesRegex(EngineExecutionError, "sentence queue overflow"):
            self._host(overflow).tick()

        host = self._host(bytes([0x19, 1, 1, 0, 0, 0, 0x60, 1, 0x80]))
        host.tick()
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["sentences"][0]["preposition"] = True
        with self.assertRaisesRegex(SaveFormatError, "preposition is noncanonical"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c21_draw_object_operands_overlap_position_and_save(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c21_draw_object.scrp").read_bytes()
        host = self._host(script)
        host.engine.state.object_states = {102: 7}
        host.engine.state.room_objects = {
            100: RoomObjectState(100, 8, 16, 16, 24, 20, 30),
            101: RoomObjectState(101, 40, 48, 16, 24, 50, 60),
            102: RoomObjectState(102, 40, 48, 16, 24, 70, 80, 7),
        }
        host.tick()
        state = host.engine.inspect_state()
        self.assertEqual(state["object_states"], {"100": 5, "101": 3, "102": 0})
        self.assertEqual(state["object_draw_queue"], [100, 101, 100])
        self.assertEqual(
            state["room_objects"]["100"],
            {"position": [96, 104], "size": [16, 24], "walk": [108, 118], "state": 5},
        )
        saved = host.save(0)
        host.engine.state.object_draw_queue.clear()
        host.engine.state.room_objects[100].x = 0
        host.load(0)
        self.assertEqual(host.engine.inspect_state()["room_objects"], state["room_objects"])
        self.assertEqual(host.engine.inspect_state()["object_draw_queue"], [100, 101, 100])
        self.assertEqual(saved.schema, 2)

    def test_c21_draw_object_fails_closed_on_stream_state_queue_and_save(self) -> None:
        cases = (
            (bytes((0x05,)), "ended at offset"),
            (bytes((0x05, 100, 0)), "ended at offset"),
            (bytes((0x05, 100, 0, 0)), "sub-op 0 is not implemented"),
            (bytes((0x05, 100, 0, 1, 2, 0)), "ended at offset"),
            (bytes((0x05, 100, 0, 2, 0, 1)), "state 256 must fit u8"),
        )
        for script, message in cases:
            with self.subTest(script=script.hex()):
                host = self._host(script)
                host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0)
                with self.assertRaisesRegex(EngineExecutionError, message):
                    host.tick()

        host = self._host(bytes((0x05, 100, 0, 0xFF)))
        host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0)
        host.engine.state.object_draw_queue = [100] * 200
        with self.assertRaisesRegex(EngineExecutionError, "queue overflow"):
            host.tick()

        host = self._host(bytes((0x80,)))
        host.engine.state.object_states[100] = 1
        host.engine.state.room_objects[100] = RoomObjectState(100, 0, 0, 8, 8, 0, 0, 1)
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["room_objects"]["100"]["state"] = 2
        with self.assertRaisesRegex(SaveFormatError, "state is noncanonical"):
            host.engine.load_state(host.context, json.dumps(payload).encode("utf-8"))

    def test_c3_delayed_slot_does_not_starve_peer(self) -> None:
        slot0 = (ROOT / "examples/resources/scumm_v5/c3_slot0.scrp").read_bytes()
        slot1 = (ROOT / "examples/resources/scumm_v5/c3_slot1.scrp").read_bytes()
        host = self._host(slot0)
        host.engine.state.scripts.append(ScriptSlot("synthetic.slot1", slot1))
        expected = [
            (4, 2, 4, 1, 3),
            (4, 1, 4, 2, 6),
            (4, 0, 4, 3, 9),
            (8, 0, 4, 4, 14),
            (8, 0, 4, 5, 20),
        ]
        for slot0_pc, slot0_delay, slot1_pc, peer_count, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            first, second = state["scripts"]
            self.assertEqual((first["pc"], first["delay"]), (slot0_pc, slot0_delay))
            self.assertEqual(second["pc"], slot1_pc)
            self.assertEqual(state["variables"].get("11"), peer_count)
            self.assertEqual(state["operations"], operations)

    def test_c4_script_lifecycle_locals_and_slot_reuse(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c4_lifecycle.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c4_child{number}.scrp").read_bytes()
            for number in (2, 3, 4)
        }
        host = self._host(main, scripts=children)
        expected = [
            (12, True, 2, 9, True, 11, {"0": 1, "1": 10}, 6),
            (26, True, 0, 15, False, 21, {"0": 2, "1": 10, "2": 20, "3": 21}, 14),
            (35, False, 0, 6, False, 30, {"0": 2, "1": 10, "2": 20, "3": 21, "4": 30}, 19),
        ]
        for main_pc, main_active, child_number, child_pc, child_active, local0, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            self.assertEqual(len(state["scripts"]), 2)
            parent, child = state["scripts"]
            self.assertEqual((parent["pc"], parent["active"]), (main_pc, main_active))
            self.assertEqual(
                (child["number"], child["pc"], child["active"], child["locals"][0]),
                (child_number, child_pc, child_active, local0),
            )
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)

    def test_c4_script_slot_capacity_fails_closed(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c4_capacity.scrp").read_bytes()
        child = (ROOT / "examples/resources/scumm_v5/c4_child2.scrp").read_bytes()
        host = self._host(script, scripts={2: child})
        for number in range(32, 56):
            host.engine.state.scripts.append(ScriptSlot(f"synthetic.{number}", bytes([0x80]), number=number))
        self.assertEqual(len(host.engine.state.scripts), 25)
        with self.assertRaisesRegex(EngineExecutionError, r"capacity exhausted \(25 slots\)"):
            host.tick()

    def test_c5_recursive_freeze_resistant_scheduler_and_queries(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c5_scheduler.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c5_child{number}.scrp").read_bytes()
            for number in (5, 6, 7)
        }
        host = self._host(main, scripts=children)
        expected = [
            (11, [0, 0], [5, 5], {"0": 1, "10": 2}, 8),
            (31, [1, 1, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "10": 3, "11": 1, "12": 1}, 21),
            (40, [1, 1, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "3": 1, "10": 3, "11": 1, "12": 2}, 28),
            (51, [0, 0, 0], [5, 6, 7], {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "10": 4, "11": 2, "12": 3}, 41),
            (62, [0, 0, 0], [0, 0, 0], {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "10": 4, "11": 2, "12": 3}, 46),
        ]
        for pc, freeze_counts, numbers, variables, operations in expected:
            host.tick()
            state = host.engine.inspect_state()
            parent, *children_state = state["scripts"]
            self.assertEqual(parent["pc"], pc)
            self.assertEqual([item["freeze_count"] for item in children_state], freeze_counts)
            self.assertEqual([item["number"] for item in children_state], numbers)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)
            if pc == 31:
                assert host.context is not None
                payload = host.engine.save_state(host.context)
                host.engine.state.scripts[1].freeze_count = 0
                host.engine.state.scripts[3].freeze_resistant = False
                host.engine.load_state(host.context, payload)
                restored = host.engine.inspect_state()["scripts"]
                self.assertEqual([item["freeze_count"] for item in restored[1:]], [1, 1, 0])
                self.assertTrue(restored[3]["freeze_resistant"])
        self.assertTrue(all(not item["active"] for item in state["scripts"]))

    def test_c6_chain_script_handoff_reuses_slot_and_never_resumes_caller(self) -> None:
        main = (ROOT / "examples/resources/scumm_v5/c6_scheduler.scrp").read_bytes()
        children = {
            number: (ROOT / f"examples/resources/scumm_v5/c6_{kind}{number}.scrp").read_bytes()
            for number, kind in ((10, "chain"), (11, "chain"), (12, "target"), (13, "target"))
        }
        host = self._host(main, scripts=children)
        expected = [
            (15, 8, {"0": 111, "1": 111, "3": 1}),
            (30, 19, {"0": 111, "1": 111, "3": 1, "4": 13, "6": 1, "7": 222}),
            (43, 24, {"0": 111, "1": 111, "3": 1, "4": 13, "6": 1, "7": 222}),
        ]
        for frame, (parent_pc, operations, variables) in enumerate(expected, start=1):
            host.tick()
            state = host.engine.inspect_state()
            parent, *children_state = state["scripts"]
            self.assertEqual(parent["pc"], parent_pc)
            self.assertEqual(state["variables"], variables)
            self.assertEqual(state["operations"], operations)
            self.assertEqual(state["variables"].get("15", 0), 0)
            if frame == 1:
                self.assertEqual(len(children_state), 1)
                child = children_state[0]
                self.assertEqual((child["number"], child["pc"], child["locals"][0]), (12, 6, 111))
                self.assertTrue(child["freeze_resistant"])
                self.assertTrue(child["recursive"])
            elif frame == 2:
                self.assertEqual(len(children_state), 2)
                self.assertEqual(
                    [(item["number"], item["pc"], item["locals"][0]) for item in children_state],
                    [(12, 6, 111), (13, 6, 222)],
                )
                self.assertTrue(children_state[0]["freeze_resistant"])
                self.assertTrue(children_state[0]["recursive"])
                self.assertFalse(children_state[1]["freeze_resistant"])
                self.assertFalse(children_state[1]["recursive"])
            else:
                self.assertFalse(any(item["active"] for item in state["scripts"]))
                self.assertEqual([item["number"] for item in state["scripts"]], [0, 0, 0])

    def test_c6_missing_target_retires_caller_before_failure(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c6_missing.scrp").read_bytes()
        host = self._host(script)
        with self.assertRaisesRegex(EngineExecutionError, r"script 14 has no resource binding"):
            host.tick()
        slot = host.engine.inspect_state()["scripts"][0]
        self.assertFalse(slot["active"])
        self.assertEqual(slot["number"], 0)

    def test_c6_capacity_does_not_reuse_reserved_boot_slot(self) -> None:
        script = (ROOT / "examples/resources/scumm_v5/c6_capacity.scrp").read_bytes()
        target = (ROOT / "examples/resources/scumm_v5/c6_target12.scrp").read_bytes()
        host = self._host(script, scripts={12: target})
        for number in range(32, 56):
            host.engine.state.scripts.append(ScriptSlot(f"synthetic.{number}", bytes([0x80]), number=number))
        self.assertEqual(len(host.engine.state.scripts), 25)
        with self.assertRaisesRegex(EngineExecutionError, r"capacity exhausted \(25 slots\)"):
            host.tick()
        state = host.engine.inspect_state()
        self.assertFalse(state["scripts"][0]["active"])
        self.assertEqual(state["scripts"][0]["number"], 0)
        self.assertTrue(all(item["active"] for item in state["scripts"][1:]))

    def test_corrupt_save_payload_fails_closed(self) -> None:
        host = self._host(bytes([0x80, 0x18, 0xFC, 0xFF]))
        assert host.context is not None
        payload = json.loads(host.engine.save_state(host.context).decode("utf-8"))
        payload["bits"] = [4096]
        with self.assertRaises(SaveFormatError):
            host.engine.load_state(
                host.context, json.dumps(payload).encode("utf-8")
            )

    def test_unknown_opcode_fails_loudly(self) -> None:
        host = self._host(bytes([0xA7]))
        with self.assertRaises(EngineExecutionError):
            host.tick()


if __name__ == "__main__":
    unittest.main()
