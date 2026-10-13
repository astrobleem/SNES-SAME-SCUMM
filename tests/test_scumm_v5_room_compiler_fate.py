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
from same.engines.scumm_v5.room_compiler import profile_game_identity
from same.engines.scumm_v5.cooked_room import decode_cooked_room
from same.profile import load_profile


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = os.environ.get("SAME_SCUMM_SOURCE_ARCHIVE")
DOS_CD_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_dos_cd.json"
LEGACY_DEMO_PROFILE = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
LEGACY_DEMO_SC5C_SHA256 = "4aa17fc06b79aaa62fa00a07ef999b1ced523ef989b2f6c2ff08fce76501bcb2"


@unittest.skipUnless(ARCHIVE, "set SAME_SCUMM_SOURCE_ARCHIVE for external FATE integration")
class FateRoom7CompilerIntegrationTests(unittest.TestCase):
    def test_canonical_dos_cd_room7_compiles_with_provenance_and_dependencies(self) -> None:
        archive = Path(ARCHIVE)  # type: ignore[arg-type]
        self.assertTrue(archive.is_file(), f"configured source archive is missing: {archive}")
        self.assertTrue(DOS_CD_PROFILE.is_file(), f"canonical profile is missing: {DOS_CD_PROFILE}")
        profile = load_profile(DOS_CD_PROFILE, verify_resources=False)
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
                     "--archive", str(archive), "--profile", str(DOS_CD_PROFILE),
                     "--room", "7", "--output-dir", str(destination),
                     "--snes-backend", "--far-programs"],
                    cwd=ROOT, env=env, check=True, capture_output=True, text=True,
                )
            first_files = {item.relative_to(output): item.read_bytes()
                           for item in output.rglob("*") if item.is_file()}
            repeat_files = {item.relative_to(repeat): item.read_bytes()
                            for item in repeat.rglob("*") if item.is_file()}

            file_sets_equal = set(first_files) == set(repeat_files)
            differences = []
            for relative_path in sorted(set(first_files) | set(repeat_files), key=str):
                first = first_files.get(relative_path)
                second = repeat_files.get(relative_path)
                if first != second:
                    differences.append({
                        "path": relative_path.as_posix(),
                        "first_sha256": None if first is None else hashlib.sha256(first).hexdigest(),
                        "second_sha256": None if second is None else hashlib.sha256(second).hexdigest(),
                    })
            determinism = {
                "schema": "same_scumm_room_compiler_determinism_v1",
                "runs": 2,
                "file_sets_equal": file_sets_equal,
                "content_equal": file_sets_equal and not differences,
                "differences": differences,
            }
            report_path = os.environ.get("SAME_SCUMM_ROOM_COMPILER_DETERMINISM_REPORT")
            if report_path:
                report = Path(report_path)
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(json.dumps(determinism, indent=2, sort_keys=True) + "\n")
            self.assertTrue(determinism["file_sets_equal"])
            self.assertTrue(determinism["content_equal"])
            self.assertEqual(first_files, repeat_files)
            manifest = json.loads((output / "manifest.json").read_text())
            ir = json.loads((output / "room-7.ir.json").read_text())
            analysis = json.loads((output / "room-7.analysis.json").read_text())

            expected_game = f"{profile.game_id}:{profile.variant}"
            self.assertEqual(profile.game_id, "indy4-fate-dos-cd-en")
            self.assertEqual(profile.variant, "DOS CD English, full voice (1993)")
            self.assertEqual(manifest["profile"]["game"], profile.game_id)
            self.assertEqual(manifest["profile"]["variant"], profile.variant)
            self.assertEqual(manifest["profile"]["sha256"],
                             hashlib.sha256(DOS_CD_PROFILE.read_bytes()).hexdigest())
            self.assertEqual(manifest["profile"]["identity_sha256"],
                             profile_game_identity(profile))
            self.assertEqual({item["source"]["game"] for item in ir["scripts"]},
                             {expected_game})

            record = manifest["records"][0]
            decode_cooked_room(
                (output / record["output"]).read_bytes(), expected_room=7,
                expected_profile_sha256=manifest["profile"]["sha256"],
                expected_game_identity_sha256=manifest["profile"]["identity_sha256"],
            )
            self.assertEqual(ir["room_sha256"],
                             "58cf45c4d2bd15cea5c4a3606003bdd6907d9586eb4864e0b672707ef18b269a")
            self.assertEqual(ir["source_member"], "ATLANTIS/ATLANTIS.001")
            self.assertEqual(ir["source_container_offset"], 730022)
            self.assertEqual(ir["room_source_offset"], 730038)
            self.assertEqual(record["original_room_sha256"], ir["room_sha256"])
            dos_cd_sc5c_sha = hashlib.sha256((output / record["output"]).read_bytes()).hexdigest()
            self.assertEqual(dos_cd_sc5c_sha, record["record_sha256"])
            self.assertNotEqual(dos_cd_sc5c_sha, LEGACY_DEMO_SC5C_SHA256,
                                "canonical DOS-CD provenance must not retain the demo-profile header")

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

            opaque_object_verbs = {
                identity: next(item for item in script["instructions"]
                               if item["operation"] == "opaque_bytecode_tail")["pc"]
                for identity, script in scripts.items()
                if identity.startswith("room.7/object.") and script["opaque_from_pc"] is not None
            }
            expected_opaque_object_verbs = {
                "room.7/object.112/verb.8": 146,
                "room.7/object.116/verb.10": 107,
                "room.7/object.117/verb.10": 107,
                "room.7/object.118/verb.10": 107,
                "room.7/object.119/verb.10": 107,
                "room.7/object.133/verb.11": 301,
                "room.7/object.130/verb.10": 99,
                "room.7/object.127/verb.3": 56,
                "room.7/object.127/verb.4": 113,
            }
            self.assertEqual(opaque_object_verbs, expected_opaque_object_verbs)
            for identity, instruction_pc in opaque_object_verbs.items():
                self.assertEqual(scripts[identity]["opaque_from_pc"], instruction_pc)

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

    def test_legacy_demo_profile_sc5c_compatibility_is_not_canonical_provenance(self) -> None:
        archive = Path(ARCHIVE)  # type: ignore[arg-type]
        self.assertTrue(archive.is_file(), f"configured source archive is missing: {archive}")
        with tempfile.TemporaryDirectory() as temp_name:
            output = Path(temp_name) / "legacy-demo-room7"
            env = dict(os.environ)
            env["PYTHONPATH"] = "src"
            # Recreate the historical profile/header pairing only to retain its
            # byte-compatibility check. This output is not canonical provenance
            # for the full DOS-CD archive.
            subprocess.run(
                [sys.executable, str(ROOT / "tools/compile_scumm_room.py"),
                 "--archive", str(archive), "--profile", str(LEGACY_DEMO_PROFILE),
                 "--room", "7", "--output-dir", str(output)],
                cwd=ROOT, env=env, check=True, capture_output=True, text=True,
            )
            manifest = json.loads((output / "manifest.json").read_text())
            ir = json.loads((output / "room-7.ir.json").read_text())
            record = manifest["records"][0]
            self.assertEqual(manifest["profile"]["game"], "indy4-fate-demo")
            self.assertEqual(manifest["profile"]["variant"], "dos-vga-en-1992-07-09")
            self.assertEqual({item["source"]["game"] for item in ir["scripts"]},
                             {"indy4-fate-demo:dos-vga-en-1992-07-09"})
            self.assertEqual(hashlib.sha256((output / record["output"]).read_bytes()).hexdigest(),
                             LEGACY_DEMO_SC5C_SHA256)


if __name__ == "__main__":
    unittest.main()
