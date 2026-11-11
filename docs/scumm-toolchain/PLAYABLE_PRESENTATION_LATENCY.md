# Playable presentation latency — work in progress

Milestone C starts at `41305d9d32cf02907dc887d3f76e449c01d57389`.
This is a performance checkpoint, not camera, complete UI, or persistent-action
acceptance. The separate progression recovery worktree is untouched.

## Verified first tranche

The Mode-3 encoder gathers each indexed pixel once and builds eight plane
bytes with shifts. Its eight temporary bytes reuse backend-owned rectangle
scratch after candidate construction. It preserves DBR and the stack. Empty
candidate/available bitset bytes are skipped without dropping individual dirty
bits or in-flight DMA ownership. The generated frame hook calls the existing
bounded four-step service; each step retains its four-tile conversion limit.
The NMI DMA budget and publication protocol are unchanged.

The source-instruction tests cover every palette value, planar bit order,
random tiles, dirty prior scratch, register/stack preservation, bitset table
edges, sparse patterns, and pending-minus-in-flight selection. These tests are
host evidence, not emulator execution.

Copyright-free native control, 2026-11-11:

- ROM SHA-256: `453d3e25b0dcc64f47e48dec22570595316479c763354a617dcdd2746a306844`.
- Identity SHA-256: `441c0b28d20b2cab37b379338312d0fe8e9f3384684c4c4bc703492944646953`.
- Local report: `/tmp/astra-mode3-sparse-full-raster-20261111/observations/report.json`.
- Six generations passed exact reference images, indexed/VRAM/CGRAM checks,
  palette-first ordering, sparse batches, and rejection while locked.
- 651 emulator frames; 63.072 seconds supervised wall time; zero guest writes.
- 43 DMA descriptors committed, zero pending/rejected DMA; SA-1 remained reset.
- Maximum observed conversion in one emulator frame: four tiles. The service
  upper bound is four steps of four tiles per logical engine turn.

The earlier control captured the first raster during forced-blank removal:
only its first sixteen rows were black. It remains a failed capture. The
observer now requires a full displayed raster after first unblank; no pixels
are masked and the exact comparison remains mandatory.

## Authentic controlled after-measurement

The row-gather/four-step revision, **before the empty-byte scan optimization**,
executed the same original object action as Milestone B through controller
input. It used the complete source package, no guest gameplay writes, and
matching ROM/state identities. Original room, costume, cursor and source fonts
matched INDEX8 and PPU output with zero differing pixels.

- ROM: `1f8c2f79b907facc9bb90d303f3ded3501e4906194b1447abeb4c1585b1e5c83`.
- Package: `5f4dfa58b58bbad5c654924380b8277929a6b2b67012a2042c2f3b4645162a16`.
- Journal: `/tmp/astra-mode3-gather-input-ready-action-20261111/observations/action.json`.
- Input frame 15856; matching queued response 16060; PPU capture 16153.
- Response latency: **297 frames**, previously **513**. This is still too slow.
- Original response first observed active at 15978; its surface generation was
  queued at 16060 and presented at 16153. These are sampled boundaries, not
  claims about exact instruction execution times.

The trace exposes an unchanged caption redraw before the response and two
128-tile text-strip conversions. Bounded glyph damage and avoiding the
unchanged submission caption are the next corrections; they are not covered
by this native result.

A subsequent walking measurement reached the original semantic target but
stopped at its 170-second observer deadline while composition was pending.
It is **NOT_VERIFIED**, not an improved walking result. Its journal and
matching failure checkpoint remain under
`/tmp/astra-mode3-gather-walk-20261111/observations/`.

## Integration corrections and observer boundaries

Room-request reset now reloads a 16-bit zero before clearing its 16-bit chunk
cursor. The captured old failure was `$0100`, from the accumulator's hidden
high byte. A regression covers all 256 hidden-byte values.

The backend-only fixture formerly linked an unused SCUMM interpreter with
unlinked room-service dependencies. The generated engine selection now owns
whether that interpreter is linked. SCUMM configurations retain it.

