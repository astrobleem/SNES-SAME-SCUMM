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
preserving source record order, caller X/Y and width state. Missing C16 records
mean no classes. Ownership alone is not a touchability predicate. No name,
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
