"""Execute the production scene acknowledgement; not native emulator proof."""
from pathlib import Path
import unittest
from test_scumm_actor_scene_abort import SceneAbortMachine


class SceneFenceTests(unittest.TestCase):
    def fence(self, ticket, committed, room=4, epoch=4):
        source = (Path(__file__).resolve().parents[1] /
                  'runtime/snes/engines/scumm_v5_actor_scene.inc.pasm').read_text()
        source = source[source.index('ScummV5_Scene_Render__ack_generation:'):]
        source = source[:source.index('    lda #$0000')]
        m = SceneAbortMachine(4, 1)
        m.code, m.labels = ['php', 'rep #$30'], {'entry': 0}
        for raw in source.splitlines():
            line = raw.split(';', 1)[0].strip()
            if not line or line.startswith('.'):
                continue
            if line.endswith(':'):
                m.labels[line[:-1]] = len(m.code)
            else:
                m.code.append(line)
        m.code.extend(('lda #$0001', 'sta.l accepted', 'bra exit'))
        m.labels['ScummV5_Scene_Render__stale'] = len(m.code)
        m.code.extend(('lda #$0001', 'sta.l stale'))
        m.labels['ScummV5_Scene_Render__done'] = len(m.code)
        m.labels['exit'] = len(m.code)
        m.code.extend(('plp', 'rtl'))
        m.mem.update(SAME_VIDEO_SURFACE_ROOM_GENERATION=room,
                     SAME_SCUMM_SCENE_ROOM_EPOCH=epoch,
                     SAME_SCUMM_SCENE_PRESENT=ticket & 65535,
                     SAME_VIDEO_SURFACE_NEXT_GENERATION=committed & 65535)
        m.mem['SAME_SCUMM_SCENE_PRESENT+2'] = ticket >> 16
        m.mem['SAME_VIDEO_SURFACE_NEXT_GENERATION+2'] = committed >> 16
        m.run('entry', preserve_a=False)
        return m.mem.get('accepted', 0), m.mem.get('stale', 0)

    def test_exact_and_later_overlay_generation(self):
        for ticket, committed in ((46, 46), (46, 153), (65535, 65536),
                                  (0xFFFFFFFE, 1)):
            self.assertEqual(self.fence(ticket, committed), (1, 0))

    def test_older_or_ambiguous_generation_cannot_complete(self):
        for ticket, committed in ((153, 46), (65536, 65535), (1, 0xFFFFFFFE),
                                  (1, 0x80000001)):
            self.assertEqual(self.fence(ticket, committed), (0, 0))

    def test_successor_from_replaced_room_cannot_complete(self):
        self.assertEqual(self.fence(46, 153, room=5), (0, 1))


if __name__ == '__main__':
    unittest.main()
