#!/usr/bin/env python3
"""Write a deterministic manifest of every Poppy include and incbin input."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from lint_poppy import include_closure


INCBIN = re.compile(r'^\s*\.incbin\s+"([^"]+)"', re.IGNORECASE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def manifest(root: Path, main: Path) -> dict[str, object]:
    root = root.resolve()
    main = (root / main).resolve() if not main.is_absolute() else main.resolve()
    assembly = include_closure(main)
    inputs: dict[str, dict[str, object]] = {}

    def add(path: Path, kind: str) -> None:
        path = path.resolve()
        if not path.is_file():
            raise RuntimeError(f"Poppy input does not exist: {path}")
        digest = sha256(path)
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            # Do not leak machine-specific absolute paths into deterministic
            # evidence. Content identity is the portable external-input key.
            name = f"external/{digest}/{path.name}"
        previous = inputs.get(name)
        row = {"path": name, "kind": kind, "size": path.stat().st_size,
               "sha256": digest}
        if previous is not None and previous != row:
            raise RuntimeError(f"ambiguous Poppy input identity: {name}")
        inputs[name] = row

    for source in assembly:
        add(source, "ASSEMBLY_INCLUDE")
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            match = INCBIN.match(line.split(";", 1)[0])
            if not match:
                continue
            binary = Path(match.group(1))
            if not binary.is_absolute():
                binary = source.parent / binary
            if not binary.is_file():
                raise RuntimeError(f"missing .incbin at {source}:{line_number}: {binary}")
            add(binary, "BINARY_INCBIN")

    rows = [inputs[key] for key in sorted(inputs)]
    return {"schema": "same_poppy_input_manifest_v1",
            "main": main.relative_to(root).as_posix(),
            "input_count": len(rows), "inputs": rows}


def main_cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--main", type=Path, default=Path("runtime/snes/main.pasm"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        data = manifest(args.root, args.main)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Poppy input manifest: FAIL: {exc}", file=sys.stderr)
        return 1
    output = args.output if args.output.is_absolute() else args.root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps({"result": "pass", "input_count": data["input_count"],
                      "manifest": output.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
