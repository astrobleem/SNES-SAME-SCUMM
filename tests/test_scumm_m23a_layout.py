from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def symbols() -> dict[str, int]:
    source = (ROOT / "runtime/snes/kernel/memory.pasm").read_text()
    return {
        name: int(value, 16)
        for name, value in re.findall(
            r"^(SAME_SCUMM_[A-Z0-9_]+)\s*=\s*\$([0-9A-Fa-f]+)",
            source,
            re.MULTILINE,
        )
    }


class M23AReturnLayoutTests(unittest.TestCase):
    def test_return_bytes_are_outside_storage_scratch_and_variable_table(self) -> None:
        address = symbols()
        return_fields = {
            address["SAME_SCUMM_M23A_RETURN_VALID"],
            address["SAME_SCUMM_M23A_RETURN_SLOT"],
            address["SAME_SCUMM_M23A_RETURN_MODE"],
        }
        self.assertEqual(len(return_fields), 3)
        self.assertEqual(
            return_fields,
            {0x7FF467, 0x7FF468, 0x7FF469},
        )

        # Storage validation clears/checks the two-byte checksum scratch at
        # $7FF2D0 and performs a 16-bit $0104 store at $7FF2D2.
        scratch = range(address["SAME_SCUMM_M23A_CHECKSUM"],
                        address["SAME_SCUMM_M23A_BYTE"] + 2)
        self.assertTrue(return_fields.isdisjoint(scratch))

        # Authored profiles place the generated word-variable table at
        # $7FF500; return metadata is before that table and beyond the M23B
        # state block, rather than inside its bulk reset extent.
        self.assertGreaterEqual(
            min(return_fields), address["SAME_SCUMM_M23B_STATE_END"]
        )
        self.assertLess(max(return_fields), address["SAME_SCUMM_M23B_VARIABLES"])

    def test_storage_validation_word_write_preserves_return_metadata(self) -> None:
        address = symbols()
        base = address["SAME_SCUMM_M23A_BYTE"]
        valid = address["SAME_SCUMM_M23A_RETURN_VALID"]
        slot = address["SAME_SCUMM_M23A_RETURN_SLOT"]
        mode = address["SAME_SCUMM_M23A_RETURN_MODE"]

        # Model the exact little-endian 16-bit STA #$0104 used by the storage
        # service, with a live global continuation and an invalid local one.
        memory = bytearray(0x200)
        memory[valid - base : mode - base + 1] = bytes((1, 7, 1))
        memory[base - base : base - base + 2] = (0x0104).to_bytes(2, "little")
        self.assertEqual(memory[valid - base : mode - base + 1], bytes((1, 7, 1)))

        memory[valid - base : mode - base + 1] = bytes((0, 0, 0))
        memory[base - base : base - base + 2] = (0x0104).to_bytes(2, "little")
        self.assertEqual(memory[valid - base : mode - base + 1], bytes((0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
