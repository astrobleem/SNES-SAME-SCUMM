; Compiled sampled backend: normalized packets retain their trace contract and
; additionally drive Terrific Audio Driver protocol v20 on the S-SMP.
; Protocol behavior is adapted from Terrific Audio Driver (c) 2023 Marcus Rowe,
; distributed under the zlib license: https://github.com/undisbeliever/terrific-audio-driver
SAME_TAD_STATE_WAIT_COMMON = $7B
SAME_TAD_STATE_WAIT_SONG   = $7C
SAME_TAD_STATE_LOAD_COMMON = $7D
SAME_TAD_STATE_LOAD_SONG   = $7F
SAME_TAD_STATE_PLAYING     = $82
SAME_TAD_COMMAND_VOLUME    = $0A
SAME_TAD_COMMAND_SECTION   = $16
SAME_TAD_COMMAND_M24RA     = $16
SAME_TAD_SWITCH_LOADER     = $A0

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
    sta.l SAME_TAD_REJECTED
    sta.l SAME_TAD_PROBE_REQUEST
    sta.l SAME_TAD_READY
    sta.l SAME_TAD_STATE
    sta.l SAME_TAD_PREVIOUS_COMMAND
    sta.l SAME_TAD_NEXT_SONG
    sta.l SAME_TAD_NEXT_PARAMETER0
    sta.l SAME_TAD_NEXT_PARAMETER1
    sta.l SAME_TAD_LAST_COMMAND
    sta.l SAME_TAD_SECTION_TOKEN
    sta.l SAME_TAD_BOUNDARY_TOKEN
    sta.l SAME_TAD_BOUNDARY_COUNT
    .if SAME_BUILD_M24RA
    jsr Same_M24RA_Reset
    .endif
    lda #$FF
    sta.l SAME_TAD_SECTION_DEFERRED
    .if SAME_BUILD_SCUMM_M20
    lda #$FF
    sta.l SAME_TAD_DEFERRED_SONG
    .endif
    jsr Same_Tad_Init
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
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_AUDIO_OP_MUSIC_PLAY
    beq Same_Audio_Handle__play
    cmp #SAME_AUDIO_OP_SFX_PLAY
    beq Same_Audio_Handle__play
    cmp #SAME_AUDIO_OP_MUSIC_STOP
    beq Same_Audio_Handle__stop
    cmp #SAME_AUDIO_OP_SFX_STOP
    beq Same_Audio_Handle__stop
    cmp #SAME_AUDIO_OP_MASTER_VOLUME
    beq Same_Audio_Handle__volume
    .if SAME_BUILD_SCUMM_M22
    cmp #SAME_AUDIO_OP_MUSIC_SECTION_SELECT
    beq Same_Audio_Handle__section
    .endif
    jmp Same_Audio_Handle__done
Same_Audio_Handle__play:
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    .if SAME_BUILD_SCUMM_M21
    jsr Same_Tad_HasRoutes
    bcs Same_Audio_Handle__play_unrouted
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Tad_MapRoute
    bcs Same_Audio_Handle__play_route_rejected
    ; Route selection is resolved only after all same-frame packets drain.
    ; A following one-shot hook therefore supersedes the silent default before
    ; either route can acquire TAD ready/playing ownership.
    sta.l SAME_TAD_DEFERRED_SONG
    bra Same_Audio_Handle__done
Same_Audio_Handle__play_route_rejected:
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
    bra Same_Audio_Handle__done
Same_Audio_Handle__play_unrouted:
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    .endif
    jsr Same_Tad_MapSound
    bcs Same_Audio_Handle__done
    .if SAME_BUILD_SCUMM_M20
    pha
    lda.l SAME_TAD_STATE
    cmp #$80
    pla
    bcs Same_Audio_Handle__play_ready
    sta.l SAME_TAD_DEFERRED_SONG
    bra Same_Audio_Handle__done
Same_Audio_Handle__play_ready:
    .a8
    .endif
    jsr Same_Tad_RequestSong
    bra Same_Audio_Handle__done
