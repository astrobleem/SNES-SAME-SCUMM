#!/usr/bin/env python3
"""Validate S2 with copyright-free raw resources and logical input events."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5 import LucasartsScummV5ResourceProvider
from same.input import SnesButton
from same.profile import load_profile
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s2_conformance.json"
OUTPUT = ROOT / "build/scumm-s2-adapters/report.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    profile = load_profile(PROFILE)
    host = EngineHost(profile, default_registry(), services=HostServices.create(profile))
    host.boot()
    provider = host.services.resources
    if not isinstance(provider, LucasartsScummV5ResourceProvider):
        raise RuntimeError("SCUMM raw resource adapter was not mounted")

    expected_resources = {
        "room.1": b"S2-ROOM-PAYLOAD",
        "script.1": bytes((0x80, 0x18, 0xFC, 0xFF)),
        "script.2": bytes((0x46, 0x2A, 0x00, 0x00)),
        "sound.1": b"S2-SOUND-PAYLOAD",
        "costume.1": b"S2-COSTUME-PAYLOAD",
        "charset.1": b"S2-CHARSET-PAYLOAD",
    }
    resources: dict[str, dict[str, object]] = {}
    for key, expected in expected_resources.items():
        actual = provider.read(key)
        if actual != expected:
            raise RuntimeError(f"S2 resource {key!r} differs from its synthetic fixture")
        stat = provider.stat(key)
        resources[key] = {
            "kind": stat.kind,
            "size": stat.size,
            "sha256": sha256(actual),
            "source": stat.source,
        }

    traces: list[dict[str, object]] = []
    host.tick(
        input_word=int(SnesButton.RIGHT | SnesButton.B),
        pointer=(319, 199),
        pointer_buttons=((0, True),),
        text="look",
    )
    traces.append(dict(host.engine.inspect_state()["input"]))
    host.tick(
        input_word=int(SnesButton.START),
        pointer_buttons=((0, False),),
    )
    traces.append(dict(host.engine.inspect_state()["input"]))
    host.tick()
    traces.append(dict(host.engine.inspect_state()["input"]))

    if traces[0]["cursor"] != [319, 199]:
        raise RuntimeError("S2 logical pointer coordinates were not preserved")
    if traces[0]["pressed_buttons"] != ["primary"] or traces[0]["text"] != ["look"]:
        raise RuntimeError("S2 pointer-button/text input trace differs")
    if traces[1]["released_buttons"] != ["primary"] or traces[1]["commands"] != ["menu"]:
        raise RuntimeError("S2 release/command input trace differs")
    if traces[2]["commands"] or traces[2]["released_buttons"] or traces[2]["text"]:
        raise RuntimeError("S2 transient input state survived into the next frame")

    source_paths = (
        ROOT / "src/same/engines/scumm_v5/engine.py",
        ROOT / "src/same/engines/scumm_v5/input.py",
        ROOT / "src/same/engines/scumm_v5/resources.py",
    )
    forbidden = ("$4016", "$4017", "$4218", "$4219", "MSU_SEEK", "MSU_DATA")
    violations = {
        path.relative_to(ROOT).as_posix(): [token for token in forbidden if token in path.read_text()]
        for path in source_paths
    }
    violations = {path: tokens for path, tokens in violations.items() if tokens}
    if violations:
        raise RuntimeError(f"SCUMM semantic/adaptor code contains direct hardware access: {violations}")

    report = {
        "gate": "S2",
        "result": "pass",
        "commercial_data_used": False,
        "profile": PROFILE.relative_to(ROOT).as_posix(),
        "profile_sha256": sha256(PROFILE.read_bytes()),
        "raw_sources": {
            name: sha256((ROOT / f"examples/resources/scumm_v5/{name}").read_bytes())
            for name in ("s2_index.000", "s2_data.001")
        },
        "resources": resources,
        "input_trace": traces,
        "logical_cursor": [319, 199],
        "physical_cursor": [host.services.video.cursor.x, host.services.video.cursor.y],
        "direct_hardware_access_violations": violations,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(OUTPUT.relative_to(ROOT))
    print(sha256(OUTPUT.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
