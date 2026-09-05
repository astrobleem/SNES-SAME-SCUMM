# Focused message/scheduler review handoff

This file is a screened review summary. It contains no ROM, savestate,
archive, generated game resource, or embedded game-byte payload.

## Scope

- Review branch: `review/hoist-message-lifetime`
- Broad implementation commit intentionally excluded: `3c88f54516bb04700ce353fb51e1d4f8c0627e6e`
- Current working-tree implementation remains in the Fate repository and is
  not copied into this review branch.

## Corrected logical-message contract

Headless mode removes presentation ownership only. It does not clear
`SAME_SCUMM_C23_MESSAGE_COUNT`, `SAME_SCUMM_TALK_ACTIVE`, or
`SAME_SCUMM_TALK_HAVE_MSG` at delivery. The normal Talk service retains the
logical message, delay, continuation, and published-clear ordering. The far
wait path saves `SAME_SCUMM_TALK_WAIT_PC` before decoding and restores it to
`SAME_SCUMM_PC` while the talk state remains active.

Relevant implementation files:

- `runtime/snes/engines/scumm_v5_matrix_far.pasm`
- `runtime/snes/kernel/memory.pasm`
- `tools/validate_scumm_message_wait_nexen.py`
- `tools/validate_scumm_message_talk_nexen.py`
- `tests/test_scumm_v5_engine.py`

The removed duplicate main-opcode rewind is intentionally not claimed here;
the production far polling implementation is the single contract.

## Focused evidence

Host validation:

```text
PYTHONPATH=src python3 -m unittest tests.test_scumm_v5_engine -q
Ran 124 tests ... OK
```

Target long-message fixture:

- ROM: `build/same-message-long-v3.sfc`
- SHA-256: `bb6eabbd834d129345f475e2bc02fa05435461a5c5775a50503eed18aae408ac`
- Evidence: `build/m25a-validator/message-long/message-wait-v3.json`
- 51 logical bytes; `FF 03` at logical position 36, beyond the 32-byte
  presentation window; wait held at PC 58; logical completion tick 64;
  continuation at slot PC 66; error 0.

Startup42 compressor/hoist continuation:

- ROM: `build/same-startup42-hoist-debug91.sfc`
- SHA-256: `b270cf83dbc39407c28d945c2fbcb0489c2ebcccf38d3fd25bafa4756c12fa53`
- Evidence: `build/startup42-debug91-hoist4/report.json`
- Both semantic submissions were acknowledged (`sentence_sent=true`,
  `sentence2_sent=true`), error remained 0, object 492 reached state 1 and
  object 500 reached state 0. The trace includes the authored room-82 visit
  and return to room 42. A final slot snapshot is not used as proof of
  sentence non-execution.

Detailed earlier same-ROM hoist effects are retained in:
`build/startup42-debug89-compressor-hoist/report.json`, ROM SHA
`54142e89acbdbaae89feac1b002257207e6aec03cad4e9d2c0c5692225a00a20`.

## Review claim

The evidence supports delayed logical message ownership and normal
`waitForMessage` release in headless acceptance mode, including a segmented
control beyond the compact presentation window. It does not claim that the
compact headless presentation buffer stores the complete long message.
