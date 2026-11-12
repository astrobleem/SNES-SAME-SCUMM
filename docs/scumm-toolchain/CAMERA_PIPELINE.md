# Checked camera-column pipeline

This extends the retained viewport and packed code cache on PR #15. It does
not change SCUMM timing, the 178-selector ABI, physical code-cache capacity,
SAMEPKG, the 33-column ring, or the 2,048-byte DMA budget. Full-game readiness
remains **NOT_READY**.

## Ownership and dependency changes

The surface service now describes a useful next source column after the
current column has been copied into INDEX8 and PRESENT has locked that surface.
At an aligned origin the next checked read can use the pending prefix during
tile conversion: the newly exposed column's encoder reads INDEX8. Nonaligned
edge conversion still reads the prefix, so lookahead rejects those origins. Speculation does **not** write pixels,
characters, or a tilemap. The existing BeginScroll still proves that a physical
slot is unreferenced before installing the next column. There is no extra
framebuffer or executable-cache lease.

A 24-byte ticket occupies the audited WRAM gap `$7E2EE8..$7E2EFF`. It records
room/epoch, column, length, full 32-bit offset/CRC/presentation generation,
origin, state, and a diagnostic hit counter. Reading and CRC-accepted states
are distinct. Reconciliation precedes any reuse of the provider descriptor.
The descriptor's destination, length, offset, CRC and successful completion
must match before the ticket is accepted. Consumption also checks the room,
epoch, origin, column and both generation words.

Resident scripts continue while a strip is loading. Code and room requests
retain priority; a required costume may discard completed speculation, but
never reclaim its still-writing buffer. Incoming rooms retain camera ownership
until the existing provider/publication drain completes. Cached reversal drops
the old ticket before reusing its pending bytes. A checked hit with invalid
installation geometry fails explicitly rather than silently issuing a retry.

Mode-3 conversion may queue its ready DMA in the same bounded slice. A completed
DMA may retire its descriptors and arm the NMI scroll ticket in the same slice.
Neither transition adds a conversion quota, raises a DMA budget, spins, or
publishes before the NMI acknowledgement. Foreground damage and the existing
world-anchored actor retention remain intact.

An initial implementation incorrectly waited until conversion finished before
prefetching. Native gameplay remained correct, but its forward sequence took
935 sampled frames, compared with the recorded 919-frame baseline. That run is
preserved as insufficient performance evidence. Source inspection and its
read-only trace established the earlier lifetime boundary used above.

## Cursor transparency during retained scrolling

A faster publication exposed a real cursor defect: the dense underlay exchange
transported background pixels through the cursor's transparent holes. The final
image had 232 incorrect source pixels although INDEX8 and PPU agreed. That run
remains failed evidence, not an observer exception.

The cursor producer now supplies each clipped source coverage row explicitly.
Capture defaults to dense coverage for existing service clients; SCUMM narrows
it before drawing. Exchange/restore never read or write transparent pixels.
Opaque index zero is still copied. Two audited 16-byte bitsets at `$7E2370` and
`$7F3EF0` fit between existing owners; the 288-byte pixel journal is unchanged.
No room staging, code-cache, actor, or NMI allocation is borrowed. A separate
correction makes overlapping text restoration consume the journal even after
an earlier retained exchange left the shared exchange-mode scratch set.

Source-instruction regressions cover changed backgrounds, opaque zero, ring
wrap, clipped rows, busy refusal, bounds, preserved registers, guards, and text
restoration after a camera exchange. The native source-driven fixture moves
its real controller cursor onto the textured background before both pans.
`native-cursor-coverage-final` passes full source/INDEX8/PPU/palette/screenshot
comparison in both directions. The interrupted authentic startup was stopped
when the text-restore regression was discovered; it is not acceptance evidence.

## Reproducible original-source control

Generate the source archive with:

```sh
PYTHONPATH=src:. python3 -m examples.resources.scumm_v5.camera_pipeline_fixture /new/path/camera.zip
PYTHONPATH=src python3 tools/package_scumm_v5_source_msu.py \
  --source /new/path/camera.zip \
  --profile examples/profiles/scumm_v5_game_analysis_fixture.json \
  --output /new/path/package
```

