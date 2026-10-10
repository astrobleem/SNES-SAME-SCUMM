; SAME checked package reads on the MSU-1. This module is the sole owner of
; MSU data registers. A client fills SAME_MSU1_REQUEST_* and calls
; Same_Msu1_ReadBegin; Same_Storage_Process transfers a bounded quantum each
; logical frame and publishes READ_OK only after per-request CRC32 succeeds.

SAME_MSU1_STATE_OFF          = $00
SAME_MSU1_ERROR_NONE         = $00
SAME_MSU1_ERROR_NO_DEVICE    = $01
SAME_MSU1_ERROR_BUSY         = $02
SAME_MSU1_ERROR_IDENTITY     = $03
SAME_MSU1_ERROR_RANGE        = $04
SAME_MSU1_ERROR_CAPACITY     = $05
SAME_MSU1_ERROR_CRC          = $06
SAME_MSU1_STATE_RESET        = $00
SAME_MSU1_STATE_INITIALIZING = $01
SAME_MSU1_STATE_TAIL_CHECK   = $02
SAME_MSU1_STATE_READY        = $03
SAME_MSU1_STATE_READING      = $04
SAME_MSU1_STATE_READ_OK      = $05
SAME_MSU1_STATE_ERROR        = $FF
SAME_MSU1_FLAG_RING           = $01
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
; The indexed live-room package contains a full 57-KiB surface. 256 bytes is
; still a bounded per-service-turn quantum and keeps room transitions
; resumable; native input/NMI/audio controls certify this larger diagnostic
; personality budget. Other provider clients retain the accepted 64-byte cap.
SAME_MSU1_STEP_BUDGET         = $0100
.else
SAME_MSU1_STEP_BUDGET         = $0040
.endif
SAME_MSU1_BUSY_POLL_LIMIT     = $40
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
SAME_MSU1_MAX_CAPACITY        = $E000 ; audited SA-1 tile-shadow staging window
.else
SAME_MSU1_MAX_CAPACITY        = $8000
.endif
SAME_MSU1_DP_DEST             = $00D0 ; direct-page 24-bit WRAM destination

Same_Msu1_Reset:
    php
    rep #$30
    .a16
    .i16
    ldx #$0000
    lda #$0000
Same_Msu1_Reset__clear:
    .a16
    sta.l SAME_MSU1_STATE,x
    inx
    inx
    cpx #$0048
    bcc Same_Msu1_Reset__clear
    sep #$20
    .a8
    lda #SAME_MSU1_STATE_RESET
    sta.l SAME_MSU1_STATUS
    lda #SAME_MSU1_ERROR_NONE
    sta.l SAME_MSU1_ERROR
    plp
    rts

; Begin package identity validation. Reads the six-byte hardware ID, then the
; exact compiler-trusted 32-byte header + directory over subsequent frames.
Same_Msu1_InitBegin:
    php
    sep #$20
    .a8
    lda.l MSU1_ID0
    cmp #$53 ; 'S'
    bne Same_Msu1_InitBegin__no_device
    lda.l MSU1_ID1
    cmp #$2D ; '-'
    bne Same_Msu1_InitBegin__no_device
    lda.l MSU1_ID2
    cmp #$4D ; 'M'
    bne Same_Msu1_InitBegin__no_device
    lda.l MSU1_ID3
    cmp #$53 ; 'S'
    bne Same_Msu1_InitBegin__no_device
    lda.l MSU1_ID4
    cmp #$55 ; 'U'
    bne Same_Msu1_InitBegin__no_device
    lda.l MSU1_ID5
    cmp #$31 ; '1'
    bne Same_Msu1_InitBegin__no_device
    lda #$00
    sta.l SAME_MSU1_PREFIX_INDEX
    sta.l SAME_MSU1_PREFIX_INDEX+1
    sta.l SAME_MSU1_REQUEST_OFFSET
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    jsr Same_Msu1_Seek
    lda #SAME_MSU1_STATE_INITIALIZING
    sta.l SAME_MSU1_STATUS
    lda #SAME_MSU1_ERROR_NONE
    sta.l SAME_MSU1_ERROR
    plp
    clc
    rts
