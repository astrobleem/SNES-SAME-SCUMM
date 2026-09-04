#!/usr/bin/env python3
"""Validate authentic room-49 -> room-63 execution through the bounded flush."""

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
STATE = ROOT / "examples/resources/scumm_v5/fate_m23c_pre_thera.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise RuntimeError(message)


def make_host(archive: Path, manifest_paths: list[Path]):
    profile = load_profile(PROFILE, verify_resources=False)
    manifests = [json.loads(path.read_text()) for path in manifest_paths]
    combined = dict(manifests[0])
    combined["records"] = [item for manifest in manifests for item in manifest["records"]]
    combined["global_scripts"] = [
        item for manifest in manifests for item in manifest.get("global_scripts", [])
    ]
    manifest_bytes = json.dumps(combined, sort_keys=True, separators=(",", ":")).encode()
    with zipfile.ZipFile(archive) as bundle:
        source = {
            "game.index": bundle.read("FATEDEMO/PLAYFATE.000"),
            "game.data": bundle.read("FATEDEMO/PLAYFATE.001"),
        }
    source["music.catalog"] = (
        ROOT / "examples/resources/music/fate_s6_compiled.json"
    ).read_bytes()
    source["cooked.rooms.manifest"] = manifest_bytes
    for path, manifest in zip(manifest_paths, manifests, strict=True):
        for item in manifest["records"]:
            source[f"cooked.room.{item['room']}"] = (path.parent / item["output"]).read_bytes()
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source), parse_game_policy(profile)
    )
    services = HostServices.create(profile, resources=provider)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    return host, manifests


def run_case(archive: Path, manifests: list[Path], case: str) -> dict[str, object]:
    fixture = json.loads(STATE.read_text())
    host, decoded_manifests = make_host(archive, manifests)
    engine = host.engine
    require(sha(PROFILE.read_bytes()) == fixture["profile_sha256"], "fixture profile differs")
    require(sha(archive.read_bytes()) == fixture["archive_sha256"], "fixture archive differs")
    for manifest in decoded_manifests:
        for record in manifest["records"]:
            require(record["record_sha256"] == fixture["room_records"][str(record["room"])],
                    f"fixture room {record['room']} differs")
        for script in manifest.get("global_scripts", []):
            expected = fixture["global_scripts"].get(str(script["number"]))
            if expected is not None:
                require(script["sha256"] == expected, f"fixture script {script['number']} differs")

    engine.state.scripts[0].active = False
    for bit in fixture["bits_set"]:
        engine.state.bit_variables[int(bit)] = True
    for key, spec in fixture["strings"].items():
        engine.state.strings[int(key)] = bytearray([int(spec["fill"])] * int(spec["length"]))
    engine.state.object_classes[595] = set(fixture["object_classes"]["595"])
    if case == "class-control":
        engine.state.object_classes[595].add(18)
    if case != "sound82-control":
        engine._audio.active_sfx[82] = 0

    trace: list[dict[str, object]] = []
    original_step = engine._step

    def traced_step(slot, context):
        start = slot.pc
        opcode = slot.program[start]
        before_queue = [list(item) for item in engine.state.sound_queue]
        before_vars = {str(i): engine.state.variables[i] for i in (0, 224, 414, 444)}
        original_step(slot, context)
        source_map = None if slot.source is None else slot.source.runtime_map(start)
        trace.append({
            "script": slot.resource_key,
            "runtime_instruction_offset": start,
            "opcode": opcode,
            "next_runtime_offset": slot.pc,
            "source_map": source_map,
            "variables_before": before_vars,
            "variables_after": {str(i): engine.state.variables[i] for i in (0, 224, 414, 444)},
            "queue_before": before_queue,
            "queue_after": [list(item) for item in engine.state.sound_queue],
        })
        # These are observation barriers after real branch/flush execution.
        # They do not change the PC, operands, condition, queue, or branch result.
        if slot.resource_key == "room.63/ENCD":
            if case == "sound82-control" and start == 0x00BC:
                slot.yielded = True
            elif case != "sound82-control" and start == 0x00C6:
                slot.yielded = True

    engine._step = traced_step
    engine._load_room(host.context, 49, required=True)
    engine._in_tick = True
    engine._tick_operations = 0
    engine._tick_max_ops = 10000
    try:
        room49 = next(
            slot for slot in engine.state.scripts
            if slot.active and slot.script_kind == "ENCD" and slot.room == 49
        )
        while room49.active and room49.pc < 0x006A:
            traced_step(room49, host.context)
        require(engine._audio.music_id == 80 and engine._audio.music_route == ("hook", 14),
                "room 49 did not establish authentic hook-14 ownership")
        engine._load_room(host.context, 63, required=True)
    finally:
        engine._in_tick = False
        engine._step = original_step

    room63 = [item for item in trace if item["script"] == "room.63/ENCD"]
    offsets = [item["runtime_instruction_offset"] for item in room63]
    script151 = [item for item in trace if item["script"] == "script.151"]
    require(offsets and offsets[0] == 0, "room-63 ENCD did not begin at PC zero")
    require(0x00A7 in offsets and 0x00B5 in offsets and 0x00B8 in offsets and 0x00BC in offsets,
            "room-63 dependency path is incomplete")
    hook = next(item for item in room63 if item["runtime_instruction_offset"] == 0x00A7)
    require(hook["queue_after"][-1] == [0x010C, 80, 0, 8], "authentic hook-8 queue differs")
    require(script151 and script151[0]["runtime_instruction_offset"] == 0,
            "authentic global script 151 did not execute from PC zero")
    active151 = next(slot for slot in engine.state.scripts if slot.number == 151)
    require(active151.active and active151.pc == 4 and active151.delay == 7200,
            "global script 151 did not yield in its authentic delayed state")
    state = engine.inspect_state()
    if case == "sound82-control":
        require(0x00C1 not in offsets and 0x00C6 not in offsets and room63[-1]["next_runtime_offset"] == 0x00DE,
                "sound-82 control did not take the authentic alternate branch")
        require(state["sound_kludge"]["queue"] == [[0x010C, 80, 0, 8]],
                "sound-82 control queue changed before its alternate-path continuation")
    else:
        require(offsets[-2:] == [0x00C1, 0x00C6], "authentic 0x0110/flush tail differs")
        flush = room63[-1]
        require(flush["queue_before"] == [[0x010C, 80, 0, 8], [0x0110]],
                "authentic room-63 final queue differs")
        require(state["sound_kludge"]["history"][-2:] == [[0x010C, 80, 0, 8], [0x0110]],
                "authentic room-63 flush order differs")
        require(state["sound_kludge"]["imuse_queue_clear_count"] == 1,
                "0x0110 did not execute its canonical clear-queue semantic")
        require(engine._audio.inspect()["music_section"]["pending_hook"] == 8,
                "authentic flush did not arm delayed hook 8")
    class_offsets = [item for item in offsets if item in (0x0000, 0x0009)]
    require(class_offsets == ([0x0000, 0x0009] if case == "class-control" else [0x0000]),
            "class control branch path differs")
    return {
        "case": case, "result": "pass", "fixture": fixture["name"],
        "fixture_sha256": sha(STATE.read_bytes()), "trace": trace,
        "room_lifecycle": engine.inspect_room_lifecycle(),
        "sound_kludge": state["sound_kludge"], "audio": engine._audio.inspect(),
        "script151": {"active": active151.active, "pc": active151.pc, "delay": active151.delay},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {
        "gate": "M23C-host-authentic-room49-room63",
        "result": "pass",
        "cases": [run_case(args.archive, args.manifest, case)
                  for case in ("positive", "class-control", "sound82-control")],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
