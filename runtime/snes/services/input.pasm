; Read auto-joypad result after the NMI-triggered hardware scan completes.
Same_Input_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_INPUT_HELD
    lda #$0000
    sta.l SAME_INPUT_PREVIOUS
    lda #$0000
    sta.l SAME_INPUT_PRESSED
    lda #$0000
    sta.l SAME_INPUT_RELEASED
    sta.l SAME_INPUT_EDGE_SEQUENCE
    sta.l SAME_INPUT_TALK_OWNED_SEQUENCE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_INPUT_TALK_OWNED_VALID
    plp
    rts

Same_Input_Poll:
    php
    sep #$20
    .a8
.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    lda #$00
    sta.l SAME_RESET_DIAG_INPUT_SP_STAGE
    sta.l SAME_RESET_DIAG_INPUT_SP_STAGE+1
    sta.l SAME_RESET_DIAG_INPUT_SP_FAILURES
    sta.l SAME_RESET_DIAG_INPUT_SP_FAILURES+1
    rep #$30
    .a16
    .i16
    tsc
    sta.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    jsr Same_Reset_Diag_CheckInputStack
    bcc Same_Input_Poll__diag_entry_ok
    jmp Same_Reset_Diag_StackFailure
Same_Input_Poll__diag_entry_ok:
    sep #$20
    .a8
.endif
Same_Input_Poll__wait_autojoy:
    sep #$20
    .a8
    lda HVBJOY
    and #$01
    bne Same_Input_Poll__wait_autojoy

    rep #$30
    .a16
    .i16
    lda.l SAME_INPUT_HELD
    sta.l SAME_INPUT_PREVIOUS
    lda JOY1L
    and #$FFF0
    sta.l SAME_INPUT_HELD

    eor #$FFFF
    and.l SAME_INPUT_PREVIOUS
    sta.l SAME_INPUT_RELEASED

    lda.l SAME_INPUT_PREVIOUS
    eor #$FFFF
    and.l SAME_INPUT_HELD
    sta.l SAME_INPUT_PRESSED

    ; Give every newly observed physical press an identity independent of the
    ; number of host polls before SCUMM's controller phase runs.
    beq Same_Input_Poll__edge_sequence_done
    lda.l SAME_INPUT_EDGE_SEQUENCE
    inc
    sta.l SAME_INPUT_EDGE_SEQUENCE
    .if SAME_BUILD_SCUMM_CONTROLLER
    ; Assign ownership at the instant the physical edge is sampled. Talk's
    ; frame routine can run later (or on a different scheduling cadence),
    ; after PRESSED has already been cleared by another poll.
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq Same_Input_Poll__edge_sequence_done
    lda #$01
    sta.l SAME_INPUT_TALK_OWNED_VALID
    rep #$20
    .a16
    lda.l SAME_INPUT_EDGE_SEQUENCE
    sta.l SAME_INPUT_TALK_OWNED_SEQUENCE
    sep #$20
    .a8
    .endif
Same_Input_Poll__edge_sequence_done:
    rep #$20
    .a16

    lda.l SAME_INPUT_PRESSED
    ora.l SAME_INPUT_RELEASED
    beq Same_Input_Poll__done

    jsr Same_Event_StageTarget
.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    php
    rep #$20
    .a16
    lda #$0002
    sta.l SAME_RESET_DIAG_INPUT_SP_STAGE
    plp
    rep #$20
    .a16
    tsc
    sta.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    jsr Same_Reset_Diag_CheckInputStack
    bcc Same_Input_Poll__diag_stage_target_ok
    jmp Same_Reset_Diag_StackFailure
Same_Input_Poll__diag_stage_target_ok:
.endif
    sep #$20
    .a8
    lda #SAME_SERVICE_INPUT
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_INPUT_OP_SNAPSHOT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SCPU
    sta.l SAME_EVENT_STAGING+SAME_PKT_SOURCE
    rep #$20
    .a16
    lda.l SAME_INPUT_HELD
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0000
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+2
    lda.l SAME_INPUT_RELEASED
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda.l SAME_INPUT_PRESSED
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+2
    jsr Same_Event_Push
.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    php
    rep #$20
    .a16
    lda #$0003
    sta.l SAME_RESET_DIAG_INPUT_SP_STAGE
    plp
    rep #$20
    .a16
    tsc
    sta.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    jsr Same_Reset_Diag_CheckInputStack
    bcc Same_Input_Poll__diag_event_push_ok
    jmp Same_Reset_Diag_StackFailure
Same_Input_Poll__diag_event_push_ok:
.endif
Same_Input_Poll__done:
.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    php
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_RESET_DIAG_INPUT_SP_STAGE
    plp
    rep #$20
    .a16
    tsc
    sta.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    jsr Same_Reset_Diag_CheckInputStack
    bcc Same_Input_Poll__diag_done_ok
    jmp Same_Reset_Diag_StackFailure
Same_Input_Poll__diag_done_ok:
.endif
    plp
    rts
