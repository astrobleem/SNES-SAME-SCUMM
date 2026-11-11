"""Non-SCUMM backend controls must not link an unused interpreter closure."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class NativeEngineLinkSelectionTests(unittest.TestCase):
    def test_engine_flag_is_owned_by_selected_binding(self):
        for engine in ('demo','mode3_surface_conformance','winston_io','scumm_v5'):
            with self.subTest(engine=engine), tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)/'active_engine.inc.pasm'
                subprocess.run([sys.executable,str(ROOT/'tools/generate_snes_engine_selection.py'),
                    '--engine',engine,'--output',str(out)]+(['--msu1-storage'] if engine=='winston_io' else []),check=True,capture_output=True)
                config=(out.parent/'build_config.inc.pasm').read_text()
                self.assertIn('SAME_BUILD_SCUMM_ENGINE = $'+('01' if engine=='scumm_v5' else '00'),config)
        source=(ROOT/'runtime/snes/main.pasm').read_text()
        self.assertIn('.if SAME_BUILD_SCUMM_ENGINE\n.include "engines/scumm_v5.pasm"\n.endif',source)

if __name__=='__main__':unittest.main()
