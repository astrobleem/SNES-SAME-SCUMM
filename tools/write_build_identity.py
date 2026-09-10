#!/usr/bin/env python3
"""Write reproducibility metadata beside a finalized SAME ROM."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def corpus_identity(archive: str | None) -> dict[str, object]:
    if not archive:
        return {"archive": None}
    path = Path(archive).resolve()
    result: dict[str, object] = {"archive": str(path), "archive_sha256": sha256(path)}
    with ZipFile(path) as bundle:
        members = {}
        for name in bundle.namelist():
            upper = name.upper()
            if upper.endswith((".000", ".001")):
                members[name] = hashlib.sha256(bundle.read(name)).hexdigest()
        result["members"] = members
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--poppy-sha256", required=True)
    parser.add_argument("--carrier-manifest", type=Path, required=True)
    parser.add_argument("--video-backend-manifest", type=Path, required=True)
    parser.add_argument("--video-overlay-manifest", type=Path, required=True)
    args = parser.parse_args()

    status = git("status", "--short")
    tracked_diff = subprocess.check_output(
        ["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    generated = []
    candidates = [
        ROOT / "runtime/snes/generated/active_engine.inc.pasm",
        ROOT / "runtime/snes/generated/build_config.inc.pasm",
        ROOT / "runtime/snes/generated/scumm_v5_rooms.inc.pasm",
        ROOT / "runtime/snes/generated/scumm_v5_room_data.inc.pasm",
        ROOT / "runtime/snes/generated/scumm_v5_room_visuals.inc.pasm",
        ROOT / "runtime/snes/generated/scumm_v5_actor_sprite.inc.pasm",
        ROOT / "runtime/snes/generated/scumm_v5_object_sprite.inc.pasm",
        args.carrier_manifest.resolve(),
        args.video_backend_manifest.resolve(),
        args.video_overlay_manifest.resolve(),
        args.rom.with_suffix(".charset.json").resolve(),
    ]
    for path in candidates:
        if path.is_file():
            generated.append({"path": str(path.relative_to(ROOT)), "sha256": sha256(path)})

    environment = {
        key: value
        for key, value in sorted(os.environ.items())
        if key.startswith("SAME_") or key in {
            "POPPY_ROOT", "DOTNET_ROOT", "PYTHON"
        }
    }
    identity = {
        "format": "same-build-identity-v1",
        "rom": {"path": str(args.rom), "sha256": sha256(args.rom)},
        "git": {
            "head": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "worktree": str(ROOT),
            "dirty": bool(status),
            "status_sha256": hashlib.sha256(status.encode()).hexdigest(),
            "diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        },
        "explicit_environment": environment,
        "generated_inputs": generated,
        "generated_inputs_sha256": hashlib.sha256(
            json.dumps(generated, sort_keys=True).encode()
        ).hexdigest(),
        "corpus": corpus_identity(environment.get("SAME_FATE_DEMO_ARCHIVE")),
        "poppy_sha256": args.poppy_sha256,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(identity, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "build_identity": str(args.output),
        "build_identity_sha256": sha256(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
