; Independent cursor underlay with explicit source coverage. No glyph, controller, ROM or PPU policy.
; Generated owner: $40:0620..073F (32-byte header/work + 256 saved pixels).
; +00 magic C9 commits LAST, +01 retained-damage-valid, +02 room u16,
; +04 installed generation, +06 packed destination, +08 width, +0A height,
; +0C payload area, +0E reserved. +10..1F is private synchronous scratch.
; Pixel payload +20..11F is tightly packed row-major (no surface stride).
; The independent engine owner begins at $40:0740 and is never touched here.
;
; Capture: A16=y*256+x, X16=width 1..16, Y16=height 1..16; caller clips.
; Restore consumes magic but retains bounds for Merge after actor restoration.
; Capture/Restore/Merge union DAMAGE, never reset it. Empty restore is a no-op.
; Capture rejects an unconsumed journal. Invalid arguments/malformed journal
; fail before surface/persistent-journal writes; private scratch may change.
; Stale identity is discarded without restoring. Invalidate on cold reset and
; BEFORE same-room background replacement (room generation may not change).
; All entries preserve P/A/X/Y/DB except carry: clear success, set failure.
; Busy Capture/Restore retain committed journal and damage. No publication.
SAME_VIDEO_CURSOR_MAGIC = $C9
SAME_VIDEO_CURSOR_HEADER_SIZE = $0020
SAME_VIDEO_CURSOR_PAYLOAD_SIZE = $0100
SAME_VIDEO_CURSOR_PIXELS = SAME_VIDEO_CURSOR_UNDERLAY+$20
SAME_VIDEO_CURSOR_PIXELS_LOW = SAME_VIDEO_CURSOR_PIXELS & $FFFF
SAME_VIDEO_CURSOR_WORK_DEST = SAME_VIDEO_CURSOR_UNDERLAY+$10
SAME_VIDEO_CURSOR_WORK_WIDTH = SAME_VIDEO_CURSOR_UNDERLAY+$12
SAME_VIDEO_CURSOR_WORK_HEIGHT = SAME_VIDEO_CURSOR_UNDERLAY+$14
SAME_VIDEO_CURSOR_WORK_AREA = SAME_VIDEO_CURSOR_UNDERLAY+$16
SAME_VIDEO_CURSOR_WORK_SURFACE = SAME_VIDEO_CURSOR_UNDERLAY+$18
SAME_VIDEO_CURSOR_WORK_PIXEL = SAME_VIDEO_CURSOR_UNDERLAY+$1A
SAME_VIDEO_CURSOR_WORK_COLUMN = SAME_VIDEO_CURSOR_UNDERLAY+$1C
SAME_VIDEO_CURSOR_WORK_ROWS = SAME_VIDEO_CURSOR_UNDERLAY+$1E

; Camera-only callers have just exchanged a validated cursor journal. Preserve
; the complete damage rectangle, but mark only tiles touched by source coverage.
; This does not clear any existing candidate: actors/text/reused columns retain
; independent invalidation. Nonaligned cameras keep the conservative path.
Same_VideoSurface_FlushCursorCameraDamage_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    jsl Same_Mode3_Retained_DamageStaysVisible_Far
    bcc Same_VideoSurface_FlushCursorCameraDamage__defer
    jsl Same_Mode3_Retained_FlushDamage_Far
    bra Same_VideoSurface_FlushCursorCameraDamage__done
Same_VideoSurface_FlushCursorCameraDamage__defer:
    .a16
    lda.l MODE3_R_NEXT
    pha
    lda.l MODE3_R_CURRENT
    sta.l MODE3_R_NEXT
    jsl Same_VideoSurface_MarkCursorCoverage_Far
    pla
    sta.l MODE3_R_NEXT
Same_VideoSurface_FlushCursorCameraDamage__done:
    .a16
    ply
    plx
    pla
    plp
    rtl

Same_VideoSurface_MarkCursorCoverage_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    beq Same_VideoSurface_MarkCursorCoverage__empty
    cmp #$0011
    bcs Same_VideoSurface_MarkCursorCoverage__dense
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    beq Same_VideoSurface_MarkCursorCoverage__empty
    cmp #$0011
    bcs Same_VideoSurface_MarkCursorCoverage__dense
    lda.l MODE3_R_NEXT
    and #$0007
    beq Same_VideoSurface_MarkCursorCoverage__aligned
