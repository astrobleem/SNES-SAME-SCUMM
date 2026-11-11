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
