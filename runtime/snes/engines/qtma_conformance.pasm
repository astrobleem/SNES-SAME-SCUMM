; ============================================================================
; Repository-owned QTMA music runtime conformance consumer.
;
; This engine knows only a logical catalog identity and engine-service responses.
; It never reads audio-backend state or touches S-SMP/DSP ports.
; ============================================================================
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_QTMA_TEST

SAME_QTMA_STATUS_WAITING   = $0000
SAME_QTMA_STATUS_REQUESTED = $0001
SAME_QTMA_STATUS_PLAYING   = $0002
SAME_QTMA_STATUS_COMPLETE  = $0003
SAME_QTMA_PLAY_FRAME       = $0078 ; allow bounded backend bootstrap: 120 frames

Same_ActiveEngine_Boot:
    php
    rep #$30
    .a16
    .i16
    lda #SAME_QTMA_STATUS_WAITING
    sta.l SAME_ENGINE_PRIVATE_STATE
    lda #SAME_QTMA_PLAY_FRAME
    sta.l SAME_ENGINE_HEARTBEAT_NEXT
    jsr Same_MusicLifecycle_Reset

    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SET_BACKDROP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda #$0210
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
    jsr Same_MusicLifecycle_Frame
    bcs Same_ActiveEngine_Frame__failed
    rep #$30
    .a16
    .i16
    lda.l SAME_ENGINE_PRIVATE_STATE
    cmp #SAME_QTMA_STATUS_WAITING
    beq Same_ActiveEngine_Frame__waiting
    cmp #SAME_QTMA_STATUS_REQUESTED
    beq Same_ActiveEngine_Frame__requested
    cmp #SAME_QTMA_STATUS_PLAYING
    beq Same_ActiveEngine_Frame__playing
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__waiting:
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_ENGINE_HEARTBEAT_NEXT
    bcc Same_ActiveEngine_Frame__done
    sep #$20
    .a8
    lda #$0001 ; logical catalog entry, not a compiled TAD song id
    jsr Same_MusicLifecycle_Play
    bcs Same_ActiveEngine_Frame__failed
    rep #$20
    .a16
    lda #SAME_QTMA_STATUS_REQUESTED
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__requested:
    sep #$20
    .a8
    lda.l SAME_ENGINE_LAST_STATUS
    cmp #SAME_ENGINE_OP_READY
    beq Same_ActiveEngine_Frame__response_ready
    cmp #SAME_ENGINE_OP_FAILED
    beq Same_ActiveEngine_Frame__failed
    bra Same_ActiveEngine_Frame__done
Same_ActiveEngine_Frame__response_ready:
    rep #$20
    .a16
    lda #SAME_QTMA_STATUS_PLAYING
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__playing:
    sep #$20
    .a8
    lda.l SAME_ENGINE_LAST_STATUS
    cmp #SAME_ENGINE_OP_STOPPED
    beq Same_ActiveEngine_Frame__response_complete
    cmp #SAME_ENGINE_OP_FAILED
    beq Same_ActiveEngine_Frame__failed
    bra Same_ActiveEngine_Frame__done
Same_ActiveEngine_Frame__response_complete:
    rep #$20
    .a16
    lda #SAME_QTMA_STATUS_COMPLETE
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__failed:
    plp
    sec
    rts
Same_ActiveEngine_Frame__done:
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

.include "../services/music_lifecycle.pasm"