Same_Audio_Handle__stop:
    .a8
    .if SAME_BUILD_SCUMM_M20
    lda #$FF
    sta.l SAME_TAD_DEFERRED_SONG
    .endif
    lda #$00
    jsr Same_Tad_RequestSong
    bra Same_Audio_Handle__done
Same_Audio_Handle__volume:
    lda.l SAME_TAD_NEXT_COMMAND
    bmi Same_Audio_Handle__volume_room
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
    bra Same_Audio_Handle__done
Same_Audio_Handle__volume_room:
    .a8
    lda #SAME_TAD_COMMAND_VOLUME
    sta.l SAME_TAD_NEXT_COMMAND
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_TAD_NEXT_PARAMETER0
    lda #$00
    sta.l SAME_TAD_NEXT_PARAMETER1
    bra Same_Audio_Handle__done
.if SAME_BUILD_SCUMM_M22
Same_Audio_Handle__section:
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_TAD_SECTION_DEFERRED
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+1
    and #$7F
    sta.l SAME_TAD_SECTION_TOKEN
.endif
Same_Audio_Handle__done:
    plp
    rts

; Call once after semantic event draining. It advances exactly one bounded TAD
; transfer/command phase and also exposes a debugger-only real-sound request.
Same_Audio_Process:
    php
    sep #$20
    .a8
    .if SAME_BUILD_M24RA
    jsr Same_M24RA_CaptureEvent
    .endif
    .if SAME_BUILD_SCUMM_M22
    lda APUIO1
    bpl Same_Audio_Process__boundary_done
    and #$7F
    cmp.l SAME_TAD_SECTION_TOKEN
    bne Same_Audio_Process__boundary_done
    cmp.l SAME_TAD_BOUNDARY_TOKEN
    beq Same_Audio_Process__boundary_done
    sta.l SAME_TAD_BOUNDARY_TOKEN
    lda.l SAME_TAD_BOUNDARY_COUNT
    inc
    sta.l SAME_TAD_BOUNDARY_COUNT
Same_Audio_Process__boundary_done:
    .a8
    .endif
    lda.l SAME_TAD_PROBE_REQUEST
    beq Same_Audio_Process__state
    jsr Same_Tad_MapSound
    bcc Same_Audio_Process__probe_mapped
    lda.l SAME_TAD_PROBE_REQUEST
    cmp #SAME_TAD_LAST_SONG+1
    bcs Same_Audio_Process__probe_invalid
    tax
    lda #$00
    sta.l SAME_TAD_PROBE_REQUEST
    txa
    jsr Same_Tad_RequestSong
    bra Same_Audio_Process__state
Same_Audio_Process__probe_mapped:
    .a8
    tax
    lda #$00
    sta.l SAME_TAD_PROBE_REQUEST
    txa
    jsr Same_Tad_RequestSong
    bra Same_Audio_Process__state
Same_Audio_Process__probe_invalid:
    .a8
    lda #$00
    sta.l SAME_TAD_PROBE_REQUEST
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
Same_Audio_Process__state:
    .a8
    lda.l SAME_TAD_STATE
    cmp #SAME_TAD_STATE_WAIT_COMMON
    beq Same_Audio_Process__wait_common
    cmp #SAME_TAD_STATE_WAIT_SONG
    bne Same_Audio_Process__not_wait_song
    jmp Same_Audio_Process__wait_song
Same_Audio_Process__not_wait_song:
    .a8
    cmp #SAME_TAD_STATE_LOAD_COMMON
    beq Same_Audio_Process__load_common
    cmp #SAME_TAD_STATE_LOAD_SONG
    .if SAME_BUILD_SCUMM_M20
    bne Same_Audio_Process__not_load_song
    jmp Same_Audio_Process__load_song
Same_Audio_Process__not_load_song:
    .a8
    .else
    beq Same_Audio_Process__load_song
    .endif
    cmp #$80
    bcc Same_Audio_Process__early_return
    .if SAME_BUILD_SCUMM_M20
    lda.l SAME_TAD_DEFERRED_SONG
    cmp #$FF
    beq Same_Audio_Process__driver_deferred_done
    pha
    lda #$FF
    sta.l SAME_TAD_DEFERRED_SONG
    pla
    jsr Same_Tad_RequestSong
    jmp Same_Audio_Process__return
