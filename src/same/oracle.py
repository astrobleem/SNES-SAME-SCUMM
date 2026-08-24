"""Fail-closed validation records for guest, video, audio, and event evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
from typing import Iterable

from .errors import SameError

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
FIELDS = ("state", "video", "audio", "events")


class OracleError(SameError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise OracleError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class OracleRecord:
    tick: int
    state: str | None = None
    video: str | None = None
    audio: str | None = None
    events: str | None = None
    identity: str | None = None

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise OracleError("oracle tick cannot be negative")
        for name in FIELDS:
            value = getattr(self, name)
            if value is not None and not HASH_RE.fullmatch(value):
                raise OracleError(f"{name} hash is not a lowercase SHA-256 digest")
        if self.identity is not None and not self.identity:
            raise OracleError("identity cannot be empty")

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "tick": self.tick,
            "identity": self.identity,
            "state": self.state,
            "video": self.video,
            "audio": self.audio,
            "events": self.events,
        }


@dataclass(frozen=True, slots=True)
class FieldComparison:
    tick: int
    field: str
    status: str
    expected: str | None
    actual: str | None

    def to_dict(self) -> dict[str, int | str | None]:
        return {
            "tick": self.tick,
            "field": self.field,
            "status": self.status,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True, slots=True)
class OracleComparison:
    status: str
    expected_identity: str | None
    actual_identity: str | None
    expected_ticks: int
    actual_ticks: int
    matched: int
    mismatched: int
    unknown: int
    fields: tuple[FieldComparison, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "expected_identity": self.expected_identity,
            "actual_identity": self.actual_identity,
            "expected_ticks": self.expected_ticks,
            "actual_ticks": self.actual_ticks,
            "matched": self.matched,
            "mismatched": self.mismatched,
            "unknown": self.unknown,
            "fields": [field.to_dict() for field in self.fields],
        }


def write_records(path: Path, records: Iterable[OracleRecord]) -> None:
    materialized = list(records)
    previous = -1
    for record in materialized:
        if record.tick <= previous:
            raise OracleError("oracle records must be strictly increasing by tick")
        previous = record.tick
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record.to_dict(), sort_keys=True) + "\n" for record in materialized),
        encoding="utf-8",
    )


def read_records(path: Path) -> list[OracleRecord]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OracleError(f"cannot read oracle file {path}: {exc}") from exc
    records: list[OracleRecord] = []
    previous = -1
    for line_number, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OracleError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise OracleError(f"{path}:{line_number}: record must be an object")
        record = OracleRecord(
            tick=int(raw.get("tick", -1)),
            identity=(None if raw.get("identity") is None else str(raw.get("identity"))),
            state=(None if raw.get("state") is None else str(raw.get("state"))),
            video=(None if raw.get("video") is None else str(raw.get("video"))),
            audio=(None if raw.get("audio") is None else str(raw.get("audio"))),
            events=(None if raw.get("events") is None else str(raw.get("events"))),
        )
        if record.tick <= previous:
            raise OracleError(f"{path}:{line_number}: ticks are not strictly increasing")
        previous = record.tick
        records.append(record)
    if not records:
        raise OracleError(f"oracle file {path} contains no records")
    return records


def compare_records(
    expected: Iterable[OracleRecord], actual: Iterable[OracleRecord]
) -> OracleComparison:
    expected_records = list(expected)
    actual_records = list(actual)
    expected_by_tick = {record.tick: record for record in expected_records}
    actual_by_tick = {record.tick: record for record in actual_records}
    fields: list[FieldComparison] = []
    for tick in sorted(set(expected_by_tick) | set(actual_by_tick)):
        expected_record = expected_by_tick.get(tick)
        actual_record = actual_by_tick.get(tick)
        for field in FIELDS:
            wanted = None if expected_record is None else getattr(expected_record, field)
            observed = None if actual_record is None else getattr(actual_record, field)
            if expected_record is None:
                status = "unexpected"
            elif wanted is None:
                status = "not_required"
            elif actual_record is None or observed is None:
                status = "unknown"
            elif wanted == observed:
                status = "match"
            else:
                status = "mismatch"
            fields.append(FieldComparison(tick, field, status, wanted, observed))
    matched = sum(field.status == "match" for field in fields)
    mismatched = sum(field.status in {"mismatch", "unexpected"} for field in fields)
    unknown = sum(field.status == "unknown" for field in fields)
    required = sum(field.status not in {"not_required", "unexpected"} for field in fields)
    identity_expected = expected_records[0].identity if expected_records else None
    identity_actual = actual_records[0].identity if actual_records else None
    identity_mismatch = (
        identity_expected is not None
        and identity_actual is not None
        and identity_expected != identity_actual
    )
    identity_unknown = identity_expected is not None and identity_actual is None
    if mismatched or identity_mismatch:
        status = "FAIL"
    elif unknown or identity_unknown or required == 0 or len(expected_records) != len(actual_records):
        status = "UNKNOWN"
    else:
        status = "PASS"
    return OracleComparison(
        status=status,
        expected_identity=identity_expected,
        actual_identity=identity_actual,
        expected_ticks=len(expected_records),
        actual_ticks=len(actual_records),
        matched=matched,
        mismatched=mismatched + int(identity_mismatch),
        unknown=unknown + int(identity_unknown),
        fields=tuple(fields),
    )


def record_from_files(
    *,
    tick: int,
    identity: str | None = None,
    state: Path | None = None,
    video: Path | None = None,
    audio: Path | None = None,
    events: Path | None = None,
) -> OracleRecord:
    return OracleRecord(
        tick=tick,
        identity=identity,
        state=None if state is None else sha256_file(state),
        video=None if video is None else sha256_file(video),
        audio=None if audio is None else sha256_file(audio),
        events=None if events is None else sha256_file(events),
    )
