"""Small reusable pieces for bounded, controller-only FATE replays."""

from __future__ import annotations

from typing import Any, Mapping


ROOM4_OPEN_TRAPDOOR_PRECONDITION = {
    "room": 4,
    "phase": 0,
    "error": 0,
    "engine_lifecycle": 2,
    "controller_ready": 1,
    "talk_active": 0,
    "controller_mode": 0,
    "cursor_world": (117, 138),
}


def _read_u16(session: Any, address: int) -> int:
    return int.from_bytes(session.read_memory("snesMemory", address, 2), "little")


def room4_controller_snapshot(session: Any) -> dict[str, int]:
    """Read the ordinary controller/scene state used by the saved prefix."""
    c19_depth = session.read_u8(0x7FD348)
    c19_override_pc = _read_u16(session, 0x7FD354 + c19_depth * 2)
    c19_override_slot = session.read_u8(0x7FD35E + c19_depth)
    return {
        "room": session.read_u8(0x7FF2BF),
        "phase": session.read_u8(0x7FF2C2),
        "error": session.read_u8(0x7E2303),
        "lifecycle": session.read_u8(0x7E2221),
        "ready": session.read_u8(0x7E5E8A),
        "controller_diag": session.read_u8(0x7E5FEC),
        "controller_diag_input": session.read_u8(0x7E5FEF),
        "talk_active": session.read_u8(0x7E7A20),
        "talk_have_msg": session.read_u8(0x7E7A21),
        "talk_delay": _read_u16(session, 0x7E7A24),
        "talk_generation": _read_u16(session, 0x7E7A26),
        "mode": session.read_u8(0x7E5FE0),
        "x": _read_u16(session, 0x7E5FE1),
        "y": _read_u16(session, 0x7E5FE3),
        "verb": session.read_u8(0x7E5FE5),
        "object": _read_u16(session, 0x7E5FE6),
        "hit_object": _read_u16(session, 0x7E5F94),
        "submissions": session.read_u8(0x7E5FE9),
        "input_held": _read_u16(session, 0x7E2200),
        "input_previous": _read_u16(session, 0x7E2202),
        "input_released": _read_u16(session, 0x7E2206),
        "input_pressed": _read_u16(session, 0x7E2204),
        "edge_sequence": _read_u16(session, 0x7E2208),
        "joy1l": _read_u16(session, 0x004218),
        "emulator_frame": int(session.get_state()["frameCount"]),
        "talk_owned_sequence": _read_u16(session, 0x7E220A),
        "talk_owned_valid": session.read_u8(0x7E220C),
        "sentence_pending": session.read_u8(0x7E7EC7),
        "c20_count": session.read_u8(0x7FD380),
        "c19_stack_pointer": session.read_u8(0x7FD348),
        "c19_override_pc": c19_override_pc,
        "c19_override_slot": c19_override_slot,
        "c19_override_script": session.read_u8(0x7E2399 + c19_override_slot),
        "c19_override_program": session.read_u8(0x7E23B2 + c19_override_slot),
        "c19_override_room": session.read_u8(0x7FF2E7 + c19_override_slot),
        "c19_override_slot_depth": session.read_u8(0x7FD363 + c19_override_slot),
        "null_scene": session.read_u8(0x7FD407),
        "c31_room": session.read_u8(0x7FF241),
        "c31_initialized": session.read_u8(0x7FF242),
        "c31_actor1_x": _read_u16(session, 0x7FF1A4),
        "c31_actor1_y": _read_u16(session, 0x7FF1A6),
    }