Use the normal full SCUMM streamed-code/live-room/actor configuration, camera
projection, no text overlay, the generated whole-source manifest, costume 1,
and `SAME_SCUMM_SYNTHETIC_VARIABLES=1`. No diagnostic native engine is added.
Global 1 loads room 1, initializes variable 70, then pans to it and yields.
The two archive members are original fixture bytes; their historical source-pair
filenames are only an existing discovery convention.

Run `tools/validate_scumm_camera_pipeline_nexen.py` through the canonical private
Xvfb/process-tree supervisor, supplying the exact ROM, native directory,
program-storage manifest, fresh output root and dedicated MCP port. The tool
refuses a different boot-body hash or visual pixel corpus before writing the
synthetic command. It uses the existing immutable queued-generation fence,
checks full source/INDEX8/VRAM/CGRAM and actual screenshot equality, and stops
at the first failure or deadline. These writes are diagnostic commands, never
claims of authentic gameplay.

The separate original retained-renderer control covers one-pixel/tile steps,
wrap, reversal, fixed HUD/foreground damage, refusal, stale publication, and
replacement. Ticket instruction tests cover foreground priority, low/high
32-bit mismatches, stale room/epoch, invalid lengths/destinations, cached
reversal, busy/error results, and installation failures.

## Native evidence and scope

Persistent private evidence is under
`/home/chad/SAME-private-evidence/milestone-c-camera-pipeline-20261112`.
No ROM, package, image, savestate, or commercial source payload belongs in Git.

- `native-phase-handoff`: 76 retained-renderer steps pass full raster checks;
  typical new columns 16 frames, cached step 8 frames. No SCUMM gameplay claim.
- `native-ahead-overlap-bound`: the original source-driven fixture passes both
  directions; 29 forward and 29 reverse checked lookahead hits, zero full-image
  differences. Four-frame sampling bounds the ordinary intervals at 16–20
  frames. This is not the resident-source fixture's cost.
- `native-ahead-pending-reversal`: a normal synthetic command reverses direction
  while the provider is writing a speculative strip; the final ticket is empty
  and the complete reversed raster agrees with the source.
- `native-overlap-crc`: one byte of synthetic strip 37 is corrupt, while the
  directory/expected CRC are unchanged. The provider and SCUMM report explicit
  failure, the ticket is cleared, and the bad column is not published.

## Final authentic acceptance

Runtime source `16592b90cbc04bdf6bd325fc772805f3396b8eb4` passes one continuous
cold session: original startup, newspaper pickup through its original script,
owner/state 15/0 to 1/1, readable inventory open/close, walking through the
camera trigger, and subsequent controller input. No synthetic story, guest
gameplay-state write, or checkpoint restore occurs in that session. Seven
completed scene/text captures have zero source/INDEX8/PPU/CGRAM differences.
The final actor is (273,139), standing chore 3, source crop 208, error zero.
The private supervised Nexen MCP session exits normally in 493.09 seconds.

A **separate matching-ROM** post-forward checkpoint control reverses using
normal controller input. It retains newspaper owner/state 1/1 and error zero,
and passes full source/INDEX8/PPU/CGRAM comparison at crop 32, actor (233,138).
It exits normally in 76.55 seconds. It is not spliced into the continuous run.

| Measurement | Packed-cache baseline | Pipeline result |
| --- | ---: | ---: |
| Forward input to final image | 919 frames | 808 frames |
| Separate reverse input to final image | 801 frames | 643 frames |
| Median sampled steady column interval | 32 frames | 24 frames |
| Final logical camera target to final crop commit | 632 frames | 528 frames |

The forward boundaries are input 6999, sampled semantic arrival 7158, final
logical camera target 7278, final crop commit 7806, final image 7807.
The reverse boundaries are 8119 and 8762. The source camera range and input
sequence are equivalent to the baseline; observer sampling phases and initial
cache warmth are not cycle-identical. Eight-frame polling gives mostly 24-frame
and occasional 32-frame column intervals; it is not an exact per-step timer.

Forward uses 21 checked lookahead hits. It also loads/evicts **one** executable
before retained scrolling: GlobalProgram(33) displaces ObjectProgram(10,147).
There is no repeated five-program eviction cycle. Reverse has zero additional
code loads/evictions; that observer did not capture the lookahead hit counter.
Do not transfer the baseline's zero-load claim to this differently warmed run.

## Exact phase timing and remaining cost

