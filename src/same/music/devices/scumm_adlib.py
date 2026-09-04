"""SCUMM v5 AdLib patch and nonlinear performance-response model."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math


_VOLUME_TABLE = (
    0, 4, 7, 11, 13, 16, 18, 20, 22, 24, 26, 27, 29, 30, 31, 33,
    34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 44, 45, 46, 47, 47,
    48, 49, 49, 50, 51, 51, 52, 53, 53, 54, 54, 55, 55, 56, 56, 57,
    57, 58, 58, 59, 59, 60, 60, 60, 61, 61, 62, 62, 62, 63, 63, 63,
)


def _lookup(value: int, scale: int) -> int:
    if scale == 0:
        return 0
    if scale == 31:
        return value
    return value * (scale + 1) // 32


@dataclass(frozen=True, slots=True)
class AdlibPatch:
    data: bytes

    def __post_init__(self) -> None:
        if len(self.data) != 30:
            raise ValueError(f"SCUMM AdLib patch must contain 30 bytes, got {len(self.data)}")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def additive(self) -> bool:
        return bool(self.data[10] & 1)

    def operator_gain(self, velocity: int, cc7: int, operator: int) -> float:
        if operator not in (0, 1):
            raise ValueError("AdLib operator must be 0 or 1")
        if not 0 <= int(velocity) <= 127 or not 0 <= int(cc7) <= 127:
            raise ValueError("AdLib velocity and CC7 must be in 0..127")
        level_index, waveform_index = ((1, 4), (6, 9))[operator]
        raw_level = min(
            63,
            (self.data[level_index] & 0x3F)
            + _lookup(int(velocity) >> 1, self.data[waveform_index] >> 2),
        )
        effective = _VOLUME_TABLE[_lookup(raw_level, int(cc7) >> 2)]
        attenuation = 63 - effective
        return 10.0 ** (-attenuation * 0.75 / 20.0)


@dataclass(frozen=True, slots=True)
class AdlibCaptureCalibration:
    velocity: int = 100
    cc7: int = 127
    backend_reference_volume: int = 96

    def __post_init__(self) -> None:
        if not 0 <= self.velocity <= 127 or not 0 <= self.cc7 <= 127:
            raise ValueError("AdLib capture velocity and CC7 must be in 0..127")
        if not 1 <= self.backend_reference_volume <= 255:
            raise ValueError("backend reference volume must be in 1..255")


class ScummV5AdlibDevice:
    """Reproduces the original SCUMM AdLib operator-volume calculation.

    It is a source-device model, not a PCM synthesizer. Exact host rendering can
    use Nuked OPL; sample backends use ``relative_gain`` to preserve the same
    performance response against an explicitly recorded capture calibration.
    """

    identifier = "scumm_v5_adlib"

    def __init__(self, calibration: AdlibCaptureCalibration | None = None) -> None:
        self.calibration = calibration or AdlibCaptureCalibration()

    @staticmethod
    def _audible_operators(patch: AdlibPatch) -> tuple[int, ...]:
        return (0, 1) if patch.additive else (1,)

    def relative_gain(self, patch: AdlibPatch, velocity: int, cc7: int) -> float:
        operators = self._audible_operators(patch)
        target_power = sum(
            patch.operator_gain(velocity, cc7, operator) ** 2
            for operator in operators
        )
        capture_power = sum(
            patch.operator_gain(
                self.calibration.velocity, self.calibration.cc7, operator,
            ) ** 2
            for operator in operators
        )
        return math.sqrt(target_power / capture_power)

    def backend_volume(self, patch: AdlibPatch, velocity: int, cc7: int) -> int:
        value = round(
            self.calibration.backend_reference_volume
            * self.relative_gain(patch, velocity, cc7)
        )
        return max(1, min(255, value))


def extract_scumm_adlib_patches(sound: object) -> dict[int, AdlibPatch]:
    """Extract one stable complete patch identity for each iMUSE channel."""
    source = str(getattr(sound, "key", "scumm-imuse"))
    patches: dict[int, AdlibPatch] = {}
    for track in tuple(getattr(sound, "imuse_events", ())):
        for event in track:
            if int(event.command) != 16:
                continue
            channel, *data = event.values
            if not 0 <= int(channel) < 16 or len(data) != 30:
                raise ValueError(f"SCUMM AdLib {source!r} has an invalid patch record")
            patch = AdlibPatch(bytes(data))
            previous = patches.setdefault(int(channel), patch)
            if previous != patch:
                raise ValueError(
                    f"SCUMM AdLib {source!r} changes channel {channel} patch identity"
                )
    if not patches:
        raise ValueError(f"SCUMM AdLib {source!r} has no complete patches")
    return patches
