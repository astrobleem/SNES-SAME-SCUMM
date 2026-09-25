"""Deterministic source-neutral playback scheduling and save states."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import itertools
import json
import re
from typing import Protocol

from .model import ControllerEvent, MarkerEvent, NoteOffEvent, NoteOnEvent, SequenceIR


class PlaybackBackend(Protocol):
    """Minimal semantic sink driven by :class:`PlaybackSession`."""

    def advance(self, frames: int) -> None: ...
    def note_on(self, voice: int, event: NoteOnEvent) -> None: ...
    def note_off(self, voice: int, event: NoteOffEvent) -> None: ...
    def controller(self, event: ControllerEvent) -> None: ...
    def stop(self) -> None: ...


class VoiceBudgetError(RuntimeError):
    def __init__(self, tick: int, limit: int, active_note_ids: tuple[int, ...], requested_note_id: int) -> None:
        self.tick = int(tick)
        self.limit = int(limit)
        self.active_note_ids = tuple(active_note_ids)
        self.requested_note_id = int(requested_note_id)
        super().__init__(
            f"music voice budget {limit} exhausted at tick {tick}; "
            f"active notes {list(active_note_ids)}, requested {requested_note_id}"
        )


class CheckpointError(ValueError):
    """A checkpoint was corrupt or incompatible with its playback session."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"music checkpoint {code}: {detail}")


@dataclass(frozen=True, slots=True)
class PlaybackAction:
    sample: int
    tick: int
    action: str
    part_id: int | None = None
    note_id: int | None = None
    voice: int | None = None
    controller: int | None = None
    value_q16: int | None = None
    reason: str | None = None
    voice_generation: int | None = None


@dataclass(frozen=True, slots=True)
class ActiveVoiceState:
    voice: int
    voice_generation: int
    allocation_order: int
    part_id: int
    note_id: int
    pitch_q8_8: int
    velocity: int
    release_velocity: int
    deferred: bool
    deferred_order: int | None


@dataclass(frozen=True, slots=True)
class PlaybackCheckpoint:
    """Complete logical sequencer state; ``event_index`` is next unconsumed."""

    schema_version: int
    sequence_ir_sha256: str
    realization_sha256: str
    engine_id: str
    profile_id: str
    timing_id: str
    sample_rate: int
    source_time_scale: int
    voice_limit: int
    voice_policy: str
    loop_repeats: int
    tick: int
    sample: int
    rational_remainder: int
    event_index: int
    loop_iteration: int
    loop_repeats_remaining: int
    controllers: tuple[tuple[int, int, int], ...]
    sustain_parts: tuple[int, ...]
    active_voices: tuple[ActiveVoiceState, ...]
    retired_note_ids: tuple[int, ...]
    next_voice_generation: int
    next_allocation_order: int
    next_deferred_order: int
    completed: bool
    stopped: bool
    paused: bool
    warm_owner_id: int = 0
    action_count: int = 0


@dataclass(slots=True)
class _ActiveVoice:
    voice: int
    voice_generation: int
    allocation_order: int
    note: NoteOnEvent
    release_velocity: int = 64
    deferred: bool = False
    deferred_order: int | None = None


