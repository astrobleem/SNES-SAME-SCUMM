# Multi-actor scene transaction — native checkpoint

The opt-in `SAME_SCUMM_ACTOR_SCENE=1` path enumerates the 32 C14 actors,
keeps per-actor pose/animation/palette identity, and composes visible actors in
source Y order (actor ID breaks ties). It uses the existing checked source-cel
compositor, shared actor scratch, INDEX8 surface and NMI presentation service.

One scene transaction restores the old journal, captures every new actor's
underlay **before drawing any actor**, then draws each complete checked pose in
painter order. Only the completed scene is published. This avoids restoring
one actor's footprint over another actor. A full 32-bit presentation fence
separates candidate scene state from displayed state.

The SA-1 carrier optionally reserves S-CPU-accessed I-RAM `$003100..$0037FF`
for metadata. The carrier explicitly grants S-CPU write access to those pages;
the SA-1 CPU remains reset, and the first mailbox page remains untouched.
The allocation and feature requirements are mechanically audited. There is
no extra pixel buffer or executable-cache lease.

## Native evidence

The copyright-free original SCUMM fixture has two different costumes, scales
231/231 and 128/200, overlapping coverage, swapped Y order, facing changes,
two animation steps and a moved actor. Four completed captures match the
independent source compositor, complete INDEX8 surface, decoded PPU and CGRAM
with **zero differences**. Native execution completed at frame1976 in
205.009 wall-clock seconds. The supervisor reports normal exit and no owned
survivors. This is synthetic renderer acceptance, not Barnett gameplay.

Private evidence: `milestone-d-scene-20261113/native-two-actors-idle-placement`.
ROM SHA-256: `2939f7fc19122026532ddd8b7afd3affd4a032a5923fed47bb20c1d3d22f92f3`
Map SHA-256: `0a34f626db70da86f333f8db7a0d21e900e4056ce99d526754e10e8ea39a6daa`
Package SHA-256: `4f81139c76b5e8a9b73bddd280b92cadcc19397aaa824fe7d9f2483f268a2605`
Build identity SHA-256: `0565159bfa3428695c43eb01dead7a6726ec17c58f119c241971f38d888f131c`

That ROM was built from a private source snapshot before this public commit;
its build identity records that exact snapshot. Subsequent mask work is not
covered by these four images. Original foreground masks, authentic Barnett
full-scene rendering and destination interaction remain NOT_VERIFIED.

Adjacent fixes permit an empty trailing SC5LIVE name table whose offset equals
the checked record length, and accept ordinary idle `putActor` position changes
with the no-walk-destination sentinel. The publisher runs after movement's
complete scheduler update; the sentinel does not denote a partial actor.

## Checked foreground masks

SC5MASK stores source z-plane/strip identities and independently checked blocks
of at most256 source rows. Blocks use zero/raw/count-value representation;
opaque/background pixels are never modified to bake in masks. The original
walkbox mask directory accompanies source dimensions and plane identities.
ROM stores bounds, source identities and CRC descriptors, not mask pixels.

For each actor, the scene captures forceClip, ignoreBoxes, class20 and its
source-foot box selection with the pose key. The existing room geometry query
supplies the reverse-order containing box; a nonzero nearest-box adjustment
is not containment. ForceClip takes priority and is clamped to existing planes.
Mask lookup uses world coordinates after per-cel scaling, before screen pixels
are written. Source slot zero stays transparent; opaque output color zero
remains subject to the same mask and palette rules as other opaque colors.

The provider remains serialized. Mask blocks borrow ACTOR-owned pending
scratch, validate immutable room/costume tickets and CRC, then decode coverage
into only the measured free tail after the **completed** underlay journal.
Each actor releases that temporary coverage before the next actor reuses it.
Insufficient journal/coverage space returns the existing explicit resource
error; this is not a claim that every whole-game actor combination fits.
Room and costume changes drain an outstanding read before scratch reuse.

The masked public fixture passed four complete source/INDEX8/PPU/CGRAM
comparisons, including two independent planes, overlapping actors, two
animation steps, facing changes and old-position restoration. Native frame2159,
227.672sec, normal supervisor exit, no surviving owned processes. Private
record: `milestone-d-scene-20261113/native-two-actors-mask-bank-fixed`.

Native masked fixture identities:

- .sfc: `f754a0755e792fec4ff1f277b575558f8e1094bb4b0fc725a41838b39ef991bc`
- .map: `df047196630864256a70a9206f163e9dc53d98805b2c75614c85f9a2209f2709`
- .msu: `ad225e7b366b20e48cb712da7c9bdc828dc8aa2f1ba1dc0aa534ea6a0f867d3c`
- .build_identity.json: `758e8c94aae604c1ddfc8e07083e7d6fb65ae82d06748271fd109f8c035c7bac`

The fixture run precedes follow-up scene-key sampling corrections (preserving
the published primary pose and snapshotting class/box policy). The fresh
commercial build records those later source bytes separately; its gameplay
acceptance is not inferred from the fixture.

