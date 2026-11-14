"""Actual committed reader/fence/capture against RAM fixtures; no native run."""
import base64
import re
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import validate_scumm_actor_visual_probe_nexen as probe

CURSOR = 0x400740


class Session:
    def __init__(self):
        self.mem = {}
        self.reads = []
        for address, value, size in (
            (probe.ROOM,4,1), (probe.LIFECYCLE,2,1), (probe.SURFACE_STATE,4,1),
            (probe.SURFACE_PRESENTED_ROOM,4,1), (probe.SURFACE_ROOM_GENERATION,2,2),
            (probe.ACTOR_RENDER_VALID,1,1), (0x7E5E10,161,2), (0x7E5E12,133,2),
            (probe.ACTOR_RENDER_FACING,90,2), (0x7E5E50,2,1), (0x7E5E51,1,1),
            (probe.ACTOR_STATE+0x15,2,1), (probe.ACTOR_STATE+0x16,1,1),
            (probe.ACTOR_STATE+0x7D,4,2), (probe.SURFACE_NEXT_GENERATION,65,2),
            (probe.MODE3_PENDING_GENERATION,65,2), (probe.MODE3_COMMITTED_GENERATION,65,2),
            (probe.MODE3_CONTROL_STATE,1,1),
        ): self.put(address,value,size)
        self.drift = False

    def put(self,address,value,size=2):
        for i in range(size): self.mem[address+i] = (value >> (8*i)) & 255

    def read_memory(self, kind, address, size):
        self.reads.append((kind,address,size))
        if kind == 'snesMemory':
            if probe.ACTOR_STATE <= address < probe.ACTOR_STATE+128:
                assert (address-probe.ACTOR_STATE,size) in ((0x15,1),(0x16,1),(0x7D,2)), 'pending pose/scratch read'
            return bytes(self.mem.get(address+i,0) for i in range(size))
        if self.drift and kind == 'snesCgRam': self.put(0x7E5E10,162)
        return bytes(size)

    def take_screenshot(self, **kwargs):
        assert kwargs == {'format': 'base64'}
        return {'base64': base64.b64encode(b'fake-session-ppu-png').decode()}

    def get_ppu_state(self):
        return {'bgMode': 3, 'frameCount': 560, 'layers':[{'chrAddr':0,'tilemapAddr':0x7000}]}

    def get_state(self):
        return {'isPaused': True, 'frameCount': 560}

    def read_u8(self,address): return self.read_memory('snesMemory',address,1)[0]
    def read_u16(self,address): return int.from_bytes(self.read_memory('snesMemory',address,2),'little')


def observer(session, directory):
    obj = probe.ProbeObserver(session, Path(directory), bytes(57344), deadline=float('inf'), cursor_base=CURSOR)
    obj.capture_timeout_boundary = Mock()
    return obj


