; ============================================================================
; Active engine: lifecycle/service conformance demo
; Replace this include with one engine adapter at link time.  The stable labels
; below are the only game-semantics entry points the engine host calls.
; ============================================================================
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_DEMO

SNES_B              = $8000
SNES_Y              = $4000
SNES_SELECT         = $2000
SNES_START          = $1000
SNES_UP             = $0800
SNES_DOWN           = $0400
SNES_LEFT           = $0200
SNES_RIGHT          = $0100
SNES_A              = $0080
SNES_X              = $0040
SNES_L              = $0020
SNES_R              = $0010

Same_ActiveEngine_Boot:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_ENGINE_PRIVATE_STATE
    lda #$003C
    sta.l SAME_ENGINE_HEARTBEAT_NEXT

    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SET_BACKDROP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda #$0010
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    plp
    clc
    rts

Same_ActiveEngine_Frame:
    php
    rep #$30
    .a16
    .i16
    lda #$0001
    sta.l SAME_ENGINE_FRAME_OPS
    lda.l SAME_INPUT_PRESSED
    bit #SNES_LEFT
    bne Same_ActiveEngine_Frame__left
    bit #SNES_RIGHT
    bne Same_ActiveEngine_Frame__right
    bit #SNES_B
    bne Same_ActiveEngine_Frame__button_b
    bit #SNES_A
    bne Same_ActiveEngine_Frame__button_a
    bit #SNES_START
    bne Same_ActiveEngine_Frame__start
    bra Same_ActiveEngine_Frame__heartbeat

Same_ActiveEngine_Frame__left:
    rep #$30
    .a16
    .i16
    lda #$7C00
    bra Same_ActiveEngine_Frame__set_color
Same_ActiveEngine_Frame__right:
    rep #$30
    .a16
    .i16
    lda #$03E0
    bra Same_ActiveEngine_Frame__set_color
Same_ActiveEngine_Frame__button_b:
    rep #$30
    .a16
    .i16
    lda #$001F
    bra Same_ActiveEngine_Frame__set_color
Same_ActiveEngine_Frame__button_a:
    rep #$30
    .a16
    .i16
    lda #$7FFF
Same_ActiveEngine_Frame__set_color:
    rep #$30
    .a16
    .i16
    pha
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SET_BACKDROP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    pla
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bra Same_ActiveEngine_Frame__heartbeat

Same_ActiveEngine_Frame__start:
    rep #$30
    .a16
    .i16
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push

Same_ActiveEngine_Frame__heartbeat:
    rep #$30
    .a16
    .i16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_ENGINE_HEARTBEAT_NEXT
    bcc Same_ActiveEngine_Frame__done
    clc
    adc #$003C
    sta.l SAME_ENGINE_HEARTBEAT_NEXT
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_KERNEL
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_KERNEL_OP_HEARTBEAT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
Same_ActiveEngine_Frame__done:
    rep #$30
    .a16
    .i16
    plp
    clc
    rts

Same_ActiveEngine_Suspend:
    clc
    rts
Same_ActiveEngine_Resume:
    clc
    rts
Same_ActiveEngine_Shutdown:
    clc
    rts
