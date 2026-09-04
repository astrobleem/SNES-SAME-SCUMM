#!/usr/bin/env python3
"""SCUMM v5 title adapter for SAME's generic declarative music graph."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from same.engines.scumm_v5.embedded_audio import ScummV5EmbeddedSound
from same.music import (
    MusicBuildGraph, SampledNote, TadInstrument, TadPanPolicy, compile_music_graph,
    compile_tad_mml, verify_music_build,
)
from build_monkey_v5_tad import BASE_PROJECT, FATE_AUDIO, _portable_sources
from convert_fate_adlib154_to_tad_mml import render as render_fate_adlib
from convert_fate_sound_to_tad_mml import render_mml
from extract_fate_adlib_patches import load_resource as load_fate_resource
from validate_monkey_v5_music import BANK, _provider, monkey_church_pipeline


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMPILER = ROOT.parent / "terrific-audio-driver/target/release/tad-compiler"


class ScummV5MusicGraphAdapter:
    """Commercial-data boundary; the generic graph never names a title or cue."""

    def __init__(self, archive: Path, graph: MusicBuildGraph) -> None:
        self.archive = archive
        self.dependencies = {dependency.name: ROOT / dependency.path for dependency in graph.dependencies}
        self._monkey_provider = None

    def read_source(self, node) -> bytes:
        sound_id = int(node.source_resource.removeprefix("sound."))
        if node.importer in {
            "scumm_v5_rol_reviewed_v1", "scumm_v5_adlib_reviewed_v1",
            "reviewed_immutable_mml_v1",
        }:
            return load_fate_resource(self.archive, sound_id)
        if node.importer == "scumm_v5_adlib_generic_v1":
            if self._monkey_provider is None:
                self._monkey_provider, _members = _provider(self.archive)
            return self._monkey_provider.read(node.source_resource)
        raise ValueError(f"unsupported SCUMM music importer {node.importer!r}")

    def render(self, node, source: bytes) -> bytes:
        if node.importer == "reviewed_immutable_mml_v1":
            dependency = node.policy.get("reviewed_dependency")
            if not isinstance(dependency, str) or dependency not in self.dependencies:
                raise ValueError(
                    f"{node.compiled_song!r} has no reviewed MML dependency"
                )
            return self.dependencies[dependency].read_bytes()
        sound = ScummV5EmbeddedSound.decode(
            source, node.source_resource,
            rendition_order=(b"ADL ",) if "adlib" in node.importer else (b"ROL ",),
        )
        if node.importer == "scumm_v5_rol_reviewed_v1":
            return render_mml(node.logical_id, sound).encode("utf-8")
        if node.importer == "scumm_v5_adlib_reviewed_v1":
            return render_fate_adlib(sound).encode("utf-8")
        if node.importer == "scumm_v5_adlib_generic_v1":
            if self._monkey_provider is None:
                raise RuntimeError("generic AdLib source provider was not initialized")
            canonical, _patches, sequence, _bank, resolved = monkey_church_pipeline(
                self._monkey_provider,
            )
            if canonical.sha256 != sound.sha256:
                raise RuntimeError("generic AdLib adapter selected a different source")
            sampled = tuple(SampledNote(
                note.start, note.end, note.midi_note, note.volume, note.zone_name,
                note.part_id, note.note_id, note.volume_changes,
            ) for note in resolved)
            song = compile_tad_mml(
                sequence, sampled,
                (
                    TadInstrument("monkey154_organ_low", "mt32_p13_low"),
                    TadInstrument("monkey154_organ_main", "mt32_p13"),
                ),
                title=str(node.policy["title"]), author=str(node.policy["author"]),
                pan_policy=TadPanPolicy(str(node.policy["pan"])),
            )
            return song.mml.encode("utf-8")
        raise ValueError(f"unsupported SCUMM music importer {node.importer!r}")

    def audit(self, node) -> bytes:
        dependency = node.policy.get("audit_dependency")
        if not isinstance(dependency, str) or dependency not in self.dependencies:
            raise ValueError(f"{node.compiled_song!r} has no route-audit dependency")
        return self.dependencies[dependency].read_bytes()

    def finalize(self, graph, stage, rendered, compiler) -> None:
        project = json.loads(BASE_PROJECT.read_text(encoding="utf-8"))
        _portable_sources(project, stage)
        by_song = {node.compiled_song: node for node in graph.nodes}
        if graph.profile == "indy4-fate-demo":
            existing = {song["name"] for song in project["songs"]}
            for song in project["songs"]:
                node = by_song.get(song["name"])
                if node is not None:
                    song["source"] = node.output
            project["songs"].extend(
                {"name": node.compiled_song, "source": node.output}
                for node in graph.nodes if node.compiled_song not in existing
            )
            # M21's listener gate is deliberately outside the playable catalog:
            # six isolated programs are appended after the two route songs, so
            # they cannot be selected by a SCUMM logical sound request.
            for program in (32, 33, 50, 57, 77, 82):
                dependency = f"fate-m21-program-{program}"
                source = self.dependencies.get(dependency)
                if source is None:
                    continue
                target = f"program_{program}_used_range.mml"
                (stage / target).write_bytes(source.read_bytes())
                project["songs"].append({
                    "name": f"m21_program_{program}_used_range",
                    "source": target,
                })
            # M22 adds only the newly reached ranges to the listener gate.
            for program in (50, 97, 107):
                dependency = f"fate-m22-program-{program}"
                source = self.dependencies.get(dependency)
                if source is None:
                    continue
                target = f"m22_program_{program}_used_range.mml"
                (stage / target).write_bytes(source.read_bytes())
                project["songs"].append({
                    "name": f"m22_program_{program}_used_range", "source": target,
                })
            project["_about"]["_comment"] = (
                "Generated by SAME's declarative music build graph."
            )
        elif graph.profile == "monkey1-ultimate-talkie":
            bank = json.loads(BANK.read_text(encoding="utf-8"))
            zones = {zone["name"]: zone for zone in bank["zones"]}
            project["instruments"].extend((
                {
                    "name": "mt32_p13_low",
                    "source": os.path.relpath((ROOT / zones["monkey154_organ_low"]["sample_resource"]).resolve(), stage),
                    "freq": 131.148, "loop": "loop_with_filter", "loop_setting": 4160,
                    "evaluator": "default", "ignore_gaussian_overflow": False,
                    "first_octave": 2, "last_octave": 3, "envelope": "adsr 15 1 7 0",
                },
                {
                    "name": "mt32_p13",
                    "source": os.path.relpath((ROOT / zones["monkey154_organ_main"]["sample_resource"]).resolve(), stage),
                    "freq": 592.593, "loop": "loop_with_filter", "loop_setting": 5120,
                    "evaluator": "default", "ignore_gaussian_overflow": False,
                    "first_octave": 3, "last_octave": 6, "envelope": "adsr 15 1 7 0",
                },
            ))
            project["songs"].extend(
                {"name": node.compiled_song, "source": node.output}
                for node in graph.nodes
            )
            project["_about"]["_comment"] = (
                "Generated by SAME's declarative music build graph; derived MML stays under build/."
            )
        else:
            raise ValueError(f"unsupported SCUMM music graph profile {graph.profile!r}")
        project_path = stage / graph.project_output
        project_path.write_text(
            json.dumps(project, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        subprocess.run((
            str(compiler), "asar-export", "--lorom",
            "--output-asm", str(stage / "tad.asm"),
            "--output-bin", str(stage / "tad.bin"),
            "--output-inc", str(stage / "tad.inc"), str(project_path),
        ), check=True)
        section_nodes = [
            node for node in graph.nodes if node.policy.get("m22_section_postlink") is True
        ]
        if section_nodes:
            if len(section_nodes) != 1:
                raise RuntimeError("M22 build must contain exactly one section-postlinked cue")
            linked = stage / "tad.m22.bin"
            subprocess.run((
                "python3", str(ROOT / "tools/postlink_m22_tad_sections.py"),
                "--input", str(stage / "tad.bin"), "--output", str(linked),
                "--report", str(stage / "m22_section_postlink.json"),
            ), check=True)
            linked.replace(stage / "tad.bin")
        enums = (stage / "tad.inc").read_text(encoding="utf-8")
        for node in graph.nodes:
            match = re.search(
                rf"^\s*!Song_{re.escape(node.compiled_song)}\s*=\s*(\d+)\s*$",
                enums, re.MULTILINE,
            )
            if match is None or int(match.group(1)) != node.compiled_song_id:
                raise RuntimeError(
                    f"compiled enum for {node.compiled_song!r} differs from graph id "
                    f"{node.compiled_song_id}"
                )


def _graph(path: Path) -> MusicBuildGraph:
    return MusicBuildGraph.decode(
        path.read_bytes(), str(path), dependency_reader=lambda name: (ROOT / name).read_bytes(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compiler", type=Path, default=DEFAULT_COMPILER)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    graph = _graph(args.graph.resolve())
    compiler = args.compiler.resolve()
    if args.verify:
        verify_music_build(graph, args.output.resolve(), compiler)
        print(f"verified graph={graph.sha256} output={args.output.resolve()}")
        return 0
    report = compile_music_graph(
        graph, ScummV5MusicGraphAdapter(args.archive.resolve(), graph),
        args.output.resolve(), compiler,
    )
    print(
        f"graph={graph.sha256} renditions={len(graph.nodes)} "
        f"compiler={report['compiler_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