Same_Audio_Process__driver_deferred_done:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M22
    lda.l SAME_TAD_SECTION_DEFERRED
    cmp #$FF
    beq Same_Audio_Process__section_deferred_done
    pha
    lda.l SAME_TAD_NEXT_COMMAND
    bpl Same_Audio_Process__section_queue_busy
    lda #SAME_TAD_COMMAND_SECTION
    sta.l SAME_TAD_NEXT_COMMAND
    pla
    sta.l SAME_TAD_NEXT_PARAMETER0
    lda #$00
    sta.l SAME_TAD_NEXT_PARAMETER1
    lda #$FF
    sta.l SAME_TAD_SECTION_DEFERRED
    bra Same_Audio_Process__section_deferred_done
Same_Audio_Process__section_queue_busy:
    pla
Same_Audio_Process__section_deferred_done:
    .a8
    .endif
    jmp Same_Audio_Process__driver

Same_Audio_Process__early_return:
    .a8
    plp
    rts
Same_Audio_Process__wait_common:
    .a8
    lda #$01
    jsr Same_Tad_CheckAndSendType
    bcs Same_Audio_Process__common_ready
    jmp Same_Audio_Process__return
Same_Audio_Process__common_ready:
    .a8
    lda #$00
    jsr Same_Tad_SelectDataItem
    bcc Same_Audio_Process__common_selected
    jmp Same_Audio_Process__return
Same_Audio_Process__common_selected:
    .a8
    lda #SAME_TAD_STATE_LOAD_COMMON
    sta.l SAME_TAD_STATE
    jmp Same_Audio_Process__return
Same_Audio_Process__load_common:
    .a8
    jsr Same_Tad_Transfer
    bcs Same_Audio_Process__common_loaded
    jmp Same_Audio_Process__return
Same_Audio_Process__common_loaded:
    .a8
    lda #SAME_TAD_STATE_WAIT_SONG
    sta.l SAME_TAD_STATE
    jmp Same_Audio_Process__return
Same_Audio_Process__wait_song:
    .a8
    lda #$E1 ; song + play immediately + reset volumes + mono
    jsr Same_Tad_CheckAndSendType
    bcs Same_Audio_Process__song_ready
    jmp Same_Audio_Process__return
Same_Audio_Process__song_ready:
    .a8
    lda.l SAME_TAD_NEXT_SONG
    beq Same_Audio_Process__blank
    jsr Same_Tad_SelectDataItem
    bcs Same_Audio_Process__song_invalid
    bra Same_Audio_Process__song_selected
Same_Audio_Process__blank:
    rep #$20
    .a16
    lda #SAME_TAD_BLANK_OFFSET
    sta.l SAME_TAD_TRANSFER_OFFSET
    lda #$0001
    sta.l SAME_TAD_TRANSFER_SIZE
    sep #$20
    .a8
Same_Audio_Process__song_selected:
    .a8
    lda #SAME_TAD_STATE_LOAD_SONG
    sta.l SAME_TAD_STATE
    bra Same_Audio_Process__return
Same_Audio_Process__song_invalid:
    .a8
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
    lda #SAME_TAD_STATE_PLAYING
    sta.l SAME_TAD_STATE
    bra Same_Audio_Process__return
Same_Audio_Process__load_song:
    .a8
    jsr Same_Tad_Transfer
    bcc Same_Audio_Process__return
    lda #$00
    sta.l SAME_TAD_PREVIOUS_COMMAND
    lda #$FF
    sta.l SAME_TAD_NEXT_COMMAND
    lda #SAME_TAD_STATE_PLAYING
    sta.l SAME_TAD_STATE
    lda #$01
    sta.l SAME_TAD_READY
    bra Same_Audio_Process__return
