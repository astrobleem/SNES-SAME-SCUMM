# Playable presentation latency — work in progress

Milestone C starts at `41305d9d32cf02907dc887d3f76e449c01d57389`.
The sections below retain the history of each separately identified experiment.
The latest result takes precedence over their earlier pending statuses. The
separate progression recovery worktree is untouched.

## Current result: retained rendering works; responsiveness gate remains open

Native source commit `cc04e1ed662a4b1093dff15dd35e4b9ce7536d5d` passed one
continuous cold authentic session: original newspaper pickup, readable inventory,
inventory close, walking through the camera trigger, and subsequent controller
input. No gameplay-state writes, synthetic story, checkpoint restore or
seven-action replay were used. Original object ownership changed 15 to 1 and
state 0 to 1. Room 10 remained RUNNING with error zero. Final actor position
was (273,139), standing chore 3; source viewport origin was 208.

The complete source/INDEX8/VRAM/PPU comparison has zero differing pixels, and
CGRAM has zero differing bytes. Capture used immutable generation 220, after
its exact commit and a completed raster, before a later DMA could alter it.
The test exited normally in 477.831 seconds under its private-Xvfb 600-second
process-tree supervisor. These are emulator results, not physical SNES results.

A separate matching-ROM continuation restored the captured post-forward state
(`ee18e52b2b233ed966033513e47897fb6831140f3bf6d68a1a1c688529ffdc76`)
and used normal controller walking to reverse the camera. It passed complete
source/INDEX8/PPU equality, persistent newspaper state and error zero at source
crop 32, actor (239,138). Input frame 9392 to captured frame 10338 was 946
frames. The private 240-second supervisor exited normally after 119.952 seconds.
It is explicitly separate from the continuous cold-session proof. Both owned
emulator trees were cleaned up; an unrelated user's emulator was not touched.

| Measurement | Previous full reconstruction | Current retained camera |
| --- | ---: | ---: |
| Typical publication tile conversions | 896 | 27 |
| Typical character upload bytes | 57,344 | 1,728 |
| DMA batches per typical publication | at least 28 | 1 |
| Input to final captured image, emulated frames | 1,908 | 1,061 |
| Typical observed tile-step commit interval | full crop transactions | 40 frames |

This removes the full-screen rebuild and reduces the recorded total by about
44%, but **does not meet the smooth-scrolling definition of done**. The normal
controller sequence and camera range are the same; sampled cursor release
produced a two-source-pixel difference in the final walk endpoint versus the
older recording. Do not describe the timing as an identical-cycle benchmark.
On this run input was frame 8043, sampled semantic arrival 8180, logical camera
target 8268, final camera commit observed 9092, and final actor/cursor image
captured 9104. Ordinary columns retained existing tiles; some sampled counters
were already reset for a subsequent generation and are not zero-work proofs.

Row-mapped cursor exchange reduced the measured retained composition span from
median 270,337 Nexen counter units/six frames to 115,615 units/three frames.
The tile encoder remains 6,565 counter units per tile. The copyright-free
132-step retained control passes full raster equality, reversal, both ring
wraps, foreground/HUD preservation, DMA refusal, stale-generation rejection
and cold replacement. Its new-column command-to-commit time is 16–17 frames
and cached-column time nine frames, including fixture source generation.
Neither figure is a claimed hardware lower bound or pure DMA time.

### Remaining measured limit

The authentic interval independently recorded 103 executable-cache loads and
102 evictions. Five recurring canonical program identities total 1,358 body
bytes, but the accepted cache has only three independently tagged 2 KiB page
windows. Its existing three-way LRU cannot keep five identities resident.
There were 56,536 provider bytes and 128 completed requests across all clients;
not all those bytes are code. This is a demonstrated descriptor-working-set
capacity problem, not the former tile-shadow alias and not proof that all
remaining latency is caused by the cache. Rendering and serialized service
work still have measured costs. No cache architecture, selector ABI, script
timing, storage format or transfer/conversion budget was changed to conceal it.

