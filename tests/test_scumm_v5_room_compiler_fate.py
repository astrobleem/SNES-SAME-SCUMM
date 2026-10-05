from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from same.engines.scumm_v5.room_compiler import compiler_source_manifest, compiler_source_sha256


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = os.environ.get("SAME_SCUMM_SOURCE_ARCHIVE")
PROFILE = Path(os.environ.get(
    "SAME_SCUMM_SOURCE_PROFILE",
    str(ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"),
))


@unittest.skipUnless(ARCHIVE, "set SAME_SCUMM_SOURCE_ARCHIVE for external FATE integration")
class FateRoom7CompilerIntegrationTests(unittest.TestCase):
    def test_authentic_room7_compiles_with_provenance_dependencies_and_legacy_bytes(self) -> None:
        archive = Path(ARCHIVE)  # type: ignore[arg-type]
        self.assertTrue(archive.is_file(), f"configured source archive is missing: {archive}")
        self.assertTrue(PROFILE.is_file(), f"configured profile is missing: {PROFILE}")
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            env = dict(os.environ)
            # Deliberately use a cwd-relative path: the CLI's backend subprocess
            # changes directory and must normalize this import path first.
            env["PYTHONPATH"] = "src"
            output, repeat = temp / "first", temp / "repeat"
            for destination in (output, repeat):
                subprocess.run(
                    [sys.executable, str(ROOT / "tools/compile_scumm_room.py"),
                     "--archive", str(archive), "--profile", str(PROFILE),
                     "--room", "7", "--output-dir", str(destination),
                     "--snes-backend", "--far-programs"],
                    cwd=ROOT, env=env, check=True, capture_output=True, text=True,
                )
            first_files = {item.relative_to(output): item.read_bytes()
                           for item in output.rglob("*") if item.is_file()}
            repeat_files = {item.relative_to(repeat): item.read_bytes()
                            for item in repeat.rglob("*") if item.is_file()}
            self.assertEqual(first_files, repeat_files)
            manifest = json.loads((output / "manifest.json").read_text())
            ir = json.loads((output / "room-7.ir.json").read_text())
            analysis = json.loads((output / "room-7.analysis.json").read_text())

            record = manifest["records"][0]
            self.assertEqual(ir["room_sha256"],
                             "58cf45c4d2bd15cea5c4a3606003bdd6907d9586eb4864e0b672707ef18b269a")
            self.assertEqual(ir["source_member"], "ATLANTIS/ATLANTIS.001")
            self.assertEqual(ir["source_container_offset"], 730022)
            self.assertEqual(ir["room_source_offset"], 730038)
            self.assertEqual(record["original_room_sha256"], ir["room_sha256"])
            self.assertEqual(
                hashlib.sha256((output / record["output"]).read_bytes()).hexdigest(),
                # The cooker/compiler adapter must retain exact legacy SC5C bytes.
                "4aa17fc06b79aaa62fa00a07ef999b1ced523ef989b2f6c2ff08fce76501bcb2",
            )

            scripts = {item["identity"]: item for item in ir["scripts"]}
            local_scripts = [item for item in ir["scripts"] if item["identity"].startswith("room.7/LSCR.")]
            self.assertEqual({item["kind"] for item in local_scripts}, {"LSCR"})
            expected_scripts = {
                "room.7/ENCD": (778827, "339b0e605941eaee59bb95c8c9e7a8195c44ad7ff8f363554796fb749055aa8d"),
                "room.7/EXCD": (778782, "dd94e4b228fd5f64e1582da091279634b94ddc4183deb33b4a9ce169048b21c9"),
                "room.7/LSCR.201": (779853, "6a3565652f8d72261d357eb6ef0d497a0a15448f15a6842d6afd22f7a8eda752"),
                "room.7/LSCR.207": (780810, "8aaee88643be64efdc3b8826b4ff7569517e7493b658ad596a09eb29ad41cc6f"),
            }
            for identity, (offset, digest) in expected_scripts.items():
                self.assertEqual(scripts[identity]["source"]["source_offset"], offset)
                self.assertEqual(scripts[identity]["source"]["source_sha256"], digest)

            objects = {item["object_id"]: item for item in ir["objects"]}
            self.assertEqual(objects[118]["obcd_sha256"],
                             "4ed263b154cc3b39937b95c69f863f909fb686428bd19e1335b9761153700466")
            self.assertEqual(objects[119]["obcd_sha256"],
                             "540496ef75dd3037d5d82debb4d9df1e63256dfdaa1116773dd7094fcb41bd19")

            operations = []
            for identity in ("room.7/object.118/verb.10", "room.7/object.119/verb.10"):
                operations.extend(scripts[identity]["instructions"])
            calls = {
                (instruction["operation"],
                 instruction["operands"].get("script", {}).get("value"))
                for instruction in operations
            }
            self.assertIn(("start_script", 207), calls)
            self.assertIn(("chain_script", 201), calls)
            self.assertIn("bit:69", analysis["state_reads"])
            local_201_edges = [
                item for item in analysis["static_dependencies"]
                if item["kind"] == "script" and item["target"] == 201
                and item["source_script"].startswith("room.7/object.")
            ]
            self.assertTrue(local_201_edges)
            self.assertEqual({item["resolution"] for item in local_201_edges}, {"resolved"})
            room3_placement = [
                item for item in analysis["static_dependencies"]
                if item["kind"] == "actor-placement" and item["target"] == 3
                and item["source_script"] == "room.7/LSCR.201"
            ]
            self.assertTrue(room3_placement)
            room3_source = scripts["room.7/LSCR.201"]
            self.assertTrue(room3_source["decode_complete"])
            room3_operations = {item["operation"] for item in room3_source["instructions"]}
            self.assertIn("put_actor_in_room", room3_operations)
            self.assertIn("actor_follow_camera", room3_operations)
            follow_transition = [
                item for item in analysis["dynamic_dependencies"]
                if item["kind"] == "room-transition"
                and item["source_script"] == "room.7/LSCR.201"
            ]
            self.assertTrue(follow_transition)
            self.assertTrue(analysis["decode_incomplete_scripts"],
                            "the report must preserve the bounded decoder's partial status")
            self.assertEqual(analysis["status"], "partial")
            self.assertEqual(manifest["compiler"]["source_sha256"], compiler_source_sha256())
            self.assertEqual(manifest["compiler"]["source_components"], compiler_source_manifest())
            self.assertEqual(manifest["compiler"]["cli_sha256"],
                             hashlib.sha256((ROOT / "tools/compile_scumm_room.py").read_bytes()).hexdigest())
            self.assertEqual(manifest["compiler"]["snes_backend_sha256"],
                             hashlib.sha256((ROOT / "tools/generate_snes_cooked_rooms.py").read_bytes()).hexdigest())

            backend_report = output / "snes-backend/report.json"
            program_map = json.loads(backend_report.read_text())["program_map"]
            identities = {item["identity"] for item in program_map}
            self.assertTrue({"room.7/LSCR.201", "room.7/LSCR.207",
                             "room.7/object.118/OBCD", "room.7/object.119/OBCD"}
                            <= identities)
            backend_artifacts = json.loads(
                (output / "snes-backend/backend-artifacts.json").read_text()
            )["files"]
            artifact_by_path = {item["path"]: item for item in backend_artifacts}
            for item in backend_artifacts:
                path = output / "snes-backend" / item["path"]
                self.assertEqual(item["size"], path.stat().st_size)
                self.assertEqual(item["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertIn("report.json", artifact_by_path)


if __name__ == "__main__":
    unittest.main()