Same_VideoSurface_MarkCursorCoverage__dense:
    .a16
    jsl Same_Mode3_Retained_MarkDamage_Far
Same_VideoSurface_MarkCursorCoverage__empty:
    .a16
    ply
    plx
    pla
    plp
    rtl
Same_VideoSurface_MarkCursorCoverage__aligned:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    pha
    and #$FFF8
    sta.l SAME_VIDEO_CURSOR_WORK_DEST
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    and #$0007
    asl
    sta.l SAME_VIDEO_CURSOR_WORK_PIXEL
    asl
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_PIXEL
    sta.l SAME_VIDEO_CURSOR_WORK_PIXEL
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    pha
    sta.l SAME_VIDEO_CURSOR_WORK_SURFACE
    and #$FFF8
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    pha
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    pha
    sta.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    lda #$0008
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda #$0000
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
Same_VideoSurface_MarkCursorCoverage__row:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    asl
    cmp #$0010
    bcc Same_VideoSurface_MarkCursorCoverage__low
    sec
    sbc #$0010
    tax
    lda.l SAME_VIDEO_CURSOR_COVERAGE_HI,x
    bra Same_VideoSurface_MarkCursorCoverage__mask
Same_VideoSurface_MarkCursorCoverage__low:
    .a16
    tax
    lda.l SAME_VIDEO_CURSOR_COVERAGE_LO,x
Same_VideoSurface_MarkCursorCoverage__mask:
    .a16
    ora.l SAME_VIDEO_CURSOR_WORK_AREA
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    inc
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    cmp.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    beq Same_VideoSurface_MarkCursorCoverage__group
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_SURFACE
    and #$0007
    bne Same_VideoSurface_MarkCursorCoverage__row
Same_VideoSurface_MarkCursorCoverage__group:
    .a16
    ; Dense-compatible captures may leave coverage bits beyond clipped width.
    ; The already validated journal bounds those bits before tile admission.
    lda.l SAME_VIDEO_CURSOR_UNDERLAY+$08
    asl
    tax
    lda.l Same_VideoSurface_CursorWidthMasks,x
    and.l SAME_VIDEO_CURSOR_WORK_AREA
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_CURSOR_WORK_PIXEL
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    lda #$0003
    sta.l SAME_VIDEO_CURSOR_WORK_WIDTH
Same_VideoSurface_MarkCursorCoverage__tile:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_COLUMN
    tax
    lda.l Same_VideoSurface_CursorTileMasks,x
    and.l SAME_VIDEO_CURSOR_WORK_AREA
    beq Same_VideoSurface_MarkCursorCoverage__next_tile
    jsl Same_Mode3_Retained_MarkDamage_Far
    rep #$30
    .a16
    .i16
Same_VideoSurface_MarkCursorCoverage__next_tile:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc #$0008
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_CURSOR_WORK_COLUMN
    inc
    inc
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_WIDTH
    bne Same_VideoSurface_MarkCursorCoverage__tile
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    cmp.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    beq Same_VideoSurface_MarkCursorCoverage__restore
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc #$0008
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda #$0000
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    brl Same_VideoSurface_MarkCursorCoverage__row
Same_VideoSurface_MarkCursorCoverage__restore:
    .a16
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    pla
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    ply
    plx
    pla
    plp
    rtl

; Left-aligned 16-bit source coverage split across at most three screen tiles.
; Rows are grouped separately; clipping is inherited from validated capture.
Same_VideoSurface_CursorTileMasks:
    .word $FF00,$00FF,$0000, $FE00,$01FE,$0001
    .word $FC00,$03FC,$0003, $F800,$07F8,$0007
    .word $F000,$0FF0,$000F, $E000,$1FE0,$001F
    .word $C000,$3FC0,$003F, $8000,$7F80,$007F
Same_VideoSurface_CursorWidthMasks:
    .word $0000,$8000,$C000,$E000,$F000,$F800,$FC00,$FE00
    .word $FF00,$FF80,$FFC0,$FFE0,$FFF0,$FFF8,$FFFC,$FFFE,$FFFF