Faster rendering exposed two observer assumptions: an authored initialization
loop can outlast a logical input boundary, and a room image can be visible
before C19 releases input. The controlled action waits for real input
ownership, without changing authored scripts or replaying the seven-action
route. No historical state was loaded into a different ROM.

## Remaining gates

Walking responsiveness, bounded text damage, the authentic camera viewport,
visible verbs/inventory, and a continuous persistent original-game action
remain pending. Full-game readiness remains **NOT_READY**. Native evidence is
Nexen evidence, not physical hardware acceptance. Commercial captures and
packages stay outside Git.

## Bounded text damage and request identity

The indexed text producer now clears and dirties the union of the old and new
clipped glyph bounds, within its existing bottom-32-row ownership. A no-ink
request retains a 1x1 publication fence. Old bounds change only after accepted
publication. No extra pixel buffer or memory allocation is introduced.
Submitting an unchanged controller sentence preserves existing dirty intent
without manufacturing another caption redraw ahead of authored dialogue.

Native build on 2026-11-11 (source snapshot includes this tranche):

- ROM: `67daa972622f1c5ee98875c7c9819c389fd7fd3b8790689090bf9e646dc09e64`.
- Map: `e1d3df33aa4a3772edd18a2b52cbb79923b44904dbe35c0693ff64332984fa71`.
- Identity: `796cc5035db59ebd236b155b8a0034a1daf0ef63965550b1cdd84368bcca8745`.
- Same complete source package as above; no gameplay writes.
- `/tmp/astra-bounded-text-action-20261111/observations/action.json`:
  input 12891, original response first observed active 13068, immutable response
  queued 13089, PPU committed 13109. Observed latency **218 frames**; 177 precede
  observed response readiness, 21 precede queueing, 20 complete presentation.
  This is an observed after-measurement, not identical CPU/scheduler phase.
- Response font, room, actor, cursor, INDEX8, VRAM and screenshot comparisons
  have zero differing pixels. Original script executed once, SCUMM error zero.

The initial caption observation was **rejected**: 121 pixels differed because
new request bytes were associated with the previous caption plus cursor
publication. The renderer had displayed the previous caption correctly. An
idle text producer can already be preflighting replacement bytes before its
new generation is allocated. The observer now requires the immutable
awaiting-commit phase, completed draw pass, and exact publication generation.
Synthetic regression reproduces that association failure without game data.
The matching-ROM caption checkpoint was restored without input or state writes:
`/tmp/astra-text-caption-fence-20261111/observations/action.json`, 11.614 seconds,
generation 237. The correct caption has zero source/INDEX8/PPU differences.
This targeted observer correction did not replay startup or the action.

Focused bounds tests execute the production rectangle and clear leaves against
independent clipping/guard oracles. The full host suite at this tranche ran
1,433 tests with 12 skips; the subsequent observer regression adds one test.
Native walking and the rest of Milestone C remain separate pending gates.


The subsequent same-ROM walking after-measurement completed in 155.288 seconds:
`/tmp/astra-bounded-text-walk-20261111/observations/action.json`. Normal inputs
reach (96,60), standing chore 3, with zero source/INDEX8/PPU differences and no
sentence submission. Input 13582, target standing PPU 13807: **225 frames**.
This did not improve on the earlier 192-frame measurement and is not reported
as a latency success. Generation 256 converted 896 unchanged tiles before the
later small actor generations. The existing palette-only flush calls the
full-screen dirty publisher; a palette-only service correction is being tested.

Independent hosted checks for checkpoint `eaad5d89670b94813e3041a12ccc07c6847bfd81`
passed: https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/42997383207.
Draft successor PR #15 targets the preserved PR #14 branch. Hosted CI performs
host tests and assembly/ROM audit, not Nexen execution. Later changes require
their own results.

## Palette-only publication and tile-shadow word copies

A palette-only SCUMM flush now submits the existing checked palette/PRESENT
transaction without a full-screen pixel-damage packet. Queue/ownership failures
retain dirty palette intent. No color, authored timing, DMA budget, or buffer
allocation changes. Actual-source tests cover success and each refusal boundary.

