# Raw input callbacks (Milestone D)

This work is a successor to PR15, not a change to its qualified camera scope.
The callback and original room10 ->75 ->2 transition are observed natively.
**Milestone D is incomplete:** room2's authored actor scale reaches an explicit
unsupported native rendering path. Destination presentation and resumed player
control are not accepted. No scale override or story patch was applied.

## Current native checkpoint

Runtime `76d7448f9fe2e61dda7c450193f0b6c673c4b394`; observer/test correction
`44c038bceb33b4417428bfe533772e64940d3e8d`. The latter waits for both held and
pressed input to clear before issuing the next distinct controller edge. A
neutral sampled level alone does not prove the prior press latch was consumed.

One continuous continuation from an exact-ROM room10 checkpoint executes
Use taxi, acknowledges the original dialogue, selects Barnett College on the
map, runs the authored callback and arrives in room2. No reset or state restore
occurs between those transitions; this is **not a continuous cold-start claim**.
The checkpoint itself comes from a separate original cold startup/newspaper/
readable-inventory run on the same ROM. Neither session uses synthetic story
scripts, guest gameplay writes or the historical seven-action replay.

| Observation | Exact evidence |
|---|---|
| Map presentation | Frame8928, completed generation170, zero source/INDEX8, source/VRAM-raster and source/CGRAM differences |
| Input callback | Frame9046, local204/canonical2018, `RoomLocalProgram(room=75,local=204)`, locals `[2,0,1]`, observed runnable at PC0 |
| Single ownership | Accepted/allocated tickets each advance4 ->5; no independent C20 sentence is submitted |
| Original destination action | Object1028 verb10, canonical783, following original local202; source selects room2 |
| Arrival | Room2 observed by frame10902, entry/local200 execute; original newspaper owner/state remain1/1 |
| Failed boundary | Error16 observed at frame10950; no accepted destination actor image or resumed player control |

The full source package still contains all2,203 ProgramUnits. The host source
component test executes the original callback/object path to a room2 request;
its intercepted destination-loader boundary is not host full-game acceptance.

| Artifact | SHA-256 |
|---|---|
| Authentic ROM | `46480f0d0ec328dfd9ac17d196fa2d85f5e39386afbf86af9a6804c9cd331dd8` |
| Matching map | `fc266c2e40067262e381ee1792c85719b4dc0c05a8c006a26dbca4418c1d23b2` |
| SAMEPKG | `e6cf5c28f36f20c10cb9ef7819a1b278b1067ed3014462cee53d9a63d9772afd` |
| Build identity JSON | `cf5a0540c4bd133db247c54c056989b9812f60196dab3da0cbd67b33859f0fbf` |

Private evidence root:
`/home/chad/SAME-private-evidence/milestone-d-input-callback-20261112`.
`continuous-lifecycle-input-fence/observations` contains the single trip's
journal, snapshots and map/failed-destination images. `cold-lifecycle-room10`
contains its checkpoint provenance. `source-linkage-lifecycle.json` compares
all61 nongenerated runtime files in both isolated builds against76d7448 with
zero mismatches. Later observer/tests/docs commits are not relabeled as new
native builds. Commercial captures, raw resources, packages and ROMs remain
outside Git.

## Remaining native actor-scale boundary

A separate68.44-second exact-ROM, read-only hook diagnostic confirms the
cause, not just a timeout or absent screenshot. At frame10957 it observes:

- `$09:9F9D`, `ScummV5_ActorPose_Compose__owner_ok`, counter514344767;
- `$09:A38D`, `ScummV5_ActorPose_Compose__invalid`, counter514344785;
- error16 written to `$7E2303`, counter514344795.

The intervening assembled code loads actor1's scale word and compares `$FFFF`;
the captured original scale is231/231. The `$09:9FAC __scale_ok` hook does not
fire. The later CPU snapshot is **not** an instruction-exact stop; only the
hook addresses/counters establish this path. Evidence is in
`college-scale-guard-hooks/observations`. The destination has a pending visual
transaction and an invalid actor render key despite a background generation;
its screenshot is retained as failure evidence, not a passing PPU comparison.

Host `room.py` already implements the classic per-cel scale table, signed
anchor phases, mirrored column traversal and overwrite order. Native
`compile_pose` currently flattens unscaled cels into final opaque spans;
the compositor explicitly supports255/255. Scaling those flattened spans with
an arbitrary bitmap resize would not preserve source behavior. The native
path needs the existing host semantics connected to checked costume data,
scale-sensitive pose identities and damage/publication lifetimes.

