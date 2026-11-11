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
