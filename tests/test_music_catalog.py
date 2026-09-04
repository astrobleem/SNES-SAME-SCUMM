from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from same.errors import ResourceError
from same.music import CompiledMusicCatalog


ROOT = Path(__file__).resolve().parents[1]


def catalog(entry: dict[str, object] | None = None) -> bytes:
    source = b"source"
    value = {
        "logical_id": 7,
        "source_resource": "music.fixture",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "compiled_song": "fixture_song",
        "compiled_song_id": 3,
        "duration": 60,
        "loop": [12, 60],
    }
    if entry:
        value.update(entry)
    return (json.dumps({
        "schema": "same_compiled_music_catalog_v1",
        "name": "fixture",
        "time_scale": 60,
        "entries": [value],
    }) + "\n").encode()


class CompiledMusicCatalogTests(unittest.TestCase):
    def test_distinct_compiled_routes_share_source_but_not_route_identity(self) -> None:
        value = json.loads(catalog())
        first = value["entries"][0]
        first["route"] = {
            "kind": "default", "value": 0, "identity": "1" * 64,
            "instrument_bank_sha256": "2" * 64, "branch": [0, 100, 0, 1920],
        }
        second = dict(first)
        second.update({"compiled_song": "hook_song", "compiled_song_id": 4})
        second["route"] = {
            "kind": "hook", "value": 14, "identity": "3" * 64,
            "instrument_bank_sha256": "2" * 64, "branch": [0, 90, 3, 1920],
        }
        value["entries"].append(second)
        decoded = CompiledMusicCatalog.decode(json.dumps(value).encode(), "routes.catalog")
        self.assertEqual(decoded.resolve(7, "default", 0).compiled_song_id, 3)
        self.assertEqual(decoded.resolve(7, "hook", 14).compiled_song_id, 4)
        self.assertEqual(decoded.resolve(7, "hook", 14).identity, "3" * 64)

    def test_identity_duration_loop_and_source_are_exact(self) -> None:
        decoded = CompiledMusicCatalog.decode(
            catalog(), "fixture.catalog",
            source_reader=lambda key: b"source",
            compiled_songs={"fixture_song": 3},
        )
        entry = decoded.resolve(7)
        self.assertEqual(entry.duration_frames(60, decoded.time_scale), 60)
        self.assertEqual(entry.loop_frames(60, decoded.time_scale), (12, 60))
        self.assertEqual(entry.identity, f"music.fixture@{hashlib.sha256(b'source').hexdigest()}")

    def test_corruption_and_duplicate_identities_fail_closed(self) -> None:
        with self.assertRaisesRegex(ResourceError, "invalid JSON"):
            CompiledMusicCatalog.decode(b"{", "bad.catalog")
        original = json.loads(catalog())
        for changed, pattern in (
            ({"schema": "wrong"}, "unsupported schema"),
            ({"time_scale": 0}, "time scale"),
        ):
            value = dict(original)
            value.update(changed)
            with self.subTest(pattern=pattern), self.assertRaisesRegex(ResourceError, pattern):
                CompiledMusicCatalog.decode(json.dumps(value).encode(), "bad.catalog")
        for field, pattern in (
            ("logical_id", "repeats logical id"),
            ("source", "repeats source identity"),
            ("compiled_song_id", "repeats compiled song id"),
        ):
            value = json.loads(catalog())
            duplicate = dict(value["entries"][0])
            duplicate["logical_id"] = 8
            duplicate["source_resource"] = "music.other"
            duplicate["source_sha256"] = hashlib.sha256(b"other").hexdigest()
            duplicate["compiled_song"] = "other_song"
            duplicate["compiled_song_id"] = 4
            if field == "logical_id":
                duplicate["logical_id"] = 7
            elif field == "source":
                duplicate["source_resource"] = "music.fixture"
                duplicate["source_sha256"] = hashlib.sha256(b"source").hexdigest()
            else:
                duplicate["compiled_song_id"] = 3
            value["entries"].append(duplicate)
            with self.subTest(field=field), self.assertRaisesRegex(ResourceError, pattern):
                CompiledMusicCatalog.decode(json.dumps(value).encode(), "bad.catalog")

    def test_stale_source_and_missing_or_renumbered_song_fail_closed(self) -> None:
        with self.assertRaisesRegex(ResourceError, "is stale"):
            CompiledMusicCatalog.decode(
                catalog(), "fixture.catalog", source_reader=lambda key: b"changed",
            )
        with self.assertRaisesRegex(ResourceError, "is missing"):
            CompiledMusicCatalog.decode(
                catalog(), "fixture.catalog", compiled_songs={"another": 3},
            )
        with self.assertRaisesRegex(ResourceError, "is id 4, not 3"):
            CompiledMusicCatalog.decode(
                catalog(), "fixture.catalog", compiled_songs={"fixture_song": 4},
            )

    def test_generator_emits_exact_bounded_table_without_title_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "catalog.json"
            enums = root / "tad.inc"
            output = root / "music.inc.pasm"
            lifecycle = root / "music-lifecycle.inc.pasm"
            source.write_bytes(catalog())
            enums.write_text("!Song_fixture_song = 3\n", encoding="utf-8")
            subprocess.run(
                [sys.executable, str(ROOT / "tools/generate_music_catalog.py"),
                 str(source), str(enums), str(output)],
                check=True, cwd=ROOT, capture_output=True, text=True,
            )
            text = output.read_text(encoding="utf-8")
            self.assertIn("SAME_MUSIC_CATALOG_COUNT = $01", text)
            self.assertIn(".byte $07, $03", text)
            subprocess.run(
                [sys.executable, str(ROOT / "tools/generate_music_catalog.py"),
                 str(source), str(enums), str(output),
                 "--lifecycle-output", str(lifecycle)],
                check=True, cwd=ROOT, capture_output=True, text=True,
            )
            lifecycle_text = lifecycle.read_text(encoding="utf-8")
            self.assertIn("SAME_MUSIC_LIFECYCLE_COUNT = $01", lifecycle_text)
            self.assertIn(".word $0000", lifecycle_text)  # looping never auto-completes
            source.write_bytes(catalog({"loop": None}))
            subprocess.run(
                [sys.executable, str(ROOT / "tools/generate_music_catalog.py"),
                 str(source), str(enums), str(output),
                 "--lifecycle-output", str(lifecycle)],
                check=True, cwd=ROOT, capture_output=True, text=True,
            )
            self.assertIn(
                ".word $003C", lifecycle.read_text(encoding="utf-8"),
            )  # 60 source ticks at 60 Hz
        backend = (ROOT / "runtime/snes/services/audio.pasm").read_text(encoding="utf-8")
        self.assertNotIn("FATE_SOUND", backend)
        self.assertNotIn("fate", backend.lower())
        self.assertNotIn("monkey", backend.lower())


if __name__ == "__main__":
    unittest.main()
