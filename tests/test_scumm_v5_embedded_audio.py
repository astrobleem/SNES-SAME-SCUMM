from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import unittest

from same.engine import EngineHost
from same.capabilities import EngineCapability
from same.engines import default_registry
from same.engines.scumm_v5.embedded_audio import (
    ScummV5EmbeddedAudioAdapter, ScummV5EmbeddedSound,
)
from same.engines.scumm_v5.engine import ScriptSlot
from same.errors import ResourceError, SaveFormatError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices


ROOT = Path(__file__).resolve().parents[1]
ROOM = (ROOT / "examples/resources/scumm_v5/room0.sc5r").read_bytes()


def chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + len(payload).to_bytes(4, "big") + payload


def synthetic_sound() -> bytes:
    track = bytes((
        0x00, 0xFF, 0x51, 0x03, 0x07, 0xA1, 0x20,
        0x00, 0xC0, 0x05,
        0x00, 0x90, 0x45, 0x64,
        0x83, 0x60, 0x80, 0x45, 0x00,
        0x00, 0xFF, 0x2F, 0x00,
    ))
    midi = b"MThd" + struct.pack(">IHHH", 6, 2, 1, 480) + chunk(b"MTrk", track)
    mdhd = chunk(b"MDhd", bytes((0, 0, 96, 127, 0, 0, 0, 128)))
    rol = chunk(b"ROL ", mdhd + midi)
    adl = chunk(b"ADL ", mdhd + midi)
    return chunk(b"SOU ", rol + adl)


def sysex(payload: bytes) -> bytes:
    return bytes((0, 0xF0, len(payload))) + payload


def interactive_sound(*, jump_padding: bytes = b"") -> bytes:
    # Hook 3 jumps from track 0/tick 10 to track 1/tick 0. Track 1 emits marker 9.
    jump = bytes.fromhex("7d3000") + bytes((
        0, 3, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0,
    )) + jump_padding + b"\xf7"
    track0 = (
        bytes((0, 0x90, 60, 100, 10, 0xF0, len(jump))) + jump
        + bytes((10, 0x80, 60, 0, 0, 0xFF, 0x2F, 0))
    )
    marker = bytes.fromhex("7d400009f7")
    track1 = (
        bytes((0, 0x90, 72, 100, 0, 0xF0, len(marker))) + marker
        + bytes((20, 0x80, 72, 0, 0, 0xFF, 0x2F, 0))
    )
    midi = (b"MThd" + struct.pack(">IHHH", 6, 2, 2, 480)
            + chunk(b"MTrk", track0) + chunk(b"MTrk", track1))
    return chunk(b"SOU ", chunk(b"ROL ", midi))


def adlib_instrument_sound() -> bytes:
    instrument = bytes.fromhex(
        "7d100901000a030f050b0f0c0002000b0308050b0f0a0003000e"
    ) + bytes(38) + b"\xf7"
    track = (
        bytes((0, 0xF0, len(instrument))) + instrument
        + bytes((0, 0xFF, 0x2F, 0))
    )
    midi = b"MThd" + struct.pack(">IHHH", 6, 2, 1, 480) + chunk(b"MTrk", track)
    return chunk(b"SOU ", chunk(b"ADL ", midi))


