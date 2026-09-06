; Target-neutral bounded INDEX8 overlay producer used by SCUMM presentation.
; This file names no PPU registers, tile indices, or DMA state.
.bank 23
.org $8000

SAME_OVERLAY_FONT_HEADER_SIZE = $003A
SAME_OVERLAY_FONT_GLYPH_SIZE  = $000E

SAME_OVERLAY_PRODUCER_PEN       = SAME_OVERLAY_WORK+$80
SAME_OVERLAY_PRODUCER_CODE      = SAME_OVERLAY_WORK+$82
SAME_OVERLAY_PRODUCER_ENTRY     = SAME_OVERLAY_WORK+$84
SAME_OVERLAY_PRODUCER_WIDTH     = SAME_OVERLAY_WORK+$86
SAME_OVERLAY_PRODUCER_HEIGHT    = SAME_OVERLAY_WORK+$88
SAME_OVERLAY_PRODUCER_XORIGIN   = SAME_OVERLAY_WORK+$8A
SAME_OVERLAY_PRODUCER_YORIGIN   = SAME_OVERLAY_WORK+$8C
SAME_OVERLAY_PRODUCER_PAYLOAD   = SAME_OVERLAY_WORK+$8E
SAME_OVERLAY_PRODUCER_PIXEL     = SAME_OVERLAY_WORK+$90
SAME_OVERLAY_PRODUCER_ROW       = SAME_OVERLAY_WORK+$92
SAME_OVERLAY_PRODUCER_COL       = SAME_OVERLAY_WORK+$94
SAME_OVERLAY_PRODUCER_TEMP      = SAME_OVERLAY_WORK+$96
SAME_OVERLAY_PRODUCER_REMAINING = SAME_OVERLAY_WORK+$98
SAME_OVERLAY_PRODUCER_ADVANCE   = SAME_OVERLAY_WORK+$9C
SAME_OVERLAY_PRODUCER_SOURCE    = SAME_OVERLAY_WORK+$9E
SAME_OVERLAY_PRODUCER_BOUND_X0  = SAME_OVERLAY_WORK+$A0
SAME_OVERLAY_PRODUCER_BOUND_Y0  = SAME_OVERLAY_WORK+$A2
SAME_OVERLAY_PRODUCER_BOUND_X1  = SAME_OVERLAY_WORK+$A4
SAME_OVERLAY_PRODUCER_BOUND_Y1  = SAME_OVERLAY_WORK+$A6

; Carry clear only when the target-owned descriptor and pixel backing can be
; replaced without touching an in-flight update.
Same_VideoOverlay_CanWrite_Far:
    sep #$20
    .a8
    lda.l SAME_OVERLAY_STATE
    cmp #SAME_OVERLAY_STATE_IDLE
    bne Same_VideoOverlay_CanWrite__no
    clc
    rtl
Same_VideoOverlay_CanWrite__no:
    sec
    rtl

Same_VideoOverlay_ShowTalkSegment_Far:
    php
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S1
    jsl Same_VideoOverlay_CanWrite_Far
    bcc Same_VideoOverlay_ShowTalkSegment__available
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plp
    rtl
Same_VideoOverlay_ShowTalkSegment__available:
    rep #$30
    .a16
    .i16
    ; Producer scratch is byte-field rich; clear it so every u8 metric has a
    ; deterministic zero high byte when consumed by the 16-bit raster loops.
    lda #$0000
    ldx #$0000
Same_VideoOverlay_ShowTalkSegment__clear_work:
    .a16
    .i16
    sta.l SAME_OVERLAY_PRODUCER_PEN,x
    inx
    inx
    cpx #$001A
    bcc Same_VideoOverlay_ShowTalkSegment__clear_work
    ; One bounded block move clears the complete 80x8 target-neutral plane.
    ; The source is a generic ROM zero span generated with the font support
    ; tables; no sentence pixels are cached.
    phb
    ldx #ScummV5_FontZeroOverlay
    ldy #SAME_OVERLAY_PIXELS_LO
    lda #SAME_OVERLAY_PIXELS_SIZE-1
    mvn $41,$18
    plb
    jsr Same_VideoOverlay_RasterSegmentFast15
    bcs Same_VideoOverlay_ShowTalkSegment__generic
    jmp Same_VideoOverlay_ShowTalkSegment__ready
