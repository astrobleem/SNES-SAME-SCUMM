; Generic v5 built-in cursor, composed LAST into the existing INDEX8 surface.
; The cursor hotspot is projected from logical room coordinates; its 16x16 UI
; mask remains screen-sized. No actor/room-resource buffer is borrowed.
; A separate service journal restores pixels including any actor underneath.
SAME_SCUMM_CURSOR_VALID = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$00
SAME_SCUMM_CURSOR_X = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$02
SAME_SCUMM_CURSOR_Y = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$04
SAME_SCUMM_CURSOR_ID = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$06
SAME_SCUMM_CURSOR_COLOR = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$08
SAME_SCUMM_CURSOR_VISIBLE = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$0A
SAME_SCUMM_CURSOR_GENERATION = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$0C
SAME_SCUMM_CURSOR_PENDING = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$0E
SAME_SCUMM_CURSOR_LEFT = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$10
SAME_SCUMM_CURSOR_TOP = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$12
SAME_SCUMM_CURSOR_WIDTH = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$14
SAME_SCUMM_CURSOR_HEIGHT = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$16
SAME_SCUMM_CURSOR_CLIP_X = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$18
SAME_SCUMM_CURSOR_CLIP_Y = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$1A
SAME_SCUMM_CURSOR_MASK = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$1C
SAME_SCUMM_CURSOR_ROW = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$1E
SAME_SCUMM_CURSOR_COLUMN = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$20
SAME_SCUMM_CURSOR_SOURCE_X = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$22
SAME_SCUMM_CURSOR_SOURCE_Y = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$24
SAME_SCUMM_CURSOR_TABLE = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$26
SAME_SCUMM_CURSOR_XCOUNT = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$28
SAME_SCUMM_CURSOR_YCOUNT = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$2A
SAME_SCUMM_CURSOR_XBASE = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$2C
SAME_SCUMM_CURSOR_YBASE = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$2E
SAME_SCUMM_CURSOR_ORIGIN_X = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$30
SAME_SCUMM_CURSOR_ORIGIN_Y = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$32
SAME_SCUMM_CURSOR_DESIRED_COLOR = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$34
SAME_SCUMM_CURSOR_DESIRED_VISIBLE = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$36
SAME_SCUMM_CURSOR_COMPOSING = SAME_SCUMM_CURSOR_PRESENTATION_BASE+$38

; Reset only on engine/room visual lifetime reset, not on animation ticks.
ScummV5_Cursor_Reset_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    ldx #$0000
    lda #$0000
ScummV5_Cursor_Reset__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_CURSOR_PRESENTATION_BASE,x
    inx
    inx
    cpx #$0040
    bcc ScummV5_Cursor_Reset__loop
    jsl Same_VideoSurface_InvalidateCursorUnderlay_Far
    plx
    pla
    plp
    rtl

; Cursor-only pass. Actor composition calls Draw itself before its PRESENT.
; A failed queue submission retries publication without recapturing painted
; cursor pixels. Busy surface ownership always wins.
ScummV5_Cursor_Frame_Far:
    php
    cld
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_ERROR
    and #$00FF
    beq ScummV5_Cursor_Frame__no_error
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__no_error:
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    and #$00FF
    beq ScummV5_Cursor_Frame__actor_complete
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__actor_complete:
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_ROOM_READY
    and #$00FF
    bne ScummV5_Cursor_Frame__room
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__room:
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Cursor_Frame__writable
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__writable:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_PENDING
    beq ScummV5_Cursor_Frame__check
    jml ScummV5_Cursor_Frame__publish
