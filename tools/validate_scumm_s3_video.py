#!/usr/bin/env python3
"""Validate S3 logical video, actors, z-mask, cursor, and fonts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from same.capabilities import DEFAULT_HOST_CAPABILITIES, EngineCapability
from same.engine import EngineHost
from same.engines import default_registry
from same.profile import load_profile
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s3_conformance.json"
OUTPUT = ROOT / "build/scumm-s3-video"
LOGICAL_HASH = "6d4451b55770536cde22b8b01338d5dbda06cdf0d6198d1d1066d86faf53b086"
PHYSICAL_HASH = "54ddea1f2a877e6a88fad3ea2a94987688e29705e78e8fb21fd1fb9f29e2afaf"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_host(capabilities: EngineCapability) -> EngineHost:
    profile = load_profile(PROFILE)
    services = HostServices.create(profile, capabilities=capabilities)
    host = EngineHost(profile, default_registry(), services=services)
    host.boot()
    return host


def main() -> int:
    disabled = DEFAULT_HOST_CAPABILITIES & ~(
        EngineCapability.TILED_VIDEO
        | EngineCapability.SPRITE_OAM
        | EngineCapability.Z_MASK
        | EngineCapability.HDMA
        | EngineCapability.SA1_JOBS
    )
    accelerated = build_host(DEFAULT_HOST_CAPABILITIES)
    baseline = build_host(disabled)
    accelerated_info = dict(accelerated.engine.inspect_state()["video"])
    baseline_info = dict(baseline.engine.inspect_state()["video"])
    logical_hashes = {
        "accelerated": accelerated_info["logical_sha256"],
        "baseline": baseline_info["logical_sha256"],
    }
    physical_hashes = {
        "accelerated": accelerated.services.video.surface.hash(),
        "baseline": baseline.services.video.surface.hash(),
    }
    if set(logical_hashes.values()) != {LOGICAL_HASH}:
        raise RuntimeError(f"S3 logical frame mismatch: {logical_hashes}")
    if set(physical_hashes.values()) != {PHYSICAL_HASH}:
        raise RuntimeError(f"S3 projected frame mismatch: {physical_hashes}")

    logical = accelerated.engine._video.logical_surface
    assert logical is not None
    probes = {
        "actor_visible": logical.pixels[90 * 320 + 135],
        "actor_behind_mask": logical.pixels[90 * 320 + 142],
        "foreground_actor": logical.pixels[100 * 320 + 145],
        "font_same": logical.pixels[16 * 320 + 50],
        "font_font": logical.pixels[180 * 320 + 236],
    }
    expected_probes = {
        "actor_visible": 28,
        "actor_behind_mask": 5,
        "foreground_actor": 30,
        "font_same": 31,
        "font_font": 31,
    }
    if probes != expected_probes:
        raise RuntimeError(f"S3 scene probes differ: {probes}")

    accelerated.tick(pointer=(319, 199))
    cursor = [accelerated.services.video.cursor.x, accelerated.services.video.cursor.y]
    if cursor != [255, 211]:
        raise RuntimeError(f"S3 projected cursor differs: {cursor}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    logical_path = OUTPUT / "logical.png"
    physical_path = OUTPUT / "physical.png"
    logical.to_image().save(logical_path)
    accelerated.services.video.write_png(physical_path)
    report = {
        "gate": "S3",
        "result": "pass",
        "commercial_data_used": False,
        "profile": PROFILE.relative_to(ROOT).as_posix(),
        "profile_sha256": sha256(PROFILE.read_bytes()),
        "fixtures": {
            name: sha256((ROOT / f"examples/resources/scumm_v5/{name}").read_bytes())
            for name in ("s3_scene.scn3", "s3_font.char", "s3_cursor.scc3")
        },
        "logical_hashes": logical_hashes,
        "physical_hashes": physical_hashes,
        "accelerated": accelerated_info,
        "baseline": baseline_info,
        "probes": probes,
        "cursor_logical": [319, 199],
        "cursor_physical": cursor,
        "images": {
            "logical.png": sha256(logical_path.read_bytes()),
            "physical.png": sha256(physical_path.read_bytes()),
        },
    }
    report_path = OUTPUT / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(report_path.relative_to(ROOT))
    print(sha256(report_path.read_bytes()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