Same_VideoOverlay_ShowTalkSegment__generic:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_PEN
    lda #$7FFF
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X0
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y0
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X1
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y1
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_SEGMENT_START
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_COL
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
Same_VideoOverlay_ShowTalkSegment__glyph:
    .a8
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    beq Same_VideoOverlay_ShowTalkSegment__ready
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_COL
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$FF
    bne Same_VideoOverlay_ShowTalkSegment__plain
    ; Preserve logical controls without presenting them as glyphs.  The
    ; fallback path is used for otherwise valid text (for example apostrophe
    ; metrics not covered by Fast15), so it must share the encoded grammar.
    inx
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$01
    beq Same_VideoOverlay_ShowTalkSegment__control_no_args
    cmp #$02
    beq Same_VideoOverlay_ShowTalkSegment__control_no_args
    cmp #$03
    beq Same_VideoOverlay_ShowTalkSegment__control_no_args
    cmp #$08
    beq Same_VideoOverlay_ShowTalkSegment__control_no_args
    inx
    inx
    inx
    rep #$20
    .a16
    txa
    sta.l SAME_OVERLAY_PRODUCER_COL
    bra Same_VideoOverlay_ShowTalkSegment__glyph
Same_VideoOverlay_ShowTalkSegment__control_no_args:
    inx
    rep #$20
    .a16
    txa
    sta.l SAME_OVERLAY_PRODUCER_COL
    bra Same_VideoOverlay_ShowTalkSegment__glyph
Same_VideoOverlay_ShowTalkSegment__plain:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    dec
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    jsr Same_VideoOverlay_RasterGlyph
    bcc Same_VideoOverlay_ShowTalkSegment__glyph_ok
    jmp Same_VideoOverlay_ShowTalkSegment__visual_error
Same_VideoOverlay_ShowTalkSegment__glyph_ok:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_COL
    inc
    sta.l SAME_OVERLAY_PRODUCER_COL
    sep #$20
    .a8
    bra Same_VideoOverlay_ShowTalkSegment__glyph
Same_VideoOverlay_ShowTalkSegment__ready:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S2
    lda #SAME_OVERLAY_MAGIC
    sta.l SAME_OVERLAY_DESCRIPTOR_MAGIC
    sep #$20
    .a8
    lda #SAME_OVERLAY_SCHEMA
    sta.l SAME_OVERLAY_DESCRIPTOR_SCHEMA
    lda #$01
    sta.l SAME_OVERLAY_DESCRIPTOR_VISIBLE
    rep #$20
    .a16
    lda.l SAME_OVERLAY_NEXT_GENERATION
    inc
    bne Same_VideoOverlay_ShowTalkSegment__generation_ok
    inc
Same_VideoOverlay_ShowTalkSegment__generation_ok:
    .a16
    sta.l SAME_OVERLAY_NEXT_GENERATION
    sta.l SAME_OVERLAY_DESCRIPTOR_GENERATION
    lda #$0000
    sta.l SAME_OVERLAY_DESCRIPTOR_GENERATION+$02
    ; Canonical screen-relative transform: string-slot X follows the current
    ; published viewport; the 200-line v5 virtual screen is centered in 224.
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X
    sec
    ; Text is positioned against the canonically published SCUMM virtual
    ; screen, not whichever room projection is currently being uploaded by
    ; the independently progressing BG1 generation.  The fixed display shows
    ; the central 256 pixels of the 320-pixel virtual screen.
    sbc.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    sec
    sbc #$0020
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sta.l SAME_OVERLAY_DESCRIPTOR_X
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y
    clc
    adc #$000C
    sta.l SAME_OVERLAY_DESCRIPTOR_Y
    lda.l SAME_OVERLAY_PRODUCER_PEN
    cmp #SAME_OVERLAY_MAX_WIDTH+1
    bcc Same_VideoOverlay_ShowTalkSegment__width_ready
    lda #SAME_OVERLAY_MAX_WIDTH
