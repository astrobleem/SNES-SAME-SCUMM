; ============================================================================
; SAME engine host lifecycle
;
; The active engine owns game semantics.  It never owns NMI, PPU registers,
; DMA channels, SPC ports, MSU-1 registers, or SA-1 mailbox addresses; those
; remain service/backend responsibilities.
; ============================================================================

SAME_ENGINE_NONE       = $00
SAME_ENGINE_DEMO       = $01
SAME_ENGINE_SCUMM_V5   = $02
SAME_ENGINE_AGI_V2     = $03

SAME_ENGINE_CREATED    = $00
SAME_ENGINE_PROBED     = $01
SAME_ENGINE_RUNNING    = $02
SAME_ENGINE_SUSPENDED  = $03
SAME_ENGINE_STOPPED    = $04
SAME_ENGINE_FAILED     = $FF

Same_Engine_Reset:
    php
    sep #$20
    .a8
    lda #SAME_ACTIVE_ENGINE_ID
    sta.l SAME_ENGINE_ID
    lda #SAME_ENGINE_CREATED
    sta.l SAME_ENGINE_LIFECYCLE
    lda #$00
    sta.l SAME_ENGINE_LAST_STATUS
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_ENGINE_FRAME_OPS
    sta.l SAME_ENGINE_TOTAL_OPS
    plp
    rts

Same_Engine_Boot:
    php
    sep #$20
    .a8
    lda.l SAME_ENGINE_LIFECYCLE
    cmp #SAME_ENGINE_CREATED
    beq Same_Engine_Boot__created
    lda #SAME_ENGINE_FAILED
    sta.l SAME_ENGINE_LIFECYCLE
    plp
    rts

Same_Engine_Boot__created:
    sep #$20
    .a8
    lda #SAME_ENGINE_PROBED
    sta.l SAME_ENGINE_LIFECYCLE

    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENGINE_OP_BOOT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    jsr Same_Event_Push

    jsr Same_ActiveEngine_Boot
    bcs Same_Engine_Boot__failed

    sep #$20
    .a8
    lda #SAME_ENGINE_RUNNING
    sta.l SAME_ENGINE_LIFECYCLE
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENGINE_OP_READY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_KERNEL
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    jsr Same_Event_Push
    plp
    clc
    rts

Same_Engine_Boot__failed:
    sep #$20
    .a8
    lda #SAME_ENGINE_OP_FAILED
    sta.l SAME_ENGINE_LIFECYCLE
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENGINE_OP_FAILED
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    jsr Same_Event_Push
    plp
    sec
    rts

Same_Engine_Frame:
    php
    sep #$20
    .a8
    lda.l SAME_ENGINE_LIFECYCLE
    cmp #SAME_ENGINE_RUNNING
    beq Same_Engine_Frame__running
    plp
    rts

Same_Engine_Frame__running:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_ENGINE_FRAME_OPS
    jsr Same_ActiveEngine_Frame
    bcs Same_Engine_Frame__failed
    lda.l SAME_ENGINE_TOTAL_OPS
    clc
    adc.l SAME_ENGINE_FRAME_OPS
    sta.l SAME_ENGINE_TOTAL_OPS
    plp
    rts

Same_Engine_Frame__failed:
    sep #$20
    .a8
    lda #SAME_ENGINE_FAILED
    sta.l SAME_ENGINE_LIFECYCLE
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENGINE_FAILED
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    jsr Same_Event_Push
    plp
    rts

Same_Engine_Suspend:
    php
    sep #$20
    .a8
    lda.l SAME_ENGINE_LIFECYCLE
    cmp #SAME_ENGINE_RUNNING
    bne Same_Engine_Suspend__done
    jsr Same_ActiveEngine_Suspend
    lda #SAME_ENGINE_SUSPENDED
    sta.l SAME_ENGINE_LIFECYCLE
Same_Engine_Suspend__done:
    sep #$20
    .a8
    plp
    rts

Same_Engine_Resume:
    php
    sep #$20
    .a8
    lda.l SAME_ENGINE_LIFECYCLE
    cmp #SAME_ENGINE_SUSPENDED
    bne Same_Engine_Resume__done
    jsr Same_ActiveEngine_Resume
    lda #SAME_ENGINE_RUNNING
    sta.l SAME_ENGINE_LIFECYCLE
Same_Engine_Resume__done:
    sep #$20
    .a8
    plp
    rts

Same_Engine_Shutdown:
    php
    sep #$20
    .a8
    lda.l SAME_ENGINE_LIFECYCLE
    cmp #SAME_ENGINE_STOPPED
    beq Same_Engine_Shutdown__done
    jsr Same_ActiveEngine_Shutdown
    lda #SAME_ENGINE_STOPPED
    sta.l SAME_ENGINE_LIFECYCLE
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENGINE_STOPPED
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    jsr Same_Event_Push
Same_Engine_Shutdown__done:
    sep #$20
    .a8
    plp
    rts

; Engine service packets arriving from a backend are kept separate from the
; direct lifecycle calls above.  This is the future asynchronous response seam.
Same_Engine_Handle:
    php
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    sta.l SAME_ENGINE_LAST_STATUS
    plp
    rts
