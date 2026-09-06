; Target-neutral fixed display-surface facade for the accepted INDEX8 service.
; SCUMM calls only these routines; carrier addresses and Mode-3 state remain here.
.bank 20
.org $8000

SAME_VIDEO_SURFACE_STATE              = SAME_BWRAM_BACKEND_BASE+$0080
SAME_VIDEO_SURFACE_ROOM               = SAME_VIDEO_SURFACE_STATE+$00
SAME_VIDEO_SURFACE_ROOM_GENERATION    = SAME_VIDEO_SURFACE_STATE+$02
SAME_VIDEO_SURFACE_STATUS             = SAME_VIDEO_SURFACE_STATE+$04
SAME_VIDEO_SURFACE_RECORD             = SAME_VIDEO_SURFACE_STATE+$05
SAME_VIDEO_SURFACE_WIDTH              = SAME_VIDEO_SURFACE_STATE+$06
SAME_VIDEO_SURFACE_HEIGHT             = SAME_VIDEO_SURFACE_STATE+$08
SAME_VIDEO_SURFACE_PITCH              = SAME_VIDEO_SURFACE_STATE+$0A
SAME_VIDEO_SURFACE_SOURCE_X           = SAME_VIDEO_SURFACE_STATE+$0C
SAME_VIDEO_SURFACE_SOURCE_Y           = SAME_VIDEO_SURFACE_STATE+$0E
SAME_VIDEO_SURFACE_DEST_X             = SAME_VIDEO_SURFACE_STATE+$10
SAME_VIDEO_SURFACE_DEST_Y             = SAME_VIDEO_SURFACE_STATE+$12
SAME_VIDEO_SURFACE_COPY_WIDTH         = SAME_VIDEO_SURFACE_STATE+$14
SAME_VIDEO_SURFACE_COPY_HEIGHT        = SAME_VIDEO_SURFACE_STATE+$16
SAME_VIDEO_SURFACE_ROW                = SAME_VIDEO_SURFACE_STATE+$18
SAME_VIDEO_SURFACE_DESCRIPTOR         = SAME_VIDEO_SURFACE_STATE+$1A
SAME_VIDEO_SURFACE_NEXT_GENERATION    = SAME_VIDEO_SURFACE_STATE+$1C
SAME_VIDEO_SURFACE_PRESENTED_ROOM     = SAME_VIDEO_SURFACE_STATE+$20
SAME_VIDEO_SURFACE_PRESENTED_GENERATION = SAME_VIDEO_SURFACE_STATE+$22
SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X = SAME_VIDEO_SURFACE_STATE+$24
SAME_VIDEO_SURFACE_PENDING_VISUAL     = SAME_VIDEO_SURFACE_STATE+$26
SAME_VIDEO_SURFACE_PENDING_ROOM       = SAME_VIDEO_SURFACE_STATE+$27
SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION = SAME_VIDEO_SURFACE_STATE+$28
SAME_VIDEO_SURFACE_PENDING_XSTART     = SAME_VIDEO_SURFACE_STATE+$2A
SAME_VIDEO_SURFACE_CAMERA_PRESENT_COUNT = SAME_VIDEO_SURFACE_STATE+$2C
SAME_VIDEO_SURFACE_CAMERA_NOCHANGE_COUNT = SAME_VIDEO_SURFACE_STATE+$2E
SAME_VIDEO_SURFACE_CAMERA_DEFER_COUNT = SAME_VIDEO_SURFACE_STATE+$30
SAME_VIDEO_SURFACE_CAMERA_STALE_COUNT = SAME_VIDEO_SURFACE_STATE+$32
SAME_VIDEO_SURFACE_STATE_SIZE         = $0034
SAME_VIDEO_SURFACE_STATUS_OK          = $01
SAME_VIDEO_SURFACE_STATUS_UNAVAILABLE = $02
SAME_VIDEO_SURFACE_STATUS_INVALID     = $03
SAME_VIDEO_SURFACE_STATUS_LOCKED      = $04
SAME_VIDEO_SURFACE_DESCRIPTOR_SIZE    = $0016
SAME_VIDEO_SURFACE_DP_SOURCE          = $00F0
SAME_VIDEO_SURFACE_DP_ROWS            = $00F3