Full-source preflight:72 rooms contain original masks,7,628 checked blocks,
162,912 mask-record bytes. Room2's record is2,525 bytes and retains both source
planes plus21 walkbox mask selectors. Three independent package builds match
SHA-256 `6d2b070dc8f08a644bafd81aa7b917b925963cc198f6ba2440f416f050117706`
(14,646,760 bytes). All commercial payloads remain private.

Current local suite:1,668 run,12 skipped,OK; make validate and44-region ownership
audit PASS. The published pre-mask checkpoint0536e4b has both hosted checks green
in run43552305237. Hosted CI does not execute Nexen. Later source changes need
their own hosted check results.

## Integration boundaries found after the fixture

The first fresh authentic build reached room10 with error16 when visible
actor11 requested costume209, absent from the earlier five-costume build.
The local source-resource configuration now includes that original costume;
no actor is hidden and no engine branch recognizes its number. The corrected
build reaches the authored room10 interface with error0. This is not yet
Barnett acceptance.

A subsequent controller observation tried to send input before the original
room-entry activation finished its matrixOps work. Its90-frame edge bound
expired while the engine remained busy; the supervisor reported validator
failure, no signal/deadline, and complete cleanup. A matching-ROM checkpoint
permits a targeted continuation that waits for entry retirement. No timeout
increase or cold replay is needed for this observer correction.

Cancellation now distinguishes an incomplete scene from a complete image
already handed to NMI. The latter retains its underlay until normal retirement
instead of trying to write a DMA-locked surface. Source-execution regressions
cover both phases. They are host evidence, not an extra native capture.
Original byte-valued walkbox mask selectors remain intact for the host/native
clamp rule. Advancing past source block255 cannot wrap through16-bit XBA.

The completed room10 verb/menu captures on ROM
`d16154335b375bc6fdbbd7442b4ebdacb441d6ef07146a1a358b61c9d7d69574`
match the complete source scene and decoded PPU, including source font HUD.
Their pose metadata is captured, not inferred. Subsequent input exposes
actor12/costume208, another missing configured resource; that session is not
pickup or Barnett acceptance. The first-error record is preserved privately.

Compiler resource dependency analysis still read legacy ActorOps `selectors`
after normalization had changed to `commands`. Room reports, whole-game graph
edges and costume census now share the normalized resource-operand adapter.
Focused actual-bytecode tests preserve both direct costume/sound references
and variable-indirect uncertainty. No runtime semantics are replaced.

The bounded rooms2/10/75 resource preflight supplies their static costume IDs;
explicit startup/dynamic seeds remain separate. Dynamic edges are not claimed
resolved. Eleven source costumes produce1,097 poses. Combined pose/chunk/
palette metadata no longer fits one ROM bank, so the cooker retains the old
layout when it fits and otherwise places chunk/palette tables in an independent
bank after cel metadata. Existing long-addressed accessors need no change.
SC5ACT layout, checked bytes and logical indices remain unchanged; oversized
individual tables still fail explicitly. Generated bank reservations and ROM
audit cover the actual emitted placement.

Fresh full build ROM
`e9042479207e2dfd80e36941625227d78278dad063e85db5e04e6de129e9bae9`
passes pinned assembly and ROM audit. All2,203 canonical IDs, semantic names,
body hashes, dispatch and source provenance compare equal against the prior
full build. Its cold bounded control is a new resource configuration; no old
checkpoint is loaded into it. Destination acceptance is still pending.

### Overlay successor publication fence

The fresh eleven-costume authentic build accepted original newspaper pickup
(owner/state 1/1), then exposed a scene completion defect while inventory was
open. The captured actor-scene ticket was generation 46; text/cursor had
already completed generation 153. Equality with `NEXT_GENERATION` prevented
scene retirement even though the scene's complete image had been published.
This was an engine fence defect, not evidence of an emulator deadlock.

The scene now requires the existing unlocked, fully committed surface fence,
the same room epoch, and a nonnegative full 32-bit serial delta from its ticket.
Later ordered overlay publications can acknowledge the earlier scene; older,
half-range-ambiguous, or replaced-room generations cannot. Focused production
source execution covers exact/successor acknowledgements, low-word carry,
32-bit rollover, stale generations and room replacement. This host evidence
is separate from native acceptance of the changed runtime.

Private failing evidence: `milestone-d-scene-20261113/cold-room-costume-closure`.
ROM SHA-256: `e9042479207e2dfd80e36941625227d78278dad063e85db5e04e6de129e9bae9`.
The supervisor recorded validator failure after 568.281 seconds, no deadline
or external signal, complete cleanup and no survivors. The captured state is
preserved; it must not be restored into the corrected ROM.

### Checked-mask native rejection

`native-mask-crc-cleanup-fence` changes one six-byte RLE mask block in an
isolated copyright-free package, retaining the original descriptor CRC.
Nexen observes provider CRC error 6 and SCUMM resource error 16 at frame 718.
The synchronous underlay rollback is still executing at that frame boundary;
by frame 734 the scene phase and composition fence are zero. Completed scene
count remains zero. No corrupt mask scene is published. The supervisor exits
normally after 53.292 seconds with complete cleanup and no surviving children.
This is a rejection control, not a successful graphics capture.

