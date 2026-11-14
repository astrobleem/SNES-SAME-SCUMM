; Source foreground-mask consumer. One actor at a time owns the existing
; checked scratch; decoded coverage occupies the free tail AFTER the complete
; scene underlay. No mask or partial scene is published before verification.
ScummV5_Mask_CaptureBounds_Far:
    .a16
    .i16
 php
 rep #$30
 .a16
 .i16
 pha
 phx
 lda.l SAME_SCUMM_SCENE_ACTOR
 asl
 asl
 asl
 asl
 asl
 tax
 lda.l SAME_SCUMM_ACTOR_CLIP_LEFT
 cmp.l SAME_SCUMM_SCENE_SNAPSHOTS+$18,x
 bcs MaskCapture_left
 sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$18,x
MaskCapture_left:
    .a16
    .i16
 lda.l SAME_SCUMM_CEL_Y
 cmp.l SAME_SCUMM_SCENE_SNAPSHOTS+$1A,x
 bcs MaskCapture_top
 sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1A,x
MaskCapture_top:
    .a16
    .i16
 lda.l SAME_SCUMM_ACTOR_CLIP_RIGHT
 cmp.l SAME_SCUMM_SCENE_SNAPSHOTS+$1C,x
 bcc MaskCapture_right
 sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1C,x
MaskCapture_right:
    .a16
    .i16
 lda.l SAME_SCUMM_CEL_Y
 inc
 cmp.l SAME_SCUMM_SCENE_SNAPSHOTS+$1E,x
 bcc MaskCapture_done
 sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1E,x
MaskCapture_done:
    .a16
    .i16
 plx
 pla
 plp
 rtl

ScummV5_Mask_Ensure_Far:
    .a16
    .i16
 php
 rep #$30
 .a16
 .i16
 pha
 phx
 phy
 phb
 .if SCUMM_MSU1_MASK_COUNT
 lda.l SAME_SCUMM_MASK_STATE
 .if SCUMM_MSU1_OBJECT_ROOM_COUNT
 cmp #$0004
 bcc ObjectMaskEnsure_base
 jsl ScummV5_ObjectImages_Masks_Far
 bcc ObjectMaskEnsure_pending
 jml ObjectMaskEnsure_complete
ObjectMaskEnsure_pending:
 .a16
 .i16
 jml MaskEnsure_pending
ObjectMaskEnsure_base:
 .a16
 .i16
 .endif
 cmp #$0003
 bne MaskEnsure_work
 jml MaskEnsure_ready
MaskEnsure_work:
    .a16
    .i16
 cmp #$0001
 bne MaskEnsure_not_reading
 jml MaskEnsure_poll
MaskEnsure_not_reading:
    .a16
    .i16
 cmp #$0002
 bne MaskEnsure_init
 jml MaskEnsure_request
MaskEnsure_init:
    .a16
    .i16
 lda #$0000
 sta.l SAME_SCUMM_MASK_PLANE
 lda.l SAME_VIDEO_SURFACE_ROOM
 and #$00FF
 asl
 asl
 asl
 asl
 tax
 sta.l SAME_SCUMM_MASK_ROOM_ROW
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$04,x
 bne MaskEnsure_planes
 jml MaskEnsure_ready
MaskEnsure_planes:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_TEMP
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$06,x
 sta.l SAME_SCUMM_MASK_BLOCKS_PER_STRIP
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$08,x
 sta.l SAME_SCUMM_MASK_STRIPS
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$0A,x
 sta.l SAME_SCUMM_MASK_FIRST
 lda.l SAME_SCUMM_SCENE_ACTOR
 asl
 asl
 asl
 asl
 asl
 tax
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$12,x
 and #$00FF
    beq MaskLongBranch_116
    jml MaskEnsure_plane
MaskLongBranch_116:
    .a16
    .i16
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$13,x
 and #$00FF
 beq MaskEnsure_boxes
 jml MaskEnsure_ready
