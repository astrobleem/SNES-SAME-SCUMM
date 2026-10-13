#!/usr/bin/env python3
"""Determinism and corruption regression for the redistributable demo package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from same.errors import PackageFormatError
from same.package import build_package, inspect_package


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "examples/packages/demo-package.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    declared_names = [str(row["name"]) for row in manifest["sections"]]
    with tempfile.TemporaryDirectory(prefix="samepkg-ci-") as temporary:
        root = Path(temporary)
        outputs = []
        for name in ("first", "independent-second"):
            directory = root / name
            package = directory / "demo.samepkg"
            include = directory / "demo-package.inc.pasm"
            info = build_package(MANIFEST, package, include)
            verified = inspect_package(package, verify=True)
            observed_names = [section.name for section in verified.sections]
            if observed_names != declared_names:
                raise SystemExit(
                    f"declared package sections differ: {declared_names} != {observed_names}"
                )
            outputs.append((package, include, info))
        first, second = outputs
        if sha256(first[0]) != sha256(second[0]):
            raise SystemExit("independent SAMEPKG builds differ")
        if sha256(first[1]) != sha256(second[1]):
            raise SystemExit("independent generated Poppy includes differ")

        corrupted = root / "corrupt.samepkg"
        raw = bytearray(first[0].read_bytes())
        raw[first[2].sections[0].offset] ^= 0x01
        corrupted.write_bytes(raw)
        try:
            inspect_package(corrupted, verify=True)
        except PackageFormatError:
            pass
        else:
            raise SystemExit("corrupted package payload was accepted")

        print(json.dumps({
            "result": "PASS",
            "package_sha256": sha256(first[0]),
            "poppy_include_sha256": sha256(first[1]),
            "sections": declared_names,
            "corruption_rejected": True,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
