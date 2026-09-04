#!/usr/bin/env python3
"""Validate M6 catalogs against both supplied v5 sources and compiled songs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from same.capabilities import EngineCapability
from same.engine import EngineContext
from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedAudioAdapter
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.music import CompiledMusicCatalog
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices
from generate_music_catalog import tad_songs
from validate_monkey_v5_music import MEMBERS as MONKEY_MEMBERS
from validate_scumm_s6_fate_preflight import MEMBERS as FATE_MEMBERS


ROOT = Path(__file__).resolve().parents[1]
FATE_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
MONKEY_PROFILE = ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json"
FATE_CATALOG = ROOT / "examples/resources/music/fate_s6_compiled.json"
MONKEY_CATALOG = ROOT / "examples/resources/music/monkey_v5_compiled.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def provider(archive: Path, profile_path: Path, members: dict[str, str], catalog: Path):
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in members.items() if name in ("index", "data")}
    profile = load_profile(profile_path, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError(f"{profile_path} has no raw v5 policy")
    backing = MemoryResourceProvider({
        "game.index": raw["index"], "game.data": raw["data"],
        "music.catalog": catalog.read_bytes(),
    })
    return profile, LucasartsScummV5ResourceProvider(backing, policy)


def validate_title(
    name: str,
    archive: Path,
    profile_path: Path,
    members: dict[str, str],
    catalog_path: Path,
    enums_path: Path,
    logical_id: int,
) -> dict[str, object]:
    profile, resources = provider(archive, profile_path, members, catalog_path)
    catalog = CompiledMusicCatalog.decode(
        catalog_path.read_bytes(), "music.catalog",
        source_reader=resources.read,
        compiled_songs=tad_songs(enums_path.read_text(encoding="utf-8")),
    )
    services = HostServices.create(
        profile, resources=resources, capabilities=EngineCapability.CHIP_AUDIO,
    )
    context = EngineContext(profile, services, EngineCapability.CHIP_AUDIO)
    adapter = ScummV5EmbeddedAudioAdapter(context, lambda sound: f"sound.{sound}")
    adapter.play_music(logical_id)
    for _ in range(3):
        adapter.tick()
    saved = adapter.save_state()
    adapter.stop_music()
    adapter.load_state(saved)
    state = adapter.inspect()
    entry = catalog.resolve(logical_id)
    if (
        state["backend"] != "compiled_tad"
        or state["music"] != logical_id
        or state["music_position"] != 3
        or saved["music_identity"] != entry.identity
    ):
        raise RuntimeError(f"{name} compiled catalog play/save semantics differ")
    return {
        "archive_sha256": sha256(archive),
        "catalog_sha256": catalog.sha256,
        "catalog_entries": len(catalog.entries),
        "logical_id": logical_id,
        "source_resource": entry.source_resource,
        "source_sha256": entry.source_sha256,
        "compiled_song": entry.compiled_song,
        "compiled_song_id": entry.compiled_song_id,
        "duration": entry.duration,
        "loop": None if entry.loop_start is None else [entry.loop_start, entry.loop_end],
        "saved_position": state["music_position"],
        "backend": state["backend"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fate-archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--monkey-archive", type=Path, default=Path("/home/chad/_monkeypacks_backup.zip"))
    parser.add_argument("--fate-enums", type=Path, required=True)
    parser.add_argument("--monkey-enums", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "schema": "same_compiled_music_catalog_m6_v1",
        "fate": validate_title(
            "Fate", args.fate_archive.resolve(), FATE_PROFILE, FATE_MEMBERS,
            FATE_CATALOG, args.fate_enums.resolve(), 172,
        ),
        "monkey": validate_title(
            "Monkey", args.monkey_archive.resolve(), MONKEY_PROFILE, MONKEY_MEMBERS,
            MONKEY_CATALOG, args.monkey_enums.resolve(), 154,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(f"M6 compiled music catalogs: PASS ({report['fate']['catalog_entries']} Fate, 1 Monkey)")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