Same_Msu1_InitBegin__no_device:
    .a8
    lda #SAME_MSU1_ERROR_NO_DEVICE
    jsr Same_Msu1_Fail
    plp
    sec
    rts

; One bounded storage-service turn. Identity verification is also incremental;
; request copying uses SAME_MSU1_STEP_BUDGET and each not-ready poll is bounded.
Same_Msu1_Process:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_INITIALIZING
    beq Same_Msu1_Process__prefix
    cmp #SAME_MSU1_STATE_TAIL_CHECK
    beq Same_Msu1_Process__tail
    cmp #SAME_MSU1_STATE_READING
    beq Same_Msu1_Process__read
    bra Same_Msu1_Process__done
Same_Msu1_Process__prefix:
    jsr Same_Msu1_VerifyPrefixStep
    bra Same_Msu1_Process__done
Same_Msu1_Process__tail:
    jsr Same_Msu1_VerifyTail
    bra Same_Msu1_Process__done
Same_Msu1_Process__read:
    jsr Same_Msu1_ReadStep
Same_Msu1_Process__done:
    ; All status dispatch reaches this label in M=8, while the entry saved A,
    ; X, and Y under M=X=16. Restore those widths before balancing the stack.
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rts

Same_Msu1_VerifyPrefixStep:
    php
    rep #$30
    .a16
    .i16
    lda #SAME_MSU1_STEP_BUDGET
    sta.l SAME_MSU1_STEP_REMAINING
Same_Msu1_VerifyPrefixStep__loop:
    .a16
    lda.l SAME_MSU1_PREFIX_INDEX
    cmp #SAME_MSU1_TRUSTED_PREFIX_SIZE
    bcs Same_Msu1_VerifyPrefixStep__prefix_done
    jsr Same_Msu1_WaitDataReady
    bcs Same_Msu1_VerifyPrefixStep__done
    sep #$20
    .a8
    lda.l MSU1_DATA
    sta.l SAME_MSU1_BYTE_SCRATCH
    rep #$20
    .a16
    lda.l SAME_MSU1_PREFIX_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_MSU1_BYTE_SCRATCH
    cmp.l Same_Msu1_TrustedPrefix,x
    bne Same_Msu1_VerifyPrefixStep__identity
    rep #$20
    .a16
    lda.l SAME_MSU1_PREFIX_INDEX
    tax
    inx
    txa
    sta.l SAME_MSU1_PREFIX_INDEX
    lda.l SAME_MSU1_STEP_REMAINING
    dec
    sta.l SAME_MSU1_STEP_REMAINING
    bne Same_Msu1_VerifyPrefixStep__loop
    bra Same_Msu1_VerifyPrefixStep__done
Same_Msu1_VerifyPrefixStep__prefix_done:
    sep #$20
    .a8
    lda #SAME_MSU1_PACKAGE_LENGTH_BYTE0
    sec
    sbc #$01
    sta.l SAME_MSU1_REQUEST_OFFSET
    lda #SAME_MSU1_PACKAGE_LENGTH_BYTE1
    sbc #$00
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    lda #SAME_MSU1_PACKAGE_LENGTH_BYTE2
    sbc #$00
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    lda #SAME_MSU1_PACKAGE_LENGTH_BYTE3
    sbc #$00
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    jsr Same_Msu1_Seek
    lda #SAME_MSU1_STATE_TAIL_CHECK
    sta.l SAME_MSU1_STATUS
    bra Same_Msu1_VerifyPrefixStep__done
Same_Msu1_VerifyPrefixStep__identity:
    .a8
    lda #SAME_MSU1_ERROR_IDENTITY
    jsr Same_Msu1_Fail
Same_Msu1_VerifyPrefixStep__done:
    plp
    rts