Same_Audio_Process__driver:
    .a8
    .if SAME_BUILD_M24RA
    .if SAME_BUILD_M24RB
    .else
    jsr Same_M24RA_Process
    .endif
    .endif
    lda.l SAME_TAD_PREVIOUS_COMMAND
    cmp APUIO0
    bne Same_Audio_Process__return
    lda.l SAME_TAD_NEXT_COMMAND
    bmi Same_Audio_Process__return
    tax
    lda.l SAME_TAD_NEXT_PARAMETER0
    sta APUIO1
    lda.l SAME_TAD_NEXT_PARAMETER1
    sta APUIO2
    lda.l SAME_TAD_PREVIOUS_COMMAND
    and #$E1
    eor #$E1
    sta.l SAME_TAD_PREVIOUS_COMMAND
    txa
    ora.l SAME_TAD_PREVIOUS_COMMAND
    sta APUIO0
    sta.l SAME_TAD_PREVIOUS_COMMAND
    txa
    sta.l SAME_TAD_LAST_COMMAND
    lda #$FF
    sta.l SAME_TAD_NEXT_COMMAND
Same_Audio_Process__return:
    plp
    rts

.if SAME_BUILD_M24RA
; Reset only the explicitly selected synthetic backend fixture.
Same_M24RA_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
Same_M24RA_Reset__loop:
    .a16
    .i16
    sta.l SAME_M24RA_STATE,x
    inx
    inx
    cpx #SAME_M24RA_STATE_SIZE
    bcc Same_M24RA_Reset__loop
    plp
    rts

; Capture driver-originated tokens.  APUIO2 carries the transition-relative
; tick for request/admission/completion events.
Same_M24RA_CaptureEvent:
    php
    sep #$20
    .a8
    lda APUIO1
    cmp #$90
    beq Same_M24RA_CaptureEvent__candidate
    cmp #$A0
    bcs Same_M24RA_CaptureEvent__above_a0
    brl Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__above_a0:
    .a8
    cmp #$A8
    bcc Same_M24RA_CaptureEvent__candidate
    cmp #$BF
    beq Same_M24RA_CaptureEvent__candidate
    cmp #$CF
    beq Same_M24RA_CaptureEvent__candidate
    brl Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__candidate:
    .a8
    cmp.l SAME_M24RA_LAST_EVENT
    bne Same_M24RA_CaptureEvent__new
    brl Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__new:
    .a8
    sta.l SAME_M24RA_LAST_EVENT
    pha
    lda.l SAME_M24RA_EVENT_COUNT
    cmp #SAME_M24RA_EVENT_CAPACITY
    bcs Same_M24RA_CaptureEvent__discard
    tax
    pla
    sta.l SAME_M24RA_EVENT_TOKENS,x
    pha
    lda APUIO2
    sta.l SAME_M24RA_EVENT_TICKS,x
    txa
    asl
    tax
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_M24RA_EVENT_FRAMES,x
    sep #$20
    .a8
    lda.l SAME_M24RA_EVENT_COUNT
    inc
    sta.l SAME_M24RA_EVENT_COUNT
    pla
    cmp #$90
    bne Same_M24RA_CaptureEvent__not_request
    lda APUIO2
    sta.l SAME_M24RA_REQUEST_TICK
    bra Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__not_request:
    .a8
    cmp #$CF
    bne Same_M24RA_CaptureEvent__not_stale
    lda.l SAME_M24RA_STALE_COUNT
    inc
    sta.l SAME_M24RA_STALE_COUNT
    bra Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__not_stale:
    .a8
    cmp #$BF
    bne Same_M24RA_CaptureEvent__steal
    lda #$00
    sta.l SAME_M24RA_GROUP_A_MASK
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_M24RA_COMPLETE_FRAME
    bra Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__steal:
    .a8
    and #$07
    tax
    lda.l Same_M24RA_VoiceBits,x
    eor #$FF
    and.l SAME_M24RA_GROUP_A_MASK
    sta.l SAME_M24RA_GROUP_A_MASK
    lda.l Same_M24RA_VoiceBits,x
    ora.l SAME_M24RA_GROUP_B_MASK
    sta.l SAME_M24RA_GROUP_B_MASK
    bra Same_M24RA_CaptureEvent__done
Same_M24RA_CaptureEvent__discard:
    pla
