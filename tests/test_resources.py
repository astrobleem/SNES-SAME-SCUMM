from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from same.errors import ResourceError
from same.package import build_package
from same.profile import ResourceBinding
from same.resources import (
    BoundResourceProvider,
    CompositeResourceProvider,
    MemoryResourceProvider,
)


class ResourceTests(unittest.TestCase):
    def test_memory_provider_slice_and_stat(self) -> None:
        provider = MemoryResourceProvider({"alpha": b"abcdef"}, kinds={"alpha": "TEST"})
        self.assertEqual(provider.read("alpha", 2, 3), b"cde")
        stat = provider.stat("alpha")
        self.assertEqual(stat.size, 6)
        self.assertEqual(stat.kind, "TEST")
        self.assertIsNotNone(stat.crc32)

    def test_bound_file_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "raw.bin"
            path.write_bytes(b"resource")
            provider = BoundResourceProvider(
                [ResourceBinding("raw", path, kind="TEST")]
            )
            self.assertEqual(provider.read("raw"), b"resource")
            self.assertIn(str(path), provider.stat("raw").source)

    def test_bound_package_section_provider(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "payload.bin").write_bytes(b"inside-package")
            manifest = root / "package.json"
            manifest.write_text(
                json.dumps(
                    {
                        "same_package": 1,
                        "sections": [
                            {
                                "name": "payload",
                                "kind": "TEST",
                                "path": "payload.bin",
                                "alignment": 16,
                            }
                        ],
                    }
                )
            )
            package = root / "data.samepkg"
            build_package(manifest, package)
            provider = BoundResourceProvider(
                [
                    ResourceBinding(
                        "resource", package, kind="TEST", package_section="payload"
                    )
                ]
            )
            self.assertEqual(provider.read("resource"), b"inside-package")

    def test_composite_rejects_ambiguous_keys(self) -> None:
        one = MemoryResourceProvider({"same": b"1"})
        two = MemoryResourceProvider({"same": b"2"})
        with self.assertRaises(ResourceError):
            CompositeResourceProvider([one, two])


if __name__ == "__main__":
    unittest.main()
