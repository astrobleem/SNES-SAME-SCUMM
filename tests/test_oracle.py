from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from same.oracle import (
    OracleRecord,
    compare_records,
    read_records,
    record_from_files,
    write_records,
)

H1 = "1" * 64
H2 = "2" * 64


class OracleTests(unittest.TestCase):
    def test_exact_pass(self) -> None:
        expected = [OracleRecord(0, state=H1, video=H2, identity="rom:a")]
        comparison = compare_records(expected, list(expected))
        self.assertEqual(comparison.status, "PASS")
        self.assertEqual(comparison.matched, 2)

    def test_mismatch_fails(self) -> None:
        expected = [OracleRecord(0, state=H1)]
        actual = [OracleRecord(0, state=H2)]
        self.assertEqual(compare_records(expected, actual).status, "FAIL")

    def test_missing_required_evidence_is_unknown(self) -> None:
        expected = [OracleRecord(0, state=H1, video=H2)]
        actual = [OracleRecord(0, state=H1)]
        comparison = compare_records(expected, actual)
        self.assertEqual(comparison.status, "UNKNOWN")
        self.assertEqual(comparison.unknown, 1)

    def test_missing_required_identity_is_unknown(self) -> None:
        expected = [OracleRecord(0, state=H1, identity="rom:a")]
        actual = [OracleRecord(0, state=H1)]
        comparison = compare_records(expected, actual)
        self.assertEqual(comparison.status, "UNKNOWN")
        self.assertEqual(comparison.unknown, 1)

    def test_extra_tick_fails(self) -> None:
        expected = [OracleRecord(0, state=H1)]
        actual = [OracleRecord(0, state=H1), OracleRecord(1, state=H1)]
        self.assertEqual(compare_records(expected, actual).status, "FAIL")

    def test_file_record_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state.bin"
            state.write_bytes(b"state")
            record = record_from_files(tick=7, identity="demo", state=state)
            oracle = root / "oracle.jsonl"
            write_records(oracle, [record])
            self.assertEqual(read_records(oracle), [record])


if __name__ == "__main__":
    unittest.main()
