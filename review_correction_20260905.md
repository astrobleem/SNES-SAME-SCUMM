# Corrected hoist review handoff

This source-only correction supersedes stale claims in the earlier packet.

## Message lifetime

The fixture does not auto-clear messages at C23 delivery. C23 accepts the
decoded stream, then `Talk_Begin_Far`, `Talk_FrameBegin_Far`, and
`Talk_FrameEnd_Far` retain logical ownership, delay, continuation, and
published-clear ordering. Headless mode omits only the presentation owner.

Focused source checks cover long encoded text beyond the 32-byte presentation
window, embedded `FF 03` controls, long-message lifetime, selected-slot save,
and per-launch sentence fetch identity. The host suite passes 122 tests.

## Same-ROM execution evidence

ROM SHA-256:
`75ce5647cad61948b028ae980a9bc08953883273994a43922cf64d388613a03f`.

The fresh startup42 run consumed `(8,492,0)`, entered LSCR 201, consumed
`(8,500,497)`, entered LSCR 207, observed object 500 state `1 -> 0` at frame
958, bit 444's packed-byte change at frame 1016, and authored `loadRoom(82)`
at frame 1087, with `error=0`. Room-42 execution included logical message
lengths 52, 99, and 135 with encoded controls. The JSON evidence remains local
at `build/startup42-hoist-debug38-effects/report.json` and is deliberately not
copied into this branch.

Validator-profile M24RB fields (`state=0`, `trigger_marker=1`,
`deferred_count=1`) are profile diagnostics only. The room-82 transition is
independently witnessed from LSCR 207.

## Screened implementation excerpt

In `runtime/snes/engines/scumm_v5_matrix_far.pasm`, the fixture overflow path
advances `SAME_SCUMM_C23_RAW_INDEX`; `Talk_Begin_Far` retains logical length
past the compact presentation window; and `Talk_Continue_Far` consumes `FF 03`
while preserving caller status. In `runtime/snes/engines/scumm_v5.pasm`, the
common opcode-success boundary and C4 selected-slot restoration preserve
slot-owned program identity/PC across nested execution, byte index width is
reasserted for slot scans, and C25 diagnostics enter the required accumulator
width. These are source-only excerpts; no broad implementation or game data is
included.