Same_VideoOverlay_ShowTalkSegment__width_ready:
    .a16
    sta.l SAME_OVERLAY_DESCRIPTOR_WIDTH
    lda #$0008
    sta.l SAME_OVERLAY_DESCRIPTOR_HEIGHT
    lda #SAME_OVERLAY_MAX_WIDTH
    sta.l SAME_OVERLAY_DESCRIPTOR_PITCH
    lda #SAME_OVERLAY_PIXELS_SIZE
    sta.l SAME_OVERLAY_DESCRIPTOR_LENGTH
    lda.l SAME_OVERLAY_PRODUCER_BOUND_X0
    sta.l SAME_OVERLAY_DESCRIPTOR_CONTENT_X0
    lda.l SAME_OVERLAY_PRODUCER_BOUND_Y0
    sta.l SAME_OVERLAY_DESCRIPTOR_CONTENT_Y0
    lda.l SAME_OVERLAY_PRODUCER_BOUND_X1
    sta.l SAME_OVERLAY_DESCRIPTOR_CONTENT_X1
    lda.l SAME_OVERLAY_PRODUCER_BOUND_Y1
    sta.l SAME_OVERLAY_DESCRIPTOR_CONTENT_Y1
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_DESCRIPTOR_TRANSPARENT
    lda #$01
    jsr Same_VideoOverlay_PushLayer
    bcs Same_VideoOverlay_ShowTalkSegment__visual_error
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S3
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plp
    rtl
Same_VideoOverlay_ShowTalkSegment__visual_error:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plp
    rtl

Same_VideoOverlay_Hide_Far:
    php
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S1
    jsl Same_VideoOverlay_CanWrite_Far
    bcs Same_VideoOverlay_Hide__error
    rep #$20
    .a16
    lda #SAME_OVERLAY_MAGIC
    sta.l SAME_OVERLAY_DESCRIPTOR_MAGIC
    lda.l SAME_OVERLAY_NEXT_GENERATION
    inc
    bne Same_VideoOverlay_Hide__generation_ok
    inc
Same_VideoOverlay_Hide__generation_ok:
    .a16
    sta.l SAME_OVERLAY_NEXT_GENERATION
    sta.l SAME_OVERLAY_DESCRIPTOR_GENERATION
    lda #$0000
    sta.l SAME_OVERLAY_DESCRIPTOR_GENERATION+$02
    sep #$20
    .a8
    lda #SAME_OVERLAY_SCHEMA
    sta.l SAME_OVERLAY_DESCRIPTOR_SCHEMA
    lda #$00
    sta.l SAME_OVERLAY_DESCRIPTOR_VISIBLE
    lda #$00
    jsr Same_VideoOverlay_PushLayer
    bcs Same_VideoOverlay_Hide__error
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S2
    sta.l SAME_OVERLAY_TRACE_S3
    plp
    rtl
Same_VideoOverlay_Hide__error:
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    inc
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plp
    rtl

; A=operation. Publish the completed descriptor last through the normal queue.
Same_VideoOverlay_PushLayer:
    pha
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SET_LAYER
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_OVERLAY_NEXT_GENERATION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0000
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    sep #$20
    .a8
    pla
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$01
    lda #$01
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsl Same_Mode3_Event_Push_Far
    rts

; Complete-font bounded fast lane for solid color 15. Eligibility is generated
; from SC5FNT metrics for every glyph; any unsupported glyph falls back before
; a destination pixel is touched.
Same_VideoOverlay_RasterSegmentFast15:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR
    and #$00FF
    cmp #$000F
    beq Same_VideoOverlay_RasterSegmentFast15__color_ok
    jmp Same_VideoOverlay_RasterSegmentFast15__fail
Same_VideoOverlay_RasterSegmentFast15__color_ok:
    .a16
    lda.l SAME_SCUMM_TALK_SEGMENT_START
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_COL
    lda.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y1
Same_VideoOverlay_RasterSegmentFast15__validate:
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    beq Same_VideoOverlay_RasterSegmentFast15__validated
    lda.l SAME_OVERLAY_PRODUCER_COL
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$FF
    beq Same_VideoOverlay_RasterSegmentFast15__validate_control
    rep #$20
    .a16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l ScummV5_FontFast15Eligible,x
    bne Same_VideoOverlay_RasterSegmentFast15__eligible
    jmp Same_VideoOverlay_RasterSegmentFast15__fail8
