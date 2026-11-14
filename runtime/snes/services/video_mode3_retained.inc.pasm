; Retained viewport in the existing Mode-3 backend. Physical character IDs
; 0..767 retain the scene, 768..895 retain the fixed HUD, 896..919 guard one
; column. The 64x32 tilemap and HOFS are committed by NMI, after character DMA.
; BG2's legacy VRAM allocation is exclusive with this layout.
MODE3_R_ACTIVE = SAME_BWRAM_CONTROL_RESERVED
MODE3_R_CURRENT = SAME_BWRAM_RETAINED_VIEWPORT+$00
MODE3_R_NEXT = SAME_BWRAM_RETAINED_VIEWPORT+$02
MODE3_R_FIRST = SAME_BWRAM_RETAINED_VIEWPORT+$04
MODE3_R_LAST = SAME_BWRAM_RETAINED_VIEWPORT+$06
MODE3_R_COLUMN = SAME_BWRAM_RETAINED_VIEWPORT+$08
MODE3_R_PHYSICAL = SAME_BWRAM_RETAINED_VIEWPORT+$0A
MODE3_R_DELTA = SAME_BWRAM_RETAINED_VIEWPORT+$0C
MODE3_R_PHASE = SAME_BWRAM_RETAINED_VIEWPORT+$0E
MODE3_R_GUARD_VALID = SAME_BWRAM_RETAINED_VIEWPORT+$0F
MODE3_R_INPUT = SAME_BWRAM_RETAINED_VIEWPORT+$10
MODE3_R_TOP = SAME_BWRAM_RETAINED_VIEWPORT+$12
MODE3_R_HEIGHT = SAME_BWRAM_RETAINED_VIEWPORT+$14
MODE3_R_SOURCE_Y = SAME_BWRAM_RETAINED_VIEWPORT+$16
MODE3_R_INDEX_ORIGIN = SAME_BWRAM_RETAINED_VIEWPORT+$18
MODE3_R_BASE = SAME_BWRAM_RETAINED_VIEWPORT+$1A
MODE3_R_GENERATION = SAME_BWRAM_RETAINED_VIEWPORT+$1C
MODE3_R_MAX = SAME_BWRAM_RETAINED_VIEWPORT+$1E
MODE3_R_HDMA = SAME_MODE3_SCROLL_HDMA
MODE3_R_X = SAME_BWRAM_RETAINED_VIEWPORT+$2A
MODE3_R_Y = SAME_BWRAM_RETAINED_VIEWPORT+$2C
MODE3_R_MASK = SAME_BWRAM_RETAINED_VIEWPORT+$30
MODE3_R_TEMP = SAME_BWRAM_RETAINED_VIEWPORT+$32
MODE3_R_GENERATION_HI = SAME_BWRAM_RETAINED_VIEWPORT+$36
MODE3_R_VALIDATED = SAME_BWRAM_RETAINED_VIEWPORT+$38
MODE3_R_EXCHANGE = SAME_BWRAM_RETAINED_VIEWPORT+$39
MODE3_R_KEEP_ACTOR = SAME_BWRAM_RETAINED_VIEWPORT+$3A

Same_Mode3_Retained_Reset_Far:
    .a16
    php
    sep #$20
    .a8
    lda #$00
    sta.l MODE3_R_ACTIVE
    plp
    rtl

; A full scene replacement invalidates cached off-screen source coverage.
; Keep the committed ring/map/origin, but trust only complete columns whose
; INDEX8 pixels were replaced. Partial edge columns must be checked again
; before exposing their previously hidden pixels, including on reversal.
Same_Mode3_Retained_InvalidateCoverage_Far:
    php
    rep #$20
    .a16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_Mode3_Retained_InvalidateCoverage__done
    lda.l MODE3_R_CURRENT
    clc
    adc #$0007
    lsr
    lsr
    lsr
    sta.l MODE3_R_FIRST
    lda.l MODE3_R_CURRENT
    clc
    adc #$0100
    lsr
    lsr
    lsr
    dec
    sta.l MODE3_R_LAST
Same_Mode3_Retained_InvalidateCoverage__done:
    plp
    rtl

; Enable a cold, already-published 256x192 scene. A16 is the maximum relative
; horizontal origin; X16 is the tile-aligned cold source origin. INDEX8 is
; row-major; the generated cold map resolves column-contiguous scene characters.
; Caller must own an idle surface; this does not publish or alter pixels.
Same_Mode3_Retained_Init_Far:
    .a8
    php
    rep #$30
    .a16
    .i16
    pha
    txa
    and #$0007
    bne Same_Mode3_Retained_Init__busy
    lda.l SAME_MODE3_CONTROL_STATE
    and #$00FF
    cmp #SAME_MODE3_STATE_IDLE
    bne Same_Mode3_Retained_Init__busy
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    bne Same_Mode3_Retained_Init__busy
    pla
    sta.l MODE3_R_MAX
    txa
    sta.l MODE3_R_BASE
    sta.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    lsr
    lsr
    lsr
    sta.l MODE3_R_FIRST
    clc
    adc #$001F
    sta.l MODE3_R_LAST
    lda #$0000
    sta.l MODE3_R_PHASE
    sta.l MODE3_R_INDEX_ORIGIN
    sta.l MODE3_R_VALIDATED
    lda #$FFFF
    sta.l MODE3_R_COLUMN
    sep #$20
    .a8
    .if SAME_VIDEO_OVERLAY_BG2
    plp
    sec
    rtl
    .else
    lda #$01
    sta.l MODE3_R_ACTIVE
    plp
    clc
    rtl
    .endif
Same_Mode3_Retained_Init__busy:
    .a8
    pla
    plp
    sec
    rtl

; A16 desired relative origin. Step only as far as the next alignment boundary
; so a physical column still sampled by the committed PPU cannot be reused.
; C clear: accepted, A16 is a required source column or $FFFF (no read needed).
; No surface/character/map byte is written here. A failed read can abort safely.
Same_Mode3_Retained_Begin_Far:
    .a8
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    beq Same_Mode3_Retained_LongSkip1
    brl Same_Mode3_Retained_Begin__busy
Same_Mode3_Retained_LongSkip1:
    .a16
    lda.l MODE3_R_PHASE
    and #$00FF
    beq Same_Mode3_Retained_LongSkip2
    brl Same_Mode3_Retained_Begin__busy
Same_Mode3_Retained_LongSkip2:
    .a16
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    beq Same_Mode3_Retained_LongSkip3
    brl Same_Mode3_Retained_Begin__busy
Same_Mode3_Retained_LongSkip3:
    .a16
    pla
    cmp.l MODE3_R_MAX
    bcc Same_Mode3_Retained_Begin__bounded
    lda.l MODE3_R_MAX
Same_Mode3_Retained_Begin__bounded:
    .a16
    sta.l MODE3_R_NEXT
    cmp.l MODE3_R_CURRENT
    bne Same_Mode3_Retained_LongSkip4
    brl Same_Mode3_Retained_Begin__unchanged
Same_Mode3_Retained_LongSkip4:
    .a16
    bcc Same_Mode3_Retained_Begin__left
    lda.l MODE3_R_CURRENT
    and #$FFF8
    clc
    adc #$0008
    cmp.l MODE3_R_NEXT
    bcs Same_Mode3_Retained_Begin__step
    sta.l MODE3_R_NEXT
    bra Same_Mode3_Retained_Begin__step
Same_Mode3_Retained_Begin__left:
    .a16
    lda.l MODE3_R_CURRENT
    dec
    and #$FFF8
    cmp.l MODE3_R_NEXT
    bcc Same_Mode3_Retained_Begin__step
    sta.l MODE3_R_NEXT
Same_Mode3_Retained_Begin__step:
    .a16
    lda.l MODE3_R_NEXT
    sec
    sbc.l MODE3_R_CURRENT
    sta.l MODE3_R_DELTA
    lda.l MODE3_R_NEXT
    lsr
    lsr
    lsr
    cmp.l MODE3_R_FIRST
    bcc Same_Mode3_Retained_Begin__column
    lda.l MODE3_R_NEXT
    clc
    adc #$00FF
    lsr
    lsr
    lsr
    cmp.l MODE3_R_LAST
    beq Same_Mode3_Retained_Begin__no_column
    bcc Same_Mode3_Retained_Begin__no_column
Same_Mode3_Retained_Begin__column:
    .a16
    sta.l MODE3_R_COLUMN
    lda.l MODE3_R_BASE
    lsr
    lsr
    lsr
    sta.l MODE3_R_TEMP
    lda.l MODE3_R_COLUMN
    sec
    sbc.l MODE3_R_TEMP
Same_Mode3_Retained_Begin__negative:
    .a16
    bpl Same_Mode3_Retained_Begin__modulo
    clc
    adc #$0021
    bra Same_Mode3_Retained_Begin__negative
Same_Mode3_Retained_Begin__modulo:
    .a16
    cmp #$0021
    bcc Same_Mode3_Retained_Begin__physical
    sec
    sbc #$0021
    bra Same_Mode3_Retained_Begin__modulo
Same_Mode3_Retained_Begin__physical:
    .a16
    sta.l MODE3_R_PHYSICAL
    bra Same_Mode3_Retained_Begin__accepted
Same_Mode3_Retained_Begin__no_column:
    .a16
    lda #$FFFF
    sta.l MODE3_R_COLUMN
Same_Mode3_Retained_Begin__accepted:
    .a16
    lda #$0000
    sta.l MODE3_R_VALIDATED
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    bne Same_Mode3_Retained_Begin__needs_validation
    lda #$0001
    sta.l MODE3_R_VALIDATED
