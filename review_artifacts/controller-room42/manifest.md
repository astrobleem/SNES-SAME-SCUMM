# Room-42 native visual WIP review

## Current acceptance status

The corrected normal replay is semantically complete and visually shows the
harbor, Indy, HUD, locker transition, active dialogue, cleared dialogue, and
post-dialogue control. Actor-fidelity proof remains pending: the validator now
uses the backend's actual accepted-PRESENT fence, but the first walking request
can be rejected while the backend is locked. The pre-fence partial surface is
preserved as a FAIL witness. A long fence can commit after walking completes,
which is not an exact walking-pose witness. The overall visible milestone is
therefore still WIP, not PASS.

`fresh-corrected-normal14/` is the latest matching-ROM normal replay. Its ROM
is `bbfabe380ed5b1c305af8174ab191bc79eb77e117e09a87be64df58b266f82d7` and its
semantic report ends with `result: pass`. Its native PNGs were opened during
review. `03-walking-surface.ppm` is a committed-generation capture only when
the new actor PRESENT is accepted; earlier `normal2`/`normal4` captures are
explicitly pre-retry negative witnesses.

This is a non-final, independently inspectable evidence packet. Images are
unchanged native emulator PNGs; none were repainted, cropped, filtered, or
replaced with host-rendered output. Fate imagery is intentionally included for
review under the requesting author's explicit instruction.

## Runs and ROMs

* `visualfix26-run1`: ROM SHA-256 `ddd8c1835f83169cbe49483a402e1f189d14b30cd3a1a22e190b09f7a9b00b6e`.
  The run report records stages at frame 128 and the semantic states below.
* `visualfix9-run`: ROM SHA-256 `8ea2ff47f9165356cc22956bf0560352f0bb97aae3fd8e3a997cdb6d08b9e4f2`.
  Preserved because it contains visibly defective dialogue presentation.
* `finaltest-clean-run`: the run did not emit a ROM hash in its report/log;
  identity is therefore `UNKNOWN`, not inferred from another run.
* `native-final5`: current incomplete run on the current source state; the
  emulator log is included, but it did not produce dialogue captures.

## Native captures: visualfix26-run1

All files below are 256x239 RGBA PNGs. The visualfix26 report identifies the
ROM and semantic run; exact per-file SHA-256 is recorded here.

| file | frame/state | assessment | SHA-256 / visual observation |
|---|---|---|---|
| `native/01-ready.png` | frame 128, room 42, actor idle, locker closed | background/HUD PASS; actor fidelity UNKNOWN; overall FAIL | `06b61c8ce16055d02130ae1b5042bcaf23718d27c30faa503ba3201aca0799ec`; harbor, Indy presence, locker and OPEN LOCKER HUD visible, but costume fidelity is not yet proven |
| `native/02-hover.png` | hover/action selection | background/HUD PASS; actor fidelity UNKNOWN; overall FAIL | `6ad84394a2183e68dd8eb69c3c303008aa9e8094e2197f1747deab048286c8ba`; harbor and OPEN LOCKER visible, actor comparison pending |
| `native/03-walking.png` | authored locker movement | background/HUD/movement PASS; actor fidelity FAIL; overall FAIL | `4c46b9932ae5b8034ce9a62fe36ba8f17e28a94d9978ed5fb515cc5faabbee45`; recognizable movement and WALKING control, visibly malformed Indy costume |
| `native/03-opened.png` | locker open, inspect available | background/HUD/state PASS; actor fidelity UNKNOWN; overall FAIL | `be671132e27737394612ec06e7566eed3eccb21313c543eb9c6bdb340a5bc5f5`; opened locker and INSPECT visible, actor fidelity unaccepted |
| `native/04-dialogue-active.png` | authored dialogue active | background/dialogue PASS; actor fidelity UNKNOWN; overall FAIL | `727a2ed4fed231c56f92ec80b67be03f69030a8f64a0a14576b3f5d82ef25ce64`; readable authored text visible, actor fidelity unaccepted |
| `native/04-dialogue-complete.png` | dialogue complete | UNKNOWN | `36b36b24570e4c68f6c92b45c9d4e2d157851a73f42507b5143832b552a93fc1`; room/actor visible, no dialogue at this instant |
| `native/05-post-dialogue.png` | post-dialogue control | UNKNOWN | `36b36b24570e4c68f6c92b45c9d4e2d157851a73f42507b5143832b552a93fc1`; byte-identical to dialogue-complete capture |

## Defective native evidence

