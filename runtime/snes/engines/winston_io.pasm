; Copyright-free bounded checked-read and MSU-PCM fixture client.
; All package reads use SAME storage state; all PCM register writes use the
; SAME MSU audio service. The engine never touches MSU hardware addresses.
SAME_ACTIVE_ENGINE_ID = SAME_ENGINE_WINSTON_IO
SAME_WINSTON_IO_STATUS_INIT   = $00
SAME_WINSTON_IO_STATUS_TESTS  = $01
SAME_WINSTON_IO_STATUS_PASS   = $02
SAME_WINSTON_IO_STATUS_ASSETS = $03
SAME_WINSTON_IO_STATUS_FAIL   = $FF
SAME_WINSTON_IO_TILE_BYTES    = $5000
SAME_WINSTON_IO_TILE_CHUNK    = $0800
; BG12NBA is in VRAM words; DMA requests use byte addresses.
SAME_WINSTON_IO_TILE_BASE     = $4000
SAME_WINSTON_IO_MAP_BYTES     = $0800
SAME_WINSTON_IO_PALETTE_BYTES = $0020

SAME_WINSTON_IO_ASSET_GATE    = $01
SAME_WINSTON_IO_ASSET_MAP     = $02
SAME_WINSTON_IO_ASSET_PALETTE = $03
SAME_WINSTON_IO_ASSET_OPEN    = $04
SAME_WINSTON_IO_ASSET_VERGE   = $05
SAME_WINSTON_IO_ASSET_SLATE   = $06
SAME_WINSTON_IO_ASSET_TRACK2  = $07
SAME_WINSTON_IO_SUB_READ      = $00
SAME_WINSTON_IO_SUB_QUEUE     = $01
SAME_WINSTON_IO_SUB_PENDING   = $02

Same_ActiveEngine_Boot:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_WINSTON_IO_CASES_PASSED
    sta.l SAME_WINSTON_IO_TOTAL_READS
    sta.l SAME_WINSTON_IO_REJECTS
    lda #$FFFF
    sta.l SAME_WINSTON_IO_FAILED_CASE
    lda #SAME_MSU1_TEST_CASE_COUNT
    sta.l SAME_WINSTON_IO_CASES_EXPECTED
    sep #$20
    .a8
    lda #$00
    sta.l SAME_WINSTON_IO_CASE_INDEX
    sta.l SAME_WINSTON_IO_AUDIO_STARTED
    sta.l SAME_WINSTON_IO_DEST_MODE
    sta.l SAME_WINSTON_IO_SAMPLE_LENGTH
    sta.l SAME_WINSTON_IO_COMPARE_INDEX
    sta.l SAME_WINSTON_IO_EXPECTED_STATUS
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    sta.l SAME_WINSTON_IO_SCENE_ID
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    sta.l SAME_WINSTON_IO_ASSET_SECTION
    sta.l SAME_WINSTON_IO_ASSET_SIZE
    sta.l SAME_WINSTON_IO_ASSET_READS
    sta.l SAME_WINSTON_IO_ASSET_CRC_OK
    sta.l SAME_WINSTON_IO_ASSET_FAILURE
    sta.l SAME_WINSTON_IO_TILE_DMA_COUNT
    sta.l SAME_WINSTON_IO_AUDIO_CHECK_FRAMES
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_WINSTON_IO_TILE_OFFSET
    sta.l SAME_WINSTON_IO_ASSET_SECTION
    sta.l SAME_WINSTON_IO_ASSET_SIZE
    sta.l SAME_WINSTON_IO_ASSET_READS
    sta.l SAME_WINSTON_IO_TILE_DMA_COUNT
    sta.l SAME_WINSTON_IO_AUDIO_CHECK_FRAMES
    sep #$20
    .a8
    lda #$A5
    sta.l SAME_WINSTON_IO_GUARD_BEFORE
    sta.l SAME_WINSTON_IO_GUARD_AFTER
    lda #$00
    sta.l SAME_WINSTON_IO_STATUS
    rep #$10
    .i16
    ldx #$0000
Same_ActiveEngine_Boot__clear_ring:
    .a8
    lda #$A5
    sta.l SAME_WINSTON_IO_RING,x
    inx
    cpx #SAME_WINSTON_IO_RING_SIZE
    bcc Same_ActiveEngine_Boot__clear_ring
    jsr Same_Msu1_InitBegin
    bcs Same_ActiveEngine_Boot__init_failed
    plp
    clc
    rts
