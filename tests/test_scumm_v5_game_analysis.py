from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from examples.resources.scumm_v5.game_analysis_fixture import source_zip, raw_pair
from same.engines.scumm_v5.game_analysis import (
    analyze_game, build_game_ir, canonical_json, execution_cycles,
    game_analysis_hash,
)
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room_compiler import compile_room_payload
from same.profile import load_profile
from same.resources import MemoryResourceProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PROFILE = ROOT / "examples/profiles/scumm_v5_game_analysis_fixture.json"
FATE_ARCHIVE = os.environ.get("SAME_SCUMM_SOURCE_ARCHIVE")
FATE_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_dos_cd.json"


def fixture_analysis():
    index, data = raw_pair()
    profile_bytes = FIXTURE_PROFILE.read_bytes()
    profile = load_profile(FIXTURE_PROFILE, verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    return analyze_game(
        provider, profile=profile, profile_bytes=profile_bytes,
        archive_sha256=hashlib.sha256(source_zip()).hexdigest(),
        source_members={"game.index": "ANALYSIS.000", "game.data": "ANALYSIS.001"},
    )


class ScummV5WholeGameAnalysisTests(unittest.TestCase):
    def test_census_and_canonical_source_identities(self) -> None:
        result = fixture_analysis()
        self.assertEqual(result.census["counts"]["room"], 2)
        self.assertEqual(result.census["global_scripts_available"], 5)
        self.assertEqual(result.census["counts"]["object-verb"], 3)
        identities = {item["identity"] for item in result.executables["items"]}
        self.assertIn("GlobalScript(1)", identities)
        self.assertIn("RoomEntry(1)", identities)
        self.assertIn("RoomExit(1)", identities)
        self.assertIn("RoomLocal(room=1,local=200)", identities)
        self.assertIn("ObjectVerb(room=1,object=100,verb=10)", identities)
        self.assertNotIn("selector", " ".join(identities).lower())
        nodes = {item["identity"]: item for item in result.dependency_graph["nodes"]}
        self.assertEqual(nodes["GlobalScript(1)"]["node_type"], "executable")
        self.assertEqual(nodes["ScriptResource(1)"]["node_type"], "resource")

    def test_graph_distinguishes_static_conditional_dynamic_and_opaque(self) -> None:
        result = fixture_analysis()
        graph = result.dependency_graph
        start2 = [edge for edge in graph["edges"]
                  if edge["source"] == "GlobalScript(1)" and edge["target"] == "GlobalScript(2)"]
        self.assertTrue(any(edge["resolution"] == "STATIC" for edge in start2))
        start3 = [edge for edge in graph["edges"]
                  if edge["source"] == "GlobalScript(1)" and edge["target"] == "GlobalScript(3)"]
        self.assertTrue(any(edge["resolution"] == "CONDITIONAL_STATIC" for edge in start3))
        dynamic = [edge for edge in graph["edges"]
                   if edge["source"] == "GlobalScript(1)" and edge["resolution"] == "DYNAMIC"]
        self.assertTrue(dynamic)
        self.assertTrue(all(edge["target"] is None for edge in dynamic))
        self.assertTrue(any(edge["candidate_targets"] for edge in dynamic))
        self.assertFalse(result.opaque_analysis["closure_complete"])
        self.assertIn("GlobalScript(2)", result.opaque_analysis["reachable_incomplete"])
        self.assertEqual(result.opaque_analysis["invariant"].split(";")[0],
                         "OPAQUE TAIL != COMPLETE ANALYSIS")
        statuses = {item["identity"]: item["analysis_status"]
                    for item in result.executables["items"]}
        self.assertEqual(statuses["GlobalScript(2)"], "UNSUPPORTED_DECODE")
        self.assertEqual(statuses["GlobalScript(5)"], "MALFORMED")

    def test_reachability_lattice_and_frontier_path(self) -> None:
        result = fixture_analysis()
        statuses = result.reachability["status_by_executable"]
        self.assertEqual(statuses["GlobalScript(1)"], "ROOT")
        self.assertEqual(statuses["GlobalScript(2)"], "DEFINITE")
        self.assertEqual(statuses["GlobalScript(3)"], "CONDITIONAL")
        self.assertEqual(statuses["GlobalScript(4)"], "CONDITIONAL")
        unsupported = [item for item in result.unsupported_frontier["items"]
                       if item["source_identity"] == "GlobalScript(2)"]
        self.assertTrue(unsupported)
        load_ego = next(item for item in unsupported
                        if item["operation"] == "load_room_with_ego")
        self.assertEqual(load_ego["classification"], "DEFINITE_BLOCKER")
        self.assertIn("GlobalScript(1)", load_ego["dependency_path"])
        opaque = next(item for item in unsupported
                      if item["operation"] == "opaque_bytecode_tail")
        self.assertEqual(opaque["classification"], "UNKNOWN_BEYOND_OPAQUE_BOUNDARY")

    def test_decoder_support_is_not_backend_or_runtime_certification(self) -> None:
        result = fixture_analysis()
        registry = result.capabilities["registry_by_operation"]
        self.assertEqual(registry["load_room"]["front_end_decode"]["status"], "SUPPORTED")
        self.assertEqual(registry["load_room"]["ir_representation"]["status"], "SUPPORTED")
        self.assertEqual(registry["load_room"]["snes_backend"]["status"], "PARTIAL")
        self.assertEqual(registry["load_room"]["snes_runtime"]["status"], "UNKNOWN")
        self.assertEqual(registry["opaque_bytecode_tail"]["front_end_decode"]["status"], "UNSUPPORTED")

    def test_room_projection_is_the_room_compiler_representation(self) -> None:
        index, data = raw_pair()
        profile = load_profile(FIXTURE_PROFILE, verify_resources=False)
        provider = LucasartsScummV5ResourceProvider(
            MemoryResourceProvider({"game.index": index, "game.data": data}),
            parse_game_policy(profile),
        )
        game, compilations = build_game_ir(
            provider, profile=profile, profile_bytes=FIXTURE_PROFILE.read_bytes(),
            archive_sha256="a" * 64,
            source_members={"game.index": "ANALYSIS.000", "game.data": "ANALYSIS.001"},
        )
        room_row = next(item for item in game.rooms if item["room"] == 1)
        location = provider.source_location("room.1")
        direct = compile_room_payload(
            provider.read("room.1"), room_number=1,
            game_name=f"{profile.game_id}:{profile.variant}", resource_key="room.1",
            source_member="ANALYSIS.001", source_container_offset=int(location["container_offset"]),
            original_room_file_offset=int(location["payload_offset"]),
            profile_sha256=hashlib.sha256(FIXTURE_PROFILE.read_bytes()).hexdigest(),
            game_identity_sha256=game.game_identity_sha256,
            archive_sha256="a" * 64,
            index_sha256=hashlib.sha256(index).hexdigest(), data_sha256=hashlib.sha256(data).hexdigest(),
            global_script_count=provider.global_script_count,
            global_object_states=provider.global_objects.states,
            global_object_owners=provider.global_objects.owners,
            global_object_classes=provider.global_objects.classes,
        )
        self.assertEqual(room_row["room_ir"], direct.room_ir.to_dict())
        self.assertEqual(compilations[1].room_ir.to_dict(), direct.room_ir.to_dict())

    def test_analysis_files_are_canonical_and_deterministic(self) -> None:
        first, second = fixture_analysis(), fixture_analysis()
        self.assertEqual(first.files(), second.files())
        self.assertEqual(game_analysis_hash(first.files()), game_analysis_hash(second.files()))
        for content in first.files().values():
            if content.startswith(b"{"):
                json.loads(content)

    def test_resource_inventory_keeps_resources_separate_from_reachability(self) -> None:
        result = fixture_analysis()
        nodes = {item["identity"]: item for item in result.dependency_graph["nodes"]}
        self.assertIn("RoomResource(2)", nodes)
        self.assertEqual(nodes["RoomResource(2)"]["node_type"], "resource")
        self.assertTrue(any(edge["domain"] == "resource" for edge in result.dependency_graph["edges"]))

    def test_cycle_analysis_handles_execution_graph_sccs(self) -> None:
        nodes = {name: {"node_type": "executable"} for name in ("A", "B", "C")}
        edges = [
            {"source": "A", "target": "B", "domain": "execution", "resolution": "STATIC"},
            {"source": "B", "target": "A", "domain": "execution", "resolution": "CONDITIONAL_STATIC"},
            {"source": "B", "target": "C", "domain": "execution", "resolution": "DYNAMIC"},
        ]
        self.assertEqual(execution_cycles(nodes, edges), [["A", "B"]])


@unittest.skipUnless(FATE_ARCHIVE, "set SAME_SCUMM_SOURCE_ARCHIVE for full FATE census integration")
class ScummV5FateWholeGameIntegrationTests(unittest.TestCase):
    def test_dos_cd_census_and_room7_shared_compiler_crosscheck(self) -> None:
        archive_path = Path(FATE_ARCHIVE)  # type: ignore[arg-type]
        with zipfile.ZipFile(archive_path) as archive:
            from same.engines.scumm_v5.room_compiler import source_member_pair
            members = source_member_pair(archive.namelist())
            raw = {key: archive.read(value) for key, value in members.items()}
        profile_bytes = FATE_PROFILE.read_bytes()
        profile = load_profile(FATE_PROFILE, verify_resources=False)
        provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw),
                                                    parse_game_policy(profile))
        analysis = analyze_game(
            provider, profile=profile, profile_bytes=profile_bytes,
            archive_sha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            source_members=members,
        )
        self.assertEqual(analysis.game_ir.game_id, "indy4-fate-dos-cd-en")
        self.assertEqual(analysis.game_ir.game_variant, "DOS CD English, full voice (1993)")
        self.assertEqual(analysis.executables["counts"]["total_epistemic"],
                         "STATIC_LOWER_BOUND")
        self.assertEqual(analysis.capacity["rooms_inventoried"]["value"], 96)
        self.assertEqual(analysis.capacity["rooms_semantically_parsed"]["value"], 93)
        self.assertEqual(analysis.capacity["objects"]["epistemic"],
                         "STATIC_LOWER_BOUND")
        room7 = next(item for item in analysis.game_ir.rooms if item["room"] == 7)
        direct = analysis.room_compilations[7].room_ir.to_dict()
        self.assertEqual(room7["room_ir"], direct)
        room7_scripts = [item for item in analysis.executables["items"]
                         if item["identity"] in {"RoomEntry(7)", "RoomExit(7)"}
                         or item["identity"].startswith(("RoomLocal(room=7,",
                                                          "ObjectVerb(room=7,"))]
        self.assertEqual(len(room7_scripts), 79)
        self.assertEqual(sum(item["analysis_status"] != "COMPLETE"
                             for item in room7_scripts), 21)
        self.assertTrue(any(edge["source"] == "ObjectVerb(room=7,object=118,verb=10)"
                            and edge["kind"] == "room-local-script"
                            and edge["target"] == "RoomLocal(room=7,local=207)"
                            for edge in analysis.dependency_graph["edges"]))
        self.assertTrue(any(edge["source"] == "ObjectVerb(room=7,object=119,verb=10)"
                            and edge["kind"] == "room-local-script"
                            and edge["target"] == "RoomLocal(room=7,local=201)"
                            for edge in analysis.dependency_graph["edges"]))
        self.assertTrue(any(edge["source"] == "RoomLocal(room=7,local=201)"
                            and edge["kind"] == "actor-placement-room"
                            and edge["target"] == "RoomEntry(3)"
                            for edge in analysis.dependency_graph["edges"]))
        self.assertTrue(any(edge["source"] == "RoomLocal(room=7,local=201)"
                            and edge["kind"] == "actor-follow-camera-room"
                            and edge["resolution"] == "DYNAMIC"
                            for edge in analysis.dependency_graph["edges"]))


