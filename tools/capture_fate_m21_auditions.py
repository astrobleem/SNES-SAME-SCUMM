#!/usr/bin/env python3
"""Capture M21's six program/range auditions from a real emulated S-DSP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from capture_fate_instrument_auditions import trim_capture
from validate_scumm_s6_tad_nexen import DEFAULT_NEXEN, require, tad_state


ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = ((32, 28), (33, 29), (50, 30), (57, 31), (77, 32), (82, 33))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, default=ROOT / "build/same-scumm-v5-fate-m21.sfc")
    parser.add_argument("--nexen", type=Path, default=DEFAULT_NEXEN)
    parser.add_argument("--port", type=int, default=44150)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rom, nexen = args.rom.resolve(), args.nexen.resolve()
    require(rom.is_file(), f"ROM not found: {rom}")
    require(nexen.is_file() and os.access(nexen, os.X_OK), f"Nexen not executable: {nexen}")
    rom_hash = hashlib.sha256(rom.read_bytes()).hexdigest()
    output = (args.output or ROOT / "build" / f"fate-m21-auditions-{rom_hash[:16]}").resolve()
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session
    mcp_session.validate_mesen_build = lambda _path: None
    captures = []
    with mcp_session.McpSession(
        rom=rom, mesen=nexen, cwd=ROOT, port=args.port, boot_wait=2.0,
        socket_timeout=90.0, stderr_log=output / "nexen-stderr.log",
    ) as session:
        session.pause()
        session.tool("reset_emulator", {"power": True})
        session.pause()
        for _ in range(240):
            session.run_frames(1)
            if tad_state(session)["state"] == 0x82 and tad_state(session)["ready"]:
                break
        else:
            raise RuntimeError("M21 audition ROM did not boot TAD")
        for program, song in PROGRAMS:
            session.write_u8(0x7E225D, song)
            for _ in range(90):
                session.run_frames(1)
                state = tad_state(session)
                if state["state"] == 0x82 and state["ready"] and state["next_song"] == song:
                    break
            else:
                raise RuntimeError(f"program {program} audition did not become ready: {state}")
            raw = raw_dir / f"program_{program}_used_range.wav"
            final = output / raw.name
            session.record_audio(raw)
            result = session.run_frames(720)
            session.stop_audio()
            require(result["framesAdvanced"] == 720 and not result["timedOut"],
                    f"program {program} capture timed out")
            evidence = trim_capture(raw, final)
            require(0 < evidence["peak"] < 32767, f"program {program} is silent or clipped")
            evidence.update({"program": program, "tad_song": song,
                             "human_timbre_verdict": "pending"})
            captures.append(evidence)

    manifest = json.loads((ROOT / "audio/fate_s6/m21_sound80/manifest.json").read_text())
    report = {"gate": "M21-program-range-auditions", "result": "mechanical-pass-human-pending",
              "rom": str(rom), "rom_sha256": rom_hash,
              "instrument_manifest_sha256": hashlib.sha256(
                  (ROOT / "audio/fate_s6/m21_sound80/manifest.json").read_bytes()).hexdigest(),
              "program_mappings": manifest["instrument_gate"]["programs"],
              "captures": captures}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Fate M21 sound-80 program/range review", "", f"ROM SHA-256: `{rom_hash}`", "",
             "These are isolated S-DSP captures. Timbre approval is intentionally pending.", ""]
    for item in captures:
        lines.extend((f"## {item['file']}", "", "- [ ] pass", "- [ ] wrong timbre",
                      "- [ ] low strained", "- [ ] high strained", "- [ ] transition audible",
                      "- [ ] out of tune", "- [ ] bad loop", "- [ ] attack/tail problem",
                      "- Notes:", "", "---", ""))
    (output / "REVIEW.md").write_text("\n".join(lines))
    print(f"M21 auditions: mechanical PASS, human timbre PENDING ({len(captures)} WAVs)")
    print(output / "REVIEW.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
