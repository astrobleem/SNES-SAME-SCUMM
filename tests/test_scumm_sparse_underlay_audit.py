"""Fail-closed audit migration: sparse API and nested palette owners."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tools import audit_scumm_residency_wram as audit


class SparseUnderlayAuditTests(unittest.TestCase):
    def test_palette_owners_are_reported_separately_and_before_save(self):
        report = audit.audit()
        rows = report['bwram_protected_low_owners']
        self.assertEqual([(r['name'],r['start'],r['end_exclusive'],r['bytes']) for r in rows], [
            ('room_palette_base','$400000','$400300',768),
            ('room_palette_desired','$400300','$400600',768),
            ('room_palette_state','$400600','$400620',32),
            ('cursor_underlay','$400620','$400740',288),
            ('cursor_presentation','$400740','$400780',64)])
        self.assertTrue(all(r['disjoint_from_save'] for r in rows))
        self.assertEqual(report['bwram_save_reserved'],
                         {'start':'$400800','end_exclusive':'$401000','bytes':2048})

    def test_carrier_validation_rejects_nested_overlap_and_save_intrusion(self):
        path = audit.ROOT / 'runtime/snes/carriers/sa1_bwram_layout.json'
        original = Path.read_text
        for offset in (0,2048):
            layout = json.loads(original(path))
            layout['protected_low']['allocations']['room_palette_state']['offset'] = offset
            def replacement(file, *args, **kwargs):
                return json.dumps(layout) if file == path else original(file,*args,**kwargs)
            with patch.object(Path, 'read_text', replacement):
                with self.assertRaisesRegex(ValueError,'palette allocation'):
                    audit.audit()

    def test_cursor_owners_reject_overlap_and_save_intrusion(self):
        path = audit.ROOT / 'runtime/snes/carriers/sa1_bwram_layout.json'
        original = Path.read_text
        for name, offset, size in [('cursor_underlay',1536,288),
                                   ('cursor_underlay',1568,481),
                                   ('cursor_presentation',1800,64),
                                   ('cursor_presentation',2048,64)]:
            layout=json.loads(original(path))
            layout['protected_low']['allocations'][name].update(offset=offset,bytes=size)
            def replacement(file,*args,**kwargs):
                return json.dumps(layout) if file==path else original(file,*args,**kwargs)
            with patch.object(Path,'read_text',replacement), self.assertRaises(ValueError):
                audit.audit()

    def test_obsolete_capture_api_cannot_satisfy_audit(self):
        path = audit.ROOT / 'runtime/snes/services/video_surface.pasm'
        original = Path.read_text
        changed = original(path).replace('Same_VideoSurface_CaptureActorRun_Far:',
                                         'Same_VideoSurface_CaptureActorUnderlay_Far:')
        def replacement(file,*args,**kwargs):
            return changed if file == path else original(file,*args,**kwargs)
        with patch.object(Path,'read_text',replacement):
            with self.assertRaisesRegex(ValueError,'sparse actor underlay API missing'):
                audit.audit()


if __name__ == '__main__':
    unittest.main()
