#!/usr/bin/env python3
"""Build the pinned, narrowly extended TAD compiler used by M22."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DONOR_COMMIT = "822164b09cb3d4750bd4c1960a430dc35b6ae04a"
SOURCE_HASHES = {
    "audio-driver/src/audio-driver.asm": "547cd71bc5082de85703ec7cf98c2aab6f7c3fe01d06baa1b6e66cc0df62c79a",
    "audio-driver/src/io-commands.inc": "d6bb6f8f1b84de02ad54c2e32767073dae4da98dbe520146ebdcf441f54926cb",
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
    patch = ROOT / "audio/fate_s6/m22_sound80/terrific_audio_driver_m22.patch"
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=output, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=output, check=True)
    subprocess.run(["cargo", "build", "--release", "-p", "tad-compiler"], cwd=output, check=True)
    compiler = output / "target/release/tad-compiler"
    print(f"compiler={compiler} sha256={digest(compiler)} donor={commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
