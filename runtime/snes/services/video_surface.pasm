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
; Pixel-space damage request owned by the surface service.  The public far
; restore entry receives A=(y<<8)|x and X=(height<<8)|width; these fields hold
; the clipped rectangle for the subsequent publish call.  No tile, PPU, or
; carrier coordinate is exposed to SCUMM.
SAME_VIDEO_SURFACE_DAMAGE_X           = SAME_VIDEO_SURFACE_STATE+$34
SAME_VIDEO_SURFACE_DAMAGE_Y           = SAME_VIDEO_SURFACE_STATE+$36
SAME_VIDEO_SURFACE_DAMAGE_WIDTH       = SAME_VIDEO_SURFACE_STATE+$38
SAME_VIDEO_SURFACE_DAMAGE_HEIGHT      = SAME_VIDEO_SURFACE_STATE+$3A
SAME_VIDEO_SURFACE_DAMAGE_X1          = SAME_VIDEO_SURFACE_STATE+$3C
SAME_VIDEO_SURFACE_DAMAGE_Y1          = SAME_VIDEO_SURFACE_STATE+$3E
SAME_VIDEO_SURFACE_STATE_SIZE         = $0040
; Debug-only service pipeline witness.  This is in the unused tail of the
; backend-reserved block, after the surface descriptor/state and before no
; other published service allocation.  It is not visible to SCUMM.
; Debug-only service witness in the reserved fixture diagnostic gap.  The
; carrier window is intentionally not used for observation: its physical
; mapping is backend-owned and must not be confused with the service state.
; The witness occupies only the prefix of the fixture diagnostic gap.  It ends
; at $7E5EC7; the following bytes remain outside this diagnostic block.
SAME_VIDEO_DIAG_BASE                  = $7E5E90
SAME_VIDEO_DIAG_ROOM_INSTALLS         = SAME_VIDEO_DIAG_BASE+$00
SAME_VIDEO_DIAG_INSTALL_NEXTGEN       = SAME_VIDEO_DIAG_BASE+$02
SAME_VIDEO_DIAG_COMPOSE_ENTRIES       = SAME_VIDEO_DIAG_BASE+$04
SAME_VIDEO_DIAG_COMPOSE_CANWRITE_FAIL = SAME_VIDEO_DIAG_BASE+$06
SAME_VIDEO_DIAG_COMPOSE_STATUS        = SAME_VIDEO_DIAG_BASE+$08
SAME_VIDEO_DIAG_COMPOSE_PUSH_FAIL     = SAME_VIDEO_DIAG_BASE+$09
SAME_VIDEO_DIAG_COMPOSE_EXITS         = SAME_VIDEO_DIAG_BASE+$0A
SAME_VIDEO_DIAG_PUSH_ENTRIES          = SAME_VIDEO_DIAG_BASE+$0C
SAME_VIDEO_DIAG_PUSH_EVENT_BEFORE     = SAME_VIDEO_DIAG_BASE+$0E
SAME_VIDEO_DIAG_PUSH_GENERATION       = SAME_VIDEO_DIAG_BASE+$10
SAME_VIDEO_DIAG_PUSH_FAIL_STAGE       = SAME_VIDEO_DIAG_BASE+$12
SAME_VIDEO_DIAG_PUSH_EVENT_AFTER      = SAME_VIDEO_DIAG_BASE+$13
SAME_VIDEO_DIAG_DRAIN_VIDEO            = SAME_VIDEO_DIAG_BASE+$14
SAME_VIDEO_DIAG_LAST_SERVICE           = SAME_VIDEO_DIAG_BASE+$16
SAME_VIDEO_DIAG_LAST_OPCODE            = SAME_VIDEO_DIAG_BASE+$17
SAME_VIDEO_DIAG_DIRTY_HANDLES          = SAME_VIDEO_DIAG_BASE+$18
SAME_VIDEO_DIAG_PALETTE_HANDLES        = SAME_VIDEO_DIAG_BASE+$1A
SAME_VIDEO_DIAG_PRESENT_HANDLES        = SAME_VIDEO_DIAG_BASE+$1C
SAME_VIDEO_DIAG_SERVICE_CALLS          = SAME_VIDEO_DIAG_BASE+$1E
SAME_VIDEO_DIAG_SERVICE_LAST_HEAD      = SAME_VIDEO_DIAG_BASE+$20
SAME_VIDEO_DIAG_SERVICE_LAST_TAIL      = SAME_VIDEO_DIAG_BASE+$22
SAME_VIDEO_DIAG_SERVICE_LAST_COUNT     = SAME_VIDEO_DIAG_BASE+$24
SAME_VIDEO_DIAG_KERNEL_ENTRIES         = SAME_VIDEO_DIAG_BASE+$26
SAME_VIDEO_DIAG_KERNEL_POPS            = SAME_VIDEO_DIAG_BASE+$28
SAME_VIDEO_DIAG_KERNEL_LAST_SERVICE    = SAME_VIDEO_DIAG_BASE+$2A
SAME_VIDEO_DIAG_KERNEL_LAST_OPCODE     = SAME_VIDEO_DIAG_BASE+$2B
SAME_VIDEO_DIAG_BACKEND_STEPS          = SAME_VIDEO_DIAG_BASE+$2C
SAME_VIDEO_DIAG_CONVERT_REMAIN         = SAME_VIDEO_DIAG_BASE+$2E
SAME_VIDEO_DIAG_BACKEND_STAGE          = SAME_VIDEO_DIAG_BASE+$30
SAME_VIDEO_DIAG_RESTORE_STAGE          = SAME_VIDEO_DIAG_BASE+$2F
SAME_VIDEO_DIAG_BLIT_ENTRIES           = SAME_VIDEO_DIAG_BASE+$32
SAME_VIDEO_DIAG_BLIT_FAIL_STAGE        = SAME_VIDEO_DIAG_BASE+$34
SAME_VIDEO_DIAG_BLIT_EXITS             = SAME_VIDEO_DIAG_BASE+$35
SAME_VIDEO_DIAG_BLIT_STATE              = SAME_VIDEO_DIAG_BASE+$36
SAME_VIDEO_DIAG_BLIT_LOCKED             = SAME_VIDEO_DIAG_BASE+$37
SAME_VIDEO_DIAG_BLIT_ENTRY_STATE        = SAME_VIDEO_DIAG_BASE+$38
SAME_VIDEO_DIAG_BLIT_ENTRY_LOCKED       = SAME_VIDEO_DIAG_BASE+$39
SAME_VIDEO_DIAG_WITNESS_ATTEMPTS        = SAME_VIDEO_DIAG_BASE+$3A
SAME_VIDEO_DIAG_WITNESS_SKIPS           = SAME_VIDEO_DIAG_BASE+$3C
SAME_VIDEO_DIAG_WITNESS_MOVING          = SAME_VIDEO_DIAG_BASE+$3E
SAME_VIDEO_DIAG_RENDER_ENTRIES          = SAME_VIDEO_DIAG_BASE+$40
SAME_VIDEO_DIAG_RENDER_DESIRED          = SAME_VIDEO_DIAG_BASE+$42
SAME_VIDEO_DIAG_RENDER_MOVING_ENTRIES   = SAME_VIDEO_DIAG_BASE+$44
SAME_VIDEO_SURFACE_STATUS_OK          = $01
SAME_VIDEO_SURFACE_STATUS_UNAVAILABLE = $02
SAME_VIDEO_SURFACE_STATUS_INVALID     = $03
SAME_VIDEO_SURFACE_STATUS_LOCKED      = $04
SAME_VIDEO_SURFACE_DESCRIPTOR_SIZE    = $0016
SAME_VIDEO_SURFACE_DP_SOURCE          = $00F0
SAME_VIDEO_SURFACE_DP_ROWS            = $00F3
SAME_VIDEO_SURFACE_DP_PIXEL_COUNT     = $00F6

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
; These are real wrappers rather than cross-bank aliases.  The surface facade
; is bank 20 while the selected overlay implementation is bank 23; a symbol
; alias would preserve the local address but could lose the implementation
; bank in a far call.
Same_VideoText_ShowSegment_Far:
    jsl Same_VideoOverlay_ShowTalkSegment_Far
    rtl