Same_VideoSurface_CaptureCursorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sta.l SAME_VIDEO_CURSOR_WORK_DEST
    txa
    sta.l SAME_VIDEO_CURSOR_WORK_WIDTH
    tya
    sta.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    jsr Same_VideoSurface_Cursor_Validate
    bcc Same_VideoSurface_Cursor_Capture__valid
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Capture__valid:
    .a16
    sep #$20
    .a8
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    cmp #SAME_VIDEO_CURSOR_MAGIC
    bne Same_VideoSurface_Cursor_Capture__empty
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Capture__empty:
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Cursor_Capture__writable
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Capture__writable:
    .a8
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$0E
    lda.l SAME_VIDEO_SURFACE_ROOM
    and #$00FF
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$02
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$04
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$06
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$08
    lda.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$0A
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$0C
    ; Dense compatibility default; the producer may narrow each row before
    ; drawing. Coverage is not inferred by comparing colors to the background.
    ldx #$0000
    lda #$FFFF
Same_VideoSurface_Cursor_Capture__coverage:
    .a16
    .i16
    sta.l SAME_VIDEO_CURSOR_COVERAGE_LO,x
    sta.l SAME_VIDEO_CURSOR_COVERAGE_HI,x
    inx
    inx
    cpx #$0010
    bcc Same_VideoSurface_Cursor_Capture__coverage
    jsr Same_VideoSurface_Cursor_StartCopy
Same_VideoSurface_Cursor_Capture__pixel:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_SURFACE
    tax
    sep #$20
    .a8
    jsl Same_VideoSurface_ReadIndexedPixel_Far
    pha
    rep #$20
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_PIXEL
    tax
    sep #$20
    .a8
    pla
    sta.l SAME_VIDEO_CURSOR_PIXELS,x
    rep #$20
    .a16
    jsr Same_VideoSurface_Cursor_NextPixel
    bcc Same_VideoSurface_Cursor_Capture__pixel
    jsr Same_VideoSurface_Cursor_UnionDamage
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_CURSOR_UNDERLAY+$01
    lda #SAME_VIDEO_CURSOR_MAGIC
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
    jmp Same_VideoSurface_Cursor_Success

 ; A16: left-aligned opaque bits; X16: row relative to clipped journal.
; Called after Capture and before drawing. Color zero remains fully opaque.
Same_VideoSurface_SetCursorCoverageRow_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    txa
    cmp #$0010
    bcs Same_VideoSurface_Cursor_Coverage__bad
    cmp.l SAME_VIDEO_CURSOR_UNDERLAY+$0A
    bcs Same_VideoSurface_Cursor_Coverage__bad
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    and #$00FF
    cmp #SAME_VIDEO_CURSOR_MAGIC
    bne Same_VideoSurface_Cursor_Coverage__bad
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_VideoSurface_Cursor_Coverage__bad
    rep #$20
    .a16
    txa
    asl
    cmp #$0010
    bcc Same_VideoSurface_Cursor_Coverage__low
    sec
    sbc #$0010
    tax
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    sta.l SAME_VIDEO_CURSOR_COVERAGE_HI,x
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Coverage__low:
    .a16
    tax
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    sta.l SAME_VIDEO_CURSOR_COVERAGE_LO,x
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Coverage__bad:
    jmp Same_VideoSurface_Cursor_Failure

Same_VideoSurface_ExchangeCursorUnderlay_Far:
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
    bra Same_VideoSurface_RestoreCursorUnderlay__common
Same_VideoSurface_RestoreCursorUnderlay_Far:
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
Same_VideoSurface_RestoreCursorUnderlay__common:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sep #$20
    .a8
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    cmp #SAME_VIDEO_CURSOR_MAGIC
    beq Same_VideoSurface_Cursor_Restore__committed
    cmp #$CB
    bne Same_VideoSurface_Cursor_Restore__not_committed
    lda.l MODE3_R_EXCHANGE
    bne Same_VideoSurface_Cursor_Restore__committed
Same_VideoSurface_Cursor_Restore__not_committed:
    .a8
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Restore__committed:
    .a8
    rep #$20
    .a16
    jsr Same_VideoSurface_Cursor_Identity
    bcc Same_VideoSurface_Cursor_Restore__identity
    jmp Same_VideoSurface_Cursor_Discard
