#!/usr/bin/env python3
"""Build the pinned TAD compiler with SAME's isolated M24R-A patch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DONOR_COMMIT = "822164b09cb3d4750bd4c1960a430dc35b6ae04a"
SOURCE_HASHES = {
    "audio-driver/src/audio-driver.asm": "547cd71bc5082de85703ec7cf98c2aab6f7c3fe01d06baa1b6e66cc0df62c79a",
    "audio-driver/src/io-commands.inc": "d6bb6f8f1b84de02ad54c2e32767073dae4da98dbe520146ebdcf441f54926cb",
    "audio-driver/src/common-memmap.inc": "a51f097f97f733ee3fc0f89e8835cba104461f2f96bf6187a084e787c6c2a806",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--donor", type=Path, default=Path("/home/chad/terrific-audio-driver"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    donor, output = args.donor.resolve(), args.output.resolve()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=donor, text=True).strip()
    if commit != DONOR_COMMIT:
        raise RuntimeError(f"TAD donor commit differs: {commit}")
    for relative, expected in SOURCE_HASHES.items():
        actual = digest(donor / relative)
        if actual != expected:
            raise RuntimeError(f"TAD donor {relative} differs: {actual}")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(donor, output, ignore=shutil.ignore_patterns("target", ".git"))
    patch = ROOT / "audio/m24ra/terrific_audio_driver_m24ra.patch"
    # The output normally lives under SAME's ignored build/ directory.  `git
    # apply` would discover the parent repository and silently scope paths to
    # that worktree instead of this copied donor.  POSIX patch operates on the
    # explicit copied-tree cwd and therefore preserves the intended isolation.
    with patch.open("rb") as stream:
        subprocess.run(["patch", "-p1", "--dry-run"], cwd=output, stdin=stream, check=True)
    with patch.open("rb") as stream:
        subprocess.run(["patch", "-p1"], cwd=output, stdin=stream, check=True)
    subprocess.run(["cargo", "build", "--release", "-p", "tad-compiler"], cwd=output, check=True)
    compiler = output / "target/release/tad-compiler"
    report = {
        "schema": "same_m24ra_tad_toolchain_v1",
        "donor_commit": commit,
        "source_hashes": SOURCE_HASHES,
        "patch_sha256": digest(patch),
        "compiler_sha256": digest(compiler),
        "new_driver_state_bytes": 13,
        "admission_table_bytes": 10,
        "reserved_code_page_bytes": 256,
    }
    report_path = output / "same-m24ra-toolchain.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"compiler={compiler} sha256={report['compiler_sha256']} donor={commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