Removing that working-set pressure requires a separately scoped cache-capacity
or packing policy with instruction/page identity, pinning and integrity proof.
That redesign is outside this camera mission's explicit constraints. Further
renderer optimization may also help; the present measurements do not certify
an irreducible minimum. Keep PR #15 draft and Milestone C incomplete.

### Exact current identities and evidence

- ROM: `369e1fb8d9522d23634134103ab84c22332391d64a31f9aec6ad1a11d0e746ff`
- Map: `be6a13e99c4d7a30b9447979ccad9211046cc77e0c6c91823917d59de1b101f1`
- Package: `70564585c15538ed04b7f614b5b4d929a07eedf7a8545b510ff0ed66e9ad29d0`
- Build identity: `0e606ca7af7b49aa791ea062820283a86f0ee8fc654dfb20b4ccf5f4d39cb1d6`

All 40 non-generated assembler inputs match cc04e1e. The isolated generated
build has its own Git/source manifest; its Git SHA is not substituted for the
public source SHA. The unchanged full package contains 2,203 ProgramUnits.
Private evidence, including failed predecessors, exact builds, commands,
profiles, captures and SHA-256 manifests, is retained under
`/home/chad/SAME-private-evidence/milestone-c-retained-20261111/column-and-cursor`.
No commercial payloads or captures are tracked in Git.

Local validation: 1,536 tests run, 1,524 passed, 12 skipped; `make validate`,
33-region memory audit, pinned Poppy assembly/ROM audit, Python compilation,
Bash syntax, tracked JSON and diff checks pass. Both hosted jobs passed on
cc04e1e: https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43091042731.
Hosted assembly is not Nexen execution. No automatic merge is authorized.

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


## Native cost boundary and explicit remaining gate

The existing six-generation copyright-free Mode-3 control passed with the
current renderer bytes: all indexed/PPU/palette comparisons, 43 DMA operations,
terminal frame 468. Entry/exit hooks installed **after** cold reset recorded
1,835 tile conversions, with median 6,565 Nexen cycle-counter units per tile.
These units are reported as observed, not converted into device throughput or
wall-clock time. The source hash of the actual renderer in this ROM matches
this branch. A first profiling attempt installed hooks before reset: reset
removed them. Its image control passed, but it supplied no CPU-cost evidence.

- ROM: `571e1ead91278bb093eacd30e21996f113099e6a6c1e506ee078b056976d343c`
- Map: `c6f73508bfeb53752ff3c15063e72f92f096ac7802c534708056d09a1b7c833c`
- Renderer: `11f3b17a8a0cbea93747c3fbd2ed1179fb22ef1861e7356e8a21dbe348bc6529`
- Local report: `astra-mode3-cost-after-reset-20261111/observations/cpu-profile.json`

This isolates the remaining cost from SCUMM scripts and storage waits. Camera
staging currently aliases the complete planar shadow. Preparing a checked
crop clears that alias; publication must invalidate every tile, including
zero tiles whose old VRAM contents are otherwise unknown. The 896 tiles then
require conversion and 57,344 character bytes of DMA. At the existing 2,048-byte
frame budget, character data alone requires at least 28 full payload budgets;
queue/map/palette overhead and CPU conversion add to that. The authentic
camera trace measured approximately 336 frames in conversion and another 96
in queued publication. This is not an authored SCUMM delay.

A few-frame full-viewport update is therefore not provided by this backend
contract. The next required backend capability is retained/incremental camera
presentation that preserves checked transaction semantics, actor restoration,
HUD/cursor ownership, and NMI-owned transfers. It must avoid destroying and
rebuilding the entire shadow on each pan. Simply removing invalidation would
publish stale tiles; raising budgets cannot remove the measured total work.
No alternate renderer, guessed memory allocation, or relaxed checksum was
introduced to conceal this limitation. **Responsive scrolling remains OPEN;
the functional continuous gameplay checkpoint is not full Milestone C acceptance.**

## Native corrupt-read rejection and diagnostic field correction