ScummV5_Cursor_Frame__check:
    .a16
    .i16
    jsl ScummV5_Cursor_Desired_Far
    lda.l SAME_SCUMM_CURSOR_VALID
    beq ScummV5_Cursor_Frame__changed
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_SCUMM_CURSOR_GENERATION
    bne ScummV5_Cursor_Frame__changed
    lda.l SAME_SCUMM_CURSOR_DESIRED_VISIBLE
    cmp.l SAME_SCUMM_CURSOR_VISIBLE
    bne ScummV5_Cursor_Frame__changed
    cmp #$0000
    bne ScummV5_Cursor_Frame__visible
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__visible:
    .a16
    .i16
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    and #$00FF
    cmp #SAME_VIDEO_CURSOR_MAGIC
    bne ScummV5_Cursor_Frame__changed
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    cmp.l SAME_SCUMM_CURSOR_X
    bne ScummV5_Cursor_Frame__changed
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    cmp.l SAME_SCUMM_CURSOR_Y
    bne ScummV5_Cursor_Frame__changed
    lda.l SAME_SCUMM_C7_CURSOR_ID
    and #$00FF
    cmp.l SAME_SCUMM_CURSOR_ID
    bne ScummV5_Cursor_Frame__changed
    lda.l SAME_SCUMM_CURSOR_DESIRED_COLOR
    cmp.l SAME_SCUMM_CURSOR_COLOR
    bne ScummV5_Cursor_Frame__changed
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__changed:
    .a16
    .i16
    lda #$0001
    sta.l SAME_SCUMM_CURSOR_COMPOSING
    lda #$0000
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    jsl Same_VideoSurface_RestoreCursorUnderlay_Far
    bcc ScummV5_Cursor_Frame__restored
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__restored:
    .a16
    .i16
    ; A previous failed capture may already have consumed the old journal.
    ; Retained bounds still belong to this unpresented restoration.
    jsl Same_VideoSurface_MergeCursorDamage_Far
    bcc ScummV5_Cursor_Frame__merged
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__merged:
    .a16
    .i16
    jsl ScummV5_Cursor_Draw_Far
    bcc ScummV5_Cursor_Frame__publish
    jml ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__publish:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    beq ScummV5_Cursor_Frame__published
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    beq ScummV5_Cursor_Frame__published
    jsl Same_VideoSurface_PushDamagePresent_Far
    bcc ScummV5_Cursor_Frame__published
    lda #$0001
    sta.l SAME_SCUMM_CURSOR_PENDING
    bra ScummV5_Cursor_Frame__done
ScummV5_Cursor_Frame__published:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_CURSOR_PENDING
    sta.l SAME_SCUMM_CURSOR_COMPOSING
ScummV5_Cursor_Frame__done:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

; Called with A/X/Y16 by the compositor; preserves registers and P.
ScummV5_Cursor_Desired_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    lda #$0000
    sta.l SAME_SCUMM_CURSOR_DESIRED_VISIBLE
    lda.l SAME_SCUMM_C7_CURSOR_STATE
    beq ScummV5_Cursor_Desired__color
    bmi ScummV5_Cursor_Desired__color
    lda #$0001
    sta.l SAME_SCUMM_CURSOR_DESIRED_VISIBLE
ScummV5_Cursor_Desired__color:
    .a16
    .i16
    ; v5 advances the color phase on every second cursor animation tick.
    lda.l SAME_SCUMM_FRAME_COUNT
    lsr
    and #$0003
    tax
    lda.l ScummV5_Cursor_Colors,x
    and #$00FF
    sta.l SAME_SCUMM_CURSOR_DESIRED_COLOR
    plx
    pla
    plp
    rtl

; Draw a completed built-in cursor. Caller has already restored its old
; journal. Capture bounds and all backing pixels BEFORE writing any mask bit.
ScummV5_Cursor_Draw_Far:
    php
    cld
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda #$0001
    sta.l SAME_SCUMM_CURSOR_COMPOSING
    jsl ScummV5_Cursor_Desired_Far
    lda.l SAME_SCUMM_CURSOR_DESIRED_VISIBLE
    bne ScummV5_Cursor_Draw__visible
    jml ScummV5_Cursor_Draw__commit
ScummV5_Cursor_Draw__visible:
    .a16
    .i16
    lda.l SAME_SCUMM_C7_CURSOR_ID
    and #$00FF
    cmp #$0004
    bcc ScummV5_Cursor_Draw__id_ok
    jml ScummV5_Cursor_Draw__invalid
ScummV5_Cursor_Draw__id_ok:
    .a16
    .i16
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_CURSOR_TABLE
    jsl ScummV5_Cursor_Project_Far
    bcc ScummV5_Cursor_Draw__projected
    jml ScummV5_Cursor_Draw__invalid
ScummV5_Cursor_Draw__projected:
    .a16
    .i16
    ; Hotspot is a screen-pixel displacement; source input remains unchanged.
    lda.l SAME_SCUMM_C7_CURSOR_ID
    and #$00FF
    asl
    tax
    lda.l ScummV5_Cursor_Hotspots,x
    and #$00FF
    sta.l SAME_SCUMM_CURSOR_SOURCE_X
    inx
    lda.l ScummV5_Cursor_Hotspots,x
    and #$00FF
    sta.l SAME_SCUMM_CURSOR_SOURCE_Y
    lda.l SAME_SCUMM_CURSOR_LEFT
    sec
    sbc.l SAME_SCUMM_CURSOR_SOURCE_X
    sta.l SAME_SCUMM_CURSOR_LEFT
    lda.l SAME_SCUMM_CURSOR_TOP
    sec
    sbc.l SAME_SCUMM_CURSOR_SOURCE_Y
    sta.l SAME_SCUMM_CURSOR_TOP
    lda.l SAME_SCUMM_CURSOR_LEFT
    bpl ScummV5_Cursor_Draw__X_nonnegative
    lda #$0000
