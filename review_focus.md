# Focused implementation review: headless SCUMM message lifetime

This is a screened source-only excerpt. It contains no ROM/resource payload.

## Current production change

In `runtime/snes/engines/scumm_v5.pasm`, the former
`SAME_BUILD_SCUMM_SCENARIO_FIXTURE` block at
`ScummV5_Op_Print__text_done` that cleared
`SAME_SCUMM_C23_MESSAGE_COUNT`, `SAME_SCUMM_TALK_ACTIVE`, and
`SAME_SCUMM_TALK_HAVE_MSG` was removed.

After complete inline text decoding, the existing M23A path now applies to the
fixture as well:

```asm
ScummV5_Op_Print__text_done:
    lda.l SAME_SCUMM_C23_RAW_INDEX
    sta.l SAME_SCUMM_C23_LAST_LENGTH
    .if SAME_BUILD_SCUMM_M23A
        lda.l SAME_SCUMM_C23_LAST_SLOT
        bne ScummV5_Op_Print__text_no_talk
        jsl ScummV5_Talk_Begin_Far
        bcc ScummV5_Op_Print__talk_started
        ; existing fail-closed error handling
    .endif
```

`Talk_Begin_Far` owns logical delay, message ownership, continuation, and
frame-end completion. `Talk_FrameBegin_Far` publishes `VAR_HAVE_MSG`, and
`Talk_FrameEnd_Far` stops/continues the message at the canonical boundary.
Presentation remains optional when no overlay/pixel backend is selected.

This is delivery/decode acknowledgement only in the sense that the text bytes
have been accepted by C23; it is not logical message completion and does not
auto-acknowledge `waitForMessage`.

The follow-up fixture path also treats `C23_RAW_INDEX >= 32` as a logical
headless-long message rather than validating a discarded buffer byte. Its
logical duration is retained without expanding the presentation buffer.
The scheduler post-run path restores the scheduler-selected slot before the
common save/retirement operation, protecting parent state after nested runs.

## Scope

No production title/gameplay behavior, ROM/resource payload, validator WRAM
write, or emulator modification is included in this review branch.
