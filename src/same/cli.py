"""Command-line interface for the SAME host SDK."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json
import sys
import wave

from .abi import generate_poppy_include
from .audio import (
    DEFAULT_SAMPLE_RATE,
    demo_trace,
    read_trace,
    render_sn76489,
    write_trace,
    write_wav,
)
from .donors import DONORS, identify, import_reference
from .engine import EngineHost
from .engines import default_registry
from .errors import SameError
from .input import SnesButton
from .package import build_package, extract_package, inspect_package
from .oracle import compare_records, read_records, record_from_files, write_records
from .profile import load_profile
from .runtime import SameRuntime
from .target import load_target


def _json(data: object, output: Path | None = None) -> None:
    text = json.dumps(data, indent=2, sort_keys=False) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)


def _input_words(path: Path | None, frames: int) -> list[int]:
    if path is None:
        return [0] * frames
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SameError(f"cannot read input script {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise SameError("input script must be a JSON list")
    words: list[int] = []
    name_map = {button.name.lower(): int(button) for button in SnesButton if button}
    current = 0
    for index, item in enumerate(raw):
        if isinstance(item, int):
            current = item & 0xFFFF
        elif isinstance(item, list):
            current = 0
            for name in item:
                try:
                    current |= name_map[str(name).lower()]
                except KeyError as exc:
                    raise SameError(f"input script item {index}: unknown SNES button {name!r}") from exc
        elif isinstance(item, dict):
            duration = int(item.get("frames", 1))
            if duration <= 0:
                raise SameError(f"input script item {index}: frames must be positive")
            current = 0
            for name in item.get("buttons", []):
                try:
                    current |= name_map[str(name).lower()]
                except KeyError as exc:
                    raise SameError(f"input script item {index}: unknown SNES button {name!r}") from exc
            words.extend([current] * duration)
            continue
        else:
            raise SameError(f"input script item {index} has unsupported type")
        words.append(current)
    if len(words) < frames:
        words.extend([0] * (frames - len(words)))
    return words[:frames]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="same", description="SAME — SA-1 Machine Environment host SDK"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    abi = sub.add_parser("abi", help="generate or inspect the service ABI")
    abi_sub = abi.add_subparsers(dest="abi_command", required=True)
    abi_generate = abi_sub.add_parser("generate")
    abi_generate.add_argument("output", type=Path)

    engine = sub.add_parser("engine", help="inspect and run reusable SAME engines")
    engine_sub = engine.add_subparsers(dest="engine_command", required=True)
    engine_sub.add_parser("list", help="list registered engine modules")
    engine_validate = engine_sub.add_parser("validate", help="validate an engine profile")
    engine_validate.add_argument("profile", type=Path)
    engine_run = engine_sub.add_parser("run", help="run an engine profile in the host oracle")
    engine_run.add_argument("profile", type=Path)
    engine_run.add_argument("--frames", type=int, default=120)
    engine_run.add_argument("--input-script", type=Path)
    engine_run.add_argument("--output", type=Path)
    engine_run.add_argument("--framebuffer", type=Path)
    engine_run.add_argument("--save-file", type=Path)
    engine_run.add_argument("--load-file", type=Path)

    target = sub.add_parser("target", help="validate target manifests")
    target_sub = target.add_subparsers(dest="target_command", required=True)
    target_validate = target_sub.add_parser("validate")
    target_validate.add_argument("manifest", type=Path)

    package = sub.add_parser("package", help="build and inspect SAME packages")
    package_sub = package.add_subparsers(dest="package_command", required=True)
    package_build = package_sub.add_parser("build")
    package_build.add_argument("manifest", type=Path)
    package_build.add_argument("output", type=Path)
    package_build.add_argument("--poppy-include", type=Path)
    package_inspect = package_sub.add_parser("inspect")
    package_inspect.add_argument("package", type=Path)
    package_extract = package_sub.add_parser("extract")
    package_extract.add_argument("package", type=Path)
    package_extract.add_argument("output", type=Path)

    simulate = sub.add_parser("simulate", help="run the deterministic host frame model")
    simulate.add_argument("target", type=Path)
    simulate.add_argument("--frames", type=int, default=120)
    simulate.add_argument("--input-script", type=Path)
    simulate.add_argument("--output", type=Path)

    audio = sub.add_parser("audio", help="run CPU-independent audio labs")
    audio_sub = audio.add_subparsers(dest="audio_command", required=True)
    audio_demo = audio_sub.add_parser("demo", help="create the bundled PSG demo")
    audio_demo.add_argument("--trace", type=Path, required=True)
    audio_demo.add_argument("--wav", type=Path, required=True)
    audio_demo.add_argument("--duration", type=float, default=1.25)
    audio_demo.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    audio_render = audio_sub.add_parser("render-sn76489")
    audio_render.add_argument("trace", type=Path)
    audio_render.add_argument("wav", type=Path)
    audio_render.add_argument("--duration", type=float, required=True)
    audio_render.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)

    oracle = sub.add_parser("oracle", help="create and compare fail-closed validation records")
    oracle_sub = oracle.add_subparsers(dest="oracle_command", required=True)
    oracle_record = oracle_sub.add_parser("record")
    oracle_record.add_argument("output", type=Path)
    oracle_record.add_argument("--tick", type=int, required=True)
    oracle_record.add_argument("--identity")
    oracle_record.add_argument("--state", type=Path)
    oracle_record.add_argument("--video", type=Path)
    oracle_record.add_argument("--audio", type=Path)
    oracle_record.add_argument("--events", type=Path)
    oracle_compare = oracle_sub.add_parser("compare")
    oracle_compare.add_argument("expected", type=Path)
    oracle_compare.add_argument("actual", type=Path)
    oracle_compare.add_argument("--output", type=Path)

    donors = sub.add_parser("donors", help="identify or import local donor repositories")
    donor_sub = donors.add_subparsers(dest="donor_command", required=True)
    donor_check = donor_sub.add_parser("check")
    donor_check.add_argument("name", choices=sorted(DONORS))
    donor_check.add_argument("--path", type=Path)
    donor_import = donor_sub.add_parser("import")
    donor_import.add_argument("name", choices=sorted(DONORS))
    donor_import.add_argument("--path", type=Path)
    donor_import.add_argument("--output", type=Path, default=Path("vendor/reference"))

    doctor = sub.add_parser("doctor", help="check the expected Chad workstation layout")
    doctor.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "abi":
            generate_poppy_include(args.output)
            print(args.output)
            return 0
        if args.command == "engine":
            registry = default_registry()
            if args.engine_command == "list":
                _json({"engines": registry.to_dict()})
                return 0
            profile = load_profile(args.profile, verify_resources=True)
            host = EngineHost(profile, registry)
            probe = host.probe()
            if args.engine_command == "validate":
                _json(
                    {
                        "profile": profile.to_dict(),
                        "engine": host.engine.descriptor.to_dict(),
                        "probe": probe.to_dict(),
                        "negotiated_capabilities": [
                            capability.name.lower()
                            for capability in type(host.negotiated_capabilities)
                            if capability and (host.negotiated_capabilities & capability) == capability
                        ],
                    }
                )
                return 0
            if args.frames <= 0:
                raise SameError("--frames must be positive")
            host.boot()
            if args.load_file is not None:
                try:
                    raw_save = args.load_file.read_bytes()
                except OSError as exc:
                    raise SameError(f"cannot read save file {args.load_file}: {exc}") from exc
                host.services.saves.write(0, raw_save)
                host.load(0)
            words = _input_words(args.input_script, args.frames)
            for frame in range(args.frames):
                host.tick(input_word=words[frame])
            if args.save_file is not None:
                envelope = host.save(0)
                args.save_file.parent.mkdir(parents=True, exist_ok=True)
                args.save_file.write_bytes(envelope.pack())
            if args.framebuffer is not None:
                host.services.video.write_png(args.framebuffer)
            host.shutdown()
            _json(host.report(), args.output)
            return 0
        if args.command == "target":
            _json(load_target(args.manifest).to_dict())
            return 0
        if args.command == "package":
            if args.package_command == "build":
                info = build_package(args.manifest, args.output, args.poppy_include)
            elif args.package_command == "inspect":
                info = inspect_package(args.package, verify=True)
            else:
                info = extract_package(args.package, args.output)
            _json(info.to_dict())
            return 0
        if args.command == "simulate":
            runtime = SameRuntime.from_path(args.target)
            words = _input_words(args.input_script, args.frames)
            _json(runtime.simulate(args.frames, words), args.output)
            return 0
        if args.command == "audio":
            if args.audio_command == "demo":
                writes = demo_trace()
                write_trace(args.trace, writes)
            else:
                writes = read_trace(args.trace)
            pcm = render_sn76489(
                writes, duration=args.duration, sample_rate=args.sample_rate
            )
            write_wav(args.wav, pcm, args.sample_rate)
            with wave.open(str(args.wav), "rb") as wav:
                summary = {
                    "trace": str(args.trace),
                    "wav": str(args.wav),
                    "writes": len(writes),
                    "sample_rate": wav.getframerate(),
                    "frames": wav.getnframes(),
                    "seconds": wav.getnframes() / wav.getframerate(),
                }
            _json(summary)
            return 0
        if args.command == "oracle":
            if args.oracle_command == "record":
                record = record_from_files(
                    tick=args.tick,
                    identity=args.identity,
                    state=args.state,
                    video=args.video,
                    audio=args.audio,
                    events=args.events,
                )
                write_records(args.output, [record])
                _json(record.to_dict())
                return 0
            comparison = compare_records(
                read_records(args.expected), read_records(args.actual)
            )
            _json(comparison.to_dict(), args.output)
            return 0 if comparison.status == "PASS" else 1
        if args.command == "donors":
            spec = DONORS[args.name]
            path = args.path or spec.default_path()
            result = (
                identify(spec, path)
                if args.donor_command == "check"
                else import_reference(spec, path, args.output)
            )
            _json(result)
            return 0
        if args.command == "doctor":
            results = []
            ok = True
            for name, spec in DONORS.items():
                path = spec.default_path()
                try:
                    result = identify(spec, path)
                    result["ok"] = True
                except SameError as exc:
                    result = {
                        "name": name,
                        "path": str(path),
                        "ok": False,
                        "error": str(exc),
                    }
                    ok = False
                results.append(result)
            data = {"ok": ok, "donors": results}
            if args.json:
                _json(data)
            else:
                for result in results:
                    marker = "OK" if result["ok"] else "FAIL"
                    detail = result.get("head", result.get("error", ""))
                    print(f"{marker:4} {result['name']:<11} {result['path']} {detail}")
            return 0 if ok else 1
        parser.error("unhandled command")
    except SameError as exc:
        parser.exit(2, f"same: error: {exc}\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
