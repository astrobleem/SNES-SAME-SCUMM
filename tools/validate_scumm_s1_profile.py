#!/usr/bin/env python3
"""Validate the S1 SCUMM game-policy boundary without reading game data."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile

from same.engines.scumm_v5.policy import parse_game_policy
from same.errors import ProfileValidationError
from same.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json"
DEFAULT_OUTPUT = ROOT / "build/scumm-s1-profile/report.json"
DONOR_ROOT = Path("/home/chad/SNES-SuperMonkeyIsland-latest")
DONOR_HEAD = "3247641c38d00aa2ce5388708ab7301d43d865aa"
DONOR_REFERENCES = {
    "tools/scumm_patches.json": "1afc1929e35b1fed9e1cc1dd26c345bba402c2d2ff53fad053c9992aca718c4e",
    "tools/scumm/gen_audio_map.py": "8e01411a29533fa24ddafd4d7768f82d28ca86e90b0767c2e2ba7549ea7ef601",
    "tools/audio/build_speech_msu.py": "8d23939b89a0771a70d7f29726ba5538a068bc60eb58daee668cb3515649c5fa",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    profile_path = args.profile.resolve()
    output = args.output.resolve()

    profile = load_profile(profile_path, verify_resources=False)
    policy = parse_game_policy(profile)
    require(policy is not None, "template did not opt into the structured SCUMM policy")

    try:
        load_profile(profile_path, verify_resources=True)
    except ProfileValidationError as exc:
        missing_error = str(exc)
    else:
        raise RuntimeError("template unexpectedly validated without user resources")
    require("required resource 'game.index'" in missing_error, missing_error)

    raw = json.loads(profile_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        temporary_root = Path(temporary)
        for binding in raw["resources"]:
            binding["path"] = binding["key"].replace(".", "_") + ".bin"
            if binding.get("required", True):
                (temporary_root / binding["path"]).write_bytes(b"S1")
        supplied_path = temporary_root / "profile.json"
        supplied_path.write_text(json.dumps(raw), encoding="utf-8")
        supplied = load_profile(supplied_path, verify_resources=True)
        require(parse_game_policy(supplied) == policy, "policy changed with resource location")

    core_path = ROOT / "src/same/engines/scumm_v5/engine.py"
    core_text = core_path.read_text(encoding="utf-8")
    require("profile.game_id" not in core_text, "opcode core branches on game identity")
    require("monkey1" not in core_text.lower(), "opcode core contains Monkey1 policy")

    donor_records = {}
    for relative, expected in DONOR_REFERENCES.items():
        path = DONOR_ROOT / relative
        observed = digest(path)
        require(observed == expected, f"donor reference changed: {relative}")
        donor_records[relative] = observed

    report = {
        "gate": "S1-monkey-profile-extraction",
        "result": "pass",
        "profile": str(profile_path),
        "profile_sha256": digest(profile_path),
        "game_id": profile.game_id,
        "policy": asdict(policy),
        "quirks": dict(profile.quirks),
        "missing_resource_failure": missing_error,
        "supplied_resource_layout_validated": True,
        "opcode_core": str(core_path),
        "opcode_core_sha256": digest(core_path),
        "opcode_core_game_identity_branch": False,
        "donor_reference": {
            "path": str(DONOR_ROOT),
            "head": DONOR_HEAD,
            "files": donor_records,
            "behavior_used_as_oracle": False,
        },
        "game_data_read": False,
        "monkey_rom_run": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("S1 SCUMM profile boundary: PASS")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