def _room4_pulse_until(
    session: Any,
    controller: "ControllerInputLease",
    mask: int,
    predicate: Any,
    *,
    press_frames: int = 4,
    release_frames: int = 1,
    poll_frames: int = 45,
    release_poll_address: int | None = None,
    wait_for_release_sample: bool = True,
) -> dict[str, Any]:
    """Send one exact press/neutral interval and observe it.

    Nexen's ``set_input(frames=...)`` is wall-clock driven at max speed, so
    this replay only changes controller level without advancing and uses
    frame-counted runs for every press/release interval. A failed edge is a
    diagnostic boundary; repeating the same input could move the cursor past
    its target and conceal the timing problem.
    """
    before = room4_controller_snapshot(session)
    start_frame = int(session.get_state()["frameCount"])
    controller.hold(mask)
    release_write_handle = None
    release_write_events: list[dict[str, Any]] = []
    release_poll_events: list[dict[str, Any]] = []
    try:
        press = advance_bounded(session, press_frames)
        press_state = room4_controller_snapshot(session)
    finally:
        # Release even when frame advancement or observation raises.
        if hasattr(session, "add_write_hook"):
            release_write_handle = session.add_write_hook(0x7E2200, 0x7E2201)
        controller.release()
    if (press["start_frame"] != start_frame
            or press["frames_advanced"] != press_frames):
        raise RuntimeError(
            f"room-4 press interval was not exactly {press_frames} frames: {press}"
        )

    def drain_release_events() -> None:
        if release_write_handle is None or not hasattr(session, "drain_notifications"):
            return
        for message in session.drain_notifications(timeout=0.0):
            params = message.get("params", message)
            if params.get("handle") == release_write_handle:
                release_write_events.append(dict(params))

    try:
        neutral = advance_bounded(session, release_frames)
        if (neutral["start_frame"] != press["end_frame"]
                or neutral["frames_advanced"] != release_frames):
            raise RuntimeError(
                f"room-4 release interval was not exactly {release_frames} frames: {neutral}"
            )

        observed_input = press_state["input_held"] | press_state["input_pressed"]
        if observed_input == 0:
            raise RuntimeError(
                "room-4 press ended without a sampled native input level; refusing "
                f"to treat the requested duration as an edge: {press_state!r}"
            )

        # A neutral host input level is not yet a released SCUMM edge until the
        # SNES input poll samples it. Wait for that observed transition before a
        # later pulse can be called a distinct physical press.
        release_poll_frames = 0
        after = room4_controller_snapshot(session)
        if wait_for_release_sample:
            while after["input_held"] & observed_input:
                drain_release_events()
                if release_poll_frames >= poll_frames:
                    cpu = session.get_cpu_state() if hasattr(session, "get_cpu_state") else None
                    raise RuntimeError(
                        "room-4 neutral input was not sampled before the release bound: "
                        f"mask=${observed_input:04X}, state={after!r}, "
                        f"native_input_held_writes={release_write_events!r}, cpu={cpu!r}"
                    )
                if release_poll_address is None or not hasattr(session, "add_exec_hook"):
                    neutral_poll = advance_bounded(session, 1)
                    if neutral_poll["frames_advanced"] != 1:
                        raise RuntimeError(
                            f"release-sampling frame advance drifted: {neutral_poll!r}"
                        )
                else:
                    start_poll_frame = int(session.get_state()["frameCount"])
                    poll_handle = session.add_exec_hook(release_poll_address)
                    try:
                        native_poll = session.run_until(
                            max_frames=2, hook_handle=poll_handle
                        )
                        session.pause()
                        end_poll_frame = int(session.get_state()["frameCount"])
                        if native_poll.get("reason") != "hookFired":
                            raise RuntimeError(
                                "native Same_Input_Poll edge-sequence boundary was not "
                                f"reached: {native_poll!r}"
                            )
                        if not 0 <= end_poll_frame - start_poll_frame <= 2:
                            raise RuntimeError(
                                "native release poll exceeded its two-frame bound: "
                                f"{start_poll_frame}->{end_poll_frame}, {native_poll!r}"
                            )
                        poll_events = []
                        for message in session.drain_notifications(timeout=0.0):
                            params = message.get("params", message)
                            if params.get("handle") == poll_handle:
                                poll_events.append(dict(params))
                        if not poll_events:
                            raise RuntimeError(
                                "native release poll breakpoint lacked event-time evidence"
                            )
                        neutral_poll = {
                            "frames_advanced": end_poll_frame - start_poll_frame,
                            "hook_event": poll_events[-1],
                            "tool_result": native_poll,
                        }
                    finally:
                        session.remove_hook(poll_handle)
                release_poll_events.append(neutral_poll)
                release_poll_frames += 1
                after = room4_controller_snapshot(session)
        drain_release_events()
        release_sample_state = after
        release_sample_frame = int(session.get_state()["frameCount"])
    finally:
        if release_write_handle is not None:
            session.remove_hook(release_write_handle)

    for _ in range(poll_frames + 1):
        after = room4_controller_snapshot(session)
        if predicate(before, after):
            return {
                "mask": mask,
                "attempt": 1,
                "start_frame": start_frame,
                "after_press_frame": press["end_frame"],
                "after_release_frame": neutral["end_frame"],
                "press_frames_advanced": press["frames_advanced"],
                "release_frames_advanced": neutral["frames_advanced"],
                "release_sampled": not bool(
                    release_sample_state["input_held"] & observed_input
                ),
                "release_sample_deferred": not wait_for_release_sample and bool(
                    release_sample_state["input_held"] & observed_input
                ),
                "release_poll_frames_after_neutral": release_poll_frames,
                "release_sample_frame": release_sample_frame,
                "release_input_write_events": release_write_events,
                "release_input_poll_events": release_poll_events,
                "input_state_at_press_end": press_state,
                "input_state_after_release_sample": release_sample_state,
                "observed_frame": int(session.get_state()["frameCount"]),
                "before": before,
                "after": after,
            }
        advance_bounded(session, 1)
    raise RuntimeError(
        f"room-4 input ${mask:03X} was not consumed after one exact-frame pulse; "
        f"before={before!r}, after={after!r}"
    )


def controller_synchronous_input_edge(
    session: Any,
    mask: int,
    predicate: Any,
    *,
    max_frames_per_boundary: int = 8,
    post_sample_dispatch_frames: int = 45,
    max_release_sample_frames: int = 45,
) -> dict[str, Any]:
    """Send one edge, observing each exact frame until SCUMM samples it.

    There is no retry of the UI action: the held level remains one physical
    press while the native edge sequence is observed, and the first sampled
    edge must satisfy the requested semantic predicate. Input is then
    released and neutral sampling is verified before another replay step.
    """
    before = room4_controller_snapshot(session)
    if before["input_held"] or before["input_pressed"]:
        raise RuntimeError(
            "cannot start a distinct controller edge while a previous input sample "
            f"is still live: {before!r}"
        )
    sequence_before = before["edge_sequence"]
    with ControllerInputLease(session) as controller:
        start_frame = int(session.get_state()["frameCount"])
        controller.hold(mask)
        press_frames: list[dict[str, Any]] = []
        sampled: dict[str, Any] | None = None
        for _ in range(max_frames_per_boundary):
            advance = advance_bounded(session, 1)
            if advance["frames_advanced"] != 1:
                raise RuntimeError(f"exact input sampling frame drifted: {advance!r}")
            current = room4_controller_snapshot(session)
            press_frames.append({"advance": advance, "state_at_frame_end": current})
            sequence_delta = (current["edge_sequence"] - sequence_before) & 0xFFFF
            if sequence_delta == 1:
                sampled = current
                break
            if sequence_delta != 0:
                raise RuntimeError(
                    "one held controller input level produced an unexpected edge count: "
                    f"before={before!r}, frames={press_frames!r}"
                )
        if sampled is None:
            raise RuntimeError(
                "controller input was not sampled within its exact-frame bound: "
                f"before={before!r}, frames={press_frames!r}"
            )
        press_bits = sampled["input_pressed"] or (sampled["input_held"] & mask)
        if not press_bits or not sampled["input_held"]:
            raise RuntimeError(f"input poll did not capture the held edge: {sampled!r}")
        action_frames = list(press_frames)
        after_action = sampled
        for _ in range(post_sample_dispatch_frames):
            if predicate(before, after_action):
                break
            advance = advance_bounded(session, 1)
            if advance["frames_advanced"] != 1:
                raise RuntimeError(f"one-frame input dispatch drifted: {advance!r}")
            after_action = room4_controller_snapshot(session)
            action_frames.append({
                "advance": advance,
                "state_at_frame_end": after_action,
                "same_held_edge": True,
            })
        if not predicate(before, after_action):
            raise RuntimeError(
                "first sampled controller edge did not produce the expected semantic "
                f"result; no retry was sent: before={before!r}, "
                f"sampled={sampled!r}, frames={action_frames!r}"
            )
        controller.release()
        release_frames: list[dict[str, Any]] = []
        released: dict[str, Any] | None = None
        for _ in range(max_release_sample_frames):
            advance = advance_bounded(session, 1)
            if advance["frames_advanced"] != 1:
                raise RuntimeError(f"exact neutral sampling frame drifted: {advance!r}")
            current = room4_controller_snapshot(session)
            release_frames.append({"advance": advance, "state_at_frame_end": current})
            if (not (current["input_held"] & press_bits)
                    and current["input_released"] & press_bits):
                released = current
                break
        if released is None:
            raise RuntimeError(
                "neutral controller input was not sampled within its exact-frame bound: "
                f"press_bits=${press_bits:04X}, frames={release_frames!r}"
            )
    if released["edge_sequence"] != sampled["edge_sequence"]:
        raise RuntimeError(
            "neutral release unexpectedly created another press sequence: "
            f"sampled={sampled!r}, released={released!r}"
        )
    return {
        "mask": mask,
        "attempts": 1,
        "input_level_start_frame": start_frame,
        "press_frames_to_sample": sampled["emulator_frame"] - start_frame,
        "press_frames": action_frames,
        "release_frames": release_frames,
        "release_sampled": True,
        "before": before,
        "after": released,
        "action_state_at_sample_frame_end": after_action,
    }


