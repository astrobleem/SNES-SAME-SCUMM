; SC5VIS v2 checked strip adapter, included in the existing live-room bank.
; No new provider, framebuffer, source parser or selector namespace. STATE:
    .a8
; 0 idle,1 exclusive staging,2 checked,3 installed awaiting PRESENT acceptance.
; MODE0 incoming room; MODE1 same-room camera publication. The established
; room request serializes provider access while the old display remains valid.

ScummV5_Camera_StartStrip_Far:
    .a8
    rep #$30
    .a16
    .i16
    txa
    sta.l SAME_SCUMM_VIEWPORT_DIRECTORY
    sep #$20
    .a8
    lda.l SAME_SCUMM_VIEWPORT_STATE
    bne ScummV5_Camera_StartStrip__prepared
    jsl ScummV5_Camera_Prepare_Far
    bcc ScummV5_Camera_StartStrip__prepare_ok
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_StartStrip__prepare_ok:
    .a8
    lda.l SAME_SCUMM_VIEWPORT_STATE
    bne ScummV5_Camera_StartStrip__prepared
    clc
    rtl
ScummV5_Camera_StartStrip__prepared:
    .a8
    cmp #$02
    bne ScummV5_Camera_StartStrip__needs_read
    clc ; retained source column already checked and cached
    rtl
ScummV5_Camera_StartStrip__needs_read:
    .a8
    cmp #$01
    beq ScummV5_Camera_StartStrip__state_ok
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_StartStrip__state_ok:
    .a8
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_VIEWPORT_DIRECTORY
    tax
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    ; Bound source pixel strip offset uses full32-bit carry propagation.
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    tay
    beq ScummV5_Camera_StartStrip__offset_ready
ScummV5_Camera_StartStrip__offset_loop:
    .a16
    lda.l SAME_MSU1_REQUEST_OFFSET
    clc
    adc.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    sta.l SAME_MSU1_REQUEST_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    adc #$0000
    bcc ScummV5_Camera_StartStrip__offset_ok
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_StartStrip__offset_ok:
    .a16
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    dey
    bne ScummV5_Camera_StartStrip__offset_loop
ScummV5_Camera_StartStrip__offset_ready:
    .a16
    lda.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    pha
    lda.l SAME_SCUMM_VIEWPORT_MODE
    and #$00FF
    beq ScummV5_Camera_StartStrip__cold_capacity
    pla
    cmp #$0801
    bcc ScummV5_Camera_StartStrip__bounded_input
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_StartStrip__cold_capacity:
    .a16
    pla
ScummV5_Camera_StartStrip__bounded_input:
    .a16
    .endif
    sta.l SAME_MSU1_REQUEST_LENGTH
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    sta.l SAME_MSU1_DEST_CAPACITY
    lda #$0000
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    asl
    asl
    clc
    adc.l SAME_SCUMM_VIEWPORT_CRC_BASE
    tax
    clc
    adc #$0004
    cmp #SCUMM_MSU1_CAMERA_CRC_BYTES
    bcc ScummV5_Camera_StartStrip__crc_ok
    beq ScummV5_Camera_StartStrip__crc_ok
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_StartStrip__crc_ok:
    .a16
    lda.l ScummV5_MsuCameraStripCrcs,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    inx
    lda.l ScummV5_MsuCameraStripCrcs,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    sep #$20
    .a8
    lda #<SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION+1
    lda #$40
    sta.l SAME_MSU1_DESTINATION+2
    jml ScummV5_MsuLiveRoom_Start_Far__read

ScummV5_Camera_Prepare_Far:
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Camera_Prepare__writable
    clc ; ordinary presentation still owns its tile shadow
    rtl
