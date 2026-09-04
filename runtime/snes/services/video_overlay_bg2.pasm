; Independent Mode-3 BG2 INDEX8 subtitle overlay.  This module owns no SCUMM
; semantics: it consumes one validated descriptor plus SET_LAYER generation.
.bank 22
.org $8000

SAME_OVERLAY_TMP_X0       = SAME_OVERLAY_WORK+$20
SAME_OVERLAY_TMP_X1       = SAME_OVERLAY_WORK+$22
SAME_OVERLAY_TMP_Y0       = SAME_OVERLAY_WORK+$24
SAME_OVERLAY_TMP_Y1       = SAME_OVERLAY_WORK+$26
SAME_OVERLAY_TMP_CELL_X   = SAME_OVERLAY_WORK+$28
SAME_OVERLAY_TMP_CELL_Y   = SAME_OVERLAY_WORK+$2A
SAME_OVERLAY_TMP_ROW      = SAME_OVERLAY_WORK+$2C
SAME_OVERLAY_TMP_COL      = SAME_OVERLAY_WORK+$2E
SAME_OVERLAY_TMP_COL_LO   = SAME_OVERLAY_TMP_COL&$FFFF
SAME_OVERLAY_TMP_SOURCE   = SAME_OVERLAY_WORK+$30
SAME_OVERLAY_TMP_SLOT     = SAME_OVERLAY_WORK+$32
SAME_OVERLAY_TMP_NONZERO  = SAME_OVERLAY_WORK+$34
SAME_OVERLAY_TMP_GROUP    = SAME_OVERLAY_WORK+$35
SAME_OVERLAY_TMP_MIN      = SAME_OVERLAY_WORK+$36
SAME_OVERLAY_TMP_MAX      = SAME_OVERLAY_WORK+$38
SAME_OVERLAY_TMP_LENGTH   = SAME_OVERLAY_WORK+$3A
SAME_OVERLAY_TMP_BIT      = SAME_OVERLAY_WORK+$3C
SAME_OVERLAY_TMP_BIT_LO   = SAME_OVERLAY_TMP_BIT&$FFFF
SAME_OVERLAY_TMP_ROWBASE  = SAME_OVERLAY_WORK+$3E
SAME_OVERLAY_TMP_SOURCE_X = SAME_OVERLAY_WORK+$40

Same_Overlay_Bg2_BitMasks:
    .byte $80,$40,$20,$10,$08,$04,$02,$01

; Two INDEX8 pixels -> two coverage bits.  Only transparent zero and one
; monochrome foreground value ($0F) are accepted by this fast path; $FF
; selects the fully general validated encoder.
Same_Overlay_Bg2_Mono15Pair:
    .byte $00,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$02
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF
    .byte $01,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$FF,$03

Same_Overlay_Bg2_Reset_Far:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
Same_Overlay_Bg2_Reset__loop:
    .a16
    sta.l SAME_OVERLAY_DESCRIPTOR,x
    inx
    inx
    cpx #$1000
    bcc Same_Overlay_Bg2_Reset__loop
    sep #$20
    .a8
    lda #SAME_OVERLAY_STATE_IDLE
    sta.l SAME_OVERLAY_STATE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S11
    plp
    rtl

; Forced-blank-only PPU setup and immutable blank map installation.
Same_Overlay_Bg2_Boot_Far:
    php
    sep #$20
    .a8
    lda #$70
    sta BG12NBA
    lda #$7C
    sta BG2SC
    stz BG2HOFS
    stz BG2HOFS
    lda #$FF
    sta BG2VOFS
    lda #$03
    sta BG2VOFS
    lda #$03
    sta TM
    rep #$20
    .a16
    lda #Same_Overlay_Bg2_BlankCharacter
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$E800
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0020
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$16
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM|SAME_DMA_FLAG_FORCED_BLANK
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Overlay_Bg2_Boot__error
    rep #$20
    .a16
    lda #Same_Overlay_Bg2_BlankTilemap
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$F800
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$16
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM|SAME_DMA_FLAG_FORCED_BLANK
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Overlay_Bg2_Boot__error
    jsl Same_Mode3_Video_Commit_Far
    bra Same_Overlay_Bg2_Boot__done
Same_Overlay_Bg2_Boot__error:
    .a8
    lda #SAME_OVERLAY_STATE_ERROR
    sta.l SAME_OVERLAY_STATE
    rep #$20
    .a16
    lda.l SAME_OVERLAY_ERROR_COUNT
    inc
    sta.l SAME_OVERLAY_ERROR_COUNT
Same_Overlay_Bg2_Boot__done:
    plp
    rtl

; Carry set means the SET_LAYER packet was consumed (accepted or rejected).
Same_Overlay_Bg2_Handle_Far:
    php
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_VIDEO_OP_SET_LAYER
    beq Same_Overlay_Bg2_Handle__ours
    plp
    clc
    rtl
