#!/usr/bin/env python3
"""Cook the selected complete SCUMM v5 charset for target delivery."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from same.engines.scumm_v5.font import decode_charset, encode_charset
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit_native_v2(sources: dict[int, bytes], output: Path, include: Path,
                   manifest: Path) -> dict:
    """One bank of CRC-checked SC5FNT records; no palette-index truncation."""
    offsets = bytearray(b"\xff\xff" * 256)
    records = bytearray()
    rows = []
    for identity, source in sorted(sources.items()):
        if type(identity) is not int or not 0 <= identity <= 255:
            raise ValueError("native charset identity must fit u8")
        raw = encode_charset(source, logical_id=identity, source_id=identity, version=2)
        font = decode_charset(raw, expected_logical_id=identity)
        if len(records) + len(raw) + len(offsets) > 32768:
            raise ValueError("native font directory exceeds its 32 KiB LoROM bank")
        offsets[identity*2:identity*2+2] = len(records).to_bytes(2, "little")
        rows.append(dict(logical_id=identity, offset=len(records), length=len(raw),
                         sha256=sha(raw), source_sha256=font.source_sha256.hex(),
                         bpp=font.bits_per_pixel))
        records.extend(raw)
    if len(records)+len(offsets) > 32768:
        raise ValueError("native font directory exceeds its 32 KiB LoROM bank")
    for path in (output, include, manifest): path.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(records)
    directory = output.with_suffix('.directory.bin')
    directory.write_bytes(offsets)
    include.write_text(
        '; Generated checked SC5FNT v2 directory; IDs are source identities.\n'
        '.bank 24\n.org $8000\nScummV5_FontDirectory:\n'
        f'.incbin "{directory.resolve().as_posix()}"\n'
        'ScummV5_FontRecords:\n'
        f'.incbin "{output.resolve().as_posix()}"\n')
    report = dict(format='same-scumm-v5-font-manifest', version=2, records=rows,
                  record_sha256=sha(records), directory_sha256=sha(offsets),
                  bytes=len(records)+len(offsets))
    manifest.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--logical-id", type=int, default=0)
    parser.add_argument("--native-v2", action="store_true")
    parser.add_argument("--source-id", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.archive) as bundle:
        members = {}
        for key, suffix in (("game.index", ".000"), ("game.data", ".001")):
            matches = [name for name in bundle.namelist() if name.upper().endswith(suffix)]
            if len(matches) != 1:
                raise RuntimeError(f"archive must contain one SCUMM {suffix} member")
            members[key] = matches[0]
        raw = {key: bundle.read(member) for key, member in members.items()}
    profile = load_profile(args.profile, verify_resources=False)
    policy = parse_game_policy(profile)
    if policy is None:
        raise RuntimeError("profile has no SCUMM v5 resource policy")
    provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(raw), policy)
    if args.native_v2:
        sources = {int(key.split('.')[1]): provider.read(key)
                   for key in provider.keys() if key.startswith('charset.')}
        print(json.dumps(emit_native_v2(sources, args.output, args.include, args.manifest), sort_keys=True))
        return 0
    source_key = f"charset.{args.source_id}"
    source = provider.read(source_key)
    cooked = encode_charset(source, logical_id=args.logical_id,
                             source_id=args.source_id)
    decoded = decode_charset(cooked, expected_logical_id=args.logical_id)
    row_masks = bytearray(256 * 8)
    for code, glyph in enumerate(decoded.glyphs):
        if glyph is None or glyph.width > 8 or glyph.height > 8:
            continue
        for y in range(glyph.height):
            value = 0
            for x in range(glyph.width):
                if glyph.pixels[y * glyph.width + x]:
                    value |= 0x80 >> x
            row_masks[code * 8 + y] = value
    row_mask_path = args.output.with_suffix(".rowmasks.bin")
    expanded15 = bytearray()
    for mask in range(256):
        expanded15.extend(15 if mask & (0x80 >> x) else 0 for x in range(8))
    expanded15_path = args.output.with_suffix(".mask15.bin")
    zero_overlay_path = args.output.with_suffix(".overlay-zero.bin")
    glyph15 = bytearray(256 * 64)
    for code in range(256):
        for y in range(8):
            mask = row_masks[code * 8 + y]
            for x in range(8):
                glyph15[code * 64 + y * 8 + x] = 15 if mask & (0x80 >> x) else 0
    glyph15_path = args.output.with_suffix(".glyph15.bin")
    advances = bytearray(256)
    fast15 = bytearray(256)
    content_ymax = bytearray([0xFF] * 256)
    for code, glyph in enumerate(decoded.glyphs):
        if glyph is None:
            continue
        advances[code] = glyph.advance
        fast15[code] = int(glyph.x_origin == 0 and glyph.y_origin == 0 and
                           glyph.height == 8 and glyph.width == glyph.advance and
                           glyph.width <= 8)
        rows = [y for y in range(glyph.height)
                if any(glyph.pixels[y * glyph.width:(y + 1) * glyph.width])]
        if rows:
            content_ymax[code] = max(rows)
    advances_path = args.output.with_suffix(".advances.bin")
    fast15_path = args.output.with_suffix(".fast15.bin")
    content_ymax_path = args.output.with_suffix(".content-ymax.bin")
    sparse_offsets = bytearray(512)
    sparse_counts = bytearray(256)
    sparse_pixels = bytearray()
    for code, glyph in enumerate(decoded.glyphs):
        sparse_offsets[code * 2:code * 2 + 2] = len(sparse_pixels).to_bytes(2, "little")
        if glyph is None or glyph.width > 8 or glyph.height > 8:
            continue
        points = [y * 80 + x for y in range(glyph.height) for x in range(glyph.width)
                  if glyph.pixels[y * glyph.width + x]]
        sparse_counts[code] = len(points)
        for point in points:
            sparse_pixels.extend(point.to_bytes(2, "little"))
    sparse_offsets_path = args.output.with_suffix(".sparse-offsets.bin")
    sparse_counts_path = args.output.with_suffix(".sparse-counts.bin")
    sparse_pixels_path = args.output.with_suffix(".sparse-pixels.bin")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.include.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(cooked)
    row_mask_path.write_bytes(row_masks)
    expanded15_path.write_bytes(expanded15)
    zero_overlay_path.write_bytes(bytes(640))
    glyph15_path.write_bytes(glyph15)
    advances_path.write_bytes(advances)
    fast15_path.write_bytes(fast15)
    content_ymax_path.write_bytes(content_ymax)
    sparse_offsets_path.write_bytes(sparse_offsets)
    sparse_counts_path.write_bytes(sparse_counts)
    sparse_pixels_path.write_bytes(sparse_pixels)
    args.include.write_text(
        "; Generated by tools/generate_snes_scumm_charset.py.\n"
        ".bank 24\n.org $8000\n"
        "ScummV5_Font0_Record:\n"
        f'.incbin "{args.output.resolve().as_posix()}"\n'
        "ScummV5_Font0_Record_End:\n"
        "ScummV5_FontZeroOverlay:\n"
        f'.incbin "{zero_overlay_path.resolve().as_posix()}"\n'
        "ScummV5_FontGlyphExpansion15:\n"
        f'.incbin "{glyph15_path.resolve().as_posix()}"\n'
        "ScummV5_FontAdvances:\n"
        f'.incbin "{advances_path.resolve().as_posix()}"\n'
        "ScummV5_FontFast15Eligible:\n"
        f'.incbin "{fast15_path.resolve().as_posix()}"\n'
        "ScummV5_FontContentYMax:\n"
        f'.incbin "{content_ymax_path.resolve().as_posix()}"\n'
        "ScummV5_FontSparseOffsets:\n"
        f'.incbin "{sparse_offsets_path.resolve().as_posix()}"\n'
        "ScummV5_FontSparseCounts:\n"
        f'.incbin "{sparse_counts_path.resolve().as_posix()}"\n'
        "ScummV5_FontSparsePixels:\n"
        f'.incbin "{sparse_pixels_path.resolve().as_posix()}"\n',
        encoding="utf-8",
    )
    report = {
        "format": "same-scumm-v5-font-manifest",
        "version": 1,
        "logical_charset_id": args.logical_id,
        "source_resource": source_key,
        "source_bytes": len(source),
        "source_sha256": sha(source),
        "record_bytes": len(cooked),
        "record_sha256": decoded.sha256,
        "font_height": decoded.font_height,
        "baseline": decoded.baseline,
        "line_spacing": decoded.line_spacing,
        "bits_per_pixel": 1,
        "character_count": 256,
        "archive_sha256": sha(args.archive.read_bytes()),
        "index_sha256": sha(raw["game.index"]),
        "data_sha256": sha(raw["game.data"]),
    }
    args.manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
