# Office inventory continuation

**Current bounded acceptance:** original Barnett-to-office gameplay now opens
the ice box, acquires and renames the jar, displays readable inventory and
continues walking. See the final acceptance below; earlier failed/qualified
observations remain historical, not alternative passes.

This work continues from Milestone E in PR17. The historical office/coat
checkpoint is preserved, but its coat reachability is qualified below after
restoring omitted source classes; it is not a whole-game completion boundary.
PR18 is additive on `scumm-fate-barnett-exploration`.

## Original source route

The installed office (room1) contains ice box21, fridge-door28 and jar22.
Original Open21 enters its OBCD atPC76. It sets the door to state1 and makes
the jar available according to the original ownership/class conditions.
Pickup22 enters atPC151, transfers ownership to Ego, sets state1, changes
classes16/32 and stores the original name `jar of mayonnaise`. The isolated
host original-body oracle verifies that result for both values of the
prior-description predicates. It is not a host playthrough or native pass.

## First newly observed failure

A normal Walk click at approximately(229,142) selected the unnamed floor
object30, whose source class mask includes32 (untouchable). The original
sentence script therefore walked toward that object's default point instead
of the cursor. Native error remained0: an error counter alone misses this
semantic defect. The continuation was deliberately stopped after the first
observed wrong target; supervisor cleanup completed with no owned survivors.
No retries of that implementation or gameplay-state writes were used.

The generated room-service hit test had rectangle checks but no mutable-class
filter. The standalone host interpreter's `findObject` already filtered32.
The correction queries the existing C16 table after a rectangle match,
preserving source record order, caller X/Y and width state. At that checkpoint, missing C16 records meant no classes; the follow-up below
corrects that incomplete source-initialization contract. Ownership alone is not a touchability predicate. No name,
object ID, room ID or game title selects the behavior; no memory is allocated.
The host room-adapter helper now accepts the same class predicate.

## Focused conformance

The copyright-free `actor_scene_fixture --hit-test-probe` installs overlapping
room objects and uses normal bytecode to set/clear class32, change ownership
and call findObject. Host and native results are
`[0,8,9,8,0x1357,8,0,0]`. The native control reaches the sentinel atframe360,
SCUMM error0, with no BRK or executable-WRAM mirror write. Supervised execution
and cleanup complete in17.976 seconds. This is semantic native conformance,
not authentic office gameplay or a new visual acceptance.

Synthetic ROM SHA-256:
`9c17ab0eee37f77ab931124485e23e1a1cbf8a129d58030fbbcc3b38ab16c1c7`.
The existing pinned compiler,4MiB ROM audit and47-region memory audit pass.
The complete authentic package remains byte-identical to accepted E:
`b6afddbf486ee26f85bb444cb03060d9606864138e3d1b3ed282657f77a09111`.

The corrected authentic ROM is
`c90b88125b57066be5b7bbf3a3d14afdcf2870a77fa006c48ad78d3ad0dd9719`.
Its previous-ROM savestate is deliberately not reused. Fresh normal-input setup
creates the matching checkpoint before the new office interaction continues.
Native jar pickup/renaming is NOT_VERIFIED at this source checkpoint.

Private reports, commands, source/build linkage and interrupted-run evidence:
`/home/chad/SAME-private-evidence/office-progression-20261114/`.
No proprietary source payloads, packages, ROMs or captures enter Git.

## Source-class defaults correction

A fresh-ROM office continuation exposed the remaining omission: the cooker
emitted initial object states and owners but omitted original DOBJ class masks.
The full source contains 1,395 masks, 994 nonzero. Loading those into 512 mutable
C16 slots would also exceed capacity; truncating them is not correct.

The cooker now retains the complete checked-by-hash class metadata. Native ROM
lookup stores dense immutable u32 defaults (5,580 bytes for this source), while
existing C16 WRAM holds only bounded mutations. Queries fall back to source
only when no override is present. An explicit zero override hides nonzero
source classes; restoring the source mask reclaims the mutable record. Actual
mutation exhaustion still fails explicitly. No additional WRAM or code-cache
storage is used. All-source manifests missing class metadata are rejected and
must be recooked. Legacy class-less synthetic inputs retain zero defaults.

Host and native membership, set/clear, pickup, hit testing, and actor mask
policy use effective classes. Host save/load preserves meaningful zero
mutations. The source package executable bodies and room payloads are not
modified to obtain these semantics.