Same_VideoOverlay_RasterSegmentFast15__eligible:
    .a8
    lda.l ScummV5_FontContentYMax,x
    cmp #$FF
    beq Same_VideoOverlay_RasterSegmentFast15__ymax_done
    cmp.l SAME_OVERLAY_PRODUCER_BOUND_Y1
    bcc Same_VideoOverlay_RasterSegmentFast15__ymax_done
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y1
Same_VideoOverlay_RasterSegmentFast15__ymax_done:
    .a8
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_COL
    inc
    sta.l SAME_OVERLAY_PRODUCER_COL
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    dec
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
    jmp Same_VideoOverlay_RasterSegmentFast15__validate
Same_VideoOverlay_RasterSegmentFast15__validate_control:
    ; C23 retains encoded controls for logical lifetime/continuation.  They
    ; are not glyphs, so skip their selector and source-defined arguments
    ; while validating the printable projection stream.
    sep #$20
    .a8
    .i16
    inx
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$01
    beq Same_VideoOverlay_RasterSegmentFast15__validate_control_no_args
    cmp #$02
    beq Same_VideoOverlay_RasterSegmentFast15__validate_control_no_args
    cmp #$03
    beq Same_VideoOverlay_RasterSegmentFast15__validate_control_no_args
    cmp #$08
    beq Same_VideoOverlay_RasterSegmentFast15__validate_control_no_args
    inx
    inx
    inx
    rep #$20
    .a16
    txa
    sta.l SAME_OVERLAY_PRODUCER_COL
    jmp Same_VideoOverlay_RasterSegmentFast15__validate
Same_VideoOverlay_RasterSegmentFast15__validate_control_no_args:
    inx
    rep #$20
    .a16
    txa
    sta.l SAME_OVERLAY_PRODUCER_COL
    bra Same_VideoOverlay_RasterSegmentFast15__validate
Same_VideoOverlay_RasterSegmentFast15__validated:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_PEN
    sta.l SAME_OVERLAY_PRODUCER_ROW
    lda.l SAME_SCUMM_TALK_SEGMENT_START
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_COL
    lda.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
Same_VideoOverlay_RasterSegmentFast15__glyph:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    bne Same_VideoOverlay_RasterSegmentFast15__have_glyph
    jmp Same_VideoOverlay_RasterSegmentFast15__complete
Same_VideoOverlay_RasterSegmentFast15__have_glyph:
    .a16
    lda.l SAME_OVERLAY_PRODUCER_COL
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$FF
    bne Same_VideoOverlay_RasterSegmentFast15__glyph_plain
    jmp Same_VideoOverlay_RasterSegmentFast15__glyph_control
Same_VideoOverlay_RasterSegmentFast15__glyph_plain:
    sta.l SAME_OVERLAY_PRODUCER_CODE
    rep #$20
    .a16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l ScummV5_FontAdvances,x
    sta.l SAME_OVERLAY_PRODUCER_ADVANCE
    lda.l ScummV5_FontContentYMax,x
    cmp #$FF
    beq Same_VideoOverlay_RasterSegmentFast15__empty_glyph
    inc
    bra Same_VideoOverlay_RasterSegmentFast15__row_count_ready
Same_VideoOverlay_RasterSegmentFast15__empty_glyph:
    .a8
    lda #$00
Same_VideoOverlay_RasterSegmentFast15__row_count_ready:
    .a8
    sta.l SAME_OVERLAY_PRODUCER_ROW
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_CODE
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l ScummV5_FontSparseCounts,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_ROW
    txa
    asl
    tax
    lda.l ScummV5_FontSparseOffsets,x
    tax
