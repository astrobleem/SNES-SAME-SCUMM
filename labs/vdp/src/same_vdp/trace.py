from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

TRACE_MAGIC = "same-vdp-trace"
TRACE_VERSION = 1


class TraceError(ValueError):
    """Raised when a SAME-VDP trace is malformed."""


def intish(value: Any, *, field: str = "value") -> int:
    if isinstance(value, bool):
        raise TraceError(f"{field} must be an integer, not bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError as exc:
            raise TraceError(f"{field} is not an integer: {value!r}") from exc
    raise TraceError(f"{field} must be an integer or 0x-prefixed string")


@dataclass(frozen=True)
class Trace:
    header: dict[str, Any]
    events: tuple[dict[str, Any], ...]
    source: Path | None = None

    @property
    def name(self) -> str:
        return str(self.header["name"])

    @property
    def width(self) -> int:
        return int(self.header["video"]["width"])

    @property
    def height(self) -> int:
        return int(self.header["video"]["height"])


def validate_header(header: dict[str, Any]) -> None:
    if header.get("format") != TRACE_MAGIC:
        raise TraceError(f"header.format must be {TRACE_MAGIC!r}")
    if intish(header.get("version"), field="header.version") != TRACE_VERSION:
        raise TraceError(f"unsupported trace version: {header.get('version')!r}")
    if not isinstance(header.get("name"), str) or not header["name"]:
        raise TraceError("header.name must be a non-empty string")
    video = header.get("video")
    if not isinstance(video, dict):
        raise TraceError("header.video must be an object")
    width = intish(video.get("width"), field="header.video.width")
    height = intish(video.get("height"), field="header.video.height")
    if width not in (256, 320):
        raise TraceError("video width must be 256 (H32) or 320 (H40)")
    if height not in (224, 240):
        raise TraceError("video height must be 224 or 240")


def validate_event(event: dict[str, Any], line_number: int) -> None:
    op = event.get("op")
    if not isinstance(op, str):
        raise TraceError(f"line {line_number}: event.op must be a string")
    if op in {"ctrl", "data"}:
        value = intish(event.get("value"), field=f"line {line_number} value")
        if not 0 <= value <= 0xFFFF:
            raise TraceError(f"line {line_number}: {op} value exceeds 16 bits")
    elif op == "data_words":
        values = event.get("values")
        if not isinstance(values, list):
            raise TraceError(f"line {line_number}: data_words.values must be an array")
        for index, raw in enumerate(values):
            value = intish(raw, field=f"line {line_number} values[{index}]")
            if not 0 <= value <= 0xFFFF:
                raise TraceError(f"line {line_number}: values[{index}] exceeds 16 bits")
    elif op in {"frame", "comment"}:
        return
    else:
        raise TraceError(f"line {line_number}: unsupported operation {op!r}")


def read_trace(path: str | Path) -> Trace:
    source = Path(path)
    records: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TraceError(f"{source}:{line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise TraceError(f"{source}:{line_number}: each record must be an object")
            records.append(record)
    if not records:
        raise TraceError(f"{source}: empty trace")
    header = records[0]
    validate_header(header)
    for index, event in enumerate(records[1:], start=2):
        validate_event(event, index)
    return Trace(header=header, events=tuple(records[1:]), source=source)


def write_trace(path: str | Path, header: dict[str, Any], events: Iterable[dict[str, Any]]) -> None:
    validate_header(header)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(header, sort_keys=True, separators=(",", ":")) + "\n")
        for line_number, event in enumerate(events, start=2):
            validate_event(event, line_number)
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
