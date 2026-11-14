; Original state-selected room objects. Checked <=1KiB rows are merged into
; the existing source-space camera strip before its normal projection. No
; source imagery resides in ROM and no second surface is allocated.
.bank 86
.org $8000

ScummV5_ObjectImages_Reset_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    lda #$0000
    ldx #$0000
ObjectImagesReset_clear:
    .a16
    .i16
    sta.l SAME_SCUMM_OBJECT_IMAGE_CONTROL,x
    inx
    inx
    cpx #(SAME_SCUMM_OBJECT_IMAGE_CONTROL_END-SAME_SCUMM_OBJECT_IMAGE_CONTROL)
    bcc ObjectImagesReset_clear
    plx
    pla
    plp
    rtl

ScummV5_ObjectImages_Changed_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_OBJECT_IMAGE_GENERATION
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_GENERATION
    bne ObjectImagesChanged_done
    lda.l SAME_SCUMM_OBJECT_IMAGE_GENERATION+2
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_GENERATION+2
ObjectImagesChanged_done:
    .a16
    .i16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    rep #$20
    .a16
    pla
    plp
    rtl

; Called after the base strip has passed its own checked read. The ROOM
; owner keeps that prefix while the disjoint tail receives object blocks.
ScummV5_ObjectImages_Begin_Far:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_MODE
    bne ObjectImagesBegin_mask
    lda #$0800
    sta.l SAME_SCUMM_OBJECT_IMAGE_SOURCE_OFFSET
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    sta.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
ObjectImagesBegin_capacity:
    .a16
    .i16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    bra ObjectImagesBegin_room
ObjectImagesBegin_mask:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_SOURCE_OFFSET
    lda.l SAME_VIDEO_SURFACE_ROOM
ObjectImagesBegin_room:
    .a16
    .i16
    pha
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_STATE
    pla
    and #$00FF
    sta.l SAME_SCUMM_OBJECT_IMAGE_ROOM
    asl
    asl
    asl
    tax
    lda.l SCUMM_MSU1_OBJECT_ROOM_ADDRESS,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY
    lda.l SCUMM_MSU1_OBJECT_ROOM_ADDRESS+2,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY+2
    lda.l SCUMM_MSU1_OBJECT_ROOM_ADDRESS+4,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_COUNT
    beq ObjectImagesBegin_empty
    lda.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
    cmp.l SCUMM_MSU1_OBJECT_ROOM_ADDRESS+6,x
    bcc ObjectImagesBegin_column
    jml ObjectImages_error
ObjectImagesBegin_column:
    .a16
    .i16
    asl
    asl
    sta.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    lda.l SAME_SCUMM_OBJECT_IMAGE_COUNT
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY
    and #$7FFF
    tax
    phb
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY+2
    pha
    plb
    rep #$20
    .a16
    lda $8000,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_INDEX
    clc
    adc $8002,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_END_INDEX
    plb
    bcc ObjectImagesBegin_range
    jml ObjectImages_error
ObjectImagesBegin_range:
    .a16
    .i16
    cmp #SCUMM_MSU1_OBJECT_BLOCK_COUNT+1
    bcc ObjectImagesBegin_next
    jml ObjectImages_error
ObjectImagesBegin_next:
    .a16
    .i16
    jml ScummV5_ObjectImages_Next_Far
ObjectImagesBegin_empty:
    .a16
    .i16
    sep #$20
    .a8
    clc
    rtl

; Select one checked block without issuing its read. The existing room
; service admits the request and preserves single-provider ownership.
ScummV5_ObjectImages_Next_Far:
    .a16
    .i16
    rep #$30
    .a16
    .i16
ObjectImagesNext_scan:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_INDEX
    cmp.l SAME_SCUMM_OBJECT_IMAGE_END_INDEX
    bcc ObjectImagesNext_entry
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_STATE
    sep #$20
    .a8
    clc
    rtl