_SESSION_IDS = itertools.count(1)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def sequence_ir_sha256(sequence: SequenceIR) -> str:
    """Return the canonical source-neutral identity used by cold states."""
    from .audit import canonical_sequence_ir
    raw = json.dumps(
        canonical_sequence_ir(sequence), sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class PlaybackSession:
    """Schedule one ``SequenceIR`` onto bounded deterministic voice handles.

    A cursor always points at the next unconsumed event. Thus a checkpoint in
    the middle of a same-timestamp group records precisely which members of the
    group have already been issued.
    """

    CHECKPOINT_SCHEMA_VERSION = 1
    COLD_ACTIVE_VOICE_POLICY = "logical-ownership-no-backend-continuity"
    TIMING_ID = "integer-rational-remainder-v1"
    SUSTAIN_CONTROLLER = 64
    SUSTAIN_ON_Q16 = 1 << 15
    VOICE_POLICIES = frozenset(("error", "steal_oldest"))

    def __init__(
        self, sequence: SequenceIR, backend: PlaybackBackend, *, sample_rate: int,
        voice_limit: int = 8, voice_policy: str = "error", loop_repeats: int = 0,
        realization_sha256: str = "", engine_id: str = "", profile_id: str = "",
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("music playback sample rate must be positive")
        if voice_limit <= 0:
            raise ValueError("music playback voice limit must be positive")
        if voice_policy not in self.VOICE_POLICIES:
            raise ValueError("unknown music voice policy")
        if loop_repeats < 0:
            raise ValueError("music loop repeat count cannot be negative")
        self.sequence = sequence
        self.backend = backend
        self.sample_rate = int(sample_rate)
        self.voice_limit = int(voice_limit)
        self.voice_policy = voice_policy
        self.loop_repeats = int(loop_repeats)
        self.sequence_ir_sha256 = sequence_ir_sha256(sequence)
        self.realization_sha256 = realization_sha256
        self.engine_id = engine_id
        self.profile_id = profile_id
        self.tick = 0
        self.sample = 0
        self.rational_remainder = 0
        self._event_index = 0
        self._active: dict[int, _ActiveVoice] = {}
        self._retired_note_ids: set[int] = set()
        self._sustain = {part.part_id: False for part in sequence.parts}
        self._controllers: dict[tuple[int, int], int] = {}
        self._actions: list[PlaybackAction] = []
        self._next_voice_generation = 1
        self._next_allocation_order = 1
        self._next_deferred_order = 1
        self.loop_iteration = 0
        self.loop_repeats_remaining = self.loop_repeats
        self.completed = False
        self.stopped = False
        self.paused = False
        self._warm_owner_id = next(_SESSION_IDS)

    @property
    def actions(self) -> tuple[PlaybackAction, ...]:
        return tuple(self._actions)

    @property
    def event_index(self) -> int:
        """Index of the next event that has not yet been consumed."""
        return self._event_index

    @property
    def active_note_ids(self) -> tuple[int, ...]:
        return tuple(sorted(self._active))

    @property
    def active_voice_handles(self) -> tuple[int, ...]:
        return tuple(sorted(item.voice for item in self._active.values()))

    @property
    def active_voice_states(self) -> tuple[ActiveVoiceState, ...]:
        return tuple(sorted((self._active_state(item) for item in self._active.values()), key=lambda item: item.voice))

    @property
    def controller_state(self) -> tuple[tuple[int, int, int], ...]:
        return tuple((part, controller, value) for (part, controller), value in sorted(self._controllers.items()))

    @property
    def sustain_parts(self) -> tuple[int, ...]:
        return tuple(sorted(part for part, enabled in self._sustain.items() if enabled))

    def sample_at_tick(self, tick: int) -> int:
        if not 0 <= int(tick) <= self.sequence.end_tick:
            raise ValueError("music playback tick lies outside the sequence")
        return int(tick) * self.sample_rate // self.sequence.source_time_scale

    def _advance_clock_delta(self, ticks: int) -> None:
        if ticks < 0:
            raise ValueError("music playback clock cannot move backwards")
        numerator = ticks * self.sample_rate + self.rational_remainder
        frames, self.rational_remainder = divmod(numerator, self.sequence.source_time_scale)
        self.backend.advance(frames)
        self.sample += frames
        self.tick += ticks

    def _advance_clock(self, tick: int) -> None:
        self._advance_clock_delta(int(tick) - self.tick)

    def _record(self, action: str, *, part_id: int | None = None, note_id: int | None = None,
                voice: int | None = None, controller: int | None = None,
                value_q16: int | None = None, reason: str | None = None,
                voice_generation: int | None = None) -> None:
        self._actions.append(PlaybackAction(
            self.sample, self.tick, action, part_id, note_id, voice,
            controller, value_q16, reason, voice_generation,
        ))

    def _active_state(self, item: _ActiveVoice) -> ActiveVoiceState:
        return ActiveVoiceState(
            item.voice, item.voice_generation, item.allocation_order,
            item.note.part_id, item.note.note_id, item.note.pitch_q8_8,
            item.note.velocity, item.release_velocity, item.deferred,
            item.deferred_order,
        )

    def _free_voice(self) -> int:
        used = {item.voice for item in self._active.values()}
        return next(voice for voice in range(self.voice_limit) if voice not in used)

    def _release(self, note_id: int, reason: str) -> None:
        active = self._active.pop(note_id)
        event = NoteOffEvent(active.note.part_id, active.note.note_id, active.release_velocity)
        self.backend.note_off(active.voice, event)
        self._record(
            "note_off", part_id=event.part_id, note_id=event.note_id,
            voice=active.voice, reason=reason, voice_generation=active.voice_generation,
        )

    def _steal_oldest(self) -> None:
        victim = min(self._active.values(), key=lambda item: (item.allocation_order, item.voice, item.note.note_id))
        note_id = victim.note.note_id
        self._release(note_id, "steal")
        self._retired_note_ids.add(note_id)

    def _release_part_sustain(self, part_id: int) -> None:
        deferred = sorted(
            (item for item in self._active.values() if item.note.part_id == part_id and item.deferred),
            key=lambda item: (item.deferred_order if item.deferred_order is not None else -1, item.voice_generation),
        )
        for item in deferred:
            self._release(item.note.note_id, "sustain")

    def _dispatch(self, payload: object) -> None:
        if isinstance(payload, NoteOnEvent):
            if len(self._active) >= self.voice_limit:
                if self.voice_policy == "error":
                    raise VoiceBudgetError(self.tick, self.voice_limit, self.active_note_ids, payload.note_id)
                self._steal_oldest()
            voice = self._free_voice()
            active = _ActiveVoice(voice, self._next_voice_generation, self._next_allocation_order, payload)
            self._next_voice_generation += 1
            self._next_allocation_order += 1
            self._active[payload.note_id] = active
            self.backend.note_on(voice, payload)
            self._record("note_on", part_id=payload.part_id, note_id=payload.note_id,
                         voice=voice, voice_generation=active.voice_generation)
        elif isinstance(payload, NoteOffEvent):
            if payload.note_id in self._retired_note_ids:
                self._retired_note_ids.remove(payload.note_id)
                self._record("retired_note_off", part_id=payload.part_id,
                             note_id=payload.note_id, reason="stolen")
                return
            active = self._active[payload.note_id]
            active.release_velocity = payload.release_velocity
            if self._sustain[payload.part_id]:
                active.deferred = True
                active.deferred_order = self._next_deferred_order
                self._next_deferred_order += 1
                self._record("defer", part_id=payload.part_id, note_id=payload.note_id,
                             voice=active.voice, reason="sustain",
                             voice_generation=active.voice_generation)
            else:
                self._release(payload.note_id, "event")
        elif isinstance(payload, ControllerEvent):
            self.backend.controller(payload)
            self._controllers[(payload.part_id, payload.controller)] = payload.value_q16
            self._record("controller", part_id=payload.part_id,
                         controller=payload.controller, value_q16=payload.value_q16)
            if payload.controller == self.SUSTAIN_CONTROLLER:
                was_on = self._sustain[payload.part_id]
                is_on = payload.value_q16 >= self.SUSTAIN_ON_Q16
                self._sustain[payload.part_id] = is_on
                if was_on and not is_on:
                    self._release_part_sustain(payload.part_id)
        elif isinstance(payload, MarkerEvent):
            self._record("marker", reason=payload.marker)

    def _require_running(self) -> None:
        if self.completed or self.stopped:
            raise RuntimeError("music playback session is no longer active")
        if self.paused:
            raise RuntimeError("music playback session is paused")

    def advance_one_event(self) -> None:
        """Consume exactly one event, permitting mid-group checkpoints."""
        self._require_running()
        if self._event_index >= len(self.sequence.events):
            raise RuntimeError("music playback has no unconsumed event")
        scheduled = self.sequence.events[self._event_index]
        self._advance_clock(scheduled.tick)
        self._dispatch(scheduled.payload)
        self._event_index += 1

    def advance_to_tick(self, target_tick: int) -> None:
        self._require_running()
        if self.loop_repeats:
            raise RuntimeError("looping playback advances by elapsed ticks")
        target_tick = int(target_tick)
        if target_tick < self.tick:
            raise ValueError("music playback cannot move backwards")
        if target_tick > self.sequence.end_tick:
            raise ValueError("music playback target exceeds sequence end")
        while self._event_index < len(self.sequence.events):
            scheduled = self.sequence.events[self._event_index]
            if scheduled.tick > target_tick:
                break
            self._advance_clock(scheduled.tick)
            self._dispatch(scheduled.payload)
            self._event_index += 1
        self._advance_clock(target_tick)

    def _consume_current_tick(self) -> None:
        while (self._event_index < len(self.sequence.events)
               and self.sequence.events[self._event_index].tick == self.tick):
            scheduled = self.sequence.events[self._event_index]
            self._dispatch(scheduled.payload)
            self._event_index += 1

    def advance_ticks(self, elapsed_ticks: int) -> None:
        """Advance elapsed sequencer ticks, applying a finite IR loop."""
        self._require_running()
        elapsed_ticks = int(elapsed_ticks)
        if elapsed_ticks < 0:
            raise ValueError("music playback elapsed ticks cannot be negative")
        self._consume_current_tick()
        for _ in range(elapsed_ticks):
            self._advance_clock_delta(1)
            if (self.sequence.loop is not None and self.loop_repeats_remaining
                    and self.tick == self.sequence.loop[1]):
                start, _ = self.sequence.loop
                self.tick = start
                self._event_index = next(
                    (index for index, event in enumerate(self.sequence.events) if event.tick >= start),
                    len(self.sequence.events),
                )
                self.loop_iteration += 1
                self.loop_repeats_remaining -= 1
            self._consume_current_tick()

    def pause(self) -> None:
        if not self.completed and not self.stopped:
            self.paused = True

    def resume(self) -> None:
        if not self.completed and not self.stopped:
            self.paused = False

    def checkpoint(self) -> PlaybackCheckpoint:
        return PlaybackCheckpoint(
            self.CHECKPOINT_SCHEMA_VERSION, self.sequence_ir_sha256,
            self.realization_sha256, self.engine_id, self.profile_id,
            self.TIMING_ID, self.sample_rate, self.sequence.source_time_scale, self.voice_limit,
            self.voice_policy, self.loop_repeats, self.tick, self.sample,
            self.rational_remainder, self._event_index, self.loop_iteration,
            self.loop_repeats_remaining, self.controller_state,
            self.sustain_parts, self.active_voice_states,
            tuple(sorted(self._retired_note_ids)), self._next_voice_generation,
            self._next_allocation_order, self._next_deferred_order,
            self.completed, self.stopped, self.paused, self._warm_owner_id,
            len(self._actions),
        )

    def _validate_checkpoint(self, state: PlaybackCheckpoint, *, warm: bool) -> None:
        expected = (
            (state.schema_version, self.CHECKPOINT_SCHEMA_VERSION, "schema version"),
            (state.sequence_ir_sha256, self.sequence_ir_sha256, "SequenceIR hash"),
            (state.realization_sha256, self.realization_sha256, "realization hash"),
            (state.engine_id, self.engine_id, "engine identity"),
            (state.profile_id, self.profile_id, "profile identity"),
            (state.timing_id, self.TIMING_ID, "timing identity"),
            (state.sample_rate, self.sample_rate, "sample rate"),
            (state.source_time_scale, self.sequence.source_time_scale, "time scale"),
            (state.voice_limit, self.voice_limit, "voice limit"),
            (state.voice_policy, self.voice_policy, "voice policy"),
            (state.loop_repeats, self.loop_repeats, "loop configuration"),
        )
        for actual, wanted, label in expected:
            if actual != wanted:
                raise CheckpointError("mismatch", label)
        if warm and state.warm_owner_id != self._warm_owner_id:
            raise CheckpointError("warm_owner", "checkpoint does not own this live backend")
        integer_values = (
            state.schema_version, state.sample_rate, state.source_time_scale,
            state.voice_limit, state.loop_repeats, state.tick, state.sample,
            state.rational_remainder, state.event_index, state.loop_iteration,
            state.loop_repeats_remaining, state.next_voice_generation,
            state.next_allocation_order, state.next_deferred_order,
            state.warm_owner_id, state.action_count,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in integer_values):
            raise CheckpointError("corrupt_type", "integer state field has a non-integer value")
        if not all(isinstance(value, bool) for value in (state.completed, state.stopped, state.paused)):
            raise CheckpointError("corrupt_type", "terminal state field is not boolean")
        if not (0 <= state.event_index <= len(self.sequence.events)):
            raise CheckpointError("corrupt_cursor", "event cursor is outside the IR")
        if not (0 <= state.tick <= self.sequence.end_tick):
            raise CheckpointError("corrupt_clock", "tick is outside the IR")
        if state.sample < 0 or state.loop_iteration < 0:
            raise CheckpointError("corrupt_clock", "sample or loop iteration is negative")
        if not (0 <= state.rational_remainder < self.sequence.source_time_scale):
            raise CheckpointError("corrupt_clock", "rational remainder is out of range")
        loop_span = 0 if self.sequence.loop is None else self.sequence.loop[1] - self.sequence.loop[0]
        elapsed_ticks = state.tick + state.loop_iteration * loop_span
        expected_sample, expected_remainder = divmod(
            elapsed_ticks * self.sample_rate, self.sequence.source_time_scale,
        )
        if (state.sample, state.rational_remainder) != (expected_sample, expected_remainder):
            raise CheckpointError("corrupt_clock", "sample and rational remainder disagree with tick history")
        first_at_tick = next((index for index, event in enumerate(self.sequence.events)
                              if event.tick >= state.tick), len(self.sequence.events))
        first_after_tick = next((index for index, event in enumerate(self.sequence.events)
                                 if event.tick > state.tick), len(self.sequence.events))
        if not first_at_tick <= state.event_index <= first_after_tick:
            raise CheckpointError("corrupt_cursor", "cursor is not a valid split at the saved tick")
        voices = [item.voice for item in state.active_voices]
        notes = [item.note_id for item in state.active_voices]
        generations = [item.voice_generation for item in state.active_voices]
        if (len(set(voices)) != len(voices) or any(not 0 <= voice < self.voice_limit for voice in voices)
                or len(set(notes)) != len(notes) or len(set(generations)) != len(generations)):
            raise CheckpointError("corrupt_ownership", "active voice ownership is not unique")
        part_ids = {part.part_id for part in self.sequence.parts}
        if any(item.part_id not in part_ids for item in state.active_voices):
            raise CheckpointError("corrupt_ownership", "active voice references an unknown part")
        note_on_by_id = {
            event.payload.note_id: event.payload for event in self.sequence.events
            if isinstance(event.payload, NoteOnEvent)
        }
        if any(note_on_by_id.get(item.note_id) != NoteOnEvent(
                item.part_id, item.note_id, item.pitch_q8_8, item.velocity,
        ) for item in state.active_voices):
            raise CheckpointError("corrupt_ownership", "active note identity disagrees with the IR")
        if set(notes) & set(state.retired_note_ids):
            raise CheckpointError("corrupt_ownership", "note is both active and retired")
        if len(set(state.retired_note_ids)) != len(state.retired_note_ids) or any(
                note not in note_on_by_id for note in state.retired_note_ids):
            raise CheckpointError("corrupt_ownership", "retired note identities are invalid")
        deferred_orders = [item.deferred_order for item in state.active_voices if item.deferred]
        if any(order is None for order in deferred_orders) or len(set(deferred_orders)) != len(deferred_orders):
            raise CheckpointError("corrupt_deferred", "deferred-release order is invalid")
        if any((not item.deferred and item.deferred_order is not None) for item in state.active_voices):
            raise CheckpointError("corrupt_deferred", "non-deferred voice has release order")
        if any(item.deferred and item.part_id not in state.sustain_parts for item in state.active_voices):
            raise CheckpointError("corrupt_deferred", "deferred voice belongs to a part without sustain")
        if any(item.voice_generation <= 0 or item.allocation_order <= 0 for item in state.active_voices):
            raise CheckpointError("corrupt_ownership", "voice identity counters must be positive")
        if generations and state.next_voice_generation <= max(generations):
            raise CheckpointError("corrupt_ownership", "next voice generation is not newer than active voices")
        allocations = [item.allocation_order for item in state.active_voices]
        if len(set(allocations)) != len(allocations) or (allocations and state.next_allocation_order <= max(allocations)):
            raise CheckpointError("corrupt_ownership", "allocation ordering is invalid")
        if deferred_orders and state.next_deferred_order <= max(deferred_orders):
            raise CheckpointError("corrupt_deferred", "next deferred-release order is stale")
        controller_keys = [(part, controller) for part, controller, _ in state.controllers]
        if (len(set(controller_keys)) != len(controller_keys)
                or any(part not in part_ids for part, _, _ in state.controllers)):
            raise CheckpointError("corrupt_controllers", "controller ownership is invalid")
        if len(set(state.sustain_parts)) != len(state.sustain_parts) or any(
                part not in part_ids for part in state.sustain_parts):
            raise CheckpointError("corrupt_controllers", "sustain part set is invalid")
        controllers = {(part, controller): value for part, controller, value in state.controllers}
        expected_sustain = {
            part for part in part_ids
            if controllers.get((part, self.SUSTAIN_CONTROLLER), 0) >= self.SUSTAIN_ON_Q16
        }
        if set(state.sustain_parts) != expected_sustain:
            raise CheckpointError("corrupt_controllers", "sustain state disagrees with controller state")
        if state.completed and state.stopped:
            raise CheckpointError("corrupt_terminal", "state is both completed and stopped")
        if (state.completed or state.stopped) and state.active_voices:
            raise CheckpointError("corrupt_terminal", "terminal state owns active voices")
        if state.paused and (state.completed or state.stopped):
            raise CheckpointError("corrupt_terminal", "terminal state cannot be paused")
        if state.completed and (state.tick != self.sequence.end_tick
                                or state.event_index != len(self.sequence.events)):
            raise CheckpointError("corrupt_terminal", "completed state has not consumed the sequence")
        if state.loop_repeats_remaining < 0 or state.loop_repeats_remaining > state.loop_repeats:
            raise CheckpointError("corrupt_loop", "remaining loop count is invalid")
        if state.loop_iteration + state.loop_repeats_remaining != state.loop_repeats:
            raise CheckpointError("corrupt_loop", "loop iteration accounting is inconsistent")
        if warm and not 0 <= state.action_count <= len(self._actions):
            raise CheckpointError("corrupt_actions", "warm action cursor is outside the live log")

    def _apply_checkpoint(self, state: PlaybackCheckpoint, *, cold: bool) -> None:
        self.tick = state.tick
        self.sample = state.sample
        self.rational_remainder = state.rational_remainder
        self._event_index = state.event_index
        self.loop_iteration = state.loop_iteration
        self.loop_repeats_remaining = state.loop_repeats_remaining
        self._controllers = {(part, controller): value for part, controller, value in state.controllers}
        self._sustain = {part.part_id: part.part_id in state.sustain_parts for part in self.sequence.parts}
        self._active = {
            item.note_id: _ActiveVoice(
                item.voice, item.voice_generation, item.allocation_order,
                NoteOnEvent(item.part_id, item.note_id, item.pitch_q8_8, item.velocity),
                item.release_velocity, item.deferred, item.deferred_order,
            ) for item in state.active_voices
        }
        self._retired_note_ids = set(state.retired_note_ids)
        self._next_voice_generation = state.next_voice_generation
        self._next_allocation_order = state.next_allocation_order
        self._next_deferred_order = state.next_deferred_order
        self.completed = state.completed
        self.stopped = state.stopped
        self.paused = state.paused
        if cold:
            self._actions.clear()
        else:
            del self._actions[state.action_count:]

    def _checked_validate(self, state: PlaybackCheckpoint, *, warm: bool) -> None:
        try:
            self._validate_checkpoint(state, warm=warm)
        except CheckpointError:
            raise
        except (TypeError, ValueError, KeyError) as exc:
            raise CheckpointError("corrupt_state", str(exc)) from exc

    def restore_warm(self, state: PlaybackCheckpoint) -> None:
        """Restore state while the same backend voices remain; emit nothing."""
        self._checked_validate(state, warm=True)
        self._apply_checkpoint(state, cold=False)

    def serialize_checkpoint(self, state: PlaybackCheckpoint | None = None) -> bytes:
        """Serialize logical state; this does *not* serialize backend voice phase."""
        state = self.checkpoint() if state is None else state
        self._checked_validate(state, warm=True)
        for value, label in ((state.realization_sha256, "realization"), (state.sequence_ir_sha256, "SequenceIR")):
            if not _SHA256_RE.fullmatch(value):
                raise CheckpointError("missing_identity", f"{label} SHA-256 is required")
        if not state.engine_id or not state.profile_id:
            raise CheckpointError("missing_identity", "engine and profile identities are required")
        body = asdict(replace(state, warm_owner_id=0, action_count=0))
        body["cold_active_voice_policy"] = self.COLD_ACTIVE_VOICE_POLICY
        body_raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = {"sha256": hashlib.sha256(body_raw).hexdigest(), "state": body}
        return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def _decode_checkpoint(raw: bytes) -> PlaybackCheckpoint:
        def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise CheckpointError("corrupt_encoding", f"duplicate key {key}")
                result[key] = value
            return result
        try:
            envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=unique)
        except CheckpointError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CheckpointError("corrupt_encoding", str(exc)) from exc
        if not isinstance(envelope, dict) or set(envelope) != {"sha256", "state"} or not isinstance(envelope["state"], dict):
            raise CheckpointError("corrupt_encoding", "invalid checkpoint envelope")
        body = envelope["state"]
        body_raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if envelope["sha256"] != hashlib.sha256(body_raw).hexdigest():
            raise CheckpointError("checksum", "checkpoint checksum does not match")
        if body.pop("cold_active_voice_policy", None) != PlaybackSession.COLD_ACTIVE_VOICE_POLICY:
            raise CheckpointError("policy", "unknown cold active-voice policy")
        expected = {field.name for field in PlaybackCheckpoint.__dataclass_fields__.values()}
        if set(body) != expected:
            raise CheckpointError("corrupt_fields", "checkpoint fields are not exact")
        try:
            body["active_voices"] = tuple(ActiveVoiceState(**item) for item in body["active_voices"])
            body["controllers"] = tuple(tuple(item) for item in body["controllers"])
            body["sustain_parts"] = tuple(body["sustain_parts"])
            body["retired_note_ids"] = tuple(body["retired_note_ids"])
            return PlaybackCheckpoint(**body)
        except (TypeError, ValueError, KeyError) as exc:
            raise CheckpointError("corrupt_fields", str(exc)) from exc

    def restore_cold(self, raw: bytes) -> None:
        """Transactionally restore logical state into a fresh session.

        No backend command is emitted. Active voice handles are deterministic
        logical ownership only; exact audio continuation additionally requires
        a backend snapshot of sample cursor, envelopes, oscillator/pitch phase,
        voice generations, and pending commands, which this schema does not hold.
        """
        if (self.tick or self.sample or self.rational_remainder or self._event_index
                or self._active or self._controllers or self._actions
                or self.completed or self.stopped or self.paused):
            raise CheckpointError("cold_target", "cold restore requires a fresh sequencer instance")
        state = self._decode_checkpoint(raw)
        self._checked_validate(state, warm=False)
        self._apply_checkpoint(state, cold=True)

    def _drain(self, reason: str) -> None:
        for item in sorted(self._active.values(), key=lambda active: (active.voice, active.note.note_id)):
            self._release(item.note.note_id, reason)
        self.backend.stop()

    def finish(self) -> None:
        if self.stopped:
            raise RuntimeError("stopped music playback cannot complete")
        if self.completed:
            return
        if self.paused:
            raise RuntimeError("paused music playback cannot complete")
        if self.loop_repeats:
            while self.loop_repeats_remaining:
                assert self.sequence.loop is not None
                self.advance_ticks(self.sequence.loop[1] - self.tick)
            self.advance_ticks(self.sequence.end_tick - self.tick)
        else:
            self.advance_to_tick(self.sequence.end_tick)
        self._drain("complete")
        self.completed = True

    def stop(self) -> None:
        if self.completed or self.stopped:
            return
        self._drain("stop")
        self.stopped = True
