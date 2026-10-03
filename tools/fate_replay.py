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
    return {
        "room": session.read_u8(0x7FF2BF),
        "phase": session.read_u8(0x7FF2C2),
        "error": session.read_u8(0x7E2303),
        "lifecycle": session.read_u8(0x7E2221),
        "ready": session.read_u8(0x7E5E8A),
        "talk_active": session.read_u8(0x7E7A20),
        "mode": session.read_u8(0x7E5FE0),
        "x": _read_u16(session, 0x7E5FE1),
        "y": _read_u16(session, 0x7E5FE3),
        "verb": session.read_u8(0x7E5FE5),
        "object": _read_u16(session, 0x7E5FE6),
        "hit_object": _read_u16(session, 0x7E5F94),
        "submissions": session.read_u8(0x7E5FE9),
    }


def _room4_pulse_until(
    session: Any,
    controller: "ControllerInputLease",
    mask: int,
    predicate: Any,
    *,
    poll_frames: int = 45,
) -> dict[str, Any]:
    """Send one exact 4-frame press/1-frame neutral interval and observe it.

    Nexen's ``set_input(frames=...)`` is wall-clock driven at max speed, so
    this replay only changes controller level without advancing and uses
    frame-counted runs for every press/release interval. A failed edge is a
    diagnostic boundary; repeating the same input could move the cursor past
    its target and conceal the timing problem.
    """
    before = room4_controller_snapshot(session)
    start_frame = int(session.get_state()["frameCount"])
    controller.hold(mask)
    try:
        press = advance_bounded(session, 4)
    finally:
        # Release even when frame advancement or observation raises.
        controller.release()
    if press["start_frame"] != start_frame or press["frames_advanced"] != 4:
        raise RuntimeError(f"room-4 press interval was not exactly four frames: {press}")

    neutral = advance_bounded(session, 1)
    if neutral["start_frame"] != press["end_frame"] or neutral["frames_advanced"] != 1:
        raise RuntimeError(f"room-4 release interval was not exactly one frame: {neutral}")

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
                "observed_frame": int(session.get_state()["frameCount"]),
                "before": before,
                "after": after,
            }
        advance_bounded(session, 1)
    raise RuntimeError(
        f"room-4 input ${mask:03X} was not consumed after one exact-frame pulse"
    )


def replay_room4_open_trapdoor_prefix(session: Any) -> dict[str, Any]:
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
    with ControllerInputLease(session) as controller:
        for _ in range(14):
            x -= 2
            steps.append(_room4_pulse_until(
                session, controller, 0x040,
                lambda _before, after, tx=x: after["x"] == tx,
            ))
        for _ in range(3):
            y -= 2
            steps.append(_room4_pulse_until(
                session, controller, 0x010,
                lambda _before, after, ty=y: after["y"] == ty,
            ))
        steps.append(_room4_pulse_until(
            session, controller, 0x001,
            lambda _before, after: (
                after["mode"] == 1 and after["verb"] == 3
                and after["object"] == 61 and after["hit_object"] == 61
            ),
        ))
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
        "input_schedule": {
            "press_frames": 4,
            "release_neutral_frames": 1,
            "controller_level_changes_advance_frames": False,
            "equivalent_attempts_per_step": 1,
        },
        "steps": steps,
        "final": final,
        "result": "controller submitted Open on object 61 at world (89,132)",
    }


def room4_message_ready(talk_state: bytes, last_generation: int | None) -> bool:
    """Return true when a new room-4 message has finished its display delay."""
    if len(talk_state) < 8:
        return False
    generation = int.from_bytes(talk_state[6:8], "little")
    delay = int.from_bytes(talk_state[4:6], "little")
    return bool(
        talk_state[0]
        and talk_state[1]
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