Same_Overlay_Bg2_Handle__ours:
    .a8
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S4
    sep #$20
    .a8
    lda.l SAME_OVERLAY_STATE
    cmp #SAME_OVERLAY_STATE_IDLE
    bne Same_Overlay_Bg2_Handle__reject
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    bne Same_Overlay_Bg2_Handle__reject16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    ora.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    beq Same_Overlay_Bg2_Handle__reject16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    and #$00FF
    cmp #$0001
    bne Same_Overlay_Bg2_Handle__reject16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    xba
    and #$00FF
    cmp #$0002
    bcs Same_Overlay_Bg2_Handle__reject16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    cmp.l SAME_OVERLAY_CURRENT_GENERATION+$02
    bcc Same_Overlay_Bg2_Handle__reject16
    bne Same_Overlay_Bg2_Handle__generation_ok
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp.l SAME_OVERLAY_CURRENT_GENERATION
    beq Same_Overlay_Bg2_Handle__reject16
    bcc Same_Overlay_Bg2_Handle__reject16
Same_Overlay_Bg2_Handle__generation_ok:
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_OVERLAY_CURRENT_GENERATION
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    sta.l SAME_OVERLAY_CURRENT_GENERATION+$02
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$01
    sta.l SAME_OVERLAY_DESCRIPTOR_VISIBLE
    lda #SAME_OVERLAY_STATE_PREPARING
    sta.l SAME_OVERLAY_STATE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S5
    rep #$20
    .a16
    lda.l SAME_OVERLAY_ACCEPTED_COUNT
    inc
    sta.l SAME_OVERLAY_ACCEPTED_COUNT
    plp
    sec
    rtl
Same_Overlay_Bg2_Handle__reject16:
    sep #$20
    .a8
Same_Overlay_Bg2_Handle__reject:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_REJECTED_COUNT
    inc
    sta.l SAME_OVERLAY_REJECTED_COUNT
    plp
    sec
    rtl

Same_Overlay_Bg2_Step_Far:
    php
    sep #$20
    .a8
    lda.l SAME_OVERLAY_STATE
    cmp #SAME_OVERLAY_STATE_PREPARING
    beq Same_Overlay_Bg2_Step__prepare
    cmp #SAME_OVERLAY_STATE_WAITING_DMA
    beq Same_Overlay_Bg2_Step__wait
    plp
    rtl

; NMI-side hook.  It may observe DMA completion, but must never enter the
; comparatively long PREPARING conversion while the engine-side step is
; already using the same bounded scratch state.
Same_Overlay_Bg2_Commit_Far:
    php
    sep #$20
    .a8
    lda.l SAME_OVERLAY_STATE
    cmp #SAME_OVERLAY_STATE_WAITING_DMA
    beq Same_Overlay_Bg2_Step__wait
    plp
    rtl
Same_Overlay_Bg2_Step__prepare:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S6_ENTRY
    jsr Same_Overlay_Bg2_Prepare
    bcs Same_Overlay_Bg2_Step__error
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S6_EXIT
    sta.l SAME_OVERLAY_TRACE_S9_ENTRY
    jsr Same_Overlay_Bg2_Queue
    bcs Same_Overlay_Bg2_Step__error
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S9_EXIT
    plp
    rtl
Same_Overlay_Bg2_Step__wait:
    rep #$20
    .a16
    lda.l SAME_DMA_COMMITTED
    cmp.l SAME_OVERLAY_EXPECTED_DMA
    bcc Same_Overlay_Bg2_Step__done
    sep #$20
    .a8
    lda.l SAME_OVERLAY_PENDING
    sta.l SAME_OVERLAY_ACTIVE_COUNT
    ldx #$0000
Same_Overlay_Bg2_Step__copy_cells:
    .a16
    cpx #SAME_OVERLAY_MAX_CELLS*2
    bcs Same_Overlay_Bg2_Step__copy_done
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PENDING_CELLS,x
    sta.l SAME_OVERLAY_ACTIVE_CELLS,x
    inx
    inx
    bra Same_Overlay_Bg2_Step__copy_cells
Same_Overlay_Bg2_Step__copy_done:
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S11
    lda.l SAME_OVERLAY_CURRENT_GENERATION
    sta.l SAME_OVERLAY_COMMITTED_GENERATION
    lda.l SAME_OVERLAY_CURRENT_GENERATION+$02
    sta.l SAME_OVERLAY_COMMITTED_GENERATION+$02
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_INFLIGHT_COUNT
    lda #SAME_OVERLAY_STATE_IDLE
    sta.l SAME_OVERLAY_STATE
    plp
    rtl
Same_Overlay_Bg2_Step__error:
    sep #$20
    .a8
    lda #SAME_OVERLAY_STATE_ERROR
    sta.l SAME_OVERLAY_STATE
    rep #$20
    .a16
    lda.l SAME_OVERLAY_ERROR_COUNT
    inc
    sta.l SAME_OVERLAY_ERROR_COUNT
Same_Overlay_Bg2_Step__done:
    plp
    rtl

; Build deterministic sparse cells. The descriptor is fully validated before
; any staging state is replaced.
Same_Overlay_Bg2_Prepare:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_DESCRIPTOR_MAGIC
    cmp #SAME_OVERLAY_MAGIC
    beq Same_Overlay_Bg2_Prepare__magic_ok
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__magic_ok:
    sep #$20
    .a8
    lda.l SAME_OVERLAY_DESCRIPTOR_SCHEMA
    cmp #SAME_OVERLAY_SCHEMA
    beq Same_Overlay_Bg2_Prepare__schema_ok
    jmp Same_Overlay_Bg2_Prepare__fail8
