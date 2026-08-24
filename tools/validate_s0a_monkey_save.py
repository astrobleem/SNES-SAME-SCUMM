#!/usr/bin/env python3
"""Prove deterministic replay from the supplied Monkey dock save state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import validate_s0a_monkey as s0a


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=43985)
    parser.add_argument("--frames", type=int, default=180)
    parser.add_argument(
        "--state",
        type=Path,
        default=s0a.ROOT / "build" / f"s0a-monkey-{s0a.ROM_SHA256[:16]}" / "dock-frontier.mss",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=s0a.ROOT / "build" / f"s0a-monkey-save-{s0a.ROM_SHA256[:16]}",
    )
    args = parser.parse_args()

    rom = s0a.BUNDLE / "SuperMonkeyIsland.sfc"
    s0a.require(rom.is_file() and s0a.sha(rom) == s0a.ROM_SHA256, "ROM identity changed")
    s0a.require(args.state.is_file(), f"missing state: {args.state}")
    args.output.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, "/home/chad/Mesen2/python")
    import mesen_mcp.session as mcp_session

    mcp_session.validate_mesen_build = lambda _path: None
    report: dict[str, object] = {
        "gate": "S0A-save-replay",
        "classification": "known-incomplete behavioral baseline, not semantic oracle",
        "rom_sha256": s0a.ROM_SHA256,
        "state": {"path": str(args.state.resolve()), "sha256": s0a.sha(args.state)},
        "frames_per_branch": args.frames,
        "result": "running",
    }
    report_path = args.output / "report.json"

    try:
        with mcp_session.McpSession(
            rom=rom,
            mesen=s0a.NEXEN,
            cwd=s0a.BUNDLE,
            port=args.port,
            boot_wait=3.0,
            socket_timeout=180.0,
            stderr_log=args.output / "nexen-stderr.log",
        ) as session:
            session.pause()

            branches = []
            for name in ("forward", "replay"):
                session.load_state(args.state)
                session.pause()
                loaded = s0a.snapshot(session, f"{name}-loaded")
                loaded_digest = s0a.state_digest(session)
                loaded_shot = s0a.capture(session, args.output / f"{name}-loaded.png")
                s0a.advance_released(session, args.frames)
                settled = s0a.snapshot(session, f"{name}-plus-{args.frames}")
                settled_digest = s0a.state_digest(session)
                settled_shot = s0a.capture(session, args.output / f"{name}-plus-{args.frames}.png")
                branches.append(
                    {
                        "name": name,
                        "loaded": loaded,
                        "loaded_digest": loaded_digest,
                        "loaded_screenshot": loaded_shot,
                        "settled": settled,
                        "settled_digest": settled_digest,
                        "settled_screenshot": settled_shot,
                    }
                )

            forward, replay = branches
            report["branches"] = branches
            report["loaded_memory_exact"] = forward["loaded_digest"] == replay["loaded_digest"]
            report["loaded_screenshot_exact"] = (
                forward["loaded_screenshot"]["sha256"] == replay["loaded_screenshot"]["sha256"]
            )
            report["settled_memory_exact"] = forward["settled_digest"] == replay["settled_digest"]
            report["settled_screenshot_exact"] = (
                forward["settled_screenshot"]["sha256"] == replay["settled_screenshot"]["sha256"]
            )
            report["result"] = "observed"
    except Exception as exc:
        report["result"] = "harness-failure"
        report["error"] = f"{type(exc).__name__}: {exc}"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"S0A save replay: HARNESS FAILURE: {exc}", file=sys.stderr)
        print(report_path)
        return 1

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "S0A save replay: OBSERVED",
        {
            "loaded_memory_exact": report["loaded_memory_exact"],
            "loaded_screenshot_exact": report["loaded_screenshot_exact"],
            "settled_memory_exact": report["settled_memory_exact"],
            "settled_screenshot_exact": report["settled_screenshot_exact"],
        },
    )
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