Same_Msu1_VerifyTail:
    php
    jsr Same_Msu1_WaitDataReady
    bcs Same_Msu1_VerifyTail__done
    sep #$20
    .a8
    lda.l MSU1_DATA
    cmp #SAME_MSU1_EXPECT_LAST_BYTE
    bne Same_Msu1_VerifyTail__identity
    lda #SAME_MSU1_STATE_READY
    sta.l SAME_MSU1_STATUS
    lda #SAME_MSU1_ERROR_NONE
    sta.l SAME_MSU1_ERROR
    rep #$20
    .a16
    lda.l SAME_MSU1_VERIFY_COUNT
    inc
    sta.l SAME_MSU1_VERIFY_COUNT
    bra Same_Msu1_VerifyTail__done
Same_Msu1_VerifyTail__identity:
    .a8
    lda #SAME_MSU1_ERROR_IDENTITY
    jsr Same_Msu1_Fail
Same_Msu1_VerifyTail__done:
    plp
    rts

; Resolve a generated, compiler-verified SAMEPKG section record, then begin its
; checked read. X16 is the section index from the trusted generated directory.
; The caller owns destination/capacity/flags; no package offset is guessed.
Same_Msu1_ReadSection:
    php
    rep #$30
    .a16
    .i16
    txa
    cmp #SAME_MSU1_DIRECTORY_COUNT
    bcc Same_Msu1_ReadSection__index_valid
    jmp Same_Msu1_ReadSection__invalid
Same_Msu1_ReadSection__index_valid:
    sta.l SAME_MSU1_SECTION_TEMP
    asl
    clc
    adc.l SAME_MSU1_SECTION_TEMP
    asl
    asl ; generated record size is 12 bytes
    tax
    sep #$20
    .a8
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l Same_Msu1_SectionRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    jsr Same_Msu1_ReadBegin
    bcs Same_Msu1_ReadSection__failed
    plp
    clc
    rts
Same_Msu1_ReadSection__invalid:
    sep #$20
    .a8
    lda #SAME_MSU1_ERROR_RANGE
    jsr Same_Msu1_Fail
Same_Msu1_ReadSection__failed:
    plp
    sec
    rts

; Request descriptor is caller-filled in SAME_MSU1_REQUEST_*. Validate all
; arithmetic/capacity before seeking or writing. Flag bit 0 enables a bounded
; rolling window for streaming digest clients (e.g. >64-KiB integrity tests).
Same_Msu1_ReadBegin:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READY
    beq Same_Msu1_ReadBegin__ready
    cmp #SAME_MSU1_STATE_READ_OK
    beq Same_Msu1_ReadBegin__ready
    jml Same_Msu1_ReadBegin__state_error
Same_Msu1_ReadBegin__ready:
    ; Sum offset + length as a checked u32, rejecting carry out.
    clc
    lda.l SAME_MSU1_REQUEST_OFFSET
    adc.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_MSU1_END_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+1
    adc.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SAME_MSU1_END_OFFSET+1
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    adc.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_END_OFFSET+2
    lda.l SAME_MSU1_REQUEST_OFFSET+3
    adc.l SAME_MSU1_REQUEST_LENGTH+3
    sta.l SAME_MSU1_END_OFFSET+3
    bcc Same_Msu1_ReadBegin__no_u32_overflow
    jml Same_Msu1_ReadBegin__range_error
Same_Msu1_ReadBegin__no_u32_overflow:
    .a8
    ; Compare the exclusive end to the compiler-trusted package length.
    lda.l SAME_MSU1_END_OFFSET+3
    cmp #SAME_MSU1_PACKAGE_LENGTH_BYTE3
    bcc Same_Msu1_ReadBegin__range_ok
    beq Same_Msu1_ReadBegin__compare_length_byte2
    jml Same_Msu1_ReadBegin__range_error
Same_Msu1_ReadBegin__compare_length_byte2:
    .a8
    lda.l SAME_MSU1_END_OFFSET+2
    cmp #SAME_MSU1_PACKAGE_LENGTH_BYTE2
    bcc Same_Msu1_ReadBegin__range_ok
    beq Same_Msu1_ReadBegin__compare_length_byte1
    jml Same_Msu1_ReadBegin__range_error