ScummV5_Camera_Prepare__writable:
    .a8
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_VIEWPORT_DIRECTORY
    clc
    adc #$0014
    tax
    lda.l ScummV5_MsuVisualRecords,x
    beq ScummV5_Camera_Prepare__invalid
    cmp #$4000
    bcs ScummV5_Camera_Prepare__invalid
    sta.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    inx
    inx
    lda.l ScummV5_MsuVisualRecords,x
    beq ScummV5_Camera_Prepare__invalid
    cmp #(SAME_SCUMM_LIVE_ROOM_PENDING_CAPACITY/8+1)
    bcs ScummV5_Camera_Prepare__invalid
    sta.l SAME_SCUMM_VIEWPORT_ROOM_HEIGHT
    asl
    asl
    asl
    sta.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    inx
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    bcc ScummV5_Camera_Prepare__invalid
    sta.l SAME_SCUMM_VIEWPORT_PITCH
    lda.l SAME_SCUMM_VIEWPORT_DIRECTORY
    clc
    adc #$0004
    tax
    lda.l ScummV5_MsuVisualRecords,x
    cmp.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    bne ScummV5_Camera_Prepare__invalid
    bra ScummV5_Camera_Prepare__dimensions_ok
ScummV5_Camera_Prepare__invalid:
    .a16
    sep #$20
    .a8
    sec
    rtl
ScummV5_Camera_Prepare__dimensions_ok:
    .a16
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    cmp #$0100
    bcc ScummV5_Camera_Prepare__width_small
    lda #$0100
ScummV5_Camera_Prepare__width_small:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_WIDTH
    lda #$0100
    sec
    sbc.l SAME_SCUMM_VIEWPORT_WIDTH
    lsr
    sta.l SAME_SCUMM_VIEWPORT_DEST_X
    lda.l SAME_SCUMM_VIEWPORT_ROOM_HEIGHT
    cmp #SAME_VIDEO_SCENE_BOTTOM
    bcc ScummV5_Camera_Prepare__height_small
    lda #SAME_VIDEO_SCENE_BOTTOM
ScummV5_Camera_Prepare__height_small:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_HEIGHT
    lda #SAME_VIDEO_SCENE_BOTTOM
    sec
    sbc.l SAME_SCUMM_VIEWPORT_HEIGHT
    lsr
    sta.l SAME_SCUMM_VIEWPORT_DEST_Y
    lda.l SAME_SCUMM_VIEWPORT_ROOM_HEIGHT
    sec
    sbc.l SAME_SCUMM_VIEWPORT_HEIGHT
    lsr
    sta.l SAME_SCUMM_VIEWPORT_SOURCE_Y
    lda.l SAME_SCUMM_VIEWPORT_MODE
    and #$00FF
    beq ScummV5_Camera_Prepare__initial_x
    lda.l SAME_VIDEO_SURFACE_PENDING_XSTART
    bra ScummV5_Camera_Prepare__x_inset
ScummV5_Camera_Prepare__initial_x:
    .a16
    lda #$0000
ScummV5_Camera_Prepare__x_inset:
    .a16
    clc
    adc #$0020
    bpl ScummV5_Camera_Prepare__x_positive
    lda #$0000
ScummV5_Camera_Prepare__x_positive:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_TEMP
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    sec
    sbc.l SAME_SCUMM_VIEWPORT_WIDTH
    cmp.l SAME_SCUMM_VIEWPORT_TEMP
    bcc ScummV5_Camera_Prepare__x_clamped
    lda.l SAME_SCUMM_VIEWPORT_TEMP
ScummV5_Camera_Prepare__x_clamped:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_SOURCE_X
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    sep #$20
    .a8
    lda.l SAME_SCUMM_VIEWPORT_MODE
    beq ScummV5_Camera_Prepare__cold_grid
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    tay
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    sec
    sbc.l SAME_SCUMM_VIEWPORT_WIDTH
    tax
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_X
    jsl Same_VideoSurface_BeginScroll_Far
    bcc ScummV5_Camera_Prepare__retained_step
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_Prepare__retained_step:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    txa
    sta.l SAME_SCUMM_VIEWPORT_SOURCE_X
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    cmp #$FFFF
    bne ScummV5_Camera_Prepare__retained_read
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_STATE
    lda #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ROOM
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    lda #SCUMM_MSU_ROOM_VALIDATED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_Camera_Prepare__retained_read:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    sta.l SAME_SCUMM_VIEWPORT_FIRST
    inc
    sta.l SAME_SCUMM_VIEWPORT_LAST
    jmp ScummV5_Camera_Prepare__directory
