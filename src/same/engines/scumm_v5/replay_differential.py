"""Compare static and resident-selector SCUMM replay observations.

Selector bytes and emulator frames are deliberately not semantic identities.
The comparison works from live activation records at each checkpoint, not a
union of scripts observed over the entire route.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


CHECKPOINTS = (
    "post_use", "post_room5_rope", "post_room6_books", "post_room7_book",
    "post_room7_cat118", "post_room7_cat119", "final_snapshot",
)

SEMANTIC_STATE_FIELDS = (
    "room", "phase", "error", "lifecycle", "actor1_room", "actor1_x",
    "actor1_y", "actor1_moving", "actor1_visible", "mode", "verb",
    "object", "hit_object", "sentence_pending", "talk_active",
    "talk_have_msg", "c20_count", "c19_stack_pointer", "bit35",
    "bit64_71", "bit69", "object61_state", "object61_owner",
)


def _snapshot(report: dict[str, Any], checkpoint: str) -> dict[str, Any]:
    value = report.get(checkpoint)
    if checkpoint == "final_snapshot":
        if not isinstance(value, dict):
            raise ValueError(f"missing {checkpoint}")
        return value
    if not isinstance(value, dict) or not isinstance(value.get("final"), dict):
        raise ValueError(f"missing settled snapshot for {checkpoint}")
    return value["final"]


def _program_unit_identity(slot: dict[str, Any]) -> str:
    """Return a canonical program-unit identity without consulting selector."""
    identity = slot.get("program_unit_identity")
    if isinstance(identity, str) and identity:
        return identity
    script = slot.get("script")
    owner = slot.get("room_owner")
    if not isinstance(script, int) or not isinstance(owner, int):
        raise ValueError("active slot lacks canonical identity and source owner")
    if owner == 0:
        return f"GlobalProgram({script})"
    return f"RoomLocalProgram(room={owner},local={script})"


def _active_slots(
    snapshot: dict[str, Any], *, peer_slots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    slots = snapshot.get("slots")
    if not isinstance(slots, list):
        raise ValueError("snapshot has no activation slot list")
    peers = {row.get("slot"): row for row in peer_slots or []}
    active = []
    for slot in slots:
        status = slot.get("status", 0)
        if not status:
            continue
        identity = slot.get("program_unit_identity")
        provenance = "native canonical binding" if identity else "source fields"
        if not identity and peer_slots is not None:
            peer = peers.get(slot.get("slot"))
            if peer is None or peer.get("script") != slot.get("script"):
                raise ValueError(
                    "static activation cannot be paired to a matching dynamic "
                    f"C4 owner (slot={slot.get('slot')})"
                )
            identity = peer.get("identity")
            if not isinstance(identity, str) or not identity:
                raise ValueError("paired dynamic activation lacks canonical identity")
            provenance = "paired dynamic identity; static slot/script/status verified"
        if not identity:
            identity = _program_unit_identity(slot)
        active.append({
            "identity": identity,
            "identity_provenance": provenance,
            "slot": slot.get("slot"),
            "script": slot.get("script"),
            "status": status,
            "room_owner": slot.get("room_owner"),
            "delay": slot.get("delay"),
            "delay_active": bool(slot.get("delay", 0)),
            "freeze_resistant": slot.get("freeze_resistant"),
            "freeze_count": slot.get("freeze_count"),
            # Kept separately in the report because instruction-boundary
            # timing may differ while the activation identity/status agrees.
            "saved_pc": slot.get("saved_pc"),
        })
    return sorted(active, key=lambda row: (
        row["identity"], int(row["status"]), int(row["room_owner"] or 0),
        int(row["delay"] or 0), int(row["slot"] or 0), int(row["saved_pc"] or 0),
    ))


def compare_replay_reports(
    static: dict[str, Any], dynamic: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic semantic comparison of two bounded route reports."""
    checkpoint_rows = []
    all_semantic_match = True
    all_live_script_match = True
    continuation_pc_differences = []
    scheduler_delay_differences = []
    for checkpoint in CHECKPOINTS:
        left = _snapshot(static, checkpoint)
        right = _snapshot(dynamic, checkpoint)
        compared_fields = [field for field in SEMANTIC_STATE_FIELDS
                           if field in left and field in right]
        missing_fields = [field for field in SEMANTIC_STATE_FIELDS
                          if field not in left or field not in right]
        state_differences = {
            field: {"static": left.get(field), "dynamic": right.get(field)}
            for field in compared_fields if left[field] != right[field]
        }
        right_slots = _active_slots(right)
        left_slots = _active_slots(left, peer_slots=right_slots)
        # Selector and generation are intentionally excluded. Preserve the
        # physical activation slot, scheduler status, room ownership and
        # freeze state, but compare delay as runnable-vs-waiting: exact ticks
        # are timing-sensitive and are reported independently below.
        slot_projection = lambda rows: Counter((
            row["identity"], row["status"], row["room_owner"],
            row["delay_active"], row["freeze_resistant"],
            row["freeze_count"], row["slot"],
        ) for row in rows)
        slot_match = slot_projection(left_slots) == slot_projection(right_slots)
        all_live_script_match &= slot_match
        left_pc = Counter((row["identity"], row["saved_pc"]) for row in left_slots)
        right_pc = Counter((row["identity"], row["saved_pc"]) for row in right_slots)
        pc_match = left_pc == right_pc
        if not pc_match:
            continuation_pc_differences.append({
                "checkpoint": checkpoint,
                "static": [{"identity": identity, "pc": pc}
                           for identity, pc in sorted(left_pc.elements(), key=str)],
                "dynamic": [{"identity": identity, "pc": pc}
                            for identity, pc in sorted(right_pc.elements(), key=str)],
            })
        left_delays = Counter((row["identity"], row["delay"]) for row in left_slots)
        right_delays = Counter((row["identity"], row["delay"]) for row in right_slots)
        if left_delays != right_delays:
            scheduler_delay_differences.append({
                "checkpoint": checkpoint,
                "static": [{"identity": identity, "delay": delay}
                           for identity, delay in sorted(left_delays.elements(), key=str)],
                "dynamic": [{"identity": identity, "delay": delay}
                            for identity, delay in sorted(right_delays.elements(), key=str)],
            })
        fields_complete = not missing_fields
        match = fields_complete and not state_differences and slot_match
        all_semantic_match &= match
        checkpoint_rows.append({
            "checkpoint": checkpoint,
            "semantic_state_match": not state_differences and fields_complete,
            "active_program_units_match": slot_match,
            "continuation_pc_match": pc_match,
            "semantic_match": match,
            "compared_state_fields": compared_fields,
            "missing_state_fields": missing_fields,
            "state_differences": state_differences,
            "static_active_program_units": left_slots,
            "dynamic_active_program_units": right_slots,
        })
    return {
        "schema": "same_scumm_replay_semantic_differential_v1",
        "static_rom_sha256": static.get("rom_sha256"),
        "dynamic_rom_sha256": dynamic.get("rom_sha256"),
        "static_dynamic_residency": static.get("dynamic_residency"),
        "dynamic_dynamic_residency": dynamic.get("dynamic_residency"),
        "static_route_result": static.get("result"),
        "dynamic_route_result": dynamic.get("result"),
        "all_semantic_acceptance_checks_pass": bool(
            all_semantic_match and static.get("result") == "pass"
            and dynamic.get("result") == "pass"
        ),
        # Keep the aggregate activation claim separate from the full state and
        # route-result gate. This lets evidence consumers tell a live-script
        # mismatch from an unrelated semantic field or final-result failure.
        "all_live_script_checks_pass": bool(all_live_script_match),
        "identity_rule": (
            "Compare active canonical ProgramUnit identity, status, owner and "
            "lifetime fields per checkpoint; never compare ephemeral selectors "
            "or a route-wide union of observed scripts."
        ),
        "continuation_pc_rule": (
            "PC equality is reported independently: timing-sensitive transient "
            "offsets do not alter identity/status comparison, and remain visible."
        ),
        "checkpoints": checkpoint_rows,
        "continuation_pc_differences": continuation_pc_differences,
        "scheduler_delay_differences": scheduler_delay_differences,
    }