ScummV5_Cursor_Draw__X_nonnegative:
    .a16
    .i16
    sta.l SAME_SCUMM_CURSOR_CLIP_X
    lda.l SAME_SCUMM_CURSOR_LEFT
    clc
    adc #$0010
    bpl ScummV5_Cursor_Draw__X_end_positive
    jml ScummV5_Cursor_Draw__commit
ScummV5_Cursor_Draw__X_end_positive:
    .a16
    .i16
    cmp #$0100
    bcc ScummV5_Cursor_Draw__X_end_clipped
    lda #$0100
ScummV5_Cursor_Draw__X_end_clipped:
    .a16
    .i16
    cmp.l SAME_SCUMM_CURSOR_CLIP_X
    bcc ScummV5_Cursor_Draw__X_empty
    bne ScummV5_Cursor_Draw__X_nonempty
ScummV5_Cursor_Draw__X_empty:
    .a16
    .i16
    jml ScummV5_Cursor_Draw__commit
ScummV5_Cursor_Draw__X_nonempty:
    .a16
    .i16
    sec
    sbc.l SAME_SCUMM_CURSOR_CLIP_X
    sta.l SAME_SCUMM_CURSOR_WIDTH
    lda.l SAME_SCUMM_CURSOR_TOP
    bpl ScummV5_Cursor_Draw__Y_nonnegative
    lda #$0000
ScummV5_Cursor_Draw__Y_nonnegative:
    .a16
    .i16
    sta.l SAME_SCUMM_CURSOR_CLIP_Y
    lda.l SAME_SCUMM_CURSOR_TOP
    clc
    adc #$0010
    bpl ScummV5_Cursor_Draw__Y_end_positive
    jml ScummV5_Cursor_Draw__commit
ScummV5_Cursor_Draw__Y_end_positive:
    .a16
    .i16
    cmp #$00E0
    bcc ScummV5_Cursor_Draw__Y_end_clipped
    lda #$00E0
ScummV5_Cursor_Draw__Y_end_clipped:
    .a16
    .i16
    cmp.l SAME_SCUMM_CURSOR_CLIP_Y
    bcc ScummV5_Cursor_Draw__Y_empty
    bne ScummV5_Cursor_Draw__Y_nonempty
ScummV5_Cursor_Draw__Y_empty:
    .a16
    .i16
    jml ScummV5_Cursor_Draw__commit
ScummV5_Cursor_Draw__Y_nonempty:
    .a16
    .i16
    sec
    sbc.l SAME_SCUMM_CURSOR_CLIP_Y
    sta.l SAME_SCUMM_CURSOR_HEIGHT
    lda.l SAME_SCUMM_CURSOR_CLIP_Y
    xba
    ora.l SAME_SCUMM_CURSOR_CLIP_X
    pha
    lda.l SAME_SCUMM_CURSOR_WIDTH
    tax
    lda.l SAME_SCUMM_CURSOR_HEIGHT
    tay
    pla
    jsl Same_VideoSurface_CaptureCursorUnderlay_Far
    bcc ScummV5_Cursor_Draw__captured
    jml ScummV5_Cursor_Draw__failure
ScummV5_Cursor_Draw__captured:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_CLIP_Y
    sta.l SAME_SCUMM_CURSOR_ROW
ScummV5_Cursor_Draw__row:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_ROW
    sec
    sbc.l SAME_SCUMM_CURSOR_TOP
    asl
    clc
    adc.l SAME_SCUMM_CURSOR_TABLE
    tax
    lda.l ScummV5_Cursor_Masks,x
    sta.l SAME_SCUMM_CURSOR_MASK
    lda.l SAME_SCUMM_CURSOR_CLIP_X
    sec
    sbc.l SAME_SCUMM_CURSOR_LEFT
    tax
    beq ScummV5_Cursor_Draw__mask_ready
    lda.l SAME_SCUMM_CURSOR_MASK
ScummV5_Cursor_Draw__shift:
    .a16
    .i16
    asl
    dex
    bne ScummV5_Cursor_Draw__shift
    sta.l SAME_SCUMM_CURSOR_MASK
ScummV5_Cursor_Draw__mask_ready:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_CLIP_X
    sta.l SAME_SCUMM_CURSOR_COLUMN
ScummV5_Cursor_Draw__pixel:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_MASK
    asl
    sta.l SAME_SCUMM_CURSOR_MASK
    bcc ScummV5_Cursor_Draw__transparent
    lda.l SAME_SCUMM_CURSOR_ROW
    xba
    ora.l SAME_SCUMM_CURSOR_COLUMN
    tax
    lda.l SAME_SCUMM_CURSOR_DESIRED_COLOR
    jsl Same_VideoSurface_WriteIndexedPixel_Far
