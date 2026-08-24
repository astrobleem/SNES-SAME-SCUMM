#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

REQUIRED_ANCESTOR = "ec005c196eedabf7d0c25ff6336398c427dd43ac"
REQUIRED_REPOSITORY = "astrobleem/poppy"


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
    if not (root / ".git").exists():
        parser.error(f"{root} is not a Git checkout")
    origin = git(root, "config", "--get", "remote.origin.url").stdout.strip().lower()
    normalized = origin.removesuffix(".git").replace(":", "/")
    if REQUIRED_REPOSITORY not in normalized:
        parser.error(f"Poppy origin is {origin!r}; SAME requires {REQUIRED_REPOSITORY}")
    ancestor = git(root, "merge-base", "--is-ancestor", REQUIRED_ANCESTOR, "HEAD", check=False)
    if ancestor.returncode != 0:
        head = git(root, "rev-parse", "HEAD").stdout.strip()
        parser.error(f"Poppy HEAD {head} does not contain required fix {REQUIRED_ANCESTOR}")
    dll = args.dll or root / "src/Poppy.CLI/bin/Release/net10.0/poppy.dll"
    if not dll.is_file():
        parser.error(f"Poppy CLI not built: {dll}")
    head = git(root, "rev-parse", "HEAD").stdout.strip()
    print(f"Poppy fork OK: {head}")
    print(dll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