Same_Mode3_Retained_Begin__needs_validation:
    .a16
    lda #$0000
    sta.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    sta.l SAME_MODE3_CONTROL_UNCHANGED_COUNT
    sep #$20
    .a8
    lda #$01
    sta.l MODE3_R_PHASE
    rep #$20
    .a16
    lda.l MODE3_R_COLUMN
    plp
    clc
    rtl
Same_Mode3_Retained_Begin__busy:
    .a16
    pla
Same_Mode3_Retained_Begin__unchanged:
    .a16
    plp
    sec
    rtl

; The caller owns verified, immutable checked input until conversion retires.
; Validate its bounded eight-pixel strip description before marking any tile.
; INPUT is a bank40 address in the dedicated first2048 pending bytes; TOP and
; HEIGHT specify scene placement; SOURCE_Y skips validated source rows.
Same_Mode3_Retained_ColumnReady_Far:
    .a16
    php
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_PHASE
    and #$00FF
    cmp #$0001
    beq Same_Mode3_Retained_LongSkip5
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip5:
    .a16
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    bne Same_Mode3_Retained_ColumnReady__has_column
    brl Same_Mode3_Retained_ColumnReady__ok
Same_Mode3_Retained_ColumnReady__has_column:
    .a16
    lda.l MODE3_R_INPUT
    cmp #SAME_BWRAM_LIVE_ROOM_PENDING&$FFFF
    bcs Same_Mode3_Retained_LongSkip6
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip6:
    .a16
    lda.l MODE3_R_HEIGHT
    bne Same_Mode3_Retained_LongSkip7
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip7:
    .a16
    clc
    adc.l MODE3_R_TOP
    bcc Same_Mode3_Retained_LongSkip8
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip8:
    .a16
    cmp #$00C1
    bcc Same_Mode3_Retained_LongSkip9
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip9:
    .a16
    lda.l MODE3_R_HEIGHT
    clc
    adc.l MODE3_R_SOURCE_Y
    bcc Same_Mode3_Retained_LongSkip10
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip10:
    .a16
    cmp #$0101
    bcc Same_Mode3_Retained_LongSkip11
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip11:
    .a16
    asl
    asl
    asl
    clc
    adc.l MODE3_R_INPUT
    bcc Same_Mode3_Retained_LongSkip12
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip12:
    .a16
    cmp #(SAME_BWRAM_LIVE_ROOM_PENDING&$FFFF)+$0801
    bcc Same_Mode3_Retained_LongSkip13
    brl Same_Mode3_Retained_ColumnReady__bad
Same_Mode3_Retained_LongSkip13:
    .a16
    lda #$0000
    sta.l MODE3_R_Y
Same_Mode3_Retained_ColumnReady__row:
    .a16
    lda.l MODE3_R_PHYSICAL
    cmp #$0020
    beq Same_Mode3_Retained_ColumnReady__guard
    lda.l MODE3_R_Y
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l MODE3_R_PHYSICAL
    bra Same_Mode3_Retained_ColumnReady__candidate
Same_Mode3_Retained_ColumnReady__guard:
    .a16
    lda.l MODE3_R_Y
    clc
    adc #$0380
Same_Mode3_Retained_ColumnReady__candidate:
    .a16
    jsr Same_Mode3_SetCandidateTile
    rep #$20
    .a16
    lda.l MODE3_R_Y
    inc
    sta.l MODE3_R_Y
    cmp #$0018
    bcc Same_Mode3_Retained_ColumnReady__row
Same_Mode3_Retained_ColumnReady__ok:
    .a16
    lda #$0001
    sta.l MODE3_R_VALIDATED
    plp
    clc
    rtl
Same_Mode3_Retained_ColumnReady__bad:
    .a16
    plp
    sec
    rtl

; Main-loop completion may request, but never perform, a visible scroll.
; C set: hold the surface/generation until NMI acknowledges this exact ticket.
Same_Mode3_Retained_Complete:
    .a16
    sep #$20
    .a8
    lda.l MODE3_R_ACTIVE
    beq Same_Mode3_Retained_Complete__done
    cmp #$02
    beq Same_Mode3_Retained_Complete__done
    lda.l MODE3_R_PHASE
    beq Same_Mode3_Retained_Complete__done
    cmp #$03
    beq Same_Mode3_Retained_Complete__ack
    cmp #$02
    beq Same_Mode3_Retained_Complete__wait
    rep #$20
    .a16
    lda.l SAME_BWRAM_CONTROL_PENDING_GENERATION
    sta.l MODE3_R_GENERATION
    lda.l SAME_MODE3_CONTROL_PENDING_GENERATION_HI
    sta.l MODE3_R_GENERATION_HI
    sep #$20
    .a8
    lda #$02 ; immutable ticket published last
    sta.l MODE3_R_PHASE
Same_Mode3_Retained_Complete__wait:
    .a8
    sec
    rts
Same_Mode3_Retained_Complete__ack:
    .a8
    lda #$00
    sta.l MODE3_R_PHASE
    lda.l MODE3_R_ACTIVE
    cmp #$03
    bne Same_Mode3_Retained_Complete__done
    lda #$00
    sta.l MODE3_R_ACTIVE
Same_Mode3_Retained_Complete__done:
    .a8
    clc
    rts

; Called by the selected backend's NMI hook, after the DMA queue service.
; No main-loop scratch, DBR, index widths or flags leak across the interrupt.
Same_Mode3_Retained_Nmi_Far:
    .a8
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    .if SAME_VIDEO_OVERLAY_BG2 == 0
    sep #$20
    .a8
    lda.l MODE3_R_ACTIVE
    bne Same_Mode3_Retained_Nmi__active
    stz HDMAEN
    stz BG1HOFS
    stz BG1HOFS
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__active:
    .a8
    .a8
    lda.l MODE3_R_PHASE
    cmp #$02
    beq Same_Mode3_Retained_Nmi__ticket
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__ticket:
    .a8
    .a8
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_COMPLETE
    beq Same_Mode3_Retained_Nmi__complete
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__complete:
    .a8
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    bne Same_Mode3_Retained_Nmi__locked
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__locked:
    .a8
    .a8
    rep #$20
    .a16
    lda.l SAME_BWRAM_CONTROL_PENDING_GENERATION
    cmp.l MODE3_R_GENERATION
    beq Same_Mode3_Retained_Nmi__low
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__low:
    .a16
    .a16
    lda.l SAME_MODE3_CONTROL_PENDING_GENERATION_HI
    cmp.l MODE3_R_GENERATION_HI
    beq Same_Mode3_Retained_Nmi__identity
    brl Same_Mode3_Retained_Nmi__done
Same_Mode3_Retained_Nmi__identity:
    .a16
    .a16
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    beq Same_Mode3_Retained_Nmi__scroll
    ; Map relative to the cold grid, preserving canonical source coordinates.
    asl
    asl
    asl
    sec
    sbc.l MODE3_R_BASE
    and #$00F8
    lsr
    lsr
    lsr
    clc
    adc #$7800
    tay
    lda.l MODE3_R_COLUMN
    asl
    asl
    asl
    sec
    sbc.l MODE3_R_BASE
    and #$0100
    beq Same_Mode3_Retained_Nmi__screen
    tya
    clc
    adc #$0400
    tay
Same_Mode3_Retained_Nmi__screen:
    .a16
    .a16
    sep #$20
    .a8
    lda #$80
    sta VMAIN
    rep #$20
    .a16
    ldx #$0000
Same_Mode3_Retained_Nmi__map_row:
    .a16
    tya
    sta VMADDL
    lda.l MODE3_R_PHYSICAL
    cmp #$0020
    beq Same_Mode3_Retained_Nmi__guard
    txa
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l MODE3_R_PHYSICAL
    bra Same_Mode3_Retained_Nmi__tile
Same_Mode3_Retained_Nmi__guard:
    .a16
    txa
    clc
    adc #$0380
Same_Mode3_Retained_Nmi__tile:
    .a16
    jsr Same_Mode3_CharacterIndex
    sta VMDATAL
    tya
    clc
    adc #$0020
    tay
    inx
    cpx #$0018
    bcc Same_Mode3_Retained_Nmi__map_row
Same_Mode3_Retained_Nmi__scroll:
    .a16
    ; HDMA mode 2 writes both BG1HOFS latch bytes on the first scanline and
    ; at line192. Two <=127-line entries cover the scene; the HUD stays fixed.
    .a16
    lda.l MODE3_R_NEXT
    sec
    sbc.l MODE3_R_BASE
    and #$01FF
    sta.l MODE3_R_HDMA+$01
    sta.l MODE3_R_HDMA+$04
    lda #$0000
    sta.l MODE3_R_HDMA+$07
    sep #$20
    .a8
    lda #$7F
    sta.l MODE3_R_HDMA
    lda #$41
    sta.l MODE3_R_HDMA+$03
    lda #$20
    sta.l MODE3_R_HDMA+$06
    lda #$00
    sta.l MODE3_R_HDMA+$09
    stz HDMAEN
    lda #$02
    sta $4360
    lda #$0D
    sta $4361
    rep #$20
    .a16
    lda #MODE3_R_HDMA&$FFFF
    sta $4362
    sep #$20
    .a8
    lda #$41
    sta $4364
    lda #$40
    sta HDMAEN
    rep #$20
    .a16
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    beq Same_Mode3_Retained_Nmi__range_done
    cmp.l MODE3_R_FIRST
    bcc Same_Mode3_Retained_Nmi__range_left
    sta.l MODE3_R_LAST
    sec
    sbc #$0020
    sta.l MODE3_R_FIRST
    bra Same_Mode3_Retained_Nmi__range_done