class ScummV5EmbeddedAudioTests(unittest.TestCase):
    def test_duplicate_unselected_rendition_does_not_mask_selected_adlib(self) -> None:
        raw = synthetic_sound()
        rol_size = 8 + int.from_bytes(raw[12:16], "big")
        rol = raw[8 : 8 + rol_size]
        adl = raw[8 + rol_size :]
        sound = ScummV5EmbeddedSound.decode(
            chunk(b"SOU ", rol + rol + adl), "sound.duplicate-sbl",
            rendition_order=(b"ADL ", b"ROL "),
        )
        self.assertEqual(sound.rendition, "ADL")

    def test_duplicate_selected_rendition_fails_closed(self) -> None:
        raw = synthetic_sound()
        rol_size = 8 + int.from_bytes(raw[12:16], "big")
        rol = raw[8 : 8 + rol_size]
        with self.assertRaisesRegex(ResourceError, "repeats rendition"):
            ScummV5EmbeddedSound.decode(chunk(b"SOU ", rol + rol), "sound.bad")

    def test_monkey_zero_extended_jump_is_canonical_but_nonzero_is_not(self) -> None:
        compatible = interactive_sound(jump_padding=b"\x00")
        decoded = ScummV5EmbeddedSound.decode(compatible, "sound.monkey-jump")
        self.assertEqual(decoded.imuse_events[0][0].values, (3, 1, 1, 0))
        with self.assertRaisesRegex(ResourceError, "jump size is invalid"):
            ScummV5EmbeddedSound.decode(
                interactive_sound(jump_padding=b"\x01"), "sound.bad-jump"
            )

    def test_lucasarts_adlib_instrument_sysex_decodes_complete_patch(self) -> None:
        sound = ScummV5EmbeddedSound.decode(adlib_instrument_sound(), "sound.adlib")
        self.assertEqual(sound.rendition, "ADL")
        self.assertEqual(sound.inspect()["imuse"], {"16": 1})
        self.assertEqual(
            sound.imuse_events[0][0].values,
            (9, 0x0A, 0x3F, 0x5B, 0xFC, 0x02, 0x0B, 0x38, 0x5B,
             0xFA, 0x03, 0x0E, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
             0, 0, 0, 0, 0, 0, 0, 0),
        )

    def test_sou_rol_smf_decode_and_pcm_are_exact(self) -> None:
        raw = synthetic_sound()
        sound = ScummV5EmbeddedSound.decode(raw, "sound.synthetic")
        self.assertEqual(
            (sound.rendition, sound.priority, sound.midi_format, sound.track_count,
             sound.division, sound.duration_us, len(sound.events)),
            ("ROL", 96, 2, 1, 480, 500_000, 3),
        )
        pcm = sound.render_pcm()
        self.assertEqual(len(pcm), 22_050)
        self.assertNotEqual(set(pcm), {0})
        self.assertEqual(
            hashlib.sha256(pcm).hexdigest(),
            "cbacba490f9cf19c54492f32ae755a6cc236e8935df4b30ced8d1f3c99065b74",
        )

    def test_embedded_adapter_streams_status_stops_and_restores(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": b"\x80", "room.0": ROOM, "sound.7": synthetic_sound()},
            kinds={"script.boot": "SCRP", "room.0": "ROOM", "sound.7": "SOUN"},
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        adapter = ScummV5EmbeddedAudioAdapter(host.context, lambda sound: f"sound.{sound}")
        adapter.play_sfx(7)
        self.assertTrue(adapter.is_running(7))
        for _ in range(10):
            adapter.tick()
        saved = adapter.save_state()
        for _ in range(20):
            adapter.tick()
        self.assertFalse(adapter.is_running(7))
        self.assertEqual(
            hashlib.sha256(bytes(host.services.audio.pcm_streams[7])).hexdigest(),
            "cbacba490f9cf19c54492f32ae755a6cc236e8935df4b30ced8d1f3c99065b74",
        )
        adapter.load_state(saved)
        self.assertEqual(adapter.active_sfx, {7: 10})
        with self.assertRaisesRegex(SaveFormatError, "outside its sound"):
            adapter.load_state({
                "kind": "embedded-midi-v2", "music": None,
                "sfx": [[7, 30]], "speech": None, "players": {},
            })

    def test_compiled_catalog_play_loop_and_save_restore_use_stable_identity(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        raw_sound = synthetic_sound()
        source_hash = hashlib.sha256(raw_sound).hexdigest()
        raw_catalog = (json.dumps({
            "schema": "same_compiled_music_catalog_v1",
            "name": "compiled fixture",
            "time_scale": 60,
            "entries": [{
                "logical_id": 7,
                "source_resource": "sound.7",
                "source_sha256": source_hash,
                "compiled_song": "fixture_song",
                "compiled_song_id": 3,
                "duration": 30,
                "loop": [5, 30],
            }],
        }) + "\n").encode()
        profile = replace(
            profile,
            optional_capabilities=profile.optional_capabilities | EngineCapability.CHIP_AUDIO,
            options={**profile.options, "compiled_music_catalog": "music.catalog"},
        )
        resources = MemoryResourceProvider({
            "script.boot": b"\x80", "room.0": ROOM,
            "sound.7": raw_sound, "music.catalog": raw_catalog,
        })
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        adapter = ScummV5EmbeddedAudioAdapter(host.context, lambda sound: f"sound.{sound}")
        adapter.play_music(7)
        self.assertEqual(adapter.inspect()["backend"], "compiled_tad")
        self.assertNotIn(7, host.services.audio.pcm_streams)
        command = host.services.audio.command_history[-1]
        self.assertEqual(command["backend"], "compiled_tad")
        self.assertEqual(command["resource"], f"sound.7@{source_hash}")
        for _ in range(12):
            adapter.tick()
        saved = adapter.save_state()
        self.assertEqual(saved["music_identity"], f"sound.7@{source_hash}")
        for _ in range(18):
            adapter.tick()
        self.assertEqual(adapter.music_position, 5)
        adapter.load_state(saved)
        self.assertEqual((adapter.music_id, adapter.music_position), (7, 12))
        broken = dict(saved)
        broken["music_identity"] = "sound.7@" + "0" * 64
        before = adapter.inspect()
        with self.assertRaisesRegex(SaveFormatError, "source identity differs"):
            adapter.load_state(broken)
        self.assertEqual(adapter.inspect(), before)

    def test_imuse_hook_jump_marker_and_player_state_restore(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider({"sound.8": interactive_sound()})
        services = HostServices.create(profile, resources=resources)
        context = type("Context", (), {"profile": profile, "services": services})()
        adapter = ScummV5EmbeddedAudioAdapter(context, lambda sound: f"sound.{sound}")
        decoded = adapter._sound(8)
        self.assertEqual((decoded.track_count, decoded.inspect()["imuse"]),
                         (2, {"48": 1, "64": 1}))
        adapter.play_sfx(8)
        self.assertTrue(adapter.set_hook(8, 0, 3, 0))
        adapter.tick()
        state = adapter.inspect()["imuse"]["8"]
        self.assertEqual(state["track"], 1)
        self.assertEqual(state["hooks"], [0, 0])
        self.assertEqual(state["markers"], [9])
        self.assertEqual(state["branches"], [[0, 10, 1, 0]])
        saved = adapter.save_state()
        prefix_size = len(services.audio.pcm_streams[8])
        adapter.tick()
        expected = bytes(services.audio.pcm_streams[8])
        adapter.load_state(saved)
        adapter.tick()
        self.assertEqual(bytes(services.audio.pcm_streams[8]), expected[prefix_size:])

    def test_compiled_section_hook_remains_pending_until_authored_boundary(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        raw_sound = synthetic_sound()
        source_hash = hashlib.sha256(raw_sound).hexdigest()
        route_default, route_hook = "1" * 64, "2" * 64
        bank, plan = "3" * 64, "4" * 64
        raw_catalog = (json.dumps({
            "schema": "same_compiled_music_catalog_v1", "name": "section fixture",
            "time_scale": 60,
            "entries": [
                {"logical_id": 80, "source_resource": "sound.80",
                 "source_sha256": source_hash, "compiled_song": "default_song",
                 "compiled_song_id": 1, "duration": 30, "loop": None,
                 "route": {"kind": "default", "value": 0, "identity": route_default,
                           "instrument_bank_sha256": bank, "branch": [0, 100, 0, 1920]}},
                {"logical_id": 80, "source_resource": "sound.80",
                 "source_sha256": source_hash, "compiled_song": "hook_song",
                 "compiled_song_id": 2, "duration": 30, "loop": None,
                 "route": {"kind": "hook", "value": 14, "identity": route_hook,
                           "instrument_bank_sha256": bank, "branch": [0, 90, 3, 1920]}},
            ],
            "sections": [{"logical_id": 80, "route_kind": "hook", "route_value": 14,
                          "hook_value": 8, "boundary": 3, "boundary_token": 1,
                          "current_section": 1, "default_section": 3,
                          "hook_section": 2, "selector": 1,
                          "source_branch": [3, 68160, 3, 1920], "identity": plan,
                          "instrument_bank_sha256": bank}],
        }) + "\n").encode()
        profile = replace(
            profile,
            optional_capabilities=profile.optional_capabilities | EngineCapability.CHIP_AUDIO,
            options={**profile.options, "compiled_music_catalog": "music.catalog"},
        )
        resources = MemoryResourceProvider({"sound.80": raw_sound, "music.catalog": raw_catalog})
        services = HostServices.create(profile, resources=resources)
        context = type("Context", (), {"profile": profile, "services": services,
                                       "negotiated_capabilities": EngineCapability.CHIP_AUDIO})()
        adapter = ScummV5EmbeddedAudioAdapter(context, lambda sound: f"sound.{sound}")
        adapter.play_music(80)
        self.assertTrue(adapter.set_hook(80, 0, 14, 0))
        before = adapter.music_position
        self.assertTrue(adapter.set_hook(80, 0, 8, 0))
        self.assertEqual((adapter.music_route, adapter.music_position), (("hook", 14), before))
        self.assertEqual(services.audio.command_history[-1]["command"], "music_section_select")
        adapter.tick()
        self.assertEqual(adapter.music_section["consumption"], "pending")
        for _ in range(2):
            adapter.tick()
        self.assertEqual(adapter.music_section["consumption"], "consumed")
        self.assertEqual(adapter.music_section["current"], 2)
        saved = adapter.save_state()
        adapter.stop_music()
        adapter.load_state(saved)
        self.assertEqual(adapter.music_section["consumption"], "consumed")
        broken = json.loads(json.dumps(saved))
        broken["music_section"]["identity"] = "0" * 64
        before_state = adapter.inspect()
        with self.assertRaisesRegex(SaveFormatError, "section identity differs"):
            adapter.load_state(broken)
        self.assertEqual(adapter.inspect(), before_state)

    def test_is_sound_running_direct_and_variable_forms(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = MemoryResourceProvider(
            {"script.boot": b"\x80", "room.0": ROOM, "sound.7": synthetic_sound()},
            kinds={"script.boot": "SCRP", "room.0": "ROOM", "sound.7": "SOUN"},
        )
        host = EngineHost(
            profile, default_registry(),
            services=HostServices.create(profile, resources=resources),
        )
        host.boot()
        host.engine._audio = ScummV5EmbeddedAudioAdapter(
            host.context, lambda sound: f"sound.{sound}"
        )
        host.engine.state.variables[2] = 7
        host.engine.state.scripts = [ScriptSlot("c40", bytes((
            0x1C, 7,
            0x7C, 0, 0, 7,
            0xFC, 1, 0, 2, 0,
            0x3C, 7,
            0x7C, 3, 0, 7,
            0x00,
        )))]
        host.tick()
        self.assertEqual(host.engine.state.variables[:4], [1, 1, 7, 0])

    def test_embedded_sound_corruption_fails_closed(self) -> None:
        raw = synthetic_sound()
        malformed = (
            (raw[:-1], "SOU size differs"),
            (chunk(b"SOU ", chunk(b"VOC ", b"x")), "no supported rendition"),
            (chunk(b"SOU ", chunk(b"ROL ", b"MDhd")), "no MIDI header"),
            (raw.replace(b"MTrk", b"BAD!", 1), "track 0 header is absent"),
        )
        for payload, message in malformed:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ResourceError, message):
                    ScummV5EmbeddedSound.decode(payload, "sound.bad")


if __name__ == "__main__":
    unittest.main()
