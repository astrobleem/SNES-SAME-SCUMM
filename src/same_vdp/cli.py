from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from .compare import compare_images, parse_crop
from .render import render_plane_a
from .testsynth import CASES, write_case
from .trace import TraceError, read_trace
from .translate import read_bundle, render_bundle, translate_plane_a, write_bundle
from .vdp import VDPState


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_state(path: Path) -> tuple[object, VDPState]:
    trace = read_trace(path)
    return trace, VDPState.from_trace(trace)


def command_generate(args: argparse.Namespace) -> int:
    names = list(CASES) if args.case == "all" else [args.case]
    destination = Path(args.output)
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = write_case(name, destination / f"{name}.vdptrace.jsonl")
        print(path)
    return 0


def command_render(args: argparse.Namespace) -> int:
    trace, state = load_state(Path(args.trace))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = render_plane_a(state, output=args.palette)
    image.save(output)
    print(output)
    return 0


def command_compile(args: argparse.Namespace) -> int:
    trace, state = load_state(Path(args.trace))
    bundle = translate_plane_a(state, case_name=trace.name)  # type: ignore[attr-defined]
    output = write_bundle(bundle, args.output)
    print(output)
    return 0



def command_render_bundle(args: argparse.Namespace) -> int:
    bundle = read_bundle(args.bundle)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    render_bundle(bundle).save(output)
    print(output)
    return 0


def command_select(args: argparse.Namespace) -> int:
    source = Path(args.bundle)
    destination = Path(args.output)
    required = ("tiles.4bpp", "tilemap.bin", "palette.cgram", "manifest.json", "assets.inc.pasm")
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        raise FileNotFoundError(f"bundle is missing: {', '.join(missing)}")
    destination.mkdir(parents=True, exist_ok=True)
    for name in required:
        shutil.copy2(source / name, destination / name)
    print(destination)
    return 0


def command_compare(args: argparse.Namespace) -> int:
    result = compare_images(
        args.expected,
        args.actual,
        crop=parse_crop(args.crop),
        diff_path=args.diff,
        result_path=args.result,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.exact else 1


def command_build_all(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    cases = root / "cases"
    expected = root / "expected"
    generated = root / "generated"
    cases.mkdir(parents=True, exist_ok=True)
    expected.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    index: dict[str, object] = {"format": "same-vdp-golden-index", "version": 1, "cases": {}}
    for name in CASES:
        trace_path = write_case(name, cases / f"{name}.vdptrace.jsonl")
        trace = read_trace(trace_path)
        state = VDPState.from_trace(trace)
        genesis_path = expected / f"{name}.genesis.png"
        snes_path = expected / f"{name}.snes.png"
        render_plane_a(state, "genesis").save(genesis_path)
        render_plane_a(state, "snes").save(snes_path)
        bundle_path = write_bundle(translate_plane_a(state, case_name=name), generated / name)
        index["cases"][name] = {  # type: ignore[index]
            "trace": {"path": str(trace_path.relative_to(root)), "sha256": sha256_file(trace_path)},
            "genesis_png": {"path": str(genesis_path.relative_to(root)), "sha256": sha256_file(genesis_path)},
            "snes_png": {"path": str(snes_path.relative_to(root)), "sha256": sha256_file(snes_path)},
            "bundle": str(bundle_path.relative_to(root)),
        }
        print(name)
    (root / "golden.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def command_verify(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    golden_path = root / "golden.json"
    expected_index = json.loads(golden_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for name, record in expected_index["cases"].items():
        for key in ("trace", "genesis_png", "snes_png"):
            item = record[key]
            path = root / item["path"]
            actual = sha256_file(path)
            if actual != item["sha256"]:
                failures.append(f"{name} {key}: expected {item['sha256']}, got {actual}")
        bundle_root = root / record["bundle"]
        manifest = json.loads((bundle_root / "manifest.json").read_text(encoding="utf-8"))
        for asset_name, asset in manifest["assets"].items():
            asset_path = bundle_root / asset_name
            actual = sha256_file(asset_path)
            if actual != asset["sha256"]:
                failures.append(f"{name} {asset_name}: expected {asset['sha256']}, got {actual}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"verified {len(expected_index['cases'])} golden cases")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="same-vdp", description="CPU-independent Genesis VDP to SNES PPU laboratory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="generate synthetic VDP traces")
    generate.add_argument("case", choices=["all", *CASES.keys()])
    generate.add_argument("--output", default="cases")
    generate.set_defaults(func=command_generate)

    render = subparsers.add_parser("render", help="render a VDP trace")
    render.add_argument("trace")
    render.add_argument("--palette", choices=("genesis", "snes"), default="genesis")
    render.add_argument("--output", required=True)
    render.set_defaults(func=command_render)

    compile_snes = subparsers.add_parser("compile-snes", help="translate Plane A into SNES-native assets")
    compile_snes.add_argument("trace")
    compile_snes.add_argument("--output", required=True)
    compile_snes.set_defaults(func=command_compile)

    render_snes = subparsers.add_parser("render-snes-bundle", help="render the emitted SNES tiles/map/CGRAM")
    render_snes.add_argument("bundle")
    render_snes.add_argument("--output", required=True)
    render_snes.set_defaults(func=command_render_bundle)

    select = subparsers.add_parser("select-snes", help="select one generated bundle for the Poppy ROM")
    select.add_argument("bundle")
    select.add_argument("--output", default="snes/generated")
    select.set_defaults(func=command_select)

    compare = subparsers.add_parser("compare", help="compare an expected frame with an emulator capture")
    compare.add_argument("expected")
    compare.add_argument("actual")
    compare.add_argument("--crop", help="crop actual as x,y,width,height")
    compare.add_argument("--diff")
    compare.add_argument("--result")
    compare.set_defaults(func=command_compare)

    build_all = subparsers.add_parser("build-all", help="regenerate all traces, goldens and SNES bundles")
    build_all.add_argument("--root", default=".")
    build_all.set_defaults(func=command_build_all)

    verify = subparsers.add_parser("verify", help="verify checked-in golden hashes")
    verify.add_argument("--root", default=".")
    verify.set_defaults(func=command_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (TraceError, ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
