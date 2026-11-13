# Raw input callbacks (Milestone D)

This work is a successor to PR15, not a change to its qualified camera scope.
Travel-map destination gameplay is not yet certified by this document.

## Contract

SCUMM v5 variable32 selects the raw input callback. Variable33 still selects
queued semantic sentences. The pinned reference is ScummVM
`10a54c2696126a81ee2b2f7f10b1a8be90ed7711`, `runInputScript` in `script.cpp`,
`verbs.cpp` and `verbs.h`. The first three ordinary locals are click area,
value and mode. Areas are verb1, scene2, inventory3, key4, sentence5; v5
primary/secondary pointer modes are1/2. A scene event supplies value0.

The host exposes `queue_input_event`. The native controller maps A/B scene
edges and confirmed original verb/inventory choices to a bounded mailbox.
Menu navigation itself does not submit an action. A callback-owned scene edge
cannot independently enter C20: the authored callback creates any sentence.
Without a callback the existing controller sentence path remains available.
Mouse globals20/21 and44/45 are published from the logical pointer.

The mailbox snapshots script number, arguments, input-edge sequence and room
request identity. A repeated held edge cannot allocate twice. Room publication
or a newer room request invalidates unconsumed input, including a same-room
revisit. An accepted event becomes one ordinary nonrecursive C4 activation,
with zeroed32-word locals, normal global/local resolution, freeze and room
ownership. Execution uses the existing checked cache; no permanent selector
or direct bytecode call is introduced. Capacity/resolution failures become
explicit errors. Pending host input is explicitly not portable-saveable.

Native mailbox allocation: `$7E22A0..$7E22B3` (20 bytes), immediately after the
DMA descriptor pool and before the VM. The memory audit covers both regions.
Code resides in the existing camera far-code bank; the first placement in the
controller bank was rejected by the ROM audit and was not used as acceptance.

## Adjacent input consumers

The authentic callback exposed two existing disconnected consumers:

- `cursorCommand` changed native cursor/user-input fields but did not publish
  variables52/53. Original hover scripts consequently remained disabled even
  with a visible cursor. Native publication now matches the existing host.
- `findObject` in a room-service build queried the isolated C21 fixture's
  three objects. It now uses the same installed room geometry query as the
  controller. Non-room-service C21/C30 conformance retains its original path.

This reuses the existing live projection, not a new parser or object table.
It does not certify every original object visibility/class/parent operation;
complete parent-chain and mutable-class filtering in the live hit-test remain
an independent capability frontier. The original source and tests determine
which concrete interactions are qualified.

## Evidence

The public `input_callback_fixture.py` creates original SCUMM resources.
Normal A runs local204, recording `[2,0,1]`, then installs global2. A held button
does not repeat. B runs global2 with `[2,0,2]`; it starts global3 with argument42,
yields and resumes. It also queries object77 from the checked installed room
and reads cursor/user-input values1/1. Host and actual Nexen values100..113 are:

`[2,0,1,1, 2,0,2,1,1,42,1, 77,1,1]`.

Exactly two callback acceptances/allocations and error0 are required. This is
source-compiled execution through the actual resolver, not the instruction
runner used by the separate mailbox unit tests. Native artifacts and process
reports are private under `milestone-d-input-callback-20261112`.

The first authentic run correctly allocated the original global4 callback but
could not pick up the newspaper. Its preserved state showed variable52=0,
hover object0 and the C21 fixture records despite12 installed room objects.
A five-second, read-only exact-ROM checkpoint inspection established this
boundary without replaying the trip. That failed run is not acceptance.

## Supervision

`tools/run_visual_once.py` is the canonical private-Xvfb supervisor. It strips
inherited DISPLAY/XAUTHORITY, performs one attempt, enforces at most600 seconds,
and cleans its owned descendants, including detached children, on normal exit,
timeout and SIGTERM. Process-only regressions verify those contracts. A process
exit is never treated as native or pixel acceptance. The validator remains the
only MCP client. Unrelated user emulator sessions are neither connected nor
terminated.

## Nested execution and checked-code waits

The authentic source trace reached object141's pickup entry PC60 in
WAIT_RESOURCE, then replaced it with its hover entry PC175 before the pickup
executed. This is a storage scheduling boundary, not an authored no-op.

The far nested-call helper also returned from its frame-index calculation in
A16 and wrote words into byte-sized pending-child tickets. An instruction-level
regression reproduced the adjacent-ticket overwrite; explicit A8 restores the
contract. C4 now follows its existing pending-child tickets to admit the
synchronous child before unrelated activations. Once the child reaches an
ordinary yield/stop/error, the parent continues through the existing handling.
Frozen callers release satisfied tickets so the child's later unfreeze can
run. New raw-input events remain accepted in their room-bound mailbox while a
nested storage continuation owns execution. Provider service and NMI remain
resumable; independently waiting activations with no nested call retain normal
admission. No executable-cache allocation or selector ABI changes are made.

The public callback fixture's optional `--nested-object-wait` case places
an action and a competing hover loop on separate checked pages of one carrier.
The action writes42; its caller must observe42. A freeze/yield/unfreeze also
checks release of the satisfied parent ticket. These are original test scripts,
not edits to the commercial game's story. Instruction-runner tests cover exact
byte writes, neighboring guards, deep waits, replacement, frozen parents,
bounded invalid tickets and deferred input ownership. They are host evidence;
actual Nexen results are recorded separately against their ROM identity.