Same_M24RA_CaptureEvent__done:
    plp
    rts

; Bind generation 1, supersede it with generation 2, prove a stale generation-1
; request is ignored, then request generation 2 at an inconvenient frame phase.
Same_M24RA_Process:
    php
    sep #$20
    .a8
    lda.l SAME_M24RA_PHASE
    beq Same_M24RA_Process__wait_song
    cmp #$01
    beq Same_M24RA_Process__bind_two
    cmp #$02
    beq Same_M24RA_Process__delay_stale
    cmp #$03
    beq Same_M24RA_Process__send_stale
    cmp #$04
    bne Same_M24RA_Process__not_delay_valid
    brl Same_M24RA_Process__delay_valid
Same_M24RA_Process__not_delay_valid:
    .a8
    cmp #$05
    bne Same_M24RA_Process__unknown_phase
    brl Same_M24RA_Process__send_valid
Same_M24RA_Process__unknown_phase:
    brl Same_M24RA_Process__done
Same_M24RA_Process__wait_song:
    .a8
    lda.l SAME_TAD_STATE
    cmp #SAME_TAD_STATE_PLAYING
    beq Same_M24RA_Process__song_playing
    brl Same_M24RA_Process__done
Same_M24RA_Process__song_playing:
    .a8
    lda.l SAME_TAD_NEXT_SONG
    cmp #$01
    beq Same_M24RA_Process__song_one
    brl Same_M24RA_Process__done
Same_M24RA_Process__song_one:
    .a8
    lda #$01
    jsr Same_M24RA_QueueBind
    bcc Same_M24RA_Process__bind_one_queued
    brl Same_M24RA_Process__done
Same_M24RA_Process__bind_one_queued:
    .a8
    lda #$01
    sta.l SAME_M24RA_PHASE
    brl Same_M24RA_Process__done
Same_M24RA_Process__bind_two:
    .a8
    jsr Same_M24RA_CommandReady
    bcc Same_M24RA_Process__bind_two_ready
    brl Same_M24RA_Process__done
Same_M24RA_Process__bind_two_ready:
    .a8
    lda #$02
    jsr Same_M24RA_QueueBind
    bcc Same_M24RA_Process__bind_two_queued
    brl Same_M24RA_Process__done
Same_M24RA_Process__bind_two_queued:
    .a8
    lda #$02
    sta.l SAME_M24RA_GENERATION
    lda #$FF
    sta.l SAME_M24RA_GROUP_A_MASK
    lda #$02
    sta.l SAME_M24RA_PHASE
    brl Same_M24RA_Process__done
Same_M24RA_Process__delay_stale:
    jsr Same_M24RA_CommandReady
    bcs Same_M24RA_Process__done
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    clc
    adc #$002F
    sta.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    lda #$03
    sta.l SAME_M24RA_PHASE
    brl Same_M24RA_Process__done
Same_M24RA_Process__send_stale:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    bcc Same_M24RA_Process__done
    lda #$01
    jsr Same_M24RA_QueueRequest
    bcs Same_M24RA_Process__done
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    clc
    adc #$0003
    sta.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    lda #$04
    sta.l SAME_M24RA_PHASE
    brl Same_M24RA_Process__done
Same_M24RA_Process__delay_valid:
    jsr Same_M24RA_CommandReady
    bcs Same_M24RA_Process__done
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    bcc Same_M24RA_Process__done
    lda #$05
    sta.l SAME_M24RA_PHASE
Same_M24RA_Process__send_valid:
    .a8
    lda #$02
    jsr Same_M24RA_QueueRequest
    bcs Same_M24RA_Process__done
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_M24RA_REQUEST_FRAME
    sep #$20
    .a8
    lda #$06
    sta.l SAME_M24RA_PHASE
Same_M24RA_Process__done:
    plp
    rts

; Carry clear when the previous command is acknowledged and the one-slot queue
; is empty.
Same_M24RA_CommandReady:
    lda.l SAME_TAD_NEXT_COMMAND
    bpl Same_M24RA_CommandReady__busy
    lda.l SAME_TAD_PREVIOUS_COMMAND
    cmp APUIO0
    bne Same_M24RA_CommandReady__busy
    clc
    rts