ObjectImagesNext_entry:
    .a16
    .i16
    phb
    pha
    and #$FC00
    xba
    lsr
    lsr
    clc
    adc #SCUMM_MSU1_OBJECT_BLOCK_BANK
    sep #$20
    .a8
    pha
    plb
    rep #$20
    .a16
    pla
    and #$03FF
    asl
    asl
    asl
    asl
    asl
    tax
    ldy #$0000
ObjectImagesNext_copy:
    .a16
    .i16
    lda $8000,x
    phx
    tyx
    sta.l SAME_SCUMM_OBJECT_IMAGE_ENTRY,x
    plx
    inx
    inx
    iny
    iny
    cpy #$0020
    bcc ObjectImagesNext_copy
    plb
    lda.l SAME_SCUMM_OBJECT_IMAGE_INDEX
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_INDEX
    jsl ScummV5_ObjectImages_Visible_Far
    bcc ObjectImagesNext_scan
    lda.l SAME_SCUMM_OBJECT_IMAGE_MODE
    bne ObjectImagesNext_capacity
    lda.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    cmp #$0801
    bcc ObjectImagesNext_capacity
    jml ObjectImages_error
ObjectImagesNext_capacity:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$04
    beq ObjectImagesNext_bad
    cmp #$0401
    bcs ObjectImagesNext_bad
    sta.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_MSU1_DEST_CAPACITY
    lda #$0000
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY
    sta.l SAME_MSU1_REQUEST_OFFSET
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+2
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+6
    sta.l SAME_MSU1_EXPECTED_CRC
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+8
    sta.l SAME_MSU1_EXPECTED_CRC+2
    lda.l SAME_SCUMM_OBJECT_IMAGE_SOURCE_OFFSET
    clc
    adc #SAME_SCUMM_LIVE_ROOM_PENDING_BASE&$FFFF
    sta.l SAME_MSU1_DESTINATION
    lda #$0001
    sta.l SAME_SCUMM_OBJECT_IMAGE_STATE
    sep #$20
    .a8
    lda #$40
    sta.l SAME_MSU1_DESTINATION+2
    lda.l SAME_SCUMM_OBJECT_IMAGE_MODE
    bne ObjectImagesNext_actor
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
ObjectImagesNext_actor:
    .a8
    .i16
    clc
    rtl
ObjectImagesNext_bad:
    .a16
    .i16
    jml ObjectImages_error

; C set means visible. Parent-state evaluation uses original local order and
; live global object states, never a title-specific list or cached selector.
ScummV5_ObjectImages_Visible_Far:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    phb
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0A
    bne ObjectImagesVisible_has_local
    jmp ObjectImagesVisible_no
ObjectImagesVisible_has_local:
    .a16
    .i16
    cmp.l SAME_SCUMM_OBJECT_IMAGE_COUNT
    bcc ObjectImagesVisible_local
    beq ObjectImagesVisible_local
    jmp ObjectImagesVisible_no
ObjectImagesVisible_local:
    .a16
    .i16
    dec
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY
    and #$7FFF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY+2
    pha
    plb
    rep #$20
    .a16
    lda $8000,x
    cmp #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcc ObjectImagesVisible_identity
    jmp ObjectImagesVisible_no
ObjectImagesVisible_identity:
    .a16
    .i16
    phx
    tax
    lda.l SAME_SCUMM_OBJECT_OWNERS,x
    and #$00FF
    beq ObjectImagesVisible_owner
    cmp #$000F
    bne ObjectImagesVisible_pop_no
ObjectImagesVisible_owner:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_STATES,x
    and #$000F
    sta.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0C
    and #$00FF
    cmp.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    bne ObjectImagesVisible_pop_no
    plx
    lda.l SAME_SCUMM_OBJECT_IMAGE_COUNT
    sta.l SAME_SCUMM_OBJECT_IMAGE_DEPTH