def room4_synchronous_input_edge(
    session: Any,
    mask: int,
    predicate: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compatibility name for the room-4 replay's generic exact-edge driver."""
    return controller_synchronous_input_edge(session, mask, predicate, **kwargs)


def skip_room4_authored_override(
    session: Any,
    *,
    release_poll_address: int | None = None,
    defer_release_sample: bool = False,
) -> dict[str, Any]:
    """Skip the active, source-authentic room-4 LSCR206 intro override once.

    The accepted cold profile reaches room 4 while its authored beginOverride
    is still active. The controller correctly rejects movement until that
    cutscene is ended. This step is allowed only when the current C19 record
    identifies room 4 LSCR206 / program $F9 and its saved continuation $0019;
    it then sends one normal X edge, never writes game state, and waits for
    the ordinary SCUMM endCutscene path to empty the stack.
    """
    before = room4_controller_snapshot(session)
    expected = {
        "room": 4,
        "phase": 0,
        "error": 0,
        "lifecycle": 2,
        "ready": 1,
        "c19_stack_pointer": 1,
        "c19_override_pc": 0x0019,
        "c19_override_slot": 3,
        "c19_override_script": 206,
        "c19_override_program": 0xF9,
        "c19_override_room": 4,
        "c19_override_slot_depth": 1,
    }
    mismatch = {
        key: (before[key], value)
        for key, value in expected.items() if before[key] != value
    }
    if mismatch:
        raise RuntimeError(
            f"room-4 authored override precondition mismatch: {mismatch!r}; "
            f"state={before!r}"
        )

    with ControllerInputLease(session) as controller:
        step = _room4_pulse_until(
            session, controller, 0x100,
            lambda _old, current: (
                current["error"] == 0
                and current["c19_override_pc"] == 0
            ),
            press_frames=4,
            release_frames=1,
            release_poll_address=release_poll_address,
            wait_for_release_sample=not defer_release_sample,
        )
    cleared_record = {
        "stack_index": 1,
        "override_pc": _read_u16(session, 0x7FD354 + 2),
        "override_slot": session.read_u8(0x7FD35E + 1),
        "owner_slot_depth": session.read_u8(0x7FD363 + before["c19_override_slot"]),
    }
    if cleared_record != {
        "stack_index": 1, "override_pc": 0, "override_slot": 0,
        "owner_slot_depth": 0,
    }:
        raise RuntimeError(f"room-4 override record was not consumed: {cleared_record!r}")
    after = room4_controller_snapshot(session)
    if (after["room"] != 4 or after["error"] != 0
            or after["c19_stack_pointer"] != 1):
        raise RuntimeError(f"room-4 override skip left an invalid scene: {after!r}")
    return {
        "action": "skip authored room-4 LSCR206 beginOverride",
        "button": "X",
        "button_mask": "0x100",
        "before": before,
        "step": step,
        "after": after,
        "cleared_override_record": cleared_record,
        "result": "the normal X edge entered the saved LSCR206 override continuation",
    }


def finish_room4_authored_cutscene(session: Any, *, max_frames: int = 300) -> dict[str, Any]:
    """Let the resumed authentic room-4 cutscene run without synthetic input."""
    before = room4_controller_snapshot(session)
    if (before["room"] != 4 or before["error"] != 0
            or before["c19_stack_pointer"] != 1
            or before["c19_override_pc"] != 0):
        raise RuntimeError(f"room-4 cutscene continuation precondition mismatch: {before!r}")

    owner_slot = 3
    owner = lambda: {
        "status": session.read_u8(0x7E2380 + owner_slot),
        "script": session.read_u8(0x7E2399 + owner_slot),
        "program": session.read_u8(0x7E23B2 + owner_slot),
        "saved_pc": _read_u16(session, 0x7E23E4 + owner_slot * 2),
        "room_owner": session.read_u8(0x7FF2E7 + owner_slot),
        "cutscene_depth": session.read_u8(0x7FD363 + owner_slot),
    }
    timeline = [{"frame": int(session.get_state()["frameCount"]),
                 "cutscene_stack": before["c19_stack_pointer"], "owner": owner()}]
    elapsed = 0
    last_signature = (before["c19_stack_pointer"], owner())
    while elapsed < max_frames:
        advanced = advance_bounded(session, min(4, max_frames - elapsed))
        elapsed += advanced["frames_advanced"]
        state = room4_controller_snapshot(session)
        if state["error"]:
            raise RuntimeError(f"SCUMM error during room-4 cutscene continuation: {state!r}")
        current_owner = owner()
        signature = (state["c19_stack_pointer"], current_owner)
        if signature != last_signature:
            timeline.append({
                "frame": int(session.get_state()["frameCount"]),
                "cutscene_stack": state["c19_stack_pointer"],
                "owner": current_owner,
            })
            last_signature = signature
        if state["c19_stack_pointer"] == 0:
            return {
                "idle_frames": elapsed,
                "timeline": timeline,
                "final": state,
                "final_owner": current_owner,
                "result": "authored cutscene completed without further input",
            }
    raise TimeoutError(
        f"room-4 authored cutscene did not end within {max_frames} neutral frames; "
        f"timeline={timeline!r}; final={room4_controller_snapshot(session)!r}; "
        f"owner={owner()!r}"
    )


def replay_room4_open_trapdoor_prefix(
    session: Any,
    *,
    pulse: Any = None,
) -> dict[str, Any]:
    """Replay the recorded normal-controller input tail from room-4 readiness.

    This does not cold-boot or create readiness. The caller must provide the
    exact ROM-bound room-4-ready state documented in
    ``examples/replays/fate-room4-open-trapdoor.json``.
    """
    initial = room4_controller_snapshot(session)
    expected = ROOM4_OPEN_TRAPDOOR_PRECONDITION
    observed = {
        "room": initial["room"],
        "phase": initial["phase"],
        "error": initial["error"],
        "engine_lifecycle": initial["lifecycle"],
        "controller_ready": initial["ready"],
        "talk_active": initial["talk_active"],
        "controller_mode": initial["mode"],
    }
    observed["cursor_world"] = (initial["x"], initial["y"])
    if observed != expected:
        raise RuntimeError(
            f"room-4 replay precondition mismatch: {observed!r} != {expected!r}"
        )

    steps: list[dict[str, Any]] = []
    x, y = initial["x"], initial["y"]

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        with ControllerInputLease(session) as controller:
            return _room4_pulse_until(session, controller, mask, predicate)

    for _ in range(14):
        x -= 2
        steps.append(send(0x040, lambda _before, after, tx=x: after["x"] == tx))
    for _ in range(3):
        y -= 2
        steps.append(send(0x010, lambda _before, after, ty=y: after["y"] == ty))
    steps.append(send(0x001, lambda _before, after: (
        after["mode"] == 1 and after["verb"] == 3
        and after["object"] == 61 and after["hit_object"] == 61
    )))
    steps.append(send(0x001, lambda before, after: (
        after["submissions"] == ((before["submissions"] + 1) & 0xFF)
    )))
    final = room4_controller_snapshot(session)
    if final["error"] != 0 or final["room"] != 4:
        raise RuntimeError(f"room-4 replay left its accepted scene: {final!r}")
    return {
        "precondition": initial,
        "input_schedule": (
            {
                "mode": "hold one level through a sampled edge and its first matching state change",
                "frame_observation": "read native WRAM after each exactly advanced emulator frame",
                "press_frames": "observed per step; bounded input sample then state-change wait",
                "release_frames": "observed per step until native neutral/released state",
                "controller_level_changes_advance_frames": False,
                "equivalent_attempts_per_step": 1,
            }
            if pulse is not None else {
                "press_frames": 4,
                "release_neutral_frames": 1,
                "controller_level_changes_advance_frames": False,
                "equivalent_attempts_per_step": 1,
            }
        ),
        "steps": steps,
        "final": final,
        "result": "controller submitted Open on object 61 at world (89,132)",
    }


def replay_room4_trapdoor_use(
    session: Any,
    *,
    pulse: Any = None,
) -> dict[str, Any]:
    """Select and submit object 61's source-authored Use verb exactly once.

    This continuation is permitted only after the recorded Open action has
    completed and controller revalidation has retained object 61 / verb 3.
    The room's authentic OBCD advertises verbs 3, 4, 9, and 10 in that order;
    the ordinary Y verb-cycle edge therefore advances 3 -> 4 -> 9 -> 10.
    The subsequent A edge submits verb 10 once. No debugger state is written.
    """
    initial = room4_controller_snapshot(session)
    expected = {
        "room": 4,
        "phase": 0,
        "error": 0,
        "lifecycle": 2,
        "talk_active": 0,
        "mode": 1,
        "verb": 3,
        "object": 61,
    }
    observed = {key: initial[key] for key in expected}
    if observed != expected:
        raise RuntimeError(
            f"room-4 Use continuation precondition mismatch: "
            f"{observed!r} != {expected!r}"
        )

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        with ControllerInputLease(session) as controller:
            return room4_synchronous_input_edge(session, mask, predicate)

    cycles = []
    for target_verb in (4, 9, 10):
        cycles.append(send(0x800, lambda _before, after, target=target_verb: (
            after["room"] == 4 and after["error"] == 0
            and after["mode"] == 1 and after["object"] == 61
            and after["verb"] == target
        )))
    selected = room4_controller_snapshot(session)
    submissions_before = selected["submissions"]
    submit = send(0x001, lambda _before, after: (
        after["room"] == 4 and after["error"] == 0
        and after["mode"] == 2 and after["object"] == 61
        and after["verb"] == 10
        and after["submissions"] == ((submissions_before + 1) & 0xFF)
    ))
    return {
        "precondition": initial,
        "verb_cycle_edges": cycles,
        "selected_use": selected,
        "submission": submit,
        "submission_count_before": submissions_before,
        "submission_count_after": room4_controller_snapshot(session)["submissions"],
        "result": "submitted source-authored Use on room4 object61 exactly once",
    }


def replay_room5_rope_to_room6(
    session: Any,
    *,
    pulse: Any = None,
    target: tuple[int, int] = (225, 124),
) -> dict[str, Any]:
    """Select and submit the already-authenticated room-5 rope sentence.

    The current authored branch is room5 object77 / verb9 with bit69 clear;
    its OBCD starts LSCR201, whose body requests room6. The replay starts only
    at the recorded room5 phase-0 entry-complete state and uses normal input.
    """
    initial = room4_controller_snapshot(session)
    actor_room = session.read_u8(0x7F3716)
    bit69 = bool(session.read_u8(0x7E2BA8) & 0x20)
    expected = {
        "room": 5,
        "phase": 0,
        "error": 0,
        "lifecycle": 2,
        "ready": 1,
        "talk_active": 0,
        "mode": 0,
        "verb": 0,
        "object": 0,
        "x": 145,
        "y": 134,
        "actor1_room": 5,
        "bit69": False,
    }
    observed = {
        **{key: initial[key] for key in expected if key in initial},
        "actor1_room": actor_room,
        "bit69": bit69,
    }
    if observed != expected:
        raise RuntimeError(
            f"room-5 rope replay precondition mismatch: {observed!r} != {expected!r}"
        )
    precondition = {**initial, "actor1_room": actor_room, "bit69": bit69}

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        return controller_synchronous_input_edge(session, mask, predicate)

    movement: list[dict[str, Any]] = []
    cursor = initial
    while (cursor["x"], cursor["y"]) != target:
        if len(movement) >= 100:
            raise RuntimeError("room-5 rope target exceeded the bounded cursor route")
        before = cursor
        mask = world_point_direction_mask(before["x"], before["y"], *target)
        if mask is None:
            break
        target_xy = (
            before["x"] + (2 if mask == 0x080 else -2 if mask == 0x040 else 0),
            before["y"] + (2 if mask == 0x020 else -2 if mask == 0x010 else 0),
        )
        step = send(mask, lambda _old, after, xy=target_xy: (
            after["room"] == 5 and after["error"] == 0
            and (after["x"], after["y"]) == xy
        ))
        movement.append(step)
        cursor = step["after"]

    target_state = room4_controller_snapshot(session)
    if (target_state["x"], target_state["y"]) != target:
        raise RuntimeError(
            f"room-5 rope cursor failed to reach the recorded point: {target_state!r}"
        )
    selection = send(0x001, lambda _old, after: (
        after["room"] == 5 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == 77
        and after["hit_object"] == 77 and after["verb"] in (8, 9)
    ))
    selected = selection["after"]
    verb_cycle: dict[str, Any] | None = None
    if selected["verb"] == 8:
        verb_cycle = send(0x800, lambda _old, after: (
            after["room"] == 5 and after["error"] == 0
            and after["mode"] == 1 and after["object"] == 77
            and after["hit_object"] == 77 and after["verb"] == 9
        ))
        selected = verb_cycle["after"]
    elif selected["verb"] != 9:
        raise RuntimeError(f"unexpected initial object77 verb selection: {selected!r}")

    submissions_before = selected["submissions"]
    submission = send(0x001, lambda _old, after: (
        after["room"] == 5 and after["error"] == 0
        and after["mode"] == 2 and after["object"] == 77
        and after["verb"] == 9
        and after["submissions"] == ((submissions_before + 1) & 0xFF)
    ))
    return {
        "precondition": precondition,
        "target": {
            "world": list(target),
            "preselection_hit_object": target_state["hit_object"],
            "selected_hit_object": selection["after"]["hit_object"],
        },
        "movement_edges": movement,
        "selection": selection,
        "selected_verb_cycle": verb_cycle,
        "submission": submission,
        "submission_count_before": submissions_before,
        "submission_count_after": submission["after"]["submissions"],
        "result": "submitted authentic room5 object77 verb9 once",
    }


def replay_room6_books_interaction(
    session: Any,
    *,
    pulse: Any = None,
    target: tuple[int, int] = (4, 81),
) -> dict[str, Any]:
    """Submit room6 object91/verb10 from the known authentic entry state.

    The source-authenticated verb tests bit69 and starts room6 LSCR200 when
    that bit is clear.  This records the known authored route into the
    bookcase interaction; it does not assume that merely submitting it proves
    a later room transition.
    """
    initial = room4_controller_snapshot(session)
    actor_room = session.read_u8(0x7F3716)
    bit69 = bool(session.read_u8(0x7E2BA8) & 0x20)
    expected = {
        "room": 6,
        "phase": 0,
        "error": 0,
        "lifecycle": 2,
        "ready": 1,
        "talk_active": 0,
        "mode": 0,
        "verb": 0,
        "object": 0,
        "x": 226,
        "y": 139,
        "actor1_room": 6,
        "bit69": False,
    }
    observed = {
        **{key: initial[key] for key in expected if key in initial
           and key != "bit69"},
        "actor1_room": actor_room,
        "bit69": bit69,
    }
    if observed != expected:
        raise RuntimeError(
            f"room-6 books replay precondition mismatch: {observed!r} != {expected!r}"
        )
    precondition = {**initial, "actor1_room": actor_room, "bit69": bit69}

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        return controller_synchronous_input_edge(session, mask, predicate)

    movement: list[dict[str, Any]] = []
    cursor = initial
    while (cursor["x"], cursor["y"]) != target:
        if len(movement) >= 160:
            raise RuntimeError("room-6 books target exceeded its bounded cursor route")
        mask = world_point_direction_mask(cursor["x"], cursor["y"], *target)
        if mask is None:
            break
        next_xy = (
            cursor["x"] + (2 if mask == 0x080 else -2 if mask == 0x040 else 0),
            cursor["y"] + (2 if mask == 0x020 else -2 if mask == 0x010 else 0),
        )
        step = send(mask, lambda _old, after, xy=next_xy: (
            after["room"] == 6 and after["error"] == 0
            and (after["x"], after["y"]) == xy
        ))
        movement.append(step)
        cursor = step["after"]

    target_state = room4_controller_snapshot(session)
    if (target_state["x"], target_state["y"]) != target:
        raise RuntimeError(
            f"room-6 books cursor failed to reach the recorded point: {target_state!r}"
        )
    selection = send(0x001, lambda _old, after: (
        after["room"] == 6 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == 91
        and after["hit_object"] == 91 and after["verb"] == 9
    ))
    verb_cycle = send(0x800, lambda _old, after: (
        after["room"] == 6 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == 91
        and after["hit_object"] == 91 and after["verb"] == 10
    ))
    submissions_before = verb_cycle["after"]["submissions"]
    submission = send(0x001, lambda _old, after: (
        after["room"] == 6 and after["error"] == 0
        and after["mode"] == 2 and after["object"] == 91
        and after["verb"] == 10
        and after["submissions"] == ((submissions_before + 1) & 0xFF)
    ))
    return {
        "precondition": precondition,
        "target": {
            "world": list(target),
            "source_rectangle_half_open": [0, 40, 40, 128],
            "preselection_hit_object": target_state["hit_object"],
            "selected_hit_object": selection["after"]["hit_object"],
        },
        "movement_edges": movement,
        "selection": selection,
        "selected_verb_cycle": verb_cycle,
        "submission": submission,
        "submission_count_before": submissions_before,
        "submission_count_after": submission["after"]["submissions"],
        "result": "submitted authentic room6 object91 verb10 once",
    }


def replay_room7_lost_dialogue_interaction(
    session: Any,
    *,
    variable_base: int,
    variable_count: int,
    pulse: Any = None,
    target: tuple[int, int] = (188, 125),
) -> dict[str, Any]:
    """Read the room-7 book's authored verb-11 interaction exactly once.

    The point is inside both the book and the pile-of-books rectangles. The
    authentic room resource orders the book first, so selection must resolve
    to object 133. No retry is permitted if native hit testing disagrees.
    """
    initial = room4_controller_snapshot(session)
    actor_room = session.read_u8(0x7F3716)
    bit69 = bool(session.read_u8(0x7E2BA8) & 0x20)
    raw_variables = session.read_memory(
        "snesMemory", variable_base, variable_count * 2
    )
    if variable_count <= 219:
        raise RuntimeError("ROM variable table does not contain room-7 state V219")
    v214 = int.from_bytes(raw_variables[214 * 2:214 * 2 + 2], "little")
    v215 = int.from_bytes(raw_variables[215 * 2:215 * 2 + 2], "little")
    v219 = int.from_bytes(raw_variables[219 * 2:219 * 2 + 2], "little")
    expected = {
        "room": 7,
        "phase": 0,
        "error": 0,
        "lifecycle": 2,
        "ready": 1,
        "talk_active": 0,
        "mode": 0,
        "verb": 0,
        "object": 0,
        "x": 162,
        "y": 129,
        "actor1_room": 7,
        "bit69": False,
        "V214": 0,
        "V215": 0,
        "V219": 0,
    }
    observed = {
        **{key: initial[key] for key in expected if key in initial},
        "actor1_room": actor_room,
        "bit69": bit69,
        "V214": v214,
        "V215": v215,
        "V219": v219,
    }
    if observed != expected:
        raise RuntimeError(
            f"room-7 book replay precondition mismatch: {observed!r} != {expected!r}"
        )
    precondition = {**initial, "actor1_room": actor_room, "bit69": bit69,
                    "V214": v214, "V215": v215, "V219": v219}

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        return controller_synchronous_input_edge(session, mask, predicate)

    movement: list[dict[str, Any]] = []
    cursor = initial
    while (cursor["x"], cursor["y"]) != target:
        if len(movement) >= 64:
            raise RuntimeError("room-7 book target exceeded its bounded cursor route")
        mask = world_point_direction_mask(cursor["x"], cursor["y"], *target)
        if mask is None:
            break
        next_xy = (
            cursor["x"] + (2 if mask == 0x080 else -2 if mask == 0x040 else 0),
            cursor["y"] + (2 if mask == 0x020 else -2 if mask == 0x010 else 0),
        )
        step = send(mask, lambda _old, after, xy=next_xy: (
            after["room"] == 7 and after["error"] == 0
            and (after["x"], after["y"]) == xy
        ))
        movement.append(step)
        cursor = step["after"]

    target_state = room4_controller_snapshot(session)
    if (target_state["x"], target_state["y"]) != target:
        raise RuntimeError(
            f"room-7 book cursor failed to reach the recorded point: {target_state!r}"
        )
    selection = send(0x001, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == 133
        and after["hit_object"] == 133 and after["verb"] == 9
    ))
    verb_cycle = send(0x800, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == 133
        and after["hit_object"] == 133 and after["verb"] == 11
    ))
    submissions_before = verb_cycle["after"]["submissions"]
    submission = send(0x001, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 2 and after["object"] == 133
        and after["verb"] == 11
        and after["submissions"] == ((submissions_before + 1) & 0xFF)
    ))
    return {
        "precondition": precondition,
        "target": {
            "world": list(target),
            "object_rectangle_half_open": [176, 120, 200, 128],
            "overlapping_object": 130,
            "source_order_winner": 133,
            "preselection_hit_object": target_state["hit_object"],
            "selected_hit_object": selection["after"]["hit_object"],
        },
        "movement_edges": movement,
        "selection": selection,
        "selected_verb_cycle": verb_cycle,
        "submission": submission,
        "submission_count_before": submissions_before,
        "submission_count_after": submission["after"]["submissions"],
        "result": "submitted authentic room7 object133 verb11 once",
    }


