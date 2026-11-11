# Original interaction and camera checkpoint

Source checkpoint: `fa11ae2cc54047217affddfcda3cc2103a307969`.
Draft successor PR: https://github.com/astrobleem/SNES-SAME-SCUMM/pull/15.
**Functional checkpoint accepted; responsiveness work remains incomplete.**

One cold, continuous Nexen session ran original source startup through normal
cutscene acknowledgements, opened the original verb page, selected Pick up and
the newspaper, submitted once, opened inventory, selected the acquired item,
closed with physical B, and walked through the original camera trigger.
No gameplay-state writes, synthetic story overlay, reset, or restored state
occurred in this session. The complete2203-ProgramUnit package was used.

- Source object141/verb11: owner15→1 and object state0→1, matching the isolated
  original-script host oracle. Native ObjectProgram(room=10,object=141) was
  active in the sampled action interval. This is not a full host playthrough.
- Readable source verb page, Pick up newspaper sentence and inventory page.
  Inventory has276 contrasting foreground pixels; exact glyph equality alone
  is insufficient to accept invisible black-on-black text.
- Continued walking ends at275,139 with standing chore3, room10 RUNNING,
  error0, source camera336/xstart176, checked visible crop208,0,256,144.
- Each accepted capture matches independent original background/costume/font
  interpretation, indexed pixels and PPU pixels. No CGRAM mismatch. Scope is
  a single unscaled actor and the currently implemented background/UI layers.
- Separate matching-ROM checkpoint continuation selected original back door136
  after the pan and rendered Open back door through normal controller input.
  It submitted no second action and retained acquired newspaper ownership.
  This targeting diagnostic is not spliced into the cold-session recording.

The cold session exited normally in551.275seconds under a600-second private
Xvfb process-tree deadline. The targeting continuation exited in44.888seconds
under180seconds. No owned emulator remained; unrelated processes were untouched.
Commercial captures, packages, states and detailed journals are private:
`/home/chad/SAME-private-evidence/milestone-c-20261111/playable-camera-checkpoint`.

## Exact identities

- ROM: `034b6836a59cb2fc18ce03892012bef05f5f77e8791fd3cafee43d09be788751`
- Map: `491c5c3d5085ad7c3ef12ccc8b9564f556e3afefbfdc2664f17e4f4f86a97713`
- SAMEPKG: `70564585c15538ed04b7f614b5b4d929a07eedf7a8545b510ff0ed66e9ad29d0`
- Build identity: `591b5488657101e4c5bb3d7e066cdf8ed58f1ef51a0f12d56dd27d72f73b2ff9`
- External source archive: `0f3fc396642c800069d31ab9a087b314f1bb1612d37accbe13b6013219ac94f0`

All39 non-generated assembler inputs hash-match the source checkpoint. The
isolated build has its own generated-source Git identity; it is not falsely
reported as the public commit. Evidence is never transferred across ROM hashes.

## Measured remaining latency

Emulated frames, not workstation time or raw MSU throughput:

| Boundary | Frame |
|---|---:|
| Camera-triggering walk input |8196|
| First sampled semantic arrival |8326|
| First sampled logical camera arrival |8374|
| First crop strips checked |8342–8694|
| First crop installed/publication cycle |8710–9150|
| Latest crop strips checked |9158–9510|
| Latest crop publication cycle |9526–9966|
| Actor rendered at new position |10006|
| Final settled capture |10104|

Input-to-final is1908frames. Two full checked crops account for73728bytes;
108937 total provider bytes were observed including code/other requests.
Boundaries are mostly sampled every8frames, then every1frame at final fences.
This is a measured slow pipeline, **not responsive camera acceptance**. Obsolete
intermediate crops and full-surface conversion/publication are the next bounded
optimization target. Source camera timing must remain unchanged.

For the verb menu, text generation104 was first observed committed at6952;
the complete idle raster was captured at6994. Input was6904. For the pickup
sentence, text generation131 committed by7275, versus final idle capture7317.
Do not count all observer settling as the first visible-text latency. Earlier
qualified taxi513→218 and short-walk192→69 comparisons retain their own ROMs,
inputs and limitations in PLAYABLE_PRESENTATION_LATENCY.md.

## Validation and limits

1498 local tests run,1486 passed,12 skipped; make validate,33-region memory
audit, source checks, pinned Poppy assembly and ROM audit passed. Both hosted
jobs passed on this checkpoint:
https://github.com/astrobleem/SNES-SAME-SCUMM/actions/runs/43032628646.
Hosted checks do not execute Nexen. No skipped test is native acceptance.

SELECT opens enabled original verbs, START owned inventory, D-pad/Y navigates,
A chooses/selects/submits, B closes. Source verb disable/save semantics remain
in force. The two-line page truncates names to13 encoded bytes per row.
Acquisition-ordered inventory queries, complete dynamic object images,
foreground masks, multi-actor/scaled composition, full audio/iMUSE, portable
streamed saves and physical hardware qualification remain outside this proof.
Whole-game status remains NOT_READY. No production FATE-specific hooks added.