class ScummV5GameAnalysisCliTests(unittest.TestCase):
    def test_two_output_directories_are_identical_for_synthetic_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "fixture.zip"
            source.write_bytes(source_zip())
            outputs = [root / "one", root / "two"]
            for output in outputs:
                subprocess.run([
                    sys.executable, str(ROOT / "tools/compile_scumm_game.py"),
                    "--source", str(source), "--profile", str(FIXTURE_PROFILE),
                    "--analyze", "--output", str(output),
                ], cwd=ROOT, check=True, capture_output=True, text=True)
            maps = [{path.relative_to(output).as_posix(): path.read_bytes()
                     for path in output.rglob("*") if path.is_file()} for output in outputs]
            self.assertEqual(maps[0], maps[1])
            capacity = json.loads((outputs[0] / "capacity.json").read_text())
            self.assertEqual(capacity["current_default_backend_selector_pool"]["value"],
                             len(range(0xD0, 0x100)) + len(range(0xCF, 0x4D, -1)))
            self.assertFalse(capacity["current_default_backend_selector_pool"]["selectors_allocated"])

    @unittest.skipUnless(FATE_ARCHIVE, "set SAME_SCUMM_SOURCE_ARCHIVE for FATE determinism integration")
    def test_two_output_directories_are_identical_for_fate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outputs = [root / "one", root / "two"]
            for output in outputs:
                subprocess.run([
                    sys.executable, str(ROOT / "tools/compile_scumm_game.py"),
                    "--source", FATE_ARCHIVE, "--profile", str(FATE_PROFILE),
                    "--analyze", "--output", str(output),
                ], cwd=ROOT, check=True, capture_output=True, text=True)
            maps = [{path.relative_to(output).as_posix(): path.read_bytes()
                     for path in output.rglob("*") if path.is_file()} for output in outputs]
            first, second = maps
            file_sets_equal = set(first) == set(second)
            differences = [name for name in sorted(set(first) | set(second))
                           if first.get(name) != second.get(name)]
            report = {"schema": "same_scumm_v5_game_analysis_determinism_v1",
                      "runs": 2, "file_sets_equal": file_sets_equal,
                      "content_equal": file_sets_equal and not differences,
                      "differences": differences}
            report_path = os.environ.get("SAME_SCUMM_GAME_ANALYSIS_DETERMINISM_REPORT")
            if report_path:
                target = Path(report_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
            self.assertEqual(maps[0], maps[1])


if __name__ == "__main__":
    unittest.main()