ObjectImagesVisible_parent:
    .a16
    .i16
    lda $800A,x
    beq ObjectImagesVisible_yes
    cmp.l SAME_SCUMM_OBJECT_IMAGE_COUNT
    bcc ObjectImagesVisible_parent_valid
    beq ObjectImagesVisible_parent_valid
    jmp ObjectImagesVisible_no
ObjectImagesVisible_parent_valid:
    .a16
    .i16
    sta.l SAME_SCUMM_OBJECT_IMAGE_PARENT
    lda $800C,x
    sta.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    lda.l SAME_SCUMM_OBJECT_IMAGE_PARENT
    dec
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_DIRECTORY
    and #$7FFF
    tax
    lda $8000,x
    cmp #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcs ObjectImagesVisible_no
    phx
    tax
    lda.l SAME_SCUMM_OBJECT_STATES,x
    and #$000F
    plx
    cmp.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    bne ObjectImagesVisible_no
    lda.l SAME_SCUMM_OBJECT_IMAGE_DEPTH
    dec
    sta.l SAME_SCUMM_OBJECT_IMAGE_DEPTH
    bne ObjectImagesVisible_parent
ObjectImagesVisible_no:
    .a16
    .i16
    plb
    clc
    rtl
ObjectImagesVisible_pop_no:
    .a16
    .i16
    plx
    jmp ObjectImagesVisible_no
ObjectImagesVisible_yes:
    .a16
    .i16
    plb
    sec
    rtl

; Entire selected block has passed CRC. Merge coverage into the still-private
; background prefix. A failure never calls the viewport publication path.
ScummV5_ObjectImages_Consume_Far:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+4
    beq ObjectImagesConsume_length
    jml ObjectImages_error
ObjectImagesConsume_length:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    sta.l SAME_SCUMM_OBJECT_IMAGE_ROW
ObjectImagesConsume_row:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    clc
    adc #$0009
    sta.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0C
    xba
    and #$00FF
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+4
    bcc ObjectImagesConsume_bounded
    beq ObjectImagesConsume_bounded
    jml ObjectImages_error
ObjectImagesConsume_bounded:
    .a16
    .i16
    sta.l SAME_SCUMM_OBJECT_IMAGE_TEMP ; next input
    lda.l SAME_SCUMM_OBJECT_IMAGE_MODE
    beq ObjectImagesConsume_background
    jsl ScummV5_ObjectImages_MaskRow_Far
    bcc ObjectImagesConsume_mask_ok
    jml ObjectImages_error
ObjectImagesConsume_mask_ok:
    .a16
    .i16
    jmp ObjectImagesConsume_skip
ObjectImagesConsume_background:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_ROW
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$10
    bcs ObjectImagesConsume_skip
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0E
    bmi ObjectImagesConsume_skip
    cmp.l SAME_SCUMM_VIEWPORT_ROOM_HEIGHT
    bcs ObjectImagesConsume_skip
    asl
    asl
    asl
    sta.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    lda.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_SOURCE_OFFSET
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    and #$00FF
    sta.l SAME_SCUMM_OBJECT_IMAGE_BITS
    inx
    ldy #$0008
ObjectImagesConsume_pixel:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_BITS
    asl
    sta.l SAME_SCUMM_OBJECT_IMAGE_BITS
    and #$0100
    beq ObjectImagesConsume_transparent
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    phx
    pha
    rep #$20
    .a16
    lda.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    tax
    sep #$20
    .a8
    pla
    sta.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    rep #$20
    .a16
    plx
ObjectImagesConsume_transparent:
    .a16
    .i16
    inx
    lda.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    dey
    bne ObjectImagesConsume_pixel
ObjectImagesConsume_skip:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_TEMP
    sta.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    lda.l SAME_SCUMM_OBJECT_IMAGE_ROW
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_ROW
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$12
    bcs ObjectImagesConsume_rows_done
    jmp ObjectImagesConsume_row