* `../visualfix9-run/native/04-dialogue-active.png`: ROM
  `8ea2ff47f9165356cc22956bf0560352f0bb97aae3fd8e3a997cdb6d08b9e4f2`,
  run `build/controller-room42-visualfix9-run`; visibly corrupted/striped
  actor/presentation and blocked/overlaid dialogue. SHA-256:
  `91eec7505749ca5dd2cd2b1b7e5ad5a8c23066fa0fc11da0a1c5793ba2cd9a8d`.
* `../finaltest-clean-run/native/01-ready.png`: ROM identity UNKNOWN in the
  source run metadata; visibly multicolored static rather than room 42. SHA-256:
  `36a259b50cc383a84def172ea6b4903f9abcb3e13310d8600498208bc6444c30`.

Actor-fidelity rule: every visualfix26 capture containing Indy is UNKNOWN for
actor fidelity unless matched against a correct source pose. The walking frame
is the explicit FAIL witness. The harbor/background and HUD assessments do not
upgrade the overall frame to PASS.

## Actor-pipeline audit

`pose-audit/` contains source-decoded individual cels, host composites, the
old malformed cooker composites, corrected cooked composites, and the complete
pose/cel manifest. Its README records the exact costume/facing/frame identity,
hashes, and stage results. The first proven divergence is the cooker: corrected
host and cooked indexed canvases match exactly for idle and walking. No exact
indexed-surface capture was available for these pose identities yet; native
walking remains a FAIL witness, not a repaired result.

## Actor-pipeline audit

`pose-audit/` contains source-decoded cel PNGs, independently composed host
poses, the old cooker composites, actual emitted corrected `.bin` frames, and
the full pose/cel manifest. Its README records the exact hashes and stage
results. The old cooker was the first demonstrated divergence; the actual
corrected emitted idle/walk frames match the host indexed composites exactly.

Fresh corrected ROM downstream evidence is under `fresh-corrected-rom/` and
`fresh-corrected-surface/`, ROM SHA-256
`bbfabe380ed5b1c305af8174ab191bc79eb77e117e09a87be64df58b266f82d7`. The
opened standing surface/native captures and walking native capture show a
coherent actor. The exact walking surface/native crop correspondence remains
formalization work, so actor fidelity is not yet final PASS.

The validator now includes a no-advance target indexed-surface dump at the
walking capture boundary, with surface/backend generations and scene metadata.
This is observational diagnostics only and does not add hardware knowledge to
SCUMM.

## Intermediate, not native acceptance evidence

`intermediate/01-ready-surface.png` is a 256x224 RGB indexed-surface export
from `build/controller-room42-final-probe`; SHA-256
`e037e6e84d6f1a418a5205636d17d21a13ca7c300a142be0289e901369207725`.
It is labeled intermediate and is not evidence of the SNES/emulator display.

## Semantic context

The associated semantic controller path reported `(3,490,0)`, actor movement
to `(218,104)` / walkbox 10, object 490 state `0 -> 1`, `(9,490,0)`, error 0.
This packet does not upgrade the visual milestone to accepted: the current
source-state controller run (`native-final5`) stopped before authored inspect
mode was published.

## Reproduction

Build profile used by the current controller validator:

```sh
SAME_FATE_DEMO_ARCHIVE=ATLANTIS.zip SAME_SNES_ENGINE=scumm_v5 \
SAME_SNES_PROFILE=examples/profiles/templates/fate_of_atlantis_demo.json \
SAME_BUILD_M24RB=1 SAME_BUILD_SCUMM_M23A=1 SAME_BUILD_SCUMM_M23B=1 \
SAME_BUILD_SCUMM_M23C=1 SAME_BUILD_SCUMM_PHASE6L_A1D=1 \
SAME_BUILD_SCUMM_M25A_VALIDATOR=1 SAME_M25A_VALIDATOR_CASE=startup42 \
SAME_BUILD_SCUMM_SCENARIO_FIXTURE=1 SAME_SCUMM_SCENARIO_START_ROOM=42 \
SAME_BUILD_SCUMM_M25_MOVEMENT=1 SAME_BUILD_SCUMM_ROOM_VISUAL=1 \
SAME_BUILD_SCUMM_CONTROLLER_FIXTURE=1 SAME_SNES_CARRIER=sa1_bwram \
SAME_SNES_VIDEO_BACKEND=mode3_surface SAME_SNES_VIDEO_OVERLAY=bg2_index4 \
bash tools/build_snes.sh
```

The WIP is intentionally not a final acceptance claim. Reviewers should open
the native PNGs above and compare them with the semantic reports.
