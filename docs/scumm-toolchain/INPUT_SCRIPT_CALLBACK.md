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

The subsequent authentic run executed the original pickup (owner/state1/1,
error0), then reported an explicit resource error while Global10 started a
new entry of its ancestor's object carrier. A reused C4 slot retained the old
outgoing dependency and formed a cycle. Fresh script/object/input/sentence and
scroll-script allocations now invalidate both outgoing and incoming tickets
for the previous slot occupant. Canonical identity alone is not activation
identity. The synthetic fixture reproduces ancestor replacement through a
second checked page and requires the replacement to execute exactly once.

The pinned reference's `runScriptNested` also refuses to resume a frozen
caller. The host execution loop and streamed native return now preserve that
rule. The fixture freezes/yields/unfreezes before the action write, requiring
its caller to observe42 only afterward. Actual Nexen acceptance passes the
combined argument, checked-page wait, frozen caller, and same-carrier ancestor
replacement fixture; no native error and exactly one replacement execution.
Authentic map-to-destination acceptance remains a separate gate.


## Authored cutscene callbacks

The next original taxi trace reached its source dialogue at object140 PC139,
then lost that activation before its endCutscene/room request. Cutscene depth
remained1. The installed start/end callback numbers are source variables35/36
(20/21 in this edition). Host dispatch already existed; native begin/end only
maintained the stack. The authored hover loop therefore remained runnable.

Native room-service cutscenes now retain all32 normal argument words, invoke
variables35/36 through the existing ordinary StartScript allocator, and pass
the saved first argument with zero trailing locals to the end callback.
`cutSceneScriptIndex` protects the original caller from freezeScripts while
the start callback executes. Checked-code waits preserve that context; actual
caller resumption clears it. No selector, cache, or memory allocation changes.

The copyright-free nested fixture now checks both callback argument frames,
freeze ownership, ordinary source yield, checked-page continuation, and the
existing same-carrier ancestor replacement. Actual Nexen passes in23.55seconds,
error0, cutscene depth0, start arguments2/4660 and end arguments2/0. Native ROM
`ddc9382fe26bbed65a0df95458ffda8d67cfdff978cdc2e361858893a4cfea02`, map
`74aee31b728862c41158ba3f6340a2684cc16202ecdf26e7be3a4889cf89d249`, package
`020edf8036dd826df92297b04be0208b035e2936e1df3b70e4bba8613c8c1f36`, identity
`57b4844cd6a28172aa52d5b8dd8fcd371c81c12ae5c977e810d9a46aafbc1093`.
These are synthetic native results, not authentic destination acceptance.

Hosted assembly caught a separate include dependency: the cutscene bridge was
inside the controller-only include, although room-service builds can omit the
controller. It now has its own room-service include in the same far bank.
The controller-disabled native build assembles and audits. The authentic ROM
and package are byte-identical before/after this source-file move; the map is
identical after excluding its generated timestamp. Existing native observations
retain their original ROM/map/build identity, with explicit byte-equality
linkage to the repaired build rather than relabeling old evidence.