Same_ActiveEngine_Boot__init_failed:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_WINSTON_IO_STATUS
    plp
    sec
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
    lda.l SAME_WINSTON_IO_STATUS
    cmp #SAME_WINSTON_IO_STATUS_PASS
    beq Same_ActiveEngine_Frame__done
    cmp #SAME_WINSTON_IO_STATUS_FAIL
    beq Same_ActiveEngine_Frame__done
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_ERROR
    beq Same_ActiveEngine_Frame__provider_failed
    lda.l SAME_WINSTON_IO_STATUS
    cmp #SAME_WINSTON_IO_STATUS_ASSETS
    beq Same_ActiveEngine_Frame__assets
    lda.l SAME_WINSTON_IO_STATUS
    beq Same_ActiveEngine_Frame__initializing
    jsr Same_WinstonIO_CheckCurrentCase
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__assets:
    jsr Same_WinstonIO_AssetFrame
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__initializing:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READY
    bne Same_ActiveEngine_Frame__done
    lda #SAME_WINSTON_IO_STATUS_TESTS
    sta.l SAME_WINSTON_IO_STATUS
    rep #$30
    .a16
    .i16
    lda #$0001
    ldx #$0001 ; loop the fixture's copyright-free clock track
    jsr Same_Msu1_Audio_Play
    jsr Same_Msu1_Audio_Status
    .a8
    and #SAME_MSU1_AUDIO_ERROR_BIT
    bne Same_ActiveEngine_Frame__fail
    sep #$20
    .a8
    lda #$01
    sta.l SAME_WINSTON_IO_AUDIO_STARTED
    jsr Same_WinstonIO_BeginCase
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__provider_failed:
    .a8
.if SAME_BUILD_MSU1_TEST_FORCE_BUSY
    lda.l SAME_MSU1_ERROR
    cmp #SAME_MSU1_ERROR_BUSY
    bne Same_ActiveEngine_Frame__fail
    lda #$02 ; the diagnostic timeout control expects a bounded BUSY error
    sta.l SAME_WINSTON_IO_STATUS
    bra Same_ActiveEngine_Frame__done
.else
    lda.l SAME_WINSTON_IO_STATUS
    cmp #SAME_WINSTON_IO_STATUS_ASSETS
    beq Same_ActiveEngine_Frame__asset_provider_failed
    bra Same_ActiveEngine_Frame__fail
.endif
Same_ActiveEngine_Frame__asset_provider_failed:
    jsr Same_WinstonIO_AssetFail
    bra Same_ActiveEngine_Frame__done

Same_ActiveEngine_Frame__fail:
    .a8
    lda #$FF
    sta.l SAME_WINSTON_IO_STATUS
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    sta.l SAME_WINSTON_IO_FAILED_CASE
Same_ActiveEngine_Frame__done:
    rep #$30
    .a16
    .i16
    plp
    clc
    rts

; Generated record layout: offset u32, length u32, CRC32 u32, expected status,
; sample length, 32 expected leading bytes, then two reserved bytes (48 total).
Same_WinstonIO_BeginCase:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    and #$00FF
    sta.l SAME_WINSTON_IO_TEMP
    asl
    clc
    adc.l SAME_WINSTON_IO_TEMP
    asl
    asl
    asl
    asl ; case index * 48
    tax
    sep #$20
    .a8
    lda.l Same_Msu1_TestCases,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    lda.l Same_Msu1_TestCases+1,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    lda.l Same_Msu1_TestCases+2,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    lda.l Same_Msu1_TestCases+3,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    lda.l Same_Msu1_TestCases+4,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    lda.l Same_Msu1_TestCases+5,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    lda.l Same_Msu1_TestCases+6,x
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    lda.l Same_Msu1_TestCases+7,x
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l Same_Msu1_TestCases+8,x
    sta.l SAME_MSU1_EXPECTED_CRC
    lda.l Same_Msu1_TestCases+9,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    lda.l Same_Msu1_TestCases+10,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    lda.l Same_Msu1_TestCases+11,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    lda.l Same_Msu1_TestCases+12,x
    sta.l SAME_WINSTON_IO_EXPECTED_STATUS
    lda.l Same_Msu1_TestCases+13,x
    sta.l SAME_WINSTON_IO_SAMPLE_LENGTH
    lda.l SAME_WINSTON_IO_EXPECTED_STATUS
    bne Same_WinstonIO_BeginCase__prepare_reject
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    ora.l SAME_MSU1_REQUEST_LENGTH+3
    bne Same_WinstonIO_BeginCase__ring
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #SAME_WINSTON_IO_STAGE_SIZE+1
    bcs Same_WinstonIO_BeginCase__ring16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MSU1_FLAGS
    sta.l SAME_WINSTON_IO_DEST_MODE
    lda #<SAME_WINSTON_IO_STAGE
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_WINSTON_IO_STAGE
    sta.l SAME_MSU1_DESTINATION+1
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
    rep #$20
    .a16
    lda #SAME_WINSTON_IO_STAGE_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    bra Same_WinstonIO_BeginCase__request
