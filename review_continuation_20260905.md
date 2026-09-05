# Hoist continuation evidence

This review-only note contains no game resources, ROMs, savestates, or
generated payloads. The implementation remains in the private working tree.

## Message lifetime

The fixture-only C23 message auto-clear was removed. Headless mode now retains
logical ownership, delay, continuation controls, and published-clear ordering;
it suppresses presentation ownership only. The focused target run is
`build/m25a-validator/message/message-wait-debug80.json` against ROM
`0508472287ba26094af1a35b4b8c0e967419a8a3acb934e1ac4fe6e75cfe5799`.
It observes yielded slot PC 9, logical completion at tick 15, clear on the
following boundary, and continuation variable 10 set to 1. Host source tests:
`PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q` (123 pass).

## Exact-ROM hoist control

ROM `build/same-startup42-hoist-debug38.sfc`, SHA-256
`75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`, was
run without rebuilding or loading a mismatched state:

`PYTHONPATH=src:/home/chad/Mesen2/python python3 tools/validate_scumm_startup42_nexen.py --nexen /home/chad/NexenTrace/run/nexen-wrapper --rom build/same-startup42-hoist-debug38.sfc --output build/startup42-hoist-debug38-continuation --frames 3000 --light --atomic-reset --sentence 8 492 0 --sentence2 8 500 497 --port 45290 --pre-event-trace-start 99999`

Observed: compressor sentence consumed; hoist sentence dispatched; bit-444
writes occurred at frames 721 and 1091; room 82 installed and continued; at
frame 3002 error was 0, cutscene depth 0, C20 empty, and active scripts were
the authored delayed LSCR 75 and LSCR 208. Final actor snapshot was
`(345,0)`, walkbox 255, idle.

## Current-source caveat

Fresh debug84/debug86 builds are not accepted hoist evidence: debug84 is
startup-safe but leaves the first sentence instance at PC 0 without a later C4
pass; a global `$AE` scheduler rewind reproduced room-0/bootstrap behavior and
was removed. No review claim treats those experimental builds as passing.
