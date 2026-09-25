; Backend content gate for authentic Fate sound-80/82 composite. Authentic
; SCUMM/LSCR execution is proven separately through the real host interpreter;
; this engine issues only the ordinary initial music packet and the accepted
; M24R-A private transition request at a compiled test phase.
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_DEMO

Same_ActiveEngine_Boot:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_ENGINE_PRIVATE_STATE
    sta.l SAME_ENGINE_PRIVATE_STATE+2
    clc
    rts

Same_ActiveEngine_Frame:
    php
    rep #$30
    .a16
    .i16
    lda #$0001
    sta.l SAME_ENGINE_FRAME_OPS
    sep #$20
    .a8
    lda.l SAME_ENGINE_PRIVATE_STATE
    beq Same_M24RB__start
    cmp #$01
    beq Same_M24RB__wait_song
    cmp #$02
    beq Same_M24RB__wait_bind
    cmp #$03
    beq Same_M24RB__wait_marker
    cmp #$04
    bne Same_M24RB__unknown_phase
    brl Same_M24RB__wait_phase
Same_M24RB__unknown_phase:
    brl Same_M24RB__done
Same_M24RB__start:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp #$003C
    sep #$20
    .a8
    bcs Same_M24RB__start_ready
    brl Same_M24RB__done
Same_M24RB__start_ready:
    .a8
    lda #$06
    sta.l SAME_M24RA_PHASE ; suppress the synthetic M24R-A command program
    jsr Same_Event_StageEngine
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
    sep #$20
    .a8
    lda #$01
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_M24RB__done
Same_M24RB__wait_song:
    .a8
    lda.l SAME_TAD_STATE
    cmp #SAME_TAD_STATE_PLAYING
    bne Same_M24RB__done
    lda #$02
    jsr Same_M24RA_QueueBind
    bcs Same_M24RB__done
    sta.l SAME_M24RA_GENERATION
    lda #$FF
    sta.l SAME_M24RA_GROUP_A_MASK
    lda #$02
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_M24RB__done
Same_M24RB__wait_bind:
    .a8
    jsr Same_M24RA_CommandReady
    bcs Same_M24RB__done
    lda #$03
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_M24RB__done
Same_M24RB__wait_marker:
    .a8
    lda APUIO1
    cmp #$88
    bne Same_M24RB__done
    .if SAME_M24RB_PHASE_DELAY == 0
    lda #$05
    sta.l SAME_ENGINE_PRIVATE_STATE
    brl Same_M24RB__done
    .else
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    clc
    adc #SAME_M24RB_PHASE_DELAY
    sta.l SAME_ENGINE_PRIVATE_STATE+2
    sep #$20
    .a8
    lda #$04
    sta.l SAME_ENGINE_PRIVATE_STATE
    bra Same_M24RB__done
    .endif
Same_M24RB__wait_phase:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_ENGINE_PRIVATE_STATE+2
    sep #$20
    .a8
    bcc Same_M24RB__done
    lda #$02
    jsr Same_M24RA_QueueRequest
    bcs Same_M24RB__done
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_M24RA_REQUEST_FRAME
    sep #$20
    .a8
    lda #$05
    sta.l SAME_ENGINE_PRIVATE_STATE
Same_M24RB__done:
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