Same_Msu1_ReadBegin__compare_length_byte1:
    .a8
    lda.l SAME_MSU1_END_OFFSET+1
    cmp #SAME_MSU1_PACKAGE_LENGTH_BYTE1
    bcc Same_Msu1_ReadBegin__range_ok
    beq Same_Msu1_ReadBegin__compare_length_byte0
    jml Same_Msu1_ReadBegin__range_error
Same_Msu1_ReadBegin__compare_length_byte0:
    .a8
    lda.l SAME_MSU1_END_OFFSET
    cmp #SAME_MSU1_PACKAGE_LENGTH_BYTE0
    bcc Same_Msu1_ReadBegin__range_ok
    beq Same_Msu1_ReadBegin__range_ok
    jml Same_Msu1_ReadBegin__range_error
Same_Msu1_ReadBegin__range_ok:
    ; Caller destination must be one bounded WRAM bank and at most 32 KiB.
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_CAPACITY
    bne Same_Msu1_ReadBegin__capacity_nonzero
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__capacity_nonzero:
    .a16
    cmp #SAME_MSU1_MAX_CAPACITY+1
    bcc Same_Msu1_ReadBegin__capacity_limit_ok
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__capacity_limit_ok:
    clc
    adc.l SAME_MSU1_DESTINATION
    bcc Same_Msu1_ReadBegin__destination_no_wrap
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__destination_no_wrap:
    sep #$20
    .a8
    lda.l SAME_MSU1_DESTINATION+2
    cmp #$7E
    beq Same_Msu1_ReadBegin__dest_bank_ok
    cmp #$7F
    beq Same_Msu1_ReadBegin__dest_bank_ok
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    cmp #$41 ; SA-1 BW-RAM tile-shadow window, independently layout-audited
    beq Same_Msu1_ReadBegin__dest_bwram_ok
    cmp #$40 ; only explicitly audited palette and pending-metadata ranges
    beq Same_Msu1_ReadBegin__dest_palette_ok
    .endif
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__dest_bank_ok:
    ; Ordinary WRAM buffers retain their 32 KiB ceiling even in a live-room
    ; build; only the explicitly audited BWRAM window may use the larger cap.
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_CAPACITY
    cmp #$8001
    bcc Same_Msu1_ReadBegin__destination_bank_limit_ok
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__destination_bank_limit_ok:
    sep #$20
    .a8
    bra Same_Msu1_ReadBegin__dest_capacity_ok
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
Same_Msu1_ReadBegin__dest_bwram_ok:
    rep #$20
    .a16
    ; The only large direct-read destination in this personality is the
    ; layout-audited indexed tile shadow at 41:0000. Do not treat every $41
    ; address as writable BWRAM or let a large read cross into CGRAM/reserved
    ; storage.
    lda.l SAME_MSU1_DESTINATION
    beq Same_Msu1_ReadBegin__bwram_base_ok
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__bwram_base_ok:
    .a16
    lda.l SAME_MSU1_DEST_CAPACITY
    cmp #$E001
    bcc Same_Msu1_ReadBegin__dest_capacity_ok16
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__dest_capacity_ok16:
    sep #$20
    .a8
    bra Same_Msu1_ReadBegin__dest_capacity_ok
.endif
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
Same_Msu1_ReadBegin__dest_palette_ok:
    sep #$20
    .a8
    lda.l SAME_MSU1_DESTINATION
    cmp #<SAME_BWRAM_LIVE_ROOM_PALETTE_STAGE
    bne Same_Msu1_ReadBegin__check_pending_address
    .a8
    lda.l SAME_MSU1_DESTINATION+1
    cmp #>SAME_BWRAM_LIVE_ROOM_PALETTE_STAGE
    beq Same_Msu1_ReadBegin__dest_palette_high_ok