Same_VideoText_Hide_Far:
    jsl Same_VideoOverlay_Hide_Far
    rtl
Same_VideoText_CanWrite_Far:
    jsl Same_VideoOverlay_CanWrite_Far
    rtl
.else
Same_VideoText_ShowSegment_Far = Same_VideoSurface_NoTextService_Far
Same_VideoText_Hide_Far = Same_VideoSurface_NoTextService_Far
Same_VideoText_CanWrite_Far = Same_VideoSurface_NoTextService_Far
Same_VideoSurface_NoTextService_Far:
    sec
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
    ; Descriptor-index arithmetic below changes A. Reload the requested room
    ; before every comparison so lookup does not compare later records with
    ; their byte offsets instead of the room identity.
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_ROOM
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
    lda.l SAME_VIDEO_DIAG_PUSH_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_PUSH_ENTRIES
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_BEFORE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-2)
    bcc Same_VideoSurface_PushPresentation__space
    sep #$20
    .a8
    lda #$04
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
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
    bcs Same_VideoSurface_PushPresentation__fail_dirty
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
    bcs Same_VideoSurface_PushPresentation__fail_palette
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
    bcs Same_VideoSurface_PushPresentation__fail_present
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_AFTER
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_VIDEO_DIAG_PUSH_GENERATION
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    clc
    rts