Same_Overlay_Bg2_Prepare__schema_ok:
    .a8
    lda.l SAME_OVERLAY_DESCRIPTOR_VISIBLE
    bne Same_Overlay_Bg2_Prepare__show
    jmp Same_Overlay_Bg2_Prepare__explicit_hide
Same_Overlay_Bg2_Prepare__show:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_DESCRIPTOR_WIDTH
    bne Same_Overlay_Bg2_Prepare__width_nonzero
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__width_nonzero:
    .a16
    cmp #SAME_OVERLAY_MAX_WIDTH+1
    bcc Same_Overlay_Bg2_Prepare__width_ok
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__width_ok:
    lda.l SAME_OVERLAY_DESCRIPTOR_HEIGHT
    bne Same_Overlay_Bg2_Prepare__height_nonzero
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__height_nonzero:
    .a16
    cmp #SAME_OVERLAY_MAX_HEIGHT+1
    bcc Same_Overlay_Bg2_Prepare__height_ok
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__height_ok:
    lda.l SAME_OVERLAY_DESCRIPTOR_PITCH
    cmp.l SAME_OVERLAY_DESCRIPTOR_WIDTH
    bcs Same_Overlay_Bg2_Prepare__pitch_ok
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__pitch_ok:
    .a16
    lda.l SAME_OVERLAY_DESCRIPTOR_LENGTH
    cmp #SAME_OVERLAY_PIXELS_SIZE
    beq Same_Overlay_Bg2_Prepare__length_ok
    jmp Same_Overlay_Bg2_Prepare__fail
Same_Overlay_Bg2_Prepare__length_ok:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_PENDING
    rep #$20
    .a16
    lda #$7FFF
    sta.l SAME_OVERLAY_TMP_MIN
    lda #$0000
    sta.l SAME_OVERLAY_TMP_MAX
    ; Clamp screen tile bounds. Negative starts clamp to zero.
    lda.l SAME_OVERLAY_DESCRIPTOR_X
    clc
    adc.l SAME_OVERLAY_DESCRIPTOR_CONTENT_X0
    bpl Same_Overlay_Bg2_Prepare__x_nonnegative
    lda #$0000
    bra Same_Overlay_Bg2_Prepare__x0
Same_Overlay_Bg2_Prepare__x_nonnegative:
    lsr
    lsr
    lsr
Same_Overlay_Bg2_Prepare__x0:
    .a16
    sta.l SAME_OVERLAY_TMP_X0
    lda.l SAME_OVERLAY_DESCRIPTOR_X
    clc
    adc.l SAME_OVERLAY_DESCRIPTOR_CONTENT_X1
    bpl Same_Overlay_Bg2_Prepare__x_end_visible
    jmp Same_Overlay_Bg2_Prepare__finalize
Same_Overlay_Bg2_Prepare__x_end_visible:
    .a16
    lsr
    lsr
    lsr
    cmp #$0020
    bcc Same_Overlay_Bg2_Prepare__x1
    lda #$001F
Same_Overlay_Bg2_Prepare__x1:
    .a16
    sta.l SAME_OVERLAY_TMP_X1
    lda.l SAME_OVERLAY_DESCRIPTOR_Y
    clc
    adc.l SAME_OVERLAY_DESCRIPTOR_CONTENT_Y0
    bpl Same_Overlay_Bg2_Prepare__y_nonnegative
    lda #$0000
    bra Same_Overlay_Bg2_Prepare__y0
Same_Overlay_Bg2_Prepare__y_nonnegative:
    lsr
    lsr
    lsr
Same_Overlay_Bg2_Prepare__y0:
    .a16
    sta.l SAME_OVERLAY_TMP_Y0
    lda.l SAME_OVERLAY_DESCRIPTOR_Y
    clc
    adc.l SAME_OVERLAY_DESCRIPTOR_CONTENT_Y1
    bmi Same_Overlay_Bg2_Prepare__finalize
    lsr
    lsr
    lsr
    cmp #$001C
    bcc Same_Overlay_Bg2_Prepare__y1
    lda #$001B
Same_Overlay_Bg2_Prepare__y1:
    sta.l SAME_OVERLAY_TMP_Y1
    lda.l SAME_OVERLAY_TMP_Y0
    sta.l SAME_OVERLAY_TMP_CELL_Y
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S7_ENTRY
Same_Overlay_Bg2_Prepare__cell_row:
    lda.l SAME_OVERLAY_TMP_X0
    sta.l SAME_OVERLAY_TMP_CELL_X
Same_Overlay_Bg2_Prepare__cell:
    jsr Same_Overlay_Bg2_EncodeCell
    bcs Same_Overlay_Bg2_Prepare__fail
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_CELL_X
    inc
    sta.l SAME_OVERLAY_TMP_CELL_X
    cmp.l SAME_OVERLAY_TMP_X1
    beq Same_Overlay_Bg2_Prepare__cell
    bcc Same_Overlay_Bg2_Prepare__cell
    lda.l SAME_OVERLAY_TMP_CELL_Y
    inc
    sta.l SAME_OVERLAY_TMP_CELL_Y
    cmp.l SAME_OVERLAY_TMP_Y1
    beq Same_Overlay_Bg2_Prepare__cell_row
    bcc Same_Overlay_Bg2_Prepare__cell_row