Same_M24RA_CommandReady__busy:
    sec
    rts

; A8 generation.
Same_M24RA_QueueBind:
    pha
    jsr Same_M24RA_CommandReady
    bcs Same_M24RA_QueueBind__busy
    lda #SAME_TAD_COMMAND_M24RA
    sta.l SAME_TAD_NEXT_COMMAND
    lda #$00
    sta.l SAME_TAD_NEXT_PARAMETER0
    pla
    sta.l SAME_TAD_NEXT_PARAMETER1
    lda.l SAME_M24RA_COMMAND_COUNT
    inc
    sta.l SAME_M24RA_COMMAND_COUNT
    clc
    rts
Same_M24RA_QueueBind__busy:
    pla
    sec
    rts

; A8 generation.
Same_M24RA_QueueRequest:
    pha
    jsr Same_M24RA_CommandReady
    bcs Same_M24RA_QueueRequest__busy
    lda #SAME_TAD_COMMAND_M24RA
    sta.l SAME_TAD_NEXT_COMMAND
    lda #$01
    sta.l SAME_TAD_NEXT_PARAMETER0
    pla
    sta.l SAME_TAD_NEXT_PARAMETER1
    lda.l SAME_M24RA_COMMAND_COUNT
    inc
    sta.l SAME_M24RA_COMMAND_COUNT
    clc
    rts
Same_M24RA_QueueRequest__busy:
    pla
    sec
    rts

Same_M24RA_VoiceBits:
    .byte $01,$02,$04,$08,$10,$20,$40,$80
.endif

; A8: request blank (0) or a compiled song (1..catalog/project maximum).
Same_Tad_RequestSong:
    pha
    cmp #SAME_TAD_LAST_SONG+1
    bcc Same_Tad_RequestSong__valid
    pla
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
    rts
Same_Tad_RequestSong__valid:
    .a8
    lda.l SAME_TAD_STATE
    cmp #$80
    bcs Same_Tad_RequestSong__ready
    pla
    lda.l SAME_TAD_REJECTED
    inc
    sta.l SAME_TAD_REJECTED
    rts
Same_Tad_RequestSong__ready:
    .a8
    pla
    sta.l SAME_TAD_NEXT_SONG
    .if SAME_BUILD_SCUMM_M22
    lda #$00
    sta.l SAME_TAD_BOUNDARY_TOKEN
    lda.l SAME_TAD_SECTION_DEFERRED
    cmp #$FF
    bne Same_Tad_RequestSong__section_selected
    lda #$00
    sta.l SAME_TAD_SECTION_DEFERRED
Same_Tad_RequestSong__section_selected:
    .a8
    .endif
    lda #SAME_TAD_STATE_WAIT_SONG
    sta.l SAME_TAD_STATE
    lda #SAME_TAD_SWITCH_LOADER
    sta APUIO3
    rts

; A8 data item: zero selects common audio, song IDs select their compiled data.
; The compiler table stores asar-mapped offsets; subtract its 51-byte callback
; bias to recover offsets from Same_Tad_AudioData. Carry reports invalid input.
Same_Tad_SelectDataItem:
    rep #$30
    .a16
    .i16
    and #$00FF
    cmp #SAME_TAD_DATA_ITEM_COUNT
    bcs Same_Tad_SelectDataItem__invalid
    sta.l SAME_TAD_TRANSFER_SIZE
    asl
    clc
    adc.l SAME_TAD_TRANSFER_SIZE
    tax
    lda.l $018000+SAME_TAD_DATA_TABLE_OFFSET+3,x
    sec
    sbc.l $018000+SAME_TAD_DATA_TABLE_OFFSET,x
    sta.l SAME_TAD_TRANSFER_SIZE
    lda.l $018000+SAME_TAD_DATA_TABLE_OFFSET,x
    sec
    sbc #SAME_TAD_ASAR_LOROM_BIAS
    sta.l SAME_TAD_TRANSFER_OFFSET
    sep #$20
    .a8
    clc
    rts