Same_VideoSurface_PushPresentation__fail_dirty:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    bra Same_VideoSurface_PushPresentation__fail
Same_VideoSurface_PushPresentation__fail_palette:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    bra Same_VideoSurface_PushPresentation__fail
Same_VideoSurface_PushPresentation__fail_present:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
Same_VideoSurface_PushPresentation__fail:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_AFTER
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_VIDEO_DIAG_PUSH_GENERATION
    sep #$20
    .a8
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

; Restore one clipped pixel-space rectangle from the installed room visual.
; Input ABI: A=(y<<8)|x, X=(height<<8)|width, both 16-bit.  The routine
; preserves P on return, clobbers A/X/Y and carry is clear only after the
; indexed surface has been restored.  The clipped request remains in the
; DAMAGE_* fields for Same_VideoSurface_PushDamagePresent_Far.
Same_VideoSurface_RestoreRect_Far:
    php
    rep #$30
    .a16
    .i16
    ; Save the incoming packed A/X before any byte-width diagnostic update.
    ; The probe must not change the high accumulator byte seen by the service.
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_INPUT_X
    txa
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_INPUT_W
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    lda.l SAME_SCUMM_CONTROLLER_RESTORE_INPUT_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    lda.l SAME_SCUMM_CONTROLLER_RESTORE_CALLS
    inc
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_CALLS
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    rep #$30
    .a16
    .i16
    ; CanWrite is a service query and may change A.  The packed arguments are
    ; already in service-owned scratch above.
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_RestoreRect__writable
    brl Same_VideoSurface_RestoreRect__busy
Same_VideoSurface_RestoreRect__writable:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    tax
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_AFTER_A
    txa
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_AFTER_X
    lda.l SAME_SCUMM_CONTROLLER_RESTORE_AFTER_A
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    xba
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    xba
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_INPUT_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_INPUT_H
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    bne Same_VideoSurface_RestoreRect__width_ok
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__width_ok:
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    bne Same_VideoSurface_RestoreRect__height_ok
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__height_ok:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    rep #$20
    .a16
    ; Reject an entirely off-display request, then clip to the 256x224
    ; surface and the installed projection viewport.
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    cmp #$0100
    bcc Same_VideoSurface_RestoreRect__x_nonempty
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__x_nonempty:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    cmp #$00E0
    bcc Same_VideoSurface_RestoreRect__y_nonempty
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__y_nonempty:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    cmp #$0100
    bcs Same_VideoSurface_RestoreRect__x_clip
    brl Same_VideoSurface_RestoreRect__x_screen_ok
Same_VideoSurface_RestoreRect__x_clip:
    rep #$20
    .a16
    lda #$0100
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
Same_VideoSurface_RestoreRect__x_screen_ok:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    cmp #$00E0
    bcs Same_VideoSurface_RestoreRect__y_clip
    brl Same_VideoSurface_RestoreRect__y_screen_ok
Same_VideoSurface_RestoreRect__y_clip:
    rep #$20
    .a16
    lda #$00E0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
Same_VideoSurface_RestoreRect__y_screen_ok:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    cmp.l SAME_VIDEO_SURFACE_DEST_X
    bcs Same_VideoSurface_RestoreRect__x_left_ok
    lda.l SAME_VIDEO_SURFACE_DEST_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