ObjectImagesConsume_rows_done:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+4
    beq ObjectImagesConsume_done
    jml ObjectImages_error
ObjectImagesConsume_done:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_MODE
    beq ObjectImagesConsume_next_background
    clc
    rtl
ObjectImagesConsume_next_background:
    .a16
    .i16
    jml ScummV5_ObjectImages_Next_Far
ObjectImages_error:
    .a16
    .i16
    sep #$20
    .a8
    sec
    rtl

; Merge one source object row into the current actor's room-space mask cache.
; Mask bytes replace base strips even where object pixels are transparent.
ScummV5_ObjectImages_MaskRow_Far:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_ROW
    cmp.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$10
    bcs ObjectMaskRow_skip
    clc
    adc.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0E
    bmi ObjectMaskRow_skip
    cmp.l SAME_SCUMM_MASK_TOP
    bcc ObjectMaskRow_skip
    cmp.l SAME_SCUMM_MASK_BOTTOM
    bcs ObjectMaskRow_skip
    sec
    sbc.l SAME_SCUMM_MASK_TOP
    clc
    adc.l SAME_SCUMM_MASK_BASE
    sta.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    lda.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
    sec
    sbc.l SAME_SCUMM_MASK_LEFT
    tax
ObjectMaskRow_column:
    .a16
    .i16
    cpx #$0000
    beq ObjectMaskRow_destination
    lda.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    clc
    adc.l SAME_SCUMM_MASK_HEIGHT
    sta.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    dex
    bra ObjectMaskRow_column
ObjectMaskRow_destination:
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    cmp.l SAME_SCUMM_MASK_END
    bcs ObjectMaskRow_bad
    lda.l SAME_SCUMM_OBJECT_IMAGE_ENTRY+$0C
    xba
    and #$00FF
    cmp.l SAME_SCUMM_MASK_PLANE
    bcc ObjectMaskRow_bad
    lda.l SAME_SCUMM_OBJECT_IMAGE_INPUT
    clc
    adc #$0008
    clc
    adc.l SAME_SCUMM_MASK_PLANE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    pha
    rep #$20
    .a16
    lda.l SAME_SCUMM_OBJECT_IMAGE_OUTPUT
    tax
    sep #$20
    .a8
    pla
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    rep #$20
    .a16
ObjectMaskRow_skip:
    .a16
    .i16
    clc
    rtl
ObjectMaskRow_bad:
    .a16
    .i16
    sec
    rtl

; Extend the existing per-actor checked-mask operation: 4=begin column,
; 5=checked object read, 6=next object block, 7=all object masks complete.
; C set means ready; errors enter the ordinary explicit resource failure.
ScummV5_ObjectImages_Masks_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_MASK_STATE
    cmp #$0007
    bne ObjectMasks_work
    jmp ObjectMasks_ready
ObjectMasks_work:
    .a16
    .i16
    cmp #$0005
    bne ObjectMasks_not_reading
    jmp ObjectMasks_poll
ObjectMasks_not_reading:
    .a16
    .i16
    cmp #$0004
    bcs ObjectMasks_admission
    lda.l SAME_SCUMM_MASK_LEFT
    sta.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
    lda #$0004
    sta.l SAME_SCUMM_MASK_STATE
    lda #$0001
    sta.l SAME_SCUMM_OBJECT_IMAGE_MODE
ObjectMasks_admission:
    .a16
    .i16
    lda.l SAME_MSU1_STATUS
    and #$00FF
    cmp #SAME_MSU1_STATE_READY
    beq ObjectMasks_provider
    cmp #SAME_MSU1_STATE_READ_OK
    beq ObjectMasks_provider
    jmp ObjectMasks_pending
ObjectMasks_provider:
    .a16
    .i16
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    and #$00FF
    cmp #$00FF
    beq ObjectMasks_room
    jmp ObjectMasks_pending