Same_Overlay_Bg2_Prepare__finalize:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S6
    sta.l SAME_OVERLAY_TRACE_S7
    sta.l SAME_OVERLAY_TRACE_S7_EXIT
    sta.l SAME_OVERLAY_TRACE_S8_ENTRY
    jsr Same_Overlay_Bg2_BuildTilemap
    php
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S8
    sta.l SAME_OVERLAY_TRACE_S8_EXIT
    plp
    rts
Same_Overlay_Bg2_Prepare__explicit_hide:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_PENDING
    rep #$20
    .a16
    lda #$7FFF
    sta.l SAME_OVERLAY_TMP_MIN
    lda #$0000
    sta.l SAME_OVERLAY_TMP_MAX
    bra Same_Overlay_Bg2_Prepare__finalize
Same_Overlay_Bg2_Prepare__fail8:
    rep #$20
    .a16
Same_Overlay_Bg2_Prepare__fail:
    sec
    rts

; Encode one screen cell to the next dynamic 4bpp slot.
Same_Overlay_Bg2_EncodeCell:
    rep #$30
    .a16
    .i16
    lda.l SAME_OVERLAY_PENDING
    and #$00FF
    cmp #SAME_OVERLAY_MAX_CELLS
    bcc Same_Overlay_Bg2_EncodeCell__capacity_ok
    jmp Same_Overlay_Bg2_EncodeCell__fail
Same_Overlay_Bg2_EncodeCell__capacity_ok:
    jsr Same_Overlay_Bg2_EncodeCellFast15
    bcs Same_Overlay_Bg2_EncodeCell__slow
    jmp Same_Overlay_Bg2_EncodeCell__tile_done
Same_Overlay_Bg2_EncodeCell__slow:
    .a16
    lda.l SAME_OVERLAY_PENDING
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_TMP_SLOT
    tax
    lda #$0000
    ldy #$0000
Same_Overlay_Bg2_EncodeCell__clear:
    .a16
    sta.l SAME_OVERLAY_TILE_STAGE,x
    inx
    inx
    iny
    iny
    cpy #$0020
    bcc Same_Overlay_Bg2_EncodeCell__clear
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_TMP_NONZERO
    lda #$FF
    sta.l SAME_OVERLAY_TMP_GROUP
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_TMP_ROW
    lda.l SAME_OVERLAY_TMP_CELL_X
    asl
    asl
    asl
    sec
    sbc.l SAME_OVERLAY_DESCRIPTOR_X
    sta.l SAME_OVERLAY_TMP_SOURCE_X
Same_Overlay_Bg2_EncodeCell__row:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_TMP_COL
    lda.l SAME_OVERLAY_TMP_CELL_Y
    asl
    asl
    asl
    clc
    adc.l SAME_OVERLAY_TMP_ROW
    sec
    sbc.l SAME_OVERLAY_DESCRIPTOR_Y
    bpl Same_Overlay_Bg2_EncodeCell__row_nonnegative
    jmp Same_Overlay_Bg2_EncodeCell__row_done
Same_Overlay_Bg2_EncodeCell__row_nonnegative:
    .a16
    .i16
    cmp.l SAME_OVERLAY_DESCRIPTOR_HEIGHT
    bcc Same_Overlay_Bg2_EncodeCell__row_inside
    jmp Same_Overlay_Bg2_EncodeCell__row_done
Same_Overlay_Bg2_EncodeCell__row_inside:
    .a16
    .i16
    tay
    lda #$0000
Same_Overlay_Bg2_EncodeCell__row_pitch:
    .a16
    .i16
    cpy #$0000
    beq Same_Overlay_Bg2_EncodeCell__row_pitch_done
    clc
    adc.l SAME_OVERLAY_DESCRIPTOR_PITCH
    dey
    bra Same_Overlay_Bg2_EncodeCell__row_pitch
Same_Overlay_Bg2_EncodeCell__row_pitch_done:
    sta.l SAME_OVERLAY_TMP_ROWBASE
Same_Overlay_Bg2_EncodeCell__pixel:
    ; source x = precomputed cell source X + column.
    lda.l SAME_OVERLAY_TMP_SOURCE_X
    clc
    adc.l SAME_OVERLAY_TMP_COL
    bpl Same_Overlay_Bg2_EncodeCell__x_positive
    jmp Same_Overlay_Bg2_EncodeCell__next
Same_Overlay_Bg2_EncodeCell__x_positive:
    cmp.l SAME_OVERLAY_DESCRIPTOR_WIDTH
    bcc Same_Overlay_Bg2_EncodeCell__x_inside
    jmp Same_Overlay_Bg2_EncodeCell__next
