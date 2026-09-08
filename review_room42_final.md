# SAME room-42 surface/controller final review

Status: CLOSED. This document supersedes the accumulated room-42 WIP reports.

## Provenance

- Source corpus: FULL `/home/chad/ATLANTIS.zip`; member hashes are recorded in
  the local build identity. DEMO data is not used for startup42.
- Poppy issue: `TheAnsarya/poppy#376`.
- Focused Poppy PR: #393. SAME pins commit
  `8ee859b33bad94e3a01e9c78026803e482292801`; fixed DLL SHA-256
  `34514923ea8dc79a4664fa327f583cee8e8daa64e3be47518ae22ba5a2c7608e`.
- Accepted SAME ROM SHA-256:
  `9370b4acb6ff649b008c5e4135771b24dc89fb74be798e5bfbc2cbda7aa8702f`.
- Build identity SHA-256:
  `3b2678c61632ca3b90fe2e0f52088da25d10d28c9c73466f191c2125ee698b5e`.

## Implementation accepted

- Poppy conditional-EQU/direct-page semantic sizing fix is pinned.
- SCUMM actor cooker uses source column-major cel decoding and directional
  placement.
- SCUMM remains blind to PPU, BG2/Mode3, BW-RAM, DMA, VRAM, CGRAM, and OAM.
  Indexed composition uses the target-neutral SAME surface service.
- FindVisual reloads the requested room key for each directory comparison.
- Bounded actor damage restores the old/new union and publishes one atomic
  damage transaction. Busy restore retry remains separate from PRESENT retry.
- Desired actor visual state is published separately from rendered cache state;
  pose-aware invalidation covers position, movement, facing, costume,
  visibility, and animation selection. Failed PRESENTs do not commit cache
  state.

## Target evidence

Explicit FULL startup42 replay reaches room 42, actor room 42, readiness 1,
and error 0.

Natural moving witness:

```text
actor              (157,101)
moving             != 0
destination        (218,104)
pose               1
damage             (65,86,32,64)
accepted PRESENT   generation 3
committed          generation 3
backend            idle/unlocked
FIFO               empty
```

The emitted pose contains 503 nontransparent pixels. The committed indexed
surface crop has 481 exact matches; 22 pixels are documented legitimate
room/object/cursor overlaps, with zero unexplained pixels. The native walking
capture was inspected and shows coherent Indy and an intact harbor without
the former horizontal stripe corruption.

The complete normal controller replay passes: `(3,490,0)` moves the actor to
`(218,104)`/walkbox 10, object 490 changes `0 -> 1`, inspection dialogue
starts and completes, post-dialogue input remains usable, and error is 0.

## Validation

- `PYTHONPATH=src python3 -m unittest discover -s tests -q`: **525/525 PASS**.
- `python3 -m py_compile` for changed Python tools: PASS.
- `git diff --check`: PASS.
- `POPPY_ROOT=/home/chad/poppy-jsl-address-fix PYTHONPATH=src python3
  tools/lint_poppy.py runtime/snes/main.pasm`: PASS, 61 files / 4667 labels.
- `python3 tools/audit_snes_rom.py ... --carrier sa1_bwram`: PASS,
  4 MiB ROM, reset `$8000`, NMI `$80E2`, IRQ `$810D`.
- Explicit FULL startup42 Mesen/Nexen replay:
  `build/poppy-fixed-actorabi7-final-run/`: PASS.

ROMs, savestates, ATLANTIS.zip, generated Fate payloads, and unrelated dirty
campaign files are intentionally excluded from this publication. Historical
failed captures remain local as regression witnesses.

Next goal: generic source-driven cursor/object hit testing, authored verb
selection, and the normal SCUMM sentence queue. Room-42-specific graphics
work is closed.
