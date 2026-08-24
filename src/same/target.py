"""Target manifests: the boundary between SAME and a specific guest machine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any

from .input import PROFILES
from .scheduler import Affinity, Phase
from .errors import TargetValidationError

MANIFEST_VERSION = 1
GUEST_KINDS = {
    "native",
    "openbor_vm",
    "m68k",
    "z80",
    "m68k_z80",
    "bytecode",
    "trace_player",
}
VIDEO_ADAPTERS = {
    "native_snes",
    "genesis_vdp",
    "taito_x",
    "black_tiger",
    "openbor_scene",
    "trace_player",
}
AUDIO_BACKENDS = {"none", "tad", "spc", "msu1", "host_wav"}
STORAGE_BACKENDS = {"rom", "msu1", "wram", "host"}


@dataclass(frozen=True, slots=True)
class GuestBusSpec:
    name: str
    address_bits: int
    endianness: str


@dataclass(frozen=True, slots=True)
class MemoryRegionSpec:
    bus: str
    name: str
    start: int
    size: int
    kind: str
    source: str | None
    adapter: str | None

    @property
    def end(self) -> int:
        return self.start + self.size


@dataclass(frozen=True, slots=True)
class ExecutionLane:
    name: str
    affinity: Affinity
    phase: Phase
    budget: int
    period: int
    priority: int


@dataclass(frozen=True, slots=True)
class TargetManifest:
    path: Path
    identifier: str
    name: str
    guest_kind: str
    input_profile: str
    video_adapter: str
    audio_backend: str
    storage_backend: str
    lanes: tuple[ExecutionLane, ...]
    buses: tuple[GuestBusSpec, ...]
    memory_map: tuple[MemoryRegionSpec, ...]
    raw: dict[str, Any]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "same_target": MANIFEST_VERSION,
            "id": self.identifier,
            "name": self.name,
            "guest_kind": self.guest_kind,
            "input_profile": self.input_profile,
            "video_adapter": self.video_adapter,
            "audio_backend": self.audio_backend,
            "storage_backend": self.storage_backend,
            "buses": [
                {
                    "name": bus.name,
                    "address_bits": bus.address_bits,
                    "endianness": bus.endianness,
                }
                for bus in self.buses
            ],
            "memory_map": [
                {
                    "bus": region.bus,
                    "name": region.name,
                    "start": region.start,
                    "size": region.size,
                    "end": region.end,
                    "kind": region.kind,
                    "source": region.source,
                    "adapter": region.adapter,
                }
                for region in self.memory_map
            ],
            "lanes": [
                {
                    "name": lane.name,
                    "affinity": lane.affinity.name,
                    "phase": lane.phase.name,
                    "budget": lane.budget,
                    "period": lane.period,
                    "priority": lane.priority,
                }
                for lane in self.lanes
            ],
            "warnings": list(self.warnings),
        }


def _object(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TargetValidationError(f"{name} must be an object")
    return value


def _choice(value: Any, name: str, choices: set[str]) -> str:
    value = str(value)
    if value not in choices:
        raise TargetValidationError(
            f"{name}={value!r} is unsupported; choices: {', '.join(sorted(choices))}"
        )
    return value


def _int_value(value: Any, name: str) -> int:
    try:
        if isinstance(value, str):
            return int(value, 0)
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TargetValidationError(f"{name} must be an integer or 0x-prefixed string") from exc


def load_target(path: Path) -> TargetManifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TargetValidationError(f"cannot read target manifest {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise TargetValidationError("target manifest root must be an object")
    if raw.get("same_target") != MANIFEST_VERSION:
        raise TargetValidationError(f"target manifest must contain same_target: {MANIFEST_VERSION}")
    identifier = str(raw.get("id", ""))
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,31}", identifier):
        raise TargetValidationError("id must be 2..32 lowercase letters, digits, '_' or '-'")
    name = str(raw.get("name", "")).strip()
    if not name or len(name) > 80:
        raise TargetValidationError("name must contain 1..80 characters")
    guest = _object(raw.get("guest"), "guest")
    guest_kind = _choice(guest.get("kind"), "guest.kind", GUEST_KINDS)
    raw_buses = guest.get("buses", {})
    if raw_buses is None:
        raw_buses = {}
    if not isinstance(raw_buses, dict):
        raise TargetValidationError("guest.buses must be an object")
    buses: list[GuestBusSpec] = []
    for bus_name, bus_value in raw_buses.items():
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,31}", str(bus_name)):
            raise TargetValidationError(f"guest bus name {bus_name!r} is invalid")
        bus = _object(bus_value, f"guest.buses.{bus_name}")
        address_bits = _int_value(bus.get("address_bits"), f"guest.buses.{bus_name}.address_bits")
        if not 1 <= address_bits <= 32:
            raise TargetValidationError(f"guest.buses.{bus_name}.address_bits must be 1..32")
        endianness = str(bus.get("endianness", ""))
        if endianness not in {"little", "big"}:
            raise TargetValidationError(f"guest.buses.{bus_name}.endianness must be little or big")
        buses.append(GuestBusSpec(str(bus_name), address_bits, endianness))

    bus_by_name = {bus.name: bus for bus in buses}
    raw_memory = raw.get("memory_map", [])
    if not isinstance(raw_memory, list):
        raise TargetValidationError("memory_map must be a list")
    memory_map: list[MemoryRegionSpec] = []
    ranges: dict[str, list[MemoryRegionSpec]] = {}
    for index, item in enumerate(raw_memory):
        region = _object(item, f"memory_map[{index}]")
        bus_name = str(region.get("bus", ""))
        if bus_name not in bus_by_name:
            raise TargetValidationError(f"memory_map[{index}].bus {bus_name!r} is not declared in guest.buses")
        region_name = str(region.get("name", ""))
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,31}", region_name):
            raise TargetValidationError(f"memory_map[{index}].name is invalid")
        kind = str(region.get("kind", ""))
        if kind not in {"ram", "rom", "device"}:
            raise TargetValidationError(f"memory_map[{index}].kind must be ram, rom, or device")
        start = _int_value(region.get("start"), f"memory_map[{index}].start")
        size = _int_value(region.get("size"), f"memory_map[{index}].size")
        if start < 0 or size <= 0:
            raise TargetValidationError(f"memory_map[{index}] start/size are invalid")
        if start + size > (1 << bus_by_name[bus_name].address_bits):
            raise TargetValidationError(f"memory_map[{index}] lies outside bus {bus_name}")
        source = None if region.get("source") is None else str(region.get("source"))
        adapter = None if region.get("adapter") is None else str(region.get("adapter"))
        if kind == "rom" and not source:
            raise TargetValidationError(f"memory_map[{index}] ROM requires source section name")
        if kind == "device" and not adapter:
            raise TargetValidationError(f"memory_map[{index}] device requires adapter")
        spec = MemoryRegionSpec(bus_name, region_name, start, size, kind, source, adapter)
        for current in ranges.setdefault(bus_name, []):
            if spec.start < current.end and current.start < spec.end:
                raise TargetValidationError(
                    f"memory regions {current.name!r} and {spec.name!r} overlap on bus {bus_name}"
                )
        ranges[bus_name].append(spec)
        memory_map.append(spec)
    services = _object(raw.get("services"), "services")
    input_service = _object(services.get("input"), "services.input")
    input_profile = str(input_service.get("profile", ""))
    if input_profile not in PROFILES:
        raise TargetValidationError(
            f"services.input.profile={input_profile!r} is unsupported; "
            f"choices: {', '.join(sorted(PROFILES))}"
        )
    video = _object(services.get("video"), "services.video")
    video_adapter = _choice(video.get("adapter"), "services.video.adapter", VIDEO_ADAPTERS)
    audio = _object(services.get("audio"), "services.audio")
    audio_backend = _choice(audio.get("backend"), "services.audio.backend", AUDIO_BACKENDS)
    storage = _object(services.get("storage"), "services.storage")
    storage_backend = _choice(
        storage.get("backend"), "services.storage.backend", STORAGE_BACKENDS
    )

    execution = raw.get("execution")
    if not isinstance(execution, list) or not execution:
        raise TargetValidationError("execution must be a non-empty list")
    names: set[str] = set()
    lanes: list[ExecutionLane] = []
    for index, item in enumerate(execution):
        lane = _object(item, f"execution[{index}]")
        lane_name = str(lane.get("name", ""))
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{1,47}", lane_name):
            raise TargetValidationError(f"execution[{index}].name is invalid")
        if lane_name in names:
            raise TargetValidationError(f"duplicate execution lane {lane_name!r}")
        names.add(lane_name)
        try:
            affinity = Affinity[str(lane.get("affinity", "")).upper()]
        except KeyError as exc:
            raise TargetValidationError(
                f"execution[{index}].affinity must be HOST, SCPU, SA1, or SPC"
            ) from exc
        try:
            phase = Phase[str(lane.get("phase", "")).upper()]
        except KeyError as exc:
            raise TargetValidationError(
                f"execution[{index}].phase must name a SAME scheduler phase"
            ) from exc
        budget = int(lane.get("budget", 0))
        period = int(lane.get("period", 1))
        priority = int(lane.get("priority", 100))
        if budget <= 0 or budget > 100_000_000:
            raise TargetValidationError(f"execution[{index}].budget is invalid")
        if period <= 0 or period > 65535:
            raise TargetValidationError(f"execution[{index}].period is invalid")
        if priority < 0 or priority > 65535:
            raise TargetValidationError(f"execution[{index}].priority is invalid")
        lanes.append(ExecutionLane(lane_name, affinity, phase, budget, period, priority))

    warnings: list[str] = []
    if guest_kind in {"m68k", "z80", "m68k_z80"} and not buses:
        warnings.append("foreign CPU target declares no guest buses")
    if buses and not memory_map:
        warnings.append("guest buses are declared but the hardware memory map is still empty")
    if guest_kind == "openbor_vm" and any(lane.affinity is Affinity.SA1 for lane in lanes):
        warnings.append(
            "OpenBOR VM is assigned to SA-1; snes-bor currently keeps it on S-CPU because "
            "its SA-1 compositor is persistent. Measure before adopting this placement."
        )
    if video_adapter != "native_snes" and not any(
        lane.phase is Phase.TRANSLATE for lane in lanes
    ):
        warnings.append("foreign video adapter has no TRANSLATE execution lane")
    if guest_kind == "m68k_z80" and len([lane for lane in lanes if lane.phase is Phase.GUEST]) < 2:
        warnings.append("m68k_z80 target defines fewer than two GUEST execution lanes")
    if storage_backend == "msu1" and "package" not in storage:
        warnings.append("MSU-1 target does not name a SAME package")
    return TargetManifest(
        path=path,
        identifier=identifier,
        name=name,
        guest_kind=guest_kind,
        input_profile=input_profile,
        video_adapter=video_adapter,
        audio_backend=audio_backend,
        storage_backend=storage_backend,
        lanes=tuple(lanes),
        buses=tuple(buses),
        memory_map=tuple(memory_map),
        raw=raw,
        warnings=tuple(warnings),
    )
