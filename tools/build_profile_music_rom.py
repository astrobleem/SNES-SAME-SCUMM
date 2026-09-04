#!/usr/bin/env python3
"""Build one SNES ROM from a profile-owned compiled-music graph."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from same.music import (
    compile_music_graph, load_profile_music_graph, profile_music_owner,
    verify_profile_music_bundle,
)
from same.profile import load_profile
from music_graph_adapters import default_music_graph_adapters


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPILER = ROOT.parent / "terrific-audio-driver/target/release/tad-compiler"
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.stage")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--music-output", type=Path)
    parser.add_argument("--rom", type=Path)
    parser.add_argument("--compiler", type=Path, default=DEFAULT_COMPILER)
    parser.add_argument(
        "--scumm-m20", action="store_true",
        help="build the SRAM-backed SCUMM compiled-music restart gate",
    )
    parser.add_argument(
        "--scumm-m21", action="store_true",
        help="build the bounded Fate compiled-route hook gate",
    )
    parser.add_argument(
        "--scumm-m22", action="store_true",
        help="build Fate sound-80's bounded delayed hook-8 section gate",
    )
    parser.add_argument(
        "--reuse", action="store_true",
        help="verify and reuse an existing complete bundle instead of compiling",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile.resolve(), verify_resources=False)
    graph = load_profile_music_graph(
        profile, dependency_reader=lambda path: (ROOT / path).read_bytes(),
    )
    compiler = args.compiler.resolve()
    music_output = (
        args.music_output.resolve() if args.music_output is not None
        else ROOT / "build/profile-music" / profile.game_id
    )
    rom = (
        args.rom.resolve() if args.rom is not None
        else ROOT / "build" / f"same-{profile.game_id}.sfc"
    )
    registration = default_music_graph_adapters().resolve(
        profile.engine_id, graph.adapter,
    )

    if not args.reuse:
        if registration.requires_source_archive and args.source_archive is None:
            parser.error("--source-archive is required unless --reuse is selected")
        archive = args.source_archive.resolve() if args.source_archive is not None else None
        compile_music_graph(
            graph, registration.factory(archive, graph), music_output,
            compiler, owner=profile_music_owner(profile),
        )
    bundle = verify_profile_music_bundle(profile, graph, music_output, compiler)

    snes_personality = profile.options.get("snes_personality", profile.engine_id)
    if not isinstance(snes_personality, str) or not snes_personality:
        raise RuntimeError("profile snes_personality must be a nonempty string")

    rom.parent.mkdir(parents=True, exist_ok=True)
    staged_rom = rom.with_name(f".{rom.stem}.stage{rom.suffix}")
    staged_pansy = staged_rom.with_suffix(".pansy")
    for path in (staged_rom, staged_pansy):
        if path.exists():
            path.unlink()
    environment = os.environ.copy()
    environment.update({
        "SAME_TAD_PREBUILT_DIR": str(bundle.directory),
        "SAME_MUSIC_CATALOG": str(bundle.directory / "catalog.json"),
        "SAME_SNES_ENGINE": snes_personality,
        "SAME_SNES_OUTPUT": str(staged_rom),
        "SAME_SNES_PROFILE": str(args.profile.resolve()),
        "SAME_BUILD_SCUMM_M20": "1" if args.scumm_m20 or args.scumm_m21 or args.scumm_m22 else "0",
        "SAME_BUILD_SCUMM_M21": "1" if args.scumm_m21 or args.scumm_m22 else "0",
        "SAME_BUILD_SCUMM_M22": "1" if args.scumm_m22 else "0",
        "SAME_SCUMM_SAVE_LOGICAL_ID": "80" if args.scumm_m21 or args.scumm_m22 else "154",
        "TAD_COMPILER": str(compiler),
    })
    subprocess.run((str(ROOT / "tools/build_snes.sh"),), cwd=ROOT, env=environment, check=True)
    os.replace(staged_rom, rom)
    if staged_pansy.is_file():
        os.replace(staged_pansy, rom.with_suffix(".pansy"))

    report = {
        "schema": "same_profile_music_rom_build_v1",
        "profile": {
            "engine_id": profile.engine_id, "game_id": profile.game_id,
            "variant": profile.variant, "sha256": bundle.profile_sha256,
        },
        "music": {
            "graph_sha256": bundle.graph_sha256,
            "compiler_sha256": bundle.compiler_sha256,
            "catalog_sha256": bundle.catalog_sha256,
            "tad_binary_sha256": bundle.tad_binary_sha256,
            "song_count": bundle.song_count,
            "build_report_sha256": _sha(bundle.directory / "report.json"),
        },
        "rom": {"file": rom.name, "bytes": rom.stat().st_size, "sha256": _sha(rom)},
    }
    report_path = rom.with_suffix(".music-build.json")
    _write_json(report_path, report)
    print(
        f"profile={profile.game_id} songs={bundle.song_count} "
        f"rom_sha256={report['rom']['sha256']}"
    )
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
