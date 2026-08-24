"""Capability vocabulary shared by SAME engines and platform backends."""

from __future__ import annotations

from enum import IntFlag
from typing import Iterable

from .errors import EngineCompatibilityError, ProfileValidationError


class EngineCapability(IntFlag):
    NONE = 0

    # Baseline ScummVM-shaped services.
    INDEXED8_SURFACE = 1 << 0
    DIRTY_RECTS = 1 << 1
    PALETTE_256 = 1 << 2
    POINTER_INPUT = 1 << 3
    DIGITAL_INPUT = 1 << 4
    TEXT_INPUT = 1 << 5
    SAVE_SLOTS = 1 << 6
    RANDOM_ACCESS_RESOURCES = 1 << 7
    STREAMING_RESOURCES = 1 << 8
    TIMER_60HZ = 1 << 9
    TIMER_30HZ = 1 << 10
    AUDIO_MUSIC = 1 << 11
    AUDIO_SFX = 1 << 12
    AUDIO_SPEECH = 1 << 13

    # Optional SNES-native accelerators. Engines must always negotiate these.
    TILED_VIDEO = 1 << 16
    SPRITE_OAM = 1 << 17
    Z_MASK = 1 << 18
    HDMA = 1 << 19
    SA1_JOBS = 1 << 20
    MSU1_STREAM = 1 << 21
    CHIP_AUDIO = 1 << 22
    FOREIGN_CPU = 1 << 23
    DEBUG_ORACLE = 1 << 24


_CAPABILITY_NAMES = {member.name.lower(): member for member in EngineCapability if member}


def capability_names(value: EngineCapability) -> tuple[str, ...]:
    return tuple(
        member.name.lower()
        for member in EngineCapability
        if member and (value & member) == member
    )


def capabilities_from_names(
    names: Iterable[str], *, profile_context: bool = False
) -> EngineCapability:
    result = EngineCapability.NONE
    error_type = ProfileValidationError if profile_context else EngineCompatibilityError
    for raw in names:
        key = str(raw).strip().lower()
        try:
            result |= _CAPABILITY_NAMES[key]
        except KeyError as exc:
            allowed = ", ".join(sorted(_CAPABILITY_NAMES))
            raise error_type(
                f"unknown engine capability {raw!r}; expected one of: {allowed}"
            ) from exc
    return result


DEFAULT_HOST_CAPABILITIES = (
    EngineCapability.INDEXED8_SURFACE
    | EngineCapability.DIRTY_RECTS
    | EngineCapability.PALETTE_256
    | EngineCapability.POINTER_INPUT
    | EngineCapability.DIGITAL_INPUT
    | EngineCapability.TEXT_INPUT
    | EngineCapability.SAVE_SLOTS
    | EngineCapability.RANDOM_ACCESS_RESOURCES
    | EngineCapability.STREAMING_RESOURCES
    | EngineCapability.TIMER_60HZ
    | EngineCapability.TIMER_30HZ
    | EngineCapability.AUDIO_MUSIC
    | EngineCapability.AUDIO_SFX
    | EngineCapability.AUDIO_SPEECH
    | EngineCapability.TILED_VIDEO
    | EngineCapability.SPRITE_OAM
    | EngineCapability.Z_MASK
    | EngineCapability.SA1_JOBS
    | EngineCapability.MSU1_STREAM
    | EngineCapability.CHIP_AUDIO
    | EngineCapability.DEBUG_ORACLE
)