Same_Mode3_Retained_Nmi__range_left:
    .a16
    sta.l MODE3_R_FIRST
    clc
    adc #$0020
    sta.l MODE3_R_LAST
Same_Mode3_Retained_Nmi__range_done:
    .a16
    lda.l MODE3_R_NEXT
    sta.l MODE3_R_CURRENT
    sep #$20
    .a8
    lda #$03
    sta.l MODE3_R_PHASE ; acknowledgment published last
    .endif
Same_Mode3_Retained_Nmi__done:
    .a8
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

; Dispatch leaves the legacy row encoder unchanged for HUD and non-scrolling
; personalities. The retained encoder is selected only after explicit init.
Same_Mode3_EncodeViewportTile:
    .a16
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    beq Same_Mode3_EncodeViewportTile__active
    jmp Same_Mode3_EncodeTile
Same_Mode3_EncodeViewportTile__active:
    .a16
    lda.l SAME_MODE3_WORK_TILE
    cmp #$0300
    bcc Same_Mode3_EncodeViewportTile__scene
    cmp #$0380
    bcs Same_Mode3_EncodeViewportTile__guard
    jmp Same_Mode3_EncodeTile
Same_Mode3_EncodeViewportTile__guard:
    .a16
    sec
    sbc #$0380
    asl
    asl
    asl
    sta.l MODE3_R_Y
    lda #$0020
    bra Same_Mode3_EncodeViewportTile__physical
Same_Mode3_EncodeViewportTile__scene:
    .a16
    pha
    and #$FFE0
    lsr
    lsr
    sta.l MODE3_R_Y
    pla
    and #$001F
Same_Mode3_EncodeViewportTile__physical:
    .a16
    sta.l SAME_MODE3_WORK_INDEX
    lda.l MODE3_R_PHASE
    and #$00FF
    cmp #$0001
    bne Same_Mode3_EncodeViewportTile__surface
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    beq Same_Mode3_EncodeViewportTile__surface
    lda.l SAME_MODE3_WORK_INDEX
    cmp.l MODE3_R_PHYSICAL
    bne Same_Mode3_EncodeViewportTile__surface
    lda #$0001
    sta.l SAME_MODE3_WORK_DESC_TYPE
    lda.l MODE3_R_COLUMN
    asl
    asl
    asl
    sec
    sbc.l MODE3_R_NEXT
    sta.l MODE3_R_X
    lda #$00FF
    sta.l MODE3_R_MASK
    brl Same_Mode3_EncodeViewportTile__setup
Same_Mode3_EncodeViewportTile__surface:
    .a16
    lda #$0000
    sta.l SAME_MODE3_WORK_DESC_TYPE
    lda.l MODE3_R_BASE
    lsr
    lsr
    lsr
    sta.l MODE3_R_TEMP
    lda.l MODE3_R_NEXT
    lsr
    lsr
    lsr
    sec
    sbc.l MODE3_R_TEMP
Same_Mode3_EncodeViewportTile__negative:
    .a16
    bpl Same_Mode3_EncodeViewportTile__modulo
    clc
    adc #$0021
    bra Same_Mode3_EncodeViewportTile__negative
Same_Mode3_EncodeViewportTile__modulo:
    .a16
    cmp #$0021
    bcc Same_Mode3_EncodeViewportTile__left
    sec
    sbc #$0021
    bra Same_Mode3_EncodeViewportTile__modulo
Same_Mode3_EncodeViewportTile__left:
    .a16
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_MODE3_WORK_INDEX
    sec
    sbc.l SAME_MODE3_WORK_TEMP
    bpl Same_Mode3_EncodeViewportTile__relative
    clc
    adc #$0021
Same_Mode3_EncodeViewportTile__relative:
    .a16
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_TEMP
    lda.l MODE3_R_NEXT
    and #$0007
    sta.l SAME_MODE3_WORK_SOURCE
    lda.l SAME_MODE3_WORK_TEMP
    sec
    sbc.l SAME_MODE3_WORK_SOURCE
    sta.l MODE3_R_X
    ; Full character offscreen pixels retain their old checked plane bits.
    sta.l SAME_MODE3_WORK_INDEX
    lda #$0000
    sta.l MODE3_R_MASK
    ldx #$0008
Same_Mode3_EncodeViewportTile__mask:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0100
    lda.l MODE3_R_MASK
    rol
    sta.l MODE3_R_MASK ; carry=1 for hidden; invert once below
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    dex
    bne Same_Mode3_EncodeViewportTile__mask
    lda.l MODE3_R_MASK
    eor #$00FF
    and #$00FF
    sta.l MODE3_R_MASK
Same_Mode3_EncodeViewportTile__setup:
    .a16
    ; A fully visible character occupies one aligned physical INDEX8 tile.
    ; Reuse the original verified encoder; only hidden edge pixels need the
    ; checked-strip/old-shadow merge below. No extra conversion budget.
    lda.l MODE3_R_X
    cmp #$00F9
    bcs Same_Mode3_EncodeViewportTile__partial
    lda.l SAME_MODE3_WORK_TILE
    pha
    lda.l MODE3_R_X
    clc
    adc.l MODE3_R_INDEX_ORIGIN
    and #$00FF
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_TEMP
    lda.l MODE3_R_Y
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_TEMP
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_EncodeTile
    rep #$20
    .a16
    pla
    sta.l SAME_MODE3_WORK_TILE
    rts
Same_Mode3_EncodeViewportTile__partial:
    .a16
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
    rep #$30
    .a16
    .i16
    ldy #$0000
Same_Mode3_EncodeViewportTile__row:
    .a16
    lda #$0000
    sta.l SAME_MODE3_WORK_CHANGED
    lda.l SAME_MODE3_WORK_DESC_TYPE
    beq Same_Mode3_EncodeViewportTile__surface_row
    lda.l MODE3_R_Y
    sec
    sbc.l MODE3_R_TOP
    bcc Same_Mode3_EncodeViewportTile__zero_row
    cmp.l MODE3_R_HEIGHT
    bcs Same_Mode3_EncodeViewportTile__zero_row
    clc
    adc.l MODE3_R_SOURCE_Y
    asl
    asl
    asl
    clc
    adc.l MODE3_R_INPUT
    tax
    bra Same_Mode3_EncodeViewportTile__row_ready
Same_Mode3_EncodeViewportTile__zero_row:
    .a16
    lda #$0002
    sta.l SAME_MODE3_WORK_CHANGED
    ldx #$0000
    bra Same_Mode3_EncodeViewportTile__row_ready
Same_Mode3_EncodeViewportTile__surface_row:
    .a16
    lda.l MODE3_R_Y
    xba
    clc
    adc.l MODE3_R_X
    clc
    adc #$2000
    tax
Same_Mode3_EncodeViewportTile__row_ready:
    .a16
    lda.l MODE3_R_X
    sta.l SAME_MODE3_WORK_INDEX
    sep #$20
    .a8
    lda #$08
    sta.l SAME_MODE3_WORK_COLUMN
Same_Mode3_EncodeViewportTile__column:
    .a8
    lda.l SAME_MODE3_WORK_DESC_TYPE
    beq Same_Mode3_EncodeViewportTile__background
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0100
    bcs Same_Mode3_EncodeViewportTile__background16
    phx
    lda.l MODE3_R_Y
    xba
    clc
    adc.l SAME_MODE3_WORK_INDEX
    tax
    sep #$20
    .a8
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    lda.l SAME_BWRAM_SURFACE_BASE,x
    plx
    plx
    bra Same_Mode3_EncodeViewportTile__pixel
Same_Mode3_EncodeViewportTile__background16:
    .a16
    sep #$20
    .a8
Same_Mode3_EncodeViewportTile__background:
    .a8
    lda.l SAME_MODE3_WORK_CHANGED
    bne Same_Mode3_EncodeViewportTile__zero
    lda.l SAME_MODE3_WORK_DESC_TYPE
    bne Same_Mode3_EncodeViewportTile__read
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0100
    sep #$20
    .a8
    bcs Same_Mode3_EncodeViewportTile__zero
Same_Mode3_EncodeViewportTile__read:
    .a8
    lda.l SAME_MODE3_WORK_DESC_TYPE
    bne Same_Mode3_EncodeViewportTile__checked_read
    phx
    rep #$20
    .a16
    txa
    sec
    sbc #$2000
    tax
    jsl Same_Mode3_MapSurfaceX_Far
    sep #$20
    .a8
    lda.l SAME_BWRAM_SURFACE_BASE,x
    plx
    bra Same_Mode3_EncodeViewportTile__pixel
Same_Mode3_EncodeViewportTile__checked_read:
    .a8
    lda.l $400000,x
    bra Same_Mode3_EncodeViewportTile__pixel
Same_Mode3_EncodeViewportTile__zero:
    .a8
    lda #$00
Same_Mode3_EncodeViewportTile__pixel:
    .a8
    lsr
    rol.w Same_Mode3_RowPlanes+0
    lsr
    rol.w Same_Mode3_RowPlanes+1
    lsr
    rol.w Same_Mode3_RowPlanes+2
    lsr
    rol.w Same_Mode3_RowPlanes+3
    lsr
    rol.w Same_Mode3_RowPlanes+4
    lsr
    rol.w Same_Mode3_RowPlanes+5
    lsr
    rol.w Same_Mode3_RowPlanes+6
    lsr
    rol.w Same_Mode3_RowPlanes+7
    inx
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    sep #$20
    .a8
    lda.l SAME_MODE3_WORK_COLUMN
    dec
    sta.l SAME_MODE3_WORK_COLUMN
    beq Same_Mode3_EncodeViewportTile__column_done
    brl Same_Mode3_EncodeViewportTile__column
