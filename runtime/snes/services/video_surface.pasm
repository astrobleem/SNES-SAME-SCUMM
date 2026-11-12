; Target-neutral fixed display-surface facade for the accepted INDEX8 service.
; SCUMM calls only these routines; carrier addresses and Mode-3 state remain here.
.bank 20
.org $8000

SAME_VIDEO_SURFACE_STATE              = SAME_BWRAM_VIDEO_SURFACE_STATE
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
; Target-neutral RGB8 palette install request.  The SCUMM producer supplies a
; validated source pointer; this service alone knows the selected backend's
; palette storage and copies the fixed 256-entry palette into it.
SAME_VIDEO_SURFACE_PALETTE_SOURCE      = SAME_VIDEO_SURFACE_STATE+$40
SAME_VIDEO_SURFACE_PALETTE_DIRTY      = SAME_VIDEO_SURFACE_STATE+$43 ; u8 service-owned, until accepted PRESENT
SAME_VIDEO_SURFACE_STATE_SIZE         = SAME_BWRAM_VIDEO_SURFACE_STATE_SIZE
SAME_VIDEO_ACTOR_UNDERLAY_MAGIC       = $A8
SAME_VIDEO_ACTOR_UNDERLAY_BUILDING    = $A9 ; not a restorable journal
SAME_VIDEO_ACTOR_UNDERLAY_HEADER_SIZE = $0010
SAME_VIDEO_ACTOR_UNDERLAY_COUNT_OFF  = $0004
SAME_VIDEO_ACTOR_UNDERLAY_USED_OFF   = $0006 ; includes header
SAME_VIDEO_ACTOR_UNDERLAY_LEFT_OFF   = $0008
SAME_VIDEO_ACTOR_UNDERLAY_TOP_OFF    = $000A
SAME_VIDEO_ACTOR_UNDERLAY_RIGHT_OFF  = $000C
SAME_VIDEO_ACTOR_UNDERLAY_BOTTOM_OFF = $000E
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

; Install the target-neutral 256-entry RGB8 palette from a validated far
; memory source. Input is a 24-bit source pointer in the public surface state.
; The SCUMM producer never names Mode-3 storage or a carrier address.
Same_VideoSurface_InstallPalette_Far:
    php
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_InstallPalette_Far__writable
    plp
    sec
    rtl
Same_VideoSurface_InstallPalette_Far__writable:
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PALETTE_SOURCE
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$01
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$02
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    rep #$30
    .a16
    .i16
    ldx #$0000
    ldy #$0000
Same_VideoSurface_InstallPalette_Far__copy:
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_MODE3_LIVE_PALETTE,x
    rep #$30
    .a16
    .i16
    inx
    iny
    cpy #$0300
    bcc Same_VideoSurface_InstallPalette_Far__copy
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
    plp
    clc
    rtl

; A producer that replaces the backing surface from a buffer aliased with the
; Mode-3 tile shadow must invalidate that shadow before the next PRESENT.
; Ordinary dirty presentations (including actor damage) keep the cache valid
; and therefore convert only their marked tiles.
Same_VideoSurface_InvalidateTileCache_Far:
    php
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    sep #$20
    .a8
    lda #$00
    sta.l SAME_BWRAM_CONTROL_TILE_VALID
    .endif
    plp
    clc
    rtl
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
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
      .if SCUMM_MSU1_CAMERA_VIEWPORT
    lda.l SAME_SCUMM_VIEWPORT_STATE
    beq Same_VideoSurface_CanWrite__external_idle
    jmp Same_VideoSurface_CanWrite__no
Same_VideoSurface_CanWrite__external_idle:
    .a8
      .endif
    .endif
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_IDLE
    beq Same_VideoSurface_CanWrite__idle
    jmp Same_VideoSurface_CanWrite__no
Same_VideoSurface_CanWrite__idle:
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    beq Same_VideoSurface_CanWrite__unlocked
    jmp Same_VideoSurface_CanWrite__no
Same_VideoSurface_CanWrite__unlocked:
    ; An accepted queued PRESENT owns the backing even before kernel drain.
    ; Scan exactly COUNT live slots; stale packets outside the ring are inert.
    rep #$30
    .a16
    .i16
    phx
    phy
    cld
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY+1)
    bcs Same_VideoSurface_CanWrite__queued
    tay
    beq Same_VideoSurface_CanWrite__available
    lda.l SAME_EVENT_HEAD
    and #SAME_EVENT_MASK
    asl
    asl
    asl
    asl
    tax
Same_VideoSurface_CanWrite__scan:
    sep #$20
    .a8
    lda.l SAME_EVENT_BUFFER+SAME_PKT_SERVICE,x
    cmp #SAME_SERVICE_VIDEO
    bne Same_VideoSurface_CanWrite__next
    lda.l SAME_EVENT_BUFFER+SAME_PKT_OPCODE,x
    cmp #SAME_VIDEO_OP_PRESENT
    beq Same_VideoSurface_CanWrite__queued
Same_VideoSurface_CanWrite__next:
    rep #$20
    .a16
    txa
    clc
    adc #$0010
    and #(SAME_EVENT_CAPACITY*16-1)
    tax
    dey
    bne Same_VideoSurface_CanWrite__scan
Same_VideoSurface_CanWrite__available:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    clc
    rtl
Same_VideoSurface_CanWrite__queued:
    rep #$30
    .a16
    .i16
    ply
    plx
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
    rep #$30
    .a16
    .i16
    pha
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    sep #$20
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$30
    .a16
    .i16
    plx
    pla
    plp
    rtl

; Byte read preserves the caller's high accumulator byte and P/X/Y. These
; synchronous pixel leaves do not publish or acquire a second surface owner.
Same_VideoSurface_ReadIndexedPixel_Far:
    php
    rep #$10
    .i16
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    sep #$20
    .a8
    lda.l SAME_BWRAM_SURFACE_BASE,x
    plx
    plp
    rtl

; A16 pair at logical X. Map separately: physical x=255 must wrap its second
; byte within the same scene row, never overwrite the next row's first pixel.
Same_VideoSurface_WriteIndexedPair_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    jsl Same_VideoSurface_WriteIndexedPixel_Far
    inx
    xba
    jsl Same_VideoSurface_WriteIndexedPixel_Far
    plx
    pla
    plp
    rtl

; Fill an inclusive viewport-relative rectangle in the active INDEX8 surface.
; The SCUMM producer supplies X0/Y0/X1/Y1 and color through the synchronous
; request fields in memory.pasm. This service normalizes reversed bounds,
; clips against the current room projection, writes the indexed backing, and
; publishes only the affected rectangle through the ordinary video event
; path. Carry is set if the surface is busy or the required events cannot be
; queued; an empty clipped rectangle is a successful no-op.
Same_VideoSurface_FillIndexedRect_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_STATUS
    cmp #SAME_VIDEO_SURFACE_STATUS_OK
    beq Same_VideoSurface_FillIndexedRect__check_writable
    cmp #SAME_VIDEO_SURFACE_STATUS_LOCKED
    beq Same_VideoSurface_FillIndexedRect__check_writable
    ; No installed/valid projection is not a writable target. Leave its
    ; status intact so the SCUMM producer can distinguish unavailable data
    ; from a transient video-backend lock.
    plp
    sec
    rtl
