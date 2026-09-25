; Copyright-free engine fixture for the backend-only M24R-A proof.  It emits
; one ordinary SAME music-play packet; transition control remains private to
; the explicitly selected audio-backend conformance build.
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_DEMO

Same_ActiveEngine_Boot:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_ENGINE_PRIVATE_STATE
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
    lda.l SAME_ENGINE_PRIVATE_STATE
    bne Same_ActiveEngine_Frame__done
    lda.l SAME_FRAME_COUNTER
    cmp #$003C
    bcc Same_ActiveEngine_Frame__done
    lda #$0001
    sta.l SAME_ENGINE_PRIVATE_STATE
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