Same_VideoSurface_CanWrite_Far:
    php
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_IDLE
    bne Same_VideoSurface_CanWrite__no
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    bne Same_VideoSurface_CanWrite__no
    plp
    clc
    rtl
Same_VideoSurface_CanWrite__no:
    plp
    sec
    rtl

; Target-neutral indexed-surface write contract.
; Input: A low byte is the indexed pixel, X is the byte offset in the active
; surface.  P, A width, and X are preserved.  The selected carrier owns the
; destination backing and may change without any SCUMM caller change.
Same_VideoSurface_WriteIndexedPixel_Far:
    php
    sep #$20
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    plp
    rtl

; Generic talk/HUD facade. The selected presentation service supplies the
; implementation without changing the established far-call ABI.
.if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
Same_VideoText_ShowSegment_Far = Same_VideoOverlay_ShowTalkSegment_Far
Same_VideoText_Hide_Far = Same_VideoOverlay_Hide_Far
.else
Same_VideoText_ShowSegment_Far = Same_VideoSurface_NoTextService_Far
Same_VideoText_Hide_Far = Same_VideoSurface_NoTextService_Far
Same_VideoSurface_NoTextService_Far:
    rtl
.endif

; Input A=u8 room identity. Output X=descriptor byte offset, carry clear.
Same_VideoSurface_FindVisual:
    sep #$20
    .a8
    sta.l SAME_VIDEO_SURFACE_ROOM
    rep #$10
    .i16
    ldx #$0000
Same_VideoSurface_FindVisual__loop:
    cmp.l SCUMM_V5_ROOM_VISUAL_DIRECTORY,x
    beq Same_VideoSurface_FindVisual__found
    rep #$20
    .a16
    txa
    clc
    adc #SAME_VIDEO_SURFACE_DESCRIPTOR_SIZE
    tax
    sep #$20
    .a8
    cpx #(SCUMM_V5_ROOM_VISUAL_COUNT*SAME_VIDEO_SURFACE_DESCRIPTOR_SIZE)
    bcc Same_VideoSurface_FindVisual__loop
    sec
    rts
Same_VideoSurface_FindVisual__found:
    rep #$20
    .a16
    txa
    sta.l SAME_VIDEO_SURFACE_DESCRIPTOR
    sep #$20
    .a8
    clc
    rts

Same_VideoSurface_ValidateDescriptor:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DESCRIPTOR
    tax
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$01,x
    cmp #SCUMM_V5_ROOM_VISUAL_DESCRIPTOR_MAGIC
    bne Same_VideoSurface_ValidateDescriptor__bad
    sep #$20
    .a8
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$03,x
    cmp #SCUMM_V5_ROOM_VISUAL_DESCRIPTOR_VERSION
    bne Same_VideoSurface_ValidateDescriptor__bad8
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$04,x
    cmp #$01
    bne Same_VideoSurface_ValidateDescriptor__bad8
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$05,x
    cmp #$01
    bne Same_VideoSurface_ValidateDescriptor__bad8
    rep #$20
    .a16
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$06,x
    beq Same_VideoSurface_ValidateDescriptor__bad
    sta.l SAME_VIDEO_SURFACE_WIDTH
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$08,x
    beq Same_VideoSurface_ValidateDescriptor__bad
    sta.l SAME_VIDEO_SURFACE_HEIGHT
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$0A,x
    cmp.l SAME_VIDEO_SURFACE_WIDTH
    bcc Same_VideoSurface_ValidateDescriptor__bad
    sta.l SAME_VIDEO_SURFACE_PITCH
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$12,x
    cmp.l SAME_VIDEO_SURFACE_HEIGHT
    bne Same_VideoSurface_ValidateDescriptor__bad
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$14,x
    cmp #$0300
    bne Same_VideoSurface_ValidateDescriptor__bad
    jsr Same_VideoSurface_ValidateRows
    bcs Same_VideoSurface_ValidateDescriptor__bad
    clc
    rts