Same_Msu1_ReadBegin__check_pending_address:
    .a8
    lda.l SAME_MSU1_DESTINATION
    cmp #<SAME_BWRAM_LIVE_ROOM_PENDING
    bne Same_Msu1_ReadBegin__dest_invalid
    lda.l SAME_MSU1_DESTINATION+1
    cmp #>SAME_BWRAM_LIVE_ROOM_PENDING
    bne Same_Msu1_ReadBegin__dest_invalid
Same_Msu1_ReadBegin__dest_pending_high_ok:
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_CAPACITY
    cmp #$0801
    bcc Same_Msu1_ReadBegin__dest_pending_capacity_ok16
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__dest_pending_capacity_ok16:
    sep #$20
    .a8
    bra Same_Msu1_ReadBegin__dest_capacity_ok
Same_Msu1_ReadBegin__dest_palette_low_ok:
    .a8
    lda.l SAME_MSU1_DESTINATION+1
    cmp #>SAME_BWRAM_LIVE_ROOM_PALETTE_STAGE
    beq Same_Msu1_ReadBegin__dest_palette_high_ok
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__dest_palette_high_ok:
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_CAPACITY
    cmp #$0301
    bcc Same_Msu1_ReadBegin__dest_palette_capacity_ok
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__dest_palette_capacity_ok:
    sep #$20
    .a8
    bra Same_Msu1_ReadBegin__dest_capacity_ok
Same_Msu1_ReadBegin__dest_invalid:
    jml Same_Msu1_ReadBegin__capacity_error
.endif
Same_Msu1_ReadBegin__dest_capacity_ok:
    .a8
    lda.l SAME_MSU1_FLAGS
    and #SAME_MSU1_FLAG_RING
    bne Same_Msu1_ReadBegin__length_ok
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    ora.l SAME_MSU1_REQUEST_LENGTH+3
    beq Same_Msu1_ReadBegin__length_fits_bank
    jml Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__length_fits_bank:
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp.l SAME_MSU1_DEST_CAPACITY
    bcc Same_Msu1_ReadBegin__length_ok16
    beq Same_Msu1_ReadBegin__length_ok16
    jml Same_Msu1_ReadBegin__capacity_error16
Same_Msu1_ReadBegin__length_ok16:
    sep #$20
    .a8
Same_Msu1_ReadBegin__length_ok:
    .a8
    ; Empty read (including exactly-at-EOF) never seeks or touches MSU_DATA.
    lda.l SAME_MSU1_REQUEST_LENGTH
    ora.l SAME_MSU1_REQUEST_LENGTH+1
    ora.l SAME_MSU1_REQUEST_LENGTH+2
    ora.l SAME_MSU1_REQUEST_LENGTH+3
    bne Same_Msu1_ReadBegin__nonempty
    lda.l SAME_MSU1_EXPECTED_CRC
    ora.l SAME_MSU1_EXPECTED_CRC+1
    ora.l SAME_MSU1_EXPECTED_CRC+2
    ora.l SAME_MSU1_EXPECTED_CRC+3
    beq Same_Msu1_ReadBegin__empty_crc_ok
    jml Same_Msu1_ReadBegin__crc_error
Same_Msu1_ReadBegin__empty_crc_ok:
    .a8
    lda #SAME_MSU1_STATE_READ_OK
    sta.l SAME_MSU1_STATUS
    plp
    clc
    rts
