"""Validated game-policy boundary for SCUMM v5 profiles.

This module names resource and compatibility choices without implementing any
game's behavior.  Resource decoders and service adapters consume the policy;
the opcode core remains game-neutral.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from ...errors import ProfileValidationError
from ...profile import EngineProfile

POLICY_SCHEMA = "scumm_v5_game_policy_v1"
_RAW_FORMATS = {"cooked", "lucasarts_scumm_v5"}
_AUDIO_SOURCES = {"external", "embedded"}
_COPY_PROTECTION_MODES = {"preserve", "bypass"}
_STUB_SOUND_POLICIES = {"not_running", "virtual_running"}


def _mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ProfileValidationError(f"SCUMM option {name} must be an object")
    return value


def _text(block: Mapping[str, Any], key: str, name: str) -> str:
    value = block.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileValidationError(f"SCUMM option {name}.{key} must be a non-empty string")
    return value


def _integer(block: Mapping[str, Any], key: str, name: str) -> int:
    value = block.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProfileValidationError(f"SCUMM option {name}.{key} must be an integer")
    return value


def _binding(profile: EngineProfile, key: str, field_name: str) -> None:
    try:
        profile.binding(key)
    except KeyError as exc:
        raise ProfileValidationError(
            f"SCUMM option {field_name} names unbound resource {key!r}"
        ) from exc


@dataclass(frozen=True, slots=True)
class ScummV5GamePolicy:
    resource_format: str
    index_key: str
    data_key: str
    script_key_template: str
    room_key_template: str
    sound_key_template: str
    costume_key_template: str
    charset_key_template: str
    audio_source: str
    sound_map_key: str | None
    speech_archive_key: str | None
    speech_index_key: str | None
    script_patch_manifest_key: str | None
    speech_track_base: int
    stub_sound_policy: str
    logical_width: int
    logical_height: int
    presentation: str
    cursor_policy: str
    copy_protection_mode: str
    copy_protection_script: int | None
    copy_protection_variable: int | None
    copy_protection_answer: int | None


def parse_game_policy(profile: EngineProfile) -> ScummV5GamePolicy | None:
    """Parse the optional structured policy block used by extracted games.

    The small cooked conformance profile predates this schema and intentionally
    remains valid.  Extracted raw-data profiles opt in explicitly.
    """
    schema = profile.options.get("policy_schema")
    if schema is None:
        return None
    if schema != POLICY_SCHEMA:
        raise ProfileValidationError(
            f"unsupported SCUMM policy_schema {schema!r}; expected {POLICY_SCHEMA!r}"
        )

    resources = _mapping(profile.options.get("resource_policy"), "resource_policy")
    audio = _mapping(profile.options.get("audio_policy"), "audio_policy")
    coordinates = _mapping(profile.options.get("coordinate_policy"), "coordinate_policy")
    copy_protection = _mapping(
        profile.options.get("copy_protection_policy"), "copy_protection_policy"
    )

    resource_format = _text(resources, "format", "resource_policy")
    if resource_format not in _RAW_FORMATS:
        raise ProfileValidationError(f"unsupported SCUMM resource format {resource_format!r}")
    index_key = _text(resources, "index_key", "resource_policy")
    data_key = _text(resources, "data_key", "resource_policy")
    script_key_template = _text(resources, "script_key_template", "resource_policy")
    room_key_template = _text(resources, "room_key_template", "resource_policy")
    sound_key_template = _text(resources, "sound_key_template", "resource_policy")
    costume_key_template = str(
        resources.get("costume_key_template", "costume.{costume}")
    )
    charset_key_template = str(
        resources.get("charset_key_template", "charset.{charset}")
    )
    for field_name, template, placeholder in (
        ("script_key_template", script_key_template, "{script}"),
        ("room_key_template", room_key_template, "{room}"),
        ("sound_key_template", sound_key_template, "{sound}"),
        ("costume_key_template", costume_key_template, "{costume}"),
        ("charset_key_template", charset_key_template, "{charset}"),
    ):
        if template.count(placeholder) != 1:
            raise ProfileValidationError(
                f"SCUMM resource_policy.{field_name} must contain {placeholder!r} exactly once"
            )
    audio_source = str(audio.get("source", "external"))
    if audio_source not in _AUDIO_SOURCES:
        raise ProfileValidationError(f"unsupported SCUMM audio source {audio_source!r}")
    sound_map_key = speech_archive_key = speech_index_key = None
    if audio_source == "external":
        sound_map_key = _text(audio, "sound_map_key", "audio_policy")
        speech_archive_key = _text(audio, "speech_archive_key", "audio_policy")
        speech_index_key = _text(audio, "speech_index_key", "audio_policy")
    patch_value = resources.get("script_patch_manifest_key")
    if patch_value is not None and (not isinstance(patch_value, str) or not patch_value):
        raise ProfileValidationError(
            "SCUMM option resource_policy.script_patch_manifest_key must be a non-empty string or null"
        )
    script_patch_manifest_key = patch_value

    bound_keys = [
        ("resource_policy.index_key", index_key),
        ("resource_policy.data_key", data_key),
    ]
    if audio_source == "external":
        assert sound_map_key is not None
        assert speech_archive_key is not None
        assert speech_index_key is not None
        bound_keys.extend(
            (
                ("audio_policy.sound_map_key", sound_map_key),
                ("audio_policy.speech_archive_key", speech_archive_key),
                ("audio_policy.speech_index_key", speech_index_key),
            )
        )
    for field_name, resource_key in bound_keys:
        _binding(profile, resource_key, field_name)
    if script_patch_manifest_key is not None:
        _binding(
            profile,
            script_patch_manifest_key,
            "resource_policy.script_patch_manifest_key",
        )

    speech_track_base = int(audio.get("speech_track_base", 1))
    if not 1 <= speech_track_base <= 65535:
        raise ProfileValidationError("SCUMM speech_track_base must be in 1..65535")
    stub_sound_policy = _text(audio, "stub_sound_policy", "audio_policy")
    if stub_sound_policy not in _STUB_SOUND_POLICIES:
        raise ProfileValidationError(f"unsupported SCUMM stub_sound_policy {stub_sound_policy!r}")

    logical_width = _integer(coordinates, "logical_width", "coordinate_policy")
    logical_height = _integer(coordinates, "logical_height", "coordinate_policy")
    expected_width = profile.video.logical_width or profile.video.width
    expected_height = profile.video.logical_height or profile.video.height
    if (logical_width, logical_height) != (expected_width, expected_height):
        raise ProfileValidationError(
            "SCUMM coordinate policy must match the profile logical video geometry"
        )
    presentation = _text(coordinates, "presentation", "coordinate_policy")
    if presentation != "host_viewport":
        raise ProfileValidationError(
            "SCUMM coordinate_policy.presentation must be 'host_viewport'"
        )
    cursor_policy = _text(coordinates, "cursor_policy", "coordinate_policy")
    if cursor_policy != "engine_default":
        raise ProfileValidationError(
            "SCUMM cursor_policy must be 'engine_default'; custom cursor behavior belongs in an adapter"
        )

    mode = _text(copy_protection, "mode", "copy_protection_policy")
    if mode not in _COPY_PROTECTION_MODES:
        raise ProfileValidationError(f"unsupported SCUMM copy-protection mode {mode!r}")
    script = variable = answer = None
    if mode == "bypass":
        script = _integer(copy_protection, "script", "copy_protection_policy")
        variable = _integer(copy_protection, "answer_variable", "copy_protection_policy")
        answer = _integer(copy_protection, "answer_value", "copy_protection_policy")
        if not 1 <= script <= 255:
            raise ProfileValidationError("SCUMM copy-protection script must be in 1..255")
        if not 0 <= variable < 2048:
            raise ProfileValidationError("SCUMM copy-protection variable must be in 0..2047")
        if not -32768 <= answer <= 32767:
            raise ProfileValidationError("SCUMM copy-protection answer must fit signed 16-bit")

    for quirk_name in profile.quirks:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", quirk_name) or quirk_name.count(".") < 2:
            raise ProfileValidationError(
                f"SCUMM quirk {quirk_name!r} must be a narrow, namespaced game.variant.behavior key"
            )

    return ScummV5GamePolicy(
        resource_format=resource_format,
        index_key=index_key,
        data_key=data_key,
        script_key_template=script_key_template,
        room_key_template=room_key_template,
        sound_key_template=sound_key_template,
        costume_key_template=costume_key_template,
        charset_key_template=charset_key_template,
        audio_source=audio_source,
        sound_map_key=sound_map_key,
        speech_archive_key=speech_archive_key,
        speech_index_key=speech_index_key,
        script_patch_manifest_key=script_patch_manifest_key,
        speech_track_base=speech_track_base,
        stub_sound_policy=stub_sound_policy,
        logical_width=logical_width,
        logical_height=logical_height,
        presentation=presentation,
        cursor_policy=cursor_policy,
        copy_protection_mode=mode,
        copy_protection_script=script,
        copy_protection_variable=variable,
        copy_protection_answer=answer,
    )
