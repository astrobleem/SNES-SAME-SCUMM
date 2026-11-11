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

    def test_provider_only_build_owns_empty_program_include(self):
        import os
        script=(ROOT/'tools/build_snes.sh').read_text()
        block=script.split('# The provider-only client',1)[1].split('"$PYTHON" tools/generate_snes_engine_selection.py',1)[0]
        block='# The provider-only client'+block
        for enabled in ('0','1'):
            with tempfile.TemporaryDirectory() as tmp:
                out=Path(tmp)/'runtime/snes/generated/scumm_v5_msu_programs.inc.pasm'
                out.parent.mkdir(parents=True)
                for previous in (None,'; existing owned directory\n'):
                    if previous is not None:out.write_text(previous)
                    subprocess.run(['bash','-c',block],cwd=tmp,check=True,
                                   env=dict(os.environ,SAME_SNES_ENGINE='winston_io',
                                            SAME_BUILD_SCUMM_MSU1_PROGRAMS=enabled))
                    if enabled=='0':
                        self.assertEqual(out.read_text(),'; Generated empty SCUMM ProgramUnit directory (MSU programs disabled).\n')
                    elif previous is None:self.assertFalse(out.exists())
                    else:self.assertEqual(out.read_text(),previous)

if __name__=='__main__':unittest.main()