MaskEnsure_boxes:
    .a16
    .i16
 ; Class policy was captured with position/elevation, before streaming.
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$16,x
 beq MaskEnsure_box
 jml MaskEnsure_ready
MaskEnsure_box:
    .a16
    .i16
 lda.l SAME_SCUMM_SCENE_ACTOR
 asl
 asl
 asl
 asl
 asl
 tax
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$14,x
 and #$00FF
 cmp #$00FF
 bne MaskEnsure_box_present
 jml MaskEnsure_ready
MaskEnsure_box_present:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_INDEX
 lda #SCUMM_MSU1_MASK_ROOM_BANK
 sep #$20
 .a8
 pha
 plb
 rep #$20
 .a16
 lda.l SAME_SCUMM_MASK_ROOM_ROW
 tax
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$0E,x
 tax
 lda.l SAME_SCUMM_MASK_INDEX
 cmp $0000,x
 bcc MaskEnsure_box_in_range
 jml MaskEnsure_error
MaskEnsure_box_in_range:
    .a16
    .i16
 txa
 clc
 adc.l SAME_SCUMM_MASK_INDEX
 tax
 lda $0002,x
 and #$00FF
MaskEnsure_plane:
    .a16
    .i16
 cmp.l SAME_SCUMM_MASK_TEMP
 bcc MaskEnsure_plane_bounded
 lda.l SAME_SCUMM_MASK_TEMP
MaskEnsure_plane_bounded:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_PLANE
 bne MaskEnsure_bounds
 jml MaskEnsure_ready
MaskEnsure_bounds:
    .a16
    .i16
 lda.l SAME_SCUMM_SCENE_ACTOR
 asl
 asl
 asl
 asl
 asl
 tax
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$18,x
 cmp #$FFFF
 bne MaskEnsure_nonempty
 lda #$0000
 sta.l SAME_SCUMM_MASK_PLANE
 jml MaskEnsure_ready
MaskEnsure_nonempty:
    .a16
    .i16
 ; Convert clipped screen coverage to source-world half-open bounds.
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_X
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_X
 bpl MaskEnsure_left
 lda #$0000
MaskEnsure_left:
    .a16
    .i16
 lsr
 lsr
 lsr
 sta.l SAME_SCUMM_MASK_LEFT
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$1C,x
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_X
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_X
 clc
 adc #$0007
 lsr
 lsr
 lsr
 cmp.l SAME_SCUMM_MASK_STRIPS
 bcc MaskEnsure_right
 lda.l SAME_SCUMM_MASK_STRIPS
MaskEnsure_right:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_RIGHT
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$1A,x
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_Y
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_Y
 bpl MaskEnsure_top
 lda #$0000
MaskEnsure_top:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_TOP
 lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$1E,x
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_Y
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_Y
 sta.l SAME_SCUMM_MASK_BOTTOM
 lda.l SAME_SCUMM_MASK_ROOM_ROW
 tax
 lda.l SCUMM_MSU1_MASK_ROOM_ADDRESS+$02,x
 cmp.l SAME_SCUMM_MASK_BOTTOM
 bcs MaskEnsure_bottom
 sta.l SAME_SCUMM_MASK_BOTTOM
MaskEnsure_bottom:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_RIGHT
 cmp.l SAME_SCUMM_MASK_LEFT
    bcs MaskLongBranch_281
    jml MaskEnsure_empty
MaskLongBranch_281:
    .a16
    .i16
    bne MaskLongBranch_282
    jml MaskEnsure_empty
MaskLongBranch_282:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_BOTTOM
 sec
 sbc.l SAME_SCUMM_MASK_TOP
    bcs MaskLongBranch_286
    jml MaskEnsure_empty
MaskLongBranch_286:
    .a16
    .i16
    bne MaskLongBranch_287
    jml MaskEnsure_empty