Same_VideoOverlay_RasterSegmentFast15__sparse_pixel:
    lda.l SAME_OVERLAY_PRODUCER_ROW
    beq Same_VideoOverlay_RasterSegmentFast15__rows_done
    lda.l ScummV5_FontSparsePixels,x
    clc
    adc.l SAME_OVERLAY_PRODUCER_PEN
    tay
    sep #$20
    .a8
    lda #$0F
    sta.w SAME_OVERLAY_PIXELS_LO,y
    rep #$20
    .a16
    inx
    inx
    lda.l SAME_OVERLAY_PRODUCER_ROW
    dec
    sta.l SAME_OVERLAY_PRODUCER_ROW
    bra Same_VideoOverlay_RasterSegmentFast15__sparse_pixel
Same_VideoOverlay_RasterSegmentFast15__rows_done:
    .a16
    lda.l SAME_OVERLAY_PRODUCER_PEN
    clc
    adc.l SAME_OVERLAY_PRODUCER_ADVANCE
    sta.l SAME_OVERLAY_PRODUCER_PEN
    lda.l SAME_OVERLAY_PRODUCER_COL
    inc
    sta.l SAME_OVERLAY_PRODUCER_COL
    lda.l SAME_OVERLAY_PRODUCER_REMAINING
    dec
    sta.l SAME_OVERLAY_PRODUCER_REMAINING
    jmp Same_VideoOverlay_RasterSegmentFast15__glyph
Same_VideoOverlay_RasterSegmentFast15__glyph_control:
    sep #$20
    .a8
    .i16
    inx
    lda.l SAME_SCUMM_TALK_RAW,x
    cmp #$01
    beq Same_VideoOverlay_RasterSegmentFast15__glyph_control_no_args
    cmp #$02
    beq Same_VideoOverlay_RasterSegmentFast15__glyph_control_no_args
    cmp #$03
    beq Same_VideoOverlay_RasterSegmentFast15__glyph_control_no_args
    cmp #$08
    beq Same_VideoOverlay_RasterSegmentFast15__glyph_control_no_args
    inx
    inx
    inx
    txa
    rep #$20
    .a16
    sta.l SAME_OVERLAY_PRODUCER_COL
    jmp Same_VideoOverlay_RasterSegmentFast15__glyph
Same_VideoOverlay_RasterSegmentFast15__glyph_control_no_args:
    inx
    txa
    rep #$20
    .a16
    sta.l SAME_OVERLAY_PRODUCER_COL
    jmp Same_VideoOverlay_RasterSegmentFast15__glyph
Same_VideoOverlay_RasterSegmentFast15__complete:
    .a16
    plb
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X0
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y0
    lda.l SAME_OVERLAY_PRODUCER_PEN
    dec
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X1
    clc
    rts
Same_VideoOverlay_RasterSegmentFast15__fail8:
    rep #$20
    .a16
Same_VideoOverlay_RasterSegmentFast15__fail:
    sec
    rts

; Input A=u8 encoded glyph. Exact complete SC5FNT metrics and MSB-first mask.
Same_VideoOverlay_RasterGlyph:
    sta.l SAME_OVERLAY_PRODUCER_CODE
    rep #$30
    .a16
    .i16
    lda.l SAME_OVERLAY_PRODUCER_CODE
    and #$00FF
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    asl
    sta.l SAME_OVERLAY_PRODUCER_ENTRY
    lda.l SAME_OVERLAY_PRODUCER_TEMP
    asl
    asl
    asl
    asl
    sec
    sbc.l SAME_OVERLAY_PRODUCER_ENTRY
    clc
    adc #SAME_OVERLAY_FONT_HEADER_SIZE
    tax
    sep #$20
    .a8
    lda.l ScummV5_Font0_Record,x
    bne Same_VideoOverlay_RasterGlyph__present
    jmp Same_VideoOverlay_RasterGlyph__missing
Same_VideoOverlay_RasterGlyph__present:
    inx
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_ADVANCE
    inx
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_WIDTH
    inx
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_HEIGHT
    inx
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_XORIGIN
    inx
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_YORIGIN
    inx
    ; Accumulate the glyph-metric coverage bounds once per glyph.  The BG2
    ; backend uses these source-neutral bounds to avoid scanning transparent
    ; screen cells outside the actual line metrics.
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_PEN
    clc
    adc.l SAME_OVERLAY_PRODUCER_XORIGIN
    cmp.l SAME_OVERLAY_PRODUCER_BOUND_X0
    bcs Same_VideoOverlay_RasterGlyph__x0_done
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X0
Same_VideoOverlay_RasterGlyph__x0_done:
    clc
    adc.l SAME_OVERLAY_PRODUCER_WIDTH
    dec
    cmp.l SAME_OVERLAY_PRODUCER_BOUND_X1
    bcc Same_VideoOverlay_RasterGlyph__x1_done
    sta.l SAME_OVERLAY_PRODUCER_BOUND_X1