Same_Tad_SelectDataItem__invalid:
    sep #$20
    .a8
    sec
    rts

; Initialize the official TAD loader and upload its 3218-byte driver. Common
; data and the initial blank song are then delivered incrementally per frame.
Same_Tad_Init:
    sep #$20
    .a8
    stz APUIO0
    rep #$10
    .i16
    ldy #$BBAA
Same_Tad_Init__wait_ipl:
    .a8
    .i16
    cpy APUIO0
    bne Same_Tad_Init__wait_ipl
    ldx #$0200
    lda #$CC
    stx APUIO2
    sta APUIO1
    sta APUIO0
Same_Tad_Init__wait_command:
    cmp APUIO0
    bne Same_Tad_Init__wait_command
    sep #$10
    .i8
    ldx #$00
Same_Tad_Init__loader_loop:
    lda.l Same_Tad_AudioData,x
    sta APUIO1
    stx APUIO0
Same_Tad_Init__loader_ack:
    .a8
    .i8
    cpx APUIO0
    bne Same_Tad_Init__loader_ack
    inx
    cpx #$74
    bcc Same_Tad_Init__loader_loop
    rep #$10
    .i16
    ldx #$0200
    stx APUIO2
    stz APUIO1
    lda #$76
    sta APUIO0
    rep #$20
    .a16
    lda #SAME_TAD_AUDIO_DRIVER_OFFSET
    sta.l SAME_TAD_TRANSFER_OFFSET
    lda #SAME_TAD_AUDIO_DRIVER_SIZE
    sta.l SAME_TAD_TRANSFER_SIZE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_TAD_TRANSFER_SPIN
    lda #$FF
    sta.l SAME_TAD_NEXT_COMMAND
    lda #$00
    sta.l SAME_TAD_NEXT_SONG
Same_Tad_Init__type:
    .a8
    .i16
    lda #$00
    jsr Same_Tad_CheckAndSendType
    bcc Same_Tad_Init__type
Same_Tad_Init__driver:
    .a8
    .i16
    jsr Same_Tad_Transfer
    bcc Same_Tad_Init__driver
    lda #SAME_TAD_STATE_WAIT_COMMON
    sta.l SAME_TAD_STATE
    rts

; A8 type. Carry set only when loader has accepted it.
Same_Tad_CheckAndSendType:
    rep #$10
    .i16
    ldx #$444C
    cpx APUIO2
    bne Same_Tad_CheckAndSendType__no
    sta APUIO1
    lda #$4C
    sta APUIO2
    lda #$44
    sta APUIO3
    lda #$00
    sta.l SAME_TAD_TRANSFER_SPIN
    sec
    rts
Same_Tad_CheckAndSendType__no:
    clc
    rts

; Transfer at most 256 bytes (128 words) from the two-bank audio blob.
; Carry reports completion; loader acknowledgement prevents silent drops.
Same_Tad_Transfer:
    sep #$20
    .a8
    lda.l SAME_TAD_TRANSFER_SPIN
    cmp APUIO3
    bne Same_Tad_Transfer__pending
    rep #$30
    .a16
    .i16
    lda.l SAME_TAD_TRANSFER_SIZE
    cmp #$0100
    bcc Same_Tad_Transfer__count
    lda #$0100
Same_Tad_Transfer__count:
    .a16
    .i16
    inc
    lsr
    tay
    asl
    eor #$FFFF
    sec
    adc.l SAME_TAD_TRANSFER_SIZE
    bcs Same_Tad_Transfer__size_ok
    lda #$0000
Same_Tad_Transfer__size_ok:
    sta.l SAME_TAD_TRANSFER_SIZE
    lda.l SAME_TAD_TRANSFER_OFFSET
    tax
    sep #$20
    .a8
Same_Tad_Transfer__loop:
    .a8
    .i16
    jsr Same_Tad_ReadByte
    sta APUIO1
    inx
    jsr Same_Tad_ReadByte
    sta APUIO2
    txa
    and #$07
    inc
    sta APUIO3
    inx
    dey
    beq Same_Tad_Transfer__block_done