Same_VideoSurface_ValidateDescriptor__bad:
    sep #$20
    .a8
Same_VideoSurface_ValidateDescriptor__bad8:
    sec
    rts

; Validate every bank-safe row before any display mutation occurs.
Same_VideoSurface_ValidateRows:
    jsr Same_VideoSurface_LoadRowTablePointer
    rep #$30
    .a16
    .i16
    ldx #$0000
    ldy #$0000
Same_VideoSurface_ValidateRows__loop:
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    iny
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    iny
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    cmp #SCUMM_V5_ROOM_VISUAL_FIRST_DATA_BANK
    bcc Same_VideoSurface_ValidateRows__bad8
    cmp #(SCUMM_V5_ROOM_VISUAL_LAST_DATA_BANK+$01)
    bcs Same_VideoSurface_ValidateRows__bad8
    iny
    rep #$20
    .a16
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    cmp.l SAME_VIDEO_SURFACE_WIDTH
    bcc Same_VideoSurface_ValidateRows__bad
    iny
    iny
    lda SAME_VIDEO_SURFACE_DP_SOURCE
    cmp #$8000
    bcc Same_VideoSurface_ValidateRows__bad
    clc
    adc.l SAME_VIDEO_SURFACE_WIDTH
    bcs Same_VideoSurface_ValidateRows__bad
    inx
    txa
    cmp.l SAME_VIDEO_SURFACE_HEIGHT
    bcc Same_VideoSurface_ValidateRows__loop
    clc
    rts
Same_VideoSurface_ValidateRows__bad:
    sec
    rts
Same_VideoSurface_ValidateRows__bad8:
    rep #$20
    .a16
    sec
    rts

Same_VideoSurface_Clear:
    rep #$30
    .a16
    .i16
    ldx #$0000
    sep #$20
    .a8
    lda #$00
Same_VideoSurface_Clear__loop:
    .a8
    .i16
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    cpx #SAME_BWRAM_SURFACE_SIZE
    bcc Same_VideoSurface_Clear__loop
    rts

Same_VideoSurface_ComputeProjection:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_WIDTH
    cmp #$0100
    bcc Same_VideoSurface_ComputeProjection__width_small
    lda #$0100
Same_VideoSurface_ComputeProjection__width_small:
    .a16
    .i16
    sta.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lda.l SAME_VIDEO_SURFACE_WIDTH
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lsr
    sta.l SAME_VIDEO_SURFACE_SOURCE_X
    lda #$0100
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lsr
    sta.l SAME_VIDEO_SURFACE_DEST_X
    lda.l SAME_VIDEO_SURFACE_HEIGHT
    cmp #$00E0
    bcc Same_VideoSurface_ComputeProjection__height_small
    lda #$00E0
Same_VideoSurface_ComputeProjection__height_small:
    .a16
    .i16
    sta.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    lda.l SAME_VIDEO_SURFACE_HEIGHT
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    lsr
    sta.l SAME_VIDEO_SURFACE_SOURCE_Y
    lda #$00E0
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    lsr
    sta.l SAME_VIDEO_SURFACE_DEST_Y
    rts

; Publish the 320-pixel SCUMM virtual screen through the fixed 256-pixel SAME
; display.  The 32-pixel inset is target-neutral viewport composition, not PPU
; scrolling; the Mode-3 backend continues seeing only a completed surface.
Same_VideoSurface_ComputeCameraProjection:
    jsr Same_VideoSurface_ComputeProjection
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_XSTART
    clc
    adc #$0020
    bpl Same_VideoSurface_ComputeCameraProjection__nonnegative
    lda #$0000
Same_VideoSurface_ComputeCameraProjection__nonnegative:
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_VIDEO_SURFACE_WIDTH
    sec
    sbc.l SAME_VIDEO_SURFACE_COPY_WIDTH
    cmp.l SAME_MODE3_WORK_TEMP
    bcs Same_VideoSurface_ComputeCameraProjection__bounded
    sta.l SAME_MODE3_WORK_TEMP
Same_VideoSurface_ComputeCameraProjection__bounded:
    lda.l SAME_MODE3_WORK_TEMP
    sta.l SAME_VIDEO_SURFACE_SOURCE_X
    rts

