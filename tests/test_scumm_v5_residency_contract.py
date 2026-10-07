from __future__ import annotations

import json
import unittest

from same.engines.scumm_v5.residency_contract import (
    DEFAULT_SELECTOR_POOL,
    ActivationCapacityExhausted,
    PinReason,
    ProgramUnitIdentity,
    ResidentBindingSimulator,
    ResolverDirectory,
    ResidencyExhausted,
    StaleSelectorReference,
    UnknownProgramUnit,
    simulate_analysis_directory,
)


def make_directory(*, global_count: int = 3, room_count: int = 2,
                   room_units: int = 4) -> ResolverDirectory:
    bundle_units: dict[str, list[str]] = {"GlobalBundle": []}
    kinds: dict[str, str] = {}
    global_numbers = {}
    for number in range(1, global_count + 1):
        identity = f"GlobalProgram({number})"
        bundle_units["GlobalBundle"].append(identity)
        kinds[identity] = "GLOBAL"
        global_numbers[number] = identity
    for room in range(1, room_count + 1):
        name = f"RoomBundle({room})"
        rows = [f"RoomEntryProgram({room})", f"RoomExitProgram({room})"]
        kinds[rows[0]] = "ROOM_ENTRY"
        kinds[rows[1]] = "ROOM_EXIT"
        while len(rows) < room_units:
            local = len(rows) - 1
            identity = f"RoomLocalProgram(room={room},local={local})"
            rows.append(identity)
            kinds[identity] = "ROOM_LOCAL"
        bundle_units[name] = rows
    return ResolverDirectory.from_units(
        bundle_units, kinds=kinds, global_script_numbers=global_numbers)


def selector_directory_fixture() -> dict:
    bundles = [{
        "identity": "GlobalBundle",
        "selector_units": [{
            "local_bundle_index": 0,
            "selector_unit_identity": "GlobalProgram(7)",
            "kind": "GLOBAL",
            "owner": {"global": 7},
            "dispatch_metadata": {"lookup_key": {"script_number": 7}},
        }],
    }, {
        "identity": "RoomBundle(3)",
        "selector_units": [{
            "local_bundle_index": 0,
            "selector_unit_identity": "RoomEntryProgram(3)",
            "kind": "ROOM_ENTRY",
            "owner": {"room": 3},
        }, {
            "local_bundle_index": 1,
            "selector_unit_identity": "RoomExitProgram(3)",
            "kind": "ROOM_EXIT",
            "owner": {"room": 3},
        }],
    }]
    return {"schema": "same_scumm_v5_selector_free_directory_v2",
            "selector_values_emitted": False, "bundles": bundles}


