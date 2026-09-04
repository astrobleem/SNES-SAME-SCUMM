import gc
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock
import weakref

from same.music import (
    CheckpointError, ControllerEvent, InstrumentRequest, MarkerEvent,
    NoteOffEvent, NoteOnEvent, PartSpec, PlaybackSession, Provenance,
    ScheduledEvent, SequenceIR,
)


IDENTITY = "6f" * 32


class TraceBackend:
    def __init__(self) -> None:
        self.commands: list[tuple[object, ...]] = []

    def advance(self, frames: int) -> None:
        self.commands.append(("advance", frames))

    def note_on(self, voice: int, event: NoteOnEvent) -> None:
        self.commands.append(("note_on", voice, event.part_id, event.note_id,
                              event.pitch_q8_8, event.velocity))

    def note_off(self, voice: int, event: NoteOffEvent) -> None:
        self.commands.append(("note_off", voice, event.part_id, event.note_id,
                              event.release_velocity))

    def controller(self, event: ControllerEvent) -> None:
        self.commands.append(("controller", event.part_id, event.controller,
                              event.value_q16))

    def stop(self) -> None:
        self.commands.append(("stop",))


def checkpoint_sequence() -> SequenceIR:
    source = Provenance("m18.fixture")
    part = PartSpec(0, InstrumentRequest(gm_fallback=0), requested_polyphony=4)
    payloads = (
        (0, ControllerEvent(0, 7, 48_000)),
        (0, ControllerEvent(0, 64, 1 << 16)),
        (0, NoteOnEvent(0, 10, 60 << 8, 90)),
        (0, NoteOnEvent(0, 11, 60 << 8, 80)),  # overlapping pitch and part
        (1, NoteOffEvent(0, 10, 31)),
        (1, NoteOffEvent(0, 11, 32)),
        (2, ControllerEvent(0, 64, 0)),
        (3, NoteOnEvent(0, 12, 62 << 8, 70)),
        (3, NoteOnEvent(0, 13, 64 << 8, 71)),
        (3, NoteOnEvent(0, 14, 65 << 8, 72)),
        (4, NoteOnEvent(0, 15, 67 << 8, 73)),  # steals note 12
        (5, NoteOffEvent(0, 12)),               # retired stolen identity
        (5, NoteOffEvent(0, 13)),
        (6, NoteOffEvent(0, 14)),
        (6, NoteOffEvent(0, 15)),
        (7, MarkerEvent("end")),
    )
    events = tuple(
        ScheduledEvent(tick, order, payload, source)
        for order, (tick, payload) in enumerate(payloads)
    )
    return SequenceIR(7, (part,), events, 7, source)


def loop_sequence() -> SequenceIR:
    source = Provenance("m18.loop.fixture")
    part = PartSpec(0, InstrumentRequest(gm_fallback=4))
    payloads = (
        (0, MarkerEvent("intro")),
        (1, NoteOnEvent(0, 20, 65 << 8, 80)),
        (3, NoteOffEvent(0, 20)),
        (4, MarkerEvent("after-loop")),
        (5, MarkerEvent("end")),
    )
    return SequenceIR(
        7, (part,), tuple(ScheduledEvent(t, i, p, source)
                         for i, (t, p) in enumerate(payloads)),
        5, source, loop=(1, 4),
    )


def session(sequence: SequenceIR, backend: TraceBackend, **extra: object) -> PlaybackSession:
    return PlaybackSession(
        sequence, backend, sample_rate=10, realization_sha256=IDENTITY,
        engine_id="same.music", profile_id="m18-test", **extra,
    )


def logical_state(playback: PlaybackSession) -> tuple[object, ...]:
    state = playback.checkpoint()
    return (
        state.tick, state.sample, state.rational_remainder, state.event_index,
        state.loop_iteration, state.loop_repeats_remaining, state.controllers,
        state.sustain_parts, state.active_voices, state.retired_note_ids,
        state.next_voice_generation, state.next_allocation_order,
        state.next_deferred_order, state.completed, state.stopped, state.paused,
    )