Same_Mode3_EncodeViewportTile__column_done:
    .a8
    tyx
    lda.l SAME_MODE3_WORK_X0+0
    sta.l SAME_MODE3_TILE_SCRATCH+$00,x
    lda.l SAME_MODE3_WORK_X0+1
    sta.l SAME_MODE3_TILE_SCRATCH+$01,x
    lda.l SAME_MODE3_WORK_X0+2
    sta.l SAME_MODE3_TILE_SCRATCH+$10,x
    lda.l SAME_MODE3_WORK_X0+3
    sta.l SAME_MODE3_TILE_SCRATCH+$11,x
    lda.l SAME_MODE3_WORK_X0+4
    sta.l SAME_MODE3_TILE_SCRATCH+$20,x
    lda.l SAME_MODE3_WORK_X0+5
    sta.l SAME_MODE3_TILE_SCRATCH+$21,x
    lda.l SAME_MODE3_WORK_X0+6
    sta.l SAME_MODE3_TILE_SCRATCH+$30,x
    lda.l SAME_MODE3_WORK_X0+7
    sta.l SAME_MODE3_TILE_SCRATCH+$31,x
    rep #$20
    .a16
    lda.l MODE3_R_Y
    inc
    sta.l MODE3_R_Y
    iny
    iny
    cpy #$0010
    beq Same_Mode3_EncodeViewportTile__encoded
    brl Same_Mode3_EncodeViewportTile__row
Same_Mode3_EncodeViewportTile__encoded:
    .a16
    plb
    lda.l MODE3_R_MASK
    cmp #$00FF
    beq Same_Mode3_EncodeViewportTile__done
    jsr Same_Mode3_Retained_ShadowAddress
    ldy #$0000
Same_Mode3_EncodeViewportTile__merge:
    .a16
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_SOURCE
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_WORK_DESC_TYPE
    cmp #$40
    beq Same_Mode3_EncodeViewportTile__read_guard
    lda.l $410000,x
    bra Same_Mode3_EncodeViewportTile__old
Same_Mode3_EncodeViewportTile__read_guard:
    .a8
    lda.l $400000,x
Same_Mode3_EncodeViewportTile__old:
    .a8
    sta.l SAME_MODE3_WORK_PIXEL
    lda.l MODE3_R_MASK
    eor #$FF
    and.l SAME_MODE3_WORK_PIXEL
    sta.l SAME_MODE3_WORK_PIXEL
    tyx
    lda.l SAME_MODE3_TILE_SCRATCH,x
    and.l MODE3_R_MASK
    ora.l SAME_MODE3_WORK_PIXEL
    sta.l SAME_MODE3_TILE_SCRATCH,x
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_SOURCE
    inc
    sta.l SAME_MODE3_WORK_SOURCE
    iny
    cpy #$0040
    bcc Same_Mode3_EncodeViewportTile__merge
Same_Mode3_EncodeViewportTile__done:
    .a16
    rep #$30
    .a16
    .i16
    rts

Same_Mode3_Retained_ShadowAddress:
    .a16
    rep #$30
    .a16
    .i16
    lda #$0041
    sta.l SAME_MODE3_WORK_DESC_TYPE
    lda.l SAME_MODE3_WORK_TILE
    cmp #$0380
    bcs Same_Mode3_Retained_ShadowAddress__guard
    jsr Same_Mode3_CharacterIndex
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_SOURCE
    rts
Same_Mode3_Retained_ShadowAddress__guard:
    .a16
    lda #$0040
    sta.l SAME_MODE3_WORK_DESC_TYPE
    lda.l SAME_MODE3_WORK_TILE
    sec
    sbc #$0380
    cmp #$000B
    bcs Same_Mode3_Retained_ShadowAddress__tail
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_BWRAM_RETAINED_GUARD_HEAD&$FFFF
    sta.l SAME_MODE3_WORK_SOURCE
    rts
Same_Mode3_Retained_ShadowAddress__tail:
    .a16
    sec
    sbc #$000B
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_MODE3_GUARD_TAIL&$FFFF
    sta.l SAME_MODE3_WORK_SOURCE
    rts


Same_Mode3_CommitViewportTile:
    .a16
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_TILE
    cmp #$0380
    bcs Same_Mode3_CommitViewportTile__guard
    jmp Same_Mode3_CommitEncodedTile
Same_Mode3_CommitViewportTile__guard:
    .a16
    ; A guard character has never been addressable through the contiguous
    ; $41 shadow: that address is live CGRAM. Copy only to the audited split.
    sec
    sbc #$0380
    cmp #$000B
    bcs Same_Mode3_CommitViewportTile__tail
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_BWRAM_RETAINED_GUARD_HEAD&$FFFF
    bra Same_Mode3_CommitViewportTile__copy
Same_Mode3_CommitViewportTile__tail:
    .a16
    sec
    sbc #$000B
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_MODE3_GUARD_TAIL&$FFFF
Same_Mode3_CommitViewportTile__copy:
    .a16
    tax
    ldy #$0000
Same_Mode3_CommitViewportTile__word:
    .a16
    phx
    tyx
    lda.l SAME_MODE3_TILE_SCRATCH,x
    plx
    sta.l $400000,x
    inx
    inx
    iny
    iny
    cpy #$0040
    bcc Same_Mode3_CommitViewportTile__word
    lda.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_SetPendingTile
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    rts

; The existing INDEX8 scene is a horizontal circular surface. Changing its
; logical origin retains every still-visible pixel in place. Only FillEdge
; writes newly exposed pixels. HUD rows remain linear. This runs under the
; same immutable generation ownership as tile conversion and publication.
Same_Mode3_Retained_ShiftSurface_Far:
    php
    rep #$20
    .a16
    lda.l MODE3_R_NEXT
    sec
    sbc.l MODE3_R_BASE
    and #$00FF
    sta.l MODE3_R_INDEX_ORIGIN
    plp
    rtl

; X16 logical INDEX8 offset -> physical offset. Preserve A/P/Y, no scratch.
; Only the live retained scene is circular; cold/retired rooms and HUD stay
; linear. Byte addition deliberately wraps within its original 256-byte row.
Same_Mode3_MapSurfaceX_Far:
    php
    cld
    rep #$20
    .a16
    pha
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_Mode3_MapSurfaceX__done
    txa
    cmp #$C000
    bcs Same_Mode3_MapSurfaceX__done
    sep #$20
    .a8
    clc
    adc.l MODE3_R_INDEX_ORIGIN
    rep #$20
    .a16
    tax
Same_Mode3_MapSurfaceX__done:
    .a16
    pla
    plp
    rtl

; Extension of the existing copyright-free Mode-3 control. Commands are
; fixture-only, never compiled as a SCUMM gameplay path. The observer writes
; only command/target, never output pixels, counters or backend state.
MODE3_RF_COMMAND = SAME_MODE3_FIXTURE+$0100
MODE3_RF_TARGET = SAME_MODE3_FIXTURE+$0102
MODE3_RF_RESULT = SAME_MODE3_FIXTURE+$0104
MODE3_RF_GENERATION = SAME_MODE3_FIXTURE+$0106
MODE3_RF_START_FRAME = SAME_MODE3_FIXTURE+$0108
MODE3_RF_END_FRAME = SAME_MODE3_FIXTURE+$010A
MODE3_RF_X = SAME_MODE3_FIXTURE+$0110
MODE3_RF_Y = SAME_MODE3_FIXTURE+$0112
MODE3_RF_DEST = SAME_MODE3_FIXTURE+$0114
MODE3_RF_VALUE = SAME_MODE3_FIXTURE+$0116
MODE3_RF_LEFT = SAME_MODE3_FIXTURE+$0118
MODE3_RF_RIGHT = SAME_MODE3_FIXTURE+$011A
MODE3_RF_FOREGROUND = SAME_MODE3_FIXTURE+$011C
MODE3_RF_REVISION = SAME_MODE3_FIXTURE+$011E

Same_Mode3_Retained_Fixture:
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_FIXTURE_DONE
    beq Same_Mode3_Retained_Fixture__return
    lda.l MODE3_RF_COMMAND
    cmp #$0001
    beq Same_Mode3_Retained_Fixture__init
    cmp #$0002
    bne Same_Mode3_Retained_Fixture__not_step
    brl Same_Mode3_Retained_Fixture__step
Same_Mode3_Retained_Fixture__not_step:
    .a16
    cmp #$0004
    bne Same_Mode3_Retained_Fixture__not_foreground
    jmp Same_Mode3_Retained_Fixture_Foreground
Same_Mode3_Retained_Fixture__not_foreground:
    .a16
    cmp #$0005
    bne Same_Mode3_Retained_Fixture__not_admission
    jmp Same_Mode3_Retained_Fixture_Admission
Same_Mode3_Retained_Fixture__not_admission:
    .a16
    cmp #$0006
    bne Same_Mode3_Retained_Fixture__not_cold
    jmp Same_Mode3_Retained_Fixture_Cold
Same_Mode3_Retained_Fixture__not_cold:
    .a16
    cmp #$0007
    bne Same_Mode3_Retained_Fixture__not_stale
    jmp Same_Mode3_Retained_Fixture_Stale