def replay_room7_cat_figure_use(
    session: Any,
    *,
    object_id: int,
    variable_base: int,
    variable_count: int,
    pulse: Any = None,
) -> dict[str, Any]:
    """Use one source-authentic room-7 cat figure, exactly once.

    This follows the authored two-distinct-figure gate: object 118 sets V217
    and increments V214 from zero; object 119 then sets V218 and
    dispatches LSCR207 followed by LSCR201.  This recipe keeps that observed
    authored order fixed and never probes alternative objects.
    """
    if object_id not in (118, 119):
        raise ValueError("room-7 deterministic cat replay accepts only objects 118/119")
    if variable_count <= 218:
        raise RuntimeError("ROM variable table does not contain room-7 V214-V218")

    initial = room4_controller_snapshot(session)
    variables = session.read_memory("snesMemory", variable_base, variable_count * 2)
    v214 = int.from_bytes(variables[428:430], "little")
    variables_215_218 = {
        index: int.from_bytes(variables[index * 2:index * 2 + 2], "little")
        for index in (215, 216, 217, 218)
    }
    actor_room = session.read_u8(0x7F3716)
    item937_owner = session.read_u8(0x7E8000 + 937)
    states = {item: session.read_u8(0x7E6000 + item) for item in (118, 119, 133)}
    owners = {item: session.read_u8(0x7E8000 + item) for item in (118, 119, 133)}

    if object_id == 118:
        expected_controller = (1, 133, 9, 188, 125)
        expected_v214 = 0
        expected_vars = (0, 0, 0, 0)
        prior = "room7 book interaction has completed; first distinct figurine is available"
    else:
        expected_controller = (1, 118, 9, 112, 123)
        expected_v214 = 1
        expected_vars = (0, 0, 1, 0)
        prior = "object118 verb10 completed and wrote V217; second distinct figurine is available"
    observed_controller = (
        initial["mode"], initial["object"], initial["verb"],
        initial["x"], initial["y"],
    )
    observed_vars = tuple(
        variables_215_218[index] for index in (215, 216, 217, 218)
    )
    expected = {
        "room": 7, "phase": 0, "error": 0, "lifecycle": 2,
        "talk_active": 0, "actor1_room": 7,
        "controller": expected_controller, "V214": expected_v214,
        "variables215_218": expected_vars,
        "object_states": {118: 0, 119: 0, 133: 0},
        "room_object_owners": {118: 15, 119: 15, 133: 15},
        "book_inventory_object937_owner": 1,
    }
    observed = {
        "room": initial["room"], "phase": initial["phase"],
        "error": initial["error"], "lifecycle": initial["lifecycle"],
        "talk_active": initial["talk_active"], "actor1_room": actor_room,
        "controller": observed_controller, "V214": v214,
        "variables215_218": observed_vars,
        "object_states": states,
        "room_object_owners": owners,
        "book_inventory_object937_owner": item937_owner,
    }
    if observed != expected:
        raise RuntimeError(
            f"room-7 object{object_id} replay precondition mismatch ({prior}): "
            f"{observed!r} != {expected!r}"
        )

    target = (112, 123) if object_id == 118 else (128, 123)

    def send(mask: int, predicate: Any) -> dict[str, Any]:
        if pulse is not None:
            return pulse(session, mask, predicate)
        return controller_synchronous_input_edge(session, mask, predicate)

    movement: list[dict[str, Any]] = []
    cursor = initial
    while (cursor["x"], cursor["y"]) != target:
        if len(movement) >= 64:
            raise RuntimeError(
                f"room-7 object{object_id} target exceeded its bounded cursor route"
            )
        mask = world_point_direction_mask(cursor["x"], cursor["y"], *target)
        if mask is None:
            break
        next_xy = (
            cursor["x"] + (2 if mask == 0x080 else -2 if mask == 0x040 else 0),
            cursor["y"] + (2 if mask == 0x020 else -2 if mask == 0x010 else 0),
        )
        movement.append(send(mask, lambda _old, after, xy=next_xy: (
            after["room"] == 7 and after["error"] == 0
            and (after["x"], after["y"]) == xy and after["mode"] == 0
        )))
        cursor = movement[-1]["after"]

    target_state = room4_controller_snapshot(session)
    if (target_state["x"], target_state["y"]) != target or target_state["mode"] != 0:
        raise RuntimeError(
            f"room-7 object{object_id} cursor did not reach its unselected target: "
            f"{target_state!r}"
        )
    selection = send(0x001, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == object_id
        and after["hit_object"] == object_id and after["verb"] == 9
    ))
    verb_cycle = send(0x800, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 1 and after["object"] == object_id
        and after["hit_object"] == object_id and after["verb"] == 10
    ))
    submissions_before = verb_cycle["after"]["submissions"]
    submission = send(0x001, lambda _old, after: (
        after["room"] == 7 and after["error"] == 0
        and after["mode"] == 2 and after["object"] == object_id
        and after["verb"] == 10
        and after["submissions"] == ((submissions_before + 1) & 0xFF)
    ))
    return {
        "precondition": observed,
        "precondition_explanation": prior,
        "target": {
            "object": object_id,
            "world": list(target),
            "rectangle_half_open": [104, 112, 120, 136] if object_id == 118
                                   else [120, 112, 136, 136],
            "expected_walk_point": [102, 133] if object_id == 118 else [118, 129],
        },
        "movement_edges": movement,
        "selection": selection,
        "selected_verb_cycle": verb_cycle,
        "submission": submission,
        "submission_count_before": submissions_before,
        "submission_count_after": submission["after"]["submissions"],
        "expected_authored_effect": (
            "set V217; increment V214 to 1"
            if object_id == 118 else
            "set V218; start LSCR207([119]); chain LSCR201"
        ),
        "result": f"submitted authentic room7 object{object_id} verb10 once",
    }