ScummV5_Cursor_Draw__transparent:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_COLUMN
    inc
    sta.l SAME_SCUMM_CURSOR_COLUMN
    sec
    sbc.l SAME_SCUMM_CURSOR_CLIP_X
    cmp.l SAME_SCUMM_CURSOR_WIDTH
    bcc ScummV5_Cursor_Draw__pixel
    lda.l SAME_SCUMM_CURSOR_ROW
    inc
    sta.l SAME_SCUMM_CURSOR_ROW
    sec
    sbc.l SAME_SCUMM_CURSOR_CLIP_Y
    cmp.l SAME_SCUMM_CURSOR_HEIGHT
    bcc ScummV5_Cursor_Draw__row
ScummV5_Cursor_Draw__commit:
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sta.l SAME_SCUMM_CURSOR_X
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sta.l SAME_SCUMM_CURSOR_Y
    lda.l SAME_SCUMM_CURSOR_DESIRED_VISIBLE
    sta.l SAME_SCUMM_CURSOR_VISIBLE
    lda.l SAME_SCUMM_CURSOR_DESIRED_COLOR
    sta.l SAME_SCUMM_CURSOR_COLOR
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_CURSOR_GENERATION
    lda.l SAME_SCUMM_C7_CURSOR_ID
    and #$00FF
    sta.l SAME_SCUMM_CURSOR_ID
    lda #$0001
    sta.l SAME_SCUMM_CURSOR_VALID
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cursor_Draw__invalid:
    .a16
    .i16
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
ScummV5_Cursor_Draw__failure:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; Map a logical hotspot on the exact installed SC5VIS sampling grid.
; All generated table loads use plain labels (pinned assembler bank rule).
ScummV5_Cursor_Project_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    .if SCUMM_MSU1_CAMERA_VIEWPORT
    ; Cursor is logical virtual-screen space; projection uses the currently
    ; installed viewport, while object hit testing keeps original world space.
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sta.l SAME_SCUMM_CURSOR_LEFT
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    clc
    adc.l SAME_SCUMM_CAMERA_CURRENT_Y
    sec
    sbc #$0064
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sta.l SAME_SCUMM_CURSOR_TOP
    ply
    plx
    pla
    plp
    clc
    rtl
    .endif
    lda.l SAME_VIDEO_SURFACE_ROOM
    and #$00FF
    asl
    tax
    lda.l ScummV5_MsuVisualProjectionOffsets,x
    cmp #SCUMM_MSU1_PROJECTION_MISSING
    bne ScummV5_Cursor_Project__found
    jml ScummV5_Cursor_Project__fail
ScummV5_Cursor_Project__found:
    .a16
    .i16
    tax
    clc
    adc #SCUMM_MSU1_PROJECTION_HEADER_SIZE
    sta.l SAME_SCUMM_CURSOR_XBASE
    inx
    inx
    inx
    inx
    lda.l ScummV5_MsuVisualProjectionData,x
    sta.l SAME_SCUMM_CURSOR_XCOUNT
    asl
    clc
    adc.l SAME_SCUMM_CURSOR_XBASE
    sta.l SAME_SCUMM_CURSOR_YBASE
    inx
    inx
    lda.l ScummV5_MsuVisualProjectionData,x
    sta.l SAME_SCUMM_CURSOR_YCOUNT
    inx
    inx
    lda.l ScummV5_MsuVisualProjectionData,x
    sta.l SAME_SCUMM_CURSOR_ORIGIN_X
    inx
    inx
    lda.l ScummV5_MsuVisualProjectionData,x
    sta.l SAME_SCUMM_CURSOR_ORIGIN_Y
    lda.l SAME_SCUMM_CURSOR_XBASE
    tax
    lda.l SAME_SCUMM_CURSOR_XCOUNT
    tay
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    bpl ScummV5_Cursor_Project__X_positive
    lda #$0000
ScummV5_Cursor_Project__X_positive:
    .a16
    .i16
    jsl ScummV5_ActorPose_ProjectSpan_Far
    clc
    adc.l SAME_SCUMM_CURSOR_ORIGIN_X
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CURSOR_LEFT
    lda.l SAME_SCUMM_CURSOR_YBASE
    tax
    lda.l SAME_SCUMM_CURSOR_YCOUNT
    tay
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    bpl ScummV5_Cursor_Project__Y_positive
    lda #$0000
ScummV5_Cursor_Project__Y_positive:
    .a16
    .i16
    jsl ScummV5_ActorPose_ProjectSpan_Far
    clc
    adc.l SAME_SCUMM_CURSOR_ORIGIN_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_CURSOR_TOP
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cursor_Project__fail:
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

.include "scumm_v5_cursor_shapes.inc.pasm"
