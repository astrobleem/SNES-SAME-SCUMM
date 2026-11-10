# Checked actor visibility checkpoint

The source-costume graphics diagnostic passes on Nexen. This is a synthetic
118-byte SCUMM driver using original external costume/background resources,
not authentic gameplay progression. No story replay was run.

## Corrections

- Restore 16-bit register widths before five underlay epilogues pop their
  saved registers. The previous A8 PLA misaligned the JSL return frame.
- Keep the visual pending flag byte-sized regardless of the frame caller's
  accumulator width; the adjacent pending-room ID is not a pending flag.
- Move the 14-byte synchronous underlay cursor alias to `$7E:5E7C..5E89`,
  entirely within nonconcurrent RestoreRect debug witnesses. The previous
  allocation overwrote persistent `ROOM_READY` at `$7E:5E8A`. The audit now
  resolves named aliases and checks every cursor field against that boundary.
- Preserve the complete pose damage rectangle across opaque-run copies.
  Previously the final span replaced it, leaving most actor tiles absent
  from the next VRAM update despite correct indexed pixels.
- Apply presentation backpressure before advancing the visual animation
  counter. Script scheduling is unchanged; pending presentation no longer
  accumulates an immediately superseding desired pose.
- Zero-extend palette bit/group indexes before TAX. An A8 load retained the
  pixel cursor's high byte, producing invalid override lookups after byte 255.
- Generate the empty actor directory for actor-disabled builds, because
  pinned Poppy resolves include paths before feature guards. Fix module/file
  invocation imports for the synthetic overlay tool.
- Capture actual VRAM/CGRAM and require exact agreement with the indexed
  surface before acknowledging each stage. Require zero old-position residue.

## Native evidence

Final local build: `/tmp/luna-actor-stack-fixed-20261109.zr2b5rf8`.
Final supervised run: `/tmp/luna-actor-fidelity-proof-20261109`.
The exact command and deadline are in `process-result.json`; observations,
raw indexed/VRAM/CGRAM captures, screenshots, and finalization are retained in
`observations/`. These commercial-resource-derived artifacts are not in Git.

| Artifact | SHA-256 |
| --- | --- |
| ROM | `70220f8f301d8b3fd6a6b7687813d7bc15551d15a996665e376af8079200d7b8` |
| Map | `0654ba5efd89e40941ba2045ade90c4c782f11fe8f5637f62345fb394d5e9a72` |
| SAMEPKG | `dd62d66937ad37a94a4898bc945c32925049caca45262f97186838e58efb6f2d` |
| Build identity | `2831660da1d723335ca38927176a243fd861a972a19fe2303861ff825a207003` |
| External archive | `0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0` |
| Original costume resource | `07e0c506e7d365e7210a6e8b380fa5e6b571d141aee4a476e61490d6b8ca0f2e` |

The build identity records parent `add72d1` plus its dirty source snapshot,
not a claim that the later commit existed at build time. All 63 assembly
includes in its Poppy input manifest match the repaired source and retained
generated inputs. Documentation/test-only changes after assembly do not
retroactively change that identity.

The run completed in 68.099 wall seconds / 3,176 emulator frames under the
600-second private-Xvfb process-tree supervisor. Error remained zero. Five
captures passed indexed-to-VRAM and RGB8-to-CGRAM comparison with zero
differences: standing (frame 3, facing 180), turned (frame 3, facing 90),
animation frame 2 steps 0 and 1, and moved standing pose. The old location
had zero residual pixels. Test-owned processes exited and MCP port 7398 was
released; the unrelated session on port 7381 was untouched.

An independent offline comparison decoded the exact original costume with
`ScummV5Costume.decode_pose`, compiled its signed foot-anchored spans with
`compile_pose`, mapped nonzero source slots through the original palette,
and overlaid them on the checked package backdrop. Each of the five complete
native indexed surfaces matched this host result byte-for-byte. The report
is `observations/host-source-comparison.json`; the local reproducer is
`/tmp/luna-actor-host-compare.py`. No new native run was used for comparison.

Earlier runs remain preserved and are not promoted to this result. In
particular, the first standing surface was not fully presented, and the
pre-palette-fix captures differed from the original source colors.

## Validation and boundaries

- 1,196 host tests, 12 skips; `make validate` passes in an isolated Git checkout.
- Focused stack-width, palette-index, damage-lifetime, animation-backpressure,
  and controller-latch ownership regressions pass.
- Pinned Poppy hash remains
  `0ab25f241ac5040683254153c57d6f3920bec971ccd507b48a12c057635766aa`.
- Full actor ROM and copyright-free actor-disabled large-room ROM assemble
  and pass ROM audit; memory audit passes. Hosted CI is recorded on PR #13
  separately and is not native emulator acceptance.
- Python compilation, shell syntax, tracked JSON, and diff whitespace checks
  pass. No commercial payload or screenshot is committed.

This proves one source-backed actor at scale 255 using checked MSU pose bytes,
the existing SCUMM interpreter, and the existing indexed/Mode-3 renderer.
It does not certify whole-game playability, story palette setup (the static
diagnostic backdrop remains blue), costume scaling, all costumes/multi-chunk
poses, multiple actors, foreground occlusion, text/audio, or portable saves.
The current bounded underlay also requires free tail space after live metadata;
large-room/multi-actor restoration is not certified by this diagnostic.
Local 213 remains NOT_VERIFIED. The progression recovery worktree is untouched.
No selector redesign, new engine personality, or FATE-specific production
branch was introduced by these corrections.

## Integration review correction

The explicit-animation flag writes now zero-extend the actor ID before
indexing the 32-byte array. `C14_BaseX` leaves the high byte of its record
address in B; an A8/X16 `TAX` could previously index outside this array for
actor IDs 4 and above. Costume changes, explicit animation, and actor reset
share the corrected helper. The regression covers all 32 actor IDs and
nonzero adjacent-byte values. This is source-model coverage, not a claim of
native visual acceptance for every actor.

The corrected full actor configuration assembles and passes the ROM audit.
The full host suite passes 1,197 tests (12 skips), and `make validate` passes.
The prior five-frame native result above remains bound to its original ROM;
new native evidence must use the corrected build identity.
