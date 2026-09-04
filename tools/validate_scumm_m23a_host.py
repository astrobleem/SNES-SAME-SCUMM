#!/usr/bin/env python3
"""Host proof for M23A authentic registration without script dispatch."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--profile", type=Path,
                        default=ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    require(policy is not None, "Fate profile has no v5 resource policy")
    manifest_bytes = args.manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    with zipfile.ZipFile(args.archive) as bundle:
        source = {
            "game.index": bundle.read("FATEDEMO/PLAYFATE.000"),
            "game.data": bundle.read("FATEDEMO/PLAYFATE.001"),
        }
    source["music.catalog"] = (
        ROOT / "examples/resources/music/fate_s6_compiled.json"
    ).read_bytes()
    source["cooked.rooms.manifest"] = manifest_bytes
    for item in manifest["records"]:
        source[f"cooked.room.{item['room']}"] = (args.manifest.parent / item["output"]).read_bytes()
    cases = []
    for room in (49, 63):
        provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(source), policy)
        services = HostServices.create(profile, resources=provider)
        host = EngineHost(profile, default_registry(), services=services)
        host.boot()
        assert host.context is not None
        engine = host.engine
        engine._load_room(host.context, room, required=True)  # validator uses normal loader
        state = engine.inspect_state()
        scripts = [item for item in state["scripts"] if item.get("room") == room]
        entry = next(item for item in scripts if item["script_kind"] == "ENCD")
        require(state["room"] == room, "host active room differs")
        require(entry["pc"] == 0 and entry["active"], "authentic ENCD was dispatched")
        require(state["sound_kludge"]["queue"] == [], "authentic registration queued sound")
        require(state["audio"]["music"] in (None, 0), "authentic registration started music")
        descriptors = state["room_resource"]["scripts"]
        expected = 20 if room == 49 else 5
        require(len(descriptors) == expected, "host script discovery count differs")
        phases = [item["phase"] for item in engine.inspect_room_lifecycle()]
        require("new_room_validated" in phases and "new_room_activated" in phases and
                "entry_script_scheduled" in phases and "entry_first_instruction" not in phases,
                "host registration-only lifecycle differs")
        cases.append({
            "room": room, "resource_sha256": hashlib.sha256(provider.read(f"room.{room}")).hexdigest(),
            "record_sha256": state["room_resource"]["record_sha256"],
            "scripts": descriptors, "entry_slot": entry, "lifecycle": phases,
            "music_commands": 0,
        })
    report = {
        "gate": "M23A-host-authentic-registration", "result": "pass",
        "archive_sha256": hashlib.sha256(args.archive.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(), "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