Same_VideoSurface_Cursor_Restore__identity:
    .a16
    jsr Same_VideoSurface_Cursor_LoadValidate
    bcc Same_VideoSurface_Cursor_Restore__valid
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Restore__valid:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_VideoSurface_Cursor_Restore__writable
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Restore__writable:
    .a16
    jsr Same_VideoSurface_Cursor_StartCopy
    ; The complete logical rectangle and journal were validated above.
    ; Map once per row, then exchange bounded physical pixels directly.
    ; The circular scene wraps within a row; fixed HUD rows never wrap.
    ; DBR=$40 permits indexed-Y journal access without a long-Y instruction.
    sep #$20
    .a8
    lda #$40
    pha
    plb
    rep #$30
    .a16
    .i16
    ldy #$0000
Same_VideoSurface_Cursor_Restore__row:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    sec
    sbc.l SAME_VIDEO_CURSOR_WORK_ROWS
    asl
    cmp #$0010
    bcc Same_VideoSurface_Cursor_Restore__coverage_low
    sec
    sbc #$0010
    tax
    lda.l SAME_VIDEO_CURSOR_COVERAGE_HI,x
    bra Same_VideoSurface_Cursor_Restore__coverage_ready
Same_VideoSurface_Cursor_Restore__coverage_low:
    .a16
    tax
    lda.l SAME_VIDEO_CURSOR_COVERAGE_LO,x
Same_VideoSurface_Cursor_Restore__coverage_ready:
    .a16
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    lda.l SAME_VIDEO_CURSOR_WORK_SURFACE
    tax
    jsl Same_Mode3_MapSurfaceX_Far
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
Same_VideoSurface_Cursor_Restore__pixel:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    asl
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    bcs Same_VideoSurface_Cursor_Restore__opaque
    ; No color/pixel transaction for transparent holes, including Restore.
    ; Their dense payload bytes are deliberately unused while coverage lives.
    sep #$20
    .a8
    bra Same_VideoSurface_Cursor_Restore__advance
Same_VideoSurface_Cursor_Restore__opaque:
    .a16
    sep #$20
    .a8
    lda.w SAME_VIDEO_CURSOR_PIXELS_LOW,y
    pha
    lda.l MODE3_R_EXCHANGE
    beq Same_VideoSurface_Cursor_Restore__plain_copy
    lda.l SAME_BWRAM_SURFACE_BASE,x
    sta.w SAME_VIDEO_CURSOR_PIXELS_LOW,y
Same_VideoSurface_Cursor_Restore__plain_copy:
    .a8
    pla
    sta.l SAME_BWRAM_SURFACE_BASE,x
Same_VideoSurface_Cursor_Restore__advance:
    .a8
    inx
    iny
    rep #$20
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_COLUMN
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    beq Same_VideoSurface_Cursor_Restore__row_done
    txa
    and #$00FF
    bne Same_VideoSurface_Cursor_Restore__pixel
    ; Physical x=255 advances to x=0 in the SAME row, not the next row.
    txa
    sec
    sbc #$0100
    tax
    bra Same_VideoSurface_Cursor_Restore__pixel
Same_VideoSurface_Cursor_Restore__row_done:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    beq Same_VideoSurface_Cursor_Restore__copied
    lda.l SAME_VIDEO_CURSOR_WORK_SURFACE
    clc
    adc #$0100
    sta.l SAME_VIDEO_CURSOR_WORK_SURFACE
    brl Same_VideoSurface_Cursor_Restore__row
Same_VideoSurface_Cursor_Restore__copied:
    .a16
    jsr Same_VideoSurface_Cursor_UnionDamage
    sep #$20
    .a8
    lda.l MODE3_R_EXCHANGE
    beq Same_VideoSurface_Cursor_Restore__consume
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    eor #$02
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Restore__consume:
    .a8
    lda #$00
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
    jmp Same_VideoSurface_Cursor_Success

; Restore only when the validated cursor journal intersects caller DAMAGE.
; Used by bounded surface overlays: an unchanged distant cursor must neither
; disappear nor expand a text-strip publication into a whole-height rectangle.
; Caller supplies a bounded, nonempty surface DAMAGE rectangle. The journal
; is still identity/geometry validated before the intersection test.
Same_VideoSurface_RestoreCursorOverlappingDamage_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sep #$20
    .a8
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    cmp #SAME_VIDEO_CURSOR_MAGIC
    beq Same_VideoSurface_Cursor_Overlap__committed
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Overlap__committed:
    rep #$20
    .a16
    jsr Same_VideoSurface_Cursor_Identity
    bcc Same_VideoSurface_Cursor_Overlap__identity
    jmp Same_VideoSurface_Cursor_Discard