The extended copyright-free native control contains 1,024 source masks
(1,000 nonzero), overlapping objects, and queries/mutations of object900 beyond
the former proposed sparse seeding bound. It passes at frame368 with
`[0,8,9,8,0x1357,8,0,7]`, error0, zero remaining overrides, and no BRK or
executable-WRAM mirror writes. ROM:
`87430628c58d0f2d4612c5d338e3c896643bf8e6a991ac4b6ffb286d0eee187f`.
Native execution took15.437 seconds; the supervisor cleaned up its owned tree.

Two earlier controls are preserved as failures: an assembler width declaration
encoded a word comparison as a byte, and `BankedLabel+2` lost the ROM bank.
Both are corrected. The native observer now also verifies the actual word
comparison and both banked load operands before launching. Source instruction
model tests alone did not establish correct assembler output.

This qualifies the generic class correction, not the authentic jar action.
Fresh source-default ROM setup and office continuation remain in progress;
previous-ROM states will not be reused. Evidence is under the private
`office-progression-20261114/class-defaults` directory.

## Qualification of earlier coat evidence

Fresh original startup and taxi/map/office entry on ROM `33e69ca3` now preserve
all source classes. The completed office capture matches source/PPU output,
error0, with newspaper1/1. Coat25 remains owner15/state0/class32. Its source
untouchable bit was never cleared during this continuation. The old coat
pickup on a ROM missing initial classes therefore does **not** establish a
source-faithful reachable interaction. Those captures remain preserved as
historical observations, not promoted to acceptance under the corrected source
contract. No class or ownership is injected to reproduce that result.

The next original action is Open21, whose authored script explicitly clears
jar22's untouchable bit before Pickup22. The updated isolated host body oracle
preserves classes2/16 on exposure and2/16/32 after pickup, including an explicit
zero/source-default distinction. The fresh native jar continuation is pending.

At commit `f74a037`, local tests run1,751 with12 skips; validation and the
47-region audit pass. Both hosted jobs pass in
[run43625823355](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43625823355).
The prior run's only remaining failure was a trailing blank line, corrected
additively. Hosted assembly is not Nexen execution.

## Original rename failure and correction

On source-default ROM `33e69ca3`, normal Open21 opens the ice box and exposes
jar22. Normal Pickup22 then transfers owner/state to1/1 and emits the original
mayonnaise description. The native CPU subsequently stops; error0 alone is
not acceptance. The preserved first-fault observation has VM opcode54 and
PC275, the first inline-byte store in original SetObjectName atPC271.

The dynamic-residency name writer called a bank-local helper with JSR, but
that helper returned RTL. Correcting it to RTS retains the caller's bank and
return frame. Focused native testing then exposed a separate one-byte excess
in cached name length. The bounded writer now counts retained encoded bytes
including the terminator, saturates at32, and overwrites only the final byte
when consuming longer source names. Control parameters containing zero remain
encoded bytes, not premature string terminators. Names outside the1024-entry
native cache are consumed without aliasing a neighboring record.

Copyright-free native ROM
`3c0bdfe58f2f475933e055c818bfe1c92315560e77f7c408a5224fd15a5d61ce`
reaches its sentinel atframe376, error0, with class/hit results unchanged and
exact cached-name lengths17,32,1,31,32. No BRK or executable-WRAM alias write
is observed. The supervisor completes cleanup. Source-instruction tests cover
all1024-cache boundary cases and adjacent guard bytes; actual native assembly
checks the RTS opcode using the bank derived from the interpreter's JSL,
because Poppy's text symbol map reports only label offsets.

The authentic corrected-ROM continuation is still pending. No prior-ROM
savestate is reused. Its package remains original source, without replacement
scripts. Private failure and proof records are in `class-defaults/jar-after-open`,
`trace-jar-first-brk`, and `native-name-length` under the evidence root above.

The dialogue observer also now distinguishes segment replacement/expiry from a
still-pending capture. Recorded second-segment candidates are not pixel proof
of the missed first segment. A successor must receive its own comparison;
no ACK is sent on behalf of an expired segment. The first BRK hook was
asynchronous; the installed MCP server does not provide the separately
documented exact-execution-stop tool. Neither record is described as an exact
callee-return capture. No camera correction was made from the timeout.

## Corrected-ROM continuous acceptance

Native runtime `2bdea03b8f3c810fb327c0350fea93c72f9f20c6` completes one
uninterrupted exact-ROM continuation, frames21496–28661. Its legitimate Barnett
checkpoint already has door34 opened by normal controller input in setup.
There is one initial restoration and none during the accepted segment; this
is not cold-start acceptance or a splice of the earlier focused sessions.