Same_VideoOverlay_RasterGlyph__x1_done:
    lda.l SAME_OVERLAY_PRODUCER_YORIGIN
    cmp.l SAME_OVERLAY_PRODUCER_BOUND_Y0
    bcs Same_VideoOverlay_RasterGlyph__y0_done
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y0
Same_VideoOverlay_RasterGlyph__y0_done:
    clc
    adc.l SAME_OVERLAY_PRODUCER_HEIGHT
    dec
    cmp.l SAME_OVERLAY_PRODUCER_BOUND_Y1
    bcc Same_VideoOverlay_RasterGlyph__y1_done
    sta.l SAME_OVERLAY_PRODUCER_BOUND_Y1
Same_VideoOverlay_RasterGlyph__y1_done:
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l ScummV5_Font0_Record,x
    sta.l SAME_OVERLAY_PRODUCER_PAYLOAD
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_PIXEL
    sta.l SAME_OVERLAY_PRODUCER_ROW
    ; Common bounded path: nonnegative glyph origins whose complete bitmap
    ; fits the 80x8 source-neutral overlay.  Keep source/destination cursors
    ; in X/Y and inspect one coverage byte per pixel; the older clipped path
    ; below remains the fail-closed fallback for unusual metrics.
    lda.l SAME_OVERLAY_PRODUCER_XORIGIN
    bit #$0080
    beq Same_VideoOverlay_RasterGlyph__fast_xorigin_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__fast_xorigin_ok:
    .a16
    clc
    adc.l SAME_OVERLAY_PRODUCER_PEN
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    clc
    adc.l SAME_OVERLAY_PRODUCER_WIDTH
    cmp #SAME_OVERLAY_MAX_WIDTH+1
    bcc Same_VideoOverlay_RasterGlyph__fast_width_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__fast_width_ok:
    .a16
    lda.l SAME_OVERLAY_PRODUCER_YORIGIN
    bit #$0080
    beq Same_VideoOverlay_RasterGlyph__fast_yorigin_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__fast_yorigin_ok:
    .a16
    clc
    adc.l SAME_OVERLAY_PRODUCER_HEIGHT
    cmp #SAME_OVERLAY_MAX_HEIGHT+1
    bcc Same_VideoOverlay_RasterGlyph__fast_height_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__fast_height_ok:
    .a16
    lda.l SAME_OVERLAY_PRODUCER_WIDTH
    cmp #$0009
    bcc Same_VideoOverlay_RasterGlyph__mask_width_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__mask_width_ok:
    .a16
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR
    and #$00FF
    cmp #$000F
    beq Same_VideoOverlay_RasterGlyph__mask_color_ok
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__mask_color_ok:
    .a16
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_ROW
    lda.l SAME_OVERLAY_PRODUCER_YORIGIN
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_PRODUCER_ENTRY
    asl
    asl
    clc
    adc.l SAME_OVERLAY_PRODUCER_ENTRY
    clc
    adc.l SAME_OVERLAY_PRODUCER_TEMP
    sta.l SAME_OVERLAY_PRODUCER_ENTRY
    lda.l SAME_OVERLAY_PRODUCER_CODE
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #ScummV5_FontGlyphExpansion15
    sta.l SAME_OVERLAY_PRODUCER_SOURCE
Same_VideoOverlay_RasterGlyph__fast_row:
    .a16
    ; Copy one generic pre-expanded coverage row. The table is complete for
    ; all 256 glyph codes and contains no sentence-specific imagery.
    lda.l SAME_OVERLAY_PRODUCER_SOURCE
    tax
    tay
    lda #$0007
    mvn $41,$18