Same_WinstonIO_BeginCase__prepare_reject:
    phx
    rep #$10
    .i16
    ldx #$0000
Same_WinstonIO_BeginCase__clear_reject_ring:
    .a8
    lda #$A5
    sta.l SAME_WINSTON_IO_RING,x
    inx
    cpx #SAME_WINSTON_IO_RING_SIZE
    bcc Same_WinstonIO_BeginCase__clear_reject_ring
    sep #$20
    .a8
    lda #$A5
    sta.l SAME_WINSTON_IO_GUARD_BEFORE
    sta.l SAME_WINSTON_IO_GUARD_AFTER
    plx
    bra Same_WinstonIO_BeginCase__ring
Same_WinstonIO_BeginCase__ring16:
    .a8
    sep #$20
    .a8
Same_WinstonIO_BeginCase__ring:
    .a8
    lda #SAME_MSU1_FLAG_RING
    sta.l SAME_MSU1_FLAGS
    lda #$01
    sta.l SAME_WINSTON_IO_DEST_MODE
    lda #<SAME_WINSTON_IO_RING
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_WINSTON_IO_RING
    sta.l SAME_MSU1_DESTINATION+1
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
    rep #$20
    .a16
    lda #SAME_WINSTON_IO_RING_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
Same_WinstonIO_BeginCase__request:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_WINSTON_IO_COMPARE_INDEX
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_TOTAL_READS
    inc
    sta.l SAME_WINSTON_IO_TOTAL_READS
    jsr Same_Msu1_ReadBegin
    bcc Same_WinstonIO_BeginCase__return
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_EXPECTED_STATUS
    beq Same_WinstonIO_BeginCase__failed
    lda.l SAME_MSU1_ERROR
    cmp #SAME_MSU1_ERROR_RANGE
    bne Same_WinstonIO_BeginCase__failed
    jsr Same_WinstonIO_CheckRingCanary
    bcs Same_WinstonIO_BeginCase__failed
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_REJECTS
    inc
    sta.l SAME_WINSTON_IO_REJECTS
    jsr Same_WinstonIO_AcceptCurrentCase
    bra Same_WinstonIO_BeginCase__return
Same_WinstonIO_BeginCase__failed:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_WINSTON_IO_STATUS
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    sta.l SAME_WINSTON_IO_FAILED_CASE
    plp
    rts
Same_WinstonIO_BeginCase__return:
    plp
    rts

Same_WinstonIO_CheckCurrentCase:
    php
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    beq Same_WinstonIO_CheckCurrentCase__done
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READ_OK
    beq Same_WinstonIO_CheckCurrentCase__success
    cmp #SAME_MSU1_STATE_ERROR
    beq Same_WinstonIO_CheckCurrentCase__rejected
    bra Same_WinstonIO_CheckCurrentCase__done
Same_WinstonIO_CheckCurrentCase__success:
    ; Only a range-reject fixture may complete with a nonzero expected status.
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_EXPECTED_STATUS
    bne Same_WinstonIO_CheckCurrentCase__fail
    jsr Same_WinstonIO_CompareSample
    bcs Same_WinstonIO_CheckCurrentCase__fail
    bra Same_WinstonIO_CheckCurrentCase__passed
Same_WinstonIO_CheckCurrentCase__rejected:
    .a8
    lda.l SAME_WINSTON_IO_EXPECTED_STATUS
    beq Same_WinstonIO_CheckCurrentCase__fail
    lda.l SAME_MSU1_ERROR
    cmp #SAME_MSU1_ERROR_RANGE
    bne Same_WinstonIO_CheckCurrentCase__fail
    jsr Same_WinstonIO_CheckRingCanary
    bcs Same_WinstonIO_CheckCurrentCase__fail
Same_WinstonIO_CheckCurrentCase__passed:
    jsr Same_WinstonIO_AcceptCurrentCase
    bra Same_WinstonIO_CheckCurrentCase__done
Same_WinstonIO_AcceptCurrentCase:
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_CASES_PASSED
    inc
    sta.l SAME_WINSTON_IO_CASES_PASSED
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_CASE_INDEX
    inc
    sta.l SAME_WINSTON_IO_CASE_INDEX
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    and #$00FF
    cmp.l SAME_WINSTON_IO_CASES_EXPECTED
    bcc Same_WinstonIO_AcceptCurrentCase__next
    sep #$20
    .a8
    lda #SAME_WINSTON_IO_STATUS_ASSETS
    sta.l SAME_WINSTON_IO_STATUS
    jsr Same_WinstonIO_StartAssetDemo
    rts
