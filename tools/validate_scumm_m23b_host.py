#!/usr/bin/env python3
"""Validate authentic room-49 ENCD execution to its single iMUSE flush."""

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
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
STATE = ROOT / "examples/resources/scumm_v5/fate_m23b_pre_thera.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def make_host(archive: Path, manifest_path: Path):
    profile = load_profile(PROFILE, verify_resources=False)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    with zipfile.ZipFile(archive) as bundle:
        source = {
            "game.index": bundle.read("FATEDEMO/PLAYFATE.000"),
            "game.data": bundle.read("FATEDEMO/PLAYFATE.001"),
        }
    source["music.catalog"] = (
        ROOT / "examples/resources/music/fate_s6_compiled.json"
    ).read_bytes()
    source["cooked.rooms.manifest"] = manifest_bytes
    for item in manifest["records"]:
        source[f"cooked.room.{item['room']}"] = (manifest_path.parent / item["output"]).read_bytes()
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source), parse_game_policy(profile)
    )
    services = HostServices.create(profile, resources=provider)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    return host, manifest


def run_case(archive: Path, manifest_path: Path, *, negative: bool) -> dict[str, object]:
    fixture = json.loads(STATE.read_text())
    host, manifest = make_host(archive, manifest_path)
    engine = host.engine
    record = manifest["records"][0]
    require(sha(PROFILE.read_bytes()) == fixture["profile_sha256"], "fixture profile differs")
    require(sha(archive.read_bytes()) == fixture["archive_sha256"], "fixture archive differs")
    require(record["record_sha256"] == fixture["room_record_sha256"], "fixture room differs")
    for item in manifest.get("global_scripts", []):
        expected = fixture["global_scripts"].get(str(item["number"]))
        require(item["sha256"] == expected, f"fixture script {item['number']} differs")

    engine.state.scripts[0].active = False
    for bit in fixture["bits_set"]:
        engine.state.bit_variables[int(bit)] = True
    for key, spec in fixture["strings"].items():
        engine.state.strings[int(key)] = bytearray([int(spec["fill"])] * int(spec["length"]))
    if negative:
        engine._audio.active_sfx[81] = 0
    engine._load_room(host.context, 49, required=True)
    entry = next(slot for slot in engine.state.scripts if slot.script_kind == "ENCD")

    trace: list[dict[str, object]] = []
    original_step = engine._step

    def traced_step(slot, context):
        start = slot.pc
        opcode = slot.program[start]
        before_vars = {str(i): engine.state.variables[i] for i in (0, 27, 450, 451)}
        before_bits = [i for i in (418, 425) if engine.state.bit_variables[i]]
        before_queue = [list(item) for item in engine.state.sound_queue]
        original_step(slot, context)
        source_map = None if slot.source is None else slot.source.runtime_map(start)
        trace.append({
            "script": slot.resource_key,
            "script_number": slot.number,
            "runtime_instruction_offset": start,
            "opcode": opcode,
            "next_runtime_offset": slot.pc,
            "source_map": source_map,
            "variables_before": before_vars,
            "variables_after": {str(i): engine.state.variables[i] for i in (0, 27, 450, 451)},
            "bits_before": before_bits,
            "bits_after": [i for i in (418, 425) if engine.state.bit_variables[i]],
            "queue_before": before_queue,
            "queue_after": [list(item) for item in engine.state.sound_queue],
        })

    engine._step = traced_step
    engine._in_tick = True
    engine._tick_operations = 0
    engine._tick_max_ops = host.context.profile.max_ops_per_tick
    try:
        while entry.active and entry.pc < 0x69:
            traced_step(entry, host.context)
    finally:
        engine._in_tick = False
        engine._step = original_step

    state = engine.inspect_state()
    parent = [item for item in trace if item["script"] == "room.49/ENCD"]
    offsets = [item["runtime_instruction_offset"] for item in parent]
    if negative:
        require(0x4F not in offsets and 0x57 not in offsets and 0x65 not in offsets,
                "negative control reached the music block")
        require(not any(item["opcode"] == 0x4C for item in trace),
                "negative control executed soundKludge")
        require(host.services.audio.music_track is None, "negative control emitted music")
    else:
        require(offsets[-3:] == [0x4F, 0x57, 0x65], "authentic music offsets differ")
        flush = parent[-1]
        require(flush["queue_before"] == [[8, 80], [0x010C, 80, 0, 14]],
                "authentic final queue differs")
        require(state["sound_kludge"]["history"][-2:] == [[8, 80], [0x010C, 80, 0, 14]],
                "single flush history differs")
        require(state["sound_kludge"]["queue"] == [], "flush left queued commands")
        require(engine._audio.music_id == 80 and engine._audio.music_route == ("hook", 14),
                "hook-14 compiled route was not selected")
    return {
        "case": "sound81-running-negative" if negative else "pre-thera-positive",
        "result": "pass",
        "fixture": fixture["name"],
        "entry_pc": entry.pc,
        "operations": engine._tick_operations,
        "trace": trace,
        "sound_kludge": state["sound_kludge"],
        "audio": engine._audio.inspect(),
        "lifecycle": engine.inspect_room_lifecycle(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "gate": "M23B-host-authentic-room49",
        "result": "pass",
        "fixture_sha256": sha(STATE.read_bytes()),
        "cases": [
            run_case(args.archive, args.manifest, negative=False),
            run_case(args.archive, args.manifest, negative=True),
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
