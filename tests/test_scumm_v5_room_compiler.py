from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from examples.resources.scumm_v5.room_bundle_fixture import source_rooms
from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.engines.scumm_v5.room_compiler import (
    analyze_room, compile_room_payload, decode_script,
)
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "examples/profiles/scumm_v5_conformance.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _compile(room: int, payload: bytes, *, profile_sha: str | None = None,
             game_sha: str | None = None):
    return compile_room_payload(
        payload,
        room_number=room,
        game_name="synthetic-conformance",
        resource_key=f"room.{room}",
        source_member="fixture:room_bundle_fixture.py",
        source_container_offset=0,
        original_room_file_offset=0,
        profile_sha256=profile_sha or _sha(b"profile"),
        game_identity_sha256=game_sha or _sha(b"game"),
        archive_sha256=_sha(b"fixture-archive"),
        index_sha256=_sha(b"fixture-index"),
        data_sha256=_sha(b"fixture-data"),
        global_script_count=200,
        global_object_states=bytes(256),
        global_object_owners=bytes(256),
        global_object_classes=(0,) * 256,
    )


class ScummV5RoomCompilerTests(unittest.TestCase):
    def test_source_bound_ir_extracts_semantics_dependencies_and_bit_reads(self) -> None:
        payload = source_rooms()[1]
        first = _compile(1, payload)
        second = _compile(1, payload)
        self.assertEqual(first.cooked_record, second.cooked_record)
        self.assertEqual(first.ir_json(), second.ir_json())
        self.assertEqual(first.analysis_json(), second.analysis_json())

        ir = first.room_ir
        self.assertEqual(ir.room, 1)
        self.assertEqual(ir.room_sha256, _sha(payload))
        self.assertEqual(ir.source_member, "fixture:room_bundle_fixture.py")
        self.assertEqual([item.kind for item in ir.scripts[:3]], ["ENCD", "EXCD", "LSCR"])
        self.assertEqual([(item.object_id, item.verb_id) for item in ir.scripts
                          if item.kind == "OBCD"],
                         [(100, 10), (100, 11), (100, 255)])
        entry = ir.scripts[0]
        self.assertTrue(entry.decode_complete)
        self.assertEqual(entry.instructions[0].operation, "branch_equal_zero")
        self.assertEqual(dict(entry.instructions[0].operands)["value"]["index"], 69)
        self.assertIn("bit:69", first.capabilities.state_reads)
        self.assertIn("object-state:100", first.capabilities.state_writes)

        static = {(item.kind, item.target, item.resolution, item.detail)
                  for item in first.capabilities.static_dependencies}
        self.assertIn(("script", 200, "resolved", "local"), static)
        self.assertIn(("room-transition", 2, "static", None), static)
        self.assertIn(("object-script", 100, "resolved", "entry 10"), static)
        self.assertIn(("object-verb", 100, "resolved", "verb 11"), static)
        self.assertEqual(first.capabilities.unclassified_operations, ())
        self.assertEqual(first.capabilities.unsupported_operations, ())

    def test_unknown_opcode_is_an_explicit_opaque_tail_not_a_noop(self) -> None:
        program = b"\xFD\x0A\xC8\xFF"
        result = decode_script(
            program, identity="synthetic/unknown", kind="LSCR", number=200,
            room=1, resource_key="room.1/LSCR.200", game_name="synthetic",
            source_member="fixture", resource_offset=0, source_offset=123,
        )
        self.assertFalse(result.decode_complete)
        self.assertEqual(result.opaque_from_pc, 0)
        self.assertEqual(result.instructions[0].operation, "opaque_bytecode_tail")
        self.assertFalse(result.instructions[0].boundary_known)
        self.assertEqual(result.instructions[0].raw_hex, program.hex())
        self.assertEqual(result.instructions[0].source_offset, 123)
        self.assertIn("instruction width", result.instructions[0].diagnostic or "")

    def test_print_operand_width_does_not_overwrite_script_identity_kind(self) -> None:
        result = decode_script(
            bytes((0x14, 1, 0x02, 0x11, 0, 0xFF, 0)),
            identity="room.1/LSCR.200", kind="LSCR", number=200,
            room=1, resource_key="room.1/LSCR.200", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=321,
        )
        self.assertTrue(result.decode_complete)
        self.assertEqual(result.kind, "LSCR")
        self.assertEqual(result.instructions[0].operation, "print_text")

    def test_print_text_terminates_print_instruction_before_following_opcode(self) -> None:
        result = decode_script(
            bytes((0x14, 1, 0x0F, ord("H"), ord("i"), 0,
                   0x1A, 0, 0, 7, 0, 0)),
            identity="room.1/LSCR.200", kind="LSCR", number=200,
            room=1, resource_key="room.1/LSCR.200", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=400,
        )
        self.assertTrue(result.decode_complete)
        self.assertEqual([item.operation for item in result.instructions],
                         ["print_text", "write_variable", "stop_script"])
        self.assertEqual(result.instructions[0].raw_hex, "14010f486900")
        self.assertEqual(result.instructions[1].pc, 6)

    def test_start_object_dependency_requires_an_existing_verb_entry(self) -> None:
        payload = source_rooms()[1].replace(
            bytes((0x37, 100, 0, 10, 0xFF)),
            bytes((0x37, 100, 0, 12, 0xFF)),
            1,
        )
        compilation = _compile(1, payload)
        dependency = next(
            item for item in compilation.capabilities.static_dependencies
            if item.kind == "object-script" and item.source_script == "room.1/ENCD"
        )
        self.assertEqual(dependency.target, 100)
        self.assertEqual(dependency.resolution, "missing")
        self.assertEqual(dependency.detail, "entry 12")

    def test_variable_script_reference_is_dynamic_not_a_guessed_static_target(self) -> None:
        compilation = _compile(1, source_rooms()[1])
        dynamic_call = decode_script(
            bytes((0x8A, 0x00, 0x80, 0xFF, 0x00)),
            identity="room.1/ENCD-dynamic", kind="ENCD", number=None,
            room=1, resource_key="room.1", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=500,
        )
        room_ir = replace(compilation.room_ir, objects=(), scripts=(dynamic_call,))
        report = analyze_room(room_ir, global_script_count=200)
        self.assertEqual(report.static_dependencies, ())
        self.assertEqual(len(report.dynamic_dependencies), 1)
        dependency = report.dynamic_dependencies[0]
        self.assertEqual((dependency.kind, dependency.target, dependency.resolution),
                         ("script", None, "dynamic"))
        self.assertEqual(dependency.source_pc, 0)
        self.assertIn("variable-indirect", dependency.expression or "")

    def test_load_room_with_ego_decodes_all_direct_and_variable_forms(self) -> None:
        cases = (
            (0x24, bytes((0x53, 0x03, 63)), 851, 63),
            (0xA4, bytes((1, 0, 63)), None, 63),
            (0x64, bytes((0x53, 0x03, 1, 0)), 851, None),
            (0xE4, bytes((1, 0, 1, 0)), None, None),
        )
        for opcode, operands, object_value, room_value in cases:
            with self.subTest(opcode=opcode):
                script = decode_script(
                    bytes((opcode,)) + operands + b"\xff\xff\xff\xff\0",
                    identity="synthetic/entry", kind="ENCD", number=None,
                    room=1, resource_key="room.1", game_name="synthetic-conformance",
                    source_member="fixture", resource_offset=0, source_offset=700,
                )
                self.assertTrue(script.decode_complete)
                operation, stop = script.instructions
                self.assertEqual(operation.operation, "load_room_with_ego")
                self.assertEqual(operation.source_offset, 700)
                values = dict(operation.operands)
                for name, expected in (("entry_object", object_value), ("room", room_value)):
                    operand = values[name]
                    if expected is None:
                        self.assertEqual(operand["mode"], "variable")
                        self.assertEqual(operand["index"], 1)
                    else:
                        self.assertEqual(operand, {"mode": "direct", "value": expected})
                self.assertEqual((values["x"], values["y"]), (-1, -1))
                self.assertEqual(values["ego_actor"], {
                    "mode": "implicit_variable", "namespace": "global", "index": 1,
                })
                self.assertEqual(stop.operation, "stop_script")

    def test_load_room_with_ego_emits_static_and_dynamic_room_object_edges(self) -> None:
        base = _compile(1, source_rooms()[1])
        direct = decode_script(
            bytes((0x24, 0x53, 0x03, 63, 0xFF, 0xFF, 0xFF, 0xFF, 0)),
            identity="room.1/ENCD", kind="ENCD", number=None,
            room=1, resource_key="room.1", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=900,
        )
        report = analyze_room(
            replace(base.room_ir, scripts=(direct,)), global_script_count=200,
        )
        direct_edges = {(item.kind, item.target, item.resolution)
                        for item in report.static_dependencies}
        self.assertIn(("room-transition", 63, "static"), direct_edges)
        self.assertIn(("room-entry-object", "63:851", "static"), direct_edges)
        self.assertIn("global:1", report.state_reads)

        indirect = decode_script(
            bytes((0xE4, 1, 0, 2, 0, 0xFF, 0xFF, 0xFF, 0xFF, 0)),
            identity="room.1/ENCD", kind="ENCD", number=None,
            room=1, resource_key="room.1", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=900,
        )
        report = analyze_room(
            replace(base.room_ir, scripts=(indirect,)), global_script_count=200,
        )
        dynamic_edges = {(item.kind, item.resolution) for item in report.dynamic_dependencies}
        self.assertIn(("room-transition", "dynamic"), dynamic_edges)
        self.assertIn(("room-entry-object", "dynamic"), dynamic_edges)

    def test_walk_actor_to_uses_all_three_flagged_operand_widths(self) -> None:
        script = decode_script(
            bytes((0x9E, 1, 0, 0x34, 0x12, 0x78, 0x56, 0)),
            identity="synthetic/entry", kind="ENCD", number=None,
            room=1, resource_key="room.1", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=1000,
        )
        self.assertTrue(script.decode_complete)
        operation = script.instructions[0]
        self.assertEqual(operation.operation, "walk_actor_to")
        operands = dict(operation.operands)
        self.assertEqual(operands["actor"], {
            "mode": "variable", "namespace": "global", "index": 1,
            "indexed": False, "index_reference": None,
        })
        self.assertEqual(operands["x"], {"mode": "direct", "value": 0x1234})
        self.assertEqual(operands["y"], {"mode": "direct", "value": 0x5678})

    def test_actor_room_placement_and_camera_follow_are_separate_edges(self) -> None:
        base = _compile(1, source_rooms()[1])
        script = decode_script(
            bytes((0xC0, 0xAD, 1, 0, 3, 0x81, 1, 0, 0xA0, 0, 0x82, 0,
                   0x52, 1, 0xA0)),
            identity="room.1/LSCR.200", kind="LSCR", number=200,
            room=1, resource_key="room.1", game_name="synthetic-conformance",
            source_member="fixture", resource_offset=0, source_offset=1200,
        )
        self.assertEqual([item.operation for item in script.instructions],
                         ["end_cutscene", "put_actor_in_room", "put_actor",
                          "actor_follow_camera", "stop_script"])
        report = analyze_room(
            replace(base.room_ir, scripts=(script,)), global_script_count=200,
        )
        placement = next(item for item in report.static_dependencies
                         if item.kind == "actor-placement")
        transition = next(item for item in report.dynamic_dependencies
                          if item.kind == "room-transition")
        self.assertEqual((placement.target, placement.resolution), (3, "static"))
        self.assertEqual(transition.resolution, "dynamic")

    def test_cooked_record_retains_exact_source_room_and_runtime_directory(self) -> None:
        payload = source_rooms()[1]
        compilation = _compile(1, payload)
        decoded = decode_cooked_room(compilation.cooked_record, expected_room=1)
        self.assertEqual(decoded.room_payload, payload)
        self.assertEqual(decoded.room_sha256, _sha(payload))
        self.assertEqual([item.kind for item in decoded.scripts], ["ENCD", "EXCD", "LSCR"])
        self.assertEqual(decoded.locals[0].number, 200)
        self.assertEqual(compilation.record_manifest["objects"][0]["verb_entries"], [
            {"verb": 10, "entry_offset": 47},
            {"verb": 11, "entry_offset": 52},
            {"verb": 255, "entry_offset": 56},
        ])

    def test_compiled_synthetic_room_runs_through_existing_host_runtime(self) -> None:
        profile_data = json.loads(PROFILE_PATH.read_text())
        profile_data["options"].update({
            "cooked_room_key_template": "cooked.room.{room}",
            "cooked_room_manifest": "cooked.manifest",
        })
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            profile_path = temp / "fixture-profile.json"
            profile_path.write_text(json.dumps(profile_data, sort_keys=True) + "\n")
            profile = load_profile(profile_path, verify_resources=False)
            profile_sha = _sha(profile_path.read_bytes())
            game_sha = _sha(
                f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode()
            )
            compiled = {
                room: _compile(room, payload, profile_sha=profile_sha, game_sha=game_sha)
                for room, payload in source_rooms().items()
            }
            source_sha = _sha(b"fixture-archive")
            index_sha = _sha(b"fixture-index")
            data_sha = _sha(b"fixture-data")
            manifest = {
                "schema": "same_scumm_v5_cooked_rooms_v1",
                "num_global_scripts": 200,
                "profile": {"sha256": profile_sha, "identity_sha256": game_sha},
                "source": {"archive_sha256": source_sha,
                           "index_sha256": index_sha, "data_sha256": data_sha},
            }
            resources = {
                "script.boot": bytes((0x72, 1, 0x00)),
                "room.0": source_rooms()[2],
                "room.1": source_rooms()[1],
                "room.2": source_rooms()[2],
                "cooked.manifest": (json.dumps(manifest) + "\n").encode(),
                "cooked.room.1": compiled[1].cooked_record,
                "cooked.room.2": compiled[2].cooked_record,
            }
            kinds = {key: "ROOM" for key in ("room.0", "room.1", "room.2")}
            kinds.update({"script.boot": "SCRP", "cooked.manifest": "JSON",
                          "cooked.room.1": "SC5C", "cooked.room.2": "SC5C"})
            provider = MemoryResourceProvider(resources, kinds=kinds)
            host = EngineHost(
                profile, default_registry(),
                services=HostServices.create(profile, resources=provider),
            )
            host.boot()
            frame = host.tick()
            state = host.engine.inspect_state()
            self.assertEqual(state["room"], 2)
            self.assertEqual(state["object_states"].get("100"), 4)
            self.assertTrue(frame.halted)
            self.assertEqual(host.lifecycle.value, "stopped")

    def test_existing_snes_generator_allocates_compiler_bundle_identities(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            profile = load_profile(PROFILE_PATH, verify_resources=False)
            profile_sha = _sha(PROFILE_PATH.read_bytes())
            game_sha = _sha(
                f"{profile.engine_id}\0{profile.game_id}\0{profile.variant}".encode()
            )
            compilation = _compile(
                1, source_rooms()[1], profile_sha=profile_sha, game_sha=game_sha,
            )
            (temp / "room-1.sc5c").write_bytes(compilation.cooked_record)
            (temp / "states.bin").write_bytes(bytes(256))
            (temp / "owners.bin").write_bytes(bytes(256))
            record = dict(compilation.record_manifest, output="room-1.sc5c")
            manifest = {
                "schema": "same_scumm_v5_cooked_rooms_v1", "num_global_scripts": 200,
                "profile": {"sha256": profile_sha, "identity_sha256": game_sha},
                "source": {"archive_sha256": _sha(b"a"), "index_sha256": _sha(b"i"),
                           "data_sha256": _sha(b"d")},
                "global_objects": {"count": 256, "states_output": "states.bin",
                                   "owners_output": "owners.bin"},
                "records": [record], "global_scripts": [],
            }
            manifest_path = temp / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
            report = temp / "programs.json"
            command = [
                sys.executable, str(ROOT / "tools/generate_snes_cooked_rooms.py"),
                "--manifest", str(manifest_path), "--output", str(temp / "tables.pasm"),
                "--data-output", str(temp / "data.pasm"), "--binary-dir", str(temp / "bin"),
                "--report", str(report), "--far-programs",
            ]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
            program_map = json.loads(report.read_text())["program_map"]
            identities = {item["identity"]: item["id"] for item in program_map}
            self.assertIn("room.1/ENCD", identities)
            self.assertIn("room.1/LSCR.200", identities)
            self.assertIn("room.1/object.100/OBCD", identities)
            self.assertEqual(len(set(identities.values())), len(identities))


if __name__ == "__main__":
    unittest.main()
