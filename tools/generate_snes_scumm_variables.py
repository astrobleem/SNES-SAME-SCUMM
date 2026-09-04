#!/usr/bin/env python3
"""Generate the source-bound SNES SCUMM v5 dense-global contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

BASE = 0x7E0800
STACK_FLOOR = 0x7E1800
EXPECTED_MAXS_SHA = {
    "004c043e2371f1f75f81df26184eda89fef95c7d6886b84deeffa07ac1c0f98f",
    "884b8f381d75ef21c89bd953caad18365a6f319275a6ce1bbd849d3768c57178",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--include", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()

    with zipfile.ZipFile(args.archive) as bundle:
        members = [name for name in bundle.namelist() if name.upper().endswith(".000")]
        if len(members) != 1:
            raise RuntimeError("archive must contain one SCUMM .000 member")
        member = members[0]
        encoded = bundle.read(member)
    decoded = bytes(value ^ 0x69 for value in encoded)
    offset = decoded.find(b"MAXS")
    if offset < 0 or offset + 8 > len(decoded):
        raise RuntimeError("authentic MAXS chunk is unavailable")
    size = struct.unpack_from(">I", decoded, offset + 4)[0]
    if size != 26 or offset + size > len(decoded):
        raise RuntimeError(f"unexpected MAXS size {size}")
    record = decoded[offset:offset + size]
    digest = hashlib.sha256(record).hexdigest()
    if digest not in EXPECTED_MAXS_SHA:
        raise RuntimeError(f"MAXS identity mismatch: {digest}")
    fields = struct.unpack_from("<9H", record, 8)
    count = fields[0]
    byte_count = count * 2
    end = BASE + byte_count
    guard = STACK_FLOOR - end
    if count <= 0 or count > 0x1000 or BASE & 1 or end > STACK_FLOOR:
        raise RuntimeError("generated global-variable range is invalid")
    if BASE < 0x7E0800 or end > 0x7E1800 or (BASE >> 16) != ((end - 1) >> 16):
        raise RuntimeError("global-variable range violates low-WRAM contract")

    args.include.parent.mkdir(parents=True, exist_ok=True)
    args.include.write_text(
        "; Generated from the profile-owned authentic SCUMM v5 MAXS record.\n"
        f"SAME_SCUMM_VARIABLES = ${BASE:06X}\n"
        f"SAME_SCUMM_VARIABLE_COUNT = ${count:04X}\n"
        f"SAME_SCUMM_VARIABLE_BYTES = ${byte_count:04X}\n"
        f"SAME_SCUMM_VARIABLE_LAST = ${count - 1:04X}\n"
        f"SAME_SCUMM_VARIABLE_END = ${end:06X}\n"
        f"SAME_SCUMM_VARIABLE_STACK_FLOOR = ${STACK_FLOOR:06X}\n"
        f"SAME_SCUMM_VARIABLE_GUARD_BYTES = ${guard:04X}\n",
        encoding="utf-8",
    )
    manifest = {
        "format": "same-scumm-v5-global-variables", "schema": 1,
        "profile_identity": hashlib.sha256(args.profile.read_bytes()).hexdigest(),
        "maxs_source": member, "maxs_offset": offset, "maxs_sha256": digest,
        "variable_count": count, "entry_bytes": 2, "variable_bytes": byte_count,
        "table_base": f"{BASE:06X}", "table_end": f"{end:06X}",
        "stack_floor": f"{STACK_FLOOR:06X}", "guard_bytes": guard,
        "maxs_fields": {"second_word": fields[1], "bit_variables": fields[2],
                        "local_objects": fields[3], "arrays": fields[4],
                        "charsets": fields[5], "verbs": fields[6],
                        "new_names": fields[7], "inventory_objects": fields[8]},
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
