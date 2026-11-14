"""Source classes must survive the compiler seam; no proprietary input."""
import contextlib
import hashlib
import io
import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from examples.resources.scumm_v5.actor_scene_fixture import write_archive
from tools.cook_scumm_v5_rooms import main as cook
from tools.generate_snes_cooked_rooms import main as generate

ROOT=Path(__file__).resolve().parents[1]

class SourceClassCookingTests(unittest.TestCase):
    def test_complete_default_table_is_declared_hashed_and_not_truncated(self):
        with patch('sys.path',[str(ROOT/'tools'),*sys.path]), tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);archive=root/'source.zip';write_archive(archive,hit_test_probe=True)
            output=root/'cooked'
            with patch('sys.argv',['cook','--archive',str(archive),'--profile',str(ROOT/'examples/profiles/scumm_v5_game_analysis_fixture.json'),'--all-source-executables','--executable','--output-dir',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cook(),0)
            manifest=output/'manifest.json';doc=json.loads(manifest.read_text());spec=doc['global_objects']
            raw=(output/spec['classes_output']).read_bytes()
            self.assertEqual(len(raw),4096)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),spec['classes_sha256'])
            self.assertEqual(int.from_bytes(raw[900*4:901*4],'little'),0x80000001)
            args=['generate','--manifest',str(manifest),'--output',str(root/'rooms.pasm'),'--data-output',str(root/'data.pasm'),'--binary-dir',str(root/'segments'),'--far-programs','--pack-source-tables']
            with patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(generate(),0)
            self.assertIn('ScummV5_ObjectClass_InitialCount = $0400',(root/'data.pasm').read_text())
            (output/spec['classes_output']).write_bytes(bytes(len(raw)))
            with patch('sys.argv',args),self.assertRaisesRegex(RuntimeError,'class checksum'):
                generate()
            del doc['global_objects']['classes_output'];manifest.write_text(json.dumps(doc))
            with patch('sys.argv',args),self.assertRaisesRegex(RuntimeError,'omits initial object classes'):
                generate()
