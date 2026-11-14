"""Original v5 room hook order, using copyright-free executable bodies."""
import unittest

import test_scumm_v5_engine as oracle


def word(n):
    return n.to_bytes(2, 'little')


def setvar(n, value):
    return b'\x1a' + word(n) + word(value)


def copyvar(n, source):
    return b'\x9a' + word(n) + word(source)


class RoomHookTests(unittest.TestCase):
    def host(self, body, scripts=None, entry=b'\0', exit=b'\0'):
        resources = oracle._cooked_room_resources(
            1, oracle.room_with_load_ego_entry(entry, object_id=100, exit_script=exit))
        resources.update(oracle._cooked_room_resources(
            2, oracle.room_with_load_ego_entry(entry, object_id=101)))
        return oracle.ScummV5EngineTests()._host(body, scripts=scripts, resources=resources)

    def test_before_body_after_order_and_old_room_identity(self):
        # Install the hooks only after the first room is active.
        body = b'\x72\x01' + b''.join(setvar(v, n) for v, n in
            [(30, 10), (31, 11), (28, 12), (29, 13)]) + b'\x72\x02\0'
        scripts = {
            10: copyvar(110, 4) + setvar(100, 1) + b'\0',
            11: copyvar(102, 100) + setvar(100, 3) + b'\0',
            12: copyvar(103, 100) + copyvar(111, 4) + setvar(100, 4) + b'\0',
            13: copyvar(105, 100) + setvar(100, 6) + b'\0',
        }
        h = self.host(body, scripts,
            entry=copyvar(104, 100) + setvar(100, 5) + b'\0',
            exit=copyvar(101, 100) + setvar(100, 2) + b'\0')
        h.tick()
        self.assertEqual(h.engine.state.current_room, 2)
        self.assertEqual([h.engine.state.variables[n] for n in range(100, 106)],
                         [6, 1, 2, 3, 4, 5])
        self.assertEqual([h.engine.state.variables[n] for n in (110, 111)], [1, 2])
        events = [e for e in h.engine.inspect_room_lifecycle()
                  if e['phase'] == 'room_hook_scheduled']
        self.assertEqual([(e['variable'], e['room']) for e in events],
                         [(30, 1), (31, 1), (28, 2), (29, 2)])

    def test_yielded_global_survives_and_receives_zero_locals(self):
        body = b'\x72\x01' + setvar(30, 10) + b'\x72\x02\x80\0'
        h = self.host(body, {10: copyvar(100, 0x4000) + b'\x80' + setvar(101, 9) + b'\0'})
        h.tick()
        self.assertEqual(h.engine.state.current_room, 2)
        self.assertEqual(h.engine.state.variables[100], 0)
        self.assertEqual(h.engine.state.variables[101], 0)
        self.assertTrue(any(s.number == 10 and s.active and s.room is None
                            for s in h.engine.state.scripts))
        h.tick()
        self.assertEqual(h.engine.state.variables[101], 9)

    def test_hooks_are_read_at_each_boundary_and_can_start_nested_scripts(self):
        body = b'\x72\x01' + setvar(30, 10) + b'\x72\x02\0'
        h = self.host(body, {
            10: setvar(31, 11) + b'\x0a\x0c\xff\0',
            11: setvar(100, 42) + b'\0',
            12: setvar(101, 43) + b'\0',
        })
        h.tick()
        self.assertEqual(h.engine.state.variables[100:102], [42, 43])

    def test_null_room_runs_exit_hooks_but_no_entry_hooks(self):
        body = b'\x72\x01' + b''.join(setvar(v, n) for v, n in
            [(30, 10), (31, 11), (28, 12), (29, 13)]) + b'\x72\x00\0'
        # The standard helper binds synthetic room0. Remove that resource so
        # this is the source-less null scene rather than a synthetic ROOM.
        resources = oracle._cooked_room_resources(
            1, oracle.room_with_load_ego_entry(b'\0', object_id=100))
        h = oracle.ScummV5EngineTests()._host(body, include_room_zero=False,
            scripts={n: setvar(100+n, 1)+b'\0' for n in (10,11,12,13)}, resources=resources)
        h.tick()
        self.assertEqual(h.engine.state.current_room, 0)
        self.assertEqual(h.engine.state.variables[110:114], [1, 1, 0, 0])

    def test_invalid_hook_does_not_fall_back_or_install_destination(self):
        h = self.host(b'\x72\x01' + setvar(30, 256) + b'\x72\x02\0')
        with self.assertRaisesRegex(oracle.EngineExecutionError, 'invalid script 256'):
            h.tick()
        self.assertEqual(h.engine.state.current_room, 1)
        self.assertNotEqual(h.lifecycle.value, 'running')


if __name__ == '__main__':
    unittest.main()