The preceding `native-mask-crc-public` observer incorrectly required rollback
to have completed at the first error-byte observation. Its failed assertion is
preserved. The corrected observer allows at most 32 frames for actual cleanup
and continues to reject any scene publication throughout that interval.

Fault package SHA-256:
`14c4c951cc2fefe06202686790008385b7f473135511db56217235b74548d119`.
The private fault manifest retains the original package hash, exact block
identity, package offset, size and expected CRC. Original package is intact.

### Room handoff owns the whole scene, not just scratch

The corrected-fence ROM `6d9fc5d5a8e19fd342fab8b2cb29d1a8ecf88c1ed9dd57efe383d78f0584d3c2`
passed original room-10 menu, pickup menu, inventory and taxi-dialogue complete
source/INDEX8/PPU/CGRAM comparisons. Inventory includes source-scaled Indy and
an authored actor whose 74 covered pixels are all hidden by plane 2. Newspaper
owner/state is 1/1. These captures are not Barnett acceptance.

The subsequent original taxi transition raised resource error16. Its preserved
write-hook continuation observes error writes at frame10852; the returned CPU
snapshot is later, not the exact offending instruction. Incoming active-room
installation was running while the old multi-actor scene could start again.
The scratch-only cancellation check missed scene ownership between transfers.

Incoming phases4/5 now prohibit scene snapshots and composition. The checked
room loader retires a non-idle scene even when its transfer scratch is NONE.
After outgoing EXCD, installation also cancels any newer outgoing scene before
revoking active metadata validity. Existing provider cancellation still drains
owned writes before scratch reuse. No new buffer or scheduler is introduced.
Focused tests execute both lifecycle admission guards; installation ordering
is checked, and an original-script copyright-free fixture adds room1→2→1
with two scaled/masked actors. Native acceptance of this correction is pending.

The first transition-fixture cook accidentally omitted `--executable` and
produced registration-only records. It timed out before stage1 with no SCUMM
error; it is not an actor/transition pass. The executable manifest is checked
before the corrected build. Failed evidence is retained, without a watchdog
increase. The authentic runtime build remains separate.

### Native masked room transition and revisit accepted

`native-mask-transitions-executable` passes six complete images: initial
scaled overlap, two animation steps, moved/restored actors, room2, and room1
revisit. Source scripts perform both room requests, with a yielded animated
pose before each request. Native room identities are 1→2→1; completed scene
generations are 1–6. Every capture has zero source/INDEX8, decoded PPU, and
source/CGRAM differences. Frame3989 finishes the control; 369.559 seconds,
normal exit, cleanup complete, no surviving owned processes. The two fixture
rooms deliberately contain identical original test artwork; this proves
resource identity/lifecycle/revisit handling, not different-room artwork.

| Artifact | SHA-256 |
|---|---|
| ROM | `e448fa318851623190fd2f10c153dd64de1b36a3c4535865a696eb523a62b909` |
| Map | `112e800167172ad750649724f34ee2e2e094aa0de7bd7c3d77473860be836fcd` |
| SAMEPKG | `4d2c9d1922761b93013a1b2e6a4b8780e5853ce4343c7411447c4d9685f96787` |
| Build identity | `f4d12ffaebce44fc4d681b1774fcdbe59efd4967828412b50a4cb3cd823aaf67` |

Runtime source matches `cfcc07e`; build snapshot is separately recorded.
Full local suite: 1,681 run, 12 skipped, OK. Validation and 44-region ownership
audit pass. Authentic Barnett acceptance remains separate and pending.


## Shared scene/text damage ownership

The fresh `cold-room-owner` authentic run exposed a concrete publication bug,
not an emulator timeout: at generation21 the queued INDEX8 image contained
actor11's clipped costume, but the committed PPU lacked1,994 pixels at
x225..255/y39..166. CGRAM matched. The shared damage rectangle had been
replaced by the subtitle rectangle during asynchronous actor composition.
ROM `03e2b677a64c53eb40150519c90b8fcc8e5ed7066d17d1276c244959b945a24a`;
the failed capture and complete supervisor cleanup remain in private evidence.

The indexed overlay now respects a neutral composition-ownership word at
text-state offset `$6C` inside its existing128-byte carrier allocation. Scene
begin claims it; successful PRESENT submission or cancellation releases it.
Text admission, pending composition and hide all consult that fence before
changing shared damage or pixels. Queued original text retains its immutable
request. Surface writability remains available to the owning compositor;
no new framebuffer, cache allocation, DMA budget or script timing change.

`test_scene_text_ownership` executes the production fence and checks writable,
backend-busy and owned states, all three text entry paths, and scene lifetime
release. These are host source-execution tests, not native acceptance. The
corrected authentic build is recorded separately; its native result is pending.