Same_Mode3_Retained_Fixture__not_stale:
    .a16
    cmp #$0008
    bne Same_Mode3_Retained_Fixture__not_recover
    jmp Same_Mode3_Retained_Fixture_Recover
Same_Mode3_Retained_Fixture__not_recover:
    .a16
    cmp #$0009
    bne Same_Mode3_Retained_Fixture__not_refresh
    jmp Same_Mode3_Retained_Fixture_Refresh
Same_Mode3_Retained_Fixture__not_refresh:
    .a16
    cmp #$0003
    beq Same_Mode3_Retained_Fixture__wait
Same_Mode3_Retained_Fixture__return:
    .a16
    rts
Same_Mode3_Retained_Fixture__init:
    .a16
    lda #$0400
    ldx #$0000
    jsl Same_Mode3_Retained_Init_Far
    bcs Same_Mode3_Retained_Fixture__error
    bra Same_Mode3_Retained_Fixture__success
Same_Mode3_Retained_Fixture__wait:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp.l MODE3_RF_GENERATION
    bne Same_Mode3_Retained_Fixture__return
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    bne Same_Mode3_Retained_Fixture__return
    lda.l SAME_FRAME_COUNTER
    sta.l MODE3_RF_END_FRAME
Same_Mode3_Retained_Fixture__success:
    .a16
    lda #$0001
    sta.l MODE3_RF_RESULT
    lda #$0000
    sta.l MODE3_RF_COMMAND
    rts
Same_Mode3_Retained_Fixture__error:
    .a16
    lda #$0002
    sta.l MODE3_RF_RESULT
    lda #$0000
    sta.l MODE3_RF_COMMAND
    rts
Same_Mode3_Retained_Fixture__step:
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l MODE3_RF_START_FRAME
    lda #$0000
    sta.l MODE3_RF_RESULT
    lda.l MODE3_RF_TARGET
    jsl Same_Mode3_Retained_Begin_Far
    bcs Same_Mode3_Retained_Fixture__error
    cmp #$FFFF
    bne Same_Mode3_Retained_Fixture__needs_column
    brl Same_Mode3_Retained_Fixture__shift
Same_Mode3_Retained_Fixture__needs_column:
    .a16
    ; Original generated eight-pixel strip, not a pre-rendered planar result.
    lda #$0000
    sta.l MODE3_RF_Y
    sta.l MODE3_RF_DEST
Same_Mode3_Retained_Fixture__strip_row:
    .a16
    lda #$0000
    sta.l MODE3_RF_X
Same_Mode3_Retained_Fixture__strip_pixel:
    .a16
    lda.l MODE3_R_COLUMN
    asl
    asl
    asl
    clc
    adc.l MODE3_RF_X
    jsr Same_Mode3_Retained_Fixture_Pixel
    pha
    lda.l MODE3_RF_DEST
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    rep #$20
    .a16
    lda.l MODE3_RF_DEST
    inc
    sta.l MODE3_RF_DEST
    lda.l MODE3_RF_X
    inc
    sta.l MODE3_RF_X
    cmp #$0008
    bcc Same_Mode3_Retained_Fixture__strip_pixel
    lda.l MODE3_RF_Y
    inc
    sta.l MODE3_RF_Y
    cmp #$00C0
    bcc Same_Mode3_Retained_Fixture__strip_row
    lda #SAME_BWRAM_LIVE_ROOM_PENDING&$FFFF
    sta.l MODE3_R_INPUT
    lda #$0000
    sta.l MODE3_R_TOP
    sta.l MODE3_R_SOURCE_Y
    lda #$00C0
    sta.l MODE3_R_HEIGHT
    jsl Same_Mode3_Retained_ColumnReady_Far
    bcc Same_Mode3_Retained_Fixture__shift
    brl Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture__shift:
    .a16
    lda.l MODE3_RF_FOREGROUND
    beq Same_Mode3_Retained_Fixture__no_restore
    lda #$0000
    jsr Same_Mode3_Retained_Fixture_Cursor
    jsl Same_Mode3_Retained_FlushDamage_Far
Same_Mode3_Retained_Fixture__no_restore:
    .a16
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    bne Same_Mode3_Retained_Fixture__have_column
    jsl Same_Mode3_Retained_ReadColumn_Far
Same_Mode3_Retained_Fixture__have_column:
    .a16
    jsl Same_Mode3_Retained_ShiftSurface_Far
    jsl Same_Mode3_Retained_FillEdge_Far
    lda.l MODE3_RF_FOREGROUND
    beq Same_Mode3_Retained_Fixture__no_cursor
    lda #$0001
    jsr Same_Mode3_Retained_Fixture_Cursor
    jsl Same_Mode3_Retained_MarkDamage_Far
Same_Mode3_Retained_Fixture__no_cursor:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    inc
    sta.l MODE3_RF_GENERATION
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0003
    sta.l MODE3_RF_COMMAND
    rts

; Existing generation6 pattern extended in world space. Its source mutations
; are original fixture pixels, not actor/gameplay state.
Same_Mode3_Retained_Fixture_Pixel:
    .a16
    sta.l MODE3_RF_VALUE
    lda.l MODE3_RF_FOREGROUND
    beq Same_Mode3_Retained_Fixture_Pixel__background
    lda.l MODE3_RF_Y
    cmp #80
    bcc Same_Mode3_Retained_Fixture_Pixel__background
    cmp #96
    bcs Same_Mode3_Retained_Fixture_Pixel__background
    lda.l MODE3_RF_VALUE
    cmp #100
    bcc Same_Mode3_Retained_Fixture_Pixel__background
    cmp #112
    bcs Same_Mode3_Retained_Fixture_Pixel__background
    and #$0001
    beq Same_Mode3_Retained_Fixture_Pixel__opaque_zero
    lda #$00B1
Same_Mode3_Retained_Fixture_Pixel__opaque_zero:
    .a16
    rts
Same_Mode3_Retained_Fixture_Pixel__background:
    .a16
    lda.l MODE3_RF_VALUE
    clc
    adc.l MODE3_RF_Y
    pha
    lda.l MODE3_RF_Y
    beq Same_Mode3_Retained_Fixture_Pixel__top
    cmp #$0009
    bne Same_Mode3_Retained_Fixture_Pixel__plain
    lda.l MODE3_RF_VALUE
    cmp #$0009
    beq Same_Mode3_Retained_Fixture_Pixel__toggle
    bra Same_Mode3_Retained_Fixture_Pixel__plain
Same_Mode3_Retained_Fixture_Pixel__top:
    .a16
    lda.l MODE3_RF_VALUE
    cmp #$0100
    bcs Same_Mode3_Retained_Fixture_Pixel__plain
    and #$0007
    bne Same_Mode3_Retained_Fixture_Pixel__plain
    lda.l MODE3_RF_VALUE
    cmp #$0080
    bcs Same_Mode3_Retained_Fixture_Pixel__toggle
    and #$0008
    beq Same_Mode3_Retained_Fixture_Pixel__plain
Same_Mode3_Retained_Fixture_Pixel__toggle:
    .a16
    pla
    eor #$0001
    bra Same_Mode3_Retained_Fixture_Pixel__revision
Same_Mode3_Retained_Fixture_Pixel__plain:
    .a16
    pla
Same_Mode3_Retained_Fixture_Pixel__revision:
    .a16
    pha
    lda.l MODE3_RF_Y
    cmp #$00C0
    pla
    bcs Same_Mode3_Retained_Fixture_Pixel__done
    eor.l MODE3_RF_REVISION
Same_Mode3_Retained_Fixture_Pixel__done:
    .a16
    rts

; Map a dirty screen-space tile through the current retained scene transform.
; HUD rows always retain their fixed row-major IDs. Rectangle scratch remains
; owned by HandleDirty; no caller pointers or actor state enter this mapping.
Same_Mode3_Retained_MapDirtyTile:
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_Mode3_Retained_MapDirtyTile__legacy
    lda.l SAME_MODE3_WORK_Y0
    cmp #$0018
    bcs Same_Mode3_Retained_MapDirtyTile__legacy
    lda.l MODE3_R_BASE
    lsr
    lsr
    lsr
    sta.l MODE3_R_TEMP
    lda.l MODE3_R_NEXT
    lsr
    lsr
    lsr
    sec
    sbc.l MODE3_R_TEMP
    clc
    adc.l SAME_MODE3_WORK_COLUMN
Same_Mode3_Retained_MapDirtyTile__negative:
    .a16
    bpl Same_Mode3_Retained_MapDirtyTile__modulo
    clc
    adc #$0021
    bra Same_Mode3_Retained_MapDirtyTile__negative
Same_Mode3_Retained_MapDirtyTile__modulo:
    .a16
    cmp #$0021
    bcc Same_Mode3_Retained_MapDirtyTile__physical
    sec
    sbc #$0021
    bra Same_Mode3_Retained_MapDirtyTile__modulo
Same_Mode3_Retained_MapDirtyTile__physical:
    .a16
    cmp #$0020
    beq Same_Mode3_Retained_MapDirtyTile__guard
    sta.l SAME_MODE3_WORK_RUN_START
    lda.l SAME_MODE3_WORK_Y0
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_RUN_START
    rts
Same_Mode3_Retained_MapDirtyTile__guard:
    .a16
    lda.l SAME_MODE3_WORK_Y0
    clc
    adc #$0380
    rts
Same_Mode3_Retained_MapDirtyTile__legacy:
    .a16
    lda.l SAME_MODE3_WORK_Y0
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_COLUMN
    rts

