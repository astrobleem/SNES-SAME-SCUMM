import unittest
from pathlib import Path

from same.donors import DONORS, donor_paths


class DonorTests(unittest.TestCase):
    def test_platform_specific_defaults(self) -> None:
        bor = DONORS["bor"]
        self.assertEqual(bor.default_path(platform="posix", environ={}), Path("/home/chad/snes-bor"))
        self.assertEqual(bor.default_path(platform="nt", environ={}), Path(r"E:\gh\snes-bor"))

    def test_environment_override(self) -> None:
        bor = DONORS["bor"]
        self.assertEqual(
            bor.default_path(
                platform="nt", environ={"SAME_DONOR_BOR_PATH": r"D:\work\bor"}
            ),
            Path(r"D:\work\bor"),
        )

    def test_explicit_path_map_wins(self) -> None:
        paths = donor_paths({"bor": Path("/tmp/bor")})
        self.assertEqual(paths["bor"], Path("/tmp/bor"))


if __name__ == "__main__":
    unittest.main()