Same_VideoSurface_FillIndexedRect__check_writable:
    rep #$30
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_FillIndexedRect__writable
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    sta.l SAME_VIDEO_SURFACE_STATUS
    brl Same_VideoSurface_FillIndexedRect__fail
Same_VideoSurface_FillIndexedRect__writable:
    .a16
    .i16
    ; Two events (DIRTY and PRESENT) must be available before mutating pixels.
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-2)
    bcc Same_VideoSurface_FillIndexedRect__events_available
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    sta.l SAME_VIDEO_SURFACE_STATUS
    brl Same_VideoSurface_FillIndexedRect__fail
Same_VideoSurface_FillIndexedRect__events_available:
    .a16
    .i16
    ; SCUMM v5 accepts reversed corners; normalize each axis independently.
    lda.l SAME_VIDEO_DRAW_RECT_X0
    cmp.l SAME_VIDEO_DRAW_RECT_X1
    bcc Same_VideoSurface_FillIndexedRect__x_ordered
    beq Same_VideoSurface_FillIndexedRect__x_ordered
    lda.l SAME_VIDEO_DRAW_RECT_X1
    pha
    lda.l SAME_VIDEO_DRAW_RECT_X0
    sta.l SAME_VIDEO_DRAW_RECT_X1
    pla
    sta.l SAME_VIDEO_DRAW_RECT_X0
Same_VideoSurface_FillIndexedRect__x_ordered:
    lda.l SAME_VIDEO_DRAW_RECT_Y0
    cmp.l SAME_VIDEO_DRAW_RECT_Y1
    bcc Same_VideoSurface_FillIndexedRect__y_ordered
    beq Same_VideoSurface_FillIndexedRect__y_ordered
    lda.l SAME_VIDEO_DRAW_RECT_Y1
    pha
    lda.l SAME_VIDEO_DRAW_RECT_Y0
    sta.l SAME_VIDEO_DRAW_RECT_Y1
    pla
    sta.l SAME_VIDEO_DRAW_RECT_Y0
Same_VideoSurface_FillIndexedRect__y_ordered:
    lda.l SAME_VIDEO_SURFACE_COPY_WIDTH
    bne Same_VideoSurface_FillIndexedRect__width_available
    brl Same_VideoSurface_FillIndexedRect__empty
Same_VideoSurface_FillIndexedRect__width_available:
    lda.l SAME_VIDEO_DRAW_RECT_X0
    cmp.l SAME_VIDEO_SURFACE_COPY_WIDTH
    bcc Same_VideoSurface_FillIndexedRect__x_origin_visible
    brl Same_VideoSurface_FillIndexedRect__empty
Same_VideoSurface_FillIndexedRect__x_origin_visible:
    lda.l SAME_VIDEO_SURFACE_COPY_WIDTH
    dec
    cmp.l SAME_VIDEO_DRAW_RECT_X1
    bcs Same_VideoSurface_FillIndexedRect__x_clipped
    sta.l SAME_VIDEO_DRAW_RECT_X1
Same_VideoSurface_FillIndexedRect__x_clipped:
    lda.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    bne Same_VideoSurface_FillIndexedRect__height_available
    brl Same_VideoSurface_FillIndexedRect__empty
Same_VideoSurface_FillIndexedRect__height_available:
    lda.l SAME_VIDEO_DRAW_RECT_Y0
    cmp.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    bcc Same_VideoSurface_FillIndexedRect__y_origin_visible
    brl Same_VideoSurface_FillIndexedRect__empty
Same_VideoSurface_FillIndexedRect__y_origin_visible:
    lda.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    dec
    cmp.l SAME_VIDEO_DRAW_RECT_Y1
    bcs Same_VideoSurface_FillIndexedRect__y_clipped
    sta.l SAME_VIDEO_DRAW_RECT_Y1
Same_VideoSurface_FillIndexedRect__y_clipped:
    ; Convert inclusive viewport corners to the service's half-open damage
    ; rectangle, adding the currently projected destination origin.
    lda.l SAME_VIDEO_SURFACE_DEST_X
    clc
    adc.l SAME_VIDEO_DRAW_RECT_X0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_SURFACE_DEST_Y
    clc
    adc.l SAME_VIDEO_DRAW_RECT_Y0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_VIDEO_DRAW_RECT_X1
    sec
    sbc.l SAME_VIDEO_DRAW_RECT_X0
    inc
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_DRAW_RECT_Y1
    sec
    sbc.l SAME_VIDEO_DRAW_RECT_Y0
    inc
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    ; Keep a duplicated INDEX8 byte for the fast paired-pixel loop. The odd
    ; final pixel is written bytewise.
    sep #$20
    .a8
    lda.l SAME_VIDEO_DRAW_RECT_COLOR
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1+$01
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_VIDEO_SURFACE_ROW
Same_VideoSurface_FillIndexedRect__row:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_ROW
    xba
    and #$FF00
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_X
    tax
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lsr
    sta.l SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    beq Same_VideoSurface_FillIndexedRect__odd
Same_VideoSurface_FillIndexedRect__pair:
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    jsl Same_VideoSurface_WriteIndexedPair_Far
    inx
    inx
    lda.l SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    dec
    sta.l SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    bne Same_VideoSurface_FillIndexedRect__pair
Same_VideoSurface_FillIndexedRect__odd:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    and #$0001
    beq Same_VideoSurface_FillIndexedRect__row_done
    sep #$20
    .a8
    lda.l SAME_VIDEO_DRAW_RECT_COLOR
    jsl Same_VideoSurface_WriteIndexedPixel_Far
    rep #$20
    .a16
Same_VideoSurface_FillIndexedRect__row_done:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_ROW
    inc
    sta.l SAME_VIDEO_SURFACE_ROW
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    bcc Same_VideoSurface_FillIndexedRect__row
    jsl Same_VideoSurface_PushDamagePresent_Far
    bcc Same_VideoSurface_FillIndexedRect__published
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    sta.l SAME_VIDEO_SURFACE_STATUS
    brl Same_VideoSurface_FillIndexedRect__fail
Same_VideoSurface_FillIndexedRect__published:
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_SURFACE_STATUS
Same_VideoSurface_FillIndexedRect__empty:
    plp
    clc
    rtl
Same_VideoSurface_FillIndexedRect__fail:
    plp
    sec
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
    ; A row ending exactly at $10000 is bank-safe: the final byte is $FFFF
    ; and the half-open end is the next bank's $8000 boundary in the packed
    ; resource layout. Reject only arithmetic that wraps past that boundary.
    bcc Same_VideoSurface_ValidateRows__row_end_ok
    bne Same_VideoSurface_ValidateRows__bad
Same_VideoSurface_ValidateRows__row_end_ok:
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
    ; Room installation must not spend one logical frame issuing a long
    ; byte-at-a-time carrier write.  The indexed surface is even-sized, so
    ; clear two pixels per iteration while preserving the caller's P/A width.
    php
    rep #$30
    .a16
    .i16
    ldx #$0000
    lda #$0000
Same_VideoSurface_Clear__loop:
    .a16
    .i16
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    cpx #SAME_BWRAM_SURFACE_SIZE
    bcc Same_VideoSurface_Clear__loop
    plp
    rts

