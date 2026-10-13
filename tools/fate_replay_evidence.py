"""Durable, identity-bound snapshots for long native FATE replay runs.

The append-only journal is written and fsynced before a human-readable report
is atomically replaced.  A failed final report write therefore cannot erase
observations already collected from the emulator.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

IDENTITY_FIELDS = (
    "rom_sha256",
    "map_sha256",
    "build_identity_sha256",
    "archive_sha256",
    "program_directory_sha256",
)
JOURNAL_SCHEMA = "same_fate_native_replay_journal_v1"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8") + b"\n"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def identity_from(report: Mapping[str, Any]) -> dict[str, str]:
    identity: dict[str, str] = {}
    for key in IDENTITY_FIELDS:
        value = report.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ValueError(f"native replay snapshot lacks a SHA-256 {key}")
        try:
            bytes.fromhex(value)
        except ValueError as exc:
            raise ValueError(f"native replay snapshot has invalid {key}") from exc
        identity[key] = value.lower()
    head = report.get("starting_head")
    if isinstance(head, str) and head:
        identity["starting_head"] = head
    return identity


def _record_body(sequence: int, previous: str | None,
                 report: Mapping[str, Any]) -> dict[str, Any]:
    payload = canonical_bytes(report)
    return {
        "schema": JOURNAL_SCHEMA,
        "sequence": sequence,
        "previous_record_sha256": previous,
        "identity": identity_from(report),
        "snapshot_sha256": digest(payload),
        "snapshot": report,
    }


def read_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    previous_hash: str | None = None
    expected_identity: dict[str, str] | None = None
    for sequence, line in enumerate(path.read_bytes().splitlines(), 1):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"invalid replay journal record {sequence}") from exc
        if record.get("schema") != JOURNAL_SCHEMA or record.get("sequence") != sequence:
            raise ValueError(f"replay journal sequence/schema mismatch at {sequence}")
        if record.get("previous_record_sha256") != previous_hash:
            raise ValueError(f"replay journal hash chain breaks at {sequence}")
        snapshot = record.get("snapshot")
        if not isinstance(snapshot, dict):
            raise ValueError(f"replay journal snapshot {sequence} is not an object")
        identity = identity_from(snapshot)
        if identity != record.get("identity"):
            raise ValueError(f"replay journal identity mismatch at {sequence}")
        if expected_identity is None:
            expected_identity = identity
        elif identity != expected_identity:
            raise ValueError(f"replay journal changes build identity at {sequence}")
        if digest(canonical_bytes(snapshot)) != record.get("snapshot_sha256"):
            raise ValueError(f"replay journal snapshot hash mismatch at {sequence}")
        unsigned = dict(record)
        record_hash = unsigned.pop("record_sha256", None)
        actual_hash = digest(canonical_bytes(unsigned))
        if record_hash != actual_hash:
            raise ValueError(f"replay journal record hash mismatch at {sequence}")
        previous_hash = actual_hash
        records.append(record)
    return records


class ReplayEvidenceJournal:
    """Append complete report snapshots in an identity-locked hash chain."""

    def __init__(self, path: Path):
        self.path = path
        records = read_journal(path)
        self.sequence = len(records)
        self.previous_hash = records[-1]["record_sha256"] if records else None
        self.identity = records[-1]["identity"] if records else None

    def append(self, report: Mapping[str, Any]) -> str:
        identity = identity_from(report)
        if self.identity is not None and identity != self.identity:
            raise ValueError("refusing to append replay evidence from another build identity")
        body = _record_body(self.sequence + 1, self.previous_hash, report)
        record_hash = digest(canonical_bytes(body))
        record = {**body, "record_sha256": record_hash}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            with os.fdopen(fd, "ab", closefd=True) as stream:
                stream.write(canonical_bytes(record))
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            # fdopen owns the descriptor after construction.
            raise
        self.sequence += 1
        self.previous_hash = record_hash
        self.identity = identity
        return record_hash


def evidence_provenance(report: Mapping[str, Any]) -> dict[str, Any]:
    """Classify only observed, hash-bound, and absent data; infer no values."""
    native_paths: list[str] = []
    reused_paths: list[str] = []
    for key in ("checkpoints", "room_observations", "final_snapshot",
                "room5_entry", "room6_entry", "room7_entry", "room3_entry",
                "controller_submissions", "residency_summary", "coverage_gaps"):
        if key not in report:
            continue
        if key in ("room5_entry", "room5_rope_action", "checkpoints") and (
                report.get("resume_report_sha256") or report.get("room5_entry_report_sha256")):
            reused_paths.append(key)
        else:
            native_paths.append(key)
    missing: list[str] = []
    room_observations = report.get("room_observations", {})
    room5 = room_observations.get("5") if isinstance(room_observations, dict) else None
    if isinstance(room5, dict):
        check = (room5.get("presentation_at_checkpoint", {})
                 .get("full_vram_check"))
        if check is None:
            missing.append("room_observations.5.presentation_at_checkpoint.full_vram_check")
    gaps = report.get("coverage_gaps", {})
    if isinstance(gaps, dict):
        missing.extend(str(key) for key, value in gaps.items()
                       if isinstance(value, str) and value.startswith("NOT_CAPTURED:"))
    return {
        "native_observation_paths": sorted(native_paths),
        "hash_bound_reused_paths": sorted(reused_paths),
        "not_captured": sorted(missing),
        "no_observations_inferred": True,
    }


def recover_latest(path: Path, *, expected_identity: Mapping[str, str] | None = None
                   ) -> dict[str, Any]:
    records = read_journal(path)
    if not records:
        raise ValueError("replay evidence journal is empty")
    latest = records[-1]
    identity = latest["identity"]
    if expected_identity is not None and dict(expected_identity) != identity:
        raise ValueError("journal does not match requested replay identity")
    report = dict(latest["snapshot"])
    report["evidence_recovery"] = {
        "status": "RECOVERED_DURABLE_SNAPSHOT",
        "journal_sequence": latest["sequence"],
        "journal_record_sha256": latest["record_sha256"],
        "identity": identity,
        "provenance": evidence_provenance(report),
        "native_execution_result_preserved_verbatim": report.get("result"),
    }
    return report


def atomic_write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