Same_Msu1_ReadBegin__nonempty:
    lda.l SAME_MSU1_DESTINATION
    sta SAME_MSU1_DP_DEST
    lda.l SAME_MSU1_DESTINATION+1
    sta SAME_MSU1_DP_DEST+1
    lda.l SAME_MSU1_DESTINATION+2
    sta SAME_MSU1_DP_DEST+2
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_MSU1_DEST_INDEX
    lda #$FFFF
    sta.l SAME_MSU1_CRC_STATE
    sta.l SAME_MSU1_CRC_STATE+2
    sep #$20
    .a8
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_MSU1_REMAINING
    lda.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SAME_MSU1_REMAINING+1
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REMAINING+2
    lda.l SAME_MSU1_REQUEST_LENGTH+3
    sta.l SAME_MSU1_REMAINING+3
    lda.l SAME_MSU1_REQUEST_OFFSET
    sta.l SAME_MSU1_LAST_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+1
    sta.l SAME_MSU1_LAST_OFFSET+1
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l SAME_MSU1_LAST_OFFSET+2
    lda.l SAME_MSU1_REQUEST_OFFSET+3
    sta.l SAME_MSU1_LAST_OFFSET+3
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_MSU1_LAST_LENGTH
    lda.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SAME_MSU1_LAST_LENGTH+1
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_LAST_LENGTH+2
    lda.l SAME_MSU1_REQUEST_LENGTH+3
    sta.l SAME_MSU1_LAST_LENGTH+3
    jsr Same_Msu1_Seek
    lda #SAME_MSU1_ERROR_NONE
    sta.l SAME_MSU1_ERROR
    lda #SAME_MSU1_STATE_READING
    sta.l SAME_MSU1_STATUS
    plp
    clc
    rts
Same_Msu1_ReadBegin__capacity_error16:
    sep #$20
    .a8
    bra Same_Msu1_ReadBegin__capacity_error
Same_Msu1_ReadBegin__range_error:
    rep #$20
    .a16
    lda.l SAME_MSU1_RANGE_REJECT_COUNT
    inc
    sta.l SAME_MSU1_RANGE_REJECT_COUNT
    sep #$20
    .a8
    lda #SAME_MSU1_ERROR_RANGE
    bra Same_Msu1_ReadBegin__fail
Same_Msu1_ReadBegin__capacity_error:
    rep #$20
    .a16
    lda.l SAME_MSU1_RANGE_REJECT_COUNT
    inc
    sta.l SAME_MSU1_RANGE_REJECT_COUNT
    sep #$20
    .a8
    lda #SAME_MSU1_ERROR_CAPACITY
    bra Same_Msu1_ReadBegin__fail
Same_Msu1_ReadBegin__crc_error:
    .a8
    lda #SAME_MSU1_ERROR_CRC
    bra Same_Msu1_ReadBegin__fail
Same_Msu1_ReadBegin__state_error:
    .a8
    lda #SAME_MSU1_ERROR_IDENTITY
    jsr Same_Msu1_Fail
    plp
    sec
    rts
Same_Msu1_ReadBegin__fail:
    .a8
    sta.l SAME_MSU1_ERROR
    lda #SAME_MSU1_STATE_READY
    sta.l SAME_MSU1_STATUS
    plp
    sec
    rts

Same_Msu1_ReadStep:
    php
    rep #$30
    .a16
    .i16
    lda #SAME_MSU1_STEP_BUDGET
    sta.l SAME_MSU1_STEP_REMAINING
Same_Msu1_ReadStep__next:
    sep #$20
    .a8
    lda.l SAME_MSU1_REMAINING
    ora.l SAME_MSU1_REMAINING+1
    ora.l SAME_MSU1_REMAINING+2
    ora.l SAME_MSU1_REMAINING+3
    bne Same_Msu1_ReadStep__has_data
    jml Same_Msu1_ReadStep__complete
Same_Msu1_ReadStep__has_data:
    jsr Same_Msu1_WaitDataReady
    bcc Same_Msu1_ReadStep__data_ready
    jml Same_Msu1_ReadStep__done
Same_Msu1_ReadStep__data_ready:
    lda MSU1_DATA
    sta.l SAME_MSU1_BYTE_SCRATCH
    jsr Same_Msu1_CrcByte
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_INDEX
    tay
    sep #$20
    .a8
    lda.l SAME_MSU1_BYTE_SCRATCH
    sta [SAME_MSU1_DP_DEST],y
    rep #$20
    .a16
    iny
    tya
    sta.l SAME_MSU1_DEST_INDEX
    sep #$20
    .a8
    lda.l SAME_MSU1_FLAGS
    and #SAME_MSU1_FLAG_RING
    beq Same_Msu1_ReadStep__advance_source
    rep #$20
    .a16
    lda.l SAME_MSU1_DEST_INDEX
    cmp.l SAME_MSU1_DEST_CAPACITY
    bcc Same_Msu1_ReadStep__advance_source16
    lda #$0000
    sta.l SAME_MSU1_DEST_INDEX