Same_WinstonIO_AcceptCurrentCase__next:
    jsr Same_WinstonIO_BeginCase
    rts
Same_WinstonIO_CheckCurrentCase__fail:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_WINSTON_IO_STATUS
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    sta.l SAME_WINSTON_IO_FAILED_CASE
Same_WinstonIO_CheckCurrentCase__done:
    plp
    rts

Same_WinstonIO_CompareSample:
    ; Short host-oracle samples occupy record bytes 14..45. Larger streaming
    ; cases carry no sample and are certified by the generated expected CRC.
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_SAMPLE_LENGTH
    beq Same_WinstonIO_CompareSample__ok
    lda.l SAME_WINSTON_IO_DEST_MODE
    cmp #$01
    beq Same_WinstonIO_CompareSample__ok
    rep #$30
    .a16
    .i16
    lda.l SAME_WINSTON_IO_CASE_INDEX
    and #$00FF
    sta.l SAME_WINSTON_IO_TEMP
    asl
    clc
    adc.l SAME_WINSTON_IO_TEMP
    asl
    asl
    asl
    asl ; case index * 48
    tax
    sep #$20
    .a8
    lda #<SAME_WINSTON_IO_STAGE
    sta SAME_MSU1_DP_DEST
    lda #>SAME_WINSTON_IO_STAGE
    sta SAME_MSU1_DP_DEST+1
    lda #$7E
    sta SAME_MSU1_DP_DEST+2
    lda #$00
    sta.l SAME_WINSTON_IO_COMPARE_INDEX
Same_WinstonIO_CompareSample__loop:
    lda.l SAME_WINSTON_IO_COMPARE_INDEX
    cmp.l SAME_WINSTON_IO_SAMPLE_LENGTH
    bcs Same_WinstonIO_CompareSample__ok
    rep #$30
    .a16
    .i16
    lda.l SAME_WINSTON_IO_COMPARE_INDEX
    and #$00FF
    tay
    sep #$20
    .a8
    lda.l Same_Msu1_TestCases+14,x
    cmp [SAME_MSU1_DP_DEST],y
    bne Same_WinstonIO_CompareSample__bad
    inx
    lda.l SAME_WINSTON_IO_COMPARE_INDEX
    inc
    sta.l SAME_WINSTON_IO_COMPARE_INDEX
    bra Same_WinstonIO_CompareSample__loop
Same_WinstonIO_CompareSample__ok:
    clc
    rts
Same_WinstonIO_CompareSample__bad:
    sec
    rts

Same_WinstonIO_CheckRingCanary:
    php
    rep #$30
    .a16
    .i16
    ldx #$0000
Same_WinstonIO_CheckRingCanary__loop:
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_RING,x
    cmp #$A5
    bne Same_WinstonIO_CheckRingCanary__bad
    rep #$30
    .a16
    .i16
    inx
    cpx #SAME_WINSTON_IO_RING_SIZE
    bcc Same_WinstonIO_CheckRingCanary__loop
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_GUARD_BEFORE
    cmp #$A5
    bne Same_WinstonIO_CheckRingCanary__bad
    lda.l SAME_WINSTON_IO_GUARD_AFTER
    cmp #$A5
    bne Same_WinstonIO_CheckRingCanary__bad
    plp
    clc
    rts
Same_WinstonIO_CheckRingCanary__bad:
    plp
    sec
    rts

; File-backed diagnostic asset sequence. Each section is selected only through
; the generated, package-verified directory. The complete resource is CRC
; checked into engine-owned staging before any DMA descriptor is published.
Same_WinstonIO_StartAssetDemo:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_WINSTON_IO_TILE_OFFSET
    sep #$20
    .a8
    lda #SAME_WINSTON_IO_ASSET_GATE
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    lda #$00
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    ldx #$0000
    lda #101
    jsr Same_WinstonIO_PlaySpeechAndRead
    bcs Same_WinstonIO_StartAssetDemo__failed
    plp
    rts
Same_WinstonIO_StartAssetDemo__failed:
    jsr Same_WinstonIO_AssetFail
    plp
    rts

Same_WinstonIO_AssetFrame:
    php
    rep #$30
    .a16
    .i16
    jsr Same_Msu1_Audio_Status
    .a8
    and #SAME_MSU1_AUDIO_ERROR_BIT
    beq Same_WinstonIO_AssetFrame__audio_ok
    jmp Same_WinstonIO_AssetFrame__fail