Same_VideoSurface_LoadPalette:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DESCRIPTOR
    tax
    sep #$20
    .a8
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$0C,x
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$0D,x
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$0E,x
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    rep #$10
    .i16
    ldx #$0000
    ldy #$0000
Same_VideoSurface_LoadPalette__loop:
    .a8
    .i16
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_MODE3_LIVE_PALETTE,x
    inx
    iny
    cpy #$0300
    bcc Same_VideoSurface_LoadPalette__loop
    rts

Same_VideoSurface_LoadRowTablePointer:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DESCRIPTOR
    tax
    sep #$20
    .a8
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$0F,x
    sta SAME_VIDEO_SURFACE_DP_ROWS
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$10,x
    sta SAME_VIDEO_SURFACE_DP_ROWS+$01
    lda.l SCUMM_V5_ROOM_VISUAL_DIRECTORY+$11,x
    sta SAME_VIDEO_SURFACE_DP_ROWS+$02
    rts

Same_VideoSurface_BlitProjection:
    jsr Same_VideoSurface_LoadRowTablePointer
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_VIDEO_SURFACE_ROW
Same_VideoSurface_BlitProjection__row:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_ROW
    sta.l SAME_MODE3_WORK_TEMP
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_TEMP
    tay
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    iny
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    iny
    lda [SAME_VIDEO_SURFACE_DP_ROWS],y
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    rep #$20
    .a16
    lda SAME_VIDEO_SURFACE_DP_SOURCE
    clc
    adc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda.l SAME_VIDEO_SURFACE_DEST_Y
    clc
    adc.l SAME_VIDEO_SURFACE_ROW
    xba
    and #$FF00
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    tax
    ldy #$0000
    sep #$20
    .a8
Same_VideoSurface_BlitProjection__pixel:
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    iny
    rep #$20
    .a16
    tya
    cmp.l SAME_VIDEO_SURFACE_COPY_WIDTH
    bcc Same_VideoSurface_BlitProjection__pixel8
    lda.l SAME_VIDEO_SURFACE_ROW
    inc
    sta.l SAME_VIDEO_SURFACE_ROW
    cmp.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    bcc Same_VideoSurface_BlitProjection__row
    rts
Same_VideoSurface_BlitProjection__pixel8:
    sep #$20
    .a8
    bra Same_VideoSurface_BlitProjection__pixel

Same_VideoSurface_PushPresentation:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-2)
    bcc Same_VideoSurface_PushPresentation__space
    jmp Same_VideoSurface_PushPresentation__fail
Same_VideoSurface_PushPresentation__space:
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SURFACE_DIRTY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    lda #$0100
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda #$00E0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushPresentation__fail
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_PALETTE_WRITE
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda #$0100
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushPresentation__fail
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_PRESENT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    inc
    bne Same_VideoSurface_PushPresentation__generation_ok
    inc
Same_VideoSurface_PushPresentation__generation_ok:
    sta.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushPresentation__fail
    clc
    rts
Same_VideoSurface_PushPresentation__fail:
    sec
    rts

; Same-room camera reprojection retains the installed RGB8 palette and emits
; only full-display dirty plus the next generation PRESENT.
Same_VideoSurface_PushDirtyPresent:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-1)
    bcc Same_VideoSurface_PushDirtyPresent__capacity_ok
    jmp Same_VideoSurface_PushDirtyPresent__fail
Same_VideoSurface_PushDirtyPresent__capacity_ok:
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SURFACE_DIRTY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    lda #$0100
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda #$00E0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushDirtyPresent__fail
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_PRESENT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    inc
    bne Same_VideoSurface_PushDirtyPresent__generation_ok
    inc
Same_VideoSurface_PushDirtyPresent__generation_ok:
    sta.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushDirtyPresent__fail
    clc
    rts
Same_VideoSurface_PushDirtyPresent__fail:
    sec
    rts