; Decode a retained source column back to the existing checked-read scratch.
; Called only by its exclusive room/camera owner after foreground restoration.
; This is reuse of already validated tile data, not a new resource provider.
Same_Mode3_Retained_ReadColumn_Far:
    php
    phb
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_DELTA
    bmi Same_Mode3_Retained_ReadColumn__left
    lda.l MODE3_R_NEXT
    clc
    adc #$00FF
    bra Same_Mode3_Retained_ReadColumn__world
Same_Mode3_Retained_ReadColumn__left:
    .a16
    lda.l MODE3_R_NEXT
Same_Mode3_Retained_ReadColumn__world:
    .a16
    lsr
    lsr
    lsr
    pha
    lda.l MODE3_R_BASE
    lsr
    lsr
    lsr
    sta.l MODE3_R_TEMP
    pla
    sec
    sbc.l MODE3_R_TEMP
Same_Mode3_Retained_ReadColumn__negative:
    .a16
    bpl Same_Mode3_Retained_ReadColumn__modulo
    clc
    adc #$0021
    bra Same_Mode3_Retained_ReadColumn__negative
Same_Mode3_Retained_ReadColumn__modulo:
    .a16
    cmp #$0021
    bcc Same_Mode3_Retained_ReadColumn__physical
    sec
    sbc #$0021
    bra Same_Mode3_Retained_ReadColumn__modulo
Same_Mode3_Retained_ReadColumn__physical:
    .a16
    sta.l MODE3_R_PHYSICAL
    lda #$0000
    sta.l MODE3_R_Y
    sep #$20
    .a8
    lda #$41
    pha
    plb
Same_Mode3_Retained_ReadColumn__row:
    .a8
    rep #$20
    .a16
    ; A tile's eight planar rows are consecutive two-byte pairs. Resolve
    ; the physical shadow once per tile, including the split guard bank.
    lda.l MODE3_R_Y
    and #$0007
    beq Same_Mode3_Retained_ReadColumn__tile_row
    lda.l SAME_MODE3_WORK_SOURCE
    clc
    adc #$0002
    sta.l SAME_MODE3_WORK_SOURCE
    brl Same_Mode3_Retained_ReadColumn__load_pairs
Same_Mode3_Retained_ReadColumn__tile_row:
    .a16
    lda.l MODE3_R_Y
    lsr
    lsr
    lsr
    pha
    lda.l MODE3_R_PHYSICAL
    cmp #$0020
    beq Same_Mode3_Retained_ReadColumn__guard
    pla
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l MODE3_R_PHYSICAL
    bra Same_Mode3_Retained_ReadColumn__tile
Same_Mode3_Retained_ReadColumn__guard:
    .a16
    pla
    clc
    adc #$0380
Same_Mode3_Retained_ReadColumn__tile:
    .a16
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_Retained_ShadowAddress
Same_Mode3_Retained_ReadColumn__load_pairs:
    .a16
    lda.l SAME_MODE3_WORK_SOURCE
    tax
    lda.l SAME_MODE3_WORK_DESC_TYPE
    and #$00FF
    cmp #$0040
    beq Same_Mode3_Retained_ReadColumn__bank40
    lda.l $410000,x
    sta.l SAME_MODE3_WORK_X0+0
    lda.l $410010,x
    sta.l SAME_MODE3_WORK_X0+2
    lda.l $410020,x
    sta.l SAME_MODE3_WORK_X0+4
    lda.l $410030,x
    sta.l SAME_MODE3_WORK_X0+6
    bra Same_Mode3_Retained_ReadColumn__planes
Same_Mode3_Retained_ReadColumn__bank40:
    .a16
    lda.l $400000,x
    sta.l SAME_MODE3_WORK_X0+0
    lda.l $400010,x
    sta.l SAME_MODE3_WORK_X0+2
    lda.l $400020,x
    sta.l SAME_MODE3_WORK_X0+4
    lda.l $400030,x
    sta.l SAME_MODE3_WORK_X0+6
Same_Mode3_Retained_ReadColumn__planes:
    .a16
    lda.l MODE3_R_Y
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    ; Fixed eight-pixel transpose. Word plane loads above preserve plane
    ; order; no per-pixel width switch, loop counter, or branch is needed.
    ; Pixel 0, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 1, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 2, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 3, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 4, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 5, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 6, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    ; Pixel 7, left to right.
    lda #$00
    asl.w Same_Mode3_RowPlanes+7
    rol
    asl.w Same_Mode3_RowPlanes+6
    rol
    asl.w Same_Mode3_RowPlanes+5
    rol
    asl.w Same_Mode3_RowPlanes+4
    rol
    asl.w Same_Mode3_RowPlanes+3
    rol
    asl.w Same_Mode3_RowPlanes+2
    rol
    asl.w Same_Mode3_RowPlanes+1
    rol
    asl.w Same_Mode3_RowPlanes+0
    rol
    sta.l SAME_BWRAM_LIVE_ROOM_PENDING,x
    inx
    rep #$20
    .a16
    lda.l MODE3_R_Y
    inc
    sta.l MODE3_R_Y
    cmp #$00C0
    bcs Same_Mode3_Retained_ReadColumn__done
    brl Same_Mode3_Retained_ReadColumn__row
Same_Mode3_Retained_ReadColumn__done:
    .a16
    lda #SAME_BWRAM_LIVE_ROOM_PENDING&$FFFF
    sta.l MODE3_R_INPUT
    lda #$0000
    sta.l MODE3_R_TOP
    sta.l MODE3_R_SOURCE_Y
    lda #$00C0
    sta.l MODE3_R_HEIGHT
    plb
    plp
    rtl

; Populate only the newly exposed INDEX8 edge from the verified input strip.
; It can be MSU input or a decoded retained column; ownership is identical.
Same_Mode3_Retained_FillEdge_Far:
    php
    phb
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_DELTA
    bmi Same_Mode3_Retained_FillEdge__left
    sta.l SAME_MODE3_WORK_LIMIT
    lda #$0100
    sec
    sbc.l SAME_MODE3_WORK_LIMIT
    sta.l MODE3_R_X
    bra Same_Mode3_Retained_FillEdge__begin
Same_Mode3_Retained_FillEdge__left:
    .a16
    eor #$FFFF
    inc
    sta.l SAME_MODE3_WORK_LIMIT
    lda #$0000
    sta.l MODE3_R_X
Same_Mode3_Retained_FillEdge__begin:
    .a16
    lda #$0000
    sta.l MODE3_R_Y
Same_Mode3_Retained_FillEdge__row:
    .a16
    lda.l MODE3_R_Y
    xba
    clc
    adc.l MODE3_R_X
    tax
    jsl Same_Mode3_MapSurfaceX_Far
    txa
    sta.l SAME_MODE3_WORK_SOURCE
    lda.l MODE3_R_Y
    sec
    sbc.l MODE3_R_TOP
    bcc Same_Mode3_Retained_FillEdge__zero
    cmp.l MODE3_R_HEIGHT
    bcs Same_Mode3_Retained_FillEdge__zero
    clc
    adc.l MODE3_R_SOURCE_Y
    asl
    asl
    asl
    clc
    adc.l MODE3_R_INPUT
    sta.l MODE3_R_TEMP
    lda.l MODE3_R_X
    clc
    adc.l MODE3_R_NEXT
    and #$0007
    clc
    adc.l MODE3_R_TEMP
    tax
    lda.l SAME_MODE3_WORK_SOURCE
    clc
    adc #$2000
    tay
    ; Begin limits each step to the next eight-pixel boundary. Thus this
    ; physical run cannot cross a row (ending exactly at 256 is legal).
    lda.l SAME_MODE3_WORK_LIMIT
    dec
    mvn $40,$40
    bra Same_Mode3_Retained_FillEdge__next
Same_Mode3_Retained_FillEdge__zero:
    .a16
    lda.l SAME_MODE3_WORK_SOURCE
    tax
    lda.l SAME_MODE3_WORK_LIMIT
    tay
    sep #$20
    .a8
    lda #$00
Same_Mode3_Retained_FillEdge__clear:
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    dey
    bne Same_Mode3_Retained_FillEdge__clear
Same_Mode3_Retained_FillEdge__next:
    rep #$20
    .a16
    lda.l MODE3_R_Y
    inc
    sta.l MODE3_R_Y
    cmp #$00C0
    bcs Same_Mode3_Retained_FillEdge__done
    brl Same_Mode3_Retained_FillEdge__row
Same_Mode3_Retained_FillEdge__done:
    .a16
    plb
    plp
    rtl

; Preserve restoration in physical characters before any pixels leave INDEX8.
; The facade's existing damage rectangle remains immutable during this leaf.
; Pending characters join the same eventual camera PRESENT, never an early DMA.
MODE3_R_DAMAGE_X = SAME_BWRAM_VIDEO_SURFACE_STATE+$34
MODE3_R_DAMAGE_Y = SAME_BWRAM_VIDEO_SURFACE_STATE+$36
MODE3_R_DAMAGE_W = SAME_BWRAM_VIDEO_SURFACE_STATE+$38
MODE3_R_DAMAGE_H = SAME_BWRAM_VIDEO_SURFACE_STATE+$3A
; A validated restoration rectangle can be encoded once, after composition,
; if none of its scene pixels leave the circular INDEX8 viewport. HUD pixels
; never move. Edge-evicted pixels still require immediate planar preservation.
; Caller owns an idle surface; A16/I16. C clear means defer safely.
Same_Mode3_Retained_DamageStaysVisible:
    .a16
    .i16
    lda.l MODE3_R_DAMAGE_W
    beq Same_Mode3_Retained_DamageStaysVisible__yes
    lda.l MODE3_R_DAMAGE_H
    beq Same_Mode3_Retained_DamageStaysVisible__yes
    lda.l MODE3_R_DAMAGE_Y
    cmp #$00C0
    bcs Same_Mode3_Retained_DamageStaysVisible__yes
    lda.l MODE3_R_DAMAGE_X
    sec
    sbc.l MODE3_R_DELTA
    cmp #$0100
    bcs Same_Mode3_Retained_DamageStaysVisible__no
    clc
    adc.l MODE3_R_DAMAGE_W
    cmp #$0101
    bcs Same_Mode3_Retained_DamageStaysVisible__no