MaskLongBranch_287:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_HEIGHT
 ; The committed journal's immutable used field proves the free tail.
 lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$30
 tax
 cmp #(SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE-$0010+1)
    bcc MaskLongBranch_293
    jml MaskEnsure_bad_bounds
MaskLongBranch_293:
    .a16
    .i16
 lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
 and #$00FF
 cmp #SAME_VIDEO_ACTOR_UNDERLAY_MAGIC
    beq MaskLongBranch_297
    jml MaskEnsure_bad_bounds
MaskLongBranch_297:
    .a16
    .i16
 lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
 cmp #$0010
    bcs MaskLongBranch_300
    jml MaskEnsure_bad_bounds
MaskLongBranch_300:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_TEMP
 txa
 clc
 adc.l SAME_SCUMM_MASK_TEMP
 bcs MaskEnsure_bad_bounds
 sta.l SAME_SCUMM_MASK_BASE
 sta.l SAME_SCUMM_MASK_END
 lda.l SAME_SCUMM_MASK_RIGHT
 sec
 sbc.l SAME_SCUMM_MASK_LEFT
 tax
MaskEnsure_capacity:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_END
 clc
 adc.l SAME_SCUMM_MASK_HEIGHT
 bcs MaskEnsure_bad_bounds
 cmp #(SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE+1)
 bcs MaskEnsure_bad_bounds
 sta.l SAME_SCUMM_MASK_END
 dex
 bne MaskEnsure_capacity
 lda.l SAME_SCUMM_MASK_LEFT
 sta.l SAME_SCUMM_MASK_COLUMN
 lda.l SAME_SCUMM_MASK_TOP
 xba
 and #$00FF
 sta.l SAME_SCUMM_MASK_BLOCK
 lda #$0002
 sta.l SAME_SCUMM_MASK_STATE
 jml MaskEnsure_pending
MaskEnsure_bad_bounds:
    .a16
    .i16
 jml MaskEnsure_error
MaskEnsure_empty:
    .a16
    .i16
 lda #$0000
 sta.l SAME_SCUMM_MASK_PLANE
 jml MaskEnsure_ready

MaskEnsure_request:
    .a16
    .i16
 ; Do not modify another client's checked descriptor, even after READ_OK.
 lda.l SAME_MSU1_STATUS
 and #$00FF
 cmp #SAME_MSU1_STATE_READY
 beq MaskEnsure_available
 cmp #SAME_MSU1_STATE_READ_OK
 beq MaskEnsure_available
 jml MaskEnsure_pending
MaskEnsure_available:
    .a16
    .i16
 lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
 and #$00FF
 cmp #$00FF
 beq MaskEnsure_cache_free
 jml MaskEnsure_pending
MaskEnsure_cache_free:
    .a16
    .i16
 lda.l SAME_SCUMM_MSU_ROOM_STATE
 and #$00FF
 cmp #SCUMM_MSU_ROOM_REQUESTED
 beq MaskEnsure_pending_jump
 cmp #SCUMM_MSU_ROOM_READING
 beq MaskEnsure_pending_jump
 .if SCUMM_MSU1_CAMERA_VIEWPORT
 jsl ScummV5_Camera_AheadRelease_Far
 rep #$30
 .a16
 .i16
 .endif
 lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
 and #$00FF
 beq MaskEnsure_owner_free
MaskEnsure_pending_jump:
    .a16
    .i16
 jml MaskEnsure_pending
MaskEnsure_owner_free:
    .a16
    .i16
 ; index = first + ((plane-1)*strips + column)*blocks_per_strip + block.
 lda.l SAME_SCUMM_MASK_PLANE
 dec
 tax
 lda.l SAME_SCUMM_MASK_COLUMN
MaskEnsure_plane_index:
    .a16
    .i16
 cpx #$0000
 beq MaskEnsure_strip_index
 clc
 adc.l SAME_SCUMM_MASK_STRIPS
    bcc MaskLongBranch_400
    jml MaskEnsure_index_bad
