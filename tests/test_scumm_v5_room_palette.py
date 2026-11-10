"""Classic v5 room palette semantics using copyright-free room resources."""
import json
from dataclasses import replace
from pathlib import Path
import struct
import unittest

from same.engine import EngineHost
from same.engines import default_registry
from same.errors import EngineExecutionError
from same.profile import load_profile
from same.resources import MemoryResourceProvider
from same.services import HostServices

ROOT = Path(__file__).resolve().parents[1]
BASE = tuple((i, 255 - i, (i * 17) % 256) for i in range(256))


def room(palette=BASE):
    return struct.pack('<4sBHHH', b'SC5R', 1, 8, 2, 256) + bytes(
        v for rgb in palette for v in rgb) + bytes(range(16))


def intensity(level, first, last):
    return bytes((0x33, 8, level, first, last))


def rgb_intensity(red, green, blue, first, last):
    return bytes((0x33, 11)) + struct.pack('<HHHBBB', red, green, blue, 0, first, last)


def color(index, rgb):
    return bytes((0x33, 4)) + struct.pack('<HHHBB', *rgb, 0, index)


def host_for(*steps, extra=None):
    script = b'\x80'.join(steps) + b'\x80\x00'
    profile = load_profile(ROOT / 'examples/profiles/scumm_v5_conformance.json')
    resources = MemoryResourceProvider({'script.boot': script, 'room.0': room(), **(extra or {})})
    host = EngineHost(profile, default_registry(), services=HostServices.create(profile, resources=resources))
    host.boot()
    return host