Same_Mode3_Retained_DamageStaysVisible__yes:
    clc
    rts
Same_Mode3_Retained_DamageStaysVisible__no:
    sec
    rts

; Surface facade may defer sparse coverage only under the same lifetime proof
; used by the dense preservation path. A16/I16, C clear means still visible.
Same_Mode3_Retained_DamageStaysVisible_Far:
    .a16
    .i16
    jsr Same_Mode3_Retained_DamageStaysVisible
    rtl

Same_Mode3_Retained_FlushDamage_Far:
    php
    cld
    rep #$30
    .a16
    .i16
    jsr Same_Mode3_Retained_DamageStaysVisible
    bcs Same_Mode3_Retained_FlushDamage__evicted
    ; Mark old physical slots under CURRENT, before advancing the ring.
    ; Their final composition is encoded through the new origin once.
    lda.l MODE3_R_NEXT
    pha
    lda.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    jsl Same_Mode3_Retained_MarkDamage_Far
    rep #$30
    .a16
    .i16
    pla
    sta.l MODE3_R_NEXT
    plp
    rtl
Same_Mode3_Retained_FlushDamage__evicted:
    .a16
    .i16
    lda.l MODE3_R_NEXT
    pha
    lda.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    lda.l MODE3_R_DAMAGE_W
    beq Same_Mode3_Retained_FlushDamage__done
    lda.l MODE3_R_DAMAGE_H
    beq Same_Mode3_Retained_FlushDamage__done
    lda.l MODE3_R_DAMAGE_Y
    lsr
    lsr
    lsr
    tay
Same_Mode3_Retained_FlushDamage__row:
    .a16
    lda.l MODE3_R_DAMAGE_X
    lsr
    lsr
    lsr
    tax
Same_Mode3_Retained_FlushDamage__column:
    .a16
    phx
    phy
    tya
    sta.l SAME_MODE3_WORK_Y0
    txa
    sta.l SAME_MODE3_WORK_COLUMN
    jsr Same_Mode3_Retained_MapDirtyTile
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_EncodeViewportTile
    jsr Same_Mode3_CommitViewportTile
    rep #$30
    .a16
    .i16
    ply
    plx
    inx
    lda.l MODE3_R_CURRENT
    and #$0007
    cpy #$0018
    bcc Same_Mode3_Retained_FlushDamage__scene
    lda #$0000
Same_Mode3_Retained_FlushDamage__scene:
    .a16
    clc
    adc.l MODE3_R_DAMAGE_X
    clc
    adc.l MODE3_R_DAMAGE_W
    dec
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_TEMP
    txa
    cmp.l SAME_MODE3_WORK_TEMP
    bcc Same_Mode3_Retained_FlushDamage__column
    beq Same_Mode3_Retained_FlushDamage__column
    iny
    lda.l MODE3_R_DAMAGE_Y
    clc
    adc.l MODE3_R_DAMAGE_H
    dec
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_TEMP
    tya
    cmp.l SAME_MODE3_WORK_TEMP
    bcc Same_Mode3_Retained_FlushDamage__row
    beq Same_Mode3_Retained_FlushDamage__row
Same_Mode3_Retained_FlushDamage__done:
    .a16
    pla
    sta.l MODE3_R_NEXT
    plp
    rtl

; Accumulate the facade's new foreground damage using the normal packet
; decoder. This does not publish a generation or touch PPU state.
Same_Mode3_Retained_MarkDamage_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_DAMAGE_W
    beq Same_Mode3_Retained_MarkDamage__done
    lda.l MODE3_R_DAMAGE_H
    beq Same_Mode3_Retained_MarkDamage__done
    jsl Same_Mode3_Event_Stage_Far
    rep #$20
    .a16
    lda.l MODE3_R_DAMAGE_X
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l MODE3_R_DAMAGE_Y
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    lda.l MODE3_R_DAMAGE_W
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda.l MODE3_R_DAMAGE_H
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    jsr Same_Mode3_HandleDirty
Same_Mode3_Retained_MarkDamage__done:
    .a16
    plp
    rtl

; Release CPU-side guard storage for an incoming room only after all queued
; work is complete. The old PPU scroll remains installed; NMI ignores the
; aliased transaction storage until a new cold generation is ready.
Same_Mode3_Retained_Retire_Far:
    php
    rep #$20
    .a16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0001
    bne Same_Mode3_Retained_Retire__done
    lda.l SAME_MODE3_CONTROL_STATE
    and #$00FF
    cmp #SAME_MODE3_STATE_IDLE
    bne Same_Mode3_Retained_Retire__wait
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    ora.l SAME_EVENT_COUNT
    ora.l SAME_DMA_PENDING
    bne Same_Mode3_Retained_Retire__wait
    sep #$20
    .a8
    lda #$02
    sta.l MODE3_R_ACTIVE
Same_Mode3_Retained_Retire__done:
    plp
    clc
    rtl
Same_Mode3_Retained_Retire__wait:
    plp
    sec
    rtl

; Called after the incoming palette no longer needs its legacy staging alias.
; Two bounded immutable map DMAs precede the normal cold character conversion.
Same_Mode3_Retained_Cold_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l MODE3_R_ACTIVE
    and #$00FF
    cmp #$0002
    beq Same_Mode3_Retained_Cold__needed
    plp
    clc
    rtl
Same_Mode3_Retained_Cold__needed:
    .a16
    lda.l SAME_DMA_PENDING
    cmp #SAME_DMA_QUEUE_SLOTS-1
    bcc Same_Mode3_Retained_Cold__capacity
    plp
    sec
    rtl
Same_Mode3_Retained_Cold__capacity:
    .a16
    lda #Same_Mode3_RetainedTilemap
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$F000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcc Same_Mode3_Retained_Cold__first
    plp
    sec
    rtl
Same_Mode3_Retained_Cold__first:
    .a8
    rep #$20
    .a16
    lda #Same_Mode3_RetainedTilemap
    clc
    adc #$0800
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$F800
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcc Same_Mode3_Retained_Cold__queued
    plp
    sec
    rtl
Same_Mode3_Retained_Cold__queued:
    .a8
    rep #$20
    .a16
    lda #$0000
    sta.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    sta.l MODE3_R_BASE
    lda #$FFFF
    sta.l MODE3_R_COLUMN
    lda #$0001
    sta.l MODE3_R_VALIDATED
    sep #$20
    .a8
    lda #$01
    sta.l MODE3_R_PHASE
    lda #$03
    sta.l MODE3_R_ACTIVE
    plp
    clc
    rtl

; Cancel only an uncomposed camera ticket after its provider request drains.
; Character writes and DMA have not begun. Remove this ticket's candidates,
; retain unrelated dirty work and the committed viewport. Never cancel a
; queued PRESENT or discard a publication waiting for NMI.
Same_Mode3_Retained_Abort_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    and #$00FF
    bne Same_Mode3_Retained_Abort__wait
    lda.l SAME_EVENT_COUNT
    bne Same_Mode3_Retained_Abort__wait
    lda.l MODE3_R_PHASE
    and #$00FF
    beq Same_Mode3_Retained_Abort__done
    cmp #$0001
    bne Same_Mode3_Retained_Abort__wait
    lda.l MODE3_R_COLUMN
    cmp #$FFFF
    beq Same_Mode3_Retained_Abort__clear
    ldy #$0000
Same_Mode3_Retained_Abort__row:
    .a16
    lda.l MODE3_R_PHYSICAL
    cmp #$0020
    beq Same_Mode3_Retained_Abort__guard
    tya
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l MODE3_R_PHYSICAL
    bra Same_Mode3_Retained_Abort__tile
Same_Mode3_Retained_Abort__guard:
    .a16
    tya
    clc
    adc #$0380
Same_Mode3_Retained_Abort__tile:
    .a16
    phy
    jsr Same_Mode3_ClearCandidateTile
    rep #$30
    .a16
    .i16
    ply
    iny
    cpy #$0018
    bcc Same_Mode3_Retained_Abort__row
Same_Mode3_Retained_Abort__clear:
    .a16
    lda.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    lda #$0000
    sta.l MODE3_R_PHASE
    sta.l MODE3_R_VALIDATED
Same_Mode3_Retained_Abort__done:
    plp
    clc
    rtl
Same_Mode3_Retained_Abort__wait:
    plp
    sec
    rtl

; Original fixture foreground uses ordinary damage/convert/DMA contracts.
; A world-anchored opaque-zero patch scrolls; a fixed cursor is restored into
; retained characters before reuse and repainted after the INDEX8 move.
Same_Mode3_Retained_Fixture_Foreground:
    .a16
    lda #$0001
    sta.l MODE3_RF_FOREGROUND
    lda #80
    sta.l MODE3_RF_Y