ScummV5_Camera_Prepare__cold_grid:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_X
    .endif
    lsr
    lsr
    lsr
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    sta.l SAME_SCUMM_VIEWPORT_FIRST
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_X
    clc
    adc.l SAME_SCUMM_VIEWPORT_WIDTH
    clc
    adc #$0007
    lsr
    lsr
    lsr
    sta.l SAME_SCUMM_VIEWPORT_LAST
ScummV5_Camera_Prepare__directory:
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    sep #$20
    .a8
    sta.l SAME_SCUMM_VIEWPORT_ROOM
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_MsuCameraCrcOffsets,x
    sta.l SAME_SCUMM_VIEWPORT_CRC_BASE
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda.l SAME_SCUMM_VIEWPORT_MODE
    and #$00FF
    bne ScummV5_Camera_Prepare__staging_ready
    .endif
    ; Zero only the staging alias after its former backend owner is idle.
    lda #$0000
    ldx #$0000
ScummV5_Camera_Prepare__clear:
    .a16
    sta.l SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE,x
    inx
    inx
    cpx #$E000
    bcc ScummV5_Camera_Prepare__clear
ScummV5_Camera_Prepare__staging_ready:
    .a16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl

; Only called after the existing provider has verified this entire strip.
ScummV5_Camera_ConsumeStrip_Far:
    .a8
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    beq ScummV5_Camera_ConsumeStrip__length_ok
    sep #$20
    .a8
    sec
    rtl
ScummV5_Camera_ConsumeStrip__length_ok:
    .a16
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda.l SAME_SCUMM_VIEWPORT_MODE
    and #$00FF
    beq ScummV5_Camera_ConsumeStrip__cold
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_BASE&$FFFF
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    sep #$20
    .a8
    lda #$40
    sta SAME_VIDEO_SURFACE_DP_SOURCE+2
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_Y
    tay
    lda.l SAME_SCUMM_VIEWPORT_DEST_Y
    tax
    lda.l SAME_SCUMM_VIEWPORT_HEIGHT
    jsl Same_VideoSurface_CheckedScrollColumn_Far
    bcc ScummV5_Camera_ConsumeStrip__retained_valid
    sec
    rtl
ScummV5_Camera_ConsumeStrip__retained_valid:
    .a16
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl
ScummV5_Camera_ConsumeStrip__cold:
    .a16
    .endif
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    asl
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; world left of strip
    sec
    sbc.l SAME_SCUMM_VIEWPORT_SOURCE_X
    bpl ScummV5_Camera_ConsumeStrip__left_visible
    ; Crop the first strip to a nonaligned camera origin.
    eor #$FFFF
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; source column
    lda #$0000
    bra ScummV5_Camera_ConsumeStrip__left_ready
ScummV5_Camera_ConsumeStrip__left_visible:
    .a16
    pha
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1
    pla
ScummV5_Camera_ConsumeStrip__left_ready:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; destination column relative to scene
    lda #$0008
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; columns
    lda.l SAME_SCUMM_VIEWPORT_WIDTH
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    bcs ScummV5_Camera_ConsumeStrip__width_ready
    sta.l SCUMM_LIVE_ROOM_TEMP3
