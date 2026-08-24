from __future__ import annotations

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class EngineCliTests(unittest.TestCase):
    def run_same(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "same.cli", *arguments],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_list(self) -> None:
        result = self.run_same("engine", "list")
        self.assertEqual(result.returncode, 0, result.stderr)
        identifiers = [item["id"] for item in json.loads(result.stdout)["engines"]]
        self.assertEqual(identifiers, ["agi_v2", "scumm_v5"])

    def test_run_writes_report_and_framebuffer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            framebuffer = root / "frame.png"
            result = self.run_same(
                "engine",
                "run",
                "examples/profiles/agi_v2_conformance.json",
                "--frames",
                "3",
                "--output",
                str(report),
                "--framebuffer",
                str(framebuffer),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(report.read_text())
            self.assertEqual(data["state"]["variables"], {"20": 3})
            self.assertEqual(data["lifecycle"], "stopped")
            self.assertTrue(framebuffer.is_file())


if __name__ == "__main__":
    unittest.main()
