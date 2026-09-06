# Room-42 native controller presentation review

This is a screened source/test handoff. ROMs, savestates, captures, ATLANTIS.zip,
generated room/audio payloads, and unrelated campaign files remain local.

## Result

The previous visual claim was rejected after opening the native PNGs: the
`finaltest-clean-run2` and `visual-repro4` images were multicolored static.
The readiness gate checked state/counters/file creation but did not inspect the
emulator pixels. The harbor backdrop repair was then validated independently.

The current native run is:

- ROM: `build/controller-room42-visualfix26.sfc`
- SHA-256: `ddd8c1835f83169cbe49483a402e1f189d14b30cd3a1a22e190b09f7a9b00b6e`
- Run: `build/controller-room42-visualfix26-run1/`
- Result: validator pass; report ROM hash matches.

Every cited native PNG was opened individually:

`01-ready.png`, `02-hover.png`, `03-walking.png`, `03-opened.png`,
`04-dialogue-active.png`, `04-dialogue-complete.png`, and
`05-post-dialogue.png`.

They show the native harbor, Indy costume, cursor/selection HUD, walking
state, open locker, readable active dialogue, cleared completed dialogue, and
the room/control state after dialogue. The active dialogue capture is taken
after the printable segment reaches length 16; the completion capture is taken
after the talk layer is hidden and `talk_active=0`. Intermediate surface dumps
are not used as final visual evidence.

## Semantic/native execution

The controller-only replay uses ordinary D-pad/A/Y input. It does not write
C20, script PCs/slots, the sentence mailbox, or object state from the
validator.

`(3,490,0)` is submitted through the controller sentence path. Actor movement
reaches `(218,104)`, walkbox 10, moving becomes zero, and object 490 changes
from state 0 to 1. The opened state selects authored Inspect; `(9,490,0)` is
submitted through the same path. Dialogue becomes active with
`talk_segment_length=16` and `overlay_pixels_nonzero=142`, then completes with
error 0. A normal post-dialogue RIGHT edge advances the cursor, proving input
remains usable.

## Generic fixes in this pass

- The controller fixture retains logical C23 message ownership and timing but
  hides the committed talk layer on completion; it no longer leaves stale
  dialogue pixels merely because the bounded presentation prefix was used.
- Native capture uses a non-black harbor landmark `(0,40,64,104)` instead of a
  black letterbox corner, and waits for a substantive printable dialogue
  segment rather than accepting the two-glyph encoded-control prefix.
- The source-cooked actor and object image are composed through the existing
  indexed surface. The cursor is drawn into the same composed surface before
  the single backend present transaction; cursor movement invalidates its
  cached render state. The helper is entered with `JSL` and returns with
  `RTL`.
- The generated overlay service still falls through ordinary surface/palette/
  present packets to the selected backend; this packet does not alter that
  accepted architecture.

## Build and validation

Build environment: `tools/build_snes.sh`, SCUMM v5, startup42, room visual,
controller fixture, Mode-3 indexed surface, BG2 overlay, SA-1/BW-RAM carrier,
ATLANTIS.zip as local source corpus, and the prebuilt Fate TAD profile. Poppy
SHA-256: `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.

Replay command:

```text
PYTHONPATH=src python3 -u tools/validate_scumm_room42_controller_nexen.py \
  --rom build/controller-room42-visualfix26.sfc \
  --output build/controller-room42-visualfix26-run1 \
  --port 44441 --startup-frames 5000
```

Focused command:

```text
PYTHONPATH=src python3 -m unittest \
  tests.test_scumm_v5_controller_fixture tests.test_scumm_v5_engine \
  tests.test_scumm_v5_room tests.test_m25a_validator -q
```

Result: 164 tests pass. Python compilation and `git diff --check` pass.

## Scope status

Semantic/controller execution and native presentation are separately proven
for this ROM/run. The broader main worktree remains dirty by design. This
review branch contains only screened source files, focused tests, and this
report; no game-derived artifacts are included.