This is not solved by baking only scale231: room2's source walkboxes also use
dynamic scale slots and other fixed scales. Baking every scale for the current
444 poses would require over2.7MiB of24-byte pose records alone, versus the
current single32KiB pose/chunk/palette directory bank. No such expansion was
implemented. Actor5/costume78 is another authored visible actor; the current
native renderer selects actor1 only, so multi-actor presentation also remains
unverified. Its source poses fit individual checked chunks; do not misclassify
that remaining limitation as proven chunk-capacity exhaustion.

## Current validation

The final local suite runs1,635 tests: **1,623 passed,12 skipped**.
`make validate`, the43-region memory audit, pinned Poppy assembly and both
4MiB ROM audits pass. Copyright-free actual Nexen callback/lifecycle acceptance
passes on the runtime above, including four nested-exit markers42 and error0.
Host instruction-model tests are reported separately from this native run.
Both hosted checks passed on44c038b:
[Independent validation](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43372654120).
Hosted assembly is not Nexen execution. Green tests do not certify the blocked
destination. Whole-game readiness remains **NOT_READY**.

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


## Optional object verbs during room exit

The original map callback now runs with locals `[2,0,1]`, canonical unit2018
(`RoomLocalProgram(room=75,local=204)`), and dispatches object1028's authored
verb10 after local202. The source requests room2. This was observed natively;
it is distinct from completed destination presentation or resumed player control.

The first exit attempt failed when the ordinary hover script probed a missing
object verb90. A read-only exact-ROM continuation with execution/write hooks
identified `ScummV5_LiveRoom_ObjectProgramResolve_Far__bad` immediately before
error11. The captured query is object1028/verb90/result0. This is not evidence
of a missing global script14, despite the parent's saved StartScript PC.

The pinned reference's `runObjectScript` returns normally when
`getVerbEntrypoint` returns0. The native live resolver now distinguishes that
ordinary absence from a failed canonical binding. An absent entry creates no
binding or checked read and does not erase an existing error; a genuine binder
failure retains its error. The existing StartObject no-entry path remains the
consumer. No game-specific object or verb numbers appear in the correction.

The public fixture probes an absent verb92, then continues into its existing
checked-page action/hover, cutscene and ancestor-replacement controls. Host
and actual Nexen pass, including marker123=1, error0, exact callback arguments
and one replacement. Runtime commit `e3719365e0663bcfc227027e5b5c7cf1c9daa540`;
synthetic ROM `74a4d55b55594db340a3b1d7bc991fa88dd855b6fb1ebdf66e23e5ff1c51cd7e`.
All61 nongenerated runtime source files match both isolated builds.

## Room capture versus actor proof

A settled room may deliberately hide actor1. The observer now has a separate
room-surface fence; actor proof still requires a visible validated actor pose.
Both reject pending/in-flight work, wrong room identity and unmatched generations.
Room-only captures do not report an accepted actor frame or invented foot.
Actual source pixels and decoded VRAM/CGRAM remain independently compared.
An emulator screenshot immediately after savestate restoration can contain an
old framebuffer even when restored video memory is correct. Such a screenshot
is not accepted as visible presentation; capture must follow completed emulation.

## Nested lifecycle checked-read descendants

The original map callback now selects Barnett College with ordinary locals
`[2,0,1]`, resolves `RoomLocalProgram(room=75,local=204)` (canonical2018),
executes the original object1028 verb10 and requests room2. Its EXCD then exposed
a separate scheduling defect. An identity-bound paused capture showed slot0
waiting for slot5, which waited for slot7; all three had WAIT_RESOURCE status
and zero freeze counts. The direct lifecycle runner retried slot5 without ever
servicing slot7. This is stronger evidence than an idle-frame timeout.

Commit `76d7448` traverses the existing exact child tickets with the25-slot hop
bound, runs only the dependent descendant, and clears only its immediate
parent's completed edge. Slot0 is rehydrated on every return. Out-of-range,
stale-selector and cyclic tickets fail explicitly; no extra WRAM, cache policy,
selector width or independent scheduler is introduced.

The original public input fixture's `--lifecycle-chain` variant adds a third
normal controller callback and EXCD -> global9 -> global10 -> global11. The
three bodies use distinct checked pages. Four propagated values must all be42
before resource-less room0 publication. The host oracle uses the compiler's
cooked room record (raw-room host rendering does not register ENCD/EXCD).
Actual Nexen passes all four markers, error0, existing held-edge/argument,
object-carrier, cutscene and ancestor-replacement controls in21.65seconds.
Native ROM `8d3d77278743fdec9c328a57030a8d6e6a699724db3a01c4013ddb237532b400`.
An earlier observer incorrectly required phase3 for null room0; that run is
not acceptance. The corrected fence requires room0's established idle phase0.
All61 non-generated runtime files in the isolated native build match76d7448.