The authentic after-measurement used ROM
`288970a5c1f43fd5d8a995fa282c2382f1197c00ad5436992ebda206d0fac6bb`,
build identity `8877128b5015086eb44d605dbbbf4f51869c7da8ecd52f58d220a8d862aae2cb`,
and the same complete source package. It contains the palette correction but
predates the word-copy optimization below. Evidence:
`/tmp/astra-palette-only-startup-walk-20261111/observations/action.json`.
Normal controller input walks from (84,60) to (96,60), with no sentence
submission or gameplay-state writes. Input 12296, first sampled arrival12317,
standing queued12352, matching PPU12365: **69 frames** input-to-standing,
48 after sampled arrival,13 after queueing. Source costume/room/cursor,
INDEX8 and PPU comparisons have zero differing pixels. This shorter walk starts
at84 rather than the prior82; do not describe it as identical-input A/B.
The combined startup/walk supervisor exited normally after296.947 seconds and
left no test-owned emulator/display. This does not certify camera or UI work.

The tile-shadow leaf now compares and copies32 words instead of64 bytes with
repeated accumulator-width switches. It preserves DBR, stack, tile bounds,
pending-bit ownership and counters. Actual-source tests cover all64 mismatch
positions, invalid/valid cache, first/last tiles and adjacent guards.
The independent six-generation native surface control passed exact PNG,
INDEX8/VRAM/CGRAM and sparse DMA checks with ROM
`571e1ead91278bb093eacd30e21996f113099e6a6c1e506ee078b056976d343c`:
`/tmp/astra-mode3-word-shadow-native-20261111/observations/report.json`.
468 emulator frames versus651 in the prior same fixture;46.384 supervised
seconds,43 committed DMA descriptors,0 pending/rejected DMA,0 guest writes.
Its deliberate locked-producer refusals remain1 each. This backend fixture
is native evidence for word-copy correctness, not authentic gameplay timing.

Full local suite:1,438 tests executed,1,426 passed,12 skipped. `make validate`
and the27-region ownership audit pass. No skipped test is native acceptance.

## Accepted asynchronous HUD work must not be retried

The camera-admission image exposed an independent presentation backlog. In
`/tmp/astra-camera-admission-continuous-20261111`, the unchanged original
Open/Close menu advanced text generations115 through296. The controller kept
HUD_DIRTY because the text service returned BUSY even after validating and
copying its request into the asynchronous producer. Each completed caption
therefore caused the same caption to be queued again. This was real rendering
work, not evidence that the source scripts kept changing the menu.

The service now returns an acceptance receipt for a validated HUD request.
Busy/rejected requests still retry. Authored talk retains its existing BUSY
wait contract. Acceptance neither draws pixels nor advances the committed
presentation generation; observers and other consumers must still use that
fence. Actual-source instruction tests distinguish these states, preserve the
request identity and stack, and reproduce20 old retries versus two genuine
refusals followed by one accepted request. A subsequent real content change
still queues normally. No buffers, source timing, or video budgets changed.

Local full suite:1,494 tests run,12 skipped. `make validate`,33-region memory
audit, pinned Poppy assembly and ROM audit pass. Native current-image evidence
is recorded separately; these host/build checks alone do not certify latency.

## Bounded checked-transfer counter batching (2026-11-11)

The existing provider still polls data readiness and CRCs each transferred
byte. X holds the bounded remaining quantum and Y the destination cursor;
32-bit request/cumulative counters are committed once at the service boundary.
A partial busy failure commits only consumed bytes and retains ERROR. Ring
wrap does not affect the consumed count. READ_OK still requires the complete
request CRC, now checked immediately when the final quantum finishes rather
than on a following empty service call. No quantum, memory allocation, package
format, cache lifetime, or script timing contract was expanded.

