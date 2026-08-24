; Milestone 0 records normalized audio requests.  The TAD/SPC backend is imported
; from snes-bor only after this queue contract is proven in isolation.
Same_Audio_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_AUDIO_LAST_OPCODE
    lda #$0000
    sta.l SAME_AUDIO_LAST_ARG0
    lda #$0000
    sta.l SAME_AUDIO_LAST_ARG0+2
    lda #$0000
    sta.l SAME_AUDIO_LAST_ARG1
    lda #$0000
    sta.l SAME_AUDIO_LAST_ARG1+2
    sep #$20
    .a8
    sta.l SAME_AUDIO_TRACE_COUNT
    plp
    rts

Same_Audio_Handle:
    php
    sep #$20
    .a8
    lda.l SAME_AUDIO_TRACE_COUNT
    cmp #SAME_AUDIO_TRACE_CAPACITY
    bcs Same_Audio_Handle__trace_done
    tax
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    sta.l SAME_AUDIO_TRACE_OPCODE,x
    lda.l SAME_EVENT_STAGING+SAME_PKT_SOURCE
    sta.l SAME_AUDIO_TRACE_SOURCE,x
    lda.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    sta.l SAME_AUDIO_TRACE_DESTINATION,x
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_AUDIO_TRACE_ARG0,x
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sta.l SAME_AUDIO_TRACE_ARG1,x
    sep #$20
    .a8
    lda.l SAME_AUDIO_TRACE_COUNT
    inc
    sta.l SAME_AUDIO_TRACE_COUNT
Same_Audio_Handle__trace_done:
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    sta.l SAME_AUDIO_LAST_OPCODE
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_AUDIO_LAST_ARG0
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+2
    sta.l SAME_AUDIO_LAST_ARG0+2
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sta.l SAME_AUDIO_LAST_ARG1
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+2
    sta.l SAME_AUDIO_LAST_ARG1+2
    plp
    rts