; A complete projected room covers the entire indexed surface.  In that case
; clearing first is redundant: the bank-safe room blit writes every pixel.
; Keep the clear for clipped/partial projections, where pixels outside the
; source rectangle retain the previous room and must be removed.  This is a
; service-owned storage optimization; callers remain pixel/projection based.
Same_VideoSurface_ClearForProjection:
    ; Background rewrite supersedes saved cursor pixels even within one room
    ; generation. Invalidate before both full-cover and cleared projections.
    .if SAME_CARRIER_IS_SA1_BWRAM
    jsl Same_VideoSurface_InvalidateCursorUnderlay_Far
    .endif
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_COPY_WIDTH
    cmp #$0100
    bne Same_VideoSurface_ClearForProjection__clear
    lda.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    cmp #$00E0
    bne Same_VideoSurface_ClearForProjection__clear
    rts
Same_VideoSurface_ClearForProjection__clear:
    jsr Same_VideoSurface_Clear
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
    ; Copy pairs while A/X/Y are 16-bit.  The old byte loop changed M on
    ; every pixel, so a full 256x224 projection monopolized the mainline
    ; long enough to prevent the next logical frame from completing.  The
    ; source row is byte-addressed, but an A16 indirect load is still a
    ; bank-safe two-byte read from the same decoded row.  The odd-width tail
    ; remains an explicit byte copy for clipped projections.
    ldy #$0000
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lsr
    sta SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
Same_VideoSurface_BlitProjection__pair:
    rep #$30
    .a16
    .i16
    lda SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    cmp #$0008
    bcc Same_VideoSurface_BlitProjection__remainder
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    lda SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    sec
    sbc #$0008
    sta SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    brl Same_VideoSurface_BlitProjection__pair
Same_VideoSurface_BlitProjection__remainder:
    lda SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    beq Same_VideoSurface_BlitProjection__tail
Same_VideoSurface_BlitProjection__remainder_loop:
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    inx
    iny
    iny
    dec SAME_VIDEO_SURFACE_DP_PIXEL_COUNT
    bne Same_VideoSurface_BlitProjection__remainder_loop
Same_VideoSurface_BlitProjection__tail:
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_COPY_WIDTH
    and #$0001
    beq Same_VideoSurface_BlitProjection__row_done
    sep #$20
    .a8
    lda [SAME_VIDEO_SURFACE_DP_SOURCE],y
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$30
    .a16
    .i16
Same_VideoSurface_BlitProjection__row_done:
    lda.l SAME_VIDEO_SURFACE_ROW
    inc
    sta.l SAME_VIDEO_SURFACE_ROW
    cmp.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    bcs Same_VideoSurface_BlitProjection__done
    brl Same_VideoSurface_BlitProjection__row
Same_VideoSurface_BlitProjection__done:
    rts

Same_VideoSurface_PushPresentation:
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_PushPresentation__writable
    sec
    rts
Same_VideoSurface_PushPresentation__writable:
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
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
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

; Common dirty/damage publication preflight: reserve the entire packet group.
; A queued PRESENT is already an owner even when the backend is still idle.
Same_VideoSurface_PreflightDirtyPresent:
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_PreflightDirtyPresent__fail
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
    beq Same_VideoSurface_PreflightDirtyPresent__clean
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-2)
    bra Same_VideoSurface_PreflightDirtyPresent__result
Same_VideoSurface_PreflightDirtyPresent__clean:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-1)
Same_VideoSurface_PreflightDirtyPresent__result:
    rts ; comparison carry is the refusal result
Same_VideoSurface_PreflightDirtyPresent__fail:
    sec
    rts

; Optional palette candidate event. Dirty remains set through any queue failure.
Same_VideoSurface_PushPendingPalette:
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
    beq Same_VideoSurface_PushPendingPalette__clean
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
    rts
Same_VideoSurface_PushPendingPalette__clean:
    clc
    rts

; Palette-only producer: the live INDEX8 pixels and tile shadow are unchanged.
; Reuse the same checked queue capacity and palette/PRESENT transaction, without
; manufacturing a full-screen SURFACE_DIRTY packet. Dirty colors are retained
; on every failure, and only accepted PRESENT acknowledges publication.
Same_VideoSurface_PushPalettePresent_Far:
    php
    jsr Same_VideoSurface_PreflightDirtyPresent
    bcs Same_VideoSurface_PushPalettePresent__fail
    jsr Same_VideoSurface_PushDirtyPresent__dirty_queued
    bcs Same_VideoSurface_PushPalettePresent__fail
    plp
    clc
    rtl
Same_VideoSurface_PushPalettePresent__fail:
    plp
    sec
    rtl

; Same-room camera reprojection retains the installed RGB8 palette and emits
; full-display dirty, any installed palette, then the next generation PRESENT.
Same_VideoSurface_PushDirtyPresent:
    jsr Same_VideoSurface_PreflightDirtyPresent
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
    bcc Same_VideoSurface_PushDirtyPresent__dirty_queued
    jmp Same_VideoSurface_PushDirtyPresent__fail
Same_VideoSurface_PushDirtyPresent__dirty_queued:
    jsr Same_VideoSurface_PushPendingPalette
    bcc Same_VideoSurface_PushDirtyPresent__palette_queued
    jmp Same_VideoSurface_PushDirtyPresent__fail
Same_VideoSurface_PushDirtyPresent__palette_queued:
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
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
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
.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER && SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES && (SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D)
    ; The MSU-backed actor build has no ROM room-visual directory. Restore the
    ; exact prior actor underlay from the validated active SC5LIVE allocation
    ; instead of indexing an empty ROM table. The sparse restore seeds
    ; DAMAGE_* with the consumed journal bbox; captures add the new bounds.
    jsl Same_VideoSurface_RestoreActorUnderlay_Far
    bcc Same_VideoSurface_RestoreRect__actor_underlay_ok
    jml Same_VideoSurface_RestoreRect__fail
Same_VideoSurface_RestoreRect__actor_underlay_ok:
    sep #$20
    .a8
    lda #$05
    sta.l SAME_VIDEO_DIAG_RESTORE_STAGE
    plp
    clc
    rtl
.endif
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
    jsl Same_VideoSurface_WriteIndexedPair_Far
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
    jsl Same_VideoSurface_WriteIndexedPixel_Far
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

; RAM-only sparse underlay, exclusively in the checked active-room tail.
; Header: magic:u8, room:u8, generation:u16, count:u16, used:u16 (incl.
; header), left/top/right/bottom:u16 (half-open). Each record is dest:u16,
; count:u16, original INDEX8 pixels[count]. A8 is committed; A9 is building.
; Restore -> Begin -> Capture ALL clipped runs -> Commit -> draw ALL runs.
; C clear succeeds; C set fails. Public entries preserve P/A/X/Y/DB except C.
; Capture input A16=linear destination, X16=count 1..256, no row crossing.
; No capture/commit failure permits drawing. Begin preserves old DAMAGE_*;
; each successful capture expands it. Restore validates the entire journal
; before its first surface write, then consumes magic but retains old damage.
; Scratch remains exactly the seven existing words at $7E5E7C..$7E5E89:
; H=header offset, E=end/record base, N=remaining/new used, R=row/dest,
; C=count/right, D=surface cursor, J=journal cursor. No pose scratch is used.
.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER && SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES && (SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D)

; Exchange uses the existing journal as the pose temporary: background goes
; to INDEX8 and actor pixels replace its payload, then the second exchange
; restores the actor and captures its new background. No extra pixel buffer.
Same_VideoSurface_ExchangeActorUnderlay_Far:
    php
    rep #$20
    .a16
    pha
    sep #$20
    .a8
    lda #$01
    sta.l MODE3_R_EXCHANGE
    rep #$20
    .a16
    pla
    plp
    bra Same_VideoSurface_RestoreActorUnderlay__common
