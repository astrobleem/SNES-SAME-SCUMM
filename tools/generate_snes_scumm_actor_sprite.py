#!/usr/bin/env python3
"""Cook source-backed SCUMM v5 costume poses into a checked SAMEPKG section.

The host costume decoder remains the format oracle. Pose pixels are package
payload, not ROM data. A small ROM directory records keys, relative offsets,
and per-pose CRCs; the native actor service fetches one pose through SAME's
checked MSU provider before the indexed-surface compositor can use it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import zlib

from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.package import build_package, inspect_package
from same.resources import MemoryResourceProvider
if __package__:
    from .actor_pose_plan import compile_pose as compile_actor_pose
else:  # build_snes.sh executes this tool by filename with tools/ on sys.path
    from actor_pose_plan import compile_pose as compile_actor_pose


def source_bytes(archive: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        pairs = (
            ("ATLANTIS/ATLANTIS.000", "ATLANTIS/ATLANTIS.001"),
            ("FATEDEMO/PLAYFATE.000", "FATEDEMO/PLAYFATE.001"),
        )
        for index_name, data_name in pairs:
            if index_name in names and data_name in names:
                return {"game.index": bundle.read(index_name),
                        "game.data": bundle.read(data_name)}
    raise RuntimeError(f"{archive}: no supported SCUMM v5 index/data pair")


def cook_pose(
    costume: ScummV5Costume,
    frame: int,
    *,
    width: int,
    height: int,
    facing: int = 180,
    step: int = 0,
) -> bytes:
    """Legacy fixed-sheet cooker used only by the isolated fixture profile."""
    pose = costume.decode_pose(frame, facing=facing, step=step)
    pixels = bytearray(width * height)
    for cel in pose.cels:
        # Costume BYLE data is traversed in source column-major order.  Keep
        # the same directional placement contract as ScummV5RoomRenderer:
        # facing-dependent poses may paint from right to left around the
        # actor anchor.  The old cooker flattened the cel row-major and
        # therefore emitted a transposed/striped actor while its self-check
        # still compared two copies of the same wrong composition.
        origin_x = width // 2 + cel.relative_x if pose.draw_to_right else width // 2 - cel.relative_x
        origin_y = height - 9 + cel.relative_y
        x_step = 1 if pose.draw_to_right else -1
        for y in range(cel.height):
            target_y = origin_y + y
            if not 0 <= target_y < height:
                continue
            for x in range(cel.width):
                target_x = origin_x + x_step * x
                if not 0 <= target_x < width:
                    continue
                value = cel.pixels[x * cel.height + y]
                if value:
                    pixels[target_y * width + target_x] = costume.palette[value]
    return bytes(pixels)


def rows(data: bytes, width: int) -> str:
    return "\n".join(
        "    .byte " + ",".join(f"${value:02X}" for value in data[offset:offset + width])
        for offset in range(0, len(data), width)
    )


_DIRECTION_FACING = {0: 270, 1: 90, 2: 180, 3: 0}
POSE_WIDTH = 32
POSE_HEIGHT = 64
POSE_BYTES = POSE_WIDTH * POSE_HEIGHT
POSE_RECORD_SIZE = 24
CHUNK_RECORD_SIZE = 16
SPAN_RECORD_SIZE = 8
PALETTE_RECORD_SIZE = 34
MAX_CHUNK_BYTES = 2048
SPANS_PER_BANK = 4096
MAX_ANIMATION_STEPS = 256


def compile_pose_set(
    costumes: dict[int, tuple[str, bytes]],
) -> tuple[bytes, list[dict[str, object]]]:
    """Return deterministic source-slot chunks and signed span metadata."""
    if not costumes:
        raise ValueError("at least one source costume is required")
    payload = bytearray()
    records: list[dict[str, object]] = []
    palette_indices = {
        costume_id: index for index, costume_id in enumerate(sorted(costumes))
    }
    for costume_id, (key, raw) in sorted(costumes.items()):
        if not 0 <= costume_id <= 0xFF:
            raise ValueError(f"costume id {costume_id} does not fit u8")
        costume = ScummV5Costume(raw, key=key)
        # animation_count is the largest valid frame*4+direction index.
        frame_count = costume.animation_count // 4 + 1
        for frame in range(frame_count):
            for direction, facing in sorted(_DIRECTION_FACING.items()):
                seen: dict[tuple[tuple[int, int], ...], int] = {}
                animation_steps: list[int] = []
                loop_start = loop_length = 0
                for step in range(MAX_ANIMATION_STEPS):
                    commands = costume.decode_pose(
                        frame, facing=facing, step=step,
                    ).commands
                    if commands in seen:
                        loop_start = seen[commands]
                        loop_length = step - loop_start
                        break
                    seen[commands] = step
                    animation_steps.append(step)
                if loop_length < 1:
                    raise ValueError(
                        f"costume {costume_id} frame {frame} direction {direction} "
                        f"did not reach a repeating command state in {MAX_ANIMATION_STEPS} steps"
                    )
                for step in animation_steps:
                    plan = compile_actor_pose(
                        costume.decode_pose(frame, facing=facing, step=step),
                        costume.palette,
                    )
                    if len(plan.palette) > 32:
                        raise ValueError("native actor palette directory supports at most 32 slots")
                    pose_chunks: list[dict[str, object]] = []
                    for chunk in plan.chunks(MAX_CHUNK_BYTES):
                        offset = len(payload)
                        payload.extend(chunk.data)
                        pose_chunks.append({
                            "relative_offset": offset,
                            "length": len(chunk.data),
                            "crc32": f"{chunk.crc32:08x}",
                            "sha256": chunk.sha256,
                            "spans": [
                                {"x": ref.x, "y": ref.y,
                                 "offset": ref.offset, "length": ref.length}
                                for ref in chunk.spans
                            ],
                        })
                    if len(pose_chunks) > 0xFF:
                        raise ValueError("one pose exceeds the native chunk-count field")
                    first = pose_chunks[0] if pose_chunks else {
                        "relative_offset": len(payload), "length": 0,
                        "crc32": "00000000",
                        "sha256": hashlib.sha256(b"").hexdigest(),
                    }
                    records.append({
                        "costume": costume_id,
                        "frame": frame,
                        "direction": direction,
                        "step": step,
                        "facing_degrees": facing,
                        "palette_index": palette_indices[costume_id],
                        "palette_size": len(plan.palette),
                        "palette_values": list(plan.palette),
                        "bounds": list(plan.bounds),
                        "opaque_pixels": plan.opaque_pixels,
                        "relative_offset": first["relative_offset"],
                        "length": first["length"],
                        "crc32": first["crc32"],
                        "sha256": first["sha256"],
                        "chunks": pose_chunks,
                        "loop_start": loop_start,
                        "loop_length": loop_length,
                        "source_resource": key,
                        "source_sha256": hashlib.sha256(raw).hexdigest(),
                    })
    return bytes(payload), records


def pose_directory_include(
    records: list[dict[str, object]], *, bank: int, span_first_bank: int = 25,
) -> str:
    if not 0 <= bank <= 0x7F:
        raise ValueError("pose directory bank must be in mapped LoROM range 0..127")
    if not 0 <= span_first_bank <= 0x7F:
        raise ValueError("span directory bank must be in mapped LoROM range 0..127")
    if len(records) * POSE_RECORD_SIZE > 0x8000:
        raise ValueError("pose directory exceeds its single 32 KiB ROM bank")
    chunk_rows: list[dict[str, int]] = []
    span_pages: list[bytearray] = [bytearray()]
    pose_rows: list[bytes] = []
    palettes: dict[int, tuple[int, ...]] = {}
    for row in records:
        palette_index = int(row["palette_index"])
        palette = tuple(int(value) for value in row["palette_values"])
        if len(palette) > 32 or any(not 0 <= value <= 0xFF for value in palette):
            raise ValueError("pose palette is outside the native 32-slot representation")
        prior = palettes.setdefault(palette_index, palette)
        if prior != palette:
            raise ValueError("one palette directory index identifies different palettes")
        chunks = list(row.get("chunks", []))
        first_chunk = len(chunk_rows)
        if first_chunk > 0xFFFF or len(chunks) > 0xFFFF:
            raise ValueError("actor chunk directory exceeds its u16 index")
        pose_raw = bytes((int(row["costume"]), int(row["frame"]),
                          int(row["direction"]), int(row["step"]),
                          palette_index, int(row["loop_start"]),
                          int(row["loop_length"])))
        pose_raw += first_chunk.to_bytes(2, "little")
        pose_raw += len(chunks).to_bytes(2, "little")
        bounds = tuple(int(value) for value in row["bounds"])
        if len(bounds) != 4 or any(not -32768 <= value <= 32767 for value in bounds):
            raise ValueError("actor pose bounds exceed signed 16-bit directory fields")
        pose_raw += b"".join(value.to_bytes(2, "little", signed=True)
                              for value in bounds)
        pose_raw += bytes(5)
        if len(pose_raw) != POSE_RECORD_SIZE:
            raise AssertionError("pose directory record width changed")
        pose_rows.append(pose_raw)
        for chunk in chunks:
            spans = list(chunk["spans"])
            if len(spans) > SPANS_PER_BANK:
                raise ValueError("one checked actor chunk exceeds a span-directory bank")
            if len(span_pages[-1]) // SPAN_RECORD_SIZE + len(spans) > SPANS_PER_BANK:
                span_pages.append(bytearray())
            page = len(span_pages) - 1
            local_first = len(span_pages[-1]) // SPAN_RECORD_SIZE
            global_first = page * SPANS_PER_BANK + local_first
            if global_first > 0xFFFF or len(spans) > 0xFFFF:
                raise ValueError("actor span directory exceeds its u16 index")
            for span in spans:
                x, y = int(span["x"]), int(span["y"])
                offset, length = int(span["offset"]), int(span["length"])
                if (not -32768 <= x <= 32767 or not -32768 <= y <= 32767
                        or not 0 <= offset <= 0xFFFF or not 1 <= length <= 0xFFFF
                        or offset + length > int(chunk["length"])):
                    raise ValueError("invalid signed actor span descriptor")
                span_pages[-1].extend(
                    x.to_bytes(2, "little", signed=True)
                    + y.to_bytes(2, "little", signed=True)
                    + offset.to_bytes(2, "little")
                    + length.to_bytes(2, "little")
                )
            chunk_rows.append({
                "offset": int(chunk["relative_offset"]),
                "crc": int(str(chunk["crc32"]), 16),
                "length": int(chunk["length"]),
                "span_first": global_first,
                "span_count": len(spans),
            })
    if span_first_bank + len(span_pages) - 1 > 0x7F:
        raise ValueError("actor span directories exceed mapped LoROM banks")
    if bank in range(span_first_bank, span_first_bank + len(span_pages)):
        raise ValueError("actor span pages overlap the pose/chunk/palette directory bank")
    if (len(records) * POSE_RECORD_SIZE + len(chunk_rows) * CHUNK_RECORD_SIZE
            + len(palettes) * PALETTE_RECORD_SIZE > 0x8000):
        raise ValueError("actor chunk/palette directories exceed their ROM bank")
    lines = [
        "; Generated lossless source-backed pose/chunk/palette directories.",
        "; Pixel slots remain in checked SC5ACT payloads in SAMEPKG.",
        f"SCUMM_V5_ACTOR_POSE_COUNT = ${len(records):04X}",
        f"SCUMM_V5_ACTOR_POSE_RECORD_SIZE = ${POSE_RECORD_SIZE:04X}",
        f"SCUMM_V5_ACTOR_CHUNK_RECORD_SIZE = ${CHUNK_RECORD_SIZE:04X}",
        f"SCUMM_V5_ACTOR_SPAN_RECORD_SIZE = ${SPAN_RECORD_SIZE:04X}",
        f"SCUMM_V5_ACTOR_SPAN_FIRST_BANK = ${span_first_bank:02X}",
        f"SCUMM_V5_ACTOR_PALETTE_RECORD_SIZE = ${PALETTE_RECORD_SIZE:04X}",
        f"SCUMM_V5_ACTOR_CHUNK_COUNT = ${len(chunk_rows):04X}",
        f"SCUMM_V5_ACTOR_PALETTE_COUNT = ${len(palettes):04X}",
        f"SCUMM_V5_ACTOR_SPANS_PER_BANK = ${SPANS_PER_BANK:04X}",
        f"SCUMM_V5_ACTOR_SPAN_BANK_COUNT = ${len(span_pages):04X}",
        f".bank {bank}", ".org $8000", "ScummV5_ActorPoseDirectory:",
    ]
    for raw in pose_rows:
        lines.extend(rows(raw, POSE_RECORD_SIZE).splitlines())
    if not records:
        lines.append("    .byte $00")
    lines.append("ScummV5_ActorPoseChunkDirectory:")
    for chunk in chunk_rows:
        raw = (chunk["offset"].to_bytes(4, "little")
               + chunk["crc"].to_bytes(4, "little")
               + chunk["length"].to_bytes(2, "little")
               + chunk["span_first"].to_bytes(2, "little")
               + chunk["span_count"].to_bytes(2, "little") + bytes(2))
        lines.extend(rows(raw, CHUNK_RECORD_SIZE).splitlines())
    lines.append("ScummV5_ActorPaletteDirectory:")
    for _palette_index, palette in sorted(palettes.items()):
        raw = len(palette).to_bytes(2, "little") + bytes(palette).ljust(32, b"\x00")
        lines.extend(rows(raw, PALETTE_RECORD_SIZE).splitlines())
    for page, payload in enumerate(span_pages):
        lines.extend((f".bank {span_first_bank + page}", ".org $8000",
                      f"ScummV5_ActorPoseSpanDirectory{page}:"))
        lines.extend(rows(bytes(payload), 16).splitlines())
        if not payload:
            lines.append("    .byte $00")
    return "\n".join(lines) + "\n"


def write_pose_package(
    output_dir: Path,
    costumes: dict[int, tuple[str, bytes]],
    *,
    directory_include: Path,
    directory_bank: int = 13,
    span_first_bank: int = 25,
    prefix_package: Path | None = None,
    prefix_sections: tuple[str, ...] | None = None,
) -> dict[str, object]:
    payload, records = compile_pose_set(costumes)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_path = output_dir / "sc5act-payload.bin"
    payload_path.write_bytes(payload)
    package_manifest = output_dir / "sc5act-package.json"
    sections: list[dict[str, object]] = []
    prefix_descriptors = []
    if prefix_package is not None:
        prefix_info = inspect_package(prefix_package, verify=True)
        prefix_raw = prefix_package.read_bytes()
        names = (tuple(section.name for section in prefix_info.sections)
                 if prefix_sections is None else prefix_sections)
        if not names or len(set(names)) != len(names):
            raise ValueError("prefix package selection must be non-empty and unique")
        by_name = {section.name: section for section in prefix_info.sections}
        for name in names:
            section = by_name.get(name)
            if section is None:
                raise ValueError(f"prefix package section not found: {name}")
            if name == "SC5ACT":
                raise ValueError("prefix package already contains reserved actor section SC5ACT")
            copied = output_dir / f"prefix-{name}.bin"
            copied.write_bytes(prefix_raw[section.offset:section.offset + section.size])
            sections.append({
                "name": section.name, "kind": section.kind,
                "path": copied.name, "alignment": section.alignment,
                "flags": ["streamable", "read_only"],
            })
            prefix_descriptors.append({"name": name, "kind": section.kind,
                                       "source_sha256": hashlib.sha256(
                                           copied.read_bytes()).hexdigest()})
    sections.append({
        "name": "SC5ACT", "kind": "SCA1", "path": payload_path.name,
        "alignment": 16, "flags": ["streamable", "read_only"],
    })
    package_manifest.write_text(json.dumps({
        "same_package": 1,
        "sections": sections,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    package_path = output_dir / "sc5act-costumes.msu"
    info = build_package(package_manifest, package_path)
    section = next(section for section in info.sections if section.name == "SC5ACT")
    directory_include.parent.mkdir(parents=True, exist_ok=True)
    directory_include.write_text(
        pose_directory_include(records, bank=directory_bank,
                               span_first_bank=span_first_bank), encoding="ascii",
    )
    manifest = {
        "schema": "same_scumm_v5_actor_pose_package_v2",
        "pose_format": "signed-foot-anchor-span-chunks-v1",
        "pose_record_bytes": POSE_RECORD_SIZE,
        "chunk_record_bytes": CHUNK_RECORD_SIZE,
        "span_record_bytes": SPAN_RECORD_SIZE,
        "palette_record_bytes": PALETTE_RECORD_SIZE,
        "package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
        "package_bytes": package_path.stat().st_size,
        "section": section.to_dict(),
        "prefix_sections": prefix_descriptors,
        "pose_count": len(records),
        "unique_sources": [
            {"costume": costume_id, "resource": key,
             "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            for costume_id, (key, raw) in sorted(costumes.items())
        ],
        "poses": records,
        "rom_payload_policy": "pose pixel slots are absent; ROM contains key, palette, and signed span metadata",
    }
    manifest_path = output_dir / "sc5act-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    inspect_package(package_path, verify=True)
    return {**manifest, "package_path": str(package_path),
            "manifest_path": str(manifest_path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--costume", type=int, action="append", default=[],
                        help="source costume id to compile; may be repeated")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--directory-include", type=Path)
    parser.add_argument("--directory-bank", type=lambda value: int(value, 0), default=13)
    parser.add_argument("--span-directory-bank", type=lambda value: int(value, 0), default=25)
    parser.add_argument("--output", type=Path,
                        help="legacy fixture-only ROM sheet include output")
    parser.add_argument("--facing", type=int, default=180,
                        help="legacy fixture-only single facing")
    parser.add_argument("--bank", type=lambda value: int(value, 0), default=95,
                        help="legacy fixture-only ROM data bank")
    parser.add_argument("--prefix-package", type=Path)
    prefix_group = parser.add_mutually_exclusive_group()
    prefix_group.add_argument("--prefix-section", action="append")
    prefix_group.add_argument("--prefix-all-sections", action="store_true")
    args = parser.parse_args()

    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    provider = LucasartsScummV5ResourceProvider(
        MemoryResourceProvider(source_bytes(args.archive)), policy
    )
    if not args.costume:
        parser.error("at least one --costume is required")
    if args.output_dir is None:
        if args.output is None or len(set(args.costume)) != 1 or args.prefix_package:
            parser.error("legacy mode requires --output and exactly one --costume")
        costume_id = args.costume[0]
        key = policy.costume_key_template.format(costume=costume_id)
        costume = ScummV5Costume(provider.read(key), key=key)
        frames = tuple(cook_pose(costume, frame, width=POSE_WIDTH,
                                 height=POSE_HEIGHT, facing=args.facing)
                       for frame in (1, 2, 3, 4))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        binary = args.output.with_suffix(".bin")
        binary.write_bytes(b"".join(frames))
        args.output.write_text("\n".join((
            "; Legacy controller-fixture ROM sheet; production actor pixels use SC5ACT.",
            f"SCUMM_V5_ACTOR_SPRITE_WIDTH = ${POSE_WIDTH:04X}",
            f"SCUMM_V5_ACTOR_SPRITE_HEIGHT = ${POSE_HEIGHT:04X}",
            f"SCUMM_V5_ACTOR_SPRITE_FRAME_COUNT = ${len(frames):02X}",
            f"SCUMM_V5_ACTOR_SPRITE_COSTUME = ${costume_id:02X}",
            f"SCUMM_V5_ACTOR_SPRITE_FACING = ${args.facing:04X}",
            f"SCUMM_V5_ACTOR_SPRITE_BANK = ${args.bank:02X}",
            f".bank {args.bank}", ".org $8000", "ScummV5_ActorSprite_Data:",
            f'.incbin "{binary.resolve()}"', "",
        )), encoding="ascii")
        print(args.output)
        return 0
    if args.directory_include is None or args.output is not None:
        parser.error("package mode requires --directory-include and cannot use --output")
    costumes = {}
    for costume_id in sorted(set(args.costume)):
        key = policy.costume_key_template.format(costume=costume_id)
        costumes[costume_id] = (key, provider.read(key))
    result = write_pose_package(
        args.output_dir, costumes, directory_include=args.directory_include,
        directory_bank=args.directory_bank,
        span_first_bank=args.span_directory_bank,
        prefix_package=args.prefix_package,
        prefix_sections=(None if args.prefix_all_sections or not args.prefix_section
                         else tuple(args.prefix_section)),
    )
    print(json.dumps({"package": result["package_path"],
                      "package_sha256": result["package_sha256"],
                      "poses": result["pose_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