Same_VideoSurface_RestoreRect__x_left_ok:
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    cmp.l SAME_VIDEO_SURFACE_DEST_Y
    bcs Same_VideoSurface_RestoreRect__y_top_ok
    lda.l SAME_VIDEO_SURFACE_DEST_Y
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
Same_VideoSurface_RestoreRect__y_top_ok:
    lda.l SAME_VIDEO_SURFACE_DEST_X
    clc
    adc.l SAME_VIDEO_SURFACE_COPY_WIDTH
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X1
    bcs Same_VideoSurface_RestoreRect__x_right_ok
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
Same_VideoSurface_RestoreRect__x_right_ok:
    lda.l SAME_VIDEO_SURFACE_DEST_Y
    clc
    adc.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    bcs Same_VideoSurface_RestoreRect__y_bottom_ok
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
Same_VideoSurface_RestoreRect__y_bottom_ok:
    sep #$20
    .a8
    lda #$04
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X
    bne Same_VideoSurface_RestoreRect__x_span
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__x_span:
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y
    bne Same_VideoSurface_RestoreRect__y_span
    brl Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__y_span:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_LOOP_W
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_LOOP_H
    ; LoadRowTablePointer uses byte loads and returns with A8.  RestoreRect's
    ; row arithmetic and loop counters are 16-bit, so re-establish the public
    ; caller contract before touching them.
    rep #$30
    .a16
    .i16
    jsr Same_VideoSurface_LoadRowTablePointer
    lda #$0000
    sta.l SAME_MODE3_WORK_TEMP
Same_VideoSurface_RestoreRect__row:
    lda.l SAME_MODE3_WORK_TEMP
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_LOOP_ROW
    ; Source row = source_y + (surface_y - dest_y) + row, then read its
    ; bank-safe three-byte row descriptor.
    lda.l SAME_MODE3_WORK_TEMP
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_DEST_Y
    clc
    adc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_MODE3_WORK_INDEX
    ; Room-visual row descriptors are five bytes: a three-byte bank-safe
    ; pointer followed by the two-byte source pitch.  Keep RestoreRect's
    ; lookup in the same descriptor contract as the full projection path;
    ; row*3 would read pointer bytes from later records and produce striped
    ; background during actor damage restores.
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_INDEX
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
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sec
    sbc.l SAME_VIDEO_SURFACE_DEST_X
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_LOOP_SRC
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_MODE3_WORK_TEMP
    xba
    and #$FF00
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_X
    tax
    txa
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_LOOP_DST
    ldy #$0000
    ; Copy two indexed pixels per bus transaction.  X/Y remain 16-bit and
    ; the odd-width tail is handled bytewise.  The former per-pixel write
    ; loop made a 32x64 restore monopolize the S-CPU mainline on the SA-1
    ; BW-RAM carrier; this keeps the same pixel contract while reducing the
    ; bounded restore's carrier transactions by half.
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lsr
    sta SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    beq Same_VideoSurface_RestoreRect__odd_only
Same_VideoSurface_RestoreRect__pixel:
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    dec SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    bne Same_VideoSurface_RestoreRect__pixel
Same_VideoSurface_RestoreRect__odd_only:
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    and #$01
    beq Same_VideoSurface_RestoreRect__row_done
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
Same_VideoSurface_RestoreRect__row_done:
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_TEMP
    inc
    sta.l SAME_MODE3_WORK_TEMP
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    bcs Same_VideoSurface_RestoreRect__done_rows
    brl Same_VideoSurface_RestoreRect__row
Same_VideoSurface_RestoreRect__done_rows:
    sep #$20
    .a8
    lda #$05
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    plp
    clc
    rtl
Same_VideoSurface_RestoreRect__fail:
    sep #$20
    .a8
    lda #$07
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    plp
    sec
    rtl
Same_VideoSurface_RestoreRect__busy:
    sep #$20
    .a8
    lda #$06
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    plp
    sec
    rtl

; Publish exactly the clipped rectangle prepared by RestoreRect.  A palette
; event is deliberately omitted: actor motion changes pixels, not palette.
Same_VideoSurface_PushDamagePresent_Far:
    php
    jsr Same_VideoSurface_PushDamagePresent
    bcs Same_VideoSurface_PushDamagePresent_Far__fail
    plp
    clc
    rtl
Same_VideoSurface_PushDamagePresent_Far__fail:
    plp
    sec
    rtl
Same_VideoSurface_PushDamagePresent:
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_PUSH_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_PUSH_ENTRIES
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_BEFORE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-1)
    bcc Same_VideoSurface_PushDamagePresent__capacity_ok
    brl Same_VideoSurface_PushDamagePresent__fail_capacity
Same_VideoSurface_PushDamagePresent__capacity_ok:
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SURFACE_DIRTY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushDamagePresent__fail_dirty
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
    bne Same_VideoSurface_PushDamagePresent__generation_ok
    inc