Same_Msu1_ReadStep__advance_source16:
    sep #$20
    .a8
Same_Msu1_ReadStep__advance_source:
    .a8
    sec
    lda.l SAME_MSU1_REMAINING
    sbc #$01
    sta.l SAME_MSU1_REMAINING
    lda.l SAME_MSU1_REMAINING+1
    sbc #$00
    sta.l SAME_MSU1_REMAINING+1
    lda.l SAME_MSU1_REMAINING+2
    sbc #$00
    sta.l SAME_MSU1_REMAINING+2
    lda.l SAME_MSU1_REMAINING+3
    sbc #$00
    sta.l SAME_MSU1_REMAINING+3
    rep #$20
    .a16
    lda.l SAME_MSU1_BYTES_READ
    inc
    sta.l SAME_MSU1_BYTES_READ
    bne Same_Msu1_ReadStep__count_done
    lda.l SAME_MSU1_BYTES_READ+2
    inc
    sta.l SAME_MSU1_BYTES_READ+2
Same_Msu1_ReadStep__count_done:
    lda.l SAME_MSU1_STEP_REMAINING
    dec
    sta.l SAME_MSU1_STEP_REMAINING
    beq Same_Msu1_ReadStep__budget_done
    jml Same_Msu1_ReadStep__next
Same_Msu1_ReadStep__budget_done:
    bra Same_Msu1_ReadStep__done
Same_Msu1_ReadStep__complete:
    .a8
    jsr Same_Msu1_CheckCrc
    bcs Same_Msu1_ReadStep__done
    lda #SAME_MSU1_STATE_READ_OK
    sta.l SAME_MSU1_STATUS
    rep #$20
    .a16
    lda.l SAME_MSU1_READ_COUNT
    inc
    sta.l SAME_MSU1_READ_COUNT
Same_Msu1_ReadStep__done:
    plp
    rts

; Reflected CRC-32 / IEEE, one input byte at a time; CRC is finalized only once
; the entire checked request has arrived.
Same_Msu1_CrcByte:
    sep #$20
    .a8
    lda.l SAME_MSU1_BYTE_SCRATCH
    eor.l SAME_MSU1_CRC_STATE
    sta.l SAME_MSU1_CRC_STATE
    lda #$08
    sta.l SAME_MSU1_CRC_BITS
Same_Msu1_CrcByte__bit:
    .a8
    lda.l SAME_MSU1_CRC_STATE
    and #$01
    sta.l SAME_MSU1_CRC_LSB
    lda.l SAME_MSU1_CRC_STATE+3
    lsr
    sta.l SAME_MSU1_CRC_STATE+3
    lda.l SAME_MSU1_CRC_STATE+2
    ror
    sta.l SAME_MSU1_CRC_STATE+2
    lda.l SAME_MSU1_CRC_STATE+1
    ror
    sta.l SAME_MSU1_CRC_STATE+1
    lda.l SAME_MSU1_CRC_STATE
    ror
    sta.l SAME_MSU1_CRC_STATE
    lda.l SAME_MSU1_CRC_LSB
    beq Same_Msu1_CrcByte__no_poly
    lda.l SAME_MSU1_CRC_STATE
    eor #$20
    sta.l SAME_MSU1_CRC_STATE
    lda.l SAME_MSU1_CRC_STATE+1
    eor #$83
    sta.l SAME_MSU1_CRC_STATE+1
    lda.l SAME_MSU1_CRC_STATE+2
    eor #$B8
    sta.l SAME_MSU1_CRC_STATE+2
    lda.l SAME_MSU1_CRC_STATE+3
    eor #$ED
    sta.l SAME_MSU1_CRC_STATE+3