Same_VideoSurface_RestoreActorUnderlay_Far:
    php
    rep #$20
    .a16
    pha
    sep #$20
    .a8
    lda #$00
    sta.l MODE3_R_EXCHANGE
    rep #$20
    .a16
    pla
    plp
Same_VideoSurface_RestoreActorUnderlay__common:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_Underlay_Restore__located
    jmp Same_VideoSurface_Underlay_Restore__empty
Same_VideoSurface_Underlay_Restore__located:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    cmp #SAME_VIDEO_ACTOR_UNDERLAY_MAGIC
    beq Same_VideoSurface_Underlay_Restore__magic
    cmp #$AA ; exchanged pose, never a partially built ($A9) journal
    bne Same_VideoSurface_Underlay_Restore__not_committed
    lda.l MODE3_R_EXCHANGE
    bne Same_VideoSurface_Underlay_Restore__magic
Same_VideoSurface_Underlay_Restore__not_committed:
    .a8
    jmp Same_VideoSurface_Underlay_Restore__empty
Same_VideoSurface_Underlay_Restore__magic:
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_Identity
    bcc Same_VideoSurface_Underlay_Restore__identity
    jsr Same_VideoSurface_Underlay_ClearMagic
    jmp Same_VideoSurface_Underlay_Restore__empty
Same_VideoSurface_Underlay_Restore__identity:
    .a16
    jsr Same_VideoSurface_Underlay_Validate
    bcc Same_VideoSurface_Underlay_Restore__valid
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Restore__valid:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Underlay_Restore__writable
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_Underlay_Restore__writable:
    .a16
    jsr Same_VideoSurface_Underlay_ZeroDamage
    jsr Same_VideoSurface_Underlay_UnionDamage
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    txa
    clc
    adc #$0010
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
Same_VideoSurface_Underlay_Restore__record:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    bne Same_VideoSurface_Underlay_Restore__run
    sep #$20
    .a8
    lda.l MODE3_R_EXCHANGE
    beq Same_VideoSurface_Underlay_Restore__consume
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    eor #$02
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    jmp Same_VideoSurface_Underlay_Success
Same_VideoSurface_Underlay_Restore__consume:
    .a8
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_ClearMagic
    jmp Same_VideoSurface_Underlay_Success
Same_VideoSurface_Underlay_Restore__run:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    txa
    clc
    adc #$0004
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
Same_VideoSurface_Underlay_Restore__pixel:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    pha
    lda.l MODE3_R_EXCHANGE
    beq Same_VideoSurface_Underlay_Restore__plain_copy
    phx
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    tax
    sep #$20
    .a8
    jsl Same_VideoSurface_ReadIndexedPixel_Far
    plx
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
Same_VideoSurface_Underlay_Restore__plain_copy:
    .a8
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    tax
    sep #$20
    .a8
    pla
    jsl Same_VideoSurface_WriteIndexedPixel_Far
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bne Same_VideoSurface_Underlay_Restore__pixel
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    brl Same_VideoSurface_Underlay_Restore__record
Same_VideoSurface_Underlay_Restore__empty:
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_ZeroDamage
    jmp Same_VideoSurface_Underlay_Success

; Translate an exchanged pose journal by the camera delta, clipping each run
; and compacting forward in-place. All old records validate before mutation;
; writes never overtake unread payload. Empty results remain valid journals.
; Camera composition transaction on the existing surface/journals. Input is
; an accepted retained ticket and a checked strip (or retained-column cache).
; No yield occurs while journals hold exchanged pixels. Room/camera ownership
; prevents other producers from observing intermediate INDEX8 state.
; Surface camera ABI: A16 desired source X, X16 maximum source X,
; Y16 cold committed source X. Return A16 checked-column index or $FFFF,
; X16 accepted source X. The producer never sees physical tile ownership.
Same_VideoSurface_BeginScroll_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l MODE3_R_ACTIVE
    and #$00FF
    bne Same_VideoSurface_BeginScroll__initialized
    txa
    tyx
    jsl Same_Mode3_Retained_Init_Far
    bcc Same_VideoSurface_BeginScroll__initialized
    pla
    plp
    sec
    rtl
Same_VideoSurface_BeginScroll__initialized:
    .a16
    pla
    jsl Same_Mode3_Retained_Begin_Far
    bcs Same_VideoSurface_BeginScroll__failed
    pha
    lda.l MODE3_R_NEXT
    tax
    pla
    plp
    clc
    rtl
Same_VideoSurface_BeginScroll__failed:
    plp
    sec
    rtl

; Checked eight-pixel strip in the existing service source pointer.
; A16 visible height, X16 destination top, Y16 source row offset. The pointer
; must name the provider-owned prefix, never a guest address or released read.
Same_VideoSurface_CheckedScrollColumn_Far:
    php
    rep #$30
    .a16
    .i16
    sta.l MODE3_R_HEIGHT
    txa
    sta.l MODE3_R_TOP
    tya
    sta.l MODE3_R_SOURCE_Y
    lda SAME_VIDEO_SURFACE_DP_SOURCE
    sta.l MODE3_R_INPUT
    sep #$20
    .a8
    lda SAME_VIDEO_SURFACE_DP_SOURCE+2
    cmp #$40
    bne Same_VideoSurface_CheckedScrollColumn__bad
    jsl Same_Mode3_Retained_ColumnReady_Far
    bcs Same_VideoSurface_CheckedScrollColumn__bad
    plp
    clc
    rtl
Same_VideoSurface_CheckedScrollColumn__bad:
    plp
    sec
    rtl

Same_VideoSurface_RetireScroll_Far:
    jml Same_Mode3_Retained_Retire_Far
Same_VideoSurface_ColdScroll_Far:
    jml Same_Mode3_Retained_Cold_Far
Same_VideoSurface_AbortScroll_Far:
    jml Same_Mode3_Retained_Abort_Far

; Immutable publication fence: carry clear only after both generation words
; match and the service has released the surface. Preserve caller A and P.
Same_VideoSurface_ScrollPresented_Far:
    php
    rep #$20
    .a16
    pha
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    bne Same_VideoSurface_ScrollPresented__pending
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    cmp.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    bne Same_VideoSurface_ScrollPresented__pending
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION+2
    cmp.l SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI
    bne Same_VideoSurface_ScrollPresented__pending
    pla
    plp
    clc
    rtl
Same_VideoSurface_ScrollPresented__pending:
    .a16
    pla
    plp
    sec
    rtl

Same_VideoSurface_CanPublishRetained_Far:
    php
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_CanPublishRetained__wait
    jsr Same_VideoSurface_PreflightDirtyPresent
    bcs Same_VideoSurface_CanPublishRetained__wait
    plp
    clc
    rtl
Same_VideoSurface_CanPublishRetained__wait:
    plp
    sec
    rtl

