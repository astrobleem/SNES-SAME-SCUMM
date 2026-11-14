# Office inventory continuation

This work continues from Milestone E in PR17. The accepted office/coat
checkpoint is preserved; it is not the whole-game completion boundary.
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