The existing copyright-free Winston client, same package and18 read oracles,
was independently assembled with the old and new loop using pinned Poppy.
Both passed all18 cases, all6 checked visual resources, ring guards and500
track2 loop-check frames. This includes >64KiB ring reads and32-bit seeks
past16MiB, expected range rejects, CRC/sample comparisons and serialized A/B/A
requests. PCM service ran concurrently; this test did not record audio samples
and is not new gapless-audio evidence.

| Native observation | Before | After |
|---|---:|---:|
| Final emulated frame |2656|2144|
| Total checked data bytes |257508|257508|
| Median ReadStep cycle-counter interval |80927|46770|
| Retained paired entry/exit intervals |1024|1017|

The median sampled call cost fell42.2%, whole-fixture frame count19.3%.
Intervals use Nexen's reported cycle counter and include interrupt effects;
retained hooks are a bounded sample, not every request. Whole-fixture frames
include script/audio/presentation work and must not be labeled raw MSU speed.
Both builds retain the64-byte quantum. Host instruction tests separately
exercise64/256-byte quanta, exact/partial/empty lengths,32-bit borrow/carry,
ring capacity1/17/1024, partial busy failures and CRC rejection.

Native identities:

before:
- rom_sha256: `b382460405daf758f4205cd7a9d991d5273e5d68d2188f31e0dbdffcd97365bd`
- map_sha256: `19ebce589bc453ae77f1c425589242303f22ce68ecd6c6f0b327f9195d8f6190`
- package_sha256: `94c05cddcd1ad704b8cad9961e86bf12c275201a1aa880af0b0b39b75d4cfd6e`
- build_identity_sha256: `aae9430911cd37a485fd778a6d33fc4997da7e6e592488ff9166b09892fd7127`

after:
- rom_sha256: `909438b04b8874ce6ebc209f0f9e474039b37515fef335168d4d0281f6300015`
- map_sha256: `5c35b0bb1c74a3cad387868529474e22c76447f42c50ce167ac56500bb82f6f9`
- package_sha256: `94c05cddcd1ad704b8cad9961e86bf12c275201a1aa880af0b0b39b75d4cfd6e`
- build_identity_sha256: `1f15bb4f9069ba6074fc4a58e8a778b9232fd3f031f676a01edcca82c4a17c67`

authentic 256-byte boot:
- rom_sha256: `88a3cfe48964a49283d78ea0f03c30607a81a8515dce30828a57d0c7e80c8781`
- map_sha256: `70180c9aa409f9a666853805896401f2eeb01aca5800d75f4f13ba0cf225a7d0`
- package_sha256: `70564585c15538ed04b7f614b5b4d929a07eedf7a8545b510ff0ed66e9ad29d0`
- build_identity_sha256: `5d867b218f0a04fa5d32767f20884c2f21e4eae230791735bd46fc085972caad`

The256-byte production personality booted the unchanged2203-unit authentic
package and published room68 at frame672, error0, in a16.972second supervised
run with no controller inputs or guest writes. Canonical bindings include
GlobalProgram(1), and the actual installed SC5LIVE header matches room68.
This is a storage/boot regression, not another interaction or visual proof.
The first observer attempt incorrectly read the version word as the room ID;
its failure is preserved separately. The correcting observer uses the actual
SC5LIVE HEADER contract; no engine/resource bytes changed between those runs.

Clean provider-only builds exposed an independent missing empty include:
Poppy opens disabled include paths before evaluating feature guards. The build
now owns the empty SCUMM directory for provider-only configurations too, while
preserving enabled generated directories. Fresh/stale-output tests and both
independent native builds cover this correction.

The separate large-live-room harness attempt is NOT native acceptance: its
assembly-only CI flags omitted a boot activation; adding the documented boot
flag exposes the legacy synthetic generated bank0 layout overflow ($FFC9, or
$FFEB with controller, versus header$FFC0). No feature was disabled to fit.
This diagnostic configuration remains an explicit limitation. The current
authentic full-directory configuration and provider-only control both link
and execute; no result is transferred between their ROM identities.

These changes reduce transfer CPU overhead. They do not remove the measured
full-viewport conversion/publication cost or certify responsive scrolling.