; Input A=u8 room. Complete validation precedes any display mutation.
Same_VideoSurface_ComposeRoom_Far:
    php
    pha
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ComposeRoom__locked
    pla
    jsr Same_VideoSurface_FindVisual
    bcs Same_VideoSurface_ComposeRoom__missing
    jsr Same_VideoSurface_ValidateDescriptor
    bcs Same_VideoSurface_ComposeRoom__invalid
    jsr Same_VideoSurface_ComputeProjection
    sep #$20
    .a8
    jsr Same_VideoSurface_Clear
    jsr Same_VideoSurface_LoadPalette
    jsr Same_VideoSurface_BlitProjection
    sep #$20
    .a8
    jsr Same_VideoSurface_PushPresentation
    bcs Same_VideoSurface_ComposeRoom__invalid
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_SURFACE_STATUS
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_VIDEO_SURFACE_PRESENTED_ROOM
    plp
    clc
    rtl
Same_VideoSurface_ComposeRoom__locked:
    .a8
    pla
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    bra Same_VideoSurface_ComposeRoom__status_fail
Same_VideoSurface_ComposeRoom__missing:
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_UNAVAILABLE
    bra Same_VideoSurface_ComposeRoom__status_fail
Same_VideoSurface_ComposeRoom__invalid:
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_INVALID
Same_VideoSurface_ComposeRoom__status_fail:
    sep #$20
    .a8
    sta.l SAME_VIDEO_SURFACE_STATUS
    plp
    sec
    rtl

; Called after canonical camera publication.  One latest request is retained
; while the backend owns the live surface; it is revalidated after unlock.
Same_VideoSurface_CameraPublished_Far:
    php
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_VIDEO_SURFACE_PENDING_ROOM
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION
    lda.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    sta.l SAME_VIDEO_SURFACE_PENDING_XSTART
    jsr Same_VideoSurface_ServicePending
    plp
    rtl

Same_VideoSurface_ServicePending_Far:
    php
    jsr Same_VideoSurface_ServicePending
    plp
    rtl

; Optional synchronous boundary for a producer that must complete its
; target-neutral presentation request before continuing. Backend event
; ownership remains inside the video service/kernel adapter.
; Publish a surface after an engine compositor has drawn an actor over the
; already-composed room.  The compositor never touches PPU registers or DMA
; ownership; it only uses the same indexed surface and event path.
Same_VideoSurface_PushDirtyPresent_Far:
    php
    jsr Same_VideoSurface_PushDirtyPresent
    plp
    rtl

Same_VideoSurface_ServicePending:
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    bne Same_VideoSurface_ServicePending__owned
    clc
    rts
Same_VideoSurface_ServicePending__owned:
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne Same_VideoSurface_ServicePending__stale
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne Same_VideoSurface_ServicePending__stale16
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ServicePending__defer
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    jsr Same_VideoSurface_FindVisual
    bcs Same_VideoSurface_ServicePending__invalid
    jsr Same_VideoSurface_ValidateDescriptor
    bcs Same_VideoSurface_ServicePending__invalid
    jsr Same_VideoSurface_ComputeCameraProjection
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    cmp.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    beq Same_VideoSurface_ServicePending__nochange
    sep #$20
    .a8
    jsr Same_VideoSurface_Clear
    jsr Same_VideoSurface_BlitProjection
    jsr Same_VideoSurface_PushDirtyPresent
    bcs Same_VideoSurface_ServicePending__invalid
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    lda.l SAME_VIDEO_SURFACE_CAMERA_PRESENT_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_PRESENT_COUNT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts
Same_VideoSurface_ServicePending__nochange:
    .a16
    lda.l SAME_VIDEO_SURFACE_CAMERA_NOCHANGE_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_NOCHANGE_COUNT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts
Same_VideoSurface_ServicePending__defer:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_CAMERA_DEFER_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_DEFER_COUNT
    sep #$20
    .a8
    clc
    rts
Same_VideoSurface_ServicePending__stale16:
    sep #$20
    .a8
Same_VideoSurface_ServicePending__stale:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_CAMERA_STALE_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_STALE_COUNT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts
Same_VideoSurface_ServicePending__invalid:
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_INVALID
    sta.l SAME_VIDEO_SURFACE_STATUS
    sec
    rts
