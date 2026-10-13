#!/usr/bin/env python3
"""Verify the pinned public Poppy/Pansy source and reproducible compiler binary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN_FILE = Path(__file__).with_name("poppy_pin.json")


def git(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *arguments], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def verify_checkout(root: Path, repository: str, commit: str, label: str) -> None:
    if not (root / ".git").exists():
        raise SystemExit(f"{label} checkout is missing: {root}")
    origin = git(root, "config", "--get", "remote.origin.url").lower()
    normalized = origin.removesuffix(".git").replace(":", "/")
    if repository.lower() not in normalized:
        raise SystemExit(f"{label} origin {origin!r} does not match {repository}")
    head = git(root, "rev-parse", "HEAD")
    if head != commit:
        raise SystemExit(f"{label} HEAD {head} does not match pinned {commit}")
    print(f"{label} source OK: {head}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--dll", type=Path)
    args = parser.parse_args()
    pin = json.loads(PIN_FILE.read_text(encoding="utf-8"))
    root = args.root.expanduser().resolve()
    verify_checkout(root, pin["repository"], pin["commit"], "Poppy")
    verify_checkout(root.parent / "pansy", pin["pansy_repository"],
                    pin["pansy_commit"], "Pansy")
    dll = args.dll or root / "src/Poppy.CLI/bin/Release/net10.0/poppy.dll"
    if not dll.is_file():
        raise SystemExit(f"Poppy CLI was not built: {dll}")
    observed = hashlib.sha256(dll.read_bytes()).hexdigest()
    if observed != pin["dll_sha256"]:
        raise SystemExit(
            f"Poppy DLL SHA-256 {observed} does not match pinned {pin['dll_sha256']}"
        )
    print(f"Poppy DLL SHA-256: {observed}")
    print(dll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
