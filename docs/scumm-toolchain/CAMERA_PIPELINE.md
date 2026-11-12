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

The authentic continuous and reverse results, exact artifact identities and
final performance accounting will be added after their observations complete.
Assembly and host tests are not substitutes for those observations. Hosted CI
assembles native code but does not run Nexen or use commercial resources.