def replay_room4_open_trapdoor_from_origin(session: Any) -> dict[str, Any]:
    """Reach object 61's authored hitbox and submit Open from cursor origin.

    This is a deterministic cold-room input path, not a state edit. The room
    controller starts at (0, 0) in the current authentic cold profile; the
    route uses one exact edge per two-pixel controller step to the interior
    point (90, 132) of object 61's half-open source rectangle [64,104)x[128,136).
    """
    initial = room4_controller_snapshot(session)
    expected = (4, 0, 0, 2, 1, 0, 0, 0, 0, 0)
    observed = (
        initial["room"], initial["phase"], initial["error"],
        initial["lifecycle"], initial["ready"], initial["talk_active"],
        initial["mode"], initial["x"], initial["y"],
        initial["c19_stack_pointer"],
    )
    if observed != expected:
        raise RuntimeError(
            f"cold room-4 replay precondition mismatch: {observed!r} != {expected!r}"
        )

    target_x, target_y = 90, 132
    steps: list[dict[str, Any]] = []
    with ControllerInputLease(session) as controller:
        x, y = initial["x"], initial["y"]
        while x != target_x:
            direction = 0x080 if target_x > x else 0x040
            x += 2 if direction == 0x080 else -2
            steps.append(_room4_pulse_until(
                session, controller, direction,
                lambda _before, after, tx=x, ty=y:
                    after["x"] == tx and after["y"] == ty,
            ))
        while y != target_y:
            direction = 0x020 if target_y > y else 0x010
            y += 2 if direction == 0x020 else -2
            steps.append(_room4_pulse_until(
                session, controller, direction,
                lambda _before, after, tx=x, ty=y:
                    after["x"] == tx and after["y"] == ty,
            ))

        at_target = room4_controller_snapshot(session)
        if at_target["hit_object"] != 61:
            raise RuntimeError(
                "authentic object-61 hitbox was not selected at derived interior "
                f"point ({target_x},{target_y}): {at_target!r}"
            )
        steps.append(_room4_pulse_until(
            session, controller, 0x001,
            lambda _before, after: (
                after["mode"] == 1 and after["verb"] == 3
                and after["object"] == 61 and after["hit_object"] == 61
            ),
        ))
        before_submit = room4_controller_snapshot(session)
        steps.append(_room4_pulse_until(
            session, controller, 0x001,
            lambda before, after: (
                after["submissions"] == ((before["submissions"] + 1) & 0xFF)
            ),
        ))

    final = room4_controller_snapshot(session)
    if final["error"] != 0 or final["room"] != 4:
        raise RuntimeError(f"room-4 replay left its accepted scene: {final!r}")
    return {
        "precondition": initial,
        "target": {"world": [target_x, target_y], "hit_object": 61,
                   "source_rect_half_open": [64, 128, 104, 136]},
        "input_schedule": {
            "press_frames": 4,
            "release_neutral_frames": 1,
            "controller_level_changes_advance_frames": False,
            "equivalent_attempts_per_step": 1,
        },
        "movement_pulses": len(steps) - 2,
        "steps": steps,
        "before_submit": before_submit,
        "final": final,
        "result": "Open selected and submitted once on authentic object 61 at world (90,132)",
    }


