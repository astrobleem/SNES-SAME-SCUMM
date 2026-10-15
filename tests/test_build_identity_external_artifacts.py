import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from tools.write_build_identity import artifact_record, corpus_identity


class BuildIdentityExternalArtifactTests(unittest.TestCase):
    def test_repository_artifact_uses_relative_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "generated" / "runtime.inc"
            artifact.parent.mkdir()
            artifact.write_bytes(b"owned by this build")

            record = artifact_record(artifact, root)

        self.assertEqual(record["path"], "generated/runtime.inc")
        self.assertEqual(
            record["sha256"], hashlib.sha256(b"owned by this build").hexdigest()
        )

    def test_external_build_artifact_keeps_absolute_identity(self):
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as out_tmp:
            root = Path(root_tmp)
            artifact = Path(out_tmp) / "isolated-rom.poppy-inputs.json"
            artifact.write_bytes(b"external generated input manifest")

            record = artifact_record(artifact, root)

        self.assertEqual(record["path"], str(artifact.resolve()))
        self.assertEqual(
            record["sha256"],
            hashlib.sha256(b"external generated input manifest").hexdigest(),
        )

    def test_source_archive_identity_includes_archive_and_game_data_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "external-source.zip"
            with ZipFile(archive, "w") as bundle:
                bundle.writestr("GAME.000", b"synthetic source data")
                bundle.writestr("README.txt", b"not a game data member")

            identity = corpus_identity(str(archive))
            expected_archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()

        self.assertEqual(identity["archive_sha256"], expected_archive_sha)
        self.assertEqual(
            identity["members"],
            {"GAME.000": hashlib.sha256(b"synthetic source data").hexdigest()},
        )


if __name__ == "__main__":
    unittest.main()