An isolated copy of the original Winston package had one byte flipped at
32753, within case 2's 31-byte checked request. Trusted header, directory and
tail remained unchanged. The provider correctly returned ERROR/CRC6 after the
first two cases, without visual-resource publication. That first run also
exposed a pre-existing diagnostic bug: three failure exits copied the byte
CASE_INDEX as a word, incorporating the adjacent CASES_PASSED low byte. Case 2
was reported as $0202. Preserve the failed assertion; it is not a failed CRC
check or a successful original diagnostic result.

All three exits now mask the case index to $00FF before storing the word
FAILED_CASE. Actual-source host tests vary both case identity and adjacent
counter, preserving the latter. The newly assembled control reports case 2,
CRC6, both $A5 guards intact, zero completed visual reads and no CRC-success
publication. It terminates at frame 24, normally, in 5.304 seconds including
private display/process supervision. No retries of unchanged binaries, guest
writes, commercial gameplay or silent ROM fallback were involved.

- ROM: `80b512144a750a428395651cddb4e890da73e235ece850112b07c8d45bdb865f`
- Map: `2752a705573c25a13c86819633d27df93c66cd3aece642066ba2d3a2ed1ff361`
- Build identity: `891b7bc134d443fb8cb8fb00b0ba009b09d4ebfda8fa85605fab2f190102767a`
- Fault package: `b35e5f29288b6fc29a4c48be2cce1e5f2813a9749e761433d119c04bfa51bb86`
- Original package: `94c05cddcd1ad704b8cad9961e86bf12c275201a1aa880af0b0b39b75d4cfd6e`
- Local report: `astra-quantum-crc-case-corrected-20261111/observations/report.json`

These failure and performance records, including failed observer attempts,
commands, build identities and cleanup results, are retained outside Git under
`/home/chad/SAME-private-evidence/milestone-c-20261111/provider-and-renderer-cost-final`
with a SHA-256 manifest. They do not replace the separate ROM-bound continuous
pickup/inventory/camera evidence. Hosted CI does not run Nexen.


Final local validation: 1,508 tests run, 1,496 passed, 12 skipped; `make validate`
passes, including Poppy lint and the 33-region WRAM/BW-RAM ownership audit.
Python compilation, 60 tracked JSON files, all 3 tracked Bash scripts, and
`git diff --check` pass. Pinned assembly/ROM audit passes for the corrected
Winston image; all 17 non-generated assembler inputs match this source tree.
The private generated build Git identity is distinct from the public source
checkpoint. Skips and hosted assembly are never counted as Nexen acceptance.


## Retained viewport integration (in progress, 2026-11-11)

The backend now retains 33 physical scene columns (24 tiles each), the fixed
32x4 HUD, and a 64x32 hardware map at VRAM $F000. Character storage ends at
$E600. Only the newly exposed checked column is converted; cached columns
are reused. NMI changes tile references and the scene scroll after character
transfers complete. An HDMA split holds the lower 32 lines fixed. The existing
2,048-byte/eight-descriptor transfer budget and four-tile conversion budget
are unchanged. BG2-overlay personalities retain their legacy allocation and
do not enable retained scrolling.

The extra 1,536-byte shadow is split between $4010C4..401384 and
$401BC4..401F04. Checked camera/actor reads use only the first 2 KiB of pending
scratch. Incoming room transactions retire the guard lifetime first. The
original palette destination $401084 remains unchanged, as required by both
the checked provider and palette consumer. The live HDMA table at
$41E73A..41E744 is outside every incoming-room alias. All ranges are declared
in the carrier/backend ownership descriptions and checked by the memory audit.

The existing actor and cursor journals can exchange opaque pixels with the
surface, restore their backgrounds into retained characters, rebase the actor
journal, and compose again without allocating another framebuffer. Journal
validation precedes writes. Source/world coordinates remain authoritative;
SCUMM uses surface-service APIs and installs the accepted transform only after
the exact two-word presentation generation commits. Busy queues retain the
checked strip and do not recompose a partially published surface.

