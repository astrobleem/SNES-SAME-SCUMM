#!/usr/bin/env python3
"""Replay the saved room-4 Open/trapdoor input prefix on its exact ROM.

The state file is an external same-ROM diagnostic checkpoint. This runner
does not create room readiness and never writes game state through debugger
memory APIs; it verifies the state precondition and sends controller input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "examples/replays/fate-room4-open-trapdoor.json"
NEXEN_DEFAULT = Path(
    "/mnt/sdc1/Nexen-r5-20260712/bin/linux-x64/Release/linux-x64/publish/Nexen"
)


def main() -> int:
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--state-identity", type=Path, required=True,
                        help="JSON sidecar binding this state SHA to the exact ROM and build identity")
    parser.add_argument("--nexen", type=Path, default=NEXEN_DEFAULT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=44972)
    args = parser.parse_args()

    rom, state = args.rom.resolve(), args.state.resolve()
    state_identity = args.state_identity.resolve()
    nexen = args.nexen.resolve()
    if not all(path.is_file() for path in (rom, state, state_identity, nexen)):
        parser.error("ROM, same-ROM state, its identity sidecar, and Nexen must exist")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    expected_rom = recipe["rom"]["sha256"]
    if rom_hash != expected_rom:
        parser.error(f"ROM SHA-256 mismatch: {rom_hash} != {expected_rom}")
    identity_data = json.loads(state_identity.read_text(encoding="utf-8"))
    state_hash = hashlib.sha256(state.read_bytes()).hexdigest()
    if identity_data.get("rom_sha256") != expected_rom:
        parser.error("state identity sidecar is not bound to the replay ROM")
    if identity_data.get("build_identity_sha256") != recipe["rom"]["build_identity_sha256"]:
        parser.error("state identity sidecar has the wrong build identity")
    if identity_data.get("state_sha256") != state_hash:
        parser.error("state identity sidecar does not match the supplied state bytes")

    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, "/home/chad/Mesen2/python")
    from fate_replay import replay_room4_open_trapdoor_prefix
    from validate_scumm_startup42_nexen import verified_symbol_map_for_rom
    import mesen_mcp.session as mcp_session

    map_path, _symbols = verified_symbol_map_for_rom(rom)
    identity_path = rom.with_suffix(".build_identity.json")
    map_hash = hashlib.sha256(map_path.read_bytes()).hexdigest()
    identity_hash = hashlib.sha256(identity_path.read_bytes()).hexdigest()
    if map_hash != recipe["rom"]["map_sha256"]:
        parser.error(f"map SHA-256 mismatch: {map_hash}")
    if identity_hash != recipe["rom"]["build_identity_sha256"]:
        parser.error(f"build identity SHA-256 mismatch: {identity_hash}")
    nexen_hash = hashlib.sha256(nexen.read_bytes()).hexdigest()
    if nexen_hash != recipe["rom"]["nexen_sha256"]:
        parser.error(f"Nexen SHA-256 mismatch: {nexen_hash}")

    mcp_session.validate_mesen_build = lambda _path: None
    report: dict[str, object] = {
        "result": "running",
        "recipe": str(RECIPE.relative_to(ROOT)),
        "rom_sha256": rom_hash,
        "map_sha256": map_hash,
        "build_identity_sha256": identity_hash,
        "state_sha256": state_hash,
        "state_identity_sha256": hashlib.sha256(state_identity.read_bytes()).hexdigest(),
        "nexen_sha256": nexen_hash,
        "evidence_class": "same-ROM state-assisted controller replay; not cold-start acceptance",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with mcp_session.McpSession(
            rom=rom, mesen=nexen, cwd=ROOT, port=args.port,
            boot_wait=2.0, socket_timeout=30.0,
        ) as session:
            session.pause()
            report["state_load"] = session.load_state(state)
            session.pause()
            report["replay"] = replay_room4_open_trapdoor_prefix(session)
            report["result"] = "pass"
    except Exception as exc:
        report["result"] = "fail"
        report["error"] = f"{type(exc).__name__}: {exc}"
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"FATE room-4 input prefix: PASS ({rom_hash})")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