Same_WinstonIO_AssetFrame__audio_ok:
    .a8
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    cmp #SAME_WINSTON_IO_ASSET_TRACK2
    bne Same_WinstonIO_AssetFrame__not_track2
    jsr Same_WinstonIO_Track2Frame
    bcc Same_WinstonIO_AssetFrame__track2_ok
    jmp Same_WinstonIO_AssetFrame__fail
Same_WinstonIO_AssetFrame__track2_ok:
    .a8
    jmp Same_WinstonIO_AssetFrame__done
Same_WinstonIO_AssetFrame__not_track2:
    .a8
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_ASSET_SUBSTATE
    beq Same_WinstonIO_AssetFrame__await_read
    cmp #SAME_WINSTON_IO_SUB_QUEUE
    beq Same_WinstonIO_AssetFrame__queue
    jsr Same_WinstonIO_AssetWaitDma
    jmp Same_WinstonIO_AssetFrame__done
Same_WinstonIO_AssetFrame__await_read:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READ_OK
    beq Same_WinstonIO_AssetFrame__read_ok
    jmp Same_WinstonIO_AssetFrame__done
Same_WinstonIO_AssetFrame__read_ok:
    .a8
    lda #$01
    sta.l SAME_WINSTON_IO_ASSET_CRC_OK
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_WINSTON_IO_ASSET_SIZE
    lda.l SAME_WINSTON_IO_ASSET_READS
    inc
    sta.l SAME_WINSTON_IO_ASSET_READS
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    cmp #SAME_WINSTON_IO_ASSET_PALETTE
    bne Same_WinstonIO_AssetFrame__palette_ready
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_STAGE
    jsr Same_Video_SetBackdrop
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_ASSET_STAGE
Same_WinstonIO_AssetFrame__palette_ready:
    .a8
    cmp #SAME_WINSTON_IO_ASSET_GATE
    beq Same_WinstonIO_AssetFrame__tile_setup
    cmp #SAME_WINSTON_IO_ASSET_MAP
    beq Same_WinstonIO_AssetFrame__map_ready
    cmp #SAME_WINSTON_IO_ASSET_PALETTE
    beq Same_WinstonIO_AssetFrame__map_ready
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_WINSTON_IO_TILE_OFFSET
    sep #$20
    .a8
    lda #$80
    jsr Same_Video_SetDisplay
Same_WinstonIO_AssetFrame__tile_setup:
    .a8
    lda #SAME_WINSTON_IO_SUB_QUEUE
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    bra Same_WinstonIO_AssetFrame__done
Same_WinstonIO_AssetFrame__map_ready:
    .a8
    lda #SAME_WINSTON_IO_SUB_QUEUE
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    bra Same_WinstonIO_AssetFrame__done

Same_WinstonIO_AssetFrame__queue:
    .a8
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    cmp #SAME_WINSTON_IO_ASSET_MAP
    beq Same_WinstonIO_AssetFrame__queue_map
    cmp #SAME_WINSTON_IO_ASSET_PALETTE
    beq Same_WinstonIO_AssetFrame__queue_palette
    jsr Same_WinstonIO_QueueTileChunk
    bcs Same_WinstonIO_AssetFrame__fail
    bra Same_WinstonIO_AssetFrame__done
Same_WinstonIO_AssetFrame__queue_map:
    rep #$20
    .a16
    lda #SAME_WINSTON_IO_MAP_BYTES
    sta.l SAME_DMA_REQUEST_LENGTH
    lda #$0000
    sta.l SAME_DMA_REQUEST_TARGET
    bra Same_WinstonIO_AssetFrame__queue_single_vram
Same_WinstonIO_AssetFrame__queue_palette:
    rep #$20
    .a16
    lda #SAME_WINSTON_IO_PALETTE_BYTES
    sta.l SAME_DMA_REQUEST_LENGTH
    lda #$0000
    sta.l SAME_DMA_REQUEST_TARGET
    sep #$20
    .a8
    lda #SAME_DMA_TYPE_CGRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    bra Same_WinstonIO_AssetFrame__queue_single
Same_WinstonIO_AssetFrame__queue_single_vram:
    sep #$20
    .a8
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
Same_WinstonIO_AssetFrame__queue_single:
    rep #$20
    .a16
    lda #$6000 ; low 16 bits of the WRAM staging address $7E:6000
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    sep #$20
    .a8
    lda #$7E
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    jsr Same_Dma_Enqueue
    bcs Same_WinstonIO_AssetFrame__fail
    lda #SAME_WINSTON_IO_SUB_PENDING
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    bra Same_WinstonIO_AssetFrame__done