Native copyright-free evidence (not authentic gameplay acceptance):

- `astra-retained-wrap-native-20261111`: 132 committed steps across both the
  33-column character ring and 64-column map, then back. Every complete
  INDEX8/VRAM/PPU comparison passed. ROM
  `7558a356c1e06e9aaebbbf42210d1828dd9be9dba49bc44c023c8d70de6b2760`.
- `astra-retained-production-edge-20261111`: production cached-column decode
  and edge fill, six forward/reverse steps, complete pixel equality. A new
  column converted 24 tiles/1,536 bytes; cached steps converted/uploaded zero.
- `astra-retained-foreground-20261111`: world-space opaque-zero foreground and
  fixed cursor, eight forward/reverse steps, full INDEX8/VRAM/PPU equality.
  Changed strips plus cursor damage uploaded 1,664 bytes; cached steps with
  cursor damage uploaded 128 bytes. Measured step intervals were 18–33 frames.
  This still includes a synchronous, interruptible INDEX8 scene move; few-frame
  scrolling is not claimed. A separate instrumented cost control isolates it.

An initial native failure exposed Poppy excluding a unary-negated conditional
around the NMI scroll routine. Explicit `== 0` fixed the emitted code; the
validator now requires the assembled commit labels before launching Nexen.
The first authentic integration attempt stopped at frame128 with explicit
resource error16 before gameplay. The proposed alternate palette destination
was rejected by the existing checked-read whitelist. The fix preserves the
original palette address and retires the aliased camera state instead. That
failed image is not accepted, and its captures/checkpoint remain preserved.

The initial full host run additionally caught direct backend references in
the engine adapter. These were moved into the existing surface-service ABI;
the architecture gate remains unchanged. The small source-instruction camera
runner now honors build conditionals instead of executing both personalities.
Focused interface, palette, ownership, and old/new transaction tests pass.

**Integrated authentic camera acceptance and final Milestone C remain pending.**
No seven-action replay, gameplay-state writes, recovery-worktree modifications,
new renderer, package format, or selector changes are part of this work.

Cost control `astra-retained-cost-fixed-observer-20261111` passed all six
full-pixel checks. Median Nexen cycleCount deltas: tile conversion11,680,
INDEX8 scene move346,914 (7.5frames), cached-column decode178,646 (4frames),
edge fill112,926 (2frames). The initial profiler failed before reset because
its overridden MCP method required an optional argument; no timing was inferred
from that failed run. The corrected observer installed hooks after reset.
These measurements identify remaining CPU work independently of provider I/O.

### Circular INDEX8 scene and retained foreground (integration in progress)

The retained backend now keeps the existing scene INDEX8 bytes in a horizontal
ring as well as retaining the planar characters. A camera step changes a bounded
row origin and fills the exposed edge; it no longer copies all192 scene rows.
The surface's byte/pair accessors map logical pixels, including actor and cursor
journals, through that origin. The32-row HUD stays linear and fixed. No pixel
buffer, executable cache page, transfer budget, or selector allocation was added.
Pairs crossing physical x255 map their second pixel back into the same row.
Cold room projections remain linear until retained initialization.

Fully visible retained characters reuse the existing native planar encoder.
Only partial edge characters need checked-strip/old-shadow merging. Exposed
runs use interruptible bank-safe moves of at most8bytes, with every source and
destination row boundary checked by exhaustive host step tests.

The original foreground fixture passed six forward/reverse steps with full
INDEX8/VRAM/CGRAM/actual PPU equality on ROM
`/tmp/astra-retained-build.7e0c_d30/mode3.sfc` (private artifact; exact hashes in
its build identity and the report). Evidence:
`/tmp/astra-retained-ring-fast-native-20261111/observations/report.json`.
Cached-column steps with a fixed cursor take9frames and upload128bytes;
new-column steps take20–24frames and upload1664bytes. These include foreground
restoration and publication. They are synthetic renderer measurements, not
an authentic-game latency claim. The earlier linear INDEX8 shift alone took
7–8frames; the circular origin change does no scene-wide pixel copy.

