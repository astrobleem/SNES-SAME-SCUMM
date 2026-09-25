# Authentic Fate `$30/$01 setBoxFlags` report

Status: **complete**. This slice implements only canonical SCUMM v5
`$30 matrixOps` subopcode `$01`, advances authentic room-49 LSCR 200 through
both consecutive flag writes, and stops at the next unsupported semantic.
M24R-B remains paused.

## Corrected source evidence

The M25 diagnostic text `30 04 0C 80` was a transcription error. The
hash-bound authentic LSCR 200 (`dc34f2d549455fbd6ee30eb057470b39e97e4544ff3cbe49d94424158e3cbc6c`)
begins:

```text
+$0000  30 01 0C 80    setBoxFlags(12, $80)   -> +$0004
+$0004  30 01 14 80    setBoxFlags(20, $80)   -> +$0008
```

`tools/validate_scumm_m25_authentic_next_nexen.py` now decodes the cooked
room-49 record, resolves LSCR 200, verifies its identity, and derives this
eight-byte prefix directly. The earlier emulator stopped after fetching `$30`
at PC `+$0000` and recorded PC `+$0001`; it never fetched the subopcode or
operands. The erratum is also recorded in
`docs/M25_AUTHENTIC_ONE_BLOCKER_REPORT.md`.

## Walkbox provenance and mutation

The source ROOM identity is
`fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6`.
Its `BOXD` chunk starts at ROOM-relative `+$0168` (original
`PLAYFATE.001` offset `$049C47`), has encoded length 470, and decodes to 23
authentic walkboxes. The generated profile data copies only their source-bound
initial flag bytes into mutable WRAM when the room record is activated.

| Box | Authentic geometry | Mask | Scale | Initial flags | Final flags |
|---|---|---:|---:|---:|---:|
| 12 | `(535,137) (600,137) (600,137) (535,137)` | 1 | `$8000` | `$00` | `$80` |
| 20 | `(366,82) (383,82) (449,108) (422,108)` | 3 | `$8003` | `$00` | `$80` |

Only the mutable raw flag byte changes. No BOXM rebuild, geometry mutation,
actor movement, path recomputation, or interpretation of bit `$80` occurs.

## Implemented semantic

Both host and SNES perform:

```text
fetch subopcode
require (subopcode & $1F) == 1
box   = getVarOrDirectByte(PARAM_1 / bit $80)
flags = getVarOrDirectByte(PARAM_2 / bit $40)
setBoxFlags(box, flags)
```

The write replaces the prior byte. Box `$FF` and a missing box table follow
the authoritative v5 no-op policy; a regular out-of-range box fails closed.
Subopcodes `$02`, `$03`, `$04`, and unknown forms remain unsupported.

The production handler is a coherent cold far-bank closure in
`runtime/snes/engines/scumm_v5_matrix_far.pasm`; the generic dispatcher and
interpreter state remain in `runtime/snes/engines/scumm_v5.pasm`. Authentic
initial flags are emitted by `tools/generate_snes_cooked_rooms.py`. Synthetic
matrix programs remain available only in non-authentic-room builds, preserving
all established M19-M23 fixture IDs.

## Fresh-power-on authentic result

The run used normal resource lookup, room lifecycle, and scheduler execution
with zero debugger writes. It reproduced the accepted ENCD/global 144/global
145/music/startScript chain, entered authentic LSCR 200 as program `$D2` in
slot 4, and recorded:

```text
PC $0000 -> $0004: subop $01, box 12, flags $80, $00 -> $80
PC $0004 -> $0008: subop $01, box 20, flags $80, $00 -> $80
```

The mutation count is exactly two; room generation and nested scheduler
ownership remain intact. Evidence is in
`build/m25-matrix/evidence/report.json`.

## Next authentic blocker

Execution continues normally through LSCR 200 `+$0008`'s authentic branch to
`+$0119 actorOps`, `+$0134 setClass`, `+$013E move`, and
`+$0143 putActorInRoom`. It then fails closed at:

```text
room.49/LSCR.200 +$0146
01 0A 47 02 88 00
putActor(actor 10, x=583, y=136)
```

Surrounding authentic bytes (`+$0138..+$0157`) are:

```text
8D 00 01 85 00 FF 1A A3 00 D9 00 2D 0A 31 01 0A
47 02 88 00 11 0A F9 07 4E 02 00 5D 50 02 01 A0
```

The existing engine already has bounded actor records and room ownership, and
the immediately preceding `$2D` places actor 10 in room 49. The blocker is an
opcode implementation gap for canonical `$01 putActor`; this slice does not
implement or pre-judge its positioning/movement side effects.

## Validation

- 330 unit tests pass (328 prior plus two host matrix tests).
- Copyright-free host and SNES fixtures cover direct and variable operands,
  independent boxes, exact `$80`, replacement, missing/invalid boxes,
  instruction boundaries, and fail-closed subopcodes `$02/$03/$04`/unknown.
- Repository validation and Poppy lint/source traps pass.
- M25A's four dedicated nested-script validators pass.
- M23B positive and negative fresh-emulator gates pass after one capture-jitter
  rerun; logical/script evidence was unchanged on both runs.
- Integrated assembly and ROM audit pass.

Final integrated Fate ROM SHA-256:

```text
944efd94614fa2673770d82e2c494881588e9ccd95146dbb989fbd05655bba48
```

The production semantic necessarily changes rebuilt integrated identities.
Rebuilt M23B positive and negative ROM SHA-256 values are respectively
`5cd29de264570d1d506d93c9013b05325c585c03cf4fe89d8a965458f3f02764`
and `12de36d6717582f322fa25accf28f5df0a9db891b4be9e564351ed9ebc70d015`.
Accepted historical identities remain recorded in their milestone reports;
newly rebuilt artifacts necessarily carry the production semantic addition.

The same shared production addition also necessarily changes rebuilt M25A
validator ROM identities: normal
`44f0af99d3cfcfcce1cdda2b28bafccf481f9a6f001f1876d411ce473ffda08c`,
depth `0741540ebba9c052924be689bf0d95f278f37454429afed5616d2e3addeed4b7`,
missing `2dcadc27e7590915c1c996b8313cc556cf860ae749d89ff38290125a86e25552`,
and outer `9d1bda17c4fa06a6d0dc8dd94cd2a6536c848d45fd0b94c13ba7c9c466bc903c`.
All four fresh-emulator semantic gates pass.

No new timbre approval required.
