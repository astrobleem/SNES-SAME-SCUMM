from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from dataclasses import replace
import unittest
import zipfile

from examples.resources.scumm_v5.game_analysis_fixture import source_zip, raw_pair
from same.engines.scumm_v5.game_analysis import (
    analyze_game, build_game_ir, canonical_json, executable_identity, execution_cycles,
    game_analysis_hash,
)
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room_compiler import compile_room_payload
from same.engines.scumm_v5.residency import build_residency_plan
from same.engines.scumm_v5.program_units import (
    build_program_unit_model, build_residency_manifest,
)
from same.engines.scumm_v5.residency_contract import (
    DEFAULT_SELECTOR_POOL, ResidentBindingSimulator, ResidencyExhausted,
    ResolverDirectory, simulate_analysis_directory,
)
from same.profile import load_profile
from same.resources import MemoryResourceProvider


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PROFILE = ROOT / "examples/profiles/scumm_v5_game_analysis_fixture.json"
FATE_ARCHIVE = os.environ.get("SAME_SCUMM_SOURCE_ARCHIVE")
FATE_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_dos_cd.json"


def fixture_analysis(*, selector_capacity=None, data_only_objects=0):
    index, data = raw_pair(data_only_objects=data_only_objects)
    profile_bytes = FIXTURE_PROFILE.read_bytes()
    profile = load_profile(FIXTURE_PROFILE, verify_resources=False)
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider({"game.index": index, "game.data": data}),
        parse_game_policy(profile),
    )
    return analyze_game(
        provider, profile=profile, profile_bytes=profile_bytes,
        archive_sha256=hashlib.sha256(
            source_zip(data_only_objects=data_only_objects)).hexdigest(),
        source_members={"game.index": "ANALYSIS.000", "game.data": "ANALYSIS.001"},
        backend_selector_capacity=(None if selector_capacity is None else {
            "value": selector_capacity, "epistemic": "EXACT", "selectors_allocated": False,
        }),
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

    def test_selector_demand_excludes_data_only_objects_and_shares_verb_carrier(self) -> None:
        result = fixture_analysis(data_only_objects=12, selector_capacity=178)
        demand = result.selector_demand
        counts = demand["counts"]
        self.assertEqual(counts["semantic_executable_identities"],
                         result.executables["counts"]["total"])
        self.assertEqual(counts["resource_records"], 13)  # one scripted + twelve data-only
        self.assertEqual(counts["objects"]["without_verb_entries"], 12)
        self.assertEqual(counts["objects"]["with_verb_entries"], 1)
        self.assertEqual(counts["objects"]["verb_entries_without_semantic_ir"], 0)
        self.assertEqual(counts["legacy_projected_ids_with_no_runtime_reference_if_included"], 12)

        object_rows = [row for row in demand["resource_records"]
                       if row["room"] == 1 and row["object"] == 100]
        self.assertEqual(len(object_rows), 1)
        self.assertEqual(len(object_rows[0]["verb_entries"]), 3)
        self.assertEqual(object_rows[0]["selector_disposition"], "SELECTOR_UNIT")
        verbs = [row for row in demand["semantic_executable_to_selector"]
                 if row["semantic_executable"].startswith("ObjectVerb(room=1,object=100,")]
        self.assertEqual(len(verbs), 3)
        self.assertEqual({row["selector_unit"] for row in verbs},
                         {"ObjectProgram(room=1,object=100)"})
        self.assertTrue(all(row["disposition"] == "SHARED_SELECTOR_UNIT" for row in verbs))

        data_only = [row for row in demand["resource_records"]
                     if row["room"] == 2]
        self.assertEqual(len(data_only), 12)
        self.assertTrue(all(row["selector_unit"] is None
                            and row["selector_disposition"] == "NO_SELECTOR_REQUIRED"
                            for row in data_only))
        self.assertEqual(counts["selector_units"],
                         counts["executable_carriers"])
        self.assertEqual(counts["selector_units"],
                         counts["legacy_backend_program_records_that_receive_ids_if_included"] - 12)
        directory = result.selector_directory
        self.assertFalse(directory["selector_values_emitted"])
        self.assertEqual(directory["schema"], "same_scumm_v5_selector_free_directory_v2")
        self.assertEqual([row["script_number"] for row in directory["global_directory"]],
                         [1, 2, 3, 4, 5])
        self.assertFalse(directory["dynamic_global_resolver"]["prebind_candidates"])
        self.assertEqual(directory["dynamic_global_resolver"]["missing_target"],
                         "fail with UnknownProgramUnit; never alias")
        self.assertEqual(len(directory["data_only_resource_records"]), 12)
        directory_units = [unit for bundle in directory["bundles"]
                           for unit in bundle["selector_units"]]
        self.assertTrue(all("selector_value" not in unit and "selector" not in unit
                            for unit in directory_units))
        room2 = next(row for row in demand["room_selector_reports"] if row["room"] == 2)
        self.assertEqual(room2["resource_records"], 12)
        self.assertEqual(room2["selector_units_by_kind"], {
            "ROOM_ENTRY": 1, "ROOM_EXIT": 1,
        })

    def test_native_program_directory_is_stable_and_selector_free(self) -> None:
        result = fixture_analysis(data_only_objects=24)
        directory = result.native_program_directory
        self.assertEqual(directory["schema"], "same_scumm_v5_native_program_directory_v1")
        self.assertEqual(directory["id_width_bits"], 16)
        self.assertEqual(directory["unbound_id"], 0xFFFF)
        self.assertFalse(directory["selector_values_emitted"])
        entries = directory["entries"]
        ids = [row["program_unit_id"] for row in entries]
        self.assertEqual(ids, list(range(len(entries))))
        self.assertEqual(len({row["identity"] for row in entries}), len(entries))
        self.assertTrue(all("selector" not in row for row in entries))
        data_only = [row for row in result.selector_demand["resource_records"]
                     if row["selector_unit"] is None]
        self.assertEqual(len(data_only), 24)
        self.assertEqual(len(entries), result.selector_demand["counts"]["selector_units"])
        self.assertEqual(result.native_program_directory,
                         fixture_analysis(data_only_objects=24).native_program_directory)
        global_ids = {row["script_number"]: row["program_unit_id"]
                      for row in directory["global_directory"]}
        self.assertEqual(len(global_ids), 5)
        self.assertEqual(len(set(global_ids.values())), 5)

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
        script3 = next(item for item in result.game_ir.global_scripts if item.number == 3)
        self.assertTrue(script3.decode_complete)
        conditional_actor_query = script3.instructions[0]
        self.assertEqual(conditional_actor_query.operation,
                         "structural_only:getActorRoom")
        self.assertEqual(conditional_actor_query.structural_status,
                         "STRUCTURALLY_DECODED")
        self.assertEqual(conditional_actor_query.semantic_status,
                         "SEMANTIC_UNSUPPORTED")
        self.assertTrue(any(edge["source"] == "GlobalScript(3)"
                            and edge["target"] == "GlobalScript(4)"
                            and edge["kind"] == "start_script"
                            and edge["resolution"] == "STATIC"
                            for edge in result.dependency_graph["edges"]))
        self.assertTrue(any(edge["source"] == "GlobalScript(1)"
                            and edge["target"] == "GlobalScript(3)"
                            and edge["resolution"] == "CONDITIONAL_STATIC"
                            for edge in result.dependency_graph["edges"]))
        script2 = next(item for item in result.game_ir.global_scripts if item.number == 2)
        actor_query = next(item for item in script2.instructions
                           if item.operation == "structural_only:getActorRoom")
        self.assertEqual(actor_query.structural_status, "STRUCTURALLY_DECODED")
        self.assertEqual(actor_query.semantic_status, "SEMANTIC_UNSUPPORTED")
        self.assertTrue(any(edge["source"] == "GlobalScript(2)"
                            and edge["target"] == "GlobalScript(4)"
                            and edge["kind"] == "start_script"
                            for edge in result.dependency_graph["edges"]))
        self.assertTrue(any(edge["source"] == "GlobalScript(2)"
                            and edge["target"] == "Sound(5)"
                            and edge["kind"] == "resource-routine-reference"
                            and edge["resolution"] == "STATIC"
                            and edge["domain"] == "resource"
                            for edge in result.dependency_graph["edges"]))
        sound_node = next(item for item in result.dependency_graph["nodes"]
                          if item["identity"] == "Sound(5)")
        self.assertEqual(sound_node["status"], "UNRESOLVED_REFERENCE")
        self.assertTrue(any(item["opcode"] == "0x2F"
                            for item in result.opcode_coverage["structural_unknowns"]))
        operation_capability = result.capabilities["registry_by_operation"][
            "structural_only:getActorRoom"]
        self.assertEqual(operation_capability["front_end_decode"]["status"], "SUPPORTED")
        self.assertEqual(operation_capability["semantic_ir"]["status"], "UNSUPPORTED")

    def test_reachability_lattice_and_frontier_path(self) -> None:
        result = fixture_analysis()
        statuses = result.reachability["status_by_executable"]
        self.assertEqual(statuses["GlobalScript(1)"], "ROOT")
        self.assertEqual(statuses["GlobalScript(2)"], "DEFINITE")
        self.assertEqual(statuses["GlobalScript(3)"], "CONDITIONAL")
        self.assertEqual(statuses["GlobalScript(4)"], "DEFINITE")
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
        self.assertEqual(source_zip(), source_zip())
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

    def test_residency_separates_source_corpus_from_room_working_sets(self) -> None:
        result = fixture_analysis(selector_capacity=178)
        plan = result.residency
        self.assertFalse(result.program_units["selector_allocation_performed"])
        self.assertEqual(plan["counts"]["semantic_by_scope"]["GLOBAL"], 5)
        self.assertEqual(plan["selector_capacity"]["capacity"], 178)
        self.assertLess(plan["selector_capacity"]["scenarios"][0]["value"], 178)
        self.assertTrue(all(item["epistemic"] in {
            "EXACT", "STATIC_LOWER_BOUND", "CONSERVATIVE_CANDIDATE_BOUND", "UNKNOWN",
        } for item in plan["selector_capacity"]["scenarios"]))
        self.assertTrue(any(edge["kind"] == "load_room"
                            and edge["phase"] == "ROOM_TRANSITION"
                            and "STAGED" in edge["coexistence"]
                            for edge in plan["program_unit_dependencies"]))
        global4 = next(item for item in plan["global_program_units"]["records"]
                       if item["program_unit"] == "GlobalProgram(4)")
        self.assertTrue(global4["may_yield"])
        self.assertTrue(global4["contains_room_transition"])
        self.assertTrue(global4["may_retain_identity_across_room_change"])
        self.assertEqual(global4["evidence_scope"],
                         "OPERATION_PRESENCE_ONLY_NOT_PROOF_OF_LIVE_OVERLAP")
        self.assertGreaterEqual(
            len(plan["global_program_units"]["dynamic_candidate_universe"]), 5)
        room1 = next(item for item in plan["room_bundles"] if item["room"] == 1)
        self.assertGreater(room1["program_unit_count"], 0)
        self.assertEqual(room1["total_conservative_candidate_program_units"]["epistemic"],
                         "CONSERVATIVE_CANDIDATE_BOUND")
        self.assertIn("GlobalProgram(4)", plan["global_program_units"]["room_transition_capable_with_yield"])
        self.assertIsNone(plan["simultaneous_residency"]["largest_proven_exact_set"]["value"])
        self.assertEqual(plan["simultaneous_residency"]["distinct_active_binding_upper_bound"]["upper_bound"], 25)

    def test_program_unit_projection_and_dynamic_candidate_pinning(self) -> None:
        base = fixture_analysis(selector_capacity=178)
        scripts = {executable_identity(item): item for item in base.game_ir.global_scripts}
        for compilation in base.room_compilations.values():
            scripts.update({executable_identity(item): item
                            for item in compilation.room_ir.scripts})
        base_global = scripts["GlobalScript(1)"]
        base_verb = next(item for item in scripts.values() if item.kind == "OBCD")
        statuses = {identity: "UNREACHED" for identity in scripts}

        synthetic_global_ids = []
        for number in range(1000, 1200):
            identity = f"GlobalScript({number})"
            source = replace(base_global.source, room=0, script_number=number)
            scripts[identity] = replace(base_global, number=number, source=source,
                                         identity=f"synthetic/global/{number}")
            statuses[identity] = "UNREACHED"
            synthetic_global_ids.append(identity)

        for room in range(10, 20):
            for object_index in range(3):
                object_id = 2000 + object_index
                for verb_id in range(10):
                    identity = f"ObjectVerb(room={room},object={object_id},verb={verb_id})"
                    source = replace(base_verb.source, room=room, object_id=object_id,
                                     verb_id=verb_id, source_offset=room * 10000 + object_id * 10 + verb_id)
                    scripts[identity] = replace(
                        base_verb, identity=f"synthetic/r{room}/o{object_id}/v{verb_id}",
                        source=source, object_id=object_id, verb_id=verb_id,
                        program=b"\x00", instructions=(), decode_complete=True,
                        opaque_from_pc=None)
                    statuses[identity] = "UNREACHED"

        graph = {"edges": list(base.dependency_graph["edges"])}
        graph["edges"].append({
            "source": "GlobalScript(1)", "target": None, "kind": "start_script",
            "domain": "execution", "resolution": "DYNAMIC", "source_pc": 3,
            "expression": "variable-selected global", "detail": None,
            "candidate_targets": synthetic_global_ids,
        })
        model = build_program_unit_model(
            scripts, {}, graph, {"status_by_executable": statuses})
        plan = build_residency_plan(
            scripts, graph, {"status_by_executable": statuses},
            backend_selector_capacity=178, program_unit_model=model)

        synthetic_object_units = [unit for unit in model["program_units"]
                                  if unit["kind"] == "OBJECT"
                                  and unit["owner"].get("room", -1) in range(10, 20)]
        self.assertEqual(len(synthetic_object_units), 30)
        self.assertEqual(sum(len(unit["semantic_executable_identities"])
                             for unit in synthetic_object_units), 300)
        self.assertEqual(model["counts"]["semantic_executable_identities"], len(scripts))
        self.assertGreater(model["counts"]["semantic_executable_identities"], 178)
        self.assertGreater(model["counts"]["program_units"], 178)
        self.assertGreater(plan["global_program_units"]["dynamic_candidate_universe_count"], 178)
        self.assertEqual(plan["working_set_questions"]["C_simultaneously_live_or_pinned"]["epistemic"],
                         "UNKNOWN")
        manifest = build_residency_manifest(model)
        self.assertFalse(manifest["selector_values_emitted"])
        self.assertEqual(len(model["semantic_to_program_unit"]), len(scripts))
        self.assertTrue(all("selector" not in unit
                            for unit in manifest["program_units"]))

        simulator = ResidentBindingSimulator(3)
        yielded_global = "GlobalProgram(4)"
        simulator.pin(yielded_global, "YIELDED_ROOM_TRANSITION")
        old_selector = simulator.reference(yielded_global).selector
        simulator.pin("RoomEntryProgram(22)", "ACTIVE_ROOM")
        selected_dynamic = "GlobalProgram(1199)"
        simulator.pin(selected_dynamic, "ACTIVE_DYNAMIC_CALL")
        self.assertEqual(simulator.resolve(yielded_global), old_selector)
        self.assertNotIn(
            "GlobalProgram(1000)",
            {item["program_unit"] for item in simulator.resident_snapshot()["bindings"]},
        )
        with self.assertRaises(ResidencyExhausted):
            simulator.resolve("GlobalProgram(1198)")
        simulator.unpin("RoomEntryProgram(22)", "ACTIVE_ROOM")
        reused = simulator.resolve("GlobalProgram(1198)")
        self.assertEqual(str(simulator.unit_for_selector(reused)), "GlobalProgram(1198)")
        self.assertEqual(str(simulator.unit_for_selector(old_selector)), yielded_global)


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
            backend_selector_capacity={
                "value": 178, "epistemic": "EXACT", "selectors_allocated": False,
                "source": "current generator pool verified by CLI acceptance",
            },
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
                             for item in room7_scripts), 0)
        room7_units = next(item for item in analysis.residency["room_bundles"]
                           if item["room"] == 7)
        self.assertEqual(room7_units["semantic_executable_count"], 79)
        self.assertEqual(room7_units["program_unit_count"], 44)
        self.assertEqual(room7_units["room_lifecycle_units"], 2)
        self.assertEqual(room7_units["local_units"], 18)
        self.assertEqual(room7_units["object_units"], 24)
        self.assertEqual(room7_units["semantic_object_verb_count"], 59)
        room7_object_units = [unit for unit in analysis.program_units["program_units"]
                              if unit["kind"] == "OBJECT"
                              and unit["owner"].get("room") == 7]
        self.assertEqual(len(room7_object_units), 24)
        self.assertEqual(sum(len(unit["semantic_executable_identities"])
                             for unit in room7_object_units), 59)
        self.assertTrue(all(item["program_unit"].startswith("ObjectProgram(room=7,")
                            for item in analysis.program_units["semantic_to_program_unit"]
                            if item["semantic_executable"].startswith("ObjectVerb(room=7,")))
        self.assertEqual(analysis.program_units["counts"]["program_units"], 2788)
        self.assertEqual(analysis.program_units["counts"]["selector_bearing_records"], 2195)
        self.assertEqual(analysis.program_units["counts"]["object_program_units"], 1362)
        self.assertEqual(analysis.program_units["counts"]["object_verb_semantic_identities"], 2674)
        demand = analysis.selector_demand
        self.assertEqual(demand["counts"]["semantic_executable_identities"], 4100)
        self.assertEqual(demand["counts"]["resource_records"], 1362)
        self.assertEqual(demand["counts"]["executable_carriers"], 2195)
        self.assertEqual(demand["counts"]["selector_units"], 2195)
        self.assertEqual(demand["counts"]["legacy_projected_ids_with_no_runtime_reference_if_included"], 593)
        self.assertEqual(demand["counts"]["objects"]["with_verb_entries"], 769)
        self.assertEqual(demand["counts"]["objects"]["without_verb_entries"], 593)
        self.assertEqual(demand["counts"]["objects"]["verb_entries_without_semantic_ir"], 0)
        self.assertEqual(demand["counts"]["objects"]["objects_with_structural_unknown_verbs"], 0)
        self.assertEqual(demand["counts"]["objects"]["malformed_or_truncated_verb_entries"], 0)

        room7_selector = next(item for item in demand["room_selector_reports"]
                              if item["room"] == 7)
        self.assertEqual(room7_selector["semantic_executable_identities"], 79)
        self.assertEqual(room7_selector["resource_records"], 24)
        self.assertEqual(room7_selector["objects_with_verb_entries"], 18)
        self.assertEqual(room7_selector["objects_without_verb_entries"], 6)
        self.assertEqual(room7_selector["executable_carriers"], 38)
        self.assertEqual(room7_selector["selector_units"], 38)
        room7_semantic_verbs = [item for item in demand["semantic_executable_to_selector"]
                                if item["semantic_executable"].startswith("ObjectVerb(room=7,")]
        self.assertEqual(len(room7_semantic_verbs), 59)
        self.assertEqual(len({item["selector_unit"] for item in room7_semantic_verbs}), 18)
        self.assertTrue(all(item["disposition"] == "SHARED_SELECTOR_UNIT"
                            for item in room7_semantic_verbs))

        room98_selector = next(item for item in demand["room_selector_reports"]
                               if item["room"] == 98)
        self.assertEqual(room98_selector["semantic_executable_identities"], 2)
        self.assertEqual(room98_selector["resource_records"], 126)
        self.assertEqual(room98_selector["objects_without_verb_entries"], 126)
        self.assertEqual(room98_selector["selector_units"], 2)
        self.assertEqual(room98_selector["selector_units_by_kind"], {
            "ROOM_ENTRY": 1, "ROOM_EXIT": 1,
        })
        self.assertEqual(room98_selector["static_addressability_count"], 2)
        room98_objects = [item for item in demand["resource_records"]
                          if item["room"] == 98]
        self.assertEqual(len(room98_objects), 126)
        self.assertTrue(all(item["has_object_resource_record"]
                            and not item["has_decoded_verb_bodies"]
                            and not item["has_executable_object_carrier"]
                            and item["legacy_selector_assigned_if_included"]
                            and not item["runtime_selector_referenced"]
                            and item["selector_required_semantically"] == "NO"
                            for item in room98_objects))

        room43 = next(item for item in analysis.residency["room_bundles"] if item["room"] == 43)
        self.assertEqual(room43["semantic_executable_count"], 174)
        self.assertEqual(room43["program_unit_count"], 40)
        self.assertEqual(len(room43["global_program_units_required"]), 11)
        self.assertEqual(room43["total_static_addressable_program_units"]["value"], 51)
        self.assertLess(room43["total_static_addressable_program_units"]["value"], 178)
        room46 = next(item for item in analysis.residency["room_bundles"] if item["room"] == 46)
        self.assertEqual(room46["program_unit_count"], 64)
        self.assertEqual(len(room46["dynamic_global_candidate_units"]), 163)
        self.assertEqual(room46["total_conservative_candidate_program_units"]["value"], 227)
        self.assertGreater(room46["total_conservative_candidate_program_units"]["value"], 178)
        room98 = analysis.residency["room_bundles"][0]
        self.assertEqual((room98["room"], room98["program_unit_count"]), (98, 128))
        self.assertFalse(analysis.residency["selector_capacity"]["static_addressability_exceeds"])
        self.assertEqual(demand["room_capacity_summary"]["largest_room_selector_unit_count"], 60)
        self.assertEqual(demand["room_capacity_summary"]["largest_static_room_plus_global_set"], 71)
        self.assertEqual(demand["room_capacity_summary"]["largest_dynamic_candidate_universe"], 216)
        self.assertEqual(demand["room_capacity_summary"]["static_room_sets_over_capacity"], [])
        selector_room46 = next(item for item in demand["room_selector_reports"]
                               if item["room"] == 46)
        self.assertEqual(selector_room46["selector_units"], 53)
        self.assertEqual(selector_room46["static_addressability_count"], 68)
        self.assertEqual(selector_room46["dynamic_candidate_universe_count"], 216)
        self.assertEqual(len(demand["global_selector_summary"]["dynamic_candidate_universe"]), 163)
        self.assertEqual(len(demand["global_selector_summary"]["yield_capable"]), 82)
        self.assertEqual(len(demand["global_selector_summary"]["room_transition_capable_with_yield"]), 15)
        self.assertEqual(analysis.selector_residency["selector_capacity"][
            "static_addressability_exceeds"], [])
        self.assertEqual(analysis.residency["simultaneous_residency"][
                         "distinct_active_binding_upper_bound"]["upper_bound"], 25)
        self.assertFalse(analysis.residency_manifest["selector_values_emitted"])
        self.assertEqual(len(analysis.program_units["semantic_to_program_unit"]), 4100)
        object118 = next(edge for edge in analysis.program_units["dependencies"]
                         if edge["source_semantic_identity"] ==
                         "ObjectVerb(room=7,object=118,verb=10)"
                         and edge["kind"] == "room-local-script")
        self.assertEqual(object118["source_program_unit"],
                         "ObjectProgram(room=7,object=118)")
        self.assertEqual(object118["target_program_unit"],
                         "RoomLocalProgram(room=7,local=207)")
        object119 = next(edge for edge in analysis.program_units["dependencies"]
                         if edge["source_semantic_identity"] ==
                         "ObjectVerb(room=7,object=119,verb=10)"
                         and edge["kind"] == "room-local-script"
                         and edge["target_semantic_identity"] ==
                         "RoomLocal(room=7,local=201)")
        self.assertEqual(object119["source_program_unit"],
                         "ObjectProgram(room=7,object=119)")
        self.assertEqual(object119["target_program_unit"],
                         "RoomLocalProgram(room=7,local=201)")
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

        # Consume the exact compiler directory in the pure residency model.
        # This is a modeled contract check, not a FATE gameplay trace.
        resolver_directory = ResolverDirectory.from_selector_directory(
            analysis.selector_directory)
        self.assertEqual(len(resolver_directory.global_scripts), 163)
        simulation = simulate_analysis_directory(
            resolver_directory, analysis.selector_demand,
            analysis.dependency_graph, selector_pool=DEFAULT_SELECTOR_POOL)
        self.assertEqual(simulation["selector_capacity"], 178)
        self.assertEqual(simulation["largest_room"]["room"], 40)
        self.assertEqual(simulation["largest_room"]["selector_units"], 60)
        self.assertEqual(simulation["largest_room"][
            "modeled_peak_with_live_globals_and_dynamic_lookup"], 84)
        self.assertTrue(simulation["largest_room"][
            "yielded_global_preserved_across_transition"])
        self.assertEqual(simulation["largest_room"][
            "transition_to_compiler_discovered_room"], 41)
        self.assertEqual(simulation["largest_room"]["transition_result"][
            "peak_activation_slots"], 25)
        self.assertEqual(simulation["dynamic_candidate_scenario"]["room"], 46)
        self.assertEqual(simulation["dynamic_candidate_scenario"][
            "candidate_universe_count"], 216)
        self.assertEqual(simulation["dynamic_candidate_scenario"][
            "max_additional_global_bindings_at_once"], 1)
        self.assertFalse(simulation["dynamic_candidate_scenario"][
            "all_candidates_prebound"])
        self.assertEqual(simulation["capacity"][
            "conservative_modeled_upper_bound"]["value"], 85)
        self.assertTrue(simulation["capacity"][
            "selector_capacity_sufficient_for_modeled_bound"])
        self.assertEqual(simulation["capacity"][
            "proven_concurrent_live_unit_maximum"]["epistemic"], "UNKNOWN")


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
            self.assertEqual(differences, [],
                             f"FATE analysis outputs differ: {differences}")


if __name__ == "__main__":
    unittest.main()
