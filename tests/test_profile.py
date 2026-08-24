from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from same.errors import ProfileValidationError
from same.engines.scumm_v5.policy import POLICY_SCHEMA, parse_game_policy
from same.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def test_bundled_profiles_validate(self) -> None:
        scumm = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        agi = load_profile(ROOT / "examples/profiles/agi_v2_conformance.json")
        self.assertEqual(scumm.engine_id, "scumm_v5")
        self.assertEqual(agi.engine_id, "agi_v2")
        self.assertEqual(scumm.binding("script.boot").kind, "SCRP")
        self.assertEqual(agi.video.width, 160)

    def test_serialized_resource_paths_are_profile_relative(self) -> None:
        profile = load_profile(ROOT / "examples/profiles/scumm_v5_conformance.json")
        resources = profile.to_dict()["resources"]
        assert isinstance(resources, list)
        self.assertEqual(resources[0]["path"], "../resources/scumm_v5/boot.scrp")
        self.assertFalse(Path(str(resources[0]["path"])).is_absolute())

    def test_missing_required_resource_fails(self) -> None:
        source = json.loads(
            (ROOT / "examples/profiles/scumm_v5_conformance.json").read_text()
        )
        source["resources"][0]["path"] = "does-not-exist.bin"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaises(ProfileValidationError):
                load_profile(path)

    def test_unknown_input_profile_fails(self) -> None:
        source = json.loads(
            (ROOT / "examples/profiles/agi_v2_conformance.json").read_text()
        )
        source["input"]["profile"] = "made_up_controller"
        for resource in source["resources"]:
            resource["path"] = str(
                (ROOT / "examples/profiles" / resource["path"]).resolve()
            )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaises(ProfileValidationError):
                load_profile(path)

    def test_required_optional_overlap_fails(self) -> None:
        source = json.loads(
            (ROOT / "examples/profiles/scumm_v5_conformance.json").read_text()
        )
        source["capabilities"]["optional"].append("indexed8_surface")
        # Resolve the bundled resources from the temporary profile.
        for resource in source["resources"]:
            resource["path"] = str(
                (ROOT / "examples/profiles" / resource["path"]).resolve()
            )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaises(ProfileValidationError):
                load_profile(path)

    def test_monkey_template_extracts_named_policy_without_game_assets(self) -> None:
        path = ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json"
        profile = load_profile(path, verify_resources=False)
        policy = parse_game_policy(profile)
        assert policy is not None
        self.assertEqual(profile.game_id, "monkey1-ultimate-talkie")
        self.assertEqual(profile.options["policy_schema"], POLICY_SCHEMA)
        self.assertEqual((policy.index_key, policy.data_key), ("game.index", "game.data"))
        self.assertEqual(
            (policy.script_key_template, policy.room_key_template, policy.sound_key_template),
            ("script.{script}", "room.{room}", "sound.{sound}"),
        )
        self.assertEqual(
            (policy.costume_key_template, policy.charset_key_template),
            ("costume.{costume}", "charset.{charset}"),
        )
        self.assertEqual(policy.audio_source, "external")
        self.assertEqual(policy.speech_track_base, 1000)
        self.assertEqual(policy.stub_sound_policy, "not_running")
        self.assertEqual((policy.logical_width, policy.logical_height), (320, 200))
        self.assertEqual(policy.presentation, "host_viewport")
        self.assertEqual(policy.cursor_policy, "engine_default")
        self.assertEqual(policy.copy_protection_mode, "bypass")
        self.assertEqual(
            (policy.copy_protection_script, policy.copy_protection_variable, policy.copy_protection_answer),
            (155, 105, -100),
        )
        self.assertEqual(
            sorted(profile.quirks),
            [
                "monkey1.cd.silent_sound_stubs",
                "monkey1.snes.script_patch_manifest",
                "monkey1.ultimate_talkie.voice_offsets",
            ],
        )

    def test_monkey_template_fails_when_user_resources_are_missing(self) -> None:
        path = ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json"
        with self.assertRaisesRegex(ProfileValidationError, r"required resource 'game.index'"):
            load_profile(path)

    def test_fate_demo_profile_uses_embedded_audio_and_font_resources(self) -> None:
        path = ROOT / "examples/profiles/templates/fate_of_atlantis_demo.json"
        profile = load_profile(path, verify_resources=False)
        policy = parse_game_policy(profile)
        assert policy is not None
        self.assertEqual(profile.game_id, "indy4-fate-demo")
        self.assertEqual(policy.audio_source, "embedded")
        self.assertIsNone(policy.sound_map_key)
        self.assertIsNone(policy.speech_archive_key)
        self.assertIsNone(policy.speech_index_key)
        self.assertEqual(policy.costume_key_template, "costume.{costume}")
        self.assertEqual(policy.charset_key_template, "charset.{charset}")
        self.assertEqual(profile.quirks, {"indy4.demo.save_menu_disabled": True})

    def test_monkey_policy_validates_with_supplied_resource_layout(self) -> None:
        source = json.loads(
            (ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json").read_text()
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for binding in source["resources"]:
                binding["path"] = binding["key"].replace(".", "_") + ".bin"
                if binding.get("required", True):
                    (root / binding["path"]).write_bytes(b"fixture")
            path = root / "monkey.json"
            path.write_text(json.dumps(source))
            policy = parse_game_policy(load_profile(path))
            self.assertIsNotNone(policy)

    def test_scumm_policy_rejects_unbound_keys_and_custom_cursor_policy(self) -> None:
        source = json.loads(
            (ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json").read_text()
        )
        source["resources"] = [
            binding for binding in source["resources"] if binding["key"] != "audio.sound_map"
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            profile = load_profile(path, verify_resources=False)
            with self.assertRaisesRegex(ProfileValidationError, r"unbound resource 'audio.sound_map'"):
                parse_game_policy(profile)

        source = json.loads(
            (ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json").read_text()
        )
        source["options"]["coordinate_policy"]["cursor_policy"] = "monkey_custom"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ProfileValidationError, r"cursor_policy must be 'engine_default'"):
                parse_game_policy(load_profile(path, verify_resources=False))

        source = json.loads(
            (ROOT / "examples/profiles/templates/monkey1_ultimate_talkie.json").read_text()
        )
        source["quirks"] = {"compat_mode": True}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ProfileValidationError, r"narrow, namespaced"):
                parse_game_policy(load_profile(path, verify_resources=False))


if __name__ == "__main__":
    unittest.main()