def room4_message_ready(talk_state: bytes, last_generation: int | None) -> bool:
    """Return true only for a new explicit SCUMM input-wait segment.

    Ordinary message segments (HAVE_MSG == 1) finish on their authored timer;
    an A edge must not be synthesized merely because that timer reached zero.
    FF 03 is represented by the runtime's $FF wait state.
    """
    if len(talk_state) < 8:
        return False
    generation = int.from_bytes(talk_state[6:8], "little")
    delay = int.from_bytes(talk_state[4:6], "little")
    return bool(
        talk_state[0]
        and talk_state[1] == 0xFF
        and delay == 0
        and generation != last_generation
    )


def world_point_direction_mask(
    world_x: int,
    world_y: int,
    target_x: int,
    target_y: int,
    *,
    tolerance: int = 0,
) -> int | None:
    """Choose one cursor axis without oscillating on the two-pixel lattice."""
    x_delta = target_x - world_x
    y_delta = target_y - world_y
    if abs(x_delta) <= tolerance and abs(y_delta) <= tolerance:
        return None
    if abs(x_delta) > tolerance:
        return 0x080 if x_delta > 0 else 0x040
    return 0x020 if y_delta > 0 else 0x010


class ControllerInputLease:
    """Own held controller state and release it before the session closes."""

    def __init__(self, session: Any, *, port: int = 0) -> None:
        self.session = session
        self.port = port
        self.buttons = 0

    def __enter__(self) -> "ControllerInputLease":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()

    def hold(self, buttons: int) -> None:
        if buttons <= 0:
            raise ValueError("held controller mask must be nonzero")
        self.session.tool("set_input", {
            "port": self.port,
            "buttons": buttons,
            "hold": True,
            "frames": 0,
        })
        self.buttons = buttons

    def release(self) -> None:
        if not self.buttons:
            return
        self.session.tool("set_input", {
            "port": self.port,
            "buttons": 0,
            "hold": True,
            "frames": 0,
        })
        self.buttons = 0