Same_WinstonIO_AssetFrame__fail:
    jsr Same_WinstonIO_AssetFail
Same_WinstonIO_AssetFrame__done:
    plp
    rts

Same_WinstonIO_Track2Frame:
    .a8
    jsr Same_Msu1_Audio_Status
    .a8
    and #SAME_MSU1_AUDIO_ERROR_BIT
    beq Same_WinstonIO_Track2Frame__no_error
    sec
    rts
Same_WinstonIO_Track2Frame__no_error:
    .a8
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_AUDIO_CHECK_FRAMES
    inc
    sta.l SAME_WINSTON_IO_AUDIO_CHECK_FRAMES
    cmp #$01F4 ; 500 frames exceeds track 2's 8-second first pass
    bcc Same_WinstonIO_Track2Frame__done
    sep #$20
    .a8
    lda.l SAME_MSU1_AUDIO_LAST_STATUS
    and #SAME_MSU1_AUDIO_PLAYING
    beq Same_WinstonIO_Track2Frame__bad
    lda.l SAME_MSU1_AUDIO_LAST_STATUS
    and #SAME_MSU1_AUDIO_LOOPING
    beq Same_WinstonIO_Track2Frame__bad
    lda #SAME_WINSTON_IO_STATUS_PASS
    sta.l SAME_WINSTON_IO_STATUS
Same_WinstonIO_Track2Frame__done:
    clc
    rts
Same_WinstonIO_Track2Frame__bad:
    sec
    rts

Same_WinstonIO_AssetWaitDma:
    rep #$20
    .a16
    lda.l SAME_DMA_PENDING
    bne Same_WinstonIO_AssetWaitDma__done
    sep #$20
    .a8
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    cmp #SAME_WINSTON_IO_ASSET_MAP
    beq Same_WinstonIO_AssetWaitDma__next
    cmp #SAME_WINSTON_IO_ASSET_PALETTE
    beq Same_WinstonIO_AssetWaitDma__next
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_TILE_OFFSET
    cmp #SAME_WINSTON_IO_TILE_BYTES
    bcs Same_WinstonIO_AssetWaitDma__next
    lda.l SAME_WINSTON_IO_TILE_OFFSET
    sta.l SAME_WINSTON_IO_TEMP
    clc
    adc #SAME_WINSTON_IO_TILE_CHUNK
    sta.l SAME_WINSTON_IO_TILE_OFFSET
    lda.l SAME_WINSTON_IO_TILE_DMA_COUNT
    inc
    sta.l SAME_WINSTON_IO_TILE_DMA_COUNT
    lda.l SAME_WINSTON_IO_TILE_OFFSET
    cmp #SAME_WINSTON_IO_TILE_BYTES
    bcs Same_WinstonIO_AssetWaitDma__next
    sep #$20
    .a8
    lda #SAME_WINSTON_IO_SUB_QUEUE
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    bra Same_WinstonIO_AssetWaitDma__done
Same_WinstonIO_AssetWaitDma__next:
    jsr Same_WinstonIO_AdvanceAsset
Same_WinstonIO_AssetWaitDma__done:
    rts

Same_WinstonIO_QueueTileChunk:
    rep #$20
    .a16
    lda.l SAME_DMA_PENDING
    bne Same_WinstonIO_QueueTileChunk__busy
    lda.l SAME_WINSTON_IO_TILE_OFFSET
    cmp #SAME_WINSTON_IO_TILE_BYTES
    bcs Same_WinstonIO_QueueTileChunk__bad
    sta.l SAME_WINSTON_IO_TEMP
    clc
    adc #$6000 ; add tile offset to the staging low word, not its low byte
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda.l SAME_WINSTON_IO_TEMP
    clc
    adc #SAME_WINSTON_IO_TILE_BASE
    sta.l SAME_DMA_REQUEST_TARGET
    lda #SAME_WINSTON_IO_TILE_CHUNK
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$7E
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    bcs Same_WinstonIO_QueueTileChunk__bad
    sep #$20
    .a8
    lda #SAME_WINSTON_IO_SUB_PENDING
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    clc
    rts
Same_WinstonIO_QueueTileChunk__busy:
    clc
    rts
Same_WinstonIO_QueueTileChunk__bad:
    sec
    rts