ScummV5_Camera_ConsumeStrip__width_ready:
    .a16
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_Y
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; pending source cursor
    lda.l SAME_SCUMM_VIEWPORT_DEST_Y
    xba
    clc
    adc.l SAME_SCUMM_VIEWPORT_DEST_X
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; stage destination cursor
    lda.l SAME_SCUMM_VIEWPORT_HEIGHT
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; rows
ScummV5_Camera_ConsumeStrip__row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tay
    lda.l SCUMM_LIVE_ROOM_TEMP2
    tax
    lda.l SCUMM_LIVE_ROOM_TEMP3
    sta.l SCUMM_LIVE_ROOM_TEMP5
ScummV5_Camera_ConsumeStrip__byte:
    .a16
    ; 65816 has no long indexed-Y. Preserve X while reading the checked source.
    phx
    tyx
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    plx
    sta.l SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE,x
    rep #$20
    .a16
    inx
    iny
    lda.l SCUMM_LIVE_ROOM_TEMP5
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP5
    bne ScummV5_Camera_ConsumeStrip__byte
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0008
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc #$0100
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP4
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP4
    bne ScummV5_Camera_ConsumeStrip__row
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    inc
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    cmp.l SAME_SCUMM_VIEWPORT_LAST
    bcs ScummV5_Camera_ConsumeStrip__complete
    sep #$20
    .a8
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_Camera_ConsumeStrip__complete:
    .a8
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl

; Room commit only. The checked SC5VIS descriptor supplies source geometry.
; SCUMM v5 starts a room at the left logical 320-pixel viewport, before ENCD.
; Same-room camera refresh MUST NOT reset authored roomOps scroll bounds.
ScummV5_Camera_InstallRoomBounds_Far:
    .a16
    rep #$20
    .a16
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    sta.l SAME_SCUMM_C10_ROOM_WIDTH
    cmp #$0140
    bcs ScummV5_Camera_InstallRoomBounds__wide
    lda #$0140
ScummV5_Camera_InstallRoomBounds__wide:
    .a16
    sec
    sbc #$00A0
    sta.l SAME_SCUMM_C10_SCROLL_MAX
    lda #$00A0
    sta.l SAME_SCUMM_C10_SCROLL_MIN
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_CAMERA_DEST_X
    sta.l SAME_SCUMM_CAMERA_REQUEST_X
    lda #$0000
    sta.l SAME_SCUMM_CAMERA_SCREEN_START_STRIP
    sta.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    lda #$0027
    sta.l SAME_SCUMM_CAMERA_SCREEN_END_STRIP
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    lda #$01
    sta.l SAME_SCUMM_CAMERA_UPDATE_PENDING
    rep #$20
    .a16
    rtl

ScummV5_Camera_InstallGeometry_Far:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    sta.l SAME_VIDEO_SURFACE_WIDTH
    lda.l SAME_SCUMM_VIEWPORT_ROOM_HEIGHT
    sta.l SAME_VIDEO_SURFACE_HEIGHT
    lda.l SAME_SCUMM_VIEWPORT_PITCH
    sta.l SAME_VIDEO_SURFACE_PITCH
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    lda.l SAME_SCUMM_VIEWPORT_SOURCE_Y
    sta.l SAME_VIDEO_SURFACE_SOURCE_Y
    lda.l SAME_SCUMM_VIEWPORT_DEST_X
    sta.l SAME_VIDEO_SURFACE_DEST_X
    lda.l SAME_SCUMM_VIEWPORT_DEST_Y
    sta.l SAME_VIDEO_SURFACE_DEST_Y
    lda.l SAME_SCUMM_VIEWPORT_WIDTH
    sta.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lda.l SAME_SCUMM_VIEWPORT_HEIGHT
    sta.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    rtl

ScummV5_Camera_ServicePending_Far:
    .a16
    sep #$20
    .a8
    ; Incoming-room publication belongs exclusively to M24. Camera refresh
    ; may neither steal its checked pixels nor start a second request.
    lda.l SAME_SCUMM_M23A_PHASE
    beq ScummV5_Camera_ServicePending__lifecycle_idle
    clc
    rtl
