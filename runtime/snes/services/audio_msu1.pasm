; SAME MSU-1 PCM service. Only this file owns MSU audio registers; engine and
; video clients submit a track/loop request through these service routines.
SAME_MSU1_AUDIO_PLAY_BIT   = $01
SAME_MSU1_AUDIO_REPEAT_BIT = $02
SAME_MSU1_AUDIO_ERROR_BIT  = $08
SAME_MSU1_AUDIO_PLAYING    = $10
SAME_MSU1_AUDIO_LOOPING    = $20
SAME_MSU1_AUDIO_BUSY       = $40

; Input: A16 = track number, X16 bit 0 = loop. One MSU PCM track is active at
; a time by device design. No independent MSU music/speech mixer is implied.
Same_Msu1_Audio_Play:
    php
    rep #$30
    .a16
    .i16
    sta.l SAME_MSU1_AUDIO_TRACK
    txa
    sta.l SAME_MSU1_AUDIO_FLAGS
    sep #$20
    .a8
    lda.l SAME_MSU1_AUDIO_TRACK
    sta.l MSU1_TRACK_LO
    lda.l SAME_MSU1_AUDIO_TRACK+1
    sta.l MSU1_TRACK_HI
    lda #$FF
    sta.l MSU1_VOLUME
    lda.l SAME_MSU1_AUDIO_FLAGS
    and #$01
    beq Same_Msu1_Audio_Play__one_shot
    lda #(SAME_MSU1_AUDIO_PLAY_BIT|SAME_MSU1_AUDIO_REPEAT_BIT)
    bra Same_Msu1_Audio_Play__control
Same_Msu1_Audio_Play__one_shot:
    .a8
    lda #SAME_MSU1_AUDIO_PLAY_BIT
Same_Msu1_Audio_Play__control:
    sta.l MSU1_CONTROL
    lda.l MSU1_STATUS
    sta.l SAME_MSU1_AUDIO_LAST_STATUS
    plp
    rts

Same_Msu1_Audio_Stop:
    php
    sep #$20
    .a8
    lda #$00
    sta.l MSU1_CONTROL
    lda.l MSU1_STATUS
    sta.l SAME_MSU1_AUDIO_LAST_STATUS
    plp
    rts

; A8 = current status snapshot. The caller must test the track-error bit
; independently from playing/audio-busy state.
Same_Msu1_Audio_Status:
    sep #$20
    .a8
    lda.l MSU1_STATUS
    sta.l SAME_MSU1_AUDIO_LAST_STATUS
    rts
