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

The current local startup42 debug53 ROM has SHA-256:

`9eab9a4847f78db12db0882ce5963dea54e7859f5573804ca6c65dc35eacb681`

Focused startup42 execution on that ROM ran in safe frame steps through room
42, room 82, and back to room 42 with `error=0`. Room-82 local scripts,
including LSCR 207, executed; the former room-82 opcode failure was removed.
The SNES family matcher was additionally audited so `$7B/$FB getActorWalkBox`
cannot alias the exact `$3B/$BB getActorScale` family.
The detailed report remains local and is intentionally excluded from this
branch.

The target message fixture was also rerun against matching ROM builds. The
generated map places its variable table at `$7E0800`; the run observes the
post-wait `var10=1` write, but currently stalls before the canonical delayed
C23 completion/clear boundary. This is retained as an open execution result,
not presented as a passing message-lifetime proof. No fixture-only message
auto-clear is enabled.

## Validation

`PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q`

Result: 123 tests passed. The new generic `$3B/$BB getActorScale` test covers
direct and variable actor operands; the existing message, nested-scheduler,
width, sentence-fetch, and actor-family coverage remain green. `git diff --check`
passes.

This handoff does not claim that the broad implementation commit is screened
for publication; it publishes only review evidence and source-level claims.