ScummV5_Camera_ServicePending__lifecycle_idle:
    .a8
    lda.l SAME_SCUMM_VIEWPORT_STATE
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    cmp #$04
    bne ScummV5_Camera_ServicePending__not_waiting_ppu
    jmp ScummV5_Camera_ServicePending__retained_wait
ScummV5_Camera_ServicePending__not_waiting_ppu:
    .a8
    .endif
    cmp #$03
    bne ScummV5_Camera_ServicePending__check_checked
    jmp ScummV5_Camera_ServicePending__publish
ScummV5_Camera_ServicePending__check_checked:
    .a8
    cmp #$02
    bne ScummV5_Camera_ServicePending__not_ready
    lda.l SAME_SCUMM_VIEWPORT_MODE
    bne ScummV5_Camera_ServicePending__camera_owned
    clc
    rtl
ScummV5_Camera_ServicePending__camera_owned:
    .a8
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    jmp ScummV5_Camera_ServicePending__retained_commit
    .else
    jmp ScummV5_Camera_ServicePending__coalesce
    .endif
ScummV5_Camera_ServicePending__not_ready:
    .a8
    cmp #$00
    beq ScummV5_Camera_ServicePending__new
    clc
    rtl
ScummV5_Camera_ServicePending__new:
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Camera_ServicePending__available
    clc
    rtl
ScummV5_Camera_ServicePending__available:
    .a8
    ; Keep the published geometry untouched until all incoming strips validate.
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_XSTART
    clc
    adc #$0020
    bpl ScummV5_Camera_ServicePending__positive
    lda #$0000
ScummV5_Camera_ServicePending__positive:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_TEMP
    lda.l SAME_VIDEO_SURFACE_WIDTH
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_WIDTH
    cmp.l SAME_SCUMM_VIEWPORT_TEMP
    bcc ScummV5_Camera_ServicePending__bounded
    lda.l SAME_SCUMM_VIEWPORT_TEMP
ScummV5_Camera_ServicePending__bounded:
    .a16
    cmp.l SAME_VIDEO_SURFACE_SOURCE_X
    bne ScummV5_Camera_ServicePending__changed
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    sta.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
    clc
    rtl
ScummV5_Camera_ServicePending__changed:
    .a8
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; Camera notifications may originate inside an executing opcode. Request
    ; a foreground turn here; only the late visual phase may compose actors.
    lda.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
    cmp #$01
    beq ScummV5_Camera_ServicePending__foreground_served
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
    clc
    rtl
ScummV5_Camera_ServicePending__foreground_served:
    .a8
    .endif
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    bne ScummV5_Camera_ServicePending__actor_drained
    jsl ScummV5_ActorPose_Cancel_Far
    clc
    rtl
ScummV5_Camera_ServicePending__actor_drained:
    .a8
    ; Storage runs after scripts. Retire a completed executable read through
    ; its cache owner before claiming the camera request; otherwise the next
    ; engine turn can start another code read forever and starve this viewport.
    ; READY/waiter pins and failure provenance remain owned by the code cache.
    jsl ScummV5_MsuProgram_ReconcileRead_Far
    bcc ScummV5_Camera_ServicePending__read_reconciled
    rtl
ScummV5_Camera_ServicePending__read_reconciled:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    beq ScummV5_Camera_ServicePending__wait
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    cmp #$FF
    bne ScummV5_Camera_ServicePending__wait
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_SCUMM_MSU_ROOM_ID
    lda #$01
    sta.l SAME_SCUMM_VIEWPORT_MODE
    lda #SCUMM_LIVE_ROOM_STAGE_PIXELS
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
ScummV5_Camera_ServicePending__wait:
    .a8
    clc
    rtl
