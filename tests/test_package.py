from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from same.errors import PackageFormatError
from same.package import build_package, extract_package, inspect_package


class PackageTests(unittest.TestCase):
    def make_manifest(self, root: Path) -> Path:
        (root / "a.bin").write_bytes(b"alpha")
        (root / "b.bin").write_bytes(bytes(range(64)))
        manifest = {
            "same_package": 1,
            "sections": [
                {"name": "CODE", "kind": "CODE", "path": "a.bin", "alignment": 256, "flags": ["executable"]},
                {"name": "VIDEO", "kind": "VDAT", "path": "b.bin", "alignment": 512, "flags": ["streamable"]},
            ],
        }
        path = root / "package.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_build_inspect_extract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "demo.samepkg"
            include = root / "package.inc.pasm"
            info = build_package(self.make_manifest(root), package, include)
            self.assertEqual(len(info.sections), 2)
            self.assertEqual(info.sections[0].offset % 256, 0)
            self.assertEqual(info.sections[1].offset % 512, 0)
            self.assertEqual(inspect_package(package), info)
            output = root / "extract"
            extract_package(package, output)
            self.assertEqual((output / "CODE").read_bytes(), b"alpha")
            self.assertEqual((output / "VIDEO").read_bytes(), bytes(range(64)))
            self.assertIn("SAME_PKG_CODE_OFFSET", include.read_text())

    def test_corruption_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "demo.samepkg"
            build_package(self.make_manifest(root), package)
            raw = bytearray(package.read_bytes())
            raw[-1] ^= 0xFF
            package.write_bytes(raw)
            with self.assertRaises(PackageFormatError):
                inspect_package(package)

    def test_duplicate_names_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = self.make_manifest(root)
            manifest = json.loads(manifest_path.read_text())
            manifest["sections"][1]["name"] = "CODE"
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(PackageFormatError):
                build_package(manifest_path, root / "bad.samepkg")


if __name__ == "__main__":
    unittest.main()
