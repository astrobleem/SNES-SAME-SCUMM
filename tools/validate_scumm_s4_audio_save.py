#!/usr/bin/env python3
"""Produce independently inspectable S4 audio/save conformance evidence."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json

from same.capabilities import DEFAULT_HOST_CAPABILITIES, EngineCapability
from same.engine import EngineHost
from same.engines import default_registry
from same.errors import SaveFormatError
from same.profile import load_profile
from same.savegame import SaveEnvelope
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples/profiles/scumm_v5_s4_conformance.json"
OUTPUT = ROOT / "build/scumm-s4-audio-save"


def host(capabilities: EngineCapability) -> EngineHost:
    profile = load_profile(PROFILE)
    result = EngineHost(
        profile,
        default_registry(),
        services=HostServices.create(profile, capabilities=capabilities),
    )
    result.boot()
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    accelerated = host(DEFAULT_HOST_CAPABILITIES)
    baseline = host(
        DEFAULT_HOST_CAPABILITIES
        & ~EngineCapability.CHIP_AUDIO
        & ~EngineCapability.MSU1_STREAM
    )
    accelerated.tick()
    baseline.tick()
    fast_audio = accelerated.engine.inspect_state()["audio"]
    slow_audio = baseline.engine.inspect_state()["audio"]
    require(fast_audio["backend"] == "curated_tad", "accelerated plan is not TAD")
    require(slow_audio["backend"] == "score_interpreter", "baseline plan is not score")
    logical_fields = ("music", "music_position", "sfx", "speech", "speech_position", "scores")
    require(
        all(fast_audio[field] == slow_audio[field] for field in logical_fields),
        "negotiated backends changed logical audio state",
    )

    room0_hash = accelerated.services.video.surface.hash()
    envelope = accelerated.save(0)
    payload_sha = hashlib.sha256(envelope.payload).hexdigest()
    saved_audio = accelerated.engine.inspect_state()["audio"]
    accelerated.tick()
    room1_hash = accelerated.services.video.surface.hash()
    require(room1_hash != room0_hash, "room transition did not change the frame")
    accelerated.load(0)
    restored = accelerated.engine.inspect_state()
    require(restored["room"] == 0, "save did not restore room zero")
    require(accelerated.services.video.surface.hash() == room0_hash, "room pixels did not restore")
    require(restored["audio"]["music_position"] == saved_audio["music_position"], "music playhead did not restore")
    require(restored["audio"]["sfx"] == saved_audio["sfx"], "SFX playhead did not restore")
    require(restored["audio"]["speech_position"] == saved_audio["speech_position"], "speech playhead did not restore")

    rejection: dict[str, str] = {}
    corrupt = bytearray(envelope.pack())
    corrupt[-1] ^= 0xFF
    invalid = {
        "wrong_game": SaveEnvelope("scumm_v5", "wrong-game", 2, envelope.payload).pack(),
        "wrong_schema": SaveEnvelope("scumm_v5", accelerated.profile.game_id, 1, envelope.payload).pack(),
        "bad_crc": bytes(corrupt),
    }
    for index, (name, raw) in enumerate(invalid.items(), 20):
        accelerated.services.saves.write(index, raw)
        try:
            accelerated.load(index)
        except SaveFormatError as exc:
            rejection[name] = str(exc)
        else:
            raise AssertionError(f"{name} save was accepted")

    report = {
        "gate": "S4",
        "result": "pass",
        "commercial_data_used": False,
        "plans": {"accelerated": fast_audio["backend"], "baseline": slow_audio["backend"]},
        "logical_audio": {field: fast_audio[field] for field in logical_fields},
        "commands": accelerated.services.audio.command_history[:3],
        "save": {
            "schema": envelope.schema,
            "payload_size": len(envelope.payload),
            "payload_sha256": payload_sha,
            "room0_sha256": room0_hash,
            "room1_sha256": room1_hash,
            "restored_audio": restored["audio"],
        },
        "rejections": rejection,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"S4 pass: {path.relative_to(ROOT)}")
    print(f"report sha256: {hashlib.sha256(path.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