; A speculative source-strip request may reuse the pending prefix only once
; the immutable current publication has finished all conversion. This returns
; A16=next missing source column, X16=origin it follows, C clear. It does not
; claim pixels or physical character slots. The latter remain owned by the
; committed map until BeginScroll proves safe reuse after the NMI commit.
Same_VideoSurface_PlanLookahead_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_VideoSurface_PlanLookahead__no
    lda.l SAME_MODE3_CONTROL_STATE
    and #$00FF
    cmp #SAME_MODE3_STATE_QUEUEING
    bcc Same_VideoSurface_PlanLookahead__no
    cmp #(SAME_MODE3_STATE_COMPLETE+1)
    bcs Same_VideoSurface_PlanLookahead__no
    lda.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    bne Same_VideoSurface_PlanLookahead__no
    lda.l MODE3_R_NEXT
    and #$0007
    bne Same_VideoSurface_PlanLookahead__no
    lda.l SAME_VIDEO_SURFACE_PENDING_XSTART
    clc
    adc #$0020
    bpl Same_VideoSurface_PlanLookahead__positive
    lda #$0000
Same_VideoSurface_PlanLookahead__positive:
    .a16
    cmp.l MODE3_R_MAX
    bcc Same_VideoSurface_PlanLookahead__bounded
    lda.l MODE3_R_MAX
Same_VideoSurface_PlanLookahead__bounded:
    .a16
    cmp.l MODE3_R_NEXT
    beq Same_VideoSurface_PlanLookahead__no
    bcc Same_VideoSurface_PlanLookahead__left
    lda.l MODE3_R_NEXT
    cmp.l MODE3_R_MAX
    bcs Same_VideoSurface_PlanLookahead__no
    tax
    lsr
    lsr
    lsr
    clc
    adc #$0020
    bra Same_VideoSurface_PlanLookahead__column
Same_VideoSurface_PlanLookahead__left:
    .a16
    lda.l MODE3_R_NEXT
    beq Same_VideoSurface_PlanLookahead__no
    tax
    lsr
    lsr
    lsr
    dec
Same_VideoSurface_PlanLookahead__column:
    .a16
    cmp.l MODE3_R_FIRST
    bcc Same_VideoSurface_PlanLookahead__yes
    cmp.l MODE3_R_LAST
    bcc Same_VideoSurface_PlanLookahead__no
    beq Same_VideoSurface_PlanLookahead__no
Same_VideoSurface_PlanLookahead__yes:
    .a16
    plp
    rep #$30
    .a16
    .i16
    clc
    rtl
Same_VideoSurface_PlanLookahead__no:
    plp
    sec
    rtl

; Match the camera publication that a source-strip ticket follows. A16 is
; the committed origin, X/Y the low/high generation words. Actor-only images
; do not invalidate this retained source identity. A camera reversal/room
; retirement is rejected; resource room/epoch validation remains the caller's.
Same_VideoSurface_LookaheadMatches_Far:
    php
    rep #$30
    .a16
    .i16
    cmp.l MODE3_R_CURRENT
    bne Same_VideoSurface_LookaheadMatches__no
    txa
    cmp.l MODE3_R_GENERATION
    bne Same_VideoSurface_LookaheadMatches__no
    tya
    cmp.l MODE3_R_GENERATION_HI
    bne Same_VideoSurface_LookaheadMatches__no
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_VideoSurface_LookaheadMatches__no
    plp
    clc
    rtl
Same_VideoSurface_LookaheadMatches__no:
    plp
    sec
    rtl

Same_VideoSurface_ComposeRetainedScroll_Far:
    php
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__writable
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__writable:
    .a8
    jsr Same_VideoSurface_PreflightDirtyPresent
    bcc Same_VideoSurface_ComposeRetainedScroll__capacity
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__capacity:
    .a8
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_ZeroDamage
    jsl Same_VideoSurface_ExchangeCursorUnderlay_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__cursor_saved
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__cursor_saved:
    .a16
    jsl Same_Mode3_Retained_FlushDamage_Far
    ; Cursor restoration has been preserved/marked. Only actor restoration
    ; may contribute to the second preservation pass; do not encode the
    ; same cursor rectangle twice when the actor is retained unchanged.
    jsr Same_VideoSurface_Underlay_ZeroDamage
    ; A fully visible world-anchored pose already occupies the correct
    ; physical ring pixels. Rebase only its restoration journal; no pixel
    ; copy, tile invalidation, or actor DMA is necessary for camera motion.
    sep #$20
    .a8
    lda #$00
    sta.l MODE3_R_KEEP_ACTOR
    rep #$20
    .a16
    jsl Same_VideoSurface_RetainActorUnderlay_Far
    bcs Same_VideoSurface_ComposeRetainedScroll__exchange_actor
    sep #$20
    .a8
    lda #$01
    sta.l MODE3_R_KEEP_ACTOR
    rep #$20
    .a16
    bra Same_VideoSurface_ComposeRetainedScroll__actor_saved
Same_VideoSurface_ComposeRetainedScroll__exchange_actor:
    .a16
    jsl Same_VideoSurface_ExchangeActorUnderlay_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__actor_saved
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__actor_saved:
    .a16
    jsl Same_Mode3_Retained_FlushDamage_Far
    rep #$20
    .a16
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    bne Same_VideoSurface_ComposeRetainedScroll__strip_ready
    jsl Same_Mode3_Retained_ReadColumn_Far
Same_VideoSurface_ComposeRetainedScroll__strip_ready:
    .a16
    jsl Same_Mode3_Retained_ShiftSurface_Far
    jsl Same_Mode3_Retained_FillEdge_Far
    lda.l MODE3_R_KEEP_ACTOR
    and #$00FF
    bne Same_VideoSurface_ComposeRetainedScroll__actor_retained
    jsl Same_VideoSurface_RebaseActorUnderlay_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__rebased
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__rebased:
    .a16
    jsl Same_VideoSurface_ExchangeActorUnderlay_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__actor_restored
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__actor_restored:
    .a16
    jsl Same_Mode3_Retained_MarkDamage_Far
Same_VideoSurface_ComposeRetainedScroll__actor_retained:
    .a16
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_ZeroDamage
    jsl Same_VideoSurface_ExchangeCursorUnderlay_Far
    bcc Same_VideoSurface_ComposeRetainedScroll__cursor_restored
    jmp Same_VideoSurface_ComposeRetainedScroll__failed
Same_VideoSurface_ComposeRetainedScroll__cursor_restored:
    .a16
    jsl Same_Mode3_Retained_MarkDamage_Far
    ; Existing publication tail, without manufacturing full-screen damage.
    jsr Same_VideoSurface_PushDirtyPresent__dirty_queued
    bcs Same_VideoSurface_ComposeRetainedScroll__failed
    plp
    clc
    rtl
Same_VideoSurface_ComposeRetainedScroll__failed:
    plp
    sec
    rtl

; Retain a committed world-anchored pose in the circular INDEX8/VRAM
; mapping. C clear means no exchange is needed; C set selects the existing
; clipping/exchange path. Validate the whole journal and translated bounds
; BEFORE changing any descriptor. Payload, physical pixels and identity stay
; untouched. A pose intersecting the exposed edge must use exchange so its
; retired character slots contain background, never stale actor pixels.
Same_VideoSurface_RetainActorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_RetainActor__located
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__located:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    and #$00FF
    cmp #SAME_VIDEO_ACTOR_UNDERLAY_MAGIC
    beq Same_VideoSurface_RetainActor__committed
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__committed:
    .a16
    jsr Same_VideoSurface_Underlay_Identity
    bcc Same_VideoSurface_RetainActor__identity
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__identity:
    .a16
    jsr Same_VideoSurface_Underlay_Validate
    bcc Same_VideoSurface_RetainActor__validated
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__validated:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_RetainActor__writable
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__writable:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    bne Same_VideoSurface_RetainActor__nonempty
    jmp Same_VideoSurface_Underlay_Success
