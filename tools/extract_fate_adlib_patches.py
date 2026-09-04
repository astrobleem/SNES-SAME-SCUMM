#!/usr/bin/env python3
"""Extract iMUSE AdLib patch records from a user-supplied Fate demo archive."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import zipfile

from same.engine import EngineHost
from same.engines import default_registry
from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedSound
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
CATALOG = ROOT / "examples/resources/music/fate_s6_compiled.json"
MEMBERS = {
    "index": "FATEDEMO/PLAYFATE.000",
    "data": "FATEDEMO/PLAYFATE.001",
    "notice": "FATEDEMO/READ.ME",
}


def load_resource(archive: Path, sound_id: int) -> bytes:
    with zipfile.ZipFile(archive) as bundle:
        raw = {name: bundle.read(member) for name, member in MEMBERS.items()}
    resources = MemoryResourceProvider(
        {
            "game.index": raw["index"],
            "game.data": raw["data"],
            "distribution.notice": raw["notice"],
            "music.catalog": CATALOG.read_bytes(),
        },
        kinds={
            "game.index": "SCIX", "game.data": "SCDT",
            "distribution.notice": "TEXT",
            "music.catalog": "MCAT",
        },
    )
    profile = load_profile(PROFILE, verify_resources=False)
    host = EngineHost(
        profile, default_registry(),
        services=HostServices.create(profile, resources=resources),
    )
    host.boot()
    return host.services.resources.read(f"sound.{sound_id}")


def extract_patch_records(raw: bytes, sound_id: int) -> tuple[bytes, list[int]]:
    sound = ScummV5EmbeddedSound.decode(
        raw, f"sound.{sound_id}", rendition_order=(b"ADL ",),
    )
    records = bytearray()
    channels: list[int] = []
    for track in sound.imuse_events:
        for event in track:
            if event.command != 0x10:
                continue
            channel, *instrument = event.values
            if len(instrument) != 30:
                raise RuntimeError(
                    f"sound {sound_id} channel {channel} has a non-extended "
                    f"{len(instrument)}-byte AdLib patch"
                )
            records.extend((channel, *instrument))
            channels.append(channel)
    if not records:
        raise RuntimeError(f"sound {sound_id} contains no AdLib patches")
    return bytes(records), channels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/home/chad/fatedemo-box.zip"))
    parser.add_argument("--sound", type=int, default=154)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records, channels = extract_patch_records(
        load_resource(args.archive.resolve(), args.sound), args.sound,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(records)
    print(f"patches={len(channels)} channels={','.join(map(str, channels))}")
    print(f"bytes={len(records)} sha256={hashlib.sha256(records).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