; Start the next data/audio stage only after the prior DMA has committed.
Same_WinstonIO_AdvanceAsset:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_WINSTON_IO_ASSET_SUBSTATE
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    cmp #SAME_WINSTON_IO_ASSET_GATE
    beq Same_WinstonIO_AdvanceAsset__map
    cmp #SAME_WINSTON_IO_ASSET_MAP
    beq Same_WinstonIO_AdvanceAsset__palette
    cmp #SAME_WINSTON_IO_ASSET_PALETTE
    beq Same_WinstonIO_AdvanceAsset__show_gate
    cmp #SAME_WINSTON_IO_ASSET_OPEN
    beq Same_WinstonIO_AdvanceAsset__show_open
    cmp #SAME_WINSTON_IO_ASSET_VERGE
    beq Same_WinstonIO_AdvanceAsset__show_verge
    cmp #SAME_WINSTON_IO_ASSET_SLATE
    bne Same_WinstonIO_AdvanceAsset__invalid_stage
    jmp Same_WinstonIO_AdvanceAsset__finish
Same_WinstonIO_AdvanceAsset__invalid_stage:
    jmp Same_WinstonIO_AdvanceAsset__fail
Same_WinstonIO_AdvanceAsset__map:
    .a8
    lda #SAME_WINSTON_IO_ASSET_MAP
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    ldx #SAME_MSU1_SECTION_BGTMAP_INDEX
    jsr Same_WinstonIO_BeginSection
    jmp Same_WinstonIO_AdvanceAsset__check
Same_WinstonIO_AdvanceAsset__palette:
    .a8
    lda #SAME_WINSTON_IO_ASSET_PALETTE
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    ldx #SAME_MSU1_SECTION_PAL16_INDEX
    jsr Same_WinstonIO_BeginSection
    jmp Same_WinstonIO_AdvanceAsset__check
Same_WinstonIO_AdvanceAsset__show_gate:
    rep #$30
    .a16
    .i16
    lda #$0001
    ldx #$0102
    jsr Same_Video_ConfigureBg1
    sep #$20
    .a8
    lda #$01
    sta.l SAME_WINSTON_IO_SCENE_ID
    lda #$0F
    jsr Same_Video_SetDisplay
    lda #SAME_WINSTON_IO_ASSET_OPEN
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    ldx #$0000
    lda #102
    jsr Same_WinstonIO_PlaySpeechAndRead
    bra Same_WinstonIO_AdvanceAsset__check
Same_WinstonIO_AdvanceAsset__show_open:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_WINSTON_IO_SCENE_ID
    lda #$0F
    jsr Same_Video_SetDisplay
    lda #SAME_WINSTON_IO_ASSET_VERGE
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    ldx #$0000
    lda #103
    jsr Same_WinstonIO_PlaySpeechAndRead
    bra Same_WinstonIO_AdvanceAsset__check
Same_WinstonIO_AdvanceAsset__show_verge:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_WINSTON_IO_SCENE_ID
    lda #$0F
    jsr Same_Video_SetDisplay
    lda #SAME_WINSTON_IO_ASSET_SLATE
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    ldx #$0000
    lda #104
    jsr Same_WinstonIO_PlaySpeechAndRead
    bra Same_WinstonIO_AdvanceAsset__check
Same_WinstonIO_AdvanceAsset__finish:
    sep #$20
    .a8
    lda #$04
    sta.l SAME_WINSTON_IO_SCENE_ID
    lda #$0F
    jsr Same_Video_SetDisplay
    rep #$30
    .a16
    .i16
    lda #$0002
    ldx #$0001 ; exercise track 2's nonzero loop point
    jsr Same_Msu1_Audio_Play
    sep #$20
    .a8
    lda #$00
    sta.l SAME_WINSTON_IO_AUDIO_CHECK_FRAMES
    lda #SAME_WINSTON_IO_ASSET_TRACK2
    sta.l SAME_WINSTON_IO_ASSET_STAGE
    bra Same_WinstonIO_AdvanceAsset__done
Same_WinstonIO_AdvanceAsset__check:
    bcs Same_WinstonIO_AdvanceAsset__fail
    rts
Same_WinstonIO_AdvanceAsset__fail:
    jsr Same_WinstonIO_AssetFail
Same_WinstonIO_AdvanceAsset__done:
    rts

; A8 = one-shot PCM track 101..104. Its corresponding generated section is
; selected from stage state; no engine code touches MSU data/audio registers.
Same_WinstonIO_PlaySpeechAndRead:
    php
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_MSU1_AUDIO_TRACK
    lda.l SAME_WINSTON_IO_ASSET_STAGE
    and #$00FF
    cmp #SAME_WINSTON_IO_ASSET_GATE
    beq Same_WinstonIO_PlaySpeechAndRead__gate
    cmp #SAME_WINSTON_IO_ASSET_OPEN
    beq Same_WinstonIO_PlaySpeechAndRead__open
    cmp #SAME_WINSTON_IO_ASSET_VERGE
    beq Same_WinstonIO_PlaySpeechAndRead__verge
    cmp #SAME_WINSTON_IO_ASSET_SLATE
    beq Same_WinstonIO_PlaySpeechAndRead__slate
    bra Same_WinstonIO_PlaySpeechAndRead__bad