Source-instruction tests cover exchanged actor/cursor journals across physical
row wrap and the fixed-HUD boundary, opaque zero, decimal/width preservation,
clipped rebasing and neighboring guards. The independent observer decodes the
actual physical surface origin; it still compares every visible pixel and
requires the exact committed generation. Authentic integration remains a
separate gate until the continuous new-ROM result is recorded.

### Retained actor lifetime and native fault controls

The first circular-surface authentic run retained original pickup/inventory
behavior but ended at final source origin208 with resource error16. It is not
accepted: `/tmp/astra-retained-ring-authentic-20261111/observations/action.json`.
The standing chore had inherited the previous walking loop's eight steps while
camera work postponed loading the new pose. Desired standing step1 had no
matching source directory row. A pose-key change now clears its loop metadata;
step0 remains unseeded until that key's own checked row supplies loop bounds.
The source-instruction regression exercises hundreds of deferred ticks and
subsequent one-step and multi-step loops.

A fully visible world-anchored actor now stays in its physical INDEX8/character
ring slots. The existing sparse underlay journal is validated, then only its
logical destinations and half-open bounds are translated. Opaque-zero pixels,
holes, identity and saved background bytes remain unchanged. Edge-clipped or
mixed scene/HUD journals use the existing exchange/clip path. Tests restore
these journals after circular-origin changes and verify every physical pixel,
including rejection without mutation for busy, stale and malformed journals.
No new pixel storage is allocated.

Same-room camera strips request one foreground turn between commits. The
existing actor/cursor compositor executes that turn only in the late visual
phase, not inside a camera opcode. Its checked transfer is allowed to finish;
then camera I/O gets its turn. The one-byte handshake uses the explicitly
unused byte inside the existing40-byte camera allocation and resets on room
requests. Incoming-room priority remains unchanged.

Current circular-surface native controls:

- `astra-retained-ring-wrap2-20261111`:132 completed forward/reverse steps,
  both ring/map wraps, fixed cursor/HUD and opaque-zero world foreground.
  Entire INDEX8/VRAM/PPU equality,9–24frames, at most27 converted tiles and
  1664character bytes per step. ROM
  `b03576cab04047f01978c62309d06f5d25d7577db7c265ebc8a49a90c4108e05`.
- `astra-retained-fault-native-20261111`: overlapping ticket refusal and
  abort preserve pixels/VRAM; actual NMI rejects a stale high generation word
  even with a matching low word. Cold replacement after scrolling resets the
  hardware map/scroll and matches every expected INDEX8/VRAM/PPU pixel.
  Supervised29.285seconds, normal exit and owned-process cleanup.

These are original fixture controls. They do not substitute for authentic
camera acceptance or physical hardware evidence. The integrated actor-corrected
original-game run is tracked separately and is not declared passing here.

### Cursor ownership during incremental publication

The actor-corrected run reached the authored camera transition without error,
but an observer admission guard recognized only an MSU transfer, not the new
foreground service turn. Its matching-ROM continuation finished the pan and
then correctly failed the full source-pixel check: cursor projection had used
the future logical camera target while earlier retained strips were visible.
The stationary cursor could move offscreen, and its final journal retained an
intermediate projection. Neither run is counted as integrated acceptance.

The cursor now uses the fixed, bounded inset of the320-pixel SCUMM virtual
screen into the256-pixel target viewport. Future camera targets no longer
move screen-owned cursor pixels. Logical world hit testing still waits for
its committed camera transform. Actual-source host execution covers delayed
commits, narrow-room clipping, multiple target origins and full cursor pixels.

A foreground turn drains an already pending cursor publication or restoration,
but does not initiate a fresh cursor blink-only PRESENT before each strip.
The camera exchanges the existing fixed cursor journal in its publication;
a changed actor draws the cursor within its own publication. Ordinary cursor
updates resume through the existing path after the pan. This removes a
redundant transaction without raising conversion or DMA budgets. Tests verify
pending/composing cursor ownership is drained before actor work.

