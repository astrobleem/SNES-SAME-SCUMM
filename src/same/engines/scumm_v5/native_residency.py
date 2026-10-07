"""Stable, selector-free directory for the native resident-program prototype.

The IDs in this module name compiler ProgramUnits.  They are deliberately a
different namespace from the one-byte selectors consumed by the SCUMM VM.
The 65816 resolver may bind these IDs to a selector for a limited lifetime.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping


SCHEMA = "same_scumm_v5_native_program_directory_v1"
UNBOUND_ID = 0xFFFF
MAX_PROGRAM_UNITS = UNBOUND_ID


def canonical_unit_identity(kind: str, *, room: int | None, number: int) -> str:
    """Return the source-independent backend ProgramUnit identity."""
    if kind in {"GLOBAL", "SCRP"}:
        return f"GlobalProgram({number})"
    if room is None:
        raise ValueError(f"{kind} ProgramUnit requires a room")
    if kind in {"ENCD", "ROOM_ENTRY"}:
        return f"RoomEntryProgram({room})"
    if kind in {"EXCD", "ROOM_EXIT"}:
        return f"RoomExitProgram({room})"
    if kind in {"LSCR", "ROOM_LOCAL"}:
        return f"RoomLocalProgram(room={room},local={number})"
    if kind in {"OBCD", "OBJECT"}:
        return f"ObjectProgram(room={room},object={number})"
    raise ValueError(f"unknown selector-bearing program kind {kind!r}")


@dataclass(frozen=True, slots=True)
class NativeProgramDirectory:
    """Validated stable ID mapping and generated lookup metadata."""

    document: dict[str, Any]

    @classmethod
    def from_programs(cls, programs: list[Mapping[str, Any]]) -> "NativeProgramDirectory":
        by_identity: dict[str, Mapping[str, Any]] = {}
        for row in programs:
            if not row.get("selector_required", True):
                continue
            identity = str(row["identity"])
            previous = by_identity.get(identity)
            if previous is not None:
                if (previous.get("sha256") != row.get("sha256")
                        or previous.get("length") != row.get("length")):
                    raise ValueError(f"conflicting duplicate ProgramUnit {identity}")
                continue
            by_identity[identity] = row
        identities = sorted(by_identity)
        if len(identities) > MAX_PROGRAM_UNITS:
            raise ValueError(f"ProgramUnit directory exceeds 16-bit ID capacity: {len(identities)}")
        ids = {identity: index for index, identity in enumerate(identities)}
        entries = []
        for identity in identities:
            row = by_identity[identity]
            entries.append({
                "program_unit_id": ids[identity],
                "identity": identity,
                "kind": row.get("kind"),
                "room": row.get("room"),
                "number": row.get("number"),
                "length": int(row.get("length", 0)),
                "sha256": row.get("sha256"),
                "bundle": row.get("bundle"),
                "bundle_local_index": row.get("bundle_local_index"),
                "source_provenance": row.get("source_provenance"),
                "dispatch": row.get("dispatch", {}),
            })
        globals_ = [
            {"script_number": int(row["number"]),
             "program_unit_id": ids[row["identity"]]}
            for row in entries if row["kind"] == "GLOBAL"
        ]
        bundles: dict[str, list[int]] = {}
        for row in entries:
            bundle = str(row.get("bundle") or "")
            if bundle:
                bundles.setdefault(bundle, []).append(int(row["program_unit_id"]))
        document = {
            "schema": SCHEMA,
            "id_width_bits": 16,
            "unbound_id": UNBOUND_ID,
            "selector_values_emitted": False,
            "identity_policy": "lexicographic canonical ProgramUnit identity within exact compiler input",
            "entries": entries,
            "global_directory": sorted(globals_, key=lambda item: item["script_number"]),
            "bundles": [
                {"identity": identity, "program_unit_ids": ids}
                for identity, ids in sorted(bundles.items())
            ],
        }
        return cls(document)

    @classmethod
    def from_selector_directory(
        cls, source: Mapping[str, Any], *, program_metadata: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> "NativeProgramDirectory":
        """Promote the existing selector-free IR directory without reparsing."""
        metadata = program_metadata or {}
        programs: list[dict[str, Any]] = []
        for bundle in source.get("bundles", []):
            for unit in bundle.get("selector_units", []):
                identity = str(unit["selector_unit_identity"])
                extra = dict(metadata.get(identity, {}))
                owner = unit.get("owner", {})
                programs.append({
                    "identity": identity,
                    "kind": unit.get("kind"),
                    "room": owner.get("room"),
                    "number": owner.get("global", owner.get("local", owner.get("object"))),
                    "bundle": bundle.get("identity"),
                    "bundle_local_index": unit.get("local_bundle_index"),
                    "source_provenance": unit.get("source_provenance"),
                    "dispatch": unit.get("dispatch_metadata", {}),
                    **extra,
                })
        return cls.from_programs(programs)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def canonical_bytes(self) -> bytes:
        return (json.dumps(self.document, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True) + "\n").encode("ascii")

    def id_for(self, identity: str) -> int:
        for row in self.document["entries"]:
            if row["identity"] == identity:
                return int(row["program_unit_id"])
        raise KeyError(identity)


def directory_assembly(directory: NativeProgramDirectory) -> str:
    """Emit selector-free 16-bit directory data for a Poppy include."""
    entries = directory.document["entries"]
    lines = [
        "; Generated canonical ProgramUnit IDs; never resident selectors.",
        f"SCUMM_RESIDENT_UNIT_COUNT = ${len(entries):04X}",
        f"SCUMM_RESIDENT_GLOBAL_COUNT = ${len(directory.document['global_directory']):04X}",
        f"SCUMM_RESIDENT_DIRECTORY_SHA256 = \"{directory.sha256}\"",
    ]
    globals_ = directory.document["global_directory"]
    lines.extend(("ScummV5_Resident_GlobalScriptNumbers:",))
    if globals_:
        for start in range(0, len(globals_), 16):
            lines.append("    .byte " + ",".join(
                f"${int(item['script_number']) & 0xff:02X}"
                for item in globals_[start:start + 16]
            ))
    else:
        lines.append("    .byte $00")
    lines.append("ScummV5_Resident_GlobalProgramUnitIds:")
    if globals_:
        for start in range(0, len(globals_), 8):
            lines.append("    .word " + ",".join(
                f"${int(item['program_unit_id']):04X}"
                for item in globals_[start:start + 8]
            ))
    else:
        lines.append("    .word $FFFF")
    return "\n".join(lines) + "\n"
