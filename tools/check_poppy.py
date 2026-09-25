#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PIN_FILE = Path(__file__).with_name("poppy_pin.json")


def git(root: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Refuse to build SAME with the wrong Poppy fork")
    parser.add_argument("root", type=Path)
    parser.add_argument("--dll", type=Path)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    pin = json.loads(PIN_FILE.read_text())
    if not (root / ".git").exists():
        parser.error(f"{root} is not a Git checkout")
    origin = git(root, "config", "--get", "remote.origin.url").stdout.strip().lower()
    normalized = origin.removesuffix(".git").replace(":", "/")
    if pin["repository"] not in normalized:
        parser.error(f"Poppy origin is {origin!r}; SAME requires {pin['repository']}")
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    if head != pin["commit"]:
        parser.error(f"Poppy HEAD {head} does not match pinned source {pin['commit']}")
    dll = args.dll or root / "src/Poppy.CLI/bin/Release/net10.0/poppy.dll"
    if not dll.is_file():
        parser.error(f"Poppy CLI not built: {dll}")
    observed = hashlib.sha256(dll.read_bytes()).hexdigest()
    if observed != pin["dll_sha256"]:
        parser.error(f"Poppy DLL {observed} does not match pinned SHA-256 {pin['dll_sha256']}")
    print(f"Poppy source OK: {head}")
    print(f"Poppy DLL SHA-256: {observed}")
    print(dll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