### Passing retained gameplay checkpoint and remaining cost

Commit1529a2c's native inputs match ROM
`07711a05005a3aa247968787cfa79270a780edc1c5af7f5f8cbaa0b022e4bece`.
One continuous cold session passed original newspaper pickup, readable inventory,
normal walking, forward retained scrolling and continued control, with error0
and complete source/INDEX8/VRAM/CGRAM equality. The matching-ROM reverse control
also passed; it is explicitly separate from the continuous recording.
Forward evidence is preserved privately under
`/home/chad/SAME-private-evidence/milestone-c-retained-20261111/forward`.
Its supervised duration was520.861seconds, with normal cleanup. No proprietary
capture, ROM or package is committed.

This is **not yet a satisfactory responsiveness result**. Input-to-final-capture
was1564frames versus1908 in the previous full-reconstruction recording. Ordinary
strips typically uploaded1728bytes in3DMA batches instead of57344bytes, but
observed commits were still approximately48frames apart. The full-screen
conversion defect is removed; the remaining sequential transaction overhead
must not be described as smooth scrolling.

The reverse control's read-only hooks measured median427005Nexen cycleCount
units (10emulated frames) inside foreground preservation/composition, versus
53604units/1frame for edge filling. Logical kernel frames had median3emulated
frames.425checked-read turns and317conversion turns were independently observed;
these overlapping measurements are not summed as a device-throughput claim.

A second correction preserves restored foreground pixels in-place when their
entire rectangle remains visible after ring motion. It marks the old physical
tiles and encodes their final composition once. Evicted pixels still receive
immediate planar preservation. Cursor damage is cleared before the independent
actor preservation pass, removing duplicate conversion of the same rectangle.
Actual-source predicate tests enumerate all x positions, edge widths, both
scroll directions and mixed scene/HUD rows. The changed backend passed132native
steps, both wraps, refusal/abort, stale-generation rejection and cold replacement,
with every INDEX8/VRAM/PPU pixel compared.

The same four bounded backend slices are now interleaved with existing kernel
phases rather than called adjacently. Storage/engine execution gives NMI an
opportunity to finish an immutable DMA batch before its next completion poll.
Conversion remains4tiles per slice,4slices per logical frame; DMA remains2048B
and8descriptors. Legacy slices emit no work. There is no timer, scheduler,
interpreter, memory-allocation or transfer-budget change. Poppy rejects repeated
includes, so the generated slice is included once in the neutral video-service
wrapper. The changed schedule passed six native forward/reverse full-pixel
steps and the refusal/stale/cold-replacement controls. Its authentic current-ROM
measurement is still pending and is not inferred from those fixture results.

## Contiguous character columns (retained viewport)

Scene character storage is now column-major: logical row*32+column maps to
column*24+row. INDEX8 and dirty candidates keep their existing logical
coordinates; pending/in-flight DMA IDs name physical characters. The fixed
HUD and guard characters keep their IDs. The ROM lookup is1,840bytes; no
WRAM, BW-RAM, VRAM, tile-conversion limit or DMA budget grows. Initial and
NMI-owned tilemaps use the same mapping; legacy BG2 retains row-major storage.

The prior row-major layout scattered an exposed column across24descriptors
and three eight-descriptor batches. A background column now occupies one
1,536-byte run. Foreground damage in the original fixture totals1,664bytes
in one batch. This fixes descriptor fragmentation without increasing the
2,048-byte NMI budget.

Native original fixture: `/tmp/astra-column-native-20261111/observations/report.json`.
ROM `3201b0902b2b48c17ca7dd36fb2fee813573c2e965047d396ef542a37ba5d95e`;
map `dde57f8ec949f34dc5f77e64f42c5556fd2090b9458866e186ca695053d90ecb`;
build identity `44617583ea9eb7818ea937baa94bb18b55c761d7bbd6cfa3d3a53563940be3ec`.
All132steps pass full INDEX8/VRAM/screenshot equality, including1pixel,
8pixels, repeated motion, both ring wraps, reversal, fixed foreground/HUD,
DMA refusal/abort, stale32-bit generation and cold replacement. Ordinary
new-column steps take16–17emulated frames with26converted tiles/1,664bytes/
one batch; cached-column steps take9frames with2tiles/128bytes. Initial
partial steps take19–20frames. This is still a measured latency frontier,
not a claim of few-frame authentic gameplay. Supervised189.555seconds,
normal exit and owned-process cleanup.