Same_VideoSurface_RetainActor__nonempty:
    .a16
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    cmp #$00C0
    bcc Same_VideoSurface_RetainActor__scene
    jmp Same_VideoSurface_Underlay_Success ; fixed HUD journal
Same_VideoSurface_RetainActor__scene:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    cmp #$00C1
    bcc Same_VideoSurface_RetainActor__bounds
    jmp Same_VideoSurface_Underlay_Failure ; mixed scene/HUD needs clipping
Same_VideoSurface_RetainActor__bounds:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    sec
    sbc.l MODE3_R_DELTA
    cmp #$0100
    bcc Same_VideoSurface_RetainActor__left
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__left:
    .a16
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    sec
    sbc.l MODE3_R_DELTA
    cmp #$0101
    bcc Same_VideoSurface_RetainActor__ready
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RetainActor__ready:
    .a16
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    txa
    clc
    adc #$0010
    tax
Same_VideoSurface_RetainActor__record:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    sec
    sbc.l MODE3_R_DELTA
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    txa
    clc
    adc #$0004
    clc
    adc.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    tax
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    bne Same_VideoSurface_RetainActor__record
    jmp Same_VideoSurface_Underlay_Success

Same_VideoSurface_RebaseActorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_RebaseActor__located
    jmp Same_VideoSurface_Underlay_Success
Same_VideoSurface_RebaseActor__located:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    cmp #$AA
    beq Same_VideoSurface_RebaseActor__exchanged
    jmp Same_VideoSurface_Underlay_Success
Same_VideoSurface_RebaseActor__exchanged:
    .a8
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_Identity
    bcc Same_VideoSurface_RebaseActor__identity
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_RebaseActor__identity:
    .a16
    jsr Same_VideoSurface_Underlay_Validate
    bcc Same_VideoSurface_RebaseActor__validated
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_RebaseActor__validated:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_RebaseActor__writable
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_RebaseActor__writable:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    lda #$0000
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    txa
    clc
    adc #$0010
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
Same_VideoSurface_RebaseActor__record:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    bne Same_VideoSurface_RebaseActor__read
    jmp Same_VideoSurface_RebaseActor__finish
Same_VideoSurface_RebaseActor__read:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    txa
    clc
    adc #$0004
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE ; next old record
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    cmp #$C000
    bcc Same_VideoSurface_RebaseActor__scene
    jmp Same_VideoSurface_RebaseActor__emit
Same_VideoSurface_RebaseActor__scene:
    .a16
    and #$00FF
    sec
    sbc.l MODE3_R_DELTA
    bpl Same_VideoSurface_RebaseActor__left_ok
    eor #$FFFF
    inc
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bcc Same_VideoSurface_RebaseActor__left_clip
    jmp Same_VideoSurface_RebaseActor__next
Same_VideoSurface_RebaseActor__left_clip:
    .a16
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    lda #$0000
Same_VideoSurface_RebaseActor__left_ok:
    .a16
    cmp #$0100
    bcc Same_VideoSurface_RebaseActor__right
    jmp Same_VideoSurface_RebaseActor__next
Same_VideoSurface_RebaseActor__right:
    .a16
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda #$0100
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_X
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bcs Same_VideoSurface_RebaseActor__right_ok
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
Same_VideoSurface_RebaseActor__right_ok:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    and #$FF00
    ora.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
Same_VideoSurface_RebaseActor__emit:
    .a16
    jsr Same_VideoSurface_Underlay_ExpandHeader
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    inc
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    tax
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    txa
    clc
    adc #$0004
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
Same_VideoSurface_RebaseActor__byte:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    pha
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    tax
    sep #$20
    .a8
    pla
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bne Same_VideoSurface_RebaseActor__byte
Same_VideoSurface_RebaseActor__next:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    jmp Same_VideoSurface_RebaseActor__record
Same_VideoSurface_RebaseActor__finish:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    sec
    sbc.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    pha
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    pla
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    jsr Same_VideoSurface_Underlay_ZeroDamage
    jsr Same_VideoSurface_Underlay_UnionDamage
    jmp Same_VideoSurface_Underlay_Success

Same_VideoSurface_BeginActorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_Underlay_Begin__located
    jmp Same_VideoSurface_Underlay_Error
Same_VideoSurface_Underlay_Begin__located:
    .a16
    jsr Same_VideoSurface_Underlay_ClearMagic
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Underlay_Begin__writable
    jmp Same_VideoSurface_Underlay_Failure
Same_VideoSurface_Underlay_Begin__writable:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda #$0000
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    lda #$0010
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$01,x
    lda #SAME_VIDEO_ACTOR_UNDERLAY_BUILDING
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    jmp Same_VideoSurface_Underlay_Success

Same_VideoSurface_CaptureActorRun_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    txa
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_Underlay_Capture__located
    jmp Same_VideoSurface_Underlay_Error
Same_VideoSurface_Underlay_Capture__located:
    .a16
    jsr Same_VideoSurface_Underlay_IsBuilding
    bcc Same_VideoSurface_Underlay_Capture__building
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__building:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Underlay_Capture__writable
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__writable:
    .a16
    jsr Same_VideoSurface_Underlay_CheckRun
    bcc Same_VideoSurface_Underlay_Capture__run_valid
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__run_valid:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    cmp #$FFFF
    bne Same_VideoSurface_Underlay_Capture__count_ok
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__count_ok:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    cmp #$0010
    bcs Same_VideoSurface_Underlay_Capture__used_min
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__used_min:
    .a16
    clc
    adc #$0004
    bcc Same_VideoSurface_Underlay_Capture__add_header
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__add_header:
    .a16
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bcc Same_VideoSurface_Underlay_Capture__add_count
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__add_count:
    .a16
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    bcc Same_VideoSurface_Underlay_Capture__add_base
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__add_base:
    .a16
    cmp #(SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE+1)
    bcc Same_VideoSurface_Underlay_Capture__capacity
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Capture__capacity:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    tax
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    txa
    clc
    adc #$0004
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
Same_VideoSurface_Underlay_Capture__pixel:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    tax
    sep #$20
    .a8
    jsl Same_VideoSurface_ReadIndexedPixel_Far
    pha
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    sep #$20
    .a8
    pla
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    rep #$20
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    inc
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bne Same_VideoSurface_Underlay_Capture__pixel
    ; Recover original run length; C was the bounded copy counter.
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    jsr Same_VideoSurface_Underlay_ExpandHeader
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    inc
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    jsr Same_VideoSurface_Underlay_UnionDamage
    jmp Same_VideoSurface_Underlay_Success

Same_VideoSurface_CommitActorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcc Same_VideoSurface_Underlay_Commit__located
    jmp Same_VideoSurface_Underlay_Error
Same_VideoSurface_Underlay_Commit__located:
    .a16
    jsr Same_VideoSurface_Underlay_IsBuilding
    bcc Same_VideoSurface_Underlay_Commit__building
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Commit__building:
    .a16
    jsr Same_VideoSurface_Underlay_Validate
    bcc Same_VideoSurface_Underlay_Commit__valid
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Commit__valid:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Underlay_Commit__writable
    jmp Same_VideoSurface_Underlay_Reject
Same_VideoSurface_Underlay_Commit__writable:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    ; Count/used/bounds/identity are complete and validated before publication.
    sep #$20
    .a8
    lda #SAME_VIDEO_ACTOR_UNDERLAY_MAGIC
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    jmp Same_VideoSurface_Underlay_Success