Same_Overlay_Bg2_EncodeCell__x_inside:
    clc
    adc.l SAME_OVERLAY_TMP_ROWBASE
    tax
    sep #$20
    .a8
    lda.l SAME_OVERLAY_PIXELS,x
    cmp.l SAME_OVERLAY_DESCRIPTOR_TRANSPARENT
    bne Same_Overlay_Bg2_EncodeCell__opaque
    jmp Same_Overlay_Bg2_EncodeCell__next8
Same_Overlay_Bg2_EncodeCell__opaque:
    .a8
    pha
    and #$0F
    bne Same_Overlay_Bg2_EncodeCell__local_ok
    jmp Same_Overlay_Bg2_EncodeCell__bad8
Same_Overlay_Bg2_EncodeCell__local_ok:
    .a8
    pla
    pha
    lsr
    lsr
    lsr
    lsr
    pha
    lda.l SAME_OVERLAY_TMP_GROUP
    cmp #$FF
    pla
    beq Same_Overlay_Bg2_EncodeCell__set_group
    cmp.l SAME_OVERLAY_TMP_GROUP
    beq Same_Overlay_Bg2_EncodeCell__group_ok
    jmp Same_Overlay_Bg2_EncodeCell__bad_pop8
    bra Same_Overlay_Bg2_EncodeCell__group_ok
Same_Overlay_Bg2_EncodeCell__set_group:
    sta.l SAME_OVERLAY_TMP_GROUP
Same_Overlay_Bg2_EncodeCell__group_ok:
    .a8
    pla
    and #$0F
    sta.l SAME_OVERLAY_TMP_NONZERO
    cmp #$0F
    bne Same_Overlay_Bg2_EncodeCell__planes_general
    ; The authentic one-color mask uses local color 15.  Emit its four equal
    ; plane bits directly; this keeps the bounded subtitle conversion inside
    ; one active-display frame without changing general INDEX8 semantics.
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_COL
    tax
    sep #$20
    .a8
    lda.l Same_Overlay_Bg2_BitMasks,x
    sta.l SAME_OVERLAY_TMP_BIT
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_ROW
    asl
    clc
    adc.l SAME_OVERLAY_TMP_SLOT
    tax
    sep #$20
    .a8
    lda.l SAME_OVERLAY_TILE_STAGE,x
    ora.l SAME_OVERLAY_TMP_BIT
    sta.l SAME_OVERLAY_TILE_STAGE,x
    lda.l SAME_OVERLAY_TILE_STAGE+1,x
    ora.l SAME_OVERLAY_TMP_BIT
    sta.l SAME_OVERLAY_TILE_STAGE+1,x
    lda.l SAME_OVERLAY_TILE_STAGE+16,x
    ora.l SAME_OVERLAY_TMP_BIT
    sta.l SAME_OVERLAY_TILE_STAGE+16,x
    lda.l SAME_OVERLAY_TILE_STAGE+17,x
    ora.l SAME_OVERLAY_TMP_BIT
    sta.l SAME_OVERLAY_TILE_STAGE+17,x
    jmp Same_Overlay_Bg2_EncodeCell__next8
Same_Overlay_Bg2_EncodeCell__planes_general:
    .a8
    .i16
    ; Set each selected plane byte.
    ldy #$0000
Same_Overlay_Bg2_EncodeCell__plane:
    .a8
    pha
    and #$01
    beq Same_Overlay_Bg2_EncodeCell__plane_skip
    rep #$20
    .a16
    tya
    and #$0001
    sta.l SAME_OVERLAY_TMP_SOURCE
    tya
    lsr
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_TMP_BIT
    lda.l SAME_OVERLAY_TMP_ROW
    asl
    clc
    adc.l SAME_OVERLAY_TMP_BIT
    clc
    adc.l SAME_OVERLAY_TMP_SOURCE
    clc
    adc.l SAME_OVERLAY_TMP_SLOT
    sta.l SAME_OVERLAY_TMP_SOURCE
    lda.l SAME_OVERLAY_TMP_COL
    tax
    sep #$20
    .a8
    lda.l Same_Overlay_Bg2_BitMasks,x
    sta.l SAME_OVERLAY_TMP_BIT
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_SOURCE
    tax
    sep #$20
    .a8
    lda.l SAME_OVERLAY_TILE_STAGE,x
    ora.l SAME_OVERLAY_TMP_BIT
    sta.l SAME_OVERLAY_TILE_STAGE,x
Same_Overlay_Bg2_EncodeCell__plane_skip:
    .a8
    pla
    lsr
    iny
    cpy #$0004
    bcc Same_Overlay_Bg2_EncodeCell__plane
Same_Overlay_Bg2_EncodeCell__next8:
    rep #$20
    .a16
Same_Overlay_Bg2_EncodeCell__next:
    .a16
    lda.l SAME_OVERLAY_TMP_COL
    inc
    sta.l SAME_OVERLAY_TMP_COL
    cmp #$0008
    bcs Same_Overlay_Bg2_EncodeCell__row_done
    jmp Same_Overlay_Bg2_EncodeCell__pixel
Same_Overlay_Bg2_EncodeCell__row_done:
    .a16
    lda.l SAME_OVERLAY_TMP_ROW
    inc
    sta.l SAME_OVERLAY_TMP_ROW
    cmp #$0008
    bcs Same_Overlay_Bg2_EncodeCell__tile_done
    jmp Same_Overlay_Bg2_EncodeCell__row