MaskLongBranch_400:
    .a16
    .i16
 dex
 bra MaskEnsure_plane_index
MaskEnsure_strip_index:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_TEMP
 lda.l SAME_SCUMM_MASK_BLOCKS_PER_STRIP
 tax
 lda #$0000
MaskEnsure_block_index:
    .a16
    .i16
 clc
 adc.l SAME_SCUMM_MASK_TEMP
    bcc MaskLongBranch_415
    jml MaskEnsure_index_bad
MaskLongBranch_415:
    .a16
    .i16
 dex
 bne MaskEnsure_block_index
 clc
 adc.l SAME_SCUMM_MASK_FIRST
    bcc MaskLongBranch_420
    jml MaskEnsure_index_bad
MaskLongBranch_420:
    .a16
    .i16
 clc
 adc.l SAME_SCUMM_MASK_BLOCK
    bcc MaskLongBranch_423
    jml MaskEnsure_index_bad
MaskLongBranch_423:
    .a16
    .i16
 cmp #SCUMM_MSU1_MASK_BLOCK_COUNT
    bcc MaskLongBranch_425
    jml MaskEnsure_index_bad
MaskLongBranch_425:
    .a16
    .i16
 sta.l SAME_SCUMM_MASK_INDEX
 and #$F800
 xba
 lsr
 lsr
 lsr
 clc
 adc #SCUMM_MSU1_MASK_FIRST_BANK
 sep #$20
 .a8
 pha
 plb
 rep #$20
 .a16
 lda.l SAME_SCUMM_MASK_INDEX
 and #$07FF
 asl
 asl
 asl
 asl
 tax
 lda $8006,x
 sta.l SAME_SCUMM_MASK_ROWS
 lda $8008,x
 sta.l SAME_SCUMM_MASK_CODEC
 lda $8004,x
 sta.l SAME_SCUMM_MASK_LENGTH
    bne MaskLongBranch_453
    jml MaskEnsure_zero
MaskLongBranch_453:
    .a16
    .i16
 cmp #$0101
    bcc MaskLongBranch_455
    jml MaskEnsure_index_bad
MaskLongBranch_455:
    .a16
    .i16
 lda $8000,x
 sta.l SAME_MSU1_REQUEST_OFFSET
 sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET
 lda $8002,x
 sta.l SAME_MSU1_REQUEST_OFFSET+2
 sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET+2
 lda $800A,x
 sta.l SAME_MSU1_EXPECTED_CRC
 sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC
 lda $800C,x
 sta.l SAME_MSU1_EXPECTED_CRC+2
 sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC+2
 lda.l SAME_SCUMM_MASK_LENGTH
 sta.l SAME_MSU1_REQUEST_LENGTH
 sta.l SAME_SCUMM_ACTOR_TICKET_LENGTH
 lda #$0000
 sta.l SAME_MSU1_REQUEST_LENGTH+2
 lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
 sta.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
 lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
 sta.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
 lda.l SAME_SCUMM_ACTOR_TICKET_SERIAL
 inc
 sta.l SAME_SCUMM_ACTOR_TICKET_SERIAL
 lda #SAME_SCUMM_ACTOR_POSE_BUFFER_SIZE
 sta.l SAME_MSU1_DEST_CAPACITY
 sep #$20
 .a8
 lda #<SAME_SCUMM_ACTOR_POSE_BUFFER
 sta.l SAME_MSU1_DESTINATION
 lda #>SAME_SCUMM_ACTOR_POSE_BUFFER
 sta.l SAME_MSU1_DESTINATION+1
 lda #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
 sta.l SAME_MSU1_DESTINATION+2
 lda #$00
 sta.l SAME_MSU1_FLAGS
 lda #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
 sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
 lda #$01
 sta.l SAME_SCUMM_ACTOR_POSE_STATE
 rep #$20
 .a16
 lda #$0001
 sta.l SAME_SCUMM_MASK_STATE
 jsl Same_Msu1_ReadBegin_FarEntry
 bcc MaskEnsure_read_started
 jml MaskEnsure_error