Same_VideoSurface_InvalidateActorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsr Same_VideoSurface_Underlay_Locate
    bcs Same_VideoSurface_Underlay_Invalidate__done
    jsr Same_VideoSurface_Underlay_ClearMagic
Same_VideoSurface_Underlay_Invalidate__done:
    rep #$30
    .a16
    .i16
    plb
    ply
    plx
    pla
    plp
    rtl

; Internal helpers enter/return A16/X16 except the common far epilogues.
; Locate returns X=H only after proving the complete header is in the tail.
Same_VideoSurface_Underlay_Locate:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_CONTROL+$01
    and #$00FF
    cmp #$0001
    bne Same_VideoSurface_Underlay_Locate__bad
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$30
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bcc Same_VideoSurface_Underlay_Locate__bad
    cmp #(SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE-$0010+1)
    bcs Same_VideoSurface_Underlay_Locate__bad
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    clc
    rts
Same_VideoSurface_Underlay_Locate__bad:
    .a16
    sec
    rts

Same_VideoSurface_Underlay_ClearMagic:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    rep #$20
    .a16
    rts

Same_VideoSurface_Underlay_IsBuilding:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    and #$00FF
    cmp #SAME_VIDEO_ACTOR_UNDERLAY_BUILDING
    bne Same_VideoSurface_Underlay_Identity__bad
Same_VideoSurface_Underlay_Identity:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$01,x
    and #$00FF
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    lda.l SAME_VIDEO_SURFACE_ROOM
    and #$00FF
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_SURFACE_CURSOR
    bne Same_VideoSurface_Underlay_Identity__bad
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne Same_VideoSurface_Underlay_Identity__bad
    clc
    rts
Same_VideoSurface_Underlay_Identity__bad:
    .a16
    sec
    rts

; R=destination, C=count. Never accepts a zero count or wraps across a row.
Same_VideoSurface_Underlay_CheckRun:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    beq Same_VideoSurface_Underlay_CheckRun__bad
    cmp #$0101
    bcs Same_VideoSurface_Underlay_CheckRun__bad
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    cmp #$E000
    bcs Same_VideoSurface_Underlay_CheckRun__bad
    and #$00FF
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    cmp #$0101
    bcs Same_VideoSurface_Underlay_CheckRun__bad
    clc
    rts
Same_VideoSurface_Underlay_CheckRun__bad:
    .a16
    sec
    rts

; Two-pass restoration uses this read-only validator before touching pixels.
; Every record must fit used, every run must fit the surface and declared
; half-open bbox, and the last record must end EXACTLY at header+used.
Same_VideoSurface_Underlay_Validate:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    cmp #$0010
    bcs Same_VideoSurface_Underlay_Validate__min
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__min:
    .a16
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    bcc Same_VideoSurface_Underlay_Validate__sum
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__sum:
    .a16
    cmp #(SAME_SCUMM_LIVE_ROOM_ACTIVE_SIZE+1)
    bcc Same_VideoSurface_Underlay_Validate__capacity
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__capacity:
    .a16
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    bne Same_VideoSurface_Underlay_Validate__nonempty
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    ora.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    ora.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    ora.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    beq Same_VideoSurface_Underlay_Validate__empty_bounds
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__empty_bounds:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$06,x
    cmp #$0010
    beq Same_VideoSurface_Underlay_Validate__empty_ok
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__empty_ok:
    .a16
    clc
    rts
Same_VideoSurface_Underlay_Validate__nonempty:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    cmp #$0101
    bcc Same_VideoSurface_Underlay_Validate__right
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__right:
    .a16
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    bne Same_VideoSurface_Underlay_Validate__width
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__width:
    .a16
    bcs Same_VideoSurface_Underlay_Validate__left
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__left:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    cmp #$00E1
    bcc Same_VideoSurface_Underlay_Validate__bottom
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__bottom:
    .a16
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    bne Same_VideoSurface_Underlay_Validate__height
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__height:
    .a16
    bcs Same_VideoSurface_Underlay_Validate__top
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__top:
    .a16
    txa
    clc
    adc #$0010
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
Same_VideoSurface_Underlay_Validate__record:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    bne Same_VideoSurface_Underlay_Validate__next
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    beq Same_VideoSurface_Underlay_Validate__done
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__done:
    .a16
    clc
    rts
Same_VideoSurface_Underlay_Validate__next:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    clc
    adc #$0004
    bcc Same_VideoSurface_Underlay_Validate__descriptor_sum
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__descriptor_sum:
    .a16
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    bcc Same_VideoSurface_Underlay_Validate__descriptor_ok
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__descriptor_ok:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$02,x
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    jsr Same_VideoSurface_Underlay_CheckRun
    bcc Same_VideoSurface_Underlay_Validate__run_ok
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__run_ok:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    clc
    adc #$0004
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    bcc Same_VideoSurface_Underlay_Validate__payload_sum
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__payload_sum:
    .a16
    cmp.l SAME_VIDEO_ACTOR_UNDERLAY_DATA_BASE
    bcc Same_VideoSurface_Underlay_Validate__payload_ok
    beq Same_VideoSurface_Underlay_Validate__payload_ok
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__payload_ok:
    .a16
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_CURSOR
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    and #$00FF
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    bcs Same_VideoSurface_Underlay_Validate__run_left
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__run_left:
    .a16
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    bcc Same_VideoSurface_Underlay_Validate__run_right
    beq Same_VideoSurface_Underlay_Validate__run_right
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__run_right:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    xba
    and #$00FF
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    bcs Same_VideoSurface_Underlay_Validate__run_top
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__run_top:
    .a16
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    bcc Same_VideoSurface_Underlay_Validate__run_bottom
    jmp Same_VideoSurface_Underlay_Validate__bad
Same_VideoSurface_Underlay_Validate__run_bottom:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    dec
    sta.l SAME_VIDEO_ACTOR_UNDERLAY_AREA
    jmp Same_VideoSurface_Underlay_Validate__record
Same_VideoSurface_Underlay_Validate__bad:
    .a16
    sec
    rts

; Expand the building header by the original run R,C. N (new used) survives.
Same_VideoSurface_Underlay_ExpandHeader:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    bne Same_VideoSurface_Underlay_ExpandHeader__existing
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    and #$00FF
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    xba
    and #$00FF
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    inc
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    rts
Same_VideoSurface_Underlay_ExpandHeader__existing:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    and #$00FF
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    bcs Same_VideoSurface_Underlay_ExpandHeader__left
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
Same_VideoSurface_Underlay_ExpandHeader__left:
    .a16
    clc
    adc.l SAME_VIDEO_ACTOR_UNDERLAY_COLUMN
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    bcc Same_VideoSurface_Underlay_ExpandHeader__right
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
Same_VideoSurface_Underlay_ExpandHeader__right:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_ROW
    xba
    and #$00FF
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    bcs Same_VideoSurface_Underlay_ExpandHeader__top
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
Same_VideoSurface_Underlay_ExpandHeader__top:
    .a16
    inc
    cmp.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    bcc Same_VideoSurface_Underlay_ExpandHeader__bottom
    sta.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
Same_VideoSurface_Underlay_ExpandHeader__bottom:
    .a16
    rts

Same_VideoSurface_Underlay_ZeroDamage:
    .a16
    lda #$0000
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    rts