class RoomPaletteTests(unittest.TestCase):
    def test_intensity_is_non_cumulative_and_255_restores_base_with_v5_cap(self):
        host = host_for(intensity(128, 0, 3), intensity(128, 0, 3), intensity(255, 0, 3))
        base = host.engine._video.room.palette
        host.tick()
        expected = [tuple(v * 128 // 255 for v in c) for c in BASE[:4]]
        self.assertEqual(list(host.services.video.surface.palette[:4]), expected)
        host.tick()
        self.assertEqual(list(host.services.video.surface.palette[:4]), expected)
        host.tick()
        self.assertEqual(list(host.services.video.surface.palette[:4]),
                         [tuple(min(252, v) for v in c) for c in BASE[:4]])
        self.assertEqual(host.services.video.surface.palette[4], BASE[4])
        self.assertIs(host.engine._video.room.palette, base)
        self.assertEqual(base, BASE)

    def test_direct_color_is_current_only_and_later_intensity_uses_room_source(self):
        host = host_for(color(7, (255, 1, 253)), intensity(128, 7, 7), color(7, (1, 2, 3)))
        host.tick()
        self.assertEqual(host.services.video.surface.palette[7], (255, 1, 253))
        host.engine._video.project()
        self.assertEqual(host.services.video.surface.palette[7], (255, 1, 253))
        host.tick()
        self.assertEqual(host.services.video.surface.palette[7], tuple(v * 128 // 255 for v in BASE[7]))
        host.tick()
        self.assertEqual(host.services.video.surface.palette[7], (1, 2, 3))
        self.assertEqual(host.engine._video.room.palette[7], BASE[7])
        self.assertEqual(host.engine._video.backdrop_surface.palette[7], BASE[7])

    def test_rgb_ranges_accumulate_in_order_and_survive_all_room_projections(self):
        host = host_for(intensity(100, 1, 2), rgb_intensity(255, 128, 0, 2, 3))
        host.tick()
        host.tick()
        expected = list(BASE)
        expected[1] = tuple(v * 100 // 255 for v in BASE[1])
        for i in (2, 3):
            expected[i] = (min(252, BASE[i][0]), BASE[i][1] * 128 // 255, 0)
        adapter = host.engine._video
        adapter.project()
        self.assertEqual(list(host.services.video.surface.palette), expected)
        composition = adapter.prepare_composition()
        self.assertEqual(list(composition.palette), expected)
        adapter.project_composition()
        self.assertEqual(list(host.services.video.surface.palette), expected)
        host.engine._actors_dirty = True
        host.tick()
        self.assertEqual(list(host.services.video.surface.palette), expected)

    def test_fresh_host_restore_keeps_effective_palette_and_original_base(self):
        steps = (intensity(80, 1, 2), rgb_intensity(20, 100, 200, 2, 4),
                 color(3, (255, 254, 253)), intensity(255, 1, 4))
        host = host_for(*steps)
        for _ in range(3):
            host.tick()
        expected = tuple(host.services.video.surface.palette)
        saved = host.engine.save_state(host.context)
        delta = json.loads(saved)['room_ops']['palette_overrides']
        self.assertEqual(set(delta), {'1', '2', '3', '4'})
        restored = host_for(*steps)
        restored.engine.load_state(restored.context, saved)
        restored.engine._video.project()
        self.assertEqual(tuple(restored.services.video.surface.palette), expected)
        restored.tick()
        self.assertEqual(list(restored.services.video.surface.palette[1:5]),
                         [tuple(min(252, v) for v in c) for c in BASE[1:5]])
        self.assertEqual(restored.engine._video.room.palette, BASE)

    def test_successful_room_change_replaces_base_and_clears_old_palette_delta(self):
        next_palette = ((240, 120, 60),) * 256
        host = host_for(intensity(0, 0, 255), bytes((0x72, 2)), intensity(128, 0, 255),
                        extra={'room.2': room(next_palette)})
        host.tick()
        host.tick()
        self.assertEqual(tuple(host.services.video.surface.palette), next_palette)
        self.assertEqual(host.engine.state.room_ops.palette_overrides, {})
        host.tick()
        self.assertEqual(host.services.video.surface.palette[0], (120, 60, 30))

    def test_bad_range_does_not_partially_modify_palette(self):
        host = host_for(color(7, (1, 2, 3)), rgb_intensity(255, 128, 0, 8, 2))
        host.tick()
        expected = tuple(host.services.video.surface.palette)
        with self.assertRaisesRegex(EngineExecutionError, 'reversed'):
            host.tick()
        self.assertEqual(tuple(host.services.video.surface.palette), expected)
        self.assertEqual(host.engine.state.room_ops.palette_overrides, {7: (1, 2, 3)})

    def test_variable_intensity_and_rgb_operands(self):
        def put(index, value):
            return b'\x1a' + struct.pack('<HH', index, value)
        init = b''.join(put(i, v) for i, v in ((200, 128), (201, 4), (202, 5), (203, 255), (204, 0)))
        level = b'\x33\xe8' + struct.pack('<HHH', 200, 201, 202)
        rgb = b'\x33\xeb' + struct.pack('<HHHBHH', 203, 200, 204, 0xc0, 201, 202)
        host = host_for(init + level, rgb)
        host.tick()
        self.assertEqual(host.services.video.surface.palette[4], tuple(v * 128 // 255 for v in BASE[4]))
        host.tick()
        for i in (4, 5):
            self.assertEqual(host.services.video.surface.palette[i], (BASE[i][0], BASE[i][1] * 128 // 255, 0))

    def test_null_room_retains_palette_base_delta_and_fresh_save_restore(self):
        def make():
            script = intensity(128, 1, 4) + b'\x80\x72\x00\x80' + intensity(255, 1, 4) + b'\x80\x00'
            profile = load_profile(ROOT / 'examples/profiles/scumm_v5_conformance.json')
            profile = replace(profile, options={**profile.options, 'initial_room': 1})
            resources = MemoryResourceProvider({'script.boot': script, 'room.1': room()})
            host = EngineHost(profile, default_registry(), services=HostServices.create(profile, resources=resources))
            host.boot()
            return host
        host = make()
        host.tick()
        expected = tuple(host.services.video.surface.palette)
        delta = dict(host.engine.state.room_ops.palette_overrides)
        host.tick()
        self.assertEqual(host.engine.state.current_room, 0)
        self.assertEqual(tuple(host.services.video.surface.palette), expected)
        self.assertEqual(host.engine.state.room_ops.palette_overrides, delta)
        self.assertEqual(host.engine.state.room_ops.base_palette, BASE)
        saved = host.engine.save_state(host.context)
        restored = make()
        restored.engine.load_state(restored.context, saved)
        self.assertEqual(tuple(restored.services.video.surface.palette), expected)
        restored.tick()
        self.assertEqual(list(restored.services.video.surface.palette[1:5]),
                         [tuple(min(252, v) for v in c) for c in BASE[1:5]])

    def test_old_save_reconstructs_base_from_source_and_bad_base_is_rejected(self):
        host = host_for(intensity(128, 1, 4))
        host.tick()
        data = json.loads(host.engine.save_state(host.context))
        del data['room_ops']['base_palette']
        restored = host_for(intensity(128, 1, 4))
        restored.engine.load_state(restored.context, json.dumps(data).encode())
        self.assertEqual(restored.engine.state.room_ops.base_palette, BASE)
        from same.errors import SaveFormatError
        for bad in ([[1, 2, 3]], [[0, 0, 256]] * 256):
            data['room_ops']['base_palette'] = bad
            with self.assertRaisesRegex(SaveFormatError, 'base palette'):
                restored.engine.load_state(restored.context, json.dumps(data).encode())

    def test_shadow_remains_state_only(self):
        command = bytes((0x33, 12)) + struct.pack('<HHHBBB', 0, 0, 0, 0, 0, 255)
        host = host_for(command)
        host.tick()
        self.assertEqual(tuple(host.services.video.surface.palette), BASE)


if __name__ == '__main__':
    unittest.main()
