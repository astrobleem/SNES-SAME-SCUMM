"""Actual observer wait method against a paused fake session; no native runs."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import validate_scumm_actor_visual_probe_nexen as probe


def scene(frame, composing=0):
    pose = bytearray(128)
    pose[3], pose[4], pose[7], pose[0x6B] = 6, 2, 2, 1
    pose[0x6C], pose[0x6E] = 117, 138
    state = dict(logical_frame=frame, room=4, lifecycle=2, error=0,
                 actor_render_valid=1, actor_render_pose_frame=6,
                 actor_render_pose_step=0, actor_render_generation=2,
                 actor_render_facing=180, surface_next_generation=53,
                 backend_pending_generation=53, backend_committed_generation=53,
                 backend_pending_generation_hi=0, backend_committed_generation_hi=0,
                 mode3_state=1, mode3_surface_locked=0, surface_pending_visual=0,
                 surface_presented_room=4, surface_packets_pending=False,
                 composition_active=composing, actor_pose_bytes=list(pose))
    return state


class PausedSession:
    def __init__(self, observer):
        self.observer = observer

    def read_memory(self, kind, address, length):
        assert (kind, address, length) == ('snesMemory', probe.ACTOR_STATE, 128)
        return bytes(self.observer.last_state['actor_pose_bytes'])


def observer(states):
    obj = probe.ProbeObserver.__new__(probe.ProbeObserver)
    obj.logical_frames = 0
    obj.last_state = states[0].copy()
    obj.session = PausedSession(obj)
    def read():
        obj.last_state = states[obj.logical_frames].copy()
        return obj.last_state
    def advance(count):
        obj.logical_frames += count
        return read()
    obj.read_scene = Mock(side_effect=read)
    obj.advance = Mock(side_effect=advance)
    obj.capture_timeout_boundary = Mock()
    return obj


class PresentedPoseObserverTests(unittest.TestCase):
    def test_ready_only_at_exact_budget_endpoint_is_returned(self):
        obj = observer({0: scene(0, 1), 10: scene(10)})
        result = obj.wait_presented_pose(max_frames=10, expected_frame=6,
                                          expected_facing=180, expected_x=117)
        self.assertEqual(result['logical_frame'], 10)
        obj.advance.assert_called_once_with(10)
        obj.capture_timeout_boundary.assert_not_called()
        self.assertEqual(result['presentation_fence'], 'mode3-committed-paused-state')

    def test_ready_now_is_not_discarded_by_future_composition(self):
        obj = observer({0: scene(0), 1: scene(1, 1)})
        result = obj.wait_presented_pose(max_frames=10)
        self.assertEqual(result['logical_frame'], 0)
        obj.advance.assert_not_called()
        obj.capture_timeout_boundary.assert_not_called()

    def test_terminal_composition_still_times_out_without_budget_overrun(self):
        obj = observer({0: scene(0, 1), 10: scene(10, 1)})
        with self.assertRaises(TimeoutError):
            obj.wait_presented_pose(max_frames=10)
        obj.advance.assert_called_once_with(10)
        obj.capture_timeout_boundary.assert_called_once_with()
        self.assertEqual(obj.last_state['composition_active'], 1)
        self.assertEqual(obj.logical_frames, 10)

    def test_persisted_samples_keep_backend_fence_and_progress_counters(self):
        obj = observer({0: scene(0)})
        state = obj.last_state
        state.update(probe.decode_backend_progress(bytes(range(64))))
        state.update(stage=None, pc=None, provider_bytes=[0]*128,
                     surface_presented_generation_stale=0, mode3_last_status=3,
                     mode3_pending_count=4, mode3_inflight_count=5, event_count=6)
        obj.progress = []
        obj.evidence_kind = 'fake-session regression'
        with tempfile.TemporaryDirectory() as directory:
            obj.output = Path(directory)
            obj._persist_progress_sample(state)
            sample = json.loads((obj.output/'actor-progress.json').read_text())['samples'][0]
        for key in state:
            if key.startswith(('backend_', 'mode3_')) and key != 'mode3_control_bytes':
                self.assertEqual(sample[key], state[key], key)
        for key in ('event_count', 'surface_packets_pending', 'surface_pending_visual',
                    'surface_presented_room', 'composition_active'):
            self.assertEqual(sample[key], state[key], key)


if __name__ == '__main__':
    unittest.main()