Same_Mode3_Retained_Fixture_Foreground__row:
    .a16
    lda #100
    sta.l MODE3_RF_X
Same_Mode3_Retained_Fixture_Foreground__pixel:
    .a16
    lda.l MODE3_RF_X
    jsr Same_Mode3_Retained_Fixture_Pixel
    pha
    lda.l MODE3_RF_Y
    xba
    clc
    adc.l MODE3_RF_X
    tax
    pla
    sep #$20
    .a8
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    sta.l SAME_BWRAM_SURFACE_BASE,x
    plx
    rep #$20
    .a16
    lda.l MODE3_RF_X
    inc
    sta.l MODE3_RF_X
    cmp #112
    bcc Same_Mode3_Retained_Fixture_Foreground__pixel
    lda.l MODE3_RF_Y
    inc
    sta.l MODE3_RF_Y
    cmp #96
    bcc Same_Mode3_Retained_Fixture_Foreground__row
    lda #100
    sta.l MODE3_R_DAMAGE_X
    lda #80
    sta.l MODE3_R_DAMAGE_Y
    lda #12
    sta.l MODE3_R_DAMAGE_W
    lda #16
    sta.l MODE3_R_DAMAGE_H
    jsl Same_Mode3_Retained_MarkDamage_Far
    lda #$0001
    jsr Same_Mode3_Retained_Fixture_Cursor
    jsl Same_Mode3_Retained_MarkDamage_Far
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    inc
    sta.l MODE3_RF_GENERATION
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0003
    sta.l MODE3_RF_COMMAND
    rts

Same_Mode3_Retained_Fixture_Cursor:
    .a16
    pha
    lda #40
    sta.l MODE3_RF_Y
Same_Mode3_Retained_Fixture_Cursor__row:
    .a16
    lda #44
    sta.l MODE3_RF_X
Same_Mode3_Retained_Fixture_Cursor__pixel:
    .a16
    lda 1,s
    beq Same_Mode3_Retained_Fixture_Cursor__restore
    lda #$00F0
    bra Same_Mode3_Retained_Fixture_Cursor__write
Same_Mode3_Retained_Fixture_Cursor__restore:
    .a16
    lda.l MODE3_RF_X
    clc
    adc.l MODE3_R_CURRENT
    jsr Same_Mode3_Retained_Fixture_Pixel
Same_Mode3_Retained_Fixture_Cursor__write:
    .a16
    pha
    lda.l MODE3_RF_Y
    xba
    clc
    adc.l MODE3_RF_X
    tax
    pla
    sep #$20
    .a8
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    sta.l SAME_BWRAM_SURFACE_BASE,x
    plx
    rep #$20
    .a16
    lda.l MODE3_RF_X
    inc
    sta.l MODE3_RF_X
    cmp #48
    bcc Same_Mode3_Retained_Fixture_Cursor__pixel
    lda.l MODE3_RF_Y
    inc
    sta.l MODE3_RF_Y
    cmp #46
    bcc Same_Mode3_Retained_Fixture_Cursor__row
    lda #44
    sta.l MODE3_R_DAMAGE_X
    lda #40
    sta.l MODE3_R_DAMAGE_Y
    lda #4
    sta.l MODE3_R_DAMAGE_W
    lda #6
    sta.l MODE3_R_DAMAGE_H
    pla
    rts

; Native failure controls use only this original fixture's command protocol.
; The observer never writes backend state. No command is a gameplay API.
Same_Mode3_Retained_Fixture_Admission:
    .a16
    lda.l MODE3_R_CURRENT
    inc
    jsl Same_Mode3_Retained_Begin_Far
    bcc Same_Mode3_Retained_Fixture_Admission__begun
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Admission__begun:
    .a16
    lda.l MODE3_R_CURRENT
    inc
    jsl Same_Mode3_Retained_Begin_Far
    bcs Same_Mode3_Retained_Fixture_Admission__refused
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Admission__refused:
    .a16
    jsl Same_Mode3_Retained_Abort_Far
    bcc Same_Mode3_Retained_Fixture_Admission__aborted
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Admission__aborted:
    .a16
    jmp Same_Mode3_Retained_Fixture__success

Same_Mode3_Retained_Fixture_Stale:
    .a16
    lda.l MODE3_R_CURRENT
    sta.l MODE3_RF_LEFT
    clc
    adc #$0008
    sta.l MODE3_R_NEXT
    lda.l SAME_BWRAM_CONTROL_PENDING_GENERATION
    sta.l MODE3_R_GENERATION
    lda.l SAME_MODE3_CONTROL_PENDING_GENERATION_HI
    inc ; stale high word with matching low word must not publish
    sta.l MODE3_R_GENERATION_HI
    sep #$20
    .a8
    lda #$01
    sta.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    lda #SAME_MODE3_STATE_COMPLETE
    sta.l SAME_MODE3_CONTROL_STATE
    lda #$02
    sta.l MODE3_R_PHASE
    rep #$20
    .a16
    jmp Same_Mode3_Retained_Fixture__success

Same_Mode3_Retained_Fixture_Recover:
    .a16
    lda.l MODE3_R_CURRENT
    cmp.l MODE3_RF_LEFT
    beq Same_Mode3_Retained_Fixture_Recover__unchanged
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Recover__unchanged:
    .a16
    sta.l MODE3_R_NEXT
    sep #$20
    .a8
    lda #$00
    sta.l MODE3_R_PHASE
    sta.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    lda #SAME_MODE3_STATE_IDLE
    sta.l SAME_MODE3_CONTROL_STATE
    rep #$20
    .a16
    jmp Same_Mode3_Retained_Fixture__success

Same_Mode3_Retained_Fixture_Cold:
    .a16
    jsl Same_Mode3_Retained_Retire_Far
    bcc Same_Mode3_Retained_Fixture_Cold__retired
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Cold__retired:
    .a16
    jsl Same_Mode3_Retained_Cold_Far
    bcc Same_Mode3_Retained_Fixture_Cold__ready
    jmp Same_Mode3_Retained_Fixture__error
Same_Mode3_Retained_Fixture_Cold__ready:
    .a16
    lda #$0000
    sta.l MODE3_RF_FOREGROUND
    sta.l MODE3_RF_REVISION
    sta.l MODE3_RF_Y
Same_Mode3_Retained_Fixture_Cold__row:
    .a16
    lda #$0000
    sta.l MODE3_RF_X
Same_Mode3_Retained_Fixture_Cold__pixel:
    .a16
    lda.l MODE3_RF_X
    jsr Same_Mode3_Retained_Fixture_Pixel
    pha
    lda.l MODE3_RF_Y
    xba
    clc
    adc.l MODE3_RF_X
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$20
    .a16
    lda.l MODE3_RF_X
    inc
    sta.l MODE3_RF_X
    cmp #$0100
    bcc Same_Mode3_Retained_Fixture_Cold__pixel
    lda.l MODE3_RF_Y
    inc
    sta.l MODE3_RF_Y
    cmp #$00E0
    bcc Same_Mode3_Retained_Fixture_Cold__row
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sta.l SAME_MODE3_WORK_X1
    lda #$00E0
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    inc
    sta.l MODE3_RF_GENERATION
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0003
    sta.l MODE3_RF_COMMAND
    rts

; Full source-image replacement at a scrolled origin, as used for changed
; room objects. Stage linear pixels in the existing shadow alias, then use
; the same backend pixel mapping as the checked room producer. No
; renderer output or cache state is injected by the native observer.
Same_Mode3_Retained_Fixture_Refresh:
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l MODE3_RF_START_FRAME
    lda.l MODE3_RF_REVISION
    eor #$0040
    sta.l MODE3_RF_REVISION
    lda #$0000
    sta.l MODE3_RF_Y
Same_Mode3_Retained_Fixture_Refresh__row:
    .a16
    lda #$0000
    sta.l MODE3_RF_X
Same_Mode3_Retained_Fixture_Refresh__pixel:
    .a16
    lda.l MODE3_RF_X
    clc
    adc.l MODE3_R_CURRENT
    jsr Same_Mode3_Retained_Fixture_Pixel
    pha
    lda.l MODE3_RF_Y
    xba
    clc
    adc.l MODE3_RF_X
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_BWRAM_TILE_SHADOW_BASE,x
    rep #$20
    .a16
    lda.l MODE3_RF_X
    inc
    sta.l MODE3_RF_X
    cmp #$0100
    bcc Same_Mode3_Retained_Fixture_Refresh__pixel
    lda.l MODE3_RF_Y
    inc
    sta.l MODE3_RF_Y
    cmp #$00C0
    bcc Same_Mode3_Retained_Fixture_Refresh__row
    ldx #$0000
    sep #$20
    .a8
Same_Mode3_Retained_Fixture_Refresh__copy:
    .a8
    lda.l SAME_BWRAM_TILE_SHADOW_BASE,x
    phx
    jsl Same_Mode3_MapSurfaceX_Far
    sta.l SAME_BWRAM_SURFACE_BASE,x
    plx
    inx
    cpx #$C000
    bcc Same_Mode3_Retained_Fixture_Refresh__copy
    ; This backend-only fixture has no SCUMM room personality; exercise the
    ; same invalidation leaves used by its surface replacement facade.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_BWRAM_CONTROL_TILE_VALID
    jsl Same_Mode3_Retained_InvalidateCoverage_Far
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sta.l SAME_MODE3_WORK_X1
    lda #$00E0
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    inc
    sta.l MODE3_RF_GENERATION
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0003
    sta.l MODE3_RF_COMMAND
    rts
