# Focused execution update

This is a screened, source-only handoff. It contains no ROM, save state,
ATLANTIS archive, cooked room payload, or emulator trace dump.

## Long-message and scheduler evidence

The accepted headless message behavior is logical rather than visual:
`C23` decodes the complete stream, `Talk_Begin_Far` retains message ownership
and logical length, and frame processing releases `waitForMessage` only at the
normal completion boundary. The 32-byte presentation buffer is a display
limit; it is not a message terminator. Embedded continuation controls remain
in the logical stream.

The scheduler fix saves the selected C4 slot only after the selected program
has returned, using the slot's own program identity and PC. Nested execution
cannot save a child context into the parent, and byte-indexed slot scans
re-establish 8-bit index width on each pass.

## Same-ROM evidence

The current local debug46 ROM has SHA-256:

`1a618f6fd12f58f1840a91270bc3d56efe892d1e834dc4a53060f04d1c539f12`

Focused startup42 execution on that ROM ran in safe frame steps through room
42, room 82, and back to room 42 with `error=0`. Room-82 local scripts,
including LSCR 207, executed; the former room-82 opcode failure was removed.
The detailed report remains local and is intentionally excluded from this
branch.

## Validation

`PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q`

Result: 123 tests passed. The new generic `$3B/$BB getActorScale` test covers
direct and variable actor operands; the existing message, nested-scheduler,
width, and sentence-fetch tests remain green. `git diff --check` passes.

This handoff does not claim that the broad implementation commit is screened
for publication; it publishes only review evidence and source-level claims.
