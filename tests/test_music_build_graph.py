from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from same.errors import ResourceError
from same.music import (
    MusicBuildGraph, compile_music_graph, load_profile_music_graph,
    profile_music_owner, verify_music_build, verify_profile_music_bundle,
)
from same.profile import load_profile


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _raw_graph(
    source: bytes, mml: bytes, dependency: bytes, audit: bytes | None = None,
) -> bytes:
    rendition = {
            "logical_id": 7, "source_resource": "music.7",
            "source_sha256": _sha(source), "importer": "fixture_v1",
            "source_device": "fixture_device_v1", "bank": "reviewed-bank",
            "target": "fixture_target_v1", "policy": {"voices": 8},
            "output": "song_7.mml", "mml_sha256": _sha(mml),
            "compiled_song": "fixture_song", "compiled_song_id": 3,
            "duration": 120, "loop": [10, 100],
    }
    if audit is not None:
        rendition.update({
            "audit_output": "song_7.audit.json",
            "audit_sha256": _sha(audit),
        })
    return (json.dumps({
        "schema": "same_music_build_graph_v1", "name": "fixture graph",
        "adapter": "fixture_v1",
        "profile": "fixture", "time_scale": 60,
        "project_output": "fixture.terrificaudio",
        "dependencies": [{
            "name": "reviewed-bank", "path": "bank.json",
            "sha256": _sha(dependency),
        }],
        "renditions": [rendition],
    }, indent=2) + "\n").encode()


class _Adapter:
    def __init__(
        self, source: bytes, mml: bytes, *, fail: bool = False, song_id: int = 3,
        audit: bytes | None = None,
    ) -> None:
        self.source = source
        self.mml = mml
        self.fail = fail
        self.song_id = song_id
        self.audit_data = audit

    def read_source(self, node) -> bytes:
        return self.source

    def render(self, node, source: bytes) -> bytes:
        return self.mml

    def audit(self, node) -> bytes:
        if self.audit_data is None:
            raise RuntimeError("fixture audit was not produced")
        return self.audit_data

    def finalize(self, graph, stage: Path, rendered, compiler: Path) -> None:
        (stage / graph.project_output).write_bytes(b"project\n")
        (stage / "tad.asm").write_bytes(b"asm\n")
        (stage / "tad.bin").write_bytes(b"bin\n")
        if self.fail:
            raise RuntimeError("fixture compiler failed")
        (stage / "tad.inc").write_text(
            f"!Song_fixture_song = {self.song_id}\n", encoding="utf-8",
        )


def _profile(path: Path, graph: Path, *, title: str = "Fixture") -> None:
    path.write_text(json.dumps({
        "same_engine_profile": 1,
        "engine": "scumm_v5",
        "game": {"id": "fixture", "title": title, "variant": "test"},
        "timing": {"tick_hz": 60, "max_ops_per_tick": 4096},
        "video": {"width": 256, "height": 224, "mode": "indexed8"},
        "input": {"profile": "scumm"},
        "capabilities": {"required": [], "optional": []},
        "resources": [{
            "key": "music.build_graph", "path": graph.name, "kind": "MBGR",
        }],
        "options": {"music_build_graph": "music.build_graph"},
    }) + "\n", encoding="utf-8")


