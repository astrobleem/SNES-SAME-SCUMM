"""Deterministic, transactional compilation graphs for symbolic music assets."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from typing import Callable, Mapping, Protocol

from ..errors import ResourceError


_SCHEMA = "same_music_build_graph_v1"
_HASH = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _safe_path(value: object, owner: str) -> str:
    if not isinstance(value, str) or not value:
        raise ResourceError(f"{owner} must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise ResourceError(f"{owner} must be a normalized relative path")
    return value


def _hash(value: object, owner: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ResourceError(f"{owner} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True, slots=True)
class MusicBuildDependency:
    name: str
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class MusicBuildNode:
    logical_id: int
    source_resource: str
    source_sha256: str
    importer: str
    source_device: str
    bank: str
    target: str
    policy: Mapping[str, object]
    output: str
    mml_sha256: str
    compiled_song: str
    compiled_song_id: int
    duration: int
    loop: tuple[int, int] | None
    audit_output: str | None = None
    audit_sha256: str | None = None
    route: Mapping[str, object] | None = None

    @property
    def policy_sha256(self) -> str:
        return _sha(json.dumps(
            self.policy, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8"))


@dataclass(frozen=True, slots=True)
class MusicBuildGraph:
    key: str
    name: str
    profile: str
    adapter: str
    time_scale: int
    project_output: str
    catalog_template: Mapping[str, object] | None
    dependencies: tuple[MusicBuildDependency, ...]
    nodes: tuple[MusicBuildNode, ...]
    sha256: str

    @classmethod
    def decode(
        cls,
        raw: bytes,
        key: str,
        *,
        dependency_reader: Callable[[str], bytes] | None = None,
    ) -> "MusicBuildGraph":
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResourceError(f"music build graph {key!r} is invalid JSON: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema") != _SCHEMA:
            raise ResourceError(f"music build graph {key!r} has an unsupported schema")
        name, profile, adapter = data.get("name"), data.get("profile"), data.get("adapter")
        if not isinstance(name, str) or not name.strip():
            raise ResourceError(f"music build graph {key!r} has no name")
        if not isinstance(profile, str) or not profile.strip():
            raise ResourceError(f"music build graph {key!r} has no profile")
        if not isinstance(adapter, str) or not _NAME.fullmatch(adapter):
            raise ResourceError(f"music build graph {key!r} has an invalid adapter")
        time_scale = data.get("time_scale")
        if isinstance(time_scale, bool) or not isinstance(time_scale, int) or not 1 <= time_scale <= 1_000_000_000:
            raise ResourceError(f"music build graph {key!r} has an invalid time scale")
        project_output = _safe_path(data.get("project_output"), f"graph {key!r} project output")

        dependencies: list[MusicBuildDependency] = []
        dependency_names: set[str] = set()
        for index, item in enumerate(data.get("dependencies", ())):
            owner = f"graph {key!r} dependency {index}"
            if not isinstance(item, dict):
                raise ResourceError(f"{owner} must be an object")
            dep_name = item.get("name")
            if not isinstance(dep_name, str) or not _NAME.fullmatch(dep_name):
                raise ResourceError(f"{owner} has an invalid name")
            if dep_name in dependency_names:
                raise ResourceError(f"graph {key!r} repeats dependency {dep_name!r}")
            dep_path = _safe_path(item.get("path"), f"{owner} path")
            dep_hash = _hash(item.get("sha256"), f"{owner} SHA-256")
            if dependency_reader is not None:
                observed = _sha(dependency_reader(dep_path))
                if observed != dep_hash:
                    raise ResourceError(
                        f"{owner} is stale: expected {dep_hash}, observed {observed}"
                    )
            dependency_names.add(dep_name)
            dependencies.append(MusicBuildDependency(dep_name, dep_path, dep_hash))

        catalog_template = None
        catalog_dependency = data.get("catalog_template")
        if catalog_dependency is not None:
            if not isinstance(catalog_dependency, str) or catalog_dependency not in dependency_names:
                raise ResourceError(
                    f"music build graph {key!r} names an unknown catalog template dependency"
                )
            if dependency_reader is None:
                raise ResourceError(
                    f"music build graph {key!r} requires a catalog template reader"
                )
            dep = next(item for item in dependencies if item.name == catalog_dependency)
            try:
                decoded_catalog = json.loads(dependency_reader(dep.path).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ResourceError(f"music build graph {key!r} catalog template is invalid") from exc
            if (
                not isinstance(decoded_catalog, dict)
                or decoded_catalog.get("schema") != "same_compiled_music_catalog_v1"
                or not isinstance(decoded_catalog.get("entries"), list)
            ):
                raise ResourceError(f"music build graph {key!r} catalog template is unsupported")
            catalog_template = decoded_catalog

        raw_nodes = data.get("renditions")
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise ResourceError(f"music build graph {key!r} has no renditions")
        nodes: list[MusicBuildNode] = []
        route_keys: set[tuple[int, str, int]] = set()
        songs: set[str] = set()
        outputs: set[str] = set()
        for index, item in enumerate(raw_nodes):
            owner = f"graph {key!r} rendition {index}"
            if not isinstance(item, dict):
                raise ResourceError(f"{owner} must be an object")
            logical_id = item.get("logical_id")
            song_id = item.get("compiled_song_id")
            duration = item.get("duration")
            if isinstance(logical_id, bool) or not isinstance(logical_id, int) or not 0 <= logical_id <= 0xFFFFFFFF:
                raise ResourceError(f"{owner} has an invalid logical id")
            if isinstance(song_id, bool) or not isinstance(song_id, int) or not 1 <= song_id <= 255:
                raise ResourceError(f"{owner} has an invalid compiled song id")
            if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
                raise ResourceError(f"{owner} has an invalid duration")
            strings = {}
            for field in ("source_resource", "importer", "source_device", "bank", "target", "compiled_song"):
                value = item.get(field)
                if not isinstance(value, str) or not value:
                    raise ResourceError(f"{owner} has no {field.replace('_', ' ')}")
                strings[field] = value
            if not _NAME.fullmatch(strings["compiled_song"]):
                raise ResourceError(f"{owner} has an invalid compiled song name")
            if strings["bank"] not in dependency_names:
                raise ResourceError(f"{owner} names unknown bank dependency {strings['bank']!r}")
            policy = item.get("policy")
            if not isinstance(policy, dict) or not policy:
                raise ResourceError(f"{owner} has no target policy")
            output = _safe_path(item.get("output"), f"{owner} output")
            if not output.endswith(".mml"):
                raise ResourceError(f"{owner} output must be an MML file")
            source_hash = _hash(item.get("source_sha256"), f"{owner} source SHA-256")
            mml_hash = _hash(item.get("mml_sha256"), f"{owner} MML SHA-256")
            audit_output_value = item.get("audit_output")
            audit_hash_value = item.get("audit_sha256")
            if (audit_output_value is None) != (audit_hash_value is None):
                raise ResourceError(f"{owner} must declare both audit output and SHA-256")
            audit_output = None
            audit_hash = None
            if audit_output_value is not None:
                audit_output = _safe_path(
                    audit_output_value, f"{owner} audit output",
                )
                if not audit_output.endswith(".json") or audit_output == output:
                    raise ResourceError(f"{owner} has an invalid audit output")
                audit_hash = _hash(audit_hash_value, f"{owner} audit SHA-256")
            loop_value = item.get("loop")
            loop = None
            if loop_value is not None:
                if (
                    not isinstance(loop_value, list) or len(loop_value) != 2
                    or any(isinstance(v, bool) or not isinstance(v, int) for v in loop_value)
                    or not 0 <= loop_value[0] < loop_value[1] <= duration
                ):
                    raise ResourceError(f"{owner} has an invalid loop")
                loop = (loop_value[0], loop_value[1])
            route = item.get("route")
            route_kind, route_value = "default", 0
            if route is not None:
                if not isinstance(route, dict):
                    raise ResourceError(f"{owner} route must be an object")
                route_kind, route_value = route.get("kind"), route.get("value")
                if (not isinstance(route_kind, str) or not _NAME.fullmatch(route_kind)
                        or isinstance(route_value, bool) or not isinstance(route_value, int)
                        or not 0 <= route_value <= 0xFFFF):
                    raise ResourceError(f"{owner} has an invalid route key")
                identity = route.get("identity")
                bank_hash = route.get("instrument_bank_sha256")
                branch = route.get("branch")
                if (not isinstance(identity, str) or not _HASH.fullmatch(identity)
                        or not isinstance(bank_hash, str) or not _HASH.fullmatch(bank_hash)
                        or not isinstance(branch, list) or len(branch) != 4
                        or any(isinstance(v, bool) or not isinstance(v, int) or v < 0
                               for v in branch)):
                    raise ResourceError(f"{owner} has invalid route provenance")
            route_key = (logical_id, route_kind, route_value)
            if (
                route_key in route_keys or strings["compiled_song"] in songs
                or output in outputs or audit_output in outputs
            ):
                raise ResourceError(f"{owner} repeats a route, song, or output")
            route_keys.add(route_key); songs.add(strings["compiled_song"]); outputs.add(output)
            if audit_output is not None:
                outputs.add(audit_output)
            nodes.append(MusicBuildNode(
                logical_id, strings["source_resource"], source_hash,
                strings["importer"], strings["source_device"], strings["bank"],
                strings["target"], policy, output, mml_hash,
                strings["compiled_song"], song_id, duration, loop,
                audit_output, audit_hash, route,
            ))
        return cls(
            key, name, profile, adapter, time_scale, project_output, catalog_template,
            tuple(dependencies), tuple(nodes), _sha(raw),
        )


class MusicBuildAdapter(Protocol):
    def read_source(self, node: MusicBuildNode) -> bytes: ...
    def render(self, node: MusicBuildNode, source: bytes) -> bytes: ...
    def audit(self, node: MusicBuildNode) -> bytes: ...
    def finalize(
        self, graph: MusicBuildGraph, stage: Path,
        rendered: Mapping[str, bytes], compiler: Path,
    ) -> None: ...


def compile_music_graph(
    graph: MusicBuildGraph,
    adapter: MusicBuildAdapter,
    output: Path,
    compiler: Path,
    *,
    owner: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compile one graph into a complete directory or leave the old one untouched."""
    compiler_raw = compiler.read_bytes()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.stage-", dir=output.parent))
    rendered: dict[str, bytes] = {}
    try:
        for node in graph.nodes:
            source = adapter.read_source(node)
            observed_source = _sha(source)
            if observed_source != node.source_sha256:
                raise ResourceError(
                    f"{node.source_resource!r} is stale: expected {node.source_sha256}, "
                    f"observed {observed_source}"
                )
            mml = adapter.render(node, source)
            observed_mml = _sha(mml)
            if observed_mml != node.mml_sha256:
                raise ResourceError(
                    f"{node.compiled_song!r} output differs: expected {node.mml_sha256}, "
                    f"observed {observed_mml}"
                )
            target = stage / node.output
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(mml)
            rendered[node.compiled_song] = mml
            if node.audit_output is not None:
                produce_audit = getattr(adapter, "audit", None)
                if not callable(produce_audit):
                    raise ResourceError(
                        f"{node.compiled_song!r} requires an audit artifact"
                    )
                audit = produce_audit(node)
                observed_audit = _sha(audit)
                if observed_audit != node.audit_sha256:
                    raise ResourceError(
                        f"{node.compiled_song!r} audit differs: expected "
                        f"{node.audit_sha256}, observed {observed_audit}"
                    )
                audit_target = stage / node.audit_output
                audit_target.parent.mkdir(parents=True, exist_ok=True)
                audit_target.write_bytes(audit)

        adapter.finalize(graph, stage, rendered, compiler)
        required = (graph.project_output, "tad.asm", "tad.bin", "tad.inc")
        missing = [name for name in required if not (stage / name).is_file()]
        if missing:
            raise ResourceError(f"music build omitted required outputs: {', '.join(missing)}")
        generated_entries = [{
                "logical_id": node.logical_id,
                "source_resource": node.source_resource,
                "source_sha256": node.source_sha256,
                "compiled_song": node.compiled_song,
                "compiled_song_id": node.compiled_song_id,
                "duration": node.duration,
                "loop": list(node.loop) if node.loop is not None else None,
                **({"route": dict(node.route)} if node.route is not None else {}),
            } for node in graph.nodes]
        if graph.catalog_template is None:
            catalog = {
                "schema": "same_compiled_music_catalog_v1", "name": graph.name,
                "time_scale": graph.time_scale, "entries": generated_entries,
            }
        else:
            catalog = dict(graph.catalog_template)
            if catalog.get("time_scale") != graph.time_scale:
                raise ResourceError("music catalog template time scale differs from graph")
            template_by_id = {
                (item.get("logical_id"), item.get("route", {}).get("kind", "default"),
                 item.get("route", {}).get("value", 0)): item for item in catalog["entries"]
                if isinstance(item, dict)
            }
            for generated in generated_entries:
                route = generated.get("route", {})
                generated_key = (
                    generated["logical_id"], route.get("kind", "default"),
                    route.get("value", 0),
                )
                if template_by_id.get(generated_key) != generated:
                    raise ResourceError(
                        f"music catalog template entry {generated_key} differs from graph"
                    )
        (stage / "catalog.json").write_bytes(_json(catalog))
        manifest = {
            "schema": "same_music_build_dependencies_v1",
            "graph": {"key": graph.key, "sha256": graph.sha256},
            "owner": None if owner is None else dict(owner),
            "compiler": {"path": compiler.name, "sha256": _sha(compiler_raw)},
            "dependencies": [dep.__dict__ if hasattr(dep, "__dict__") else {
                "name": dep.name, "path": dep.path, "sha256": dep.sha256,
            } for dep in graph.dependencies],
            "renditions": [{
                "logical_id": node.logical_id, "source_resource": node.source_resource,
                "source_sha256": node.source_sha256, "importer": node.importer,
                "source_device": node.source_device, "bank": node.bank,
                "target": node.target, "policy_sha256": node.policy_sha256,
                "mml_sha256": node.mml_sha256,
                "audit_output": node.audit_output,
                "audit_sha256": node.audit_sha256,
            } for node in graph.nodes],
        }
        (stage / "dependencies.json").write_bytes(_json(manifest))
        artifacts = {
            str(path.relative_to(stage)): _sha(path.read_bytes())
            for path in sorted(stage.rglob("*")) if path.is_file()
        }
        report = {
            "schema": "same_music_build_report_v1", "graph_sha256": graph.sha256,
            "compiler_sha256": _sha(compiler_raw), "artifacts": artifacts,
        }
        (stage / "report.json").write_bytes(_json(report))

        backup = output.with_name(f".{output.name}.previous")
        if backup.exists():
            shutil.rmtree(backup)
        if output.exists():
            os.replace(output, backup)
        try:
            os.replace(stage, output)
        except BaseException:
            if backup.exists() and not output.exists():
                os.replace(backup, output)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def verify_music_build(
    graph: MusicBuildGraph,
    output: Path,
    compiler: Path,
    *,
    owner: Mapping[str, object] | None = None,
) -> None:
    """Fail closed when any graph, compiler, dependency, or emitted artifact changed."""
    try:
        manifest = json.loads((output / "dependencies.json").read_text("utf-8"))
        report = json.loads((output / "report.json").read_text("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ResourceError(f"music build at {output} is incomplete: {exc}") from exc
    if manifest.get("graph", {}).get("sha256") != graph.sha256:
        raise ResourceError("music build graph identity changed")
    expected_owner = None if owner is None else dict(owner)
    if manifest.get("owner") != expected_owner:
        raise ResourceError("music build owner identity changed")
    if manifest.get("compiler", {}).get("sha256") != _sha(compiler.read_bytes()):
        raise ResourceError("music compiler identity changed")
    for dep in graph.dependencies:
        recorded = next((item for item in manifest.get("dependencies", ()) if item.get("name") == dep.name), None)
        if recorded is None or recorded.get("sha256") != dep.sha256:
            raise ResourceError(f"music dependency {dep.name!r} changed")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ResourceError("music build has no artifact manifest")
    for name, expected in artifacts.items():
        path = output / _safe_path(name, "artifact path")
        if not path.is_file() or _sha(path.read_bytes()) != expected:
            raise ResourceError(f"music build artifact {name!r} is missing or stale")
