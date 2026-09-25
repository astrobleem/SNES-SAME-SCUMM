; ============================================================================
; Optional generic compiled-music lifecycle coordinator.
;
; The coordinator owns catalog timing and engine notifications. It sends only
; normalized audio packets and never reads TAD state or S-SMP/DSP ports.
; ============================================================================
SAME_MUSIC_STATUS_IDLE       = $00
SAME_MUSIC_STATUS_PENDING    = $01
SAME_MUSIC_STATUS_PLAYING    = $02
SAME_MUSIC_STATUS_COMPLETED  = $03
SAME_MUSIC_STATUS_STOPPED    = $04
SAME_MUSIC_STATUS_FAILED     = $FF
SAME_MUSIC_START_FRAMES      = $000F ; TAD's documented 250 ms start interval

Same_MusicLifecycle_Reset:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    sta.l SAME_MUSIC_LIFECYCLE_DURATION
    sta.l SAME_MUSIC_LIFECYCLE_DEADLINE
    rts

; A8 logical catalog identity. Carry reports a required-packet queue failure;
; invalid identities are reported asynchronously through ENGINE FAILED.
Same_MusicLifecycle_Play:
    rep #$10
    sep #$20
    .a8
    .i16
    sta.l SAME_MUSIC_LIFECYCLE_LOGICAL
    ldx #$0000
Same_MusicLifecycle_Play__lookup:
    .a8
    .i16
    cpx #SAME_MUSIC_LIFECYCLE_COUNT
    bcs Same_MusicLifecycle_Play__missing
    cmp.l Same_Music_Lifecycle_LogicalIds,x
    beq Same_MusicLifecycle_Play__found
    inx
    bra Same_MusicLifecycle_Play__lookup
Same_MusicLifecycle_Play__found:
    .a8
    .i16
    rep #$20
    .a16
    txa
    asl
    tax
    lda.l Same_Music_Lifecycle_DurationFrames,x
    sta.l SAME_MUSIC_LIFECYCLE_DURATION
    lda.l SAME_FRAME_COUNTER
    clc
    adc #SAME_MUSIC_START_FRAMES
    sta.l SAME_MUSIC_LIFECYCLE_DEADLINE
    jsr Same_MusicLifecycle_StageAudio
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda.l SAME_MUSIC_LIFECYCLE_LOGICAL
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bcs Same_MusicLifecycle_Play__queue_failed
    lda #SAME_MUSIC_STATUS_PENDING
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    lda #$00
    sta.l SAME_ENGINE_LAST_STATUS
    clc
    rts
Same_MusicLifecycle_Play__missing:
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_FAILED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    lda #SAME_ENGINE_OP_FAILED
    jsr Same_MusicLifecycle_Notify
    rts
Same_MusicLifecycle_Play__queue_failed:
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_FAILED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    sec
    rts

; Explicit stop remains distinct from natural COMPLETED state.
Same_MusicLifecycle_Stop:
    jsr Same_MusicLifecycle_QueueStop
    bcs Same_MusicLifecycle_Stop__failed
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_STOPPED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    lda #SAME_ENGINE_OP_STOPPED
    jsr Same_MusicLifecycle_Notify
    rts
Same_MusicLifecycle_Stop__failed:
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_FAILED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    sec
    rts

; Called once per semantic frame. Carry reports a required-packet failure.
Same_MusicLifecycle_Frame:
    sep #$20
    .a8
    lda.l SAME_MUSIC_LIFECYCLE_STATUS
    cmp #SAME_MUSIC_STATUS_PENDING
    beq Same_MusicLifecycle_Frame__pending
    cmp #SAME_MUSIC_STATUS_PLAYING
    beq Same_MusicLifecycle_Frame__playing
    clc
    rts
Same_MusicLifecycle_Frame__pending:
    .a8
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_MUSIC_LIFECYCLE_DEADLINE
    bcc Same_MusicLifecycle_Frame__idle
    lda.l SAME_MUSIC_LIFECYCLE_DURATION
    beq Same_MusicLifecycle_Frame__pending_ready
    clc
    adc.l SAME_FRAME_COUNTER
    sta.l SAME_MUSIC_LIFECYCLE_DEADLINE
Same_MusicLifecycle_Frame__pending_ready:
    .a16
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_PLAYING
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    lda #SAME_ENGINE_OP_READY
    jsr Same_MusicLifecycle_Notify
    rts
Same_MusicLifecycle_Frame__playing:
    .a8
    rep #$20
    .a16
    lda.l SAME_MUSIC_LIFECYCLE_DURATION
    beq Same_MusicLifecycle_Frame__idle
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_MUSIC_LIFECYCLE_DEADLINE
    bcc Same_MusicLifecycle_Frame__idle
    jsr Same_MusicLifecycle_QueueStop
    bcs Same_MusicLifecycle_Frame__failed
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_COMPLETED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    lda #SAME_ENGINE_OP_STOPPED
    jsr Same_MusicLifecycle_Notify
    rts
Same_MusicLifecycle_Frame__failed:
    sep #$20
    .a8
    lda #SAME_MUSIC_STATUS_FAILED
    sta.l SAME_MUSIC_LIFECYCLE_STATUS
    sec
    rts
Same_MusicLifecycle_Frame__idle:
    sep #$20
    .a8
    clc
    rts

Same_MusicLifecycle_QueueStop:
    jsr Same_MusicLifecycle_StageAudio
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MUSIC_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    jsr Same_Event_Push
    rts

Same_MusicLifecycle_StageAudio:
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    rts

; A8 EngineOpcode response. The existing engine-service seam retains it.
Same_MusicLifecycle_Notify:
    pha
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    pla
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_SERVICE_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_FLAG_RESPONSE
    sta.l SAME_EVENT_STAGING+SAME_PKT_FLAGS
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_SOURCE
    lda #SAME_ENDPOINT_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    lda.l SAME_MUSIC_LIFECYCLE_LOGICAL
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    rts

.include "../generated/music_lifecycle_catalog.inc.pasm"