MaskEnsure_read_started:
    .a16
    .i16
 jml MaskEnsure_pending
MaskEnsure_index_bad:
    .a16
    .i16
 jml MaskEnsure_error
MaskEnsure_zero:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_CODEC
 beq MaskEnsure_decode
 jml MaskEnsure_error
MaskEnsure_poll:
    .a16
    .i16
 jsl ScummV5_ActorPose_ProviderMatches_Far
 bcs MaskEnsure_ticket
 jml MaskEnsure_error
MaskEnsure_ticket:
    .a16
    .i16
 rep #$30
 .a16
 .i16
 lda.l SAME_MSU1_STATUS
 and #$00FF
 cmp #SAME_MSU1_STATE_ERROR
 bne MaskEnsure_not_error
 jml MaskEnsure_error
MaskEnsure_not_error:
    .a16
    .i16
 cmp #SAME_MSU1_STATE_READ_OK
 beq MaskEnsure_decode
 jml MaskEnsure_pending
MaskEnsure_decode:
    .a16
    .i16
 ; At most256 decoded rows per service turn. Every block validates exact
 ; expansion and checked byte consumption before becoming reusable coverage.
 lda.l SAME_SCUMM_MASK_ROWS
    bne MaskLongBranch_546
    jml MaskEnsure_decode_bad
MaskLongBranch_546:
    .a16
    .i16
 cmp #$0101
    bcc MaskLongBranch_548
    jml MaskEnsure_decode_bad
MaskLongBranch_548:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_CODEC
 cmp #$0003
    bcc MaskLongBranch_551
    jml MaskEnsure_decode_bad
MaskLongBranch_551:
    .a16
    .i16
 lda #$0000
 sta.l SAME_SCUMM_MASK_INPUT
 sta.l SAME_SCUMM_MASK_ROW
MaskEnsure_decode_next:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_ROW
 cmp.l SAME_SCUMM_MASK_ROWS
 bcc MaskEnsure_decode_run
 lda.l SAME_SCUMM_MASK_INPUT
 cmp.l SAME_SCUMM_MASK_LENGTH
    beq MaskLongBranch_563
    jml MaskEnsure_decode_bad
MaskLongBranch_563:
    .a16
    .i16
 jml MaskEnsure_block_done
MaskEnsure_decode_run:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_CODEC
    bne MaskLongBranch_569
    jml MaskEnsure_decode_zero
MaskLongBranch_569:
    .a16
    .i16
 cmp #$0001
 beq MaskEnsure_decode_raw
 lda.l SAME_SCUMM_MASK_INPUT
 clc
 adc #$0002
 cmp.l SAME_SCUMM_MASK_LENGTH
 bcc MaskEnsure_rle_length
 beq MaskEnsure_rle_length
    jml MaskEnsure_decode_bad
MaskEnsure_rle_length:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_INPUT
 tax
 lda.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
 and #$00FF
 inc
 sta.l SAME_SCUMM_MASK_RUN
 inx
 lda.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
 and #$00FF
 sta.l SAME_SCUMM_MASK_VALUE
 inx
 txa
 sta.l SAME_SCUMM_MASK_INPUT
 bra MaskEnsure_run_ready
MaskEnsure_decode_raw:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_INPUT
 cmp.l SAME_SCUMM_MASK_LENGTH
 bcs MaskEnsure_decode_bad
 tax
 lda.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
 and #$00FF
 sta.l SAME_SCUMM_MASK_VALUE
 inx
 txa
 sta.l SAME_SCUMM_MASK_INPUT
 lda #$0001
 sta.l SAME_SCUMM_MASK_RUN
 bra MaskEnsure_run_ready
MaskEnsure_decode_zero:
    .a16
    .i16
 lda #$0000
 sta.l SAME_SCUMM_MASK_VALUE
 lda.l SAME_SCUMM_MASK_ROWS
 sta.l SAME_SCUMM_MASK_RUN
