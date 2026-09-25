# Phase 6L acceptance

Phase 6L is closed. The authored Fate path is accepted from a fresh power-on:

```text
room 49 -> global script 2 -> object 596 / LSCR 211
         -> sound-82 fallback -> $02D9 -> $02DE
         -> generic $24/$64/$A4/$E4 loadRoomWithEgo -> room 63
```

The transition uses the generic SCUMM v5 lifecycle, mailbox/resource delivery,
C4 scheduler, and bounded C25 audio path. Room 63 ENCD completes normally and
global script 151 enters its authored delay/movement/message loop. At the
accepted stable observation actor 1 is at `(430,140)`, walkbox 5, stationary;
the camera lifecycle is running normally. Sound 80 is owned, sounds 81 and 82
are inactive. The retained `$010C` command is canonical: room 63 queues hook 8
and the sound-82-false branch intentionally does not issue the later `$0110`
and flush commands.

The accepted target was run for 10,000 emulator frames with `error=0`.

```text
ROM SHA-256: fddea1f7b877bbdb5f0bc9d9ca9bf8a13df4d4cc319a708410df178014b3a555
```

Focused validation passed: 460 Python tests, Poppy lint, LoROM audit, and the
authored room-49-to-room-63 Nexen run. The legacy `make m23c` target is tracked
separately as layout-compatibility debt: its old non-relocated M23C build does
not accommodate the relocated M25 layout and is not a reason to roll back the
accepted relocation.

## Next authentic boundary

No player action is required by the accepted room-63 script at this boundary.
The next gameplay boundary is the normal SCUMM sentence/input dispatcher after
the periodic global-151 loop; no synthetic sentence is introduced here.