Same_VideoOverlay_RasterGlyph__fast_row_done:
    .a16
    lda.l SAME_OVERLAY_PRODUCER_SOURCE
    clc
    adc #$0008
    sta.l SAME_OVERLAY_PRODUCER_SOURCE
    lda.l SAME_OVERLAY_PRODUCER_ENTRY
    clc
    adc #SAME_OVERLAY_MAX_WIDTH
    sta.l SAME_OVERLAY_PRODUCER_ENTRY
    lda.l SAME_OVERLAY_PRODUCER_ROW
    inc
    sta.l SAME_OVERLAY_PRODUCER_ROW
    cmp.l SAME_OVERLAY_PRODUCER_HEIGHT
    bcs Same_VideoOverlay_RasterGlyph__fast_complete
    jmp Same_VideoOverlay_RasterGlyph__fast_row
Same_VideoOverlay_RasterGlyph__fast_complete:
    plb
    jmp Same_VideoOverlay_RasterGlyph__complete
Same_VideoOverlay_RasterGlyph__row:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_PRODUCER_COL
Same_VideoOverlay_RasterGlyph__pixel:
    lda.l SAME_OVERLAY_PRODUCER_PIXEL
    clc
    adc.l SAME_OVERLAY_PRODUCER_PAYLOAD
    tax
    sep #$20
    .a8
    lda.l ScummV5_Font0_Record,x
    beq Same_VideoOverlay_RasterGlyph__next
    ; target = (row+yOrigin)*80 + pen+col+xOrigin
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_ROW
    clc
    adc.l SAME_OVERLAY_PRODUCER_YORIGIN
    bmi Same_VideoOverlay_RasterGlyph__next16
    cmp #SAME_OVERLAY_MAX_HEIGHT
    bcs Same_VideoOverlay_RasterGlyph__next16
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_PRODUCER_ENTRY
    asl
    asl
    clc
    adc.l SAME_OVERLAY_PRODUCER_ENTRY
    clc
    adc.l SAME_OVERLAY_PRODUCER_PEN
    clc
    adc.l SAME_OVERLAY_PRODUCER_COL
    clc
    adc.l SAME_OVERLAY_PRODUCER_XORIGIN
    bmi Same_VideoOverlay_RasterGlyph__next16
    cmp #SAME_OVERLAY_PIXELS_SIZE
    bcs Same_VideoOverlay_RasterGlyph__next16
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR
    sta.l SAME_OVERLAY_PIXELS,x
Same_VideoOverlay_RasterGlyph__next:
    rep #$20
    .a16
Same_VideoOverlay_RasterGlyph__next16:
    lda.l SAME_OVERLAY_PRODUCER_PIXEL
    inc
    sta.l SAME_OVERLAY_PRODUCER_PIXEL
    lda.l SAME_OVERLAY_PRODUCER_COL
    inc
    sta.l SAME_OVERLAY_PRODUCER_COL
    cmp.l SAME_OVERLAY_PRODUCER_WIDTH
    bcs Same_VideoOverlay_RasterGlyph__row_advance
    jmp Same_VideoOverlay_RasterGlyph__pixel
Same_VideoOverlay_RasterGlyph__row_advance:
    lda.l SAME_OVERLAY_PRODUCER_ROW
    inc
    sta.l SAME_OVERLAY_PRODUCER_ROW
    cmp.l SAME_OVERLAY_PRODUCER_HEIGHT
    bcs Same_VideoOverlay_RasterGlyph__complete
    jmp Same_VideoOverlay_RasterGlyph__row
Same_VideoOverlay_RasterGlyph__complete:
    sep #$20
    .a8
    lda.l SAME_OVERLAY_PRODUCER_ADVANCE
    rep #$20
    .a16
    and #$00FF
    clc
    adc.l SAME_OVERLAY_PRODUCER_PEN
    sta.l SAME_OVERLAY_PRODUCER_PEN
    sep #$20
    .a8
    clc
    rts
Same_VideoOverlay_RasterGlyph__missing:
    sep #$20
    .a8
    sec
    rts
Same_VideoOverlay_RasterGlyph__fail:
    sep #$20
    .a8
    sec
    rts