Same_Overlay_Bg2_EncodeCell__tile_done:
    sep #$20
    .a8
    lda.l SAME_OVERLAY_TMP_NONZERO
    beq Same_Overlay_Bg2_EncodeCell__empty
    lda.l SAME_OVERLAY_PENDING
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l SAME_OVERLAY_TMP_CELL_Y
    xba
    and #$FF00
    lsr
    lsr
    lsr
    clc
    adc.l SAME_OVERLAY_TMP_CELL_X
    sta.l SAME_OVERLAY_PENDING_CELLS,x
    cmp.l SAME_OVERLAY_TMP_MIN
    bcs Same_Overlay_Bg2_EncodeCell__not_min
    sta.l SAME_OVERLAY_TMP_MIN
Same_Overlay_Bg2_EncodeCell__not_min:
    cmp.l SAME_OVERLAY_TMP_MAX
    bcc Same_Overlay_Bg2_EncodeCell__not_max
    sta.l SAME_OVERLAY_TMP_MAX
Same_Overlay_Bg2_EncodeCell__not_max:
    sep #$20
    .a8
    lda.l SAME_OVERLAY_PENDING
    inc
    sta.l SAME_OVERLAY_PENDING
Same_Overlay_Bg2_EncodeCell__empty:
    clc
    rts
Same_Overlay_Bg2_EncodeCell__bad_pop8:
    pla
    rep #$20
    .a16
    bra Same_Overlay_Bg2_EncodeCell__fail
Same_Overlay_Bg2_EncodeCell__bad8:
    pla
    rep #$20
    .a16
Same_Overlay_Bg2_EncodeCell__fail:
    sec
    rts

; Fast bounded mask encoder for transparent zero / foreground index 15.
; Other INDEX8 palette values retain the generic path above.
Same_Overlay_Bg2_EncodeCellFast15:
    rep #$30
    .a16
    .i16
    lda.l SAME_OVERLAY_DESCRIPTOR_TRANSPARENT
    and #$00FF
    beq Same_Overlay_Bg2_EncodeCellFast15__transparent_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback
Same_Overlay_Bg2_EncodeCellFast15__transparent_ok:
    .a16
    lda.l SAME_OVERLAY_PENDING
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_TMP_SLOT
    lda.l SAME_OVERLAY_TMP_CELL_X
    asl
    asl
    asl
    sec
    sbc.l SAME_OVERLAY_DESCRIPTOR_X
    bpl Same_Overlay_Bg2_EncodeCellFast15__source_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback
Same_Overlay_Bg2_EncodeCellFast15__source_ok:
    .a16
    sta.l SAME_OVERLAY_TMP_SOURCE_X
    clc
    adc #$0008
    cmp.l SAME_OVERLAY_DESCRIPTOR_WIDTH
    bcc Same_Overlay_Bg2_EncodeCellFast15__width_ok
    beq Same_Overlay_Bg2_EncodeCellFast15__width_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback
Same_Overlay_Bg2_EncodeCellFast15__width_ok:
    .a16
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
    rep #$20
    .a16
    ; Every one of the 8 rows below writes all four plane bytes, including
    ; zero masks for transparent/out-of-bounds rows.  A separate 32-byte
    ; clear is therefore redundant on this generic monochrome path.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_TMP_NONZERO
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_TMP_ROW
    lda.l SAME_OVERLAY_TMP_CELL_Y
    asl
    asl
    asl
    sec
    sbc.l SAME_OVERLAY_DESCRIPTOR_Y
    sta.l SAME_OVERLAY_TMP_ROWBASE
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_TMP_SOURCE
    asl
    asl
    clc
    adc.l SAME_OVERLAY_TMP_SOURCE
    clc
    adc.l SAME_OVERLAY_TMP_SOURCE_X
    sta.l SAME_OVERLAY_TMP_SOURCE
Same_Overlay_Bg2_EncodeCellFast15__row:
    lda.l SAME_OVERLAY_TMP_ROWBASE
    bpl Same_Overlay_Bg2_EncodeCellFast15__row_nonnegative
    jmp Same_Overlay_Bg2_EncodeCellFast15__row_done
Same_Overlay_Bg2_EncodeCellFast15__row_nonnegative:
    cmp.l SAME_OVERLAY_DESCRIPTOR_HEIGHT
    bcc Same_Overlay_Bg2_EncodeCellFast15__row_inside
    jmp Same_Overlay_Bg2_EncodeCellFast15__row_done
Same_Overlay_Bg2_EncodeCellFast15__row_inside:
    .a16
    lda.l SAME_OVERLAY_TMP_SOURCE
    tax
    lda #$0000
    sta.w SAME_OVERLAY_TMP_COL_LO
    sep #$20
    .a8
    ; Pack four validated pixel pairs.  This remains generic monochrome
    ; INDEX8 handling, but avoids eight branch-heavy per-pixel iterations.
    txy
    lda.w SAME_OVERLAY_PIXELS_LO+1,y
    asl
    asl
    asl
    asl
    ora.w SAME_OVERLAY_PIXELS_LO,y
    sta.w SAME_OVERLAY_TMP_COL_LO
    ldx.w SAME_OVERLAY_TMP_COL_LO
    lda.l Same_Overlay_Bg2_Mono15Pair,x
    cmp #$FF
    bne Same_Overlay_Bg2_EncodeCellFast15__pair0_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback_active8