.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
; Runs only from the late visual phase, never inside a SCUMM opcode.
ScummV5_Camera_ServiceForeground_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
    cmp #$02
    bne ScummV5_Camera_ServiceForeground__done
    lda.l SAME_SCUMM_M23A_PHASE
    ora.l SAME_SCUMM_VIEWPORT_STATE
    bne ScummV5_Camera_ServiceForeground__done
    jsl Same_VideoSurface_CanWrite_Far
    bcs ScummV5_Camera_ServiceForeground__done
    jsl ScummV5_MsuProgram_ReconcileRead_Far
    bcs ScummV5_Camera_ServiceForeground__done
    jsl ScummV5_Controller_RenderActor_Far
    jsl ScummV5_Cursor_Frame_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    bne ScummV5_Camera_ServiceForeground__done
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    bne ScummV5_Camera_ServiceForeground__done
    lda.l SAME_SCUMM_CURSOR_PENDING
    ora.l SAME_SCUMM_CURSOR_PENDING+1
    bne ScummV5_Camera_ServiceForeground__done
    lda #$01
    sta.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
ScummV5_Camera_ServiceForeground__done:
    plp
    rtl

ScummV5_Camera_ServicePending__retained_commit:
    .a8
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    jsl Same_VideoSurface_CanPublishRetained_Far
    bcc ScummV5_Camera_ServicePending__retained_capacity
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl
ScummV5_Camera_ServicePending__retained_capacity:
    .a8
    jsl Same_VideoSurface_ComposeRetainedScroll_Far
    bcc ScummV5_Camera_ServicePending__retained_published
    ; A malformed journal is an explicit transaction failure, never a retry
    ; after silently publishing partial pixels.
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_ServicePending__retained_published:
    .a8
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl
ScummV5_Camera_ServicePending__retained_wait:
    .a8
    jsl Same_VideoSurface_ScrollPresented_Far
    bcs ScummV5_Camera_ServicePending__retained_pending
    jsl ScummV5_Camera_InstallGeometry_Far
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    sta.l SAME_SCUMM_VIEWPORT_MODE
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    sta.l SAME_SCUMM_VIEWPORT_ACTOR_SERVED
    lda #$01
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rtl
ScummV5_Camera_ServicePending__retained_pending:
    .a8
    clc
    rtl
.endif

ScummV5_Camera_ServicePending__commit:
    .a8
    ; Incoming staged pixels are complete. No producer can publish the aliased
    ; tile shadow until ownership is synchronously released below.
    rep #$30
    .a16
    .i16
    ldx #$0000
ScummV5_Camera_ServicePending__copy:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE,x
    sta.l SAME_SCUMM_LIVE_ROOM_SURFACE_BASE,x
    inx
    inx
    cpx #(SAME_VIDEO_SCENE_BOTTOM*256)
    bcc ScummV5_Camera_ServicePending__copy
    jsl Same_VideoSurface_InvalidateTileCache_Far
    jsl Same_VideoSurface_InvalidateActorUnderlay_Far
    jsl ScummV5_Camera_InstallGeometry_Far
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
    lda #$03
    sta.l SAME_SCUMM_VIEWPORT_STATE
ScummV5_Camera_ServicePending__publish:
    .a8
    ; Transfer this owner's completed surface to the shared video service.
    ; CanWrite refuses external staging owners, including ourselves. Release
    ; only during this synchronous call (no engine producer runs inside it),
    ; and reclaim installed ownership on refusal. NMI remains video-owned.
    ; Never recopy the stage after the backend reclaims its tile-shadow alias.
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    jsl Same_VideoSurface_PushDirtyPresent_Far
    bcc ScummV5_Camera_ServicePending__published
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl
ScummV5_Camera_ServicePending__published:
    .a8
    sep #$20
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    sta.l SAME_SCUMM_VIEWPORT_MODE
    ; The logical camera can advance while strips load. Reconcile the latest
    ; desired crop after this PRESENT commits; never acknowledge an old crop
    ; as the newest request. The idle comparison clears an unchanged request.
    lda #$01
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rtl