Same_VideoSurface_Cursor_Overlap__identity:
    jsr Same_VideoSurface_Cursor_LoadValidate
    bcc Same_VideoSurface_Cursor_Overlap__valid
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Overlap__valid:
    .a16
    .i16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    and #$00FF
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_WIDTH
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X
    bcc Same_VideoSurface_Cursor_Overlap__outside
    beq Same_VideoSurface_Cursor_Overlap__outside
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    cmp.l SAME_VIDEO_CURSOR_WORK_COLUMN
    bcc Same_VideoSurface_Cursor_Overlap__outside
    beq Same_VideoSurface_Cursor_Overlap__outside
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    xba
    and #$00FF
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y
    bcc Same_VideoSurface_Cursor_Overlap__outside
    beq Same_VideoSurface_Cursor_Overlap__outside
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    cmp.l SAME_VIDEO_CURSOR_WORK_COLUMN
    bcc Same_VideoSurface_Cursor_Overlap__outside
    beq Same_VideoSurface_Cursor_Overlap__outside
    ; A previous retained exchange must not turn an ordinary text restore
    ; into a new exchange. This entry consumes the journal, like Restore.
    sep #$20
    .a8
    lda #$00
    sta.l MODE3_R_EXCHANGE
    rep #$20
    .a16
    jmp Same_VideoSurface_Cursor_Restore__valid
Same_VideoSurface_Cursor_Overlap__outside:
    jmp Same_VideoSurface_Cursor_Success

Same_VideoSurface_MergeCursorDamage_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    sep #$20
    .a8
    lda.l SAME_VIDEO_CURSOR_UNDERLAY+$01
    cmp #$01
    beq Same_VideoSurface_Cursor_Merge__retained
    jmp Same_VideoSurface_Cursor_Success
Same_VideoSurface_Cursor_Merge__retained:
    .a8
    rep #$20
    .a16
    jsr Same_VideoSurface_Cursor_Identity
    bcc Same_VideoSurface_Cursor_Merge__identity
    jmp Same_VideoSurface_Cursor_Discard
Same_VideoSurface_Cursor_Merge__identity:
    .a16
    jsr Same_VideoSurface_Cursor_LoadValidate
    bcc Same_VideoSurface_Cursor_Merge__valid
    jmp Same_VideoSurface_Cursor_Failure
Same_VideoSurface_Cursor_Merge__valid:
    .a16
    jsr Same_VideoSurface_Cursor_UnionDamage
    jmp Same_VideoSurface_Cursor_Success

Same_VideoSurface_InvalidateCursorUnderlay_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
Same_VideoSurface_Cursor_Discard:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_VIDEO_CURSOR_UNDERLAY
Same_VideoSurface_Cursor_Success:
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
Same_VideoSurface_Cursor_Failure:
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

Same_VideoSurface_Cursor_Identity:
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM
    and #$00FF
    cmp.l SAME_VIDEO_CURSOR_UNDERLAY+$02
    bne Same_VideoSurface_Cursor_Identity__bad
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_VIDEO_CURSOR_UNDERLAY+$04
    bne Same_VideoSurface_Cursor_Identity__bad
    clc
    rts
Same_VideoSurface_Cursor_Identity__bad:
    sec
    rts

Same_VideoSurface_Cursor_LoadValidate:
    .a16
    lda.l SAME_VIDEO_CURSOR_UNDERLAY+$06
    sta.l SAME_VIDEO_CURSOR_WORK_DEST
    lda.l SAME_VIDEO_CURSOR_UNDERLAY+$08
    sta.l SAME_VIDEO_CURSOR_WORK_WIDTH
    lda.l SAME_VIDEO_CURSOR_UNDERLAY+$0A
    sta.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    jsr Same_VideoSurface_Cursor_Validate
    bcs Same_VideoSurface_Cursor_LoadValidate__bad
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    cmp.l SAME_VIDEO_CURSOR_UNDERLAY+$0C
    bne Same_VideoSurface_Cursor_LoadValidate__bad
    clc
    rts
Same_VideoSurface_Cursor_LoadValidate__bad:
    sec
    rts

