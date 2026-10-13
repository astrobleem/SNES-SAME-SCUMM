from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.package_scumm_v5_source_msu import (
    directory_endpoint_probe,
    exact_room_code_duplication,
    main as package_main,
    normalize_build_paths,
)


def _hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class _Directory:
    def __init__(self, entries):
        self.document = {"entries": entries, "selector_values_emitted": False}


class WholeSourcePackageTests(unittest.TestCase):
    def test_first_middle_last_directory_probes_keep_canonical_ids(self) -> None:
        entries = [{
            "program_unit_id": index,
            "identity": f"GlobalProgram({index + 1})",
            "length": index + 3,
            "sha256": f"{index:064x}",
        } for index in range(5)]
        storage = {"records": [{
            "program_unit_id": index,
            "identity": row["identity"],
            "length": row["length"],
            "sha256": row["sha256"],
            "package_section": "SC5CODE",
            "page_count": 1,
        } for index, row in enumerate(entries)]}
        result = directory_endpoint_probe(_Directory(entries), storage)
        self.assertEqual([row["program_unit_id"] for row in result["probes"]], [0, 2, 4])
        self.assertEqual(result["status"],
                         "ALL_ENTRIES_RECONCILED; FIRST_MIDDLE_LAST_PROBED")

    def test_exact_room_code_duplicates_are_measured_and_verified(self) -> None:
        entry = b"room entry bytes"
        local = b"room local bytes"
        object_body = b"object carrier bytes"
        record = entry + local + object_body
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "room.sc5c").write_bytes(record)
            cooked = {"records": [{
                "room": 4,
                "output": "room.sc5c",
                "scripts": [
                    {"kind": "ENCD", "number": 10002,
                     "cooked_record_offset": 0, "program_length": len(entry),
                     "sha256": _hash(entry)},
                    {"kind": "LSCR", "number": 207,
                     "cooked_record_offset": len(entry), "program_length": len(local),
                     "sha256": _hash(local)},
                ],
                "objects": [{"object_id": 118,
                             "cooked_record_offset": len(entry) + len(local),
                             "obcd_length": len(object_body),
                             "obcd_sha256": _hash(object_body)}],
            }]}
            storage = {"records": [
                {"identity": "RoomEntryProgram(4)", "length": len(entry),
                 "sha256": _hash(entry)},
                {"identity": "RoomLocalProgram(room=4,local=207)",
                 "length": len(local), "sha256": _hash(local)},
                {"identity": "ObjectProgram(room=4,object=118)",
                 "length": len(object_body), "sha256": _hash(object_body)},
            ]}
            result = exact_room_code_duplication(root, cooked, storage)
        self.assertEqual(result["program_unit_body_records_exactly_repeated_in_sc5room"], 3)
        self.assertEqual(result["exact_repeated_body_bytes"],
                         len(entry) + len(local) + len(object_body))

    def test_room_code_duplicate_must_match_carrier_body_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "room.sc5c").write_bytes(b"source")
            cooked = {"records": [{
                "room": 1, "output": "room.sc5c",
                "scripts": [{"kind": "ENCD", "number": 0,
                             "cooked_record_offset": 0, "program_length": 6,
                             "sha256": _hash(b"source")}],
            }]}
            storage = {"records": [{
                "identity": "RoomEntryProgram(1)", "length": 6,
                "sha256": _hash(b"different"),
            }]}
            with self.assertRaisesRegex(ValueError, "disagree"):
                exact_room_code_duplication(root, cooked, storage)

    def test_build_path_normalization_removes_only_paths_inside_build_root(self) -> None:
        root = Path("/tmp/build-root")
        value = {"inside": str(root / "package" / "file.bin"),
                 "external": "/home/source/archive.zip"}
        result = normalize_build_paths(value, root)
        self.assertEqual(result["inside"], "package/file.bin")
        self.assertEqual(result["external"], "/home/source/archive.zip")

    def test_nonempty_build_root_is_rejected_without_consuming_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.zip"
            profile = root / "profile.json"
            source.write_bytes(b"synthetic source placeholder")
            profile.write_text("{}", encoding="utf-8")
            output = root / "output"
            output.mkdir()
            stale = output / "room-legacy.seg"
            stale.write_bytes(b"must remain untouched")
            argv = [
                "package_scumm_v5_source_msu.py",
                "--source", str(source),
                "--profile", str(profile),
                "--output", str(output),
            ]
            with mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit) as raised:
                    package_main()
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(stale.read_bytes(), b"must remain untouched")

    def test_invalid_selected_comparison_is_rejected_before_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.zip"
            profile = root / "profile.json"
            source.write_bytes(b"synthetic source placeholder")
            profile.write_text("{}", encoding="utf-8")
            output = root / "new-output"
            argv = [
                "package_scumm_v5_source_msu.py",
                "--source", str(source),
                "--profile", str(profile),
                "--output", str(output),
                "--compare-program-storage", str(root / "missing-storage.json"),
            ]
            with mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit) as raised:
                    package_main()
            self.assertEqual(raised.exception.code, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