ObjectMasks_room:
    .a16
    .i16
    lda.l SAME_SCUMM_MSU_ROOM_STATE
    and #$00FF
    cmp #SCUMM_MSU_ROOM_REQUESTED
    beq ObjectMasks_busy
    cmp #SCUMM_MSU_ROOM_READING
    beq ObjectMasks_busy
    jsl ScummV5_Camera_AheadRelease_Far
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    and #$00FF
    beq ObjectMasks_claim
ObjectMasks_busy:
    .a16
    .i16
    jmp ObjectMasks_pending
ObjectMasks_claim:
    .a16
    .i16
    sep #$20
    .a8
    lda #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    rep #$20
    .a16
    lda.l SAME_SCUMM_MASK_STATE
    cmp #$0004
    bne ObjectMasks_next
    jsl ScummV5_ObjectImages_Begin_Far
    bra ObjectMasks_selected
ObjectMasks_next:
    .a16
    .i16
    jsl ScummV5_ObjectImages_Next_Far
ObjectMasks_selected:
    .a8
    .i16
    bcc ObjectMasks_selected_ok
    jmp ObjectMasks_error
ObjectMasks_selected_ok:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_IMAGE_STATE
    bne ObjectMasks_ticket
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    rep #$20
    .a16
    lda.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
    inc
    sta.l SAME_SCUMM_OBJECT_IMAGE_COLUMN
    cmp.l SAME_SCUMM_MASK_RIGHT
    bcc ObjectMasks_more_columns
    jmp ObjectMasks_ready
ObjectMasks_more_columns:
    .a16
    .i16
    lda #$0004
    sta.l SAME_SCUMM_MASK_STATE
    jmp ObjectMasks_pending
ObjectMasks_ticket:
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_OFFSET
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET+2
    lda.l SAME_MSU1_EXPECTED_CRC
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC
    lda.l SAME_MSU1_EXPECTED_CRC+2
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC+2
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    lda.l SAME_SCUMM_ACTOR_TICKET_SERIAL
    inc
    sta.l SAME_SCUMM_ACTOR_TICKET_SERIAL
    lda #$0005
    sta.l SAME_SCUMM_MASK_STATE
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    lda #$00
    sta.l SAME_MSU1_FLAGS
    jsl Same_Msu1_ReadBegin_FarEntry
    bcc ObjectMasks_started
    jmp ObjectMasks_error
ObjectMasks_started:
    .a8
    .i16
    jmp ObjectMasks_pending
ObjectMasks_poll:
    .a16
    .i16
    jsl ScummV5_ActorPose_ProviderMatches_Far
    bcs ObjectMasks_ticket_valid
    jmp ObjectMasks_error
ObjectMasks_ticket_valid:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_STATUS
    and #$00FF
    cmp #SAME_MSU1_STATE_ERROR
    bne ObjectMasks_not_error
    jmp ObjectMasks_error
ObjectMasks_not_error:
    .a16
    .i16
    cmp #SAME_MSU1_STATE_READ_OK
    beq ObjectMasks_consume
    jmp ObjectMasks_pending
ObjectMasks_consume:
    .a16
    .i16
    jsl ScummV5_ObjectImages_Consume_Far
    bcc ObjectMasks_consumed
    jmp ObjectMasks_error
ObjectMasks_consumed:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda #$0006
    sta.l SAME_SCUMM_MASK_STATE
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_STATE
    sep #$20
    .a8
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jmp ObjectMasks_pending
ObjectMasks_ready:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda #$0007
    sta.l SAME_SCUMM_MASK_STATE
    lda #$0000
    sta.l SAME_SCUMM_OBJECT_IMAGE_STATE
    sta.l SAME_SCUMM_OBJECT_IMAGE_MODE
    ply
    plx
    pla
    plp
    sec
    rtl
ObjectMasks_error:
    .a16
    .i16
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    rep #$20
    .a16
    jsl ScummV5_ActorPose_Cancel_Far
ObjectMasks_pending:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