One bounded, read-only timing diagnostic restores the matching pre-camera and
post-forward checkpoints as separate continuations. It does not replay startup
or inject gameplay state. Its 1,531 durable events identify actual engine frame
boundaries, independent of MCP wall-clock observation overhead:

| Prepared new column | Frame |
| --- | ---: |
| Consume previously verified source strip / compose | 7266 |
| Composition complete | 7268 |
| Request following strip while current conversion runs | 7269 |
| Following strip CRC accepted / ticket reconciled | 7279 / 7280 |
| Queue current character DMA | 7284 |
| Observe completed DMA | 7286 |
| NMI commits current tilemap/scroll | 7287 |

This is **21 frames composition-to-PPU**; the preceding commit is at 7264,
giving an exact 23-frame column interval. A cached reverse column composes at
8226, reconstructs its indexed strip at 8227–8231, queues at 8236, observes DMA
at 8240, and commits at 8242: **16 frames composition-to-PPU**.

The 16–17-frame new-column and approximately 9-frame cached fixture targets
are **not fully reached in authentic gameplay**. Remaining measured CPU work
is explicit, rather than attributed to an unexplained resource wait:

| Complete-call CPU counter cost | Prepared new | Cached reverse |
| --- | ---: | ---: |
| Composition, including cursor/edge work | 110,636 | 299,063 |
| Conversion/scan | 291,709 | 79,444 |
| Checked transfers for the following strip | 195,185 | 130,178 |
| Complete SCUMM scheduler calls inside the interval | 165,434 | 90,701 |
| Total interval | 941,199 | 711,181 |

Cached composition includes 184,578 counter units reconstructing INDEX8 from
retained planar data. New-column conversion includes 33 encoder attempts
(217,485 units), but only **25 changed/uploaded tiles, 1,600 bytes, one DMA**.
The cached sample attempts eight encodes and uploads five tiles/320 bytes in
one DMA. Encoder, edge and cursor costs are nested and must not be added twice.
Scheduler calls crossing interval endpoints are excluded from the call totals.
These are Nexen CPU counters, not raw MSU throughput, elapsed observer time,
or a demonstrated hardware minimum. No script cadence or DMA budget changed.

The checked-read serialization and cursor corruption identified in this pass
are corrected and the integrated pipeline is accepted for review. This does
not certify smooth 60 Hz scrolling or prove all remaining CPU work optimal.
Further performance work would have to reduce measured conversion/composition
or service cost, not repeat the same gameplay to search for another wait.

## Identities and validation

Private build: `auth-build-wcu3bm0o/fate-authentic-room` under the evidence root.

| Artifact | SHA-256 |
| --- | --- |
| ROM | `c244c4ba509f94fe219ef03257cbd4e39ec782158298b5dfeb5a7832aa641aac` |
| Map | `0eac10ebc08a5bf27a8123e623109bde52c2f144ed03e53ec4b9f21087a50745` |
| Full-source package | `e6cf5c28f36f20c10cb9ef7819a1b278b1067ed3014462cee53d9a63d9772afd` |
| Build identity JSON | `d3a14f3a59f5bdc30334f38d99ccbdfb86e2d1984cc5fc40bd8dfadb167b4f5d` |

The isolated build has its own recorded source-snapshot identity. All 59
non-generated runtime files byte-match `16592b9`; the linkage manifest records
that comparison, rather than claiming the ROM was rebuilt from a later docs
commit. The 2,203-unit package hash is unchanged from the packed-cache baseline.

Evidence: `authentic-pipeline-final/observations/action.json`,
`authentic-pipeline-reverse/observations/action.json`, their
`pipeline-performance.json`, `final-column-profile/observations/phase-costs.json`,
and `final-source-build-linkage.json`. Images and checkpoint states remain local.
Failed predecessors and the interrupted startup remain separately labeled.

Local suite: **1,574 passed, 12 skipped** (1,586 run). `make validate`, the
41-region WRAM ownership audit, pinned Poppy assembly, 4 MiB ROM audits,
Python/Bash/JSON and diff checks pass. The runtime commit's two hosted jobs pass:
https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43178831917 .
Hosted CI assembles native code but does not run Nexen or use commercial data.
No physical hardware, complete game semantics/audio, or portable streamed-save
acceptance is claimed. PR #15 remains stacked on #14 and is not auto-merged.
