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

    def test_known_width_semantic_unsupported_string_op_keeps_next_boundary(self) -> None:
        result = decode(b"\x27\x01\x25note\0\x0a\x02\xff\x00")
        string_op, start, stop = result.instructions
        self.assertEqual(string_op.operation, "structural_only:stringOps")
        self.assertEqual(string_op.structural_status, "STRUCTURALLY_DECODED")
        self.assertEqual(string_op.semantic_status, "SEMANTIC_UNSUPPORTED")
        self.assertEqual(string_op.instruction_width, 8)
        self.assertEqual(string_op.raw_operand_hex, "01256e6f746500")
        self.assertEqual((start.pc, start.operation), (8, "start_script"))
        self.assertEqual((stop.pc, stop.operation), (11, "stop_script"))
        self.assertTrue(result.decode_complete)
        self.assertIsNone(result.opaque_from_pc)

    def test_structural_conditional_keeps_branch_target_and_fallthrough(self) -> None:
        result = decode(bytes((0x1D, 1, 0, 0, 2, 0, 0xFF, 0, 0, 0x00)))
        branch = result.instructions[0]
        self.assertEqual(branch.operation, "structural_only:ifClassOfIs")
        self.assertEqual(branch.control_flow, "CONDITIONAL_BRANCH")
        self.assertEqual(branch.branch_target, 9)
        self.assertTrue(branch.fallthrough)
        self.assertEqual(branch.structural_status, "STRUCTURALLY_DECODED")

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
        self.assertEqual(verb.operation, "structural_only:verbOps")
        self.assertEqual(verb.structural_status, "STRUCTURALLY_DECODED")
        self.assertEqual(verb.instruction_width, 9)
        self.assertEqual(dict(verb.operands)["commands"],
                         [{"subopcode": 2, "values": [b"Open\x00".hex()]}])
        self.assertEqual((result.instructions[1].pc, result.instructions[1].operation),
                         (9, "start_script"))
        self.assertEqual((result.instructions[2].pc, result.instructions[2].operation),
                         (12, "stop_script"))

    def test_actor_name_command_consumes_its_inline_string(self) -> None:
        result = decode(b"\x13\x01\x0dIndy\x00\xff\x00")
        actor_ops = result.instructions[0]
        self.assertEqual(actor_ops.operation, "structural_only:actorOps")
        self.assertEqual(actor_ops.instruction_width, 9)
        self.assertEqual(dict(actor_ops.operands)["commands"],
                         [{"subopcode": 13, "values": [b"Indy\x00".hex()]}])
        self.assertEqual((result.instructions[1].pc,
                          result.instructions[1].operation), (9, "stop_script"))

    def test_room_save_load_string_have_known_structural_width(self) -> None:
        for selector in (13, 14):
            with self.subTest(selector=selector):
                program = bytes((0x33, selector, 0x05)) + b"TARGET.iq\x00\x00"
                result = decode(program)
                room_ops = result.instructions[0]
                self.assertEqual(room_ops.operation, "structural_only:roomOps")
                self.assertEqual(room_ops.semantic_status, "SEMANTIC_UNSUPPORTED")
                self.assertEqual(room_ops.structural_status, "STRUCTURALLY_DECODED")
                self.assertEqual(room_ops.instruction_width, 13)
                self.assertEqual(dict(room_ops.operands)["filename_hex"],
                                 b"TARGET.iq\x00".hex())
                self.assertEqual((result.instructions[1].pc,
                                  result.instructions[1].operation),
                                 (13, "stop_script"))

    def test_room_transform_and_cycle_speed_keep_operand_boundaries(self) -> None:
        transform = decode(b"\x33\x0f\x03\x81\x02\x83\x04\x00\x00\x00")
        self.assertEqual(transform.instructions[0].instruction_width, 9)
        self.assertEqual((transform.instructions[1].pc,
                          transform.instructions[1].operation), (9, "stop_script"))

        cycle = decode(b"\x33\x90\x02\x03\x00\x00")
        self.assertEqual(cycle.instructions[0].instruction_width, 5)
        self.assertEqual((cycle.instructions[1].pc,
                          cycle.instructions[1].operation), (5, "stop_script"))

    def test_set_object_name_consumes_helper_loaded_string(self) -> None:
        result = decode(b"\xd4\x34\x12widget\x00\x00")
        self.assertEqual(result.instructions[0].operation,
                         "structural_only:setObjectName")
        self.assertEqual(result.instructions[0].instruction_width, 10)
        self.assertEqual(result.instructions[0].parameter_flags, 0x80)
        self.assertEqual(dict(result.instructions[0].operands)["operand_1"],
                         b"widget\x00".hex())
        self.assertEqual(result.instructions[1].pc, 10)

    def test_pseudo_room_pair_layout_keeps_following_instruction(self) -> None:
        result = decode(b"\xcc\x11\x81\x22\x82\x00\x00\x00")
        pseudo_room = result.instructions[0]
        self.assertEqual(pseudo_room.operation, "structural_only:pseudoRoom")
        self.assertEqual(pseudo_room.instruction_width, 7)
        self.assertEqual(dict(pseudo_room.operands)["room_map"], [(17, 129), (34, 130)])
        self.assertEqual((result.instructions[1].pc, result.instructions[1].operation),
                         (7, "stop_script"))


if __name__ == "__main__":
    unittest.main()
