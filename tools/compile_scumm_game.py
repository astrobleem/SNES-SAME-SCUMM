#!/usr/bin/env python3
"""Inventory and conservatively analyze a complete raw SCUMM v5 source edition."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from same.engines.scumm_v5.game_analysis import analyze_game, canonical_json, game_analysis_hash
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.engines.scumm_v5.room_compiler import compiler_source_manifest, source_member_pair
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from generate_snes_cooked_rooms import OVERFLOW_PROGRAM_IDS, PRIMARY_PROGRAM_IDS


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_source(path: Path) -> tuple[dict[str, bytes], dict[str, str], str]:
    if path.is_dir():
        members = {}
        for key, suffix in (("game.index", ".000"), ("game.data", ".001")):
            matches = sorted(item for item in path.rglob("*") if item.is_file()
                             and item.name.upper().endswith(suffix))
            if len(matches) != 1:
                raise ValueError(f"source directory must contain exactly one {suffix} member")
            members[key] = matches[0].name
            raw_path = matches[0]
            members[f"{key}.__path"] = str(raw_path)
        raw = {key: Path(members[f"{key}.__path"]).read_bytes()
               for key in ("game.index", "game.data")}
        source_hash = sha(canonical_json([
            {"member": members[key], "sha256": sha(raw[key])}
            for key in ("game.index", "game.data")
        ]))
        clean_members = {key: members[key] for key in ("game.index", "game.data")}
        return raw, clean_members, source_hash
    source_bytes = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        found = source_member_pair(archive.namelist())
        raw = {key: archive.read(member) for key, member in found.items()}
    return raw, found, sha(source_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="ZIP containing one .000/.001 pair, or directory containing that pair")
    parser.add_argument("--profile", type=Path, required=True,
                        help="thin source-edition profile with raw SCUMM v5 resource policy")
    parser.add_argument("--analyze", action="store_true", required=True,
                        help="emit census, IR, graph, reachability, capabilities, and frontier")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw, members, source_hash = read_source(args.source)
    profile_bytes = args.profile.read_bytes()
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None or policy.resource_format != "lucasarts_scumm_v5":
        raise ValueError("profile must select raw LucasArts SCUMM v5 resources")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    result = analyze_game(provider, profile=profile, profile_bytes=profile_bytes,
                          archive_sha256=source_hash, source_members=members,
                          backend_selector_capacity={
                              "primary_ids": len(PRIMARY_PROGRAM_IDS),
                              "overflow_ids": len(OVERFLOW_PROGRAM_IDS),
                              "value": len(PRIMARY_PROGRAM_IDS) + len(OVERFLOW_PROGRAM_IDS),
                              "epistemic": "EXACT",
                              "source": "tools/generate_snes_cooked_rooms.py default allocator pools",
                              "selectors_allocated": False,
                          })
    files = result.files()
    manifest = {
        "schema": "same_scumm_v5_game_analysis_manifest_v1",
        "game_id": profile.game_id,
        "variant": profile.variant,
        "profile_sha256": sha(profile_bytes),
        "source_sha256": source_hash,
        "compiler_source_components": compiler_source_manifest(),
        "analysis_file_set_sha256": game_analysis_hash(files),
        "files": [{"path": name, "size": len(content), "sha256": sha(content)}
                  for name, content in sorted(files.items())],
    }
    files["analysis_manifest.json"] = (json.dumps(manifest, sort_keys=True,
                                                   indent=2) + "\n").encode()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (args.output / name).write_bytes(content)
    summary = result.census["counts"]
    print(f"{profile.game_id}: {summary.get('room', 0)} rooms, "
          f"{result.executables['counts']['total']} executable identities, "
          f"{result.dependency_graph['counts']['edges']} graph edges")
    print(f"Analysis identity SHA-256: {manifest['analysis_file_set_sha256']}")
    print(f"Static closure complete: {result.opaque_analysis['closure_complete']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
