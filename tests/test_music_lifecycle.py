from __future__ import annotations

import hashlib
import json
import unittest

from same.abi import AudioOpcode, EngineOpcode
from same.music import (
    CompiledMusicCatalog, CompiledMusicLifecycle, MusicLifecycleStatus,
)


def _catalog(*, loop: bool = False) -> CompiledMusicCatalog:
    raw = (json.dumps({
        "schema": "same_compiled_music_catalog_v1", "name": "lifecycle",
        "time_scale": 125,
        "entries": [{
            "logical_id": 1, "source_resource": "music.fixture",
            "source_sha256": hashlib.sha256(b"fixture").hexdigest(),
            "compiled_song": "fixture", "compiled_song_id": 1,
            "duration": 600, "loop": [0, 600] if loop else None,
        }],
    }) + "\n").encode()
    return CompiledMusicCatalog.decode(raw, "fixture")


class MusicLifecycleTests(unittest.TestCase):
    def test_nonlooping_play_ready_and_natural_completion_are_exact(self) -> None:
        lifecycle = CompiledMusicLifecycle(_catalog())
        play = lifecycle.play(1, 120)
        self.assertEqual(play[0].audio, AudioOpcode.MUSIC_PLAY)
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.PENDING)
        self.assertEqual(lifecycle.tick(134), ())
        self.assertEqual(lifecycle.tick(135)[0].response, EngineOpcode.READY)
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.PLAYING)
        self.assertEqual(lifecycle.tick(422), ())
        complete = lifecycle.tick(423)
        self.assertEqual(
            [(item.audio, item.response) for item in complete],
            [(AudioOpcode.MUSIC_STOP, None), (None, EngineOpcode.STOPPED)],
        )
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.COMPLETED)

    def test_explicit_stop_is_distinct_from_completion(self) -> None:
        lifecycle = CompiledMusicLifecycle(_catalog())
        lifecycle.play(1, 10)
        stopped = lifecycle.stop()
        self.assertEqual(stopped[-1].response, EngineOpcode.STOPPED)
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.STOPPED)

    def test_invalid_identity_fails_without_audio_request(self) -> None:
        lifecycle = CompiledMusicLifecycle(_catalog())
        actions = lifecycle.play(99, 0)
        self.assertEqual(actions[0].response, EngineOpcode.FAILED)
        self.assertIsNone(actions[0].audio)
        self.assertEqual(actions[0].logical_id, 99)
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.FAILED)

    def test_looping_song_never_auto_completes(self) -> None:
        lifecycle = CompiledMusicLifecycle(_catalog(loop=True))
        lifecycle.play(1, 0)
        lifecycle.tick(15)
        self.assertEqual(lifecycle.tick(0xFFFF), ())
        self.assertEqual(lifecycle.status, MusicLifecycleStatus.PLAYING)


if __name__ == "__main__":
    unittest.main()
