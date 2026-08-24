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
    plp
    rts

Same_Input_Poll:
    php
    sep #$20
    .a8
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

    lda.l SAME_INPUT_PRESSED
    ora.l SAME_INPUT_RELEASED
    beq Same_Input_Poll__done

    jsr Same_Event_StageTarget
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
Same_Input_Poll__done:
    plp
    rts