class ScummV5ResidencyContractTests(unittest.TestCase):
    def test_selector_pool_matches_backend_order_and_reserved_range(self) -> None:
        self.assertEqual(len(DEFAULT_SELECTOR_POOL), 178)
        self.assertEqual(DEFAULT_SELECTOR_POOL[:3], (0xD0, 0xD1, 0xD2))
        self.assertEqual(DEFAULT_SELECTOR_POOL[48:51], (0xCF, 0xCE, 0xCD))
        self.assertEqual(DEFAULT_SELECTOR_POOL[-1], 0x4E)
        self.assertFalse(set(DEFAULT_SELECTOR_POOL) & set(range(0x4E)))
        with self.assertRaisesRegex(ValueError, "reserved backend"):
            ResidentBindingSimulator(selector_pool=(0x00,))

    def test_directory_ingests_selector_free_units_and_rejects_values(self) -> None:
        directory = ResolverDirectory.from_selector_directory(selector_directory_fixture())
        self.assertEqual(directory.global_unit(7).value, "GlobalProgram(7)")
        self.assertEqual(directory.room_bundles, {3: "RoomBundle(3)"})
        with self.assertRaises(UnknownProgramUnit):
            directory.global_unit(8)
        invalid = selector_directory_fixture()
        invalid["bundles"][0]["selector_units"][0]["selector_value"] = 0xD0
        with self.assertRaises(ValueError):
            ResolverDirectory.from_selector_directory(invalid)

    def test_bind_reuse_native_pool_order_eviction_and_stale_generation(self) -> None:
        sim = ResidentBindingSimulator(1)
        old = sim.reference("GlobalProgram(1)")
        self.assertEqual(sim.resolve("GlobalProgram(1)"), old.selector)
        sim.resolve("GlobalProgram(2)")
        with self.assertRaises(StaleSelectorReference):
            sim.validate_reference(old)
        current = sim.reference("GlobalProgram(2)")
        self.assertEqual(current.selector, old.selector)
        self.assertGreater(current.generation, old.generation)

        pool_order = ResidentBindingSimulator(2)
        pool_order.resolve("A")
        pool_order.resolve("B")
        pool_order.resolve("A")  # Access time does not alter the native scan order.
        pool_order.resolve("C")
        self.assertIsNone(pool_order.binding("A"))
        self.assertIsNotNone(pool_order.binding("B"))

    def test_unpinned_first_native_selector_is_reused_after_owner_retires(self) -> None:
        sim = ResidentBindingSimulator(3)
        owner = sim.resolve("GlobalProgram(1)")
        owner_ref = sim.reference("GlobalProgram(1)")
        pin = sim.pin("GlobalProgram(1)", PinReason.ACTIVE_SCRIPT_SLOT)
        sim.resolve("RoomEntryProgram(1)")
        sim.resolve("RoomExitProgram(1)")
        sim.unpin(pin)
        replacement = sim.resolve("GlobalProgram(192)")
        self.assertEqual(replacement, owner)
        current_ref = sim.reference("GlobalProgram(192)")
        self.assertEqual(current_ref.generation, owner_ref.generation + 1)
        with self.assertRaises(StaleSelectorReference):
            sim.validate_reference(owner_ref)

    def test_multiple_pin_reasons_prevent_reassignment_until_all_release(self) -> None:
        sim = ResidentBindingSimulator(1)
        first = sim.pin("GlobalProgram(1)", PinReason.ACTIVE_SCRIPT_SLOT)
        second = sim.pin("GlobalProgram(1)", PinReason.CUTSCENE_OVERRIDE)
        self.assertEqual(sim.pins_for("GlobalProgram(1)"), {
            "ACTIVE_SCRIPT_SLOT": 1, "CUTSCENE_OVERRIDE": 1,
        })
        with self.assertRaises(ResidencyExhausted):
            sim.resolve("GlobalProgram(2)")
        sim.unpin(first)
        with self.assertRaises(ResidencyExhausted):
            sim.resolve("GlobalProgram(2)")
        sim.unpin(second)
        self.assertEqual(str(sim.unit_for_selector(sim.resolve("GlobalProgram(2)"))),
                         "GlobalProgram(2)")

    def test_room_bundle_release_retains_yielded_global_then_reclaims_local(self) -> None:
        directory = make_directory(global_count=4, room_count=2, room_units=4)
        sim = ResidentBindingSimulator(directory=directory,
                                       selector_pool=(0xD0, 0xD1, 0xD2, 0xD3,
                                                      0xD4, 0xD5, 0xD6, 0xD7))
        sim.begin_room("RoomBundle(1)")
        global_activation = sim.begin_global(1, pc=0x123, locals=(4, 5), yielded=True)
        global_selector = global_activation.reference.selector
        global_reference = global_activation.reference
        continuation = sim.hold_continuation(
            "room-change-return", global_activation.program_unit,
            reason=PinReason.ROOM_CONTINUATION,
            activation_id=global_activation.activation_id)
        local = next(unit for unit in directory.bundle_units("RoomBundle(1)")
                     if directory.unit(unit).kind == "ROOM_LOCAL")
        local_reference = sim.reference(local)
        local_activation = sim.begin_activation(local, pc=9, locals=(1, 2))
        sim.hold_continuation(
            "retired-local-continuation", local,
            reason=PinReason.ROOM_CONTINUATION,
            activation_id=local_activation.activation_id)
        sim.hold_continuation(
            "orphaned-local-continuation", local,
            reason=PinReason.CUTSCENE_OVERRIDE)

        result = sim.transition_room("RoomBundle(1)", "RoomBundle(2)")
        self.assertTrue(result["old_bundle_released_before_incoming_bind"])
        self.assertIn(global_activation.program_unit.value, result["globals_preserved"])
        self.assertEqual(sim.resolve(global_activation.program_unit), global_selector)
        self.assertNotIn(local_activation.activation_id, sim._activations)
        self.assertNotIn("retired-local-continuation", sim._continuations)
        self.assertNotIn("orphaned-local-continuation", sim._continuations)
        self.assertIsNone(sim.binding(local))
        self.assertIn("RoomBundle(2)", sim._loaded_bundles)
        self.assertNotIn("RoomBundle(1)", sim._loaded_bundles)
        self.assertTrue(sim.validate_reference(global_activation.reference))
        sim.resolve("GlobalProgram(4)")
        with self.assertRaises(StaleSelectorReference):
            sim.validate_reference(local_reference)

        sim.mark_yielded(global_activation.activation_id, False)
        sim.end_activation(global_activation.activation_id)
        sim.release_continuation(continuation.continuation_id)
        self.assertFalse(sim.is_pinned("GlobalProgram(1)"))
        self.assertTrue(sim.release_unit("GlobalProgram(1)"))
        self.assertIsNone(sim.binding("GlobalProgram(1)"))
        recycled_selector = sim.reference("GlobalProgram(3)")
        self.assertEqual(recycled_selector.selector, global_selector)
        self.assertGreater(recycled_selector.generation, global_reference.generation)
        with self.assertRaises(StaleSelectorReference):
            sim.validate_reference(global_reference)

    def test_nested_parent_and_same_program_replacement_share_binding(self) -> None:
        directory = make_directory(global_count=2, room_count=0)
        sim = ResidentBindingSimulator(directory=directory, selector_pool=(0xD0, 0xD1))
        caller = sim.begin_global(1, pc=33, locals=(10, 11))
        caller_selector = caller.reference.selector
        child = sim.begin_global(2, parent_activation_id=caller.activation_id)
        self.assertEqual(sim.pins_for("GlobalProgram(1)")["NESTED_PARENT"], 1)
        sim.end_activation(child.activation_id)
        self.assertNotIn("NESTED_PARENT", sim.pins_for("GlobalProgram(1)"))
        self.assertEqual(sim.resolve("GlobalProgram(1)"), caller_selector)

        replacement = sim.replace_activation(caller.activation_id, pc=0, locals=(99,))
        self.assertEqual(replacement.program_unit, caller.program_unit)
        self.assertEqual(replacement.reference.selector, caller_selector)
        self.assertEqual(sum(name == "GlobalProgram(1)"
                             for name in sim._unit_to_binding), 1)
        self.assertEqual(replacement.locals, (99,))
        sim.end_activation(replacement.activation_id)
        self.assertTrue(sim.release_unit("GlobalProgram(2)"))

    def test_activation_slot_ceiling_is_separate_from_selector_capacity(self) -> None:
        directory = make_directory(global_count=3, room_count=0)
        sim = ResidentBindingSimulator(directory=directory, selector_pool=(0xD0, 0xD1, 0xD2),
                                       activation_capacity=2)
        first = sim.begin_global(1)
        second = sim.begin_global(2)
        with self.assertRaises(ActivationCapacityExhausted):
            sim.begin_global(3)
        self.assertEqual(len(sim._unit_to_binding), 2)
        sim.end_activation(second.activation_id)
        sim.end_activation(first.activation_id)

    def test_global_directory_is_lazy_and_unknown_numbers_do_not_alias(self) -> None:
        directory = make_directory(global_count=220, room_count=1, room_units=3)
        sim = ResidentBindingSimulator(directory=directory)
        self.assertEqual(len(directory.global_scripts), 220)
        sim.begin_room("RoomBundle(1)")
        activation = sim.begin_global(217, pc=12, locals=(217,))
        self.assertEqual(len([name for name in sim._unit_to_binding
                              if name.startswith("GlobalProgram(")]), 1)
        self.assertEqual(len(sim._unit_to_binding), 4)
        sim.end_activation(activation.activation_id)
        sim.release_unit("GlobalProgram(217)")
        with self.assertRaises(UnknownProgramUnit):
            sim.resolve_global(221)
        self.assertNotIn("GlobalProgram(221)",
                         {item["program_unit"]
                          for item in sim.resident_snapshot()["bindings"]})

    def test_portable_snapshot_reassigns_selector_and_restores_semantics(self) -> None:
        directory = make_directory(global_count=200, room_count=0)
        sim = ResidentBindingSimulator(directory=directory)
        for number in range(1, 50):
            sim.resolve(f"GlobalProgram({number})")
        activation = sim.begin_global(200, pc=0x1234, locals=(7, 8, 9), yielded=True)
        sim.hold_continuation("cutscene-return", activation.program_unit,
                              reason=PinReason.CUTSCENE_OVERRIDE,
                              activation_id=activation.activation_id)
        self.assertEqual(activation.reference.selector.hex, "$CE")
        portable = sim.snapshot()
        self.assertNotIn("selector", json.dumps(portable).lower())

        restored = ResidentBindingSimulator.restore(
            portable, directory=directory,
            prebind=[f"GlobalProgram({number})" for number in range(1, 95)])
        restored_activation = restored._activation(activation.activation_id)
        self.assertEqual(restored_activation.reference.selector.hex, "$A1")
        self.assertNotEqual(restored_activation.reference.selector,
                            activation.reference.selector)
        self.assertEqual(portable, restored.snapshot())
        self.assertEqual(restored_activation.pc, 0x1234)
        self.assertEqual(restored_activation.locals, (7, 8, 9))
        self.assertTrue(restored_activation.yielded)
        self.assertEqual(restored.pins_for("GlobalProgram(200)"), {
            "ACTIVE_SCRIPT_SLOT": 1,
            "CUTSCENE_OVERRIDE": 1,
            "YIELDED_SCRIPT": 1,
        })
        self.assertNotIn("SAVE_RESTORE_RECONSTRUCTION",
                         restored.pins_for("GlobalProgram(200)"))

    def test_portable_restore_preserves_room_and_nested_activation_ownership(self) -> None:
        directory = make_directory(global_count=3, room_count=1, room_units=4)
        sim = ResidentBindingSimulator(directory=directory,
                                       selector_pool=DEFAULT_SELECTOR_POOL[:12])
        sim.begin_room("RoomBundle(1)")
        local = next(name for name in directory.bundle_units("RoomBundle(1)")
                     if directory.unit(name).kind == "ROOM_LOCAL")
        parent = sim.begin_activation(local, pc=0x77, locals=(4, 9))
        child = sim.begin_global(1, pc=0x88, locals=(1,),
                                 parent_activation_id=parent.activation_id)
        portable = sim.snapshot()
        restored = ResidentBindingSimulator.restore(
            portable, directory=directory,
            selector_pool=DEFAULT_SELECTOR_POOL[:12],
            prebind=("GlobalProgram(2)",))
        restored_parent = restored._activation(parent.activation_id)
        restored_child = restored._activation(child.activation_id)
        self.assertEqual(restored.active_room_bundle, "RoomBundle(1)")
        self.assertEqual(restored_parent.room_ownership, "RoomBundle(1)")
        self.assertEqual(restored_parent.pc, 0x77)
        self.assertEqual(restored_parent.locals, (4, 9))
        self.assertEqual(restored_child.parent_activation_id, parent.activation_id)
        self.assertEqual(restored_child.pc, 0x88)
        self.assertEqual(restored.pins_for(local)["NESTED_PARENT"], 1)
        self.assertEqual(restored.snapshot(), portable)

    def test_exhaustion_is_atomic_and_released_pin_allows_reuse(self) -> None:
        names = [f"Unit({index})" for index in range(179)]
        directory = ResolverDirectory.from_units({"All": names})
        sim = ResidentBindingSimulator(directory=directory)
        pins = [sim.pin(name, PinReason.ACTIVE_SCRIPT_SLOT) for name in names[:178]]
        before = sim.resident_snapshot()
        with self.assertRaisesRegex(ResidencyExhausted, "RESIDENCY_EXHAUSTED"):
            sim.resolve(names[178])
        self.assertEqual(before, sim.resident_snapshot())
        self.assertEqual(len(sim._selector_to_unit), 178)
        self.assertEqual(len(set(sim._selector_to_unit)), 178)
        sim.unpin(pins[0])
        sim.resolve(names[178])
        self.assertIsNone(sim.binding(names[0]))
        for name in names[1:178]:
            self.assertTrue(sim.is_pinned(name))
        self.assertEqual(len(sim._selector_to_unit), 178)

    def test_more_than_pool_corpus_cycles_room_bundles_and_dynamic_candidates(self) -> None:
        directory = make_directory(global_count=220, room_count=12, room_units=20)
        self.assertGreater(len(directory.units), 178)
        sim = ResidentBindingSimulator(directory=directory)
        sim.begin_room("RoomBundle(1)")
        global_activation = sim.begin_global(1, yielded=True)
        for room in range(1, 12):
            sim.transition_room(f"RoomBundle({room})", f"RoomBundle({room + 1})")
        self.assertEqual(len(sim._unit_to_binding), 21)
        self.assertLessEqual(sim.peak_bindings, 21)
        self.assertTrue(sim.validate_reference(global_activation.reference))

        additional_peaks = []
        for number in (100, 160, 220):
            dynamic = sim.begin_global(number, pc=number)
            additional_peaks.append(len(sim._unit_to_binding))
            sim.end_activation(dynamic.activation_id)
            sim.release_unit(dynamic.program_unit)
        self.assertEqual(max(additional_peaks), 22)
        self.assertEqual(len(sim._unit_to_binding), 21)
        sim.end_activation(global_activation.activation_id)

    def test_failed_bundle_load_does_not_partially_install(self) -> None:
        names = [f"RoomLocalProgram(room=9,local={i})" for i in range(4)]
        directory = ResolverDirectory.from_units(
            {"RoomBundle(9)": names},
            kinds={name: "ROOM_LOCAL" for name in names})
        sim = ResidentBindingSimulator(directory=directory,
                                       selector_pool=(0xD0, 0xD1, 0xD2))
        before = sim.resident_snapshot()
        with self.assertRaises(ResidencyExhausted):
            sim.load_bundle("RoomBundle(9)")
        self.assertEqual(before["bindings"], sim.resident_snapshot()["bindings"])
        self.assertEqual(sim._loaded_bundles, set())

    def test_fate_analysis_simulation_report_is_deterministic_and_bounded(self) -> None:
        directory = make_directory(global_count=30, room_count=2, room_units=4)
        semantic_map = {
            "RoomLocal(room=1,local=1)": "RoomLocalProgram(room=1,local=1)",
            "RoomEntry(2)": "RoomEntryProgram(2)",
        }
        demand = {
            "semantic_to_selector_index": semantic_map,
            "source_coverage": {"rooms_inventoried": 2, "rooms_parsed": 2},
            "room_selector_reports": [
                {"room": room, "dynamic_candidate_universe_count": 30,
                 "dynamic_global_candidate_selector_units": [
                     f"GlobalProgram({number})" for number in range(1, 31)]}
                for room in (1, 2)
            ],
            "global_selector_summary": {
                "dynamic_candidate_universe": [
                    f"GlobalProgram({number})" for number in range(1, 31)]},
            "room_capacity_summary": {"largest_dynamic_candidate_universe": 34},
        }
        graph = {"edges": [{
            "source": "RoomLocal(room=1,local=1)",
            "target": "RoomEntry(2)", "kind": "load_room",
            "resolution": "CONDITIONAL_STATIC",
        }]}
        first = simulate_analysis_directory(directory, demand, graph)
        second = simulate_analysis_directory(directory, demand, graph)
        self.assertEqual(first, second)
        self.assertEqual(first["room_transition_scenarios"][
            "compiler_discovered_static_or_conditional_load_edges"], 1)
        self.assertEqual(first["room_transition_scenarios"]["peak_binding_count"], 27)
        self.assertEqual(first["room_transition_scenarios"]["largest_peak_examples"][0][
            "peak_activation_slots"], 25)
        self.assertLessEqual(first["capacity"]["conservative_modeled_upper_bound"]["value"], 178)
        self.assertTrue(first["portable_snapshot_restore"]["portable_state_equal"])
        self.assertTrue(first["portable_snapshot_restore"][
            "selector_reassignment_demonstrated"])
        self.assertFalse(first["portable_snapshot_restore"][
            "portable_snapshot_contains_selector_fields"])


if __name__ == "__main__":
    unittest.main()