MaskEnsure_run_ready:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_RUN
 clc
 adc.l SAME_SCUMM_MASK_ROW
 cmp.l SAME_SCUMM_MASK_ROWS
 bcc MaskEnsure_store
 beq MaskEnsure_store
MaskEnsure_decode_bad:
    .a16
    .i16
 jml MaskEnsure_error
MaskEnsure_store:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_BLOCK
 xba
 clc
 adc.l SAME_SCUMM_MASK_ROW
 cmp.l SAME_SCUMM_MASK_TOP
    bcs MaskLongBranch_640
    jml MaskEnsure_store_next
MaskLongBranch_640:
    .a16
    .i16
 cmp.l SAME_SCUMM_MASK_BOTTOM
    bcc MaskLongBranch_642
    jml MaskEnsure_store_next
MaskLongBranch_642:
    .a16
    .i16
 sec
 sbc.l SAME_SCUMM_MASK_TOP
 clc
 adc.l SAME_SCUMM_MASK_BASE
 sta.l SAME_SCUMM_MASK_OUTPUT
 lda.l SAME_SCUMM_MASK_COLUMN
 sec
 sbc.l SAME_SCUMM_MASK_LEFT
 tax
MaskEnsure_store_column:
    .a16
    .i16
 cpx #$0000
 beq MaskEnsure_store_byte
 lda.l SAME_SCUMM_MASK_OUTPUT
 clc
 adc.l SAME_SCUMM_MASK_HEIGHT
 sta.l SAME_SCUMM_MASK_OUTPUT
 dex
 bra MaskEnsure_store_column
MaskEnsure_store_byte:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_OUTPUT
 cmp.l SAME_SCUMM_MASK_END
    bcc MaskLongBranch_668
    jml MaskEnsure_decode_bad
MaskLongBranch_668:
    .a16
    .i16
 tax
 sep #$20
 .a8
 lda.l SAME_SCUMM_MASK_VALUE
 sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
 rep #$20
 .a16
MaskEnsure_store_next:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_ROW
 inc
 sta.l SAME_SCUMM_MASK_ROW
 lda.l SAME_SCUMM_MASK_RUN
 dec
 sta.l SAME_SCUMM_MASK_RUN
    beq MaskLongBranch_685
    jml MaskEnsure_store
MaskLongBranch_685:
    .a16
    .i16
 jml MaskEnsure_decode_next
MaskEnsure_block_done:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_LENGTH
 beq MaskEnsure_block_released
 jsl ScummV5_ActorPose_ReleaseBuffer_Far
 sep #$20
 .a8
 lda #$00
 sta.l SAME_SCUMM_ACTOR_POSE_STATE
 rep #$20
 .a16
MaskEnsure_block_released:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_BLOCK
 inc
 sta.l SAME_SCUMM_MASK_BLOCK
 ; A 65535-row source has block255. Its next row is65536, which must
 ; advance the strip rather than wrap to row1 through XBA.
 cmp #$0100
 bcs MaskEnsure_next_column
 xba
 cmp.l SAME_SCUMM_MASK_BOTTOM
 bcc MaskEnsure_more_blocks
MaskEnsure_next_column:
    .a16
    .i16
 lda.l SAME_SCUMM_MASK_COLUMN
 inc
 sta.l SAME_SCUMM_MASK_COLUMN
 cmp.l SAME_SCUMM_MASK_RIGHT
 bcs MaskEnsure_ready
 lda.l SAME_SCUMM_MASK_TOP
 xba
 and #$00FF
 sta.l SAME_SCUMM_MASK_BLOCK
MaskEnsure_more_blocks:
    .a16
    .i16
 lda #$0002
 sta.l SAME_SCUMM_MASK_STATE
 jml MaskEnsure_pending
 .endif
