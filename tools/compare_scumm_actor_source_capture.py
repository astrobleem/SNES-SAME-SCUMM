#!/usr/bin/env python3
"""Offline source-decoder INDEX8 comparison; never launches an emulator.

Only diagnostics explicitly known to have no actor palette overrides are
supported. A match is not native acceptance or evidence about CGRAM/PPU output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from same.engines.scumm_v5.costume import ScummV5Costume
from same.engines.scumm_v5.policy import parse_game_policy
from same.engines.scumm_v5.resources import LucasartsScummV5ResourceProvider
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from tools.actor_pose_plan import PosePlan, project_pose_aspect_fit, render_reference
from tools.actor_pose_plan import compile_pose
from tools.generate_snes_scumm_actor_sprite import source_bytes


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_sha256(record: dict, field: str, data: bytes) -> str:
    """Bind supplied bytes to a mandatory recorded identity; never infer it."""
    expected = record.get(field)
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f'missing or invalid required identity: {field}')
    actual = sha(data)
    if expected != actual:
        raise ValueError(f'{field} differs from supplied bytes')
    return actual


def compare_capture(plan: PosePlan, pose: dict, visual: dict,
                    backdrop: bytes, actual: bytes) -> dict:
    """Pure comparison for the declared no-overrides, scale255 diagnostic."""
    width, height = visual['width'], visual['height']
    if (width, height, visual['pitch']) != (256, 224, 256):
        raise ValueError('capture comparison requires a 256x224, pitch256 surface')
    if len(backdrop) != width * height or len(actual) != len(backdrop):
        raise ValueError('capture/backdrop length differs from complete indexed surface')
    if pose.get('actor_palette_overrides') or pose.get('palette_overrides'):
        raise ValueError('actor palette overrides are outside this diagnostic contract')
    for field in ('actor_scale', 'actor_scale_x', 'actor_scale_y'):
        if field in pose and pose[field] != 255:
            raise ValueError('only scale255 diagnostic poses are supported')
    foot = pose['foot_screen']
    if len(foot) != 2 or any(type(v) is not int or not -32768 <= v <= 65535 for v in foot):
        raise ValueError('foot must contain two signed16 or raw u16 coordinates')
    # Current observations serialize the native signed scratch with read_u16.
    fx, fy = (v - 65536 if v > 32767 else v for v in foot)
    space = pose.get('foot_coordinate_space', 'surface')
    if space == 'source_room':
        projection = pose.get('room_projection')
        stored = visual.get('projection')
        if not isinstance(projection, dict) or not isinstance(stored, dict):
            raise ValueError('source_room capture requires observed and stored projection metadata')
        for field in ('source_width', 'source_height', 'target_width', 'target_height',
                      'content_width', 'content_height', 'offset_x', 'offset_y', 'sampling'):
            if field not in projection or projection[field] != stored.get(field):
                raise ValueError(f'observed room projection differs: {field}')
        sw, sh = projection['source_width'], projection['source_height']
        if type(sw) is not int or type(sh) is not int or not 1 <= sw <= 65535 or not 1 <= sh <= 65535:
            raise ValueError('source dimensions must be positive u16')
        if width * sh <= height * sw:
            cw, ch = width, max(1, sh * width // sw)
        else:
            cw, ch = max(1, sw * height // sh), height
        expected_geometry = (width, height, cw, ch, (width-cw)//2, (height-ch)//2)
        if tuple(projection[k] for k in ('target_width', 'target_height', 'content_width',
                                        'content_height', 'offset_x', 'offset_y')) != expected_geometry:
            raise ValueError('projection metadata disagrees with source aspect fit')
        if projection['sampling'] != 'nearest_neighbor_aspect_fit':
            raise ValueError('unsupported projection sampling')
        plan = project_pose_aspect_fit(plan, foot_x=fx, foot_y=fy,
                                      source_width=sw, source_height=sh)
        fx = fy = 0
    elif space != 'surface':
        raise ValueError(f'unknown foot coordinate space: {space}')
    expected = render_reference(backdrop, width, height, plan, anchor_x=fx, anchor_y=fy)
    return dict(different_pixels=sum(a != b for a, b in zip(actual, expected)),
                captured_indexed_sha256=sha(actual), source_reference_sha256=sha(expected),
                foot_coordinate_space=space)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'profile', 'observations', 'storage', 'package', 'rom', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--diagnostic-no-actor-palette-overrides', action='store_true', required=True,
                        help='explicitly attest these diagnostic captures used no actor palette overrides')
    args = parser.parse_args()
    try:
        observations = json.loads(args.observations.read_text())
        storage = json.loads(args.storage.read_text())
        package = args.package.read_bytes()
        rom = args.rom.read_bytes()
        package_hash = require_sha256(observations, 'package_sha256', package)
        rom_hash = require_sha256(observations, 'rom_sha256', rom)
        require_sha256(storage, 'package_sha256', package)
        policy = parse_game_policy(load_profile(args.profile, verify_resources=False))
        provider = LucasartsScummV5ResourceProvider(MemoryResourceProvider(source_bytes(args.archive)), policy)
        captures = observations['captures']
        if not isinstance(captures, list) or not captures:
            raise ValueError('observations must contain at least one capture')
        report = dict(kind='OFFLINE_SOURCE_DECODER_INDEXED_COMPARISON',
                      scope='scale255 diagnostic; no actor palette overrides; INDEX8 only; not native acceptance',
                      archive_sha256=sha(args.archive.read_bytes()), rom_sha256=rom_hash,
                      package_sha256=package_hash, profile_sha256=sha(args.profile.read_bytes()),
                      observations_sha256=sha(args.observations.read_bytes()),
                      storage_sha256=sha(args.storage.read_bytes()), captures=[])
        for capture in captures:
            pose = capture['pose']
            room = pose['surface_presented_room']
            matches = [r for r in storage['visual_records'] if r['room'] == room]
            if len(matches) != 1:
                raise ValueError(f'expected exactly one visual record for presented room {room}')
            visual = matches[0]
            offset, length = visual['pixel_package_offset'], visual['pixel_length']
            if type(offset) is not int or type(length) is not int or offset < 0 or length <= 0 or offset + length > len(package):
                raise ValueError('visual pixel range exceeds package')
            backdrop = package[offset:offset + length]
            if zlib.crc32(backdrop) & 0xffffffff != int(visual['pixel_crc32'], 16):
                raise ValueError('visual pixel CRC-32 differs from storage manifest')
            label = capture['label']
            if not isinstance(label, str) or not label or Path(label).name != label or label in ('.', '..'):
                raise ValueError('capture label must be a single filename component')
            actual = (args.observations.parent / (label + '.indexed.bin')).read_bytes()
            require_sha256(capture, 'indexed_surface_sha256', actual)
            key = policy.costume_key_template.format(costume=pose['costume_id'])
            raw = provider.read(key)
            costume = ScummV5Costume(raw, key=key)
            frame, facing, step = (pose[k] for k in (
                'actor_render_pose_frame', 'actor_render_facing', 'actor_render_pose_step'))
            plan = compile_pose(costume.decode_pose(frame, facing=facing, step=step), costume.palette)
            report['captures'].append(dict(label=label, room=room, source_key=key,
                source_sha256=sha(raw), frame=frame, facing=facing, step=step,
                foot=pose['foot_screen'], **compare_capture(plan, pose, visual, backdrop, actual)))
        matched = all(c['different_pixels'] == 0 for c in report['captures'])
        report['result'] = 'SOURCE_INDEXED_MATCH' if matched else 'SOURCE_INDEXED_MISMATCH'
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return 0 if matched else 1
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f'comparison error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