; Validate complete clipped rectangle and bounded area before any pixel write.
Same_VideoSurface_Cursor_Validate:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    beq Same_VideoSurface_Cursor_Validate__bad
    cmp #$0011
    bcs Same_VideoSurface_Cursor_Validate__bad
    lda.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    beq Same_VideoSurface_Cursor_Validate__bad
    cmp #$0011
    bcs Same_VideoSurface_Cursor_Validate__bad
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    and #$00FF
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_WIDTH
    cmp #$0101
    bcs Same_VideoSurface_Cursor_Validate__bad
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    xba
    and #$00FF
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    cmp #$00E1
    bcs Same_VideoSurface_Cursor_Validate__bad
    lda.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    lda #$0000
Same_VideoSurface_Cursor_Validate__area:
    .a16
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_AREA
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    beq Same_VideoSurface_Cursor_Validate__ok
    lda.l SAME_VIDEO_CURSOR_WORK_AREA
    bra Same_VideoSurface_Cursor_Validate__area
Same_VideoSurface_Cursor_Validate__ok:
    clc
    rts
Same_VideoSurface_Cursor_Validate__bad:
    sec
    rts

Same_VideoSurface_Cursor_StartCopy:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    sta.l SAME_VIDEO_CURSOR_WORK_SURFACE
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    lda.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    lda #$0000
    sta.l SAME_VIDEO_CURSOR_WORK_PIXEL
    rts

; C clear => another pixel, C set => finished. Scratch never survives a call.
Same_VideoSurface_Cursor_NextPixel:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_PIXEL
    inc
    sta.l SAME_VIDEO_CURSOR_WORK_PIXEL
    lda.l SAME_VIDEO_CURSOR_WORK_SURFACE
    inc
    sta.l SAME_VIDEO_CURSOR_WORK_SURFACE
    lda.l SAME_VIDEO_CURSOR_WORK_COLUMN
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    bne Same_VideoSurface_Cursor_NextPixel__more
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    dec
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    beq Same_VideoSurface_Cursor_NextPixel__done
    lda.l SAME_VIDEO_CURSOR_WORK_SURFACE
    clc
    adc #$0100
    sec
    sbc.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_SURFACE
    lda.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
Same_VideoSurface_Cursor_NextPixel__more:
    clc
    rts
Same_VideoSurface_Cursor_NextPixel__done:
    sec
    rts

; Damage belongs to the active surface; caller supplies either an empty or
; valid surface rectangle. Column/Rows become exclusive new right/bottom.
Same_VideoSurface_Cursor_UnionDamage:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    and #$00FF
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_WIDTH
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    xba
    and #$00FF
    clc
    adc.l SAME_VIDEO_CURSOR_WORK_HEIGHT
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    beq Same_VideoSurface_Cursor_UnionDamage__empty
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    beq Same_VideoSurface_Cursor_UnionDamage__empty
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    cmp.l SAME_VIDEO_CURSOR_WORK_COLUMN
    bcc Same_VideoSurface_Cursor_UnionDamage__right
    sta.l SAME_VIDEO_CURSOR_WORK_COLUMN
Same_VideoSurface_Cursor_UnionDamage__right:
    .a16
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    cmp.l SAME_VIDEO_CURSOR_WORK_ROWS
    bcc Same_VideoSurface_Cursor_UnionDamage__bottom
    sta.l SAME_VIDEO_CURSOR_WORK_ROWS
Same_VideoSurface_Cursor_UnionDamage__bottom:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    and #$00FF
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_X
    bcs Same_VideoSurface_Cursor_UnionDamage__left
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
Same_VideoSurface_Cursor_UnionDamage__left:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    xba
    and #$00FF
    cmp.l SAME_VIDEO_SURFACE_DAMAGE_Y
    bcs Same_VideoSurface_Cursor_UnionDamage__size
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    bra Same_VideoSurface_Cursor_UnionDamage__size
Same_VideoSurface_Cursor_UnionDamage__empty:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_VIDEO_CURSOR_WORK_DEST
    xba
    and #$00FF
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
Same_VideoSurface_Cursor_UnionDamage__size:
    .a16
    lda.l SAME_VIDEO_CURSOR_WORK_COLUMN
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_VIDEO_CURSOR_WORK_ROWS
    sec
    sbc.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    rts