class MusicCheckpointTests(unittest.TestCase):
    def assert_cold_fork(self, prepare, *, sequence: SequenceIR | None = None,
                         constructor: dict[str, object] | None = None) -> None:
        sequence = checkpoint_sequence() if sequence is None else sequence
        constructor = {"voice_limit": 3, "voice_policy": "steal_oldest"} if constructor is None else constructor
        backend_a = TraceBackend()
        backend_old = TraceBackend()
        run_a = session(sequence, backend_a, **constructor)
        run_old = session(sequence, backend_old, **constructor)
        prepare(run_a)
        prepare(run_old)
        encoded = run_old.serialize_checkpoint()
        start_a = len(backend_a.commands)
        old_ref = weakref.ref(run_old)
        del run_old
        gc.collect()
        self.assertIsNone(old_ref())

        backend_b = TraceBackend()
        run_b = session(sequence, backend_b, **constructor)
        with mock.patch("same.music.importers.decode_qtma_events", side_effect=AssertionError("QTMA importer reached")), \
             mock.patch("same.music.importers.extract_qtma_movie", side_effect=AssertionError("MOV importer reached")):
            run_b.restore_cold(encoded)
        self.assertEqual(backend_b.commands, [])
        self.assertEqual(logical_state(run_a), logical_state(run_b))

        if run_a.paused:
            run_a.resume()
            run_b.resume()
        if not run_a.completed and not run_a.stopped:
            if run_a.loop_repeats:
                while run_a.loop_repeats_remaining or run_a.tick < sequence.end_tick:
                    run_a.advance_ticks(1)
                    run_b.advance_ticks(1)
                    self.assertEqual(logical_state(run_a), logical_state(run_b))
                    self.assertEqual(backend_a.commands[start_a:], backend_b.commands)
            else:
                for tick in range(run_a.tick, sequence.end_tick + 1):
                    run_a.advance_to_tick(tick)
                    run_b.advance_to_tick(tick)
                    self.assertEqual(logical_state(run_a), logical_state(run_b))
                    self.assertEqual(backend_a.commands[start_a:], backend_b.commands)
            run_a.finish()
            run_b.finish()
        self.assertEqual(logical_state(run_a), logical_state(run_b))
        self.assertEqual(backend_a.commands[start_a:], backend_b.commands)
        self.assertEqual(run_a.actions[-len(run_b.actions):], run_b.actions)

    def test_fork_oracle_before_during_after_timestamp_groups_and_remainder(self) -> None:
        preparations = (
            lambda run: None,                       # immediately before tick-zero group
            lambda run: run.advance_one_event(),   # during same-timestamp group
            lambda run: run.advance_to_tick(0),    # after same-timestamp group
            lambda run: run.advance_to_tick(1),    # note-off group + remainder 3/7
            lambda run: (run.advance_to_tick(0), run.advance_one_event()),
            lambda run: run.advance_to_tick(3),    # immediately before stealing
        )
        for index, prepare in enumerate(preparations):
            with self.subTest(checkpoint=index):
                self.assert_cold_fork(prepare)

    def test_fork_oracle_crosses_loop_boundaries(self) -> None:
        constructor = {"voice_limit": 2, "loop_repeats": 1}
        for elapsed in (3, 4):  # immediately before and immediately after reset
            with self.subTest(elapsed=elapsed):
                self.assert_cold_fork(
                    lambda run, elapsed=elapsed: run.advance_ticks(elapsed),
                    sequence=loop_sequence(), constructor=constructor,
                )

    def test_warm_restore_is_command_silent_and_repeatable(self) -> None:
        backend = TraceBackend()
        run = session(checkpoint_sequence(), backend, voice_limit=3,
                      voice_policy="steal_oldest")
        run.advance_to_tick(1)
        state = run.checkpoint()
        before = list(backend.commands)
        run.restore_warm(state)
        run.restore_warm(state)
        self.assertEqual(backend.commands, before)
        self.assertEqual(run.checkpoint(), state)
        other = session(checkpoint_sequence(), TraceBackend(), voice_limit=3,
                        voice_policy="steal_oldest")
        with self.assertRaisesRegex(CheckpointError, "warm_owner"):
            other.restore_warm(state)

    def test_pause_stop_note_off_and_end_states_round_trip(self) -> None:
        def paused(run: PlaybackSession) -> None:
            run.advance_to_tick(1)
            run.pause()
        self.assert_cold_fork(paused)

        for terminal in ("stop", "finish"):
            with self.subTest(terminal=terminal):
                backend = TraceBackend()
                original = session(checkpoint_sequence(), backend, voice_limit=3,
                                   voice_policy="steal_oldest")
                if terminal == "stop":
                    original.advance_to_tick(1)
                    original.stop()
                else:
                    original.finish()
                raw = original.serialize_checkpoint()
                restored = session(checkpoint_sequence(), TraceBackend(), voice_limit=3,
                                   voice_policy="steal_oldest")
                restored.restore_cold(raw)
                self.assertEqual(logical_state(original), logical_state(restored))
                self.assertEqual(restored.backend.commands, [])

    def test_corrupt_and_mismatched_cold_states_reject_transactionally(self) -> None:
        original = session(checkpoint_sequence(), TraceBackend(), voice_limit=3,
                           voice_policy="steal_oldest")
        original.advance_to_tick(1)
        raw = original.serialize_checkpoint()
        target_backend = TraceBackend()
        target = session(checkpoint_sequence(), target_backend, voice_limit=3,
                         voice_policy="steal_oldest")
        before = logical_state(target)
        damaged = bytearray(raw)
        damaged[len(damaged) // 2] ^= 1
        with self.assertRaises(CheckpointError):
            target.restore_cold(bytes(damaged))
        self.assertEqual(logical_state(target), before)
        self.assertEqual(target_backend.commands, [])

        mismatches = {
            "schema_version": 2,
            "sequence_ir_sha256": "00" * 32,
            "realization_sha256": "11" * 32,
            "engine_id": "another-engine",
            "profile_id": "wrong-profile",
            "timing_id": "another-clock",
            "sample_rate": 11,
            "source_time_scale": 8,
            "voice_limit": 4,
            "voice_policy": "error",
            "loop_repeats": 1,
        }
        for field, value in mismatches.items():
            with self.subTest(binding=field):
                envelope = json.loads(raw)
                envelope["state"][field] = value
                body = json.dumps(envelope["state"], sort_keys=True, separators=(",", ":")).encode()
                envelope["sha256"] = hashlib.sha256(body).hexdigest()
                mismatch = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
                with self.assertRaisesRegex(CheckpointError, "mismatch"):
                    target.restore_cold(mismatch)
                self.assertEqual(logical_state(target), before)
                self.assertEqual(target_backend.commands, [])

        envelope = json.loads(raw)
        envelope["state"]["active_voices"][1]["voice"] = \
            envelope["state"]["active_voices"][0]["voice"]
        body = json.dumps(envelope["state"], sort_keys=True, separators=(",", ":")).encode()
        envelope["sha256"] = hashlib.sha256(body).hexdigest()
        corrupt_ownership = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
        with self.assertRaisesRegex(CheckpointError, "corrupt_ownership"):
            target.restore_cold(corrupt_ownership)
        self.assertEqual(logical_state(target), before)
        self.assertEqual(target_backend.commands, [])

        # The same immutable bytes produce the same logical state repeatedly.
        first = session(checkpoint_sequence(), TraceBackend(), voice_limit=3,
                        voice_policy="steal_oldest")
        second = session(checkpoint_sequence(), TraceBackend(), voice_limit=3,
                         voice_policy="steal_oldest")
        first.restore_cold(raw)
        second.restore_cold(raw)
        self.assertEqual(logical_state(first), logical_state(second))
        self.assertEqual(first.backend.commands, second.backend.commands)

    def test_cold_serialization_requires_all_build_identities(self) -> None:
        run = PlaybackSession(checkpoint_sequence(), TraceBackend(), sample_rate=10)
        with self.assertRaisesRegex(CheckpointError, "missing_identity"):
            run.serialize_checkpoint()


if __name__ == "__main__":
    unittest.main()
