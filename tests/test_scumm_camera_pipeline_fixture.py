"""The public fixture reproduces the source used by the native camera control."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile
from examples.resources.scumm_v5.camera_pipeline_fixture import source_files, write_archive


class CameraFixtureTests(unittest.TestCase):
    def test_independent_archives_are_deterministic_and_preserve_declared_members(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = (Path(directory) / name for name in ('a.zip', 'b.zip'))
            write_archive(a)
            write_archive(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                self.assertEqual({n: archive.read(n) for n in archive.namelist()}, source_files())
            with self.assertRaises(FileExistsError):
                write_archive(a)

    def test_native_source_member_identities(self):
        expected = {
            'ATLANTIS/ATLANTIS.000': 'f9cce2f7c4400fa0403c6ceb2ef2f833b4456801bc6b2c0ea9e811c92053a6c1',
            'ATLANTIS/ATLANTIS.001': '9027375061d10622754019b8e1b37a220eebbabbd70341b01cce9fccc9b9c5b2',
        }
        self.assertEqual({n: hashlib.sha256(v).hexdigest() for n, v in source_files().items()}, expected)