| Normal player action | Original executable | Observed result |
| --- | --- | --- |
| Walk through door34 | room2 object34, verb10, PC50, canonical232 | Original exit/entry lifecycle reaches office room1 |
| Open ice box21 | room1 object21, verb3, PC76, canonical168 | Door28 state0→1, bit213 false→true, jar becomes touchable |
| Pick up jar22 | room1 object22, verb11, PC151, canonical169 | Owner15→1, state0→1, encoded name becomes `jar of mayonnaise` |
| Open/select inventory, close it | Normal controller menu | Original renamed entry visibly presented; 290 contrasting text pixels |
| Walk again | Original sentence/input scripts | Ego(199,134), room1 RUNNING, input ready, error0 |

The final newspaper remains owner/state1/1. Coat25 stays owner15/state0; no
untouchable class is bypassed. The original-body host oracle predicts the
same door, jar, bit213, name and preserved newspaper results. It covers both
values of the original description predicates, but is isolated body execution,
not a host end-to-end playthrough. Captured activations include canonical232
atPC50/64/115,168 atPC76/81/255, and169 atPC151/293.

Five completed captures (office entry, original ice-box continuation text,
opened ice box, jar inventory, and continued walking) have zero complete
source/INDEX8/decoded-PPU differences and matching CGRAM. The readable original
response is “Guess I should have cleaned it out.” with568 contrasting pixels.
The first short ice-box segment and the mayonnaise description expired before
completed capture and remain **NOT_VERIFIED** visually. The inventory's compact
13-character label is `jar of mayonn`; the full underlying original name is
preserved. The final walking image uses the actual captured pose, not an
invented standing animation.

The supervised session completes in557.513 seconds under the unchanged600-second
process-tree deadline, with normal exit and no owned survivors. The7165 emulated
frames include the whole route, authored movement, checked resources, presentation
and observational pacing; this is not a device-throughput or60Hz claim.

### Exact artifacts

| Artifact | SHA-256 |
| --- | --- |
| ROM | `c4b2b3b36fa730a85afd03da4114d0821c00dbf4454d4091ac921ad0f2511c76` |
| Map | `93ddd7ad88c4f9aac57a20920b05cf322354467577e18bb5a39c0081213800d4` |
| SAMEPKG | `b6afddbf486ee26f85bb444cb03060d9606864138e3d1b3ed282657f77a09111` |
| Build identity | `b62dad3dbfd0da1df60d8f44a548d38a2613c94b2eb3e0a071ca473d887a9212` |

All160 tracked runtime/host-engine/compiler files match the isolated assembled
source snapshot byte-for-byte. Later evidence documentation does not change
ROM bytes or retroactively alter build identity. All2203 canonical ProgramUnits
and the original deterministic package remain intact. No replacement story
scripts, gameplay writes, commercial payload commits or new title-specific
production hooks were used.

Persistent private evidence is in `class-defaults/name-fixed/continuous-final`
under the root above: complete action journal, source/PPU comparisons, original
controller command, captures, state/ROM identities and supervisor cleanup.
`name-fixed/acceptance.json` indexes their hashes and source linkage.

### Preserved observer failures

The first continuous attempt stopped before pickup: coarse cursor release
landed atx253, outside the jar's source rectangle256–271. The corrected target
uses its interior; this was a replay placement error, not an engine defect.
A focused pickup subsequently proved the native rename and continued walking,
but its menu predicate captured an older blank HUD while text state2 was still
pending. Its original report is preserved and explicitly qualified by
`post-capture-qualification.json`; it is not readable-inventory acceptance.
The final observer requires the expected encoded menu through the existing
text-composition/commit predicate. The old capture fails that predicate offline.
Actual final images were inspected after emulator cleanup. Source comparisons
run from immutable captures after the owned session closes, still within the
same600-second supervisor. No timeout was extended.

### Validation and remaining scope

Local runtime tests:1753 run,1741 passed,12 skipped. `make validate`,47-region
WRAM/BW-RAM audit, pinned Poppy assembly and4MiB ROM audit pass. Both required
hosted jobs pass on runtime2bdea03 in
[run43629978507](https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43629978507).
The final documentation head receives its own checks. Hosted assembly is not
Nexen execution. PR18 remains draft and additive on PR17, with no automatic merge.

This qualifies the requested bounded Milestone E gameplay scope using a
source-faithful persistent action. It does not qualify the old coat reachability,
all office puzzles, later dynamic dependencies, full sound realization, portable
native saves, physical hardware or whole-game completion. Full object refresh
and presentation remain slow. Whole-game readiness remains NOT_READY; that label
is a capability boundary, not evidence that the completed bounded route failed.
