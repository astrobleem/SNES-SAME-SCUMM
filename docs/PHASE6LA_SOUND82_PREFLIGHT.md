# Phase 6L-A — authentic sound-82 prerequisite adjudication

Status: **hard stop after mandatory Phase A; classification A**.

The bounded composite remains useful prior work, but the authentic target has
not reached its producer.  Phase B is therefore not authorized by this gate.

## Corrected Phase 6K scope

Phase 6K proved the far/cold `$4C` dispatch into the common C25 handler and the
isolated empty-queue FLUSH packet.  Its validator did not sample LSCR 211 at
the pre-flush boundary: `queue_before` was hardcoded, and a synthetic M23C
room-63 transition was accepted.  The report and validator now say so.

## Source provenance

* archive: `/home/chad/fatedemo-box.zip`, SHA-256
  `558cc436cebed658ad12bc64152efa19490e0327f89ec97acfb108e8d438d798`
* `FATEDEMO/PLAYFATE.000`: 12,030 bytes, SHA-256
  `4e277158329edab802619ea3ef91c3f6ecec04c3fab6b67f44d275fc5f9b65a9`
* `FATEDEMO/PLAYFATE.001`: 929,852 bytes, SHA-256
  `e3bb0ad591c8a633377ad6219eff700517a144effb6f3944dcce31bb3ae43240`
* room 49 begins at decoded file offset 301,791, length 80,351, SHA-256
  `fbf234f2ffe3530ba365980abfae556636d83e5cada9bdc649c43d4cce7242f6`
* cooked room record: 82,535 bytes, SHA-256
  `7f87742246295b430ead21b50872f046d005620d5f5b1f3a24126b8b22881328`
* LSCR 208 chunk: decoded file offset 372,057, room-relative offset
  70,266, chunk length 7,450, payload length 7,441, SHA-256
  `2c84fa24e6e6c37c353cc08cfb2d94b78cc2a27be39cdc161b1131f480cd7876`.
  It is generated as the room-owned LSCR 208 program (historical program
  identity `$DA`) at cooked-record offset 72,418.

## Authentic caller chain

Room-49 ENCD does not directly start LSCR 208.  Its tail stores 204 in
`Var[164]` and starts LSCR 200.  The source-owned direct caller is LSCR 204:

```text
0000 48 B0 00 02 00 06 00    if Var[176] == 2, branch to 000D
0007 0A CE FF                startScript(206, [])
000A 18 1A 00                jump 0027
000D 48 B0 00 0A 00 06 00    if Var[176] == 10, branch to 001A
0014 0A CD FF                startScript(205, [])
0017 18 0D 00                jump 0027
001A 48 B0 00 0B 00 06 00    if Var[176] == 11, branch to 0027
0021 0A D0 FF                startScript(208, [])
0024 18 00 00                jump 0027
0027 A0                      stopObjectCode
```

The target's existing M24R-B integrated evidence registers LSCR 208 in slot 1
with PC zero, but then resumes the room-entry owner and fails at runtime PC
`$007D` with `SCUMM_ERR_SCRIPT ($0B)`.  LSCR 208 never executes.  The old host
validator is diagnostic only: it calls `_allocate_script_slot(..., 208, ...)`
directly and therefore does not prove this caller chain.

This is classification **A — authentic LSCR 208 is not started**.  Repairing
the scheduler/caller path is a prerequisite to evaluating loadSound 82,
trigger/deferred command processing, marker delivery, or composite admission.
Starting Phase B from a directly allocated script would repeat the invalid
split-proof pattern, so no audio command or composite code changed.

## Relevant LSCR 208 prefix

The source prefix reconfirms the expected command construction:

```text
0000 1A 00 40 00 00          move Bit[0], 0
0005 40 01 02 00 FF          cutscene([2])
000A 0C 02 52                loadSound(82)
000D 62 97 ...               stop/wait resource operation (host decode required)
000F 4C ... 010C,80,0,7      sound-80 hook/marker-7 setup
001D 4C ... 010E,80,7        install marker-7 trigger
002A 4C ... 010F,010D,80,0,600 deferred fade
003D 4C ... 010F,-1          close deferred list
0049 4C ... 010E,80,8        install marker-8 trigger
0056 4C ... 010F,0101,80,0   deferred priority
0068 4C ... 010F,0106,80,0   deferred speed
007A 4C ... 010F,010D,80,0,60 deferred fade
008F 4C ... 010F,8,82        deferred start sound 82
009C 4C ... 010F,-1          close deferred list
```

Later payload bytes at `$1C97` reconfirm the sound-82 query followed by
`$0106`, `$0101`, and `$010D` controls on the absent-player path.

## Parked Phase 6L transition

The preliminary worktree subset was captured at
`docs/attachments/PHASE6L_PRELIMINARY_LOAD_ROOM_WITH_EGO.patch`.  Because the
repository has no clean milestone commit and contains all prior accepted
uncommitted phases, that attachment is intentionally a broad file-subset
snapshot, not a minimal patch.  The `$24` cold-dispatch edge and host opcode
registration are disabled for Phase 6L-A.  The decoded stop boundary remains
LSCR 211 `$02DE`; room 63 cannot be entered by the Phase 6L-A artifacts.