Same_VideoSurface_PushDamagePresent__generation_ok:
    sta.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsl Same_Mode3_Event_Push_Far
    bcs Same_VideoSurface_PushDamagePresent__fail_present
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_AFTER
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_VIDEO_DIAG_PUSH_GENERATION
    clc
    rts
Same_VideoSurface_PushDamagePresent__fail_capacity:
    sep #$20
    .a8
    lda #$04
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    bra Same_VideoSurface_PushDamagePresent__fail
Same_VideoSurface_PushDamagePresent__fail_dirty:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
    bra Same_VideoSurface_PushDamagePresent__fail
Same_VideoSurface_PushDamagePresent__fail_present:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_VIDEO_DIAG_PUSH_FAIL_STAGE
Same_VideoSurface_PushDamagePresent__fail:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_PUSH_EVENT_AFTER
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_VIDEO_DIAG_PUSH_GENERATION
    sep #$20
    .a8
    sec
    rts

; Compose the installed room into the indexed surface without publishing it.
; This is used when a caller must add dynamic pixels before one atomic
; presentation transaction.  The surface service still owns all room-source
; projection and clipping; the caller only decides when its completed pixels
; are ready to publish.
Same_VideoSurface_ComposeRoomOnly_Far:
    php
    pha
    sep #$20
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ComposeRoomOnly__locked
    pla
    jsr Same_VideoSurface_FindVisual
    bcs Same_VideoSurface_ComposeRoomOnly__fail
    jsr Same_VideoSurface_ValidateDescriptor
    bcs Same_VideoSurface_ComposeRoomOnly__fail
    jsr Same_VideoSurface_ComputeProjection
    sep #$20
    .a8
    jsr Same_VideoSurface_Clear
    jsr Same_VideoSurface_LoadPalette
    jsr Same_VideoSurface_BlitProjection
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_SURFACE_STATUS
    plp
    clc
    rtl
Same_VideoSurface_ComposeRoomOnly__locked:
    sep #$20
    .a8
    pla
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
Same_VideoSurface_ComposeRoomOnly__fail:
    sep #$20
    .a8
    sta.l SAME_VIDEO_SURFACE_STATUS
    plp
    sec
    rtl

; Input A=u8 room. Complete validation precedes any display mutation.
Same_VideoSurface_ComposeRoom_Far:
    php
    pha
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_COMPOSE_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_COMPOSE_ENTRIES
    sep #$20
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ComposeRoom__locked_diag
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
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_DIAG_COMPOSE_STATUS
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_COMPOSE_EXITS
    inc
    sta.l SAME_VIDEO_DIAG_COMPOSE_EXITS
    sep #$20
    .a8
    plp
    clc
    rtl
Same_VideoSurface_ComposeRoom__locked_diag:
    sep #$20
    .a8
    pla
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    sta.l SAME_VIDEO_DIAG_COMPOSE_STATUS
    lda.l SAME_VIDEO_DIAG_COMPOSE_CANWRITE_FAIL
    inc
    sta.l SAME_VIDEO_DIAG_COMPOSE_CANWRITE_FAIL
    bra Same_VideoSurface_ComposeRoom__status_fail
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
    sta.l SAME_VIDEO_DIAG_COMPOSE_STATUS
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_COMPOSE_EXITS
    inc
    sta.l SAME_VIDEO_DIAG_COMPOSE_EXITS
    sep #$20
    .a8
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

; Queue the first presentation for a newly installed room.  Room installation
; can race an in-flight presentation from the previous room; retain the
; request and retry from the normal service boundary instead of dropping it.
Same_VideoSurface_RoomInstalled_Far:
    php
    sep #$20
    .a8
    lda #$02
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_VIDEO_SURFACE_PENDING_ROOM
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION
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
    bcs Same_VideoSurface_PushDirtyPresent_Far__fail
    plp
    clc
    rtl
Same_VideoSurface_PushDirtyPresent_Far__fail:
    plp
    sec
    rtl

Same_VideoSurface_ServicePending:
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    beq Same_VideoSurface_ServicePending__none
    jmp Same_VideoSurface_ServicePending__owned
Same_VideoSurface_ServicePending__none:
    clc
    rts
Same_VideoSurface_ServicePending__owned:
    sep #$20
    .a8
    cmp #$02
    bne Same_VideoSurface_ServicePending__normal
    jmp Same_VideoSurface_ServicePending__initial
Same_VideoSurface_ServicePending__normal:
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    beq Same_VideoSurface_ServicePending__room_ok
    brl Same_VideoSurface_ServicePending__stale
