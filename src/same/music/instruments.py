"""Fingerprint-addressed reviewed instrument zones for compiled backends."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Mapping

from ..errors import ResourceError


def _int(value: object, name: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ResourceError(f"instrument bank {name} must be in {low}..{high}")
    return value


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ResourceError(f"instrument bank {name} must be a SHA-256 digest")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise ResourceError(f"instrument bank {name} must be hexadecimal") from exc
    return value


@dataclass(frozen=True, slots=True)
class InstrumentZone:
    name: str
    patch_fingerprint: str
    sample_resource: str
    sample_sha256: str
    root_pitch: int
    first_pitch: int
    last_pitch: int
    loop_point: int
    loop_samples: int
    review_status: str

    def __post_init__(self) -> None:
        if not self.name or not self.sample_resource:
            raise ValueError("instrument zone name and sample resource cannot be empty")
        for value, name in ((self.patch_fingerprint, "patch"), (self.sample_sha256, "sample")):
            if len(value) != 64:
                raise ValueError(f"instrument zone {name} fingerprint must be SHA-256")
            bytes.fromhex(value)
        if not 0 <= self.root_pitch <= 127:
            raise ValueError("instrument zone root pitch is outside 0..127")
        if not 0 <= self.first_pitch <= self.last_pitch <= 127:
            raise ValueError("instrument zone pitch range is invalid")
        if self.loop_point < 0 or self.loop_samples <= 0:
            raise ValueError("instrument zone loop is invalid")
        if self.review_status not in {"accepted", "provisional", "rejected"}:
            raise ValueError("instrument zone review status is invalid")

    def covers(self, pitch: int) -> bool:
        return self.first_pitch <= int(pitch) <= self.last_pitch


@dataclass(frozen=True, slots=True)
class InstrumentBank:
    name: str
    source_device: str
    capture_velocity: int
    capture_cc7: int
    reference_volume: int
    zones: tuple[InstrumentZone, ...]

    @classmethod
    def decode(cls, raw: bytes, key: str) -> "InstrumentBank":
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ResourceError(f"instrument bank {key!r} is invalid JSON: {exc}") from exc
        if not isinstance(data, Mapping) or data.get("schema") != "same_instrument_bank_v1":
            raise ResourceError(f"instrument bank {key!r} has an unsupported schema")
        raw_zones = data.get("zones")
        if not isinstance(raw_zones, list) or not raw_zones:
            raise ResourceError(f"instrument bank {key!r} has no zones")
        zones: list[InstrumentZone] = []
        for index, item in enumerate(raw_zones):
            if not isinstance(item, Mapping):
                raise ResourceError(f"instrument bank zone {index} is not an object")
            try:
                zones.append(InstrumentZone(
                    name=str(item["name"]),
                    patch_fingerprint=_sha(item.get("patch_sha256"), f"zone {index} patch"),
                    sample_resource=str(item["sample_resource"]),
                    sample_sha256=_sha(item.get("sha256"), f"zone {index} sample"),
                    root_pitch=_int(item.get("root_pitch"), f"zone {index} root pitch", 0, 127),
                    first_pitch=_int(item.get("first_pitch"), f"zone {index} first pitch", 0, 127),
                    last_pitch=_int(item.get("last_pitch"), f"zone {index} last pitch", 0, 127),
                    loop_point=_int(item.get("loop_point"), f"zone {index} loop point", 0, 1 << 30),
                    loop_samples=_int(item.get("loop_samples"), f"zone {index} loop samples", 1, 1 << 30),
                    review_status=str(item.get("review_status", "")),
                ))
            except (KeyError, TypeError, ValueError) as exc:
                raise ResourceError(f"instrument bank zone {index} is invalid: {exc}") from exc
        names = [zone.name for zone in zones]
        if len(names) != len(set(names)):
            raise ResourceError(f"instrument bank {key!r} repeats a zone name")
        return cls(
            name=str(data.get("name", "")),
            source_device=str(data.get("source_device", "")),
            capture_velocity=_int(data.get("capture_velocity"), "capture velocity", 0, 127),
            capture_cc7=_int(data.get("capture_cc7"), "capture CC7", 0, 127),
            reference_volume=_int(data.get("reference_volume"), "reference volume", 1, 255),
            zones=tuple(zones),
        )

    def zone(self, name: str) -> InstrumentZone:
        try:
            return next(zone for zone in self.zones if zone.name == name)
        except StopIteration as exc:
            raise ResourceError(f"instrument bank {self.name!r} has no zone {name!r}") from exc

    def resolve(self, patch_fingerprint: str, pitch: int) -> InstrumentZone:
        matches = [
            zone for zone in self.zones
            if zone.patch_fingerprint == patch_fingerprint and zone.covers(pitch)
            and zone.review_status == "accepted"
        ]
        if len(matches) != 1:
            raise ResourceError(
                f"instrument bank {self.name!r} resolves patch {patch_fingerprint[:16]} "
                f"pitch {pitch} to {len(matches)} accepted zones"
            )
        return matches[0]