def advance_bounded(
    session: Any,
    max_frames: int,
    *,
    error_hook: int | None = None,
) -> dict[str, Any]:
    """Advance a bounded window and verify actual emulator frame progress."""
    if max_frames <= 0:
        raise ValueError("max_frames must be positive")
    before = int(session.get_state()["frameCount"])
    if error_hook is None:
        result = session.run_frames(max_frames)
    else:
        result = session.run_until(max_frames=max_frames, hook_handle=error_hook)
    after = int(session.get_state()["frameCount"])
    advanced = after - before
    if result.get("timedOut"):
        raise RuntimeError(f"emulator frame advance timed out: {result}")
    reported = result.get("framesAdvanced")
    if reported is not None and int(reported) != advanced:
        raise RuntimeError(
            f"emulator frame count disagrees with tool result: {advanced} != {reported}"
        )
    if advanced < 0 or advanced > max_frames:
        raise RuntimeError(f"emulator advanced outside requested window: {result}")
    hook_fired = result.get("reason") == "hookFired"
    if advanced == 0 and not hook_fired:
        raise RuntimeError(f"bounded frame advance made no progress: {result}")
    return {
        "start_frame": before,
        "end_frame": after,
        "frames_advanced": advanced,
        "hook_fired": hook_fired,
        "tool_result": result,
    }


def next_input_safe_window(
    host_frame: int,
    frame_limit: int,
    *,
    release_frame: int | None,
    sample_interval: int,
    max_batch: int = 10,
) -> int:
    """Bound error-watch polling so it cannot cross an owned-input release."""
    if host_frame < 0 or frame_limit < 0 or sample_interval <= 0 or max_batch <= 0:
        raise ValueError("invalid frame-window bounds")
    remaining = frame_limit - host_frame
    if remaining <= 0:
        return 0
    window = min(max_batch, sample_interval, remaining)
    if release_frame is not None:
        until_release = release_frame - host_frame
        if until_release <= 0:
            return 0
        window = min(window, until_release)
    return window


def activation_observation(
    params: Mapping[str, Any],
    *,
    snapshot: Mapping[str, Any],
    synchronized: bool,
) -> dict[str, Any]:
    """Keep event timestamps separate from later host-side state snapshots."""
    event: dict[str, Any] = {"hook_event": dict(params)}
    if synchronized:
        event["event_time_snapshot"] = dict(snapshot)
        event["snapshot_timing"] = "synchronized_pause"
    else:
        event["drain_time_snapshot"] = dict(snapshot)
        event["snapshot_timing"] = "after_notification_drain"
    return event