Same_VideoSurface_ServicePending__room_ok:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    beq Same_VideoSurface_ServicePending__generation_ok
    brl Same_VideoSurface_ServicePending__stale16
Same_VideoSurface_ServicePending__generation_ok:
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ServicePending__defer
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    jsr Same_VideoSurface_FindVisual
    bcc Same_VideoSurface_ServicePending__visual_ok
    brl Same_VideoSurface_ServicePending__invalid
Same_VideoSurface_ServicePending__visual_ok:
    jsr Same_VideoSurface_ValidateDescriptor
    bcc Same_VideoSurface_ServicePending__descriptor_ok
    brl Same_VideoSurface_ServicePending__invalid
Same_VideoSurface_ServicePending__descriptor_ok:
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

Same_VideoSurface_ServicePending__initial:
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne Same_VideoSurface_ServicePending__stale
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM_GENERATION
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne Same_VideoSurface_ServicePending__stale16
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PENDING_ROOM
    jsl Same_VideoSurface_ComposeRoom_Far
    bcs Same_VideoSurface_ServicePending__defer
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts

; Kept in a separate service bank so adding the bounded sprite operation does
; not move or range-expand unrelated SCUMM/script control flow.  The API is
; still target-neutral: callers pass an indexed source rectangle, while this
; service owns clipping, transparency, and carrier writes.
Same_VideoSurface_BlitIndexedRect_Far:
    php
    rep #$20
    .a16
    ; Preserve the public pixel-space destination before diagnostics use A.
    ; The ABI is A=(y<<8)|x, X=(height<<8)|width, Y=source offset.
    pha
    lda.l SAME_VIDEO_DIAG_BLIT_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_BLIT_ENTRIES
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    lda.l SAME_MODE3_CONTROL_STATE
    sta.l SAME_VIDEO_DIAG_BLIT_ENTRY_STATE
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    sta.l SAME_VIDEO_DIAG_BLIT_ENTRY_LOCKED
    rep #$30
    .a16
    .i16
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    txa
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    tya
    sta.l SAME_MODE3_WORK_INDEX
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_BlitIndexedRect__writable
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    brl Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__writable:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    xba
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    xba
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    cmp #$0100
    bcc Same_VideoSurface_BlitIndexedRect__x_ok
    sep #$20
    .a8
    lda #$02
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    brl Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__x_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    cmp #$00E0
    bcc Same_VideoSurface_BlitIndexedRect__y_ok
    sep #$20
    .a8
    lda #$03
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    brl Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__y_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    bne Same_VideoSurface_BlitIndexedRect__width_ok
    sep #$20
    .a8
    lda #$04
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    brl Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__width_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    bne Same_VideoSurface_BlitIndexedRect__height_ok
    sep #$20
    .a8
    lda #$05
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    brl Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__height_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    xba
    and #$FF00
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_VIDEO_SURFACE_ROW
Same_VideoSurface_BlitIndexedRect__row:
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    lda.l SAME_MODE3_WORK_TEMP
    tax
    lda.l SAME_MODE3_WORK_INDEX
    tay
Same_VideoSurface_BlitIndexedRect__pixel:
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    beq Same_VideoSurface_BlitIndexedRect__transparent
    sta.l SAME_BWRAM_SURFACE_BASE,x
Same_VideoSurface_BlitIndexedRect__transparent:
    inx
    iny
    rep #$20
    .a16
    dec SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    bne Same_VideoSurface_BlitIndexedRect__pixel
    lda.l SAME_MODE3_WORK_INDEX
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_MODE3_WORK_INDEX
    lda.l SAME_MODE3_WORK_TEMP
    clc
    adc #$0100
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_VIDEO_SURFACE_ROW
    dec
    sta.l SAME_VIDEO_SURFACE_ROW
    bne Same_VideoSurface_BlitIndexedRect__row
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_BLIT_EXITS
    inc
    sta.l SAME_VIDEO_DIAG_BLIT_EXITS
    plp
    clc
    rtl
Same_VideoSurface_BlitIndexedRect__fail:
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_STATE
    sta.l SAME_VIDEO_DIAG_BLIT_STATE
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    sta.l SAME_VIDEO_DIAG_BLIT_LOCKED
    rep #$20
    .a16
    pla
    lda.l SAME_VIDEO_DIAG_BLIT_EXITS
    inc
    sta.l SAME_VIDEO_DIAG_BLIT_EXITS
    plp
    sec
    rtl