MaskEnsure_ready:
    .a16
    .i16
 .if SCUMM_MSU1_OBJECT_ROOM_COUNT
 lda.l SAME_SCUMM_MASK_PLANE
 beq ObjectMaskEnsure_no_plane
 jsl ScummV5_ObjectImages_Masks_Far
 bcs ObjectMaskEnsure_complete
 jml MaskEnsure_pending
ObjectMaskEnsure_no_plane:
 .a16
 .i16
 .endif
 lda #$0003
 sta.l SAME_SCUMM_MASK_STATE
ObjectMaskEnsure_complete:
 .a16
 .i16
 plb
 ply
 plx
 pla
 plp
 sec
 rtl
MaskEnsure_error:
    .a16
    .i16
 rep #$30
 .a16
 .i16
 sep #$20
 .a8
 lda #SCUMM_ERR_RESOURCE
 sta.l SAME_SCUMM_ERROR
 rep #$20
 .a16
 jsl ScummV5_ActorPose_Cancel_Far
MaskEnsure_pending:
    .a16
    .i16
 rep #$30
 .a16
 .i16
 plb
 ply
 plx
 pla
 plp
 clc
 rtl

; Carry set means hidden. Reads only the immutable verified current-actor ROI.
; Input remains the source-cel compositor's projected X/Y, AFTER scaling.
ScummV5_Mask_Pixel_Far:
    .a16
    .i16
 php
 rep #$30
 .a16
 .i16
 pha
 phx
 lda.l SAME_SCUMM_MASK_PLANE
 bne MaskPixel_plane
 jml MaskPixel_clear
MaskPixel_plane:
    .a16
    .i16
 lda.l SAME_SCUMM_CEL_X
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_X
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_X
 sta.l SAME_SCUMM_MASK_WORLD_X
 and #$0007
 tax
 lda.l MaskPixel_bits,x
 and #$00FF
 sta.l SAME_SCUMM_MASK_BIT
 lda.l SAME_SCUMM_MASK_WORLD_X
 lsr
 lsr
 lsr
 sec
 sbc.l SAME_SCUMM_MASK_LEFT
    bcs MaskLongBranch_797
    jml MaskPixel_bad
MaskLongBranch_797:
    .a16
    .i16
 tax
 lda.l SAME_SCUMM_CEL_Y
 clc
 adc.l SAME_SCUMM_SCENE_SOURCE_Y
 sec
 sbc.l SAME_VIDEO_SURFACE_DEST_Y
 sec
 sbc.l SAME_SCUMM_MASK_TOP
    bcs MaskLongBranch_806
    jml MaskPixel_bad
MaskLongBranch_806:
    .a16
    .i16
 cmp.l SAME_SCUMM_MASK_HEIGHT
    bcc MaskLongBranch_808
    jml MaskPixel_bad
MaskLongBranch_808:
    .a16
    .i16
 clc
 adc.l SAME_SCUMM_MASK_BASE
MaskPixel_column:
    .a16
    .i16
 cpx #$0000
 beq MaskPixel_read
 clc
 adc.l SAME_SCUMM_MASK_HEIGHT
 dex
 bra MaskPixel_column
MaskPixel_read:
    .a16
    .i16
 cmp.l SAME_SCUMM_MASK_END
 bcs MaskPixel_bad
 tax
 lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
 and.l SAME_SCUMM_MASK_BIT
 beq MaskPixel_clear
MaskPixel_hidden:
    .a16
    .i16
 plx
 pla
 plp
 sec
 rtl
MaskPixel_bad:
    .a16
    .i16
 sep #$20
 .a8
 lda #SCUMM_ERR_RESOURCE
 sta.l SAME_SCUMM_ERROR
 rep #$20
 .a16
 bra MaskPixel_hidden
MaskPixel_clear:
    .a16
    .i16
 plx
 pla
 plp
 clc
 rtl
MaskPixel_bits:
 .byte $80,$40,$20,$10,$08,$04,$02,$01