Same_Overlay_Bg2_EncodeCellFast15__pair0_ok:
    .a8
    asl
    asl
    asl
    asl
    asl
    asl
    sta.w SAME_OVERLAY_TMP_BIT_LO
    iny
    iny
    lda.w SAME_OVERLAY_PIXELS_LO+1,y
    asl
    asl
    asl
    asl
    ora.w SAME_OVERLAY_PIXELS_LO,y
    sta.w SAME_OVERLAY_TMP_COL_LO
    ldx.w SAME_OVERLAY_TMP_COL_LO
    lda.l Same_Overlay_Bg2_Mono15Pair,x
    cmp #$FF
    bne Same_Overlay_Bg2_EncodeCellFast15__pair1_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback_active8
Same_Overlay_Bg2_EncodeCellFast15__pair1_ok:
    .a8
    asl
    asl
    asl
    asl
    ora.w SAME_OVERLAY_TMP_BIT_LO
    sta.w SAME_OVERLAY_TMP_BIT_LO
    iny
    iny
    lda.w SAME_OVERLAY_PIXELS_LO+1,y
    asl
    asl
    asl
    asl
    ora.w SAME_OVERLAY_PIXELS_LO,y
    sta.w SAME_OVERLAY_TMP_COL_LO
    ldx.w SAME_OVERLAY_TMP_COL_LO
    lda.l Same_Overlay_Bg2_Mono15Pair,x
    cmp #$FF
    bne Same_Overlay_Bg2_EncodeCellFast15__pair2_ok
    jmp Same_Overlay_Bg2_EncodeCellFast15__fallback_active8
Same_Overlay_Bg2_EncodeCellFast15__pair2_ok:
    .a8
    asl
    asl
    ora.w SAME_OVERLAY_TMP_BIT_LO
    sta.w SAME_OVERLAY_TMP_BIT_LO
    iny
    iny
    lda.w SAME_OVERLAY_PIXELS_LO+1,y
    asl
    asl
    asl
    asl
    ora.w SAME_OVERLAY_PIXELS_LO,y
    sta.w SAME_OVERLAY_TMP_COL_LO
    ldx.w SAME_OVERLAY_TMP_COL_LO
    lda.l Same_Overlay_Bg2_Mono15Pair,x
    cmp #$FF
    beq Same_Overlay_Bg2_EncodeCellFast15__fallback_active8
    ora.w SAME_OVERLAY_TMP_BIT_LO
    sta.w SAME_OVERLAY_TMP_BIT_LO
    rep #$20
    .a16
    .a16
    lda.l SAME_OVERLAY_TMP_BIT
    beq Same_Overlay_Bg2_EncodeCellFast15__row_mask_ready
    sep #$20
    .a8
    lda #$01
    sta.l SAME_OVERLAY_TMP_NONZERO
    rep #$20
    .a16
Same_Overlay_Bg2_EncodeCellFast15__row_mask_ready:
    lda.l SAME_OVERLAY_TMP_ROW
    asl
    clc
    adc.l SAME_OVERLAY_TMP_SLOT
    tax
    sep #$20
    .a8
    lda.l SAME_OVERLAY_TMP_BIT
    sta.w SAME_OVERLAY_TILE_STAGE_LO,x
    sta.w SAME_OVERLAY_TILE_STAGE_LO+1,x
    sta.w SAME_OVERLAY_TILE_STAGE_LO+16,x
    sta.w SAME_OVERLAY_TILE_STAGE_LO+17,x
Same_Overlay_Bg2_EncodeCellFast15__row_done:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_ROWBASE
    inc
    sta.l SAME_OVERLAY_TMP_ROWBASE
    lda.l SAME_OVERLAY_TMP_SOURCE
    clc
    adc #SAME_OVERLAY_MAX_WIDTH
    sta.l SAME_OVERLAY_TMP_SOURCE
    lda.l SAME_OVERLAY_TMP_ROW
    inc
    sta.l SAME_OVERLAY_TMP_ROW
    cmp #$0008
    bcs Same_Overlay_Bg2_EncodeCellFast15__complete
    jmp Same_Overlay_Bg2_EncodeCellFast15__row
Same_Overlay_Bg2_EncodeCellFast15__complete:
    plb
    clc
    rts
Same_Overlay_Bg2_EncodeCellFast15__fallback_active:
    .a16
    plb
    sec
    rts
Same_Overlay_Bg2_EncodeCellFast15__fallback_active8:
    plb
Same_Overlay_Bg2_EncodeCellFast15__fallback8:
    rep #$20
    .a16
Same_Overlay_Bg2_EncodeCellFast15__fallback:
    sec
    rts

