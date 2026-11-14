# Checked source-cel actor scaling

Milestone D remains in progress. The source-neutral native scaling control
passes; authenticated destination gameplay is not yet accepted.

## Representation and compositor

`SAME_SCUMM_ACTOR_CELS=1` retains source cels in the existing SC5ACT collection.
The source decoder, SAMEPKG envelope, checked provider, INDEX8 surface, underlay
journal and Mode-3 publication service are unchanged. Legacy v2 flattened
poses remain available. The new path currently requires camera-viewport
projection; aspect-fit builds fail preflight rather than silently projecting
scaled cels incorrectly.

The v3 pose record retains the existing 24-byte width. Byte19 identifies cel
format and source drawing direction; bytes20..23 identify its cel range.
Each32-byte cel descriptor contains source width/height, signed relative and
limb-movement offsets, and an ordered span range. Eight-byte span records hold
source x/y and logical opaque-slot offset/length. Gaps represent transparent
source slot0. Individual cels and their painter order are never flattened.
The last word of each16-byte checked chunk descriptor is its logical pose
byte offset. All offsets/counts/geometry and complete span/chunk coverage are
validated before serialization and checked again by native admission.

Opaque source slots are checked before palette mapping. A nonzero source slot
mapping to screen color0 remains opaque. Native scaling applies the original
256-entry phase table per cel, including signed foot-relative origins,
cumulative limb movement, independent X/Y phases, mirror direction, horizontal
collapsed-column overwrite order and vertical row selection. It does not resize
an already flattened bitmap.

Transfers remain at most2048bytes with independent CRCs. A complete-pose underlay
is captured before any chunk draws. The surface transaction stays private
between chunks; the cursor cannot publish or reset its damage, and camera
foreground service resumes the actor transaction. Only the completed pose is
presented. Simulation continues without rewriting the outstanding pose key.
Room cancellation restores the captured background and drains provider ownership.

Additional state is72bytes at `$7E22B4..$7E22FB`, initialized at cold boot.
No new pixel buffer, executable-cache lease or DMA budget. Active SC5LIVE's
unused tail remains the existing bounded underlay allocation; it is not free
BW-RAM. Pose payload offsets remainu16 (maximum65535opaque source bytes),
cel dimensions1..512, with explicit capacity rejection. Multi-actor composition
and z-mask consumption have not been qualified by this single-actor control.

## Native evidence

Private root:
`/home/chad/SAME-private-evidence/milestone-d-actor-scaling-20261113`

`native-scaled-cels-3/observations/report.json` records actual supervised Nexen
execution,287.248seconds under a600second process-tree watchdog. No owned
process remained afterward. The original copyright-free SCUMM fixture supplies
two overlapping cels, transparent holes, opaque palette0 and2909source bytes
split across two checked chunks. Its ordinary interpreter script controls the
stages; observer writes acknowledge only the fixture's local handshake.

All nine completed captures have zero source/INDEX8, decoded VRAM/PPU, and
CGRAM differences:255/255,231/231,128/200, mirrored231/231, clipped255/255,
empty frame, two animation steps and a moved231/231pose. Complete-background
comparison includes restoration of the old actor footprint. No intermediate
pose publication was observed; the observer rejects publication while the
checked multi-chunk transaction is incomplete.

| Artifact | SHA-256 |
|---|---|
| ROM | `0f618437cb0436c193cc0cc4a4fd80988f40b7f85aff0b233221758abfbd2b16` |
| Map | `fc06eeb6a1a67139479e64eb86163df9332f8a3957351e970cf2234437fde58a` |
| Package | `758b5fa2eb816aa3dc70f40468e459c9375a6023c99fd367c375b7b75974cac6` |
| Build identity | `69e70df7a7c7ccd5c12aa32c6b3b0b1bf50ad0a755b147f3feb3bc7aa279e932` |

This isolated source snapshot predates the subsequent unchanged cache-service
ROM-bank relocation, hidden-actor scale-key correction, and stricter cooker
preflight. Do not relabel it as native evidence for a later ROM. The full-source
build exposed a162-byte overflow in the controller/resolver/cache bank; the
complete unchanged cache service now follows live-room code in its existing
bank84. The pinned assembler and4MiB ROM audit pass with that layout.

Earlier controls are preserved as failures. Run1 exposed uninitialized new
cold state and a misplaced committed-scale key. Run2 obtained final255/231
matches but incorrectly published between chunks through the cursor pass;
its asymmetric final PPU also differed200pixels. Those are NOT acceptance.

The first new-ROM authentic startup stopped at a room hold before the taxi,
error0. A matching-ROM read-only continuation confirms an outstanding video
publication. Source/cache-key inspection found hidden poses committing an old
scale ticket and requesting redundant publications. The hidden path now
commits its own desired scale without fetching or drawing stale costume data.
A new-ROM regression reached the original room10 interface, but its subsequent
controller edge was not sampled within the unchanged90-frame deadline. This
exposed excessive synchronous cel composition work, not a reason to extend the
input timeout.

## Composition cost correction

