# FATE authentic-resume repair checkpoint

This document records a bounded repair checkpoint for the investigation
snapshot `20f50d89a548615ba85b209d5c2976449f3f03a2`. It is not a claim that
the authentic room42 scenario or the full FATE action was reached. No new
open-ended gameplay run was performed for this checkpoint.

## Baseline suite disposition

The full baseline `make test` run from a clean detached checkout reported
803 tests, 6 failures, 4 errors, and 8 skips. The supplied review described
two errors; the clean reproduction had two additional test-model `KeyError`s.
The complete log is retained in the review handoff evidence.

| Baseline test(s) | Classification | Disposition |
| --- | --- | --- |
| `test_fate_room4_message_input`, `test_fate_room5_navigation` | Missing committed dependency | Recovered the reusable message-generation and world-point helpers into `tools/fate_replay.py`; the tests import that durable module. |
| `test_overflow_handoff`, `test_primary_handoff` | Stale test-model dependency | Added the omitted `SAME_SCUMM_RETURN_MODE` model value; the replacement assertions remain. |
| `test_scumm_run_save_restore` | Stale expectation | The host already exposes deterministic default variables. Tests now assert the script-controlled value and defaults rather than requiring an incomplete whole-dictionary snapshot. |
| Four `test_scumm_v5_cooked_room` cases | Stale fixture variable IDs | Their counters collided with built-in default variables. Moved fixture counters to non-default IDs; lifecycle ordering, rejection, room-zero cleanup, and outer-context assertions remain. |
| `test_two_tick_semantic_and_service_trace` | Stale expectation | Asserts its authored variable and default-variable values instead of rejecting legitimate defaults. |
| Host owner/matrix reproduction probes | Real behavioral regression | Save/load omitted mutable object-owner and script-created walkbox routing state; fixed as described below. |

The two recovered helpers are exercised by regular unit tests; the original
one-off native probes remain untracked and were not added to the repository.

## Host save-state correction

SCUMM save-state schema 6 now serializes the current object-owner table and
the optional dynamic walkbox routing matrix. Restore validates both fields
before mutating engine state. Older schema-6 saves without these optional
fields use archive ownership defaults and authored room routes; a saved
script-created route is restored exactly and is not rebuilt from defaults.

Behavioral host tests cover pickup/save/fresh-host restore, restoring an
earlier save after later ownership changes, old-save defaults, and a created
walkbox matrix whose first movement step matches before and after fresh-host
restore. These are host executions, not SNES-native claims.

## C19 native skip-index correction

`ScummV5_C19_AbortOverride_Far` now zero-extends every byte-sized override
depth/slot before indexing while X is 16-bit. The matching `BeginOverride`
byte-index boundary is corrected as well. No room, script, or actor-specific
case was added.

The isolated native control uses a generated copyright-free 300-byte script
that records its override continuation at `$011B`. On the diagnostic ROM
`62ca792cb1d088d1e7650720499c967c0b0db744d16423a8f87dcb608d3985f5`, Nexen
executes the X-skip gate, restores the continuation into C4 slot 1, selects
that activation once, and executes its skip-only marker once. The selected
override record is consumed, neighboring sentinel records are unchanged,
the resume PC is `$011B`, the terminal PC is `$012C`, SCUMM error is zero,
and the native JSL/RTL stack witness is balanced (`8175 -> 8176 -> 8179`).
The control intentionally seeds inactive neighboring-record sentinels; it is
a bounded synthetic native regression, not gameplay-state setup.

## Observer and input discipline

`tools/fate_replay.py` separates event-time hook data from snapshots read
after notification draining. Unsynchronized batches retain their native event
timestamps and label later slot/program/PC reads as drain-time snapshots.
Tests use multiple activation events in one batch.

Error-watch advancement uses bounded frame windows and the same controller
press/release schedule as the ordinary runner. It respects the pending
release frame, verifies actual frame advancement and timeout results, and
releases the input lease in cleanup. Fake-session tests cover those
properties without gameplay.

## Reusable historical input prefix

`examples/replays/fate-room4-open-trapdoor.json` and
`tools/replay_fate_room4_prefix.py` preserve the previously successful
room-4 cursor and Open/trapdoor input prefix. Its evidence is explicitly
historical and tied to ROM SHA
`aa85cc2e8f26279b7e9254d711f352e4caf4a5202008d8b0de75488bd4d346b0`, map
SHA `6f7de8b6006cb63399446877dfb709633ba54b70e92e05999dd25702799d037b`,
build identity SHA
`ca7c2804a926a65a57bf0fa5795de7a2eeadb043a4cd5b966e6f7826140d850f`, and
Nexen SHA `17d243c404b8ef32bbb1754a5b026584f2ae24cb047f54b9f250a6f4b721650a`.
The driver requires a same-ROM room4-ready state and a sidecar binding the
state bytes to that ROM/build; neither state nor ROM is committed. It
verifies room/controller preconditions, sends ordinary input only, releases
each press, and checks object 61/Open selection and one sentence submission.
This is a state-assisted replay tail, not cold-start acceptance, and the
historical input prefix has not been represented as a new execution on the
repair ROM.

## One previously observed refusal

The only classified gameplay boundary is the already-recorded room75
Barnett/map-object attempt in the historical report
`authentic-room75-barnett-getdist-v62-cold-fixed-observer.json`, tied to ROM
SHA `83121557cb92c153741900dffb29c828dadf6a09ac16ebedcf89c75a4903ab13`.
No replay was launched for this checkpoint. That report records ordinary
controller selection of object 1028 with verb 10 at cursor `(180,67)`,
submission advancing from 255 to 0, and a native `GetDist` execution in
program `$D0`, slot 1. The message text decodes to “I can't reach it”; room
75 remains phase 0, error 0, lifecycle RUNNING. Thus this was not a missed
input, wrong hit-test selection, unresolved script start, or SCUMM runtime
error. It is an authored reachability refusal / unsatisfied action context.
The exact upstream story prerequisite is not proven here: the historical
state shows actor 1 recorded in room 10 while room 75 is active, so the
context may itself reflect the prior exploratory route. This is a classified
refusal boundary, not acceptance of an authentic cold path.

## Operating rule

`AGENTS.md` now requires successful interactions to become reusable replay
steps, known setup/input procedures to be recorded and reused, and each
repeat experiment to change a hypothesis, observation, implementation, or
controlled input. Two equivalent UI attempts with no new evidence end UI
retries; instrumentation or a concrete blocker report follows. A red
regression must be fixed or explained before gameplay resumes. No endless
player-choice exploration is required.