Same_WinstonIO_PlaySpeechAndRead__gate:
    .a16
    .i16
    ldx #SAME_MSU1_SECTION_GATE4B_INDEX
    bra Same_WinstonIO_PlaySpeechAndRead__selected
Same_WinstonIO_PlaySpeechAndRead__open:
    .a16
    .i16
    ldx #SAME_MSU1_SECTION_OPEN4B_INDEX
    bra Same_WinstonIO_PlaySpeechAndRead__selected
Same_WinstonIO_PlaySpeechAndRead__verge:
    .a16
    .i16
    ldx #SAME_MSU1_SECTION_VERGE4B_INDEX
    bra Same_WinstonIO_PlaySpeechAndRead__selected
Same_WinstonIO_PlaySpeechAndRead__slate:
    .a16
    .i16
    ldx #SAME_MSU1_SECTION_SLATE4B_INDEX
Same_WinstonIO_PlaySpeechAndRead__selected:
    .a16
    .i16
    txa
    sta.l SAME_WINSTON_IO_ASSET_SECTION
    lda #$0000
    sta.l SAME_WINSTON_IO_ASSET_SIZE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_WINSTON_IO_ASSET_CRC_OK
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_AUDIO_TRACK
    ldx #$0000
    jsr Same_Msu1_Audio_Play
    jsr Same_Msu1_Audio_Status
    .a8
    and #SAME_MSU1_AUDIO_ERROR_BIT
    beq Same_WinstonIO_PlaySpeechAndRead__audio_ok
    lda.l SAME_MSU1_AUDIO_LAST_STATUS
    ora #$80
    sta.l SAME_WINSTON_IO_ASSET_FAILURE
    bra Same_WinstonIO_PlaySpeechAndRead__bad
Same_WinstonIO_PlaySpeechAndRead__audio_ok:
    .a8
    rep #$20
    .a16
    lda.l SAME_WINSTON_IO_ASSET_SECTION
    tax
    jsr Same_WinstonIO_BeginSection
    bcs Same_WinstonIO_PlaySpeechAndRead__bad
    plp
    clc
    rts
Same_WinstonIO_PlaySpeechAndRead__bad:
    plp
    sec
    rts

Same_WinstonIO_BeginSection:
    ; X16 is a generated section index. The package directory supplies offset,
    ; exact size, and CRC; destination is bounded to the 20-KiB staging region.
    php
    rep #$30
    .a16
    .i16
    txa
    sta.l SAME_WINSTON_IO_ASSET_SECTION
    lda #$6000
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_WINSTON_IO_STAGE
    sta.l SAME_MSU1_DESTINATION+1
    sep #$20
    .a8
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
    lda #$00
    sta.l SAME_MSU1_FLAGS
    rep #$20
    .a16
    lda #SAME_WINSTON_IO_STAGE_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    lda.l SAME_WINSTON_IO_ASSET_SECTION
    tax
    lda.l SAME_WINSTON_IO_TOTAL_READS
    inc
    sta.l SAME_WINSTON_IO_TOTAL_READS
    jsr Same_Msu1_ReadSection
    bcs Same_WinstonIO_BeginSection__bad
    plp
    clc
    rts
Same_WinstonIO_BeginSection__bad:
    plp
    sec
    rts

Same_WinstonIO_AssetFail:
    sep #$20
    .a8
    lda.l SAME_MSU1_ERROR
    bne Same_WinstonIO_AssetFail__store
    lda.l SAME_WINSTON_IO_ASSET_FAILURE
    bne Same_WinstonIO_AssetFail__status
    lda #$FF ; non-provider DMA/audio/state-machine failure
Same_WinstonIO_AssetFail__store:
    .a8
    sta.l SAME_WINSTON_IO_ASSET_FAILURE
Same_WinstonIO_AssetFail__status:
    .a8
    lda #SAME_WINSTON_IO_STATUS_FAIL
    sta.l SAME_WINSTON_IO_STATUS
    rep #$20
    .a16
    lda #$FFFE
    sta.l SAME_WINSTON_IO_FAILED_CASE
    rts

Same_ActiveEngine_Suspend:
    clc
    rts
Same_ActiveEngine_Resume:
    clc
    rts
Same_ActiveEngine_Shutdown:
    jsr Same_Msu1_Audio_Stop
    clc
    rts