; Build one bounded contiguous tilemap run spanning old and desired cells.
Same_Overlay_Bg2_BuildTilemap:
    rep #$30
    .a16
    .i16
    lda.l SAME_OVERLAY_ACTIVE_COUNT
    and #$00FF
    beq Same_Overlay_Bg2_BuildTilemap__new_bounds
    dec
    asl
    tax
    lda.l SAME_OVERLAY_ACTIVE_CELLS
    cmp.l SAME_OVERLAY_TMP_MIN
    bcs Same_Overlay_Bg2_BuildTilemap__old_min_ok
    sta.l SAME_OVERLAY_TMP_MIN
Same_Overlay_Bg2_BuildTilemap__old_min_ok:
    lda.l SAME_OVERLAY_ACTIVE_CELLS,x
    cmp.l SAME_OVERLAY_TMP_MAX
    bcc Same_Overlay_Bg2_BuildTilemap__new_bounds
    sta.l SAME_OVERLAY_TMP_MAX
Same_Overlay_Bg2_BuildTilemap__new_bounds:
    .a16
    lda.l SAME_OVERLAY_TMP_MIN
    cmp #$7FFF
    bne Same_Overlay_Bg2_BuildTilemap__range
    lda #$0000
    sta.l SAME_OVERLAY_TMP_LENGTH
    clc
    rts
Same_Overlay_Bg2_BuildTilemap__range:
    .a16
    lda.l SAME_OVERLAY_TMP_MAX
    sec
    sbc.l SAME_OVERLAY_TMP_MIN
    inc
    cmp #$0401
    bcs Same_Overlay_Bg2_BuildTilemap__fail
    sta.l SAME_OVERLAY_TMP_LENGTH
    ldx #$0000
Same_Overlay_Bg2_BuildTilemap__entry:
    .a16
    lda #$0040
    sta.l SAME_OVERLAY_TILEMAP_STAGE,x
    inx
    inx
    txa
    lsr
    cmp.l SAME_OVERLAY_TMP_LENGTH
    bcc Same_Overlay_Bg2_BuildTilemap__entry
    ; Replace desired cells with priority-set dynamic tile entries.
    sep #$20
    .a8
    lda.l SAME_OVERLAY_PENDING
    beq Same_Overlay_Bg2_BuildTilemap__done
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_OVERLAY_TMP_SLOT
    ldy #$0000
Same_Overlay_Bg2_BuildTilemap__active:
    .a16
    tya
    tax
    lda.l SAME_OVERLAY_PENDING_CELLS,x
    sec
    sbc.l SAME_OVERLAY_TMP_MIN
    asl
    tax
    tya
    lsr
    clc
    adc #$2041
    sta.l SAME_OVERLAY_TILEMAP_STAGE,x
    iny
    iny
    tya
    lsr
    cmp.l SAME_OVERLAY_TMP_SLOT
    bcc Same_Overlay_Bg2_BuildTilemap__active
Same_Overlay_Bg2_BuildTilemap__done:
    clc
    rts
Same_Overlay_Bg2_BuildTilemap__fail:
    sec
    rts

Same_Overlay_Bg2_Queue:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_OVERLAY_INFLIGHT_COUNT
    lda.l SAME_OVERLAY_PENDING
    beq Same_Overlay_Bg2_Queue__tilemap
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_DMA_REQUEST_LENGTH
    lda #SAME_OVERLAY_TILE_STAGE&$FFFF
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$E820
    sta.l SAME_DMA_REQUEST_TARGET
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Overlay_Bg2_Queue__fail
    lda.l SAME_OVERLAY_INFLIGHT_COUNT
    inc
    sta.l SAME_OVERLAY_INFLIGHT_COUNT
Same_Overlay_Bg2_Queue__tilemap:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_TMP_LENGTH
    beq Same_Overlay_Bg2_Queue__armed
    asl
    sta.l SAME_DMA_REQUEST_LENGTH
    lda #SAME_OVERLAY_TILEMAP_STAGE&$FFFF
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda.l SAME_OVERLAY_TMP_MIN
    asl
    clc
    adc #$F800
    sta.l SAME_DMA_REQUEST_TARGET
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Overlay_Bg2_Queue__fail
    lda.l SAME_OVERLAY_INFLIGHT_COUNT
    inc
    sta.l SAME_OVERLAY_INFLIGHT_COUNT
Same_Overlay_Bg2_Queue__armed:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_INFLIGHT_COUNT
    and #$00FF
    clc
    adc.l SAME_DMA_COMMITTED
    sta.l SAME_OVERLAY_EXPECTED_DMA
    sep #$20
    .a8
    lda #SAME_OVERLAY_STATE_WAITING_DMA
    sta.l SAME_OVERLAY_STATE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_OVERLAY_TRACE_S9
    clc
    rts
Same_Overlay_Bg2_Queue__fail:
    sec
    rts

; Forced-blank initialization assets. Tilemap entries reference transparent
; character 64, not BG1 tile zero.
Same_Overlay_Bg2_BlankCharacter:
    .byte $00,$00,$00,$00,$00,$00,$00,$00
    .byte $00,$00,$00,$00,$00,$00,$00,$00
    .byte $00,$00,$00,$00,$00,$00,$00,$00
    .byte $00,$00,$00,$00,$00,$00,$00,$00
Same_Overlay_Bg2_BlankTilemap:
    .incbin "../generated/video_overlay_bg2_tilemap.bin"
