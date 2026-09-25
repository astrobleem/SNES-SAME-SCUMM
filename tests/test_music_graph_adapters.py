from __future__ import annotations

from pathlib import Path
import hashlib
import json
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class MusicGraphAdapterRegistryTests(unittest.TestCase):
    def test_profile_orchestrator_has_no_scumm_adapter_import(self) -> None:
        source = (ROOT / "tools/build_profile_music_rom.py").read_text("utf-8")
        self.assertNotIn("build_scumm_v5_music_graph", source)

    def test_registry_requires_matching_engine_and_source_family(self) -> None:
        from music_graph_adapters import default_music_graph_adapters

        registry = default_music_graph_adapters()
        qtma = registry.resolve("demo", "qtma_fixture_v1")
        self.assertFalse(qtma.requires_source_archive)
        qtma_movie = registry.resolve("demo", "qtma_mov_musi_v1")
        self.assertFalse(qtma_movie.requires_source_archive)
        scumm = registry.resolve("scumm_v5", "scumm_v5_archive_v1")
        self.assertTrue(scumm.requires_source_archive)
        with self.assertRaisesRegex(ValueError, "no music graph adapter"):
            registry.resolve("scumm_v5", "qtma_fixture_v1")

    def test_qtma_movie_adapter_terminates_at_existing_importer_and_mml(self) -> None:
        from same.music import load_profile_music_graph
        from same.profile import load_profile
        from music_graph_adapters import default_music_graph_adapters

        for name, policy in (
            ("qtma_music_mov_runtime_conformance.json", "exact"),
            ("qtma_music_time_runtime_conformance.json", "nearest_absolute"),
        ):
            with self.subTest(profile=name):
                profile = load_profile(
                    ROOT / "examples/profiles" / name, verify_resources=False,
                )
                graph = load_profile_music_graph(
                    profile,
                    dependency_reader=lambda path: (ROOT / path).read_bytes(),
                )
                self.assertEqual(
                    graph.nodes[0].policy["time_normalization"], policy,
                )
                registration = default_music_graph_adapters().resolve(
                    profile.engine_id, graph.adapter,
                )
                adapter = registration.factory(None, graph)
                source = adapter.read_source(graph.nodes[0])
                self.assertEqual(
                    hashlib.sha256(source).hexdigest(),
                    graph.nodes[0].source_sha256,
                )
                self.assertEqual(
                    hashlib.sha256(
                        adapter.render(graph.nodes[0], source),
                    ).hexdigest(),
                    graph.nodes[0].mml_sha256,
                )
                audit = adapter.audit(graph.nodes[0])
                self.assertEqual(
                    hashlib.sha256(audit).hexdigest(),
                    graph.nodes[0].audit_sha256,
                )
                document = json.loads(audit)
                self.assertEqual(
                    document["schema"], "same_music_sequence_audit_v1",
                )
                self.assertEqual(
                    document["normalized"]["end_tick"], graph.nodes[0].duration,
                )
                fresh = registration.factory(None, graph)
                with patch(
                    "build_qtma_music_graph.extract_qtma_movie",
                    side_effect=AssertionError("MOV importer entered during IR replay"),
                ), patch(
                    "build_qtma_music_graph.decode_qtma_events",
                    side_effect=AssertionError("QTMA importer entered during IR replay"),
                ):
                    replayed = fresh.replay_audit(graph.nodes[0], audit)
                self.assertEqual(
                    hashlib.sha256(replayed).hexdigest(),
                    graph.nodes[0].mml_sha256,
                )
        adapter_source = (ROOT / "tools/build_qtma_music_graph.py").read_text()
        self.assertIn("extract_qtma_movie", adapter_source)
        self.assertIn("decode_qtma_events", adapter_source)

    def test_qtma_runtime_personality_uses_only_generic_audio_packets(self) -> None:
        profile = json.loads(
            (ROOT / "examples/profiles/qtma_music_runtime_conformance.json").read_text()
        )
        self.assertEqual(profile["options"]["snes_personality"], "qtma_conformance")
        source = (ROOT / "runtime/snes/engines/qtma_conformance.pasm").read_text()
        lifecycle = (ROOT / "runtime/snes/services/music_lifecycle.pasm").read_text()
        self.assertIn("Same_MusicLifecycle_Play", source)
        self.assertIn("SAME_AUDIO_OP_MUSIC_PLAY", lifecycle)
        self.assertIn("SAME_AUDIO_OP_MUSIC_STOP", lifecycle)
        self.assertNotIn("SAME_TAD_", source)
        self.assertNotIn("APUIO", source)
        self.assertNotIn("SAME_TAD_", lifecycle)
        self.assertNotIn("APUIO", lifecycle)


if __name__ == "__main__":
    unittest.main()
