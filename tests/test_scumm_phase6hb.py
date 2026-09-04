import json, subprocess, sys, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class Phase6HBDenseGlobalsTests(unittest.TestCase):
    def test_source_derived_dense_global_contract(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            tmp_path=Path(directory); inc=tmp_path/"vars.inc"; manifest=tmp_path/"vars.json"
            subprocess.run([sys.executable,str(ROOT/"tools/generate_snes_scumm_variables.py"),
                "--archive","/home/chad/fatedemo-box.zip","--profile",str(ROOT/"examples/profiles/templates/fate_of_atlantis_demo.json"),
                "--include",str(inc),"--manifest",str(manifest)],check=True)
            data=json.loads(manifest.read_text()); text=inc.read_text()
            self.assertEqual((data["maxs_offset"],data["variable_count"]),(979,800))
            self.assertEqual((data["variable_bytes"],data["guard_bytes"]),(1600,0x9C0))
            self.assertIn("SAME_SCUMM_VARIABLES = $7E0800",text)
            self.assertIn("SAME_SCUMM_VARIABLE_END = $7E0E40",text)

    def test_dense_assembly_has_no_phase6hb_split_or_special_case(self):
        text=(ROOT/"runtime/snes/engines/scumm_v5.pasm").read_text()
        self.assertNotIn("cmp #$0078",text)
        self.assertIn(".if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB",text)
