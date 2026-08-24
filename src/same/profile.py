"""Engine game-profile manifests.

A profile is deliberately game data and policy, not engine code.  The SCUMM v5
engine can therefore run several games without gaining Monkey-Island-specific
branches, and an AGI engine can accept King's Quest, Space Quest, and other AGI
resource sets through the same host interface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import os
import re
from typing import Any, Mapping

from .capabilities import EngineCapability, capabilities_from_names, capability_names
from .errors import ProfileValidationError
from .input import PROFILES as INPUT_PROFILES

PROFILE_VERSION = 1
_ID_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{0,47}$")
_RESOURCE_KEY_RE = re.compile(r"[A-Za-z0-9_.:-]{1,96}$")


def _identifier(value: object, field_name: str) -> str:
    text = str(value or "").strip()
    if not _ID_RE.fullmatch(text):
        raise ProfileValidationError(
            f"{field_name}={text!r} must match {_ID_RE.pattern!r}"
        )
    return text


def _string_map(value: object, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ProfileValidationError(f"{field_name} must be an object")
    return {str(key): item for key, item in value.items()}


@dataclass(frozen=True, slots=True)
class ResourceBinding:
    key: str
    path: Path
    kind: str = "DATA"
    required: bool = True
    streamable: bool = False
    package_section: str | None = None

    def __post_init__(self) -> None:
        if not _RESOURCE_KEY_RE.fullmatch(self.key):
            raise ProfileValidationError(
                f"resource key {self.key!r} must match {_RESOURCE_KEY_RE.pattern!r}"
            )
        if not re.fullmatch(r"[A-Za-z0-9_]{4}", self.kind):
            raise ProfileValidationError(
                f"resource {self.key}: kind {self.kind!r} must be four ASCII characters"
            )
        if self.package_section is not None and not re.fullmatch(
            r"[A-Za-z0-9_.-]{1,8}", self.package_section
        ):
            raise ProfileValidationError(
                f"resource {self.key}: invalid package section {self.package_section!r}"
            )

    def to_dict(self, base: Path | None = None) -> dict[str, object]:
        path = self.path
        if base is not None:
            try:
                path = Path(os.path.relpath(path, base))
            except ValueError:
                # Different Windows drives cannot be represented by one relative path.
                pass
        result: dict[str, object] = {
            "key": self.key,
            "path": path.as_posix(),
            "kind": self.kind,
            "required": self.required,
            "streamable": self.streamable,
        }
        if self.package_section is not None:
            result["section"] = self.package_section
        return result


@dataclass(frozen=True, slots=True)
class VideoProfile:
    width: int
    height: int
    mode: str = "indexed8"
    logical_width: int | None = None
    logical_height: int | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.width <= 2048 or not 1 <= self.height <= 2048:
            raise ProfileValidationError("video width/height must be in 1..2048")
        if self.mode != "indexed8":
            raise ProfileValidationError(
                f"unsupported baseline video mode {self.mode!r}; expected 'indexed8'"
            )
        for field_name, value in (
            ("logical_width", self.logical_width),
            ("logical_height", self.logical_height),
        ):
            if value is not None and not 1 <= value <= 4096:
                raise ProfileValidationError(f"video {field_name} must be in 1..4096")

    def to_dict(self) -> dict[str, object]:
        return {
            "width": self.width,
            "height": self.height,
            "mode": self.mode,
            "logical_width": self.logical_width or self.width,
            "logical_height": self.logical_height or self.height,
        }


@dataclass(frozen=True, slots=True)
class EngineProfile:
    path: Path
    engine_id: str
    game_id: str
    title: str
    variant: str
    tick_hz: int
    max_ops_per_tick: int
    video: VideoProfile
    input_profile: str
    resources: tuple[ResourceBinding, ...]
    required_capabilities: EngineCapability = EngineCapability.NONE
    optional_capabilities: EngineCapability = EngineCapability.NONE
    options: Mapping[str, Any] = field(default_factory=dict)
    quirks: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _identifier(self.engine_id, "engine")
        _identifier(self.game_id, "game.id")
        if not self.title.strip():
            raise ProfileValidationError("game.title must not be empty")
        if not 1 <= self.tick_hz <= 240:
            raise ProfileValidationError("timing.tick_hz must be in 1..240")
        if not 1 <= self.max_ops_per_tick <= 1_000_000:
            raise ProfileValidationError("timing.max_ops_per_tick must be positive")
        if self.input_profile not in INPUT_PROFILES:
            choices = ", ".join(sorted(INPUT_PROFILES))
            raise ProfileValidationError(
                f"input.profile={self.input_profile!r} is unsupported; choices: {choices}"
            )
        keys = [binding.key for binding in self.resources]
        if len(keys) != len(set(keys)):
            raise ProfileValidationError("resource keys must be unique")
        overlap = self.required_capabilities & self.optional_capabilities
        if overlap:
            names = ", ".join(capability_names(overlap))
            raise ProfileValidationError(
                f"capabilities cannot be both required and optional: {names}"
            )

    @property
    def root(self) -> Path:
        return self.path.parent

    def binding(self, key: str) -> ResourceBinding:
        for binding in self.resources:
            if binding.key == key:
                return binding
        raise KeyError(key)

    def to_dict(self) -> dict[str, object]:
        return {
            "same_engine_profile": PROFILE_VERSION,
            "engine": self.engine_id,
            "game": {
                "id": self.game_id,
                "title": self.title,
                "variant": self.variant,
            },
            "timing": {
                "tick_hz": self.tick_hz,
                "max_ops_per_tick": self.max_ops_per_tick,
            },
            "video": self.video.to_dict(),
            "input": {"profile": self.input_profile},
            "capabilities": {
                "required": list(capability_names(self.required_capabilities)),
                "optional": list(capability_names(self.optional_capabilities)),
            },
            "resources": [binding.to_dict(self.root) for binding in self.resources],
            "options": dict(self.options),
            "quirks": dict(self.quirks),
        }


def _resource_binding(root: Path, item: object, index: int) -> ResourceBinding:
    if not isinstance(item, dict):
        raise ProfileValidationError(f"resources[{index}] must be an object")
    key = str(item.get("key", ""))
    raw_path = str(item.get("path", ""))
    if not raw_path:
        raise ProfileValidationError(f"resources[{index}].path must not be empty")
    path = (root / raw_path).resolve()
    section = item.get("section")
    return ResourceBinding(
        key=key,
        path=path,
        kind=str(item.get("kind", "DATA")),
        required=bool(item.get("required", True)),
        streamable=bool(item.get("streamable", False)),
        package_section=None if section is None else str(section),
    )


def load_profile(path: Path, *, verify_resources: bool = True) -> EngineProfile:
    path = path.resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileValidationError(f"cannot read profile {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileValidationError("profile root must be an object")
    if raw.get("same_engine_profile") != PROFILE_VERSION:
        raise ProfileValidationError(
            f"profile must contain same_engine_profile: {PROFILE_VERSION}"
        )

    game = raw.get("game")
    timing = raw.get("timing", {})
    video = raw.get("video")
    input_block = raw.get("input", {})
    capabilities = raw.get("capabilities", {})
    resources_raw = raw.get("resources", [])
    if not isinstance(game, dict):
        raise ProfileValidationError("game must be an object")
    if not isinstance(timing, dict):
        raise ProfileValidationError("timing must be an object")
    if not isinstance(video, dict):
        raise ProfileValidationError("video must be an object")
    if not isinstance(input_block, dict):
        raise ProfileValidationError("input must be an object")
    if not isinstance(capabilities, dict):
        raise ProfileValidationError("capabilities must be an object")
    if not isinstance(resources_raw, list):
        raise ProfileValidationError("resources must be a list")

    resources = tuple(
        _resource_binding(path.parent, item, index)
        for index, item in enumerate(resources_raw)
    )
    if verify_resources:
        for binding in resources:
            if binding.required and not binding.path.is_file():
                raise ProfileValidationError(
                    f"required resource {binding.key!r} does not exist: {binding.path}"
                )

    logical_width = video.get("logical_width")
    logical_height = video.get("logical_height")
    profile = EngineProfile(
        path=path,
        engine_id=_identifier(raw.get("engine"), "engine"),
        game_id=_identifier(game.get("id"), "game.id"),
        title=str(game.get("title", "")),
        variant=str(game.get("variant", "default")),
        tick_hz=int(timing.get("tick_hz", 60)),
        max_ops_per_tick=int(timing.get("max_ops_per_tick", 4096)),
        video=VideoProfile(
            width=int(video.get("width", 0)),
            height=int(video.get("height", 0)),
            mode=str(video.get("mode", "indexed8")),
            logical_width=None if logical_width is None else int(logical_width),
            logical_height=None if logical_height is None else int(logical_height),
        ),
        input_profile=str(input_block.get("profile", "snes")),
        resources=resources,
        required_capabilities=capabilities_from_names(
            capabilities.get("required", []), profile_context=True
        ),
        optional_capabilities=capabilities_from_names(
            capabilities.get("optional", []), profile_context=True
        ),
        options=_string_map(raw.get("options"), "options"),
        quirks=_string_map(raw.get("quirks"), "quirks"),
    )
    return profile