class CommittedPoseObserverTests(unittest.TestCase):
    def test_live_capture_rejects_pending_scene_even_with_idle_backend(self):
        address = 0x3700
        session = Session()
        with tempfile.TemporaryDirectory() as directory:
            for phase, dirty in ((0, 1), (1, 0), (2, 0), (3, 0), (4, 0)):
                with self.subTest(phase=phase, dirty=dirty):
                    session.put(address, phase)
                    session.put(address + 4, dirty)
                    self.assertTrue(probe.committed_surface_is_presented(
                        probe.read_committed_pose(session, cursor_base=CURSOR)))
                    with self.assertRaisesRegex(RuntimeError, "scene redraw"):
                        probe.capture_committed_surface(session, Path(directory), 'pending',
                            cursor_base=CURSOR, scene_control_address=address)
            session.put(address, 0)
            session.put(address + 4, 0)
            result = probe.capture_committed_surface(session, Path(directory), 'settled',
                cursor_base=CURSOR, scene_control_address=address)
            self.assertEqual(result['ppu_indexed_differences'], 0)
            self.assertEqual(result['scene_control'], bytes(26).hex())
        self.assertFalse(probe.scene_control_is_settled(bytes(25)))

    def test_hidden_actor_room_capture_does_not_certify_actor(self):
        s = Session()
        s.put(0x7E5E51, 0, 1)
        s.put(probe.ACTOR_STATE+0x7D, 0, 2)
        state = probe.read_committed_pose(s, cursor_base=CURSOR)
        self.assertTrue(probe.committed_surface_is_presented(state, expected_room=4))
        self.assertFalse(probe.committed_pose_is_presented(state))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                probe.capture_committed_surface(s, Path(directory), 'actor', cursor_base=CURSOR)
            record = probe.capture_committed_surface(s, Path(directory), 'room',
                cursor_base=CURSOR, expected_room=4, require_visible_actor=False)
            self.assertEqual(record['presentation_fence'], 'committed-room-surface-paused-state')
            self.assertNotIn('accepted_frame', record['pose'])
            self.assertEqual(record['ppu_indexed_differences'], 0)
            self.assertEqual(record['cgram_difference_bytes'], 0)
            with self.assertRaisesRegex(RuntimeError, 'cannot certify'):
                probe.capture_committed_surface(s, Path(directory), 'invalid',
                    cursor_base=CURSOR, require_visible_actor=False, expected_frame=3)
        for change in (dict(mode3_inflight_count=1), dict(surface_pending_visual=1),
                       dict(surface_room=5), dict(backend_committed_generation=64),
                       dict(backend_committed_generation_hi=1), dict(composition_active=1),
                       dict(actor_render_retry=1), dict(event_count=1)):
            with self.subTest(change=change):
                self.assertFalse(probe.committed_surface_is_presented(dict(state, **change)))

    def test_visible_contrast_is_separate_from_pixel_equality_and_slot_zero(self):
        cgram=bytearray(512)
        self.assertEqual(probe.indexed_contrast_pixels(bytes((0,1,178)),cgram),0)
        cgram[356:358]=(0x7FFF).to_bytes(2,'little')
        self.assertEqual(probe.indexed_contrast_pixels(bytes((0,1,178)),cgram),1)
        self.assertEqual(probe.indexed_contrast_pixels(bytes((0,1,178)),cgram,background_index=178),2)
        for bad in (b'',bytes(511),bytes(513)):
            with self.assertRaises(ValueError):probe.indexed_contrast_pixels(b'abc',bad)
        with self.assertRaises(ValueError):probe.indexed_contrast_pixels(b'abc',cgram,background_index=256)


    def test_requested_text_cannot_borrow_old_caption_pixels(self):
        text=bytearray(128);expected=b'Look at lamp';pose={'room':4,
            'surface_room_generation':2,'backend_pending_generation':65}
        def put(offset,value):text[offset:offset+2]=value.to_bytes(2,'little')
        for offset,value in ((0,2),(2,64),(4,64),(0x24,len(expected)),
                             (0x38,1),(0x64,4),(0x66,2),(0x68,1)):put(offset,value)
        check=lambda:probe.indexed_text_request_is_composed(
            text,expected,pose,expected,after_generation=64)
        self.assertFalse(check())  # new bytes, old displayed generation
        put(0,1);put(2,65);self.assertTrue(check())
        self.assertFalse(probe.indexed_text_request_is_composed(
            text,b'Use the lamp',pose,expected,after_generation=64))
        put(0,0);self.assertFalse(check()) # completion not acknowledged
        put(4,65);self.assertFalse(check()) # idle bytes may already belong to replacement
        pose['backend_pending_generation']=66;self.assertFalse(check()) # unrelated cursor generation
        put(0,2);self.assertFalse(check()) # new request can replace retained bytes
        put(0,0);put(0x66,3);self.assertFalse(check())

    def test_preflight_cannot_relabel_previous_caption_capture(self):
        # Captured failure shape, using original synthetic text only: new raw
        # bytes/preflight while the old caption and a cursor generation exist.
        text=bytearray(128);raw=b'Look at lamp'
        for offset,value in ((0,0),(2,235),(4,235),(0x24,len(raw)),
                             (0x38,0),(0x64,4),(0x66,2),(0x68,1)):
            text[offset:offset+2]=value.to_bytes(2,'little')
        pose={'room':4,'surface_room_generation':2,'backend_pending_generation':236}
        self.assertFalse(probe.indexed_text_request_is_composed(
            text,raw,pose,raw,after_generation=234))
        text[0:2]=(1).to_bytes(2,'little');text[2:4]=(236).to_bytes(2,'little')
        self.assertFalse(probe.indexed_text_request_is_composed(
            text,raw,pose,raw,after_generation=234)) # no completed draw pass
        text[0x38:0x3a]=(1).to_bytes(2,'little')
        self.assertTrue(probe.indexed_text_request_is_composed(
            text,raw,pose,raw,after_generation=234))

    def test_settled_text_is_only_a_pixel_comparison_candidate(self):
        pose = probe.read_committed_pose(Session(), cursor_base=CURSOR)
        text = bytearray(128); raw = b'Original fixture text'
        for offset, value in ((0,0),(2,61),(4,61),(0x24,len(raw)),
                              (0x38,1),(0x64,4),(0x66,2),(0x68,1)):
            text[offset:offset+2] = value.to_bytes(2, 'little')
        check = lambda: probe.indexed_text_committed_candidate(
            text, raw, pose, raw, after_generation=60)
        self.assertTrue(check()) # later actor/cursor generation is fully committed
        # This is deliberately NOT the immutable queued-caption association.
        self.assertFalse(probe.indexed_text_request_is_composed(
            text, raw, pose, raw, after_generation=60))
        for offset, value in ((0,2),(4,60),(0x38,0),(0x66,3),(0x68,0)):
            old = bytes(text[offset:offset+2]); text[offset:offset+2] = value.to_bytes(2, 'little')
            self.assertFalse(check()); text[offset:offset+2] = old
        pose['mode3_inflight_count'] = 1; self.assertFalse(check())

    def test_immutable_generation_survives_new_cursor_composition(self):
        s = Session()
        s.put(probe.MODE3_COMMITTED_GENERATION,64)
        s.put(probe.MODE3_CONTROL_STATE,2,1)
        s.put(probe.MODE3_SURFACE_LOCKED,1,1)
        snapshot = probe.snapshot_locked_generation(s,cursor_base=CURSOR)
        # Previous frame is now committed, but the CPU has already drawn the
        # next cursor into INDEX8. Only the immutable old snapshot matches PPU.
        s.put(probe.MODE3_COMMITTED_GENERATION,65)
        s.put(probe.MODE3_PENDING_GENERATION,66)
        s.put(probe.SURFACE_NEXT_GENERATION,66)
        s.put(probe.SURFACE,7,1)
        current = probe.read_committed_pose(s,cursor_base=CURSOR)
        self.assertFalse(probe.committed_pose_is_presented(current))
        self.assertTrue(probe.queued_generation_is_presented(snapshot,current))
        with tempfile.TemporaryDirectory() as directory:
            record = probe.capture_presented_generation(s,snapshot,Path(directory),'animation',cursor_base=CURSOR)
            self.assertEqual(record['ppu_indexed_differences'],0)
            self.assertEqual((Path(directory)/'animation.indexed.bin').read_bytes(),bytes(57344))
        for change in (dict(backend_committed_generation=64), dict(backend_committed_generation=66),
                       dict(mode3_state=3), dict(mode3_state=4), dict(mode3_inflight_count=1),
                       dict(surface_room_generation=3), dict(room=5), dict(error=16),
                       dict(backend_pending_generation_hi=1)):
            with self.subTest(change=change):
                self.assertFalse(probe.queued_generation_is_presented(snapshot,dict(current,**change)))

    def test_queued_capture_requires_lock_and_rechecks_paused_identity(self):
        s = Session()
        with self.assertRaises(RuntimeError): probe.snapshot_locked_generation(s,cursor_base=CURSOR)
        s.put(probe.MODE3_CONTROL_STATE,2,1)
        s.put(probe.MODE3_SURFACE_LOCKED,1,1)
        snapshot=probe.snapshot_locked_generation(s,cursor_base=CURSOR)
        s.put(probe.MODE3_PENDING_GENERATION,66)
        s.put(probe.SURFACE_NEXT_GENERATION,66)
        s.drift=True
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(RuntimeError):
            probe.capture_presented_generation(s,snapshot,Path(directory),'drift',cursor_base=CURSOR)

    def test_persistent_controller_addresses_match_memory_contract(self):
        memory = (Path(__file__).resolve().parents[1]/'runtime/snes/kernel/memory.pasm').read_text()
        session = Session()
        fields = {
            'RENDER_X': ('actor_position_source_room', 2),
            'RENDER_Y': ('actor_position_source_room', 2),
            'RENDER_VALID': ('actor_render_valid', 1),
            'RENDER_RETRY': ('actor_render_retry', 1),
            'RENDER_FACING': ('actor_render_facing', 2),
            'RENDER_COSTUME': ('costume_id', 1),
            'RENDER_VISIBLE': ('actor_render_visible', 1),
        }
        for suffix, (field, size) in fields.items():
            symbol = 'SAME_SCUMM_CONTROLLER_' + suffix
            match = re.search(r'^' + symbol + r'\s*=\s*\$([0-9A-Fa-f]+)', memory, re.M)
            self.assertIsNotNone(match, symbol)
            address = int(match[1],16)
            session.put(address, 123, size)
            state = probe.read_committed_pose(session,cursor_base=CURSOR)
            actual = state[field]
            if suffix in ('RENDER_X','RENDER_Y'):
                actual = actual[0 if suffix == 'RENDER_X' else 1]
            self.assertEqual(actual,123,symbol)
            self.assertIn(('snesMemory',address,size),session.reads)
        # The old wrong address must not determine retry readiness.
        session = Session()
        session.put(0x7E5E17,255,1)
        self.assertTrue(probe.committed_pose_is_presented(probe.read_committed_pose(session,cursor_base=CURSOR)))
        session.put(0x7E5E24,1,1)
        self.assertFalse(probe.committed_pose_is_presented(probe.read_committed_pose(session,cursor_base=CURSOR)))

    def test_next_fetch_does_not_replace_committed_key_or_block_fence(self):
        s = Session()
        for offset, value in ((1,1),(2,99),(3,2),(7,5),(10,2),(0x6B,0)):
            s.put(probe.ACTOR_STATE+offset,value,1)
        state = probe.read_committed_pose(s,cursor_base=CURSOR)
        self.assertTrue(probe.committed_pose_is_presented(state,expected_room=4,expected_x=161,expected_y=133))
        self.assertEqual((state['costume_id'],state['actor_render_pose_step'],state['actor_render_generation']), (2,1,4))
        self.assertEqual(state['actor_position_source_room'],[161,133])
        # Held-probe predicate remains strict about READ / incomplete composition.
        self.assertFalse(probe.pose_is_presented(bytes(128), render_valid=1,
            render_frame=2,render_step=1,render_generation=4,render_facing=90,
            next_generation=65,backend_pending_generation=65,backend_committed_generation=65,
            backend_pending_generation_hi=0,backend_committed_generation_hi=0,
            backend_state=1,surface_locked=0,pending_visual=0,presented_room=4,room=4,
            surface_packets_pending=False))

    def test_every_fence_component_and_position_filter_fails_closed(self):
        state = probe.read_committed_pose(Session(),cursor_base=CURSOR)
        changes = dict(error=16,lifecycle=1,actor_render_valid=0,actor_render_retry=1,
            actor_render_visible=0,actor_render_generation=0,
            composition_active=1,surface_next_generation=0,backend_pending_generation=64,
            backend_committed_generation=64,backend_pending_generation_hi=1,
            backend_committed_generation_hi=1,mode3_state=2,mode3_surface_locked=1,
            mode3_pending_count=1,mode3_inflight_count=1,event_count=1,
            surface_packets_pending=True,surface_pending_visual=1,surface_room=5,
            surface_presented_room=5,room=5)
        for key,value in changes.items():
            with self.subTest(field=key):
                self.assertFalse(probe.committed_pose_is_presented(dict(state,**{key:value})))
        for expected in ({'expected_room':5},{'expected_x':162},{'expected_y':134}):
            self.assertFalse(probe.committed_pose_is_presented(state,**expected))
        with self.assertRaises(RuntimeError): probe.read_committed_pose(Session(),cursor_base=None)

    def test_capture_omits_pending_bounds_and_feet_and_saves_raw_artifacts(self):
        s = Session()
        with tempfile.TemporaryDirectory() as directory:
            obj = observer(s,directory)
            obj.advance = Mock(side_effect=AssertionError('must not advance ready frame'))
            record = obj.capture_committed_stage('walk',max_frames=0,expected_x=161,expected_y=133)
            self.assertEqual(record['ppu_indexed_differences'],0)
            self.assertEqual(record['cgram_difference_bytes'],0)
            self.assertNotIn('foot_screen',record['pose'])
            self.assertNotIn('pose_bounds_relative_signed',record['pose'])
            self.assertNotIn('actor_bound_difference_pixels',record)
            self.assertEqual(record['pose']['actor_render_pose_step'],1)
            for suffix,size in (('indexed.bin',57344),('palette-rgb.bin',768),('vram.bin',65536),('cgram.bin',512)):
                self.assertEqual((Path(directory)/f'walk.{suffix}').stat().st_size,size)
            self.assertEqual((Path(directory)/'walk.ppu.png').read_bytes(), b'fake-session-ppu-png')
            self.assertEqual((Path(directory)/'walk.surface.ppm').read_bytes(),
                             b'P6\n256 224\n255\n'+bytes(57344*3))
            self.assertEqual(json.loads((Path(directory)/'walk.ppu-state.json').read_text()),
                             s.get_ppu_state())
            saved = json.loads((Path(directory)/'walk.committed.json').read_text())
            self.assertEqual(saved['pose'],record['pose'])
            self.assertEqual(obj.captures,[record])

    def test_expected_frame_rejects_old_walk_key_and_capture_forwards_filter(self):
        session = Session()  # committed walk frame 2, next request may be stand 3
        session.put(probe.ACTOR_STATE+3, 3, 1)
        state = probe.read_committed_pose(session, cursor_base=CURSOR)
        self.assertFalse(probe.committed_pose_is_presented(state, expected_frame=3))
        self.assertTrue(probe.committed_pose_is_presented(state, expected_frame=2))
        with tempfile.TemporaryDirectory() as directory:
            obj = observer(session, directory)
            with self.assertRaisesRegex(RuntimeError, 'fence is not satisfied'):
                probe.capture_committed_surface(session, Path(directory), 'old-walk',
                                                cursor_base=CURSOR, expected_frame=3)
            self.assertEqual(list(Path(directory).iterdir()), [])
            def advance(count):
                self.assertEqual(count, 1)
                obj.logical_frames += count
                session.put(probe.ACTOR_STATE+0x15, 3, 1)
            obj.advance = Mock(side_effect=advance)
            with patch.object(probe, 'capture_committed_surface', wraps=probe.capture_committed_surface) as capture:
                result = obj.capture_committed_stage('stand', max_frames=1, expected_frame=3)
            obj.advance.assert_called_once_with(1)
            self.assertEqual(capture.call_args.kwargs['expected_frame'], 3)
            self.assertEqual(result['pose']['actor_render_pose_frame'], 3)
            self.assertEqual(result['vm']['logical_frame'], 1)

    def test_optional_source_foot_is_explicit_not_live_elevation(self):
        s = Session()
        s.put(0x7E5E10,-3)
        with tempfile.TemporaryDirectory() as directory:
            result = probe.capture_committed_surface(s,Path(directory),'elevated',
                cursor_base=CURSOR,source_foot=(-3,123))
            self.assertEqual(result['pose']['foot_screen'],[-3,123])
            self.assertEqual(result['pose']['actor_position_source_room'],[-3,133])
            self.assertEqual(result['pose']['foot_coordinate_space'],'source_room')
            self.assertIn('caller-provided',result['pose']['foot_evidence'])

    def test_capture_rejects_key_drift_before_writing_files(self):
        s = Session(); s.drift = True
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError,'changed during capture'):
                probe.capture_committed_surface(s,Path(directory),'drift',cursor_base=CURSOR)
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_wait_checks_every_frame_including_exact_budget_boundary(self):
        s = Session(); s.put(CURSOR+56,1)
        with tempfile.TemporaryDirectory() as directory:
            obj = observer(s,directory)
            def advance(count):
                self.assertEqual(count,1)
                obj.logical_frames += count
                if obj.logical_frames == 2: s.put(CURSOR+56,0)
            obj.advance = Mock(side_effect=advance)
            result = obj.wait_committed_pose(max_frames=2)
            self.assertEqual(result['logical_frame'],2)
            self.assertEqual(obj.advance.call_count,2)
            obj.capture_timeout_boundary.assert_not_called()
            s.put(CURSOR+56,1)
            with self.assertRaises(TimeoutError): obj.wait_committed_pose(max_frames=0)
            obj.capture_timeout_boundary.assert_called_once_with()


if __name__ == '__main__': unittest.main()
