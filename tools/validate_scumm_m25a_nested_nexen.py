#!/usr/bin/env python3
"""Fresh-emulator proof for M25A's production nested-script machinery."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NEXEN = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/"
    "linux-x64/publish/Nexen"
)
COMMON = 0x7E2300
STATUS = 0x7E2380
NUMBER = 0x7E2399
PROGRAM = 0x7E23B2
PC = 0x7E23E4
LOCALS = 0x7E2448
CURRENT_SLOT = 0x7E2A88
ACTIVE_COUNT = 0x7E2A8A
NEST_DEPTH = 0x7FF465
NEST_FRAMES = 0x7FF900
VARIABLES = 0x7FF500
LEGACY_VARIABLES = 0x7E2320
EVIDENCE = 0x7E5000
TRACE = 0x7E5010
TRACE_CAPACITY = 128


class GateFailure(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise GateFailure(message)


def u16(raw: bytes, offset: int = 0) -> int:
    return raw[offset] | raw[offset + 1] << 8


def words(raw: bytes) -> list[int]:
    return [u16(raw, index) for index in range(0, len(raw), 2)]


def decode_trace(raw: bytes, count: int) -> list[dict[str, int]]:
    result = []
    for index in range(min(count, TRACE_CAPACITY)):
        item = raw[index * 8:(index + 1) * 8]
        result.append({
            "event": item[0], "depth": item[1], "slot": item[2],
            "program": item[3], "pc": u16(item, 4), "status": item[6],
            "active_slots": item[7],
        })
    return result


def snapshot(session: object) -> dict[str, object]:
    common = session.read_memory("snesMemory", COMMON, 0x64)
    evidence = session.read_memory("snesMemory", EVIDENCE, 4)
    count = min(evidence[0], TRACE_CAPACITY)
    statuses = list(session.read_memory("snesMemory", STATUS, 25))
    numbers = list(session.read_memory("snesMemory", NUMBER, 25))
    programs = list(session.read_memory("snesMemory", PROGRAM, 25))
    pcs = words(session.read_memory("snesMemory", PC, 50))
    local_raw = session.read_memory("snesMemory", LOCALS, 25 * 64)
    return {
        "vm_pc": u16(common), "vm_status": common[2], "error": common[3],
        "last_opcode": common[6], "selected_program": common[0x62],
        "return_mode": common[0x63],
        "trace_count": evidence[0], "trace_overflow": evidence[1],
        "max_depth": evidence[2], "fault_depth": evidence[3],
        "trace": decode_trace(
            session.read_memory("snesMemory", TRACE, TRACE_CAPACITY * 8), count),
        "nest_depth": session.read_memory("snesMemory", NEST_DEPTH, 1)[0],
        "current_slot": session.read_memory("snesMemory", CURRENT_SLOT, 1)[0],
        "active_count": session.read_memory("snesMemory", ACTIVE_COUNT, 1)[0],
        "slots": [{
            "slot": index, "status": statuses[index], "number": numbers[index],
            "program": programs[index], "pc": pcs[index],
            "locals": words(local_raw[index * 64:(index + 1) * 64]),
        } for index in range(25)],
        "globals": (words(session.read_memory("snesMemory", LEGACY_VARIABLES, 32))
                    + words(session.read_memory("snesMemory", VARIABLES, 32))),
        "wram_evidence_hex": session.read_memory(
            "snesMemory", EVIDENCE, 0x410).hex(),
        "nest_frames_hex": session.read_memory(
            "snesMemory", NEST_FRAMES, 24 * 3).hex(),
    }


def step(session: object) -> None:
    result = session.run_frames(1)
    require(result["framesAdvanced"] == 1 and not result["timedOut"],
            f"emulator frame did not advance: {result}")


def run_case(rom: Path, nexen: Path, port: int, output: Path,
             case: str) -> dict[str, object]:
    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    case_dir = output / case
    case_dir.mkdir(parents=True, exist_ok=True)
    timeline: list[dict[str, object]] = []
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=port, boot_wait=2.0,
        socket_timeout=60.0, stderr_log=case_dir / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        require(session.get_state()["frameCount"] == 0,
                f"{case}: power reset did not reach frame zero")
        last_key = None
        final = None
        initialized = False
        for frame in range(120):
            step(session)
            state = snapshot(session)
            if not initialized:
                initialized = state["trace_count"] == 0
                if not initialized:
                    continue
            key = (state["trace_count"], state["nest_depth"], state["active_count"],
                   state["error"], tuple((slot["status"], slot["pc"])
                                         for slot in state["slots"][:4]))
            if key != last_key:
                timeline.append({
                    "frame": frame + 1, "trace_count": state["trace_count"],
                    "nest_depth": state["nest_depth"],
                    "active_count": state["active_count"], "error": state["error"],
                    "slots": state["slots"][:4],
                })
                last_key = key
            if case == "normal":
                if (state["active_count"] == 0 and state["trace_count"] >= 10
                        and state["nest_depth"] == 0):
                    final = state
                    break
            elif case == "outer":
                if state["active_count"] == 0 and state["trace_count"] >= 4:
                    final = state
                    break
            elif state["error"] != 0 and state["nest_depth"] == 0:
                final = state
                break
        require(final is not None, f"{case}: did not reach its terminal evidence state")

    evidence = {
        "case": case, "fresh_power_on": True, "rom": str(rom),
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "timeline": timeline, "final": final,
    }
    trace = final["trace"]
    require(final["trace_overflow"] == 0, f"{case}: transition trace overflowed")
    require(final["nest_depth"] == 0, f"{case}: nested frame leaked")

    if case == "normal":
        expected_prefix = [
            (1, 0, 0, 0xD0, 3), (2, 1, 1, 0xD2, 0),
            (1, 1, 1, 0xD2, 18), (2, 2, 2, 0xD3, 0),
            (3, 2, 2, 0xD3, 16), (4, 1, 1, 0xD2, 18),
            (3, 1, 1, 0xD2, 27), (4, 0, 0, 0xD0, 3),
        ]
        actual_prefix = [(x["event"], x["depth"], x["slot"],
                          x["program"], x["pc"]) for x in trace[:8]]
        require(actual_prefix == expected_prefix,
                f"normal: immediate nested ordering differs: {actual_prefix}")
        scheduler = [(x["event"], x["slot"], x["program"], x["pc"])
                     for x in trace[8:]]
        require(scheduler == [(5, 1, 0xD2, 27), (5, 2, 0xD3, 16)],
                f"normal: yielded scheduler order differs: {scheduler}")
        require(final["globals"][10:15] == [15, 18, 27, 0, 16],
                f"normal: PC sentinels differ: {final['globals'][10:15]}")
        require(final["slots"][1]["locals"][:2] == [0x1112, 0x2222],
                "normal: parent locals were not independently preserved")
        require(final["slots"][2]["locals"][:2] == [0x3334, 0x4444],
                "normal: child locals/yield continuation differ")
        require(final["error"] == 0 and final["max_depth"] == 2,
                f"normal: unexpected fault/depth: {final['error']}/{final['max_depth']}")
        evidence["critical_order"] = [
            "parent save pc=18", "child entry pc=0", "child breakHere saved pc=16",
            "parent restore pc=18", "parent breakHere saved pc=27",
            "scheduler resumes parent pc=27", "scheduler resumes child pc=16",
            "child completes",
        ]
    elif case == "outer":
        expected = [
            (1, 0, 0, 0xD0, 8), (2, 1, 1, 0xD2, 0),
            (3, 1, 1, 0xD2, 6), (4, 0, 0, 0xD0, 8),
        ]
        actual = [(x["event"], x["depth"], x["slot"], x["program"], x["pc"])
                  for x in trace[:4]]
        require(actual == expected, f"outer: context transition differs: {actual}")
        require(final["globals"][10:13] == [0x1010, 0x1111, 0x1212],
                f"outer: parent resume/yield values differ: {final['globals'][10:13]}")
        require(final["slots"][1]["locals"][0] == 0x2020,
                "outer: stopped child local was corrupted")
        require(final["return_mode"] == 0 and final["error"] == 0,
                f"outer: outer return mode/fault differs: "
                f"{final['return_mode']}/{final['error']}")
    elif case == "depth":
        entered = {x["depth"] for x in trace if x["event"] == 2}
        require(entered == set(range(1, 25)),
                f"depth: successful context levels differ: {sorted(entered)}")
        faults = [x for x in trace if x["event"] == 0xF0]
        require(len(faults) == 1 and faults[0]["depth"] == 24,
                f"depth: 25th-context fault differs: {faults}")
        require(final["error"] == 0x09 and final["fault_depth"] == 24
                and final["max_depth"] == 24,
                "depth: bounded capacity error/depth evidence differs")
        require([final["slots"][slot]["locals"][0] for slot in range(1, 25)]
                == list(range(200, 224)),
                "depth: a scheduler slot/local record was overwritten")
        require(all(x["depth"] <= 24 for x in trace),
                "depth: trace proves an out-of-bounds context")
    else:
        faults = [x for x in trace if x["event"] == 0xF1]
        require(len(faults) == 1 and faults[0]["depth"] == 1,
                f"missing: lookup fault trace differs: {faults}")
        require(final["error"] == 0x0B and final["fault_depth"] == 1,
                "missing: canonical script error/fault depth differs")
        require(final["slots"][1]["locals"][0] == 0x5151,
                "missing: parent local was corrupted: "
                f"{final['slots'][1]['locals'][:4]}")
        require(final["globals"][15] == 0,
                "missing: post-fault parent instruction executed")
        require(not any(slot["number"] == 250 for slot in final["slots"]),
                "missing: unresolved local retained a scheduler slot")
    return evidence


def descriptor_evidence(manifest: Path) -> dict[str, object]:
    data = json.loads(manifest.read_text())
    record = data["records"][0]
    return {
        "manifest": str(manifest),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "record_sha256": record["record_sha256"],
        "lookup_key": {"active_room": record["room"], "script_kind": "LSCR"},
        "scripts": record["scripts"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-rom", type=Path, required=True)
    parser.add_argument("--depth-rom", type=Path, required=True)
    parser.add_argument("--missing-rom", type=Path, required=True)
    parser.add_argument("--outer-rom", type=Path, required=True)
    parser.add_argument("--normal-manifest", type=Path, required=True)
    parser.add_argument("--depth-manifest", type=Path, required=True)
    parser.add_argument("--missing-manifest", type=Path, required=True)
    parser.add_argument("--outer-manifest", type=Path, required=True)
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44250)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "build/m25a-validator/evidence")
    args = parser.parse_args()
    paths = (args.normal_rom, args.depth_rom, args.missing_rom, args.outer_rom,
             args.normal_manifest, args.depth_manifest, args.missing_manifest,
             args.outer_manifest)
    for path in paths:
        require(path.is_file(), f"required validator input is missing: {path}")
    require(args.nexen.is_file() and os.access(args.nexen, os.X_OK),
            "Nexen executable is unavailable")
    args.output.mkdir(parents=True, exist_ok=True)
    report = {
        "gate": "M25A-production-SNES-nested-room-local",
        "result": "running", "debugger_writes": 0,
        "production_paths": [
            "cooked ROOM validation", "generated LSCR resolver",
            "C4 scheduler/allocation", "existing SCUMM interpreter",
            "M25A far context suspend/restore", "breakHere",
        ],
    }
    report_path = args.output / "report.json"
    try:
        report["normal"] = run_case(args.normal_rom.resolve(), args.nexen.resolve(),
                                    args.port, args.output, "normal")
        report["depth"] = run_case(args.depth_rom.resolve(), args.nexen.resolve(),
                                   args.port + 1, args.output, "depth")
        report["missing"] = run_case(args.missing_rom.resolve(), args.nexen.resolve(),
                                     args.port + 2, args.output, "missing")
        report["outer"] = run_case(args.outer_rom.resolve(), args.nexen.resolve(),
                                   args.port + 3, args.output, "outer")
        report["descriptors"] = {
            "normal": descriptor_evidence(args.normal_manifest),
            "depth": descriptor_evidence(args.depth_manifest),
            "missing": descriptor_evidence(args.missing_manifest),
            "outer": descriptor_evidence(args.outer_manifest),
        }
        normal_scripts = {item["number"]: item for item in
                          report["descriptors"]["normal"]["scripts"]}
        require(200 in normal_scripts and 201 in normal_scripts,
                "normal generated table lacks parent/child descriptors")
        report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["failure"] = str(exc)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        raise
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    human = args.output / "critical-trace.txt"
    trace = report["normal"]["final"]["trace"]
    human.write_text("\n".join(
        f"event={item['event']:02X} depth={item['depth']:02d} "
        f"slot={item['slot']:02d} program={item['program']:02X} "
        f"pc={item['pc']:04X} status={item['status']:02X}"
        for item in trace
    ) + "\n")
    print(json.dumps({
        "result": report["result"], "report": str(report_path),
        "normal_rom_sha256": report["normal"]["rom_sha256"],
        "depth_rom_sha256": report["depth"]["rom_sha256"],
        "missing_rom_sha256": report["missing"]["rom_sha256"],
        "outer_rom_sha256": report["outer"]["rom_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
