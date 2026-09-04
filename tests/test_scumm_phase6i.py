import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Phase6ITests(unittest.TestCase):
    def test_profile_closure_adds_only_script83(self):
        profile=json.loads((ROOT/"examples/profiles/templates/fate_of_atlantis_demo.json").read_text())
        self.assertEqual(profile["options"]["snes_global_script_sets"]["phase6i"],[2,14,83,144,145,151])
    def test_script83_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable,str(ROOT/"tools/cook_scumm_v5_rooms.py"),"--archive","/home/chad/fatedemo-box.zip","--profile",str(ROOT/"examples/profiles/templates/fate_of_atlantis_demo.json"),"--rooms","49","--global-scripts","83","--executable","--output-dir",d],check=True,stdout=subprocess.DEVNULL)
            m=json.loads((Path(d)/"manifest.json").read_text()); s=m["global_scripts"][0]
            self.assertEqual((m["num_global_scripts"],s["namespace"],s["length"]),(200,"WIO_GLOBAL",45))
            self.assertEqual(s["decoded_payload_offset"],547114)
            self.assertEqual(s["sha256"],"598a8bed2a2870fba2dfe1622572608f2877fb1a9e1c172f2dd0ecd3f6f2e538")
