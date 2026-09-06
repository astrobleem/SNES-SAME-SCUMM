# Room-42 controller scene review update

This screened handoff contains only source/test evidence for the controller
playable room-42 locker scene. It contains no ROM, savestate, ATLANTIS archive,
room payload, generated game bytes, or emulator capture.

## Source identity

- Scenario profile: `startup42`, source corpus `ATLANTIS.zip` (local only).
- ROM under test: `build/controller-room42-finaltest.sfc`.
- ROM SHA-256: `4a98d260b33b60d9db45d090647fc9e4a76f2d8481f1a5265b315820f7d44676`.
- Build used the existing `tools/build_snes.sh` SCUMM v5/M24RB/M23A/M23B/M23C,
  scenario-fixture, controller-fixture, room-visual, Mode-3 surface, SA-1/BW-RAM
  carrier, Fate TAD prebuilt-data configuration.

## Target execution evidence

Command:

```text
PYTHONPATH=src python3 tools/validate_scumm_room42_controller_nexen.py \
  --nexen /home/chad/NexenTrace/run/nexen-wrapper \
  --rom build/controller-room42-finaltest.sfc \
  --output build/controller-room42-finaltest-clean-run2 \
  --startup-frames 500 --port 44247
```

The clean replay passed. It observed: room-42 visual readiness; cursor moved
to locker hotspot; A selected object 490; Y selected authored Open; A submitted
`(3,490,0)` through the normal sentence mailbox; actor reached `(218,104)` in
walkbox 10 and became idle; object 490 changed `0 -> 1`; the controller waited
for the semantic inspect mode; A submitted `(9,490,0)`; dialogue became logically
active and then completed; final error was 0 and controller submissions were 2.

The replay captures `01-ready.png`, `02-hover.png`, `03-opened.png`,
`04-dialogue-complete.png` and corresponding local surface PPMs. These derived
captures remain local.

## Focused implementation claims

- `scumm_v5_controller_far.pasm` is fixture-gated. It consumes ordinary SNES
  input, draws the bounded scene HUD through the existing talk overlay, and
  publishes only the normal sentence API fields. It never constructs C20,
  writes script PCs/slots, or mutates object state directly.
- `kernel/frame.pasm` invokes the fixture controller after the normal SCUMM
  frame; the next normal frame consumes the API mailbox.
- The source-backed startup actor setup now calls the generic
  `ScummV5_PutActor_FarCall_DefaultActor` before applying costume 2 and the
  authored room-42 position. This prevents inherited zero speed/scale from
  making a valid locker route appear stalled.
- The controller encodes object 2 as zero, preserving the authored tuple for
  both Open and Inspect.
- `tests/test_scumm_v5_controller_fixture.py` covers the tuple encoding,
  production mailbox seam, controller lifecycle assertions, and generic actor
  default initialization.

## Validation

```text
PYTHONPATH=src python3 -m unittest \
  tests.test_scumm_v5_controller_fixture \
  tests.test_scumm_v5_engine tests.test_scumm_v5_room \
  tests.test_m25a_validator -q
PYTHONPATH=src python3 -m py_compile \
  tools/validate_scumm_room42_controller_nexen.py
git diff --check
```

Result: 154 tests passed; Python compilation and whitespace checks passed.

## Scope exclusions

The broad campaign worktree, ROMs, savestates, ATLANTIS resources, generated
room/audio payloads, DOCX files, and unrelated documents are intentionally not
included in this review branch.
