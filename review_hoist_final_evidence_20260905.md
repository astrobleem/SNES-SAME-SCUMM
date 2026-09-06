# Same-ROM compressor/hoist completion evidence

Screened review evidence only. No ROM, savestate, ATLANTIS bytes, generated
game payload, or unrelated campaign files are included.

## Implementation identity

- Source tree: SAME main worktree, generator and runtime changes as recorded in
  `session_checkpoint.md`.
- Final ROM: `build/same-hoist-final.sfc`.
- SHA-256: `8484361a7d2f93d5046ed6401c91ab32c336680eb4e6187365d7bb9376f957d1`.
- Source corpus: `ATLANTIS.zip` (local only).
- Poppy: `715b14431478b62433498cc516c1cbbb8f418c1d7b39a8e71098ed98d9c9167e`.
- Build output was isolated; matching reports were produced under
  `build/hoist-final-*` and are local-only.

## Root cause and generic fix

The first corrected build proved the old room-82 observation was not an F5
decode error. The room entry program completed to its terminal PC, while the
shared selector became neutral and slot zero still held the live generated
program. The next room lifecycle pass rehydrated slot zero from PC 0. A broad
common-boundary save was tested and reverted because it perturbed startup.

The retained fix is in `runtime/snes/engines/scumm_v5.pasm`: at the room
slot-zero lifecycle boundary, only an outer, non-nested neutral selector with
a live slot-0 owner is reconciled with the authoritative slot program before
the slot is saved/rehydrated. Nonzero selector mismatches remain fail-closed.
The generated-program bank fix is in
`tools/generate_snes_cooked_rooms.py`: executable programs are packed into
explicit LoROM banks so long `Program_*` fetches retain their emitted bank.

## Target execution

Fresh exact-ROM run:

```
startup42 -> room 42, error 0
(8,492,0) -> object 492 state 1 / running compressor
(8,500,497) -> LSCR 207 / hoist
```

Observed in `build/hoist-final-hoist500/report.json`:

- object 500 state `1 -> 0`, frame 1567;
- bit 444 packed-byte change, frame 1598;
- room 82 entry and error-free room-82 execution;
- room 82 phase 5 reached, then authored return to room 42 at frames 1929–1930;
- final error 0, cutscene depth 0, C20 empty.

This proves execution, not static opcode presence. The final snapshot is room
42 after the authored return; continuing delayed scripts remain a normal
runtime state, not an asserted full-game quiescence.

## Exact commands

Build flags and the full commands are retained in the project checkpoint. The
focused host validation was:

```
PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine tests.test_scumm_v5_room tests.test_m25a_validator
```

Result: 151 tests, OK. ROM audit and `git diff --check` passed.