class MusicBuildGraphTests(unittest.TestCase):
    def test_profile_bundle_binds_profile_graph_catalog_and_tad(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b"bank"
            graph_path = root / "graph.json"
            graph_path.write_bytes(_raw_graph(source, mml, dependency))
            profile_path = root / "profile.json"
            _profile(profile_path, graph_path)
            profile = load_profile(profile_path, verify_resources=False)
            graph = load_profile_music_graph(
                profile, dependency_reader=lambda path: dependency,
            )
            compiler = root / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = root / "bundle"
            compile_music_graph(
                graph, _Adapter(source, mml), output, compiler,
                owner=profile_music_owner(profile),
            )
            bundle = verify_profile_music_bundle(profile, graph, output, compiler)
            self.assertEqual(bundle.song_count, 1)
            self.assertEqual(bundle.graph_sha256, graph.sha256)

            _profile(profile_path, graph_path, title="Changed profile bytes")
            changed_profile = load_profile(profile_path, verify_resources=False)
            with self.assertRaisesRegex(ResourceError, "owner identity changed"):
                verify_profile_music_bundle(changed_profile, graph, output, compiler)

    def test_profile_bundle_rejects_tad_catalog_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b"bank"
            graph_path = root / "graph.json"
            graph_path.write_bytes(_raw_graph(source, mml, dependency))
            profile_path = root / "profile.json"
            _profile(profile_path, graph_path)
            profile = load_profile(profile_path, verify_resources=False)
            graph = load_profile_music_graph(
                profile, dependency_reader=lambda path: dependency,
            )
            compiler = root / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = root / "bundle"
            compile_music_graph(
                graph, _Adapter(source, mml, song_id=4), output, compiler,
                owner=profile_music_owner(profile),
            )
            with self.assertRaisesRegex(ResourceError, "id 4, not 3"):
                verify_profile_music_bundle(profile, graph, output, compiler)

    def test_complete_fate_graph_accounts_for_every_catalog_entry(self) -> None:
        root = Path(__file__).resolve().parents[1]
        graph_path = root / "examples/resources/music/fate_s6_build_graph.json"
        graph = MusicBuildGraph.decode(
            graph_path.read_bytes(), str(graph_path),
            dependency_reader=lambda path: (root / path).read_bytes(),
        )
        catalog = json.loads(
            (root / "examples/resources/music/fate_s6_compiled.json").read_text()
        )
        self.assertEqual(len(graph.nodes), 21)
        self.assertEqual(
            {node.logical_id for node in graph.nodes},
            {entry["logical_id"] for entry in catalog["entries"]},
        )
        importers = [node.importer for node in graph.nodes]
        self.assertEqual(importers.count("reviewed_immutable_mml_v1"), 16)
        self.assertEqual(importers.count("scumm_v5_rol_reviewed_v1"), 4)
        self.assertEqual(importers.count("scumm_v5_adlib_reviewed_v1"), 1)
        dependencies = {item.name: item for item in graph.dependencies}
        for node in graph.nodes:
            if node.importer != "reviewed_immutable_mml_v1":
                continue
            dependency = dependencies[node.policy["reviewed_dependency"]]
            self.assertEqual(dependency.sha256, node.mml_sha256)
            if not node.policy.get("m22_section_postlink"):
                self.assertEqual(Path(dependency.path).name, Path(node.output).name)

    def test_music_build_graph_is_repeatable_and_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b"bank"
            graph = MusicBuildGraph.decode(
                _raw_graph(source, mml, dependency), "fixture",
                dependency_reader=lambda path: dependency,
            )
            compiler = tmp_path / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = tmp_path / "output"
            first = compile_music_graph(graph, _Adapter(source, mml), output, compiler)
            first_files = {
                str(path.relative_to(output)): path.read_bytes()
                for path in output.rglob("*") if path.is_file()
            }
            second = compile_music_graph(graph, _Adapter(source, mml), output, compiler)
            second_files = {
                str(path.relative_to(output)): path.read_bytes()
                for path in output.rglob("*") if path.is_file()
            }
            self.assertEqual(first, second)
            self.assertEqual(first_files, second_files)
            verify_music_build(graph, output, compiler)
            catalog = json.loads((output / "catalog.json").read_text())
            self.assertEqual(catalog["entries"][0]["logical_id"], 7)

    def test_audit_artifact_is_expected_hashed_and_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b'{"audit":1}\n'
            audit = b'{"schema":"fixture_audit_v1"}\n'
            graph = MusicBuildGraph.decode(
                _raw_graph(source, mml, dependency, audit), "fixture",
                dependency_reader=lambda path: dependency,
            )
            compiler = root / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = root / "output"
            compile_music_graph(
                graph, _Adapter(source, mml, audit=audit), output, compiler,
            )
            self.assertEqual((output / "song_7.audit.json").read_bytes(), audit)
            (output / "song_7.audit.json").write_bytes(b"changed")
            with self.assertRaisesRegex(ResourceError, "audit.json"):
                verify_music_build(graph, output, compiler)
            with self.assertRaisesRegex(ResourceError, "audit differs"):
                compile_music_graph(
                    graph, _Adapter(source, mml, audit=b"wrong"), output, compiler,
                )

    def test_music_build_graph_fails_closed_without_replacing_old_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b"bank"
            graph = MusicBuildGraph.decode(
                _raw_graph(source, mml, dependency), "fixture",
                dependency_reader=lambda path: dependency,
            )
            compiler = tmp_path / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = tmp_path / "output"
            output.mkdir()
            (output / "sentinel").write_bytes(b"old complete build")
            with self.assertRaisesRegex(RuntimeError, "compiler failed"):
                compile_music_graph(graph, _Adapter(source, mml, fail=True), output, compiler)
            self.assertEqual((output / "sentinel").read_bytes(), b"old complete build")
            self.assertFalse((output / "dependencies.json").exists())

    def test_music_build_graph_rejects_changed_inputs_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            source, mml, dependency = b"source", b"mml\n", b"bank"
            raw = _raw_graph(source, mml, dependency)
            with self.assertRaisesRegex(ResourceError, "dependency 0 is stale"):
                MusicBuildGraph.decode(raw, "fixture", dependency_reader=lambda path: b"changed")
            graph = MusicBuildGraph.decode(
                raw, "fixture", dependency_reader=lambda path: dependency,
            )
            compiler = tmp_path / "compiler"
            compiler.write_bytes(b"compiler-v1")
            output = tmp_path / "output"
            with self.assertRaisesRegex(ResourceError, "music.7.*stale"):
                compile_music_graph(graph, _Adapter(b"changed", mml), output, compiler)
            compile_music_graph(graph, _Adapter(source, mml), output, compiler)
            compiler.write_bytes(b"compiler-v2")
            with self.assertRaisesRegex(ResourceError, "compiler identity changed"):
                verify_music_build(graph, output, compiler)
            compiler.write_bytes(b"compiler-v1")
            (output / "tad.bin").write_bytes(b"tampered")
            with self.assertRaisesRegex(ResourceError, "tad.bin"):
                verify_music_build(graph, output, compiler)

    def test_music_build_graph_requires_explicit_adapter_family(self) -> None:
        raw = json.loads(_raw_graph(b"source", b"mml\n", b"bank"))
        del raw["adapter"]
        with self.assertRaisesRegex(ResourceError, "invalid adapter"):
            MusicBuildGraph.decode(json.dumps(raw).encode(), "fixture")