The preceding `94a6c88` authentic run reached the intended camera origin and
error0, but its observer required two idle samples while cursor publications
continued. The600-second supervisor terminated it. It is NOT_ACCEPTED, and
no screenshot is inferred. Captured samples contain valid committed windows;
offline observer regression passes14tests. The next observer polls each frame
at the target and also uses the existing immutable queued-generation fence,
requiring a complete raster before capture and rejecting subsequent DMA.
Read-only execution-hook events are now journaled during collection, rather
than written only on normal session exit. No replay was used to test this
reporting correction. The changed-ROM authentic measurement remains separate.

Column tranche validation:1,535tests run,1,523passed,12skipped; `make validate`
and33-region ownership audit pass. Pinned Poppy assembles both the original
fixture and full authentic configuration; ROM audits pass. The prior
94a6c88hosted run43085838908passed both jobs; it does not certify this change.
The synthetic command-to-commit interval includes its generated strip loop,
so16–17frames is not asserted to be pure conversion/DMA time.

## Column-layout authentic continuation and remaining working set

The cold column-layout run was terminated by its600-second supervisor after
source camera192/error0, before the final capture. Preserve that run as
NOT_ACCEPTED. A separately labelled, exact-ROM pre-camera checkpoint
continuation then passed in172.953seconds:
`/tmp/astra-column-targeted-native-20261111/observations/action.json`.
It is not spliced into a continuous acceptance claim. ROM
`77600cd358447b527477a19a5db572cab4253fc669dc096d20bd3dd3cd321c47`,
same full package70564585..., actor277,139 standing3, source crop208.
Source background/costume/font/cursor, INDEX8, VRAM and PPU match exactly.
Input8236→capture9399:1,163frames, versus1,908before retained presentation.
Ordinary observed column intervals are about42frames;27tiles/1,728bytes/
one DMA batch replaces896tiles/57,344bytes/full reconstruction. This is
functional incremental rendering, **not smooth camera acceptance**.

Read-only hooks show median tile encoder6,565Nexen counter units and retained
composition approximately270,337units/six emulated frames. Cursor exchange
mapped each pixel through two far helpers. The next bounded correction maps
each validated row once and preserves within-row circular wrap, fixed HUD,
transparent/opaque-zero pixels, and the existing damage/publication protocol.
Host source-instruction tests cover all prior cursor cases plus wrap/guards/
scene-HUD boundaries;1,536tests run,1,524passed,12skipped. Pinned assembly and
33-region memory validation pass. New native integration evidence is pending.

The same camera interval also recorded109executable-cache loads and109
evictions,57,267provider bytes and135completed requests. Sampled request
identities (bound to the matching full directory) repeatedly include:

| Canonical source identity | Body bytes |
| --- | ---: |
| GlobalProgram(59) |787|
| RoomLocalProgram(room=10,local=211) |120|
| RoomLocalProgram(room=10,local=215) |107|
| RoomLocalProgram(room=10,local=217) |163|
| RoomLocalProgram(room=10,local=218) |181|

These are integration observations, never production selection rules. Their
combined1,358bytes fit within the physical6KiB cache, but the accepted cache
has three independently tagged2KiB windows, each holding one ProgramUnit
page. Five repeatedly scheduled identities exceed its descriptor working set.
This is a separate measured cache-granularity limitation, not proof that
rendering is free, nor permission to redesign the cache in a camera change.
Provider request sampling can miss intermediate requests; counter deltas
remain exact for the captured interval. Reports stay private with identities.
