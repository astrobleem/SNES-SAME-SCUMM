"""Validated build-time descriptions for SAME's SNES cartridge carriers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryRegion:
    name: str
    address: int
    size: int

    @property
    def end(self) -> int:
        return self.address + self.size


@dataclass(frozen=True)
class CarrierDescription:
    name: str
    carrier_id: int
    map_mode: int
    cartridge_type: int
    ram_size: int
    save_base: int
    save_bytes: int
    layout: dict[str, Any] | None
    config_sha256: str
    layout_sha256: str | None


def parse_address(value: str) -> int:
    bank, offset = value.split(":", 1)
    address = (int(bank, 16) << 16) | int(offset, 16)
    if not 0 <= address <= 0xFFFFFF:
        raise ValueError(f"SNES address escapes 24-bit space: {value}")
    return address


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_layout(layout: dict[str, Any]) -> tuple[MemoryRegion, ...]:
    if layout.get("format") != "same-sa1-bwram-storage" or layout.get("version") != 1:
        raise ValueError("unsupported SA-1 BW-RAM layout schema")
    if layout.get("bwram_bytes") != 0x20000:
        raise ValueError("SA-1 carrier requires exactly 128 KiB BW-RAM")
    expected = {
        "protected_low": (0x400000, 0x0800),
        "save_reserved": (0x400800, 0x0800),
        "backend_reserved": (0x401000, 0x1000),
        "live_surface": (0x402000, 0xE000),
        "tile_shadow": (0x410000, 0xE000),
        "cgram_shadow": (0x41E000, 0x0200),
        "future_staging": (0x41E200, 0x1E00),
    }
    regions: list[MemoryRegion] = []
    for name, (expected_address, expected_size) in expected.items():
        record = layout.get(name)
        if not isinstance(record, dict):
            raise ValueError(f"missing BW-RAM region {name}")
        address = parse_address(str(record.get("address")))
        size = record.get("bytes")
        if (address, size) != (expected_address, expected_size):
            raise ValueError(
                f"BW-RAM region {name} differs: {(address, size)!r} != "
                f"{(expected_address, expected_size)!r}"
            )
        region = MemoryRegion(name, address, size)
        if not 0x400000 <= region.address < region.end <= 0x420000:
            raise ValueError(f"BW-RAM region {name} escapes configured 128 KiB")
        regions.append(region)
    ordered = sorted(regions, key=lambda item: item.address)
    for left, right in zip(ordered, ordered[1:]):
        if left.end > right.address:
            raise ValueError(f"BW-RAM regions overlap: {left.name} and {right.name}")
    if sum(region.size for region in regions) != 0x20000:
        raise ValueError("BW-RAM layout does not account for exactly 128 KiB")
    if layout["live_surface"].get("width") != 256 or layout["live_surface"].get("height") != 224:
        raise ValueError("live surface dimensions differ from 256x224")
    if layout["live_surface"].get("format") != "indexed8":
        raise ValueError("live surface is not INDEX8")
    if layout["tile_shadow"].get("tiles") != 896 or layout["tile_shadow"].get("tile_bytes") != 64:
        raise ValueError("tile shadow dimensions differ")
    subregions = layout["backend_reserved"].get("allocations")
    if not isinstance(subregions, dict):
        raise ValueError("backend-reserved BW-RAM requires explicit internal allocations")
    occupied: list[tuple[int, int, str]] = []
    for name, item in subregions.items():
        if not isinstance(item, dict):
            raise ValueError(f"backend allocation {name} is malformed")
        offset, size = item.get("offset"), item.get("bytes")
        if not isinstance(offset, int) or not isinstance(size, int) or offset < 0 or size <= 0:
            raise ValueError(f"backend allocation {name} has invalid bounds")
        if offset + size > layout["backend_reserved"]["bytes"]:
            raise ValueError(f"backend allocation {name} escapes backend_reserved")
        occupied.append((offset, offset + size, name))
    occupied.sort()
    for left, right in zip(occupied, occupied[1:]):
        if left[1] > right[0]:
            raise ValueError(f"backend allocations overlap: {left[2]} and {right[2]}")
    expected_allocations = {
        "mode3_control": (0x000, 0x040),
        "video_surface_state": (0x040, 0x044),
        "live_room_palette_stage": (0x084, 0x300),
        "live_room_control": (0x384, 0x040),
        "live_room_pending": (0x3C4, 0xC3C),
    }
    for name, expected_bounds in expected_allocations.items():
        allocation = subregions.get(name)
        if not isinstance(allocation, dict):
            raise ValueError(f"backend allocation {name} is missing")
        actual_bounds = (allocation.get("offset"), allocation.get("bytes"))
        if actual_bounds != expected_bounds:
            raise ValueError(
                f"backend allocation {name} differs: {actual_bounds!r} != "
                f"{expected_bounds!r}"
            )
    # The SCUMM live-room personality owns the mode-3 layout's explicitly
    # reserved 4 KiB tail. It must never overlap active palette/work state.
    live_room = layout.get("live_room_active")
    if not isinstance(live_room, dict):
        raise ValueError("live-room active metadata allocation is missing")
    live_address = parse_address(str(live_room.get("address")))
    live_size = live_room.get("bytes")
    staging = layout["future_staging"]
    staging_address = parse_address(str(staging["address"]))
    if not isinstance(live_size, int) or live_size != 0x1800:
        raise ValueError("live-room active metadata must be the measured 6 KiB alias")
    if not (staging_address <= live_address and live_address + live_size <= staging_address + staging["bytes"]):
        raise ValueError("live-room active metadata escapes future_staging")
    if staging_address != 0x41E200 or staging.get("bytes") != 0x1E00:
        raise ValueError("Mode-3 staging ownership changed")
    if staging.get("allocations") != {}:
        raise ValueError("Mode-3 future staging must not claim the live SCUMM cache page")
    if set(live_room.get("exclusive_with", ())) != {
        "runtime/snes/video_backends/mode3_surface_layout.json:fixture",
        "runtime/snes/video_backends/mode3_surface_layout.json:reserved",
    }:
        raise ValueError("live-room active metadata must declare both Mode-3 lifetime aliases")
    pending = subregions.get("live_room_pending")
    if pending != {"offset": 0x3C4, "bytes": 0xC3C,
                   "owner": "SCUMM live-room incoming metadata transaction"}:
        raise ValueError("live-room pending metadata must use its packed 3,132-byte backend allocation")
    return tuple(ordered)


def load_carrier(
    root: Path,
    name: str,
    *,
    save_enabled: bool,
) -> CarrierDescription:
    config_path = root / "runtime/snes/carriers.json"
    config_raw = config_path.read_bytes()
    config = json.loads(config_raw)
    if config.get("format") != "same-snes-carriers" or config.get("version") != 1:
        raise ValueError("unsupported SNES carrier schema")
    carriers = config.get("carriers")
    if not isinstance(carriers, dict) or name not in carriers:
        raise ValueError(f"unknown SNES carrier {name!r}")
    record = carriers[name]
    if not isinstance(record, dict):
        raise ValueError(f"malformed SNES carrier {name!r}")
    suffix = "with_save" if save_enabled else "without_save"
    layout = None
    layout_hash = None
    layout_name = record.get("layout")
    if layout_name is not None:
        layout_path = root / str(layout_name)
        layout_raw = layout_path.read_bytes()
        layout = json.loads(layout_raw)
        _validate_layout(layout)
        if name == "sa1_bwram":
            video_path = root / "runtime/snes/video_backends/mode3_surface_layout.json"
            video_layout = json.loads(video_path.read_text(encoding="utf-8"))
            active = layout["live_room_active"]
            reserved = video_layout.get("reserved", {})
            fixture = video_layout.get("fixture", {})
            expected_live_start = parse_address(str(fixture.get("address")))
            expected_live_end = (parse_address(str(reserved.get("address")))
                                 + int(reserved.get("bytes", 0)))
            if (parse_address(str(active.get("address"))), active.get("bytes")) != (
                    expected_live_start, expected_live_end - expected_live_start,
                ):
                raise ValueError(
                    "live-room metadata alias must cover fixture plus reserved Mode-3 storage"
                )
            active_start = parse_address(str(active["address"]))
            active_end = active_start + int(active["bytes"])
            for region_name, region in video_layout.items():
                if region_name in {"format", "version", "active_convert_tile_budget",
                                   "dma_byte_budget", "dma_descriptor_limit", "reserved"}:
                    continue
                if not isinstance(region, dict) or "address" not in region or "bytes" not in region:
                    continue
                start = parse_address(str(region["address"]))
                end = start + int(region["bytes"])
                if region_name in {"fixture", "reserved"}:
                    continue
                if active_start < end and start < active_end:
                    raise ValueError(
                        f"live-room metadata overlaps active video region {region_name}"
                    )
        layout_hash = _sha256(layout_raw)
    description = CarrierDescription(
        name=name,
        carrier_id=int(record["id"]),
        map_mode=int(record["map_mode"]),
        cartridge_type=int(record[f"cartridge_type_{suffix}"]),
        ram_size=int(record[f"ram_size_{suffix}"]),
        save_base=parse_address(str(record["save_base"])),
        save_bytes=int(record["save_bytes"]),
        layout=layout,
        config_sha256=_sha256(config_raw),
        layout_sha256=layout_hash,
    )
    if description.save_bytes != 0x0800:
        raise ValueError("carrier changes the accepted 2 KiB save contract")
    if name == "lorom":
        if (description.map_mode, description.save_base) != (0x20, 0x700000):
            raise ValueError("ordinary LoROM carrier identity differs")
    elif name == "sa1_bwram":
        if (description.map_mode, description.cartridge_type, description.ram_size) != (
            0x23,
            0x35,
            0x07,
        ):
            raise ValueError("SA-1 header identity differs")
        assert layout is not None
        if description.save_base != parse_address(layout["save_reserved"]["address"]):
            raise ValueError("SA-1 save base differs from accepted layout")
        if description.save_bytes != layout["save_reserved"]["bytes"]:
            raise ValueError("SA-1 save size differs from accepted layout")
    return description


def default_carrier(root: Path) -> str:
    config = json.loads((root / "runtime/snes/carriers.json").read_text(encoding="utf-8"))
    value = config.get("default")
    if value != "lorom":
        raise ValueError("ordinary LoROM must remain the default carrier")
    return value


def layout_regions(layout: dict[str, Any]) -> tuple[MemoryRegion, ...]:
    return _validate_layout(layout)