; A checked crop is still private staging, not a presentation obligation.
; If the authored camera advanced during I/O, avoid installing and encoding
; an obsolete full frame. Keep the old displayed geometry and restart through
; the same checked-strip adapter. This never cancels an in-flight provider read.
ScummV5_Camera_ServicePending__coalesce:
    .a8
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_XSTART
    clc
    adc #$0020
    bpl ScummV5_Camera_ServicePending__latest_positive
    lda #$0000
ScummV5_Camera_ServicePending__latest_positive:
    .a16
    sta.l SAME_SCUMM_VIEWPORT_TEMP
    lda.l SAME_SCUMM_VIEWPORT_ROOM_WIDTH
    sec
    sbc.l SAME_SCUMM_VIEWPORT_WIDTH
    cmp.l SAME_SCUMM_VIEWPORT_TEMP
    bcc ScummV5_Camera_ServicePending__latest_bounded
    lda.l SAME_SCUMM_VIEWPORT_TEMP
ScummV5_Camera_ServicePending__latest_bounded:
    .a16
    cmp.l SAME_SCUMM_VIEWPORT_SOURCE_X
    bne ScummV5_Camera_ServicePending__superseded
    sep #$20
    .a8
    jmp ScummV5_Camera_ServicePending__commit
ScummV5_Camera_ServicePending__superseded:
    .a16
    sep #$20
    .a8
    ; Temporarily release only inside synchronous Prepare, which reacquires
    ; the same staging alias before returning. No producer interleaves here.
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    jsl ScummV5_Camera_Prepare_Far
    bcc ScummV5_Camera_ServicePending__reprepared
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_ServicePending__reprepared:
    .a8
    lda.l SAME_SCUMM_VIEWPORT_STATE
    bne ScummV5_Camera_ServicePending__restart_checked
    ; Backpressure: keep exclusive ownership of the old unpublished stage.
    lda #$02
    sta.l SAME_SCUMM_VIEWPORT_STATE
    clc
    rtl
ScummV5_Camera_ServicePending__restart_checked:
    .a8
    lda #SCUMM_LIVE_ROOM_STAGE_PIXELS
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl

ScummV5_Camera_Invalid_Far:
    .a8
    sep #$20
    .a8
    jml ScummV5_MsuLiveRoom_Start_Far__invalid

; A scripted room request can arrive while camera strips own the checked
; cursor. Drain the accepted read, discard its unpublished viewport, then
; begin the real pending-room request. Never advertise camera completion as
; incoming metadata validation. Carry set means still draining.
ScummV5_Camera_YieldToRoom_Far:
    .a8
    sep #$20
    lda.l SAME_SCUMM_VIEWPORT_MODE
    beq ScummV5_Camera_YieldToRoom__idle
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$04
    bne ScummV5_Camera_YieldToRoom__idle
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_Camera_YieldToRoom__drained
    sec
    rtl
ScummV5_Camera_YieldToRoom__drained:
    .a8
    cmp #SAME_MSU1_STATE_ERROR
    bne ScummV5_Camera_YieldToRoom__verified_or_idle
    jsl ScummV5_MsuRoom_Service_Far__fail
    sec
    rtl
ScummV5_Camera_YieldToRoom__verified_or_idle:
    .a8
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    jsl Same_VideoSurface_AbortScroll_Far
    bcc ScummV5_Camera_YieldToRoom__aborted
    sec
    rtl
ScummV5_Camera_YieldToRoom__aborted:
    .a8
    .else
    jsl Same_VideoSurface_InvalidateTileCache_Far
    .endif
    sep #$20
    lda #$00
    sta.l SAME_SCUMM_VIEWPORT_STATE
    sta.l SAME_SCUMM_VIEWPORT_MODE
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    jsl ScummV5_MsuRoom_Request_Far
ScummV5_Camera_YieldToRoom__idle:
    .a8
    clc
    rtl