Same_Tad_Transfer__ack:
    cmp APUIO3
    bne Same_Tad_Transfer__ack
    bra Same_Tad_Transfer__loop
Same_Tad_Transfer__block_done:
    sta.l SAME_TAD_TRANSFER_SPIN
    rep #$20
    .a16
    txa
    sta.l SAME_TAD_TRANSFER_OFFSET
    lda.l SAME_TAD_TRANSFER_SIZE
    bne Same_Tad_Transfer__pending16
    sep #$20
    .a8
Same_Tad_Transfer__final_ack:
    .a8
    .i16
    lda.l SAME_TAD_TRANSFER_SPIN
    cmp APUIO3
    bne Same_Tad_Transfer__final_ack
    lda #$80
    sta APUIO3
    sec
    rts
Same_Tad_Transfer__pending16:
    sep #$20
    .a8
Same_Tad_Transfer__pending:
    clc
    rts

; Read one byte by linear TAD offset X. LoROM's second 32 KiB bank is not
; numerically contiguous with bank 1, so offsets >= $8000 use a corrected base.
Same_Tad_ReadByte:
    .a8
    .i16
    cpx #SAME_TAD_LOROM_SPLIT
    bcs Same_Tad_ReadByte__high
    lda.l Same_Tad_AudioData,x
    rts
Same_Tad_ReadByte__high:
    .a8
    lda.l $020000,x
    rts

; Map a logical sound id in A to a compiled TAD song id in A. Carry is clear on
; success. The profile-owned table is generated only after catalog schema and
; TAD enum validation; this backend contains no engine, title, or cue policy.
Same_Tad_MapSound:
    .a8
    .i16
    ldx #$0000
Same_Tad_MapSound__next:
    .a8
    .i16
    cpx #(SAME_MUSIC_CATALOG_COUNT * 2)
    bcs Same_Tad_MapSound__missing
    cmp.l Same_Music_Catalog,x
    beq Same_Tad_MapSound__found
    inx
    inx
    bra Same_Tad_MapSound__next
Same_Tad_MapSound__found:
    .a8
    .i16
    inx
    lda.l Same_Music_Catalog,x
    clc
    rts
Same_Tad_MapSound__missing:
    .a8
    sec
    rts

; Profile-owned route records are (logical id, route kind, route value,
; compiled song).  They let an engine name semantic routes without knowing a
; title's final TAD song numbers.  Packet arg1 stores value in its low byte and
; kind in its high byte.
.if SAME_BUILD_SCUMM_M21
Same_Tad_HasRoutes:
    .a8
    .i16
    pha
    ldx #$0000
Same_Tad_HasRoutes__next:
    .a8
    .i16
    cpx #(SAME_MUSIC_ROUTE_COUNT * 4)
    bcs Same_Tad_HasRoutes__missing
    pla
    pha
    cmp.l Same_Music_Routes,x
    beq Same_Tad_HasRoutes__found
    inx
    inx
    inx
    inx
    bra Same_Tad_HasRoutes__next
Same_Tad_HasRoutes__found:
    pla
    clc
    rts
Same_Tad_HasRoutes__missing:
    pla
    sec
    rts

Same_Tad_MapRoute:
    .a8
    .i16
    pha
    ldx #$0000
Same_Tad_MapRoute__next:
    .a8
    .i16
    cpx #(SAME_MUSIC_ROUTE_COUNT * 4)
    bcs Same_Tad_MapRoute__missing
    pla
    pha
    cmp.l Same_Music_Routes,x
    bne Same_Tad_MapRoute__advance
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+1
    cmp.l Same_Music_Routes+1,x
    bne Same_Tad_MapRoute__advance
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    cmp.l Same_Music_Routes+2,x
    bne Same_Tad_MapRoute__advance
    pla
    lda.l Same_Music_Routes+3,x
    clc
    rts
Same_Tad_MapRoute__advance:
    inx
    inx
    inx
    inx
    bra Same_Tad_MapRoute__next
Same_Tad_MapRoute__missing:
    pla
    sec
    rts
.endif

.include "../generated/music_catalog.inc.pasm"
