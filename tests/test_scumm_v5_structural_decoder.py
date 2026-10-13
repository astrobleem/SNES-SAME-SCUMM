from __future__ import annotations

import unittest

from same.engines.scumm_v5.room_compiler import decode_script
from same.engines.scumm_v5.v5_opcode_schema import opcode_schema, schema_coverage


def decode(program: bytes):
    return decode_script(
        program, identity="fixture", kind="SCRP", number=1, room=0,
        resource_key="script.1", game_name="copyright-free-fixture",
        source_member="fixture", resource_offset=0, source_offset=0,
    )


class ScummV5StructuralDecoderTests(unittest.TestCase):
    def test_parameter_flag_variants_share_a_family_and_schema(self) -> None:
        variants = [opcode_schema(value) for value in (0x25, 0x65, 0xA5, 0xE5)]
        self.assertEqual({item.family for item in variants if item}, {"pickupObject"})
        self.assertEqual({item.opcode for item in variants if item}, {0x25})
        self.assertEqual([item.parameter_flag_mask for item in variants if item],
                         [0xC0] * 4)
        self.assertEqual([item.parameter_flags for item in variants if item],
                         [0x00, 0x40, 0x80, 0xC0])
        coverage = schema_coverage()
        self.assertEqual(coverage["registered_v5_opcode_bytes"], 244)
        self.assertEqual(coverage["unregistered_opcode_bytes"], 12)
        self.assertEqual(coverage["family_assignment_collisions"], 0)
        self.assertEqual(coverage["families"], coverage["families_with_operand_forms"])
        set_name = opcode_schema(0xD4)
        self.assertIsNotNone(set_name)
        self.assertEqual(set_name.family, "setObjectName")
        self.assertEqual(set_name.parameter_flag_mask, 0x80)
        self.assertEqual(set_name.parameter_flags, 0x80)
        start_script_flagged = decode(b"\x2a\x07\xff\x00").instructions[0]
        self.assertEqual(start_script_flagged.base_opcode, 0x0A)
        self.assertEqual(start_script_flagged.opcode_variant_flags, 0x20)
        self.assertEqual(start_script_flagged.parameter_flags, 0)
        start_script_variable = decode(b"\x8a\x01\x00\xff\x00").instructions[0]
        self.assertEqual(start_script_variable.base_opcode, 0x0A)
        self.assertEqual(start_script_variable.opcode_variant_flags, 0x80)
        self.assertEqual(start_script_variable.parameter_flags, 0x80)

    def test_string_op_semantic_ir_keeps_following_instruction_boundary(self) -> None:
        result = decode(b"\x27\x01\x25note\0\x0a\x02\xff\x00")
        string_op, start, stop = result.instructions
        self.assertEqual(string_op.operation, "string_ops")
        self.assertEqual(string_op.structural_status, "STRUCTURALLY_DECODED")
        self.assertEqual(string_op.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(string_op.instruction_width, 8)
        self.assertEqual(dict(string_op.operands)["operation"], "load_string")
        self.assertEqual(dict(string_op.operands)["encoded_text_hex"], "6e6f746500")
        self.assertEqual((start.pc, start.operation), (8, "start_script"))
        self.assertEqual((stop.pc, stop.operation), (11, "stop_object_code"))
        self.assertTrue(result.decode_complete)
        self.assertIsNone(result.opaque_from_pc)

    def test_result_query_ir_preserves_result_and_flagged_operand_modes(self) -> None:
        cases = (
            (bytes((0x16, 0, 0, 10)), "get_random_nr", "maximum",
             {"mode": "direct", "value": 10}),
            (bytes((0x96, 0, 0, 1, 0)), "get_random_nr", "maximum",
             {"mode": "variable", "namespace": "global", "index": 1,
              "indexed": False, "index_reference": None}),
            (bytes((0x03, 0, 0, 2)), "get_actor_room", "actor",
             {"mode": "direct", "value": 2}),
            (bytes((0xC3, 0, 0, 1, 0)), "get_actor_x", "actor",
             {"mode": "variable", "namespace": "global", "index": 1,
              "indexed": False, "index_reference": None}),
            (bytes((0x23, 0, 0, 2, 0)), "get_actor_y", "actor",
             {"mode": "direct", "value": 2}),
            (bytes((0x0F, 0, 0, 0x34, 0x12)), "get_object_state", "object",
             {"mode": "direct", "value": 0x1234}),
            (bytes((0x90, 0, 0, 2, 0)), "get_object_owner", "object",
             {"mode": "variable", "namespace": "global", "index": 2,
              "indexed": False, "index_reference": None}),
            (bytes((0x3D, 0, 0, 2, 1)), "find_inventory", "owner",
             {"mode": "direct", "value": 2}),
        )
        for program, operation, argument, expected in cases:
            with self.subTest(operation=operation, program=program.hex()):
                result = decode(program + b"\x00")
                instruction = result.instructions[0]
                operands = dict(instruction.operands)
                self.assertEqual(instruction.operation, operation)
                self.assertEqual(instruction.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(instruction.structural_status, "STRUCTURALLY_DECODED")
                self.assertEqual(operands["result"]["index"], 0)
                self.assertEqual(operands[argument], expected)
                if operation == "get_random_nr":
                    self.assertEqual(operands["range"], "inclusive 0..maximum")
                self.assertEqual(result.instructions[-1].operation, "stop_object_code")

    def test_spatial_and_inventory_query_ir_is_explicit(self) -> None:
        cases = (
            (bytes((0x35, 0, 0, 12, 34)), "find_object", "x", "y",
             {"mode": "direct", "value": 12}, {"mode": "direct", "value": 34}),
            (bytes((0xF5, 0, 0, 1, 0, 2, 0)), "find_object", "x", "y",
             {"mode": "variable", "namespace": "global", "index": 1,
              "indexed": False, "index_reference": None},
             {"mode": "variable", "namespace": "global", "index": 2,
              "indexed": False, "index_reference": None}),
            (bytes((0x15, 0, 0, 12, 0, 34, 0)), "actor_from_pos", "x", "y",
             {"mode": "direct", "value": 12}, {"mode": "direct", "value": 34}),
            (bytes((0xD5, 0, 0, 1, 0, 2, 0)), "actor_from_pos", "x", "y",
             {"mode": "variable", "namespace": "global", "index": 1,
              "indexed": False, "index_reference": None},
             {"mode": "variable", "namespace": "global", "index": 2,
              "indexed": False, "index_reference": None}),
        )
        for program, operation, x_name, y_name, x_value, y_value in cases:
            with self.subTest(operation=operation, program=program.hex()):
                instruction = decode(program + b"\x00").instructions[0]
                operands = dict(instruction.operands)
                self.assertEqual(instruction.operation, operation)
                self.assertEqual(instruction.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(operands["result"]["index"], 0)
                self.assertEqual(operands[x_name], x_value)
                self.assertEqual(operands[y_name], y_value)

    def test_script_and_verb_lifecycle_ir_retains_scumm_operations(self) -> None:
        freeze = decode(bytes((0x60, 0x80, 0xE0, 3, 0, 0))).instructions
        self.assertEqual(freeze[0].operation, "freeze_scripts")
        self.assertEqual(freeze[0].semantic_status, "SEMANTIC_IR_AVAILABLE")
        freeze_ir = dict(freeze[0].operands)
        self.assertEqual(freeze_ir["flag"], {"mode": "direct", "value": 0x80})
        self.assertEqual(freeze_ir["force_freeze_resistant_when_at_least"], 0x80)
        self.assertEqual(freeze[1].operation, "freeze_scripts")
        self.assertEqual(dict(freeze[1].operands)["flag"]["index"], 3)

        save_restore = decode(bytes((0xAB, 2, 1, 3, 5, 0x00))).instructions[0]
        operands = dict(save_restore.operands)
        self.assertEqual(save_restore.operation, "save_restore_verbs")
        self.assertEqual(save_restore.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(operands["command"], "restore")
        self.assertTrue(operands["valid_subopcode"])
        self.assertEqual([operands[key]["value"] for key in
                          ("range_first", "range_last", "bank")], [1, 3, 5])

        save_invalid = decode(bytes((0xAB, 0x82, 1, 3, 5, 0x00))).instructions[0]
        invalid_ir = dict(save_invalid.operands)
        self.assertEqual(invalid_ir["command"], "restore")
        self.assertFalse(invalid_ir["valid_subopcode"])
        self.assertEqual(save_invalid.semantic_status, "SEMANTIC_IR_AVAILABLE")

        find_inventory = decode(bytes((0x3D, 0, 0, 2, 1, 0x00))).instructions[0]
        inventory_ir = dict(find_inventory.operands)
        self.assertEqual(find_inventory.operation, "find_inventory")
        self.assertEqual(inventory_ir["indexing"],
                         "one-based inventory order; zero when absent")

    def test_diagnostic_graphics_and_system_commands_have_explicit_ir(self) -> None:
        debug = decode(bytes((0x6B, 0x34, 0x12, 0x00))).instructions[0]
        self.assertEqual(debug.operation, "debug_log")
        self.assertEqual(debug.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(dict(debug.operands)["value"],
                         {"mode": "direct", "value": 0x1234})

        variable_debug = decode(bytes((0xEB, 4, 0, 0x00))).instructions[0]
        self.assertEqual(dict(variable_debug.operands)["value"]["index"], 4)

        draw = decode(bytes((
            0x3F, 1, 0, 2, 0,       # x1/y1
            0x00,                   # auxiliary selector, all direct
            3, 0, 4, 0, 5,          # x2/y2/color
            0x00,
        ))).instructions[0]
        draw_ir = dict(draw.operands)
        self.assertEqual(draw.operation, "draw_box")
        self.assertEqual(draw.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual([draw_ir[key]["value"] for key in
                          ("x1", "y1", "x2", "y2", "color")],
                         [1, 2, 3, 4, 5])

        system = decode(bytes((0x98, 2, 0x00))).instructions[0]
        self.assertEqual(system.operation, "system_operation")
        self.assertEqual(dict(system.operands)["command"], "pause")

    def test_object_ownership_ir_preserves_all_parameter_flag_variants(self) -> None:
        variants = (
            (0x29, bytes((0x58, 0, 2)), "set_object_owner"),
            (0x69, bytes((0x58, 0, 1, 0)), "set_object_owner"),
            (0xA9, bytes((1, 0, 2)), "set_object_owner"),
            (0xE9, bytes((1, 0, 2, 0)), "set_object_owner"),
            (0x25, bytes((0x58, 0, 2)), "pickup_object"),
            (0x65, bytes((0x58, 0, 1, 0)), "pickup_object"),
            (0xA5, bytes((1, 0, 2)), "pickup_object"),
            (0xE5, bytes((1, 0, 2, 0)), "pickup_object"),
        )
        for opcode, encoded, operation in variants:
            with self.subTest(opcode=f"0x{opcode:02x}"):
                instruction = decode(bytes((opcode,)) + encoded + b"\x80").instructions[0]
                operands = dict(instruction.operands)
                self.assertEqual(instruction.operation, operation)
                self.assertEqual(instruction.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(instruction.structural_status, "STRUCTURALLY_DECODED")
                self.assertEqual(operands["object"]["mode"],
                                 "variable" if opcode & 0x80 else "direct")
                second_name = "owner" if operation == "set_object_owner" else "source_room"
                self.assertEqual(operands[second_name]["mode"],
                                 "variable" if opcode & 0x40 else "direct")
                if operation == "pickup_object":
                    self.assertEqual(operands["recipient"], "VAR_EGO")
                    self.assertEqual(operands["sets_state"], 1)
                    self.assertTrue(operands["adds_untouchable_class"])

    def test_structural_conditional_keeps_branch_target_and_fallthrough(self) -> None:
        result = decode(bytes((0x1D, 1, 0, 0, 2, 0, 0xFF, 0, 0, 0x00)))
        branch = result.instructions[0]
        self.assertEqual(branch.operation, "if_class_of_is")
        self.assertEqual(branch.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(branch.control_flow, "CONDITIONAL_BRANCH")
        self.assertEqual(branch.branch_target, 9)
        self.assertTrue(branch.fallthrough)
        self.assertEqual(branch.structural_status, "STRUCTURALLY_DECODED")
        predicates = dict(branch.operands)["class_predicates"]
        self.assertEqual(predicates, [{
            "class_value": {"mode": "direct", "value": 2},
            "match": "present when bit7 is set; absent otherwise",
        }])

    def test_draw_object_state_and_position_subcommands_have_semantic_ir(self) -> None:
        cases = (
            (bytes((0x05, 0x58, 0, 1, 10, 0, 20, 0)), "draw_at_position"),
            (bytes((0x05, 0x58, 0, 2, 3, 0)), "draw_state"),
            (bytes((0x05, 0x58, 0, 0x1F)), "draw_current_state"),
        )
        for program, draw_operation in cases:
            with self.subTest(operation=draw_operation):
                instruction = decode(program + b"\x00").instructions[0]
                operands = dict(instruction.operands)
                self.assertEqual(instruction.operation, "draw_object")
                self.assertEqual(instruction.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(operands["object"], {"mode": "direct", "value": 0x58})
                self.assertEqual(operands["draw_operation"], draw_operation)

    def test_timer_pseudo_room_and_variable_range_ir(self) -> None:
        delay = decode(bytes((0x2B, 1, 0, 0))).instructions[0]
        self.assertEqual(delay.operation, "delay_variable")
        self.assertEqual(delay.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(dict(delay.operands)["duration_variable"]["index"], 1)

        pseudo = decode(bytes((0xCC, 5, 0x81, 0x82, 0, 0))).instructions
        self.assertEqual(pseudo[0].operation, "pseudo_room_map")
        self.assertEqual(dict(pseudo[0].operands)["mappings"], [
            {"resource_room": 5, "pseudo_room": 0x81},
        ])

        set_range = decode(bytes((0x26, 0, 0, 2, 7, 8, 0))).instructions[0]
        self.assertEqual(set_range.operation, "set_var_range")
        self.assertEqual(dict(set_range.operands)["count"], 2)
        self.assertEqual(dict(set_range.operands)["values"], [7, 8])
        self.assertEqual(dict(set_range.operands)["value_width_bits"], 8)

        # Encoded count zero means 256 entries, not an empty instruction body.
        wide = decode(bytes((0x26, 0, 0, 0)) + bytes(range(256)) + b"\x00")
        self.assertEqual(wide.instructions[0].instruction_width, 260)
        self.assertEqual(dict(wide.instructions[0].operands)["count"], 256)
        self.assertEqual(wide.instructions[1].pc, 260)

    def test_sentence_cutscene_override_and_wait_ir(self) -> None:
        sentence = decode(bytes((0x19, 3, 0x58, 0, 0, 0, 0))).instructions[0]
        sentence_ir = dict(sentence.operands)
        self.assertEqual(sentence.operation, "submit_sentence")
        self.assertEqual(sentence_ir["verb"], {"mode": "direct", "value": 3})
        self.assertEqual(sentence_ir["object_a"]["value"], 0x58)
        self.assertEqual(sentence_ir["object_b"]["value"], 0)

        cancel = decode(bytes((0x19, 0xFE, 0))).instructions[0]
        self.assertEqual(cancel.operation, "cancel_sentence_queue")

        override = decode(bytes((0x58, 1, 0))).instructions[0]
        self.assertEqual(override.operation, "set_cutscene_override")
        self.assertEqual(dict(override.operands)["enabled"], 1)

        waits = (
            (bytes((0xAE, 2)), "message_acknowledged"),
            (bytes((0xAE, 3)), "camera_arrived"),
            (bytes((0xAE, 4)), "sentence_finished"),
            (bytes((0xAE, 0x81, 2, 0)), "actor_stopped"),
        )
        for program, condition in waits:
            with self.subTest(condition=condition):
                wait = decode(program + b"\x00").instructions[0]
                self.assertEqual(wait.operation, "wait")
                self.assertEqual(wait.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(dict(wait.operands)["condition"], condition)

    def test_chain_script_is_a_control_flow_terminator(self) -> None:
        result = decode(b"\x42\x07\xff\x00")
        chain = result.instructions[0]
        self.assertEqual(chain.operation, "chain_script")
        self.assertEqual(chain.control_flow, "TERMINATOR")
        self.assertFalse(chain.fallthrough)
        # Linear structural census still records following source bytes, while
        # graph traversal must not treat them as continuation of this activation.
        self.assertEqual(result.instructions[1].pc, 3)
        self.assertTrue(result.decode_complete)

    def test_unregistered_opcode_is_structural_unknown_not_semantic_unsupported(self) -> None:
        result = decode(b"\x2f\x0a\x02\xff")
        tail = result.instructions[0]
        self.assertEqual(tail.structural_status, "STRUCTURAL_UNKNOWN")
        self.assertEqual(tail.semantic_status, "SEMANTIC_UNKNOWN")
        self.assertFalse(tail.boundary_known)
        self.assertEqual(result.opaque_from_pc, 0)
        self.assertFalse(result.decode_complete)

    def test_unknown_print_selector_is_reported_at_its_actual_operand_position(self) -> None:
        result = decode(b"\x14\x02\x0d\xaa\xbb")
        tail = result.instructions[0]
        self.assertEqual(tail.opcode, 0x14)
        self.assertEqual(tail.subopcode, 0x0D)
        self.assertEqual(tail.structural_status, "STRUCTURAL_UNKNOWN")
        self.assertEqual(tail.raw_operand_hex, "020daabb")

    def test_known_opcode_with_truncated_operands_is_malformed_boundary(self) -> None:
        result = decode(b"\x18\x01")
        tail = result.instructions[0]
        self.assertEqual(tail.structural_status, "TRUNCATED")
        self.assertEqual(tail.opcode_family, "jumpRelative")
        self.assertFalse(tail.boundary_known)
        self.assertEqual(result.opaque_from_pc, 0)

    def test_verb_name_selector_consumes_helper_loaded_string(self) -> None:
        result = decode(b"\x7a\x64\x02Open\x00\xff\x0a\x03\xff\x00")
        verb = result.instructions[0]
        self.assertEqual(verb.operation, "verb_ops")
        self.assertEqual(verb.structural_status, "STRUCTURALLY_DECODED")
        self.assertEqual(verb.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(verb.instruction_width, 9)
        self.assertEqual(dict(verb.operands)["commands"],
                         [{"subopcode": 2, "operation": "set_inline_name",
                           "parameter_flags": 0,
                           "encoded_name_hex": b"Open\x00".hex()}])
        self.assertEqual((result.instructions[1].pc, result.instructions[1].operation),
                         (9, "start_script"))
        self.assertEqual((result.instructions[2].pc, result.instructions[2].operation),
                         (12, "stop_object_code"))

    def test_actor_name_command_consumes_its_inline_string(self) -> None:
        result = decode(b"\x13\x01\x0dIndy\x00\xff\x00")
        actor_ops = result.instructions[0]
        self.assertEqual(actor_ops.operation, "actor_ops")
        self.assertEqual(actor_ops.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(actor_ops.instruction_width, 9)
        command = dict(actor_ops.operands)["commands"][0]
        self.assertEqual(command["operation"], "set_actor_name")
        self.assertEqual(command["resource_kind"], "actor_name")
        self.assertEqual(command["encoded_name_hex"], b"Indy\x00".hex())
        self.assertEqual((result.instructions[1].pc,
                          result.instructions[1].operation), (9, "stop_object_code"))

    def test_actor_and_object_movement_ir_names_operands(self) -> None:
        cases = (
            (bytes((0x0E, 2, 0x58, 0)), "put_actor_at_object",
             {"actor": {"mode": "direct", "value": 2},
              "object": {"mode": "direct", "value": 0x58},
              "operation": "put_actor_at_object"}),
            (bytes((0x36, 2, 0x58, 0)), "walk_actor_to_object",
             {"actor": {"mode": "direct", "value": 2},
              "object": {"mode": "direct", "value": 0x58},
              "operation": "walk_actor_to_object"}),
            (bytes((0x09, 2, 0x58, 0)), "face_actor",
             {"actor": {"mode": "direct", "value": 2},
              "object_or_actor": {"mode": "direct", "value": 0x58},
              "operation": "face_actor"}),
        )
        for program, operation, expected in cases:
            with self.subTest(operation=operation):
                instruction = decode(program + b"\x00").instructions[0]
                self.assertEqual(instruction.operation, operation)
                self.assertEqual(instruction.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(dict(instruction.operands), expected)

    def test_room_save_load_string_have_known_structural_width(self) -> None:
        for selector in (13, 14):
            with self.subTest(selector=selector):
                program = bytes((0x33, selector, 0x05)) + b"TARGET.iq\x00\x00"
                result = decode(program)
                room_ops = result.instructions[0]
                self.assertEqual(room_ops.operation, "room_ops")
                self.assertEqual(room_ops.semantic_status, "SEMANTIC_IR_AVAILABLE")
                self.assertEqual(room_ops.structural_status, "STRUCTURALLY_DECODED")
                self.assertEqual(room_ops.instruction_width, 13)
                self.assertEqual(dict(room_ops.operands)["filename_hex"],
                                 b"TARGET.iq\x00".hex())
                self.assertEqual((result.instructions[1].pc,
                                  result.instructions[1].operation),
                                 (13, "stop_object_code"))

    def test_room_transform_and_cycle_speed_keep_operand_boundaries(self) -> None:
        transform = decode(b"\x33\x0f\x03\x81\x02\x83\x04\x00\x00\x00")
        self.assertEqual(transform.instructions[0].instruction_width, 9)
        self.assertEqual((transform.instructions[1].pc,
                          transform.instructions[1].operation), (9, "stop_object_code"))

        cycle = decode(b"\x33\x90\x02\x03\x00\x00")
        self.assertEqual(cycle.instructions[0].instruction_width, 5)
        self.assertEqual((cycle.instructions[1].pc,
                          cycle.instructions[1].operation), (5, "stop_object_code"))

    def test_set_object_name_consumes_helper_loaded_string(self) -> None:
        result = decode(b"\xd4\x34\x12widget\x00\x00")
        self.assertEqual(result.instructions[0].operation, "set_object_name")
        self.assertEqual(result.instructions[0].semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(result.instructions[0].instruction_width, 10)
        self.assertEqual(result.instructions[0].parameter_flags, 0x80)
        self.assertEqual(dict(result.instructions[0].operands)["encoded_name_hex"],
                         b"widget\x00".hex())
        self.assertEqual(dict(result.instructions[0].operands)["object"], {
            "mode": "variable", "namespace": "global", "index": 0x234,
            "indexed": False, "index_reference": None,
        })
        self.assertEqual(result.instructions[1].pc, 10)

    def test_pseudo_room_pair_layout_keeps_following_instruction(self) -> None:
        result = decode(b"\xcc\x11\x81\x22\x82\x00\x00\x00")
        pseudo_room = result.instructions[0]
        self.assertEqual(pseudo_room.operation, "pseudo_room_map")
        self.assertEqual(pseudo_room.semantic_status, "SEMANTIC_IR_AVAILABLE")
        self.assertEqual(pseudo_room.instruction_width, 7)
        self.assertEqual(dict(pseudo_room.operands)["mappings"], [
            {"resource_room": 17, "pseudo_room": 129},
            {"resource_room": 34, "pseudo_room": 130},
        ])
        self.assertEqual((result.instructions[1].pc, result.instructions[1].operation),
                         (7, "stop_object_code"))


if __name__ == "__main__":
    unittest.main()