The compositor now acquires surface write ownership once per synchronous turn,
checks each pixel against the accepted chunk length and clipped coordinates,
and calls the existing target-neutral indexed pixel leaf. It no longer invokes
the whole opaque-run ownership/damage transaction for each individual pixel.
Capture uses the exact monotonic first/last destination of each opaque span.
Vertical phases advance from the preceding source row instead of recounting
from the cel origin for every span. Drawing skips spans owned entirely by other
checked chunks; canonical validation and underlay capture still cover all cels.

`native-scaled-cels-optimized/observations/report.json` repeats all nine actual
native comparisons with zero differences, including opaque color0 and complete
old-position restoration. It finished at emulated frame2499 versus3069 for the
earlier control (includes boot, presentation and observer acknowledgements;
not a raw CPU benchmark),224.764seconds with owned-process cleanup. The package
hash is unchanged. ROM `ee05c763c67ffb5628ab87c2174af0237840e970621df5acf6024f883dd4b51d`,
map `733a0b2f5a530c870bbd00d837273547ae5d5ff31dd076bd313748a8139c9c06`,
build identity `eac5eedca0758d9a0571a9cb1a1393b9cc772fa1e7ddaf7bbcb9218ee722a9c6`.
No new memory allocation or video budget change. Authentic controller/travel
acceptance must be reported separately from these synthetic captures.

## Validation boundaries

Host tests execute the production phase/composition instructions against the
independent room compositor, including1000origin cases,1000lossless pose
roundtrips,80random complete rasters, source-decoder fixtures and malformed
metadata. They are host evidence, distinct from the native captures above.
The synthetic fixture checks animation, clipping, empty poses and multi-chunk
publication. Existing v2 tests remain enabled. The44-region ownership audit,
pinned Poppy and ROM audits pass; full-suite/hosted results are recorded with
publication, not inferred from these focused controls.

No new production FATE hooks. No commercial payloads or captures in Git.
Barnett College rendering, additional actors, required occlusion, resumed
control and destination interaction remain NOT_VERIFIED. Whole-game NOT_READY.

## Camera exposure and whole-pose publication

The first authentic scaled trip reaches room2, lifecycle RUNNING, error0,
newspaper owner/state1/1. Authored entry movement changes Indy from231/231 to
50/50 at(435,110). The matching-ROM `college-presentation` capture is not a
whole-scene pass: source comparison found41 missing Indy pixels. His pose had
been composed completely outside the incoming camera. Retained scrolling
shifted an empty journal, while the unchanged actor key suppressed composition
when the camera finally revealed him.

The compositor now retains signed, unclipped horizontal coverage (four bytes).
A committed camera transform invalidates the actor key only when previously
clipped source coverage becomes visible. Fully retained poses keep their path.
The source-neutral camera fixture changes only camera position after its initial
actor setup, including partial exposure, complete exposure and reversals.

That regression also exposed a real ownership gap: between checked pose chunks,
POSE_STATE is idle while CEL_VALID still owns incomplete INDEX8 pixels. Camera
foreground completion formerly admitted a room-strip request in this gap.
The same pose generation4 was captured with CEL_VALID1 at frames809 and825,
while presentation advanced8→9 and room I/O claimed scratch. This is preserved
in `native-camera-exposure`; it is a failed native control, not an observer pass.
Foreground completion now checks the whole-pose owner before admitting camera
work. The focused source-instruction regression checks both incomplete and
released ownership, with otherwise idle resource state.

`native-camera-exposure-fenced` completed seven captures in260.475seconds,
with zero source/INDEX8, VRAM/PPU and CGRAM differences, no intermediate pose
publication observed, and normal supervised cleanup. ROM
`69e16d93bfc4dd4e72d3046258d5729834221bf01b8e7d770d8a697d092cedfe`,
map `47fa2c23cf218a14a05eeabd2a15431e2b18b2a646057152bb37f2935cf156fa`,
package `d3038f0853201ef322dceaee981ddd10ba0c2f55515f7f0d6a42ea46a56139a1`,
build identity `1e01506f88c2c8db1382d7327f47bf7dbafdb92f7d6d00258a9ccd7a4fe39b69`.

This does not qualify Barnett's complete scene. Its captured actor table also
contains visible actor5/costume78. The source compositor requires another178
visible pixels and masks four more with the original room z-plane (secondary
facing/frame were source-inferred in that offline comparison, not native pose
captures). Native presentation still has a single actor binding, one combined
underlay journal, and no checked z-mask consumer. Do not hide that actor,
substitute Indy's costume, or count the background-only image as acceptance.

The corrected full-source image assembles and passes the ROM audit:
ROM `2cd18ce9781f10687d26f157560904eda8c1bcd6ac549f5e811c9672a24961a7`,
build identity `65c4fc4251f0a1f0cc2968037aa1a3c459f81fcf36f7ef66031b62073bcb1e9e`.
Its new cold control `cold-scaled-exposure` was interrupted after17.029seconds
(exit130, interrupted=true, timeout=false), last captured room68/frame672/error0.
The signal origin was NOT_CAPTURED. Cleanup completed. This is not an engine
failure, a valid destination checkpoint, or authentic acceptance of the fix;
no unchanged retry was performed. Older checkpoints belong to different ROMs.

Latest local validation:1656 tests run,12 skipped,OK (1644 executed);31 focused
scaling/camera tests; make validate;44-region memory audit; pinned Poppy full
and synthetic assemblies and4MiB ROM audits. Hosted results are commit-bound.