Same_Msu1_CrcByte__no_poly:
    lda.l SAME_MSU1_CRC_BITS
    dec
    sta.l SAME_MSU1_CRC_BITS
    bne Same_Msu1_CrcByte__bit
    rts

Same_Msu1_CheckCrc:
    sep #$20
    .a8
    lda.l SAME_MSU1_CRC_STATE
    eor #$FF
    cmp.l SAME_MSU1_EXPECTED_CRC
    bne Same_Msu1_CheckCrc__bad
    lda.l SAME_MSU1_CRC_STATE+1
    eor #$FF
    cmp.l SAME_MSU1_EXPECTED_CRC+1
    bne Same_Msu1_CheckCrc__bad
    lda.l SAME_MSU1_CRC_STATE+2
    eor #$FF
    cmp.l SAME_MSU1_EXPECTED_CRC+2
    bne Same_Msu1_CheckCrc__bad
    lda.l SAME_MSU1_CRC_STATE+3
    eor #$FF
    cmp.l SAME_MSU1_EXPECTED_CRC+3
    bne Same_Msu1_CheckCrc__bad
    clc
    rts
Same_Msu1_CheckCrc__bad:
    .a8
    lda #SAME_MSU1_ERROR_CRC
    jsr Same_Msu1_Fail
    sec
    rts

Same_Msu1_WaitDataReady:
    php
    sep #$20
    .a8
    lda #SAME_MSU1_BUSY_POLL_LIMIT
    sta.l SAME_MSU1_TIMEOUT
Same_Msu1_WaitDataReady__poll:
    .a8
.if SAME_BUILD_MSU1_TEST_FORCE_BUSY
    lda #$80
.else
    lda.l MSU1_STATUS
.endif
    and #$80 ; ignore audio-busy/status bits 3..6
    beq Same_Msu1_WaitDataReady__ready
    lda.l SAME_MSU1_TIMEOUT
    dec
    sta.l SAME_MSU1_TIMEOUT
    bne Same_Msu1_WaitDataReady__poll
    rep #$20
    .a16
    lda.l SAME_MSU1_TIMEOUT_COUNT
    inc
    sta.l SAME_MSU1_TIMEOUT_COUNT
    sep #$20
    .a8
    lda #SAME_MSU1_ERROR_BUSY
    jsr Same_Msu1_Fail
    plp
    sec
    rts
Same_Msu1_WaitDataReady__ready:
    plp
    clc
    rts

Same_Msu1_Seek:
    php
    sep #$20
    .a8
    lda.l SAME_MSU1_REQUEST_OFFSET
    sta.l MSU1_SEEK0
    lda.l SAME_MSU1_REQUEST_OFFSET+1
    sta.l MSU1_SEEK1
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l MSU1_SEEK2
    lda.l SAME_MSU1_REQUEST_OFFSET+3
    sta.l MSU1_SEEK3
    rep #$20
    .a16
    lda.l SAME_MSU1_SEEK_COUNT
    inc
    sta.l SAME_MSU1_SEEK_COUNT
    plp
    rts

; Far-call veneers keep engine consumers on SAME's storage-service boundary.
; The SCUMM bytecode cache supplies the standard checked request descriptor;
; it never touches MSU hardware registers itself.
Same_Msu1_ReadBegin_FarEntry:
    jsr Same_Msu1_ReadBegin
    rtl

Same_Msu1_InitBegin_FarEntry:
    jsr Same_Msu1_InitBegin
    rtl

Same_Msu1_Fail:
    php
    sep #$20
    .a8
    sta.l SAME_MSU1_ERROR
    lda #SAME_MSU1_STATE_ERROR
    sta.l SAME_MSU1_STATUS
    rep #$20
    .a16
    lda.l SAME_MSU1_READ_COUNT
    inc
    sta.l SAME_MSU1_READ_COUNT
    plp
    rts

.include "../generated/msu1_read_cases.inc.pasm"