; Header bbox union with old damage. Width/height remain WORDS (256 allowed).
Same_VideoSurface_Underlay_UnionDamage:
    .a16
    lda.l SAME_VIDEO_ACTOR_UNDERLAY_RECORD_LENGTH
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$04,x
    bne Same_VideoSurface_Underlay_UnionDamage__nonempty
    rts
Same_VideoSurface_Underlay_UnionDamage__nonempty:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    beq Same_VideoSurface_Underlay_UnionDamage__seed
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    beq Same_VideoSurface_Underlay_UnionDamage__seed
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X
    bcs Same_VideoSurface_Underlay_UnionDamage__left
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
Same_VideoSurface_Underlay_UnionDamage__left:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y
    bcs Same_VideoSurface_Underlay_UnionDamage__top
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
Same_VideoSurface_Underlay_UnionDamage__top:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X1
    bcc Same_VideoSurface_Underlay_UnionDamage__right
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
Same_VideoSurface_Underlay_UnionDamage__right:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    bcc Same_VideoSurface_Underlay_UnionDamage__sizes
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    bra Same_VideoSurface_Underlay_UnionDamage__sizes
Same_VideoSurface_Underlay_UnionDamage__seed:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$08,x
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0A,x
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0C,x
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X1
    lda.l SAME_SCUMM_LIVE_ROOM_STAGING_BASE+$0E,x
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y1
Same_VideoSurface_Underlay_UnionDamage__sizes:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X1
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y1
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    rts

Same_VideoSurface_Underlay_Reject:
    rep #$20
    .a16
    jsr Same_VideoSurface_Underlay_ClearMagic
Same_VideoSurface_Underlay_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
Same_VideoSurface_Underlay_Failure:
    rep #$30
    .a16
    .i16
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
Same_VideoSurface_Underlay_Success:
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
.endif

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
    jsr Same_VideoSurface_PreflightDirtyPresent
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
    bcc Same_VideoSurface_PushDamagePresent__dirty_queued
    jmp Same_VideoSurface_PushDamagePresent__fail_dirty
Same_VideoSurface_PushDamagePresent__dirty_queued:
    jsr Same_VideoSurface_PushPendingPalette
    bcc Same_VideoSurface_PushDamagePresent__palette_queued
    jmp Same_VideoSurface_PushDamagePresent__fail_dirty
Same_VideoSurface_PushDamagePresent__palette_queued:
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
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
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
    jsr Same_VideoSurface_ClearForProjection
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
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    ; In live-room mode pixels/palette have already been CRC-validated and
    ; installed into the existing shared surface. Never consult the ROM
    ; visual directory as a fallback.
    pla
    sta.l SAME_VIDEO_SURFACE_ROOM
    ; The incoming-transfer valid bit is cleared as soon as the next room
    ; request starts. Presentation consumes the separately-lived active
    ; visual, which remains valid until a newly checked image is published.
    lda.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID
    cmp #$01
    bne Same_VideoSurface_ComposeRoom__invalid
    jsr Same_VideoSurface_PushPresentation
    bcs Same_VideoSurface_ComposeRoom__invalid
    bra Same_VideoSurface_ComposeRoom__presented
.endif
    pla
    jsr Same_VideoSurface_FindVisual
    bcs Same_VideoSurface_ComposeRoom__missing
    jsr Same_VideoSurface_ValidateDescriptor
    bcs Same_VideoSurface_ComposeRoom__invalid
    jsr Same_VideoSurface_ComputeProjection
    sep #$20
    .a8
    jsr Same_VideoSurface_ClearForProjection
    jsr Same_VideoSurface_LoadPalette
    jsr Same_VideoSurface_BlitProjection
    sep #$20
    .a8
    jsr Same_VideoSurface_PushPresentation
    bcs Same_VideoSurface_ComposeRoom__invalid
Same_VideoSurface_ComposeRoom__presented:
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
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
      .if SCUMM_MSU1_CAMERA_VIEWPORT
    jsl ScummV5_Camera_ServicePending_Far
    rts
      .endif
    .endif
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_ServicePending__defer
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    ; The live-resource room is already a checked, installed indexed surface.
    ; A deferred camera notification must never re-enter the ROM visual
    ; directory (which is deliberately not authoritative in this build).
    ; Reproject only from the active surface and publish only when the
    ; computed source window actually changes.
    jsr Same_VideoSurface_ComputeCameraProjection
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    cmp.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    beq Same_VideoSurface_ServicePending__live_nochange
    sep #$20
    .a8
    jsr Same_VideoSurface_ClearForProjection
    jsr Same_VideoSurface_BlitProjection
    jsr Same_VideoSurface_PushDirtyPresent
    bcs Same_VideoSurface_ServicePending__live_defer
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_PRESENTED_SOURCE_X
    lda.l SAME_VIDEO_SURFACE_CAMERA_PRESENT_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_PRESENT_COUNT
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_SURFACE_STATUS
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts
Same_VideoSurface_ServicePending__live_nochange:
    .a16
    lda.l SAME_VIDEO_SURFACE_CAMERA_NOCHANGE_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_NOCHANGE_COUNT
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_OK
    sta.l SAME_VIDEO_SURFACE_STATUS
    lda #$00
    sta.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    clc
    rts
Same_VideoSurface_ServicePending__live_defer:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_CAMERA_DEFER_COUNT
    inc
    sta.l SAME_VIDEO_SURFACE_CAMERA_DEFER_COUNT
    sep #$20
    .a8
    lda #SAME_VIDEO_SURFACE_STATUS_LOCKED
    sta.l SAME_VIDEO_SURFACE_STATUS
    clc
    rts
.else
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
    jsr Same_VideoSurface_ClearForProjection
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
.endif

; Shared exits stay outside the live/static conditional so either assembled
; personality can validate room ownership and defer a locked presentation.
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
    ; ASTRA_BOUND_CHECK_V1: destination must be wholly inside INDEX8.
    ; The legacy packed ABI has unsigned x/y. New callers preclip signed
    ; positions; this guard rejects overflow instead of writing outside it.
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    cmp #$0101
    bcc Same_VideoSurface_BlitIndexedRect__right_bound_ok
    sep #$20
    .a8
    lda #$06
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    jmp Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__right_bound_ok:
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    cmp #$00E1
    bcc Same_VideoSurface_BlitIndexedRect__bottom_bound_ok
    sep #$20
    .a8
    lda #$07
    sta.l SAME_VIDEO_DIAG_BLIT_FAIL_STAGE
    jmp Same_VideoSurface_BlitIndexedRect__fail
Same_VideoSurface_BlitIndexedRect__bottom_bound_ok:
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
    jsl Same_VideoSurface_WriteIndexedPixel_Far
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
    ; Packed A was already popped before CanWrite; only saved P remains.
    lda.l SAME_VIDEO_DIAG_BLIT_EXITS
    inc
    sta.l SAME_VIDEO_DIAG_BLIT_EXITS
    plp
    sec
    rtl

; Single opaque INDEX8 run primitive for checked costume chunks. The caller
; clips signed coordinates and palette-maps source slots before calling it.
.include "opaque_run.inc.pasm"

; Independent dense cursor journal; no controller/resource policy in service.
.if SAME_VIDEO_SURFACE_AVAILABLE && SAME_CARRIER_IS_SA1_BWRAM
.include "cursor_underlay.inc.pasm"
.endif
