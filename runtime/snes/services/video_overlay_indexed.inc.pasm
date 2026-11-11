; SC5FNT v2 producer for the existing INDEX8 surface and dirty/PRESENT service.
; A declared bottom 32-row UI viewport belongs exclusively to this producer.
; No second pixel buffer, palette lease, PPU access, or active-room alias.
.bank 23
.org $8000
SAME_TEXT_PEN_X = SAME_VIDEO_TEXT_STATE+$0A
SAME_TEXT_PEN_Y = SAME_VIDEO_TEXT_STATE+$0C
SAME_TEXT_FONT = SAME_VIDEO_TEXT_STATE+$0E
SAME_TEXT_ENTRY = SAME_VIDEO_TEXT_STATE+$10
SAME_TEXT_SOURCE = SAME_VIDEO_TEXT_STATE+$12
SAME_TEXT_WIDTH = SAME_VIDEO_TEXT_STATE+$14
SAME_TEXT_HEIGHT = SAME_VIDEO_TEXT_STATE+$16
SAME_TEXT_X = SAME_VIDEO_TEXT_STATE+$18
SAME_TEXT_Y = SAME_VIDEO_TEXT_STATE+$1A
SAME_TEXT_ADVANCE = SAME_VIDEO_TEXT_STATE+$1C
SAME_TEXT_ROW = SAME_VIDEO_TEXT_STATE+$1E
SAME_TEXT_COL = SAME_VIDEO_TEXT_STATE+$20
SAME_TEXT_INDEX = SAME_VIDEO_TEXT_STATE+$22
SAME_TEXT_LENGTH = SAME_VIDEO_TEXT_STATE+$24
SAME_TEXT_INK = SAME_VIDEO_TEXT_STATE+$26
SAME_TEXT_CHARSET = SAME_VIDEO_TEXT_STATE+$28
SAME_TEXT_BPP = SAME_VIDEO_TEXT_STATE+$2A
SAME_TEXT_BITS = SAME_VIDEO_TEXT_STATE+$2C
SAME_TEXT_BYTE = SAME_VIDEO_TEXT_STATE+$2E
SAME_TEXT_SLOT = SAME_VIDEO_TEXT_STATE+$30
SAME_TEXT_TEMP = SAME_VIDEO_TEXT_STATE+$32
SAME_TEXT_DX = SAME_VIDEO_TEXT_STATE+$34
SAME_TEXT_DY = SAME_VIDEO_TEXT_STATE+$36
SAME_TEXT_DRAW = SAME_VIDEO_TEXT_STATE+$38
SAME_TEXT_SPACING = SAME_VIDEO_TEXT_STATE+$3A
; Half-open glyph bounds: pending immutable layout and last published layout.
; These words use the existing text producer's reserved state, not room/cache RAM.
SAME_TEXT_NEW_LEFT = SAME_VIDEO_TEXT_STATE+$3C
SAME_TEXT_NEW_TOP = SAME_VIDEO_TEXT_STATE+$3E
SAME_TEXT_NEW_RIGHT = SAME_VIDEO_TEXT_STATE+$40
SAME_TEXT_NEW_BOTTOM = SAME_VIDEO_TEXT_STATE+$42
SAME_TEXT_OLD_LEFT = SAME_VIDEO_TEXT_STATE+$44
SAME_TEXT_OLD_TOP = SAME_VIDEO_TEXT_STATE+$46
SAME_TEXT_OLD_RIGHT = SAME_VIDEO_TEXT_STATE+$48
SAME_TEXT_OLD_BOTTOM = SAME_VIDEO_TEXT_STATE+$4A
SAME_TEXT_RAW = SAME_SCUMM_TEXT_PENDING_RAW
SAME_TEXT_INITIAL_INK = SAME_VIDEO_TEXT_STATE+$60
SAME_TEXT_INITIAL_CHARSET = SAME_VIDEO_TEXT_STATE+$62
SAME_TEXT_ROOM = SAME_VIDEO_TEXT_STATE+$64
SAME_TEXT_ROOM_GENERATION = SAME_VIDEO_TEXT_STATE+$66
SAME_TEXT_VISIBLE = SAME_VIDEO_TEXT_STATE+$68
SAME_TEXT_TALK_GENERATION = SAME_VIDEO_TEXT_STATE+$6A

Same_VideoOverlay_Reset_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    lda #$0000
    ldx #$0000
Same_Text_Reset_loop:
    .a16
    .i16
    sta.l SAME_VIDEO_TEXT_STATE,x
    inx
    inx
    cpx #$0080
    bcc Same_Text_Reset_loop
    plx
    pla
    plp
    rtl

Same_VideoOverlay_Frame_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    lda.l SAME_OVERLAY_STATE
    cmp #$0002
    bne Same_Text_Frame_hide
    jsl Same_Text_ProcessPending_Far
    bra Same_Text_Frame_fence
Same_Text_Frame_hide:
    .a16
    cmp #$0003
    bne Same_Text_Frame_fence
    jsl Same_Text_ProcessHide_Far
Same_Text_Frame_fence:
    .a16
    lda.l SAME_OVERLAY_STATE
    cmp #$0001
    bne Same_Text_Frame_done
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_TEXT_ROOM_GENERATION
    bne Same_Text_Frame_stale
    lda.l SAME_VIDEO_SURFACE_ROOM
    cmp.l SAME_TEXT_ROOM
    bne Same_Text_Frame_stale
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp.l SAME_OVERLAY_CURRENT_GENERATION
    bne Same_Text_Frame_done
    sta.l SAME_OVERLAY_COMMITTED_GENERATION
Same_Text_Frame_stale:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_STATE
Same_Text_Frame_done:
    .a16
    ply
    plx
    pla
    plp
    rtl

Same_VideoOverlay_CanWrite_Far:
    .a16
    .i16
    php
    rep #$20
    .a16
    lda.l SAME_OVERLAY_STATE
    bne Same_Text_CanWrite_no
    lda.l SAME_VIDEO_SURFACE_PENDING_VISUAL
    and #$00FF
    bne Same_Text_CanWrite_no
    jsl Same_VideoSurface_CanWrite_Far
    bcs Same_Text_CanWrite_no
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-3)
    bcs Same_Text_CanWrite_no
    plp
    clc
    rtl
Same_Text_CanWrite_no:
    .a16
    .i16
    plp
    sec
    rtl

Same_VideoOverlay_ShowTalkSegment_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    lda.l SAME_OVERLAY_STATE
    beq Same_Text_Show_available
    jmp Same_Text_busy
Same_Text_Show_available:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    and #$00FF
    bne Same_Text_Show_hud_style
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_CHARSET
    and #$00FF
    sta.l SAME_TEXT_INITIAL_CHARSET
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    and #$00FF
    sta.l SAME_TEXT_INITIAL_INK
    jmp Same_Text_Show_talk
Same_Text_Show_hud_style:
    .a16
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET
    and #$00FF
    sta.l SAME_TEXT_INITIAL_CHARSET
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR
    and #$00FF
    sta.l SAME_TEXT_INITIAL_INK
    lda.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    and #$00FF
    beq Same_Text_Show_talk
    lda.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
    and #$00FF
    cmp #$0020
    bcc Same_Text_Show_controller_ok
    jmp Same_Text_unsupported
Same_Text_Show_controller_ok:
    .a16
    .i16
    sta.l SAME_TEXT_LENGTH
    ldx #$0000
Same_Text_Show_controller_copy:
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    sta.l SAME_TEXT_RAW,x
    rep #$20
    .a16
    inx
    cpx #$0020
    bcc Same_Text_Show_controller_copy
    bra Same_Text_Show_validate
Same_Text_Show_talk:
    .a16
    .i16
    lda.l SAME_SCUMM_TALK_SEGMENT_START
    and #$00FF
    tax
    lda.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    and #$00FF
    sta.l SAME_TEXT_LENGTH
    txa
    clc
    adc.l SAME_TEXT_LENGTH
    cmp #$0100
    bcc Same_Text_Show_talk_ok
    jmp Same_Text_unsupported
Same_Text_Show_talk_ok:
    .a16
    .i16
    ldy #$0000
Same_Text_Show_talk_copy:
    .a16
    .i16
    cpy #$00FF
    bcs Same_Text_Show_validate
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW,x
    phx
    tyx
    sta.l SAME_TEXT_RAW,x
    plx
    rep #$20
    .a16
    inx
    iny
    ; Long comparisons use A; DBR is never assumed to be BW-RAM.
    tya
    cmp.l SAME_TEXT_LENGTH
    bcc Same_Text_Show_talk_copy
Same_Text_Show_validate:
    .a16
    .i16
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_TEXT_DRAW
    jsr Same_Text_Layout
    bcc Same_Text_Show_valid
    jmp Same_Text_unsupported
Same_Text_Show_valid:
    .a16
    .i16
    lda.l SAME_SCUMM_TALK_GENERATION
    sta.l SAME_TEXT_TALK_GENERATION
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_TEXT_ROOM
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_TEXT_ROOM_GENERATION
    lda #$0002
    sta.l SAME_OVERLAY_STATE
    jmp Same_Text_busy

; Called by the service frame hook before actor/cursor producers. A busy
; surface cannot starve the immutable request or change its charset/style.
Same_Text_ProcessPending_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    ; An older queued subtitle/HUD must not complete a replacement message.
    ; Keep the request immutable; discard it before writes and let the new
    ; talk owner retry with its own raw bytes/style/generation.
    lda.l SAME_SCUMM_TALK_ACTIVE
    and #$00FF
    beq Same_Text_Process_owner_ready
    lda.l SAME_SCUMM_TALK_GENERATION
    cmp.l SAME_TEXT_TALK_GENERATION
    beq Same_Text_Process_owner_ready
    lda #$0000
    sta.l SAME_OVERLAY_STATE
    jmp Same_Text_busy
Same_Text_Process_owner_ready:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_ROOM
    cmp.l SAME_TEXT_ROOM
    bne Same_Text_Process_stale
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_TEXT_ROOM_GENERATION
    bne Same_Text_Process_stale
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_Text_Process_capacity
    jmp Same_Text_busy
Same_Text_Process_capacity:
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-3)
    bcc Same_Text_Process_ready
    jmp Same_Text_busy
Same_Text_Process_stale:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_STATE
    jmp Same_Text_unsupported
Same_Text_Process_ready:
    .a16
    jsr Same_Text_SeedDamage
    jsl Same_VideoSurface_RestoreCursorOverlappingDamage_Far
    bcc Same_Text_Show_cursor_ready
    jmp Same_Text_busy
Same_Text_Show_cursor_ready:
    .a16
    .i16
    jsr Same_Text_Clear
    lda #$0001
    sta.l SAME_TEXT_DRAW
    jsr Same_Text_Layout
    bcc Same_Text_Show_drawn
    ; The identical immutable input was preflighted before any surface write.
    jmp Same_Text_unsupported
Same_Text_Show_drawn:
    .a16
    .i16
    lda #$0001
    sta.l SAME_TEXT_VISIBLE
    jsr Same_Text_Publish
    bcc Same_Text_success
    jmp Same_Text_busy
Same_Text_success:
    .a16
    .i16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    bra Same_Text_return
Same_Text_busy:
    .a16
    .i16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    bra Same_Text_return
Same_Text_unsupported:
    .a16
    .i16
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
Same_Text_return:
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

Same_VideoOverlay_Hide_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    ; Retain hide even when DMA owns the surface. The next service frame
    ; consumes it; stopped talk does not have to retry a synchronous call.
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_TEXT_ROOM
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_TEXT_ROOM_GENERATION
    lda #$0003
    sta.l SAME_OVERLAY_STATE
    jmp Same_Text_busy

Same_Text_ProcessHide_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    cld
    lda.l SAME_VIDEO_SURFACE_ROOM
    cmp.l SAME_TEXT_ROOM
    bne Same_Text_Hide_stale
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_TEXT_ROOM_GENERATION
    bne Same_Text_Hide_stale
    jsl Same_VideoSurface_CanWrite_Far
    bcc Same_Text_Hide_capacity
    jmp Same_Text_busy
Same_Text_Hide_stale:
    .a16
    lda #$0000
    sta.l SAME_OVERLAY_STATE
    jmp Same_Text_success
Same_Text_Hide_capacity:
    .a16
    lda.l SAME_EVENT_COUNT
    cmp #(SAME_EVENT_CAPACITY-3)
    bcc Same_Text_Hide_ready
    jmp Same_Text_busy
Same_Text_Hide_ready:
    .a16
    .i16
    jsr Same_Text_ResetBounds
    jsr Same_Text_SeedDamage
    jsl Same_VideoSurface_RestoreCursorOverlappingDamage_Far
    bcc Same_Text_Hide_cursor_ready
    jmp Same_Text_busy
Same_Text_Hide_cursor_ready:
    .a16
    .i16
    jsr Same_Text_Clear
    lda #$0000
    sta.l SAME_TEXT_VISIBLE
    jsr Same_Text_Publish
    bcc Same_Text_Hide_ok
    jmp Same_Text_busy
Same_Text_Hide_ok:
    .a16
    .i16
    jmp Same_Text_success

Same_Text_Clear:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ; Cursor restoration may have enlarged damage outside the text viewport.
    ; Clear only old/new text bounds; publication merges cursor damage later.
    jsr Same_Text_SeedDamage
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    xba
    clc
    adc.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_TEXT_DY
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_TEXT_ROW
Same_Text_Clear_row:
    .a16
    .i16
    lda.l SAME_TEXT_DY
    tax
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    tay
    sep #$20
    .a8
    lda #$00
Same_Text_Clear_pixel:
    .a8
    .i16
    sta.l SAME_BWRAM_SURFACE_BASE,x
    inx
    dey
    bne Same_Text_Clear_pixel
    rep #$20
    .a16
    lda.l SAME_TEXT_DY
    clc
    adc #$0100
    sta.l SAME_TEXT_DY
    lda.l SAME_TEXT_ROW
    dec
    sta.l SAME_TEXT_ROW
    bne Same_Text_Clear_row
    rts

Same_Text_ResetBounds:
    .a16
    lda #$0100
    sta.l SAME_TEXT_NEW_LEFT
    lda #SAME_VIDEO_TEXT_BOTTOM
    sta.l SAME_TEXT_NEW_TOP
    lda #$0000
    sta.l SAME_TEXT_NEW_RIGHT
    sta.l SAME_TEXT_NEW_BOTTOM
    rts

; Union of clipped old and new glyph rectangles. Transparent margins may be
; included, but distant empty UI tiles never need conversion. A no-ink request
; still publishes a bounded 1x1 fence so message ownership can complete.
Same_Text_SeedDamage:
    .a16
    .i16
    rep #$20
    .a16
    lda #$0100
    sta.l SAME_TEXT_DX
    lda #SAME_VIDEO_TEXT_BOTTOM
    sta.l SAME_TEXT_DY
    lda #$0000
    sta.l SAME_TEXT_COL
    sta.l SAME_TEXT_ROW
    lda.l SAME_TEXT_NEW_RIGHT
    cmp.l SAME_TEXT_NEW_LEFT
    beq Same_Text_SeedDamage__new_done
    bcc Same_Text_SeedDamage__new_done
    lda.l SAME_TEXT_NEW_BOTTOM
    cmp.l SAME_TEXT_NEW_TOP
    beq Same_Text_SeedDamage__new_done
    bcc Same_Text_SeedDamage__new_done
    lda.l SAME_TEXT_NEW_LEFT
    cmp.l SAME_TEXT_DX
    bcs Same_Text_SeedDamage__new_left
    sta.l SAME_TEXT_DX
Same_Text_SeedDamage__new_left:
    .a16
    lda.l SAME_TEXT_NEW_TOP
    cmp.l SAME_TEXT_DY
    bcs Same_Text_SeedDamage__new_top
    sta.l SAME_TEXT_DY
Same_Text_SeedDamage__new_top:
    .a16
    lda.l SAME_TEXT_NEW_RIGHT
    cmp.l SAME_TEXT_COL
    bcc Same_Text_SeedDamage__new_right
    sta.l SAME_TEXT_COL
Same_Text_SeedDamage__new_right:
    .a16
    lda.l SAME_TEXT_NEW_BOTTOM
    cmp.l SAME_TEXT_ROW
    bcc Same_Text_SeedDamage__new_bottom
    sta.l SAME_TEXT_ROW
Same_Text_SeedDamage__new_bottom:
    .a16
Same_Text_SeedDamage__new_done:
    .a16
    lda.l SAME_TEXT_OLD_RIGHT
    cmp.l SAME_TEXT_OLD_LEFT
    beq Same_Text_SeedDamage__old_done
    bcc Same_Text_SeedDamage__old_done
    lda.l SAME_TEXT_OLD_BOTTOM
    cmp.l SAME_TEXT_OLD_TOP
    beq Same_Text_SeedDamage__old_done
    bcc Same_Text_SeedDamage__old_done
    lda.l SAME_TEXT_OLD_LEFT
    cmp.l SAME_TEXT_DX
    bcs Same_Text_SeedDamage__old_left
    sta.l SAME_TEXT_DX
Same_Text_SeedDamage__old_left:
    .a16
    lda.l SAME_TEXT_OLD_TOP
    cmp.l SAME_TEXT_DY
    bcs Same_Text_SeedDamage__old_top
    sta.l SAME_TEXT_DY
Same_Text_SeedDamage__old_top:
    .a16
    lda.l SAME_TEXT_OLD_RIGHT
    cmp.l SAME_TEXT_COL
    bcc Same_Text_SeedDamage__old_right
    sta.l SAME_TEXT_COL
Same_Text_SeedDamage__old_right:
    .a16
    lda.l SAME_TEXT_OLD_BOTTOM
    cmp.l SAME_TEXT_ROW
    bcc Same_Text_SeedDamage__old_bottom
    sta.l SAME_TEXT_ROW
Same_Text_SeedDamage__old_bottom:
    .a16
Same_Text_SeedDamage__old_done:
    .a16
    lda.l SAME_TEXT_COL
    bne Same_Text_SeedDamage__nonempty
    lda #$0000
    sta.l SAME_TEXT_DX
    lda #SAME_VIDEO_TEXT_TOP
    sta.l SAME_TEXT_DY
    inc
    sta.l SAME_TEXT_ROW
    lda #$0001
    sta.l SAME_TEXT_COL
Same_Text_SeedDamage__nonempty:
    .a16
    lda.l SAME_TEXT_DX
    sta.l SAME_VIDEO_SURFACE_DAMAGE_X
    lda.l SAME_TEXT_DY
    sta.l SAME_VIDEO_SURFACE_DAMAGE_Y
    lda.l SAME_TEXT_COL
    sec
    sbc.l SAME_TEXT_DX
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_TEXT_ROW
    sec
    sbc.l SAME_TEXT_DY
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    rts

Same_Text_Publish:
    .a16
    .i16
    jsr Same_Text_SeedDamage
    ; An intact journal means the cursor was outside the text strip and
    ; remains composed. Only a consumed/restored journal contributes damage.
    lda.l SAME_VIDEO_CURSOR_UNDERLAY
    and #$00FF
    cmp #SAME_VIDEO_CURSOR_MAGIC
    beq Same_Text_Publish_cursor_retained
    jsl Same_VideoSurface_MergeCursorDamage_Far
Same_Text_Publish_cursor_retained:
    .a16
    jsl Same_VideoSurface_PushDamagePresent_Far
    bcs Same_Text_Publish_done
    lda.l SAME_TEXT_NEW_LEFT
    sta.l SAME_TEXT_OLD_LEFT
    lda.l SAME_TEXT_NEW_TOP
    sta.l SAME_TEXT_OLD_TOP
    lda.l SAME_TEXT_NEW_RIGHT
    sta.l SAME_TEXT_OLD_RIGHT
    lda.l SAME_TEXT_NEW_BOTTOM
    sta.l SAME_TEXT_OLD_BOTTOM
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_OVERLAY_CURRENT_GENERATION
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_TEXT_ROOM
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_TEXT_ROOM_GENERATION
    lda #$0001
    sta.l SAME_OVERLAY_STATE
    clc
Same_Text_Publish_done:
    .a16
    .i16
    rts

; Both passes use immutable checked ROM records and the retained bounded text.
Same_Text_Layout:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    jsr Same_Text_ResetBounds
    lda #$0000
    sta.l SAME_TEXT_INDEX
    lda #$0002
    sta.l SAME_TEXT_PEN_X
    lda #SAME_VIDEO_TEXT_TOP
    sta.l SAME_TEXT_PEN_Y
    lda.l SAME_TEXT_INITIAL_INK
    sta.l SAME_TEXT_INK
    lda.l SAME_TEXT_INITIAL_CHARSET
    sta.l SAME_TEXT_CHARSET
    jsr Same_Text_SelectFont
    bcc Same_Text_Layout_next
    rts
Same_Text_Layout_next:
    .a16
    .i16
    lda.l SAME_TEXT_INDEX
    cmp.l SAME_TEXT_LENGTH
    bcc Same_Text_Layout_read
    clc
    rts
Same_Text_Layout_read:
    .a16
    .i16
    jsr Same_Text_GetByte
    cmp #$0000
    bne Same_Text_Layout_nonzero
    clc
    rts
Same_Text_Layout_nonzero:
    .a16
    .i16
    cmp #$00FF
    bne Same_Text_Layout_glyph
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    cmp #$0001
    beq Same_Text_Layout_newline
    cmp #$000C
    beq Same_Text_Layout_color
    cmp #$000E
    beq Same_Text_Layout_font
    cmp #$000A
    beq Same_Text_Layout_speech_word
    cmp #$0008
    beq Same_Text_Layout_next
    ; Wait/continuation belongs to the SCUMM message sequencer. Unknown
    ; unresolved substitutions must not be silently skipped by presentation.
Same_Text_Layout_fail:
    .a16
    .i16
    sec
    rts
Same_Text_Layout_newline:
    .a16
    .i16
    jsr Same_Text_Newline
    brl Same_Text_Layout_next
Same_Text_Layout_color:
    .a16
    .i16
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    sta.l SAME_TEXT_INK
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    cmp #$0000
    bne Same_Text_Layout_fail
    brl Same_Text_Layout_next
; Talkie cue words carry no pixels. Preserve their bytes in TALK_RAW and
; expose unavailable voice realization independently of subtitle rendering.
Same_Text_Layout_speech_word:
    .a16
    .i16
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    lda #$0001
    sta.l SAME_VIDEO_TEXT_STATE+$72 ; speech cue present, audio NOT_IMPLEMENTED
    brl Same_Text_Layout_next
Same_Text_Layout_font:
    .a16
    .i16
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    sta.l SAME_TEXT_CHARSET
    jsr Same_Text_GetByte
    bcs Same_Text_Layout_fail
    cmp #$0000
    bne Same_Text_Layout_fail
    jsr Same_Text_SelectFont
    bcs Same_Text_Layout_fail
    brl Same_Text_Layout_next
Same_Text_Layout_glyph:
    .a16
    .i16
    sta.l SAME_TEXT_TEMP
    asl
    asl
    asl
    asl
    sec
    sbc.l SAME_TEXT_TEMP
    clc
    adc #$004A
    clc
    adc.l SAME_TEXT_FONT
    sta.l SAME_TEXT_ENTRY
    tax
    lda.l ScummV5_FontRecords,x
    and #$00FF
    cmp #$0001
    beq Same_Text_Layout_present
    ; Classic zero-offset glyphs draw nothing and advance by zero. The cooked
    ; directory has already checked that all absent entries are canonical.
    jmp Same_Text_Layout_next
Same_Text_Layout_present:
    .a16
    .i16
    inx
    lda.l ScummV5_FontRecords,x
    sta.l SAME_TEXT_ADVANCE
    inx
    inx
    lda.l ScummV5_FontRecords,x
    and #$00FF
    sta.l SAME_TEXT_WIDTH
    inx
    lda.l ScummV5_FontRecords,x
    and #$00FF
    sta.l SAME_TEXT_HEIGHT
    inx
    lda.l ScummV5_FontRecords,x
    jsr Same_Text_SignedByte
    sta.l SAME_TEXT_X
    inx
    lda.l ScummV5_FontRecords,x
    jsr Same_Text_SignedByte
    sta.l SAME_TEXT_Y
    inx
    lda.l ScummV5_FontRecords,x
    clc
    adc.l SAME_TEXT_FONT
    sta.l SAME_TEXT_SOURCE
    lda.l SAME_TEXT_PEN_X
    clc
    adc.l SAME_TEXT_ADVANCE
    cmp #$00FE
    bcc Same_Text_Layout_fits
    jsr Same_Text_Newline
Same_Text_Layout_fits:
    .a16
    .i16
    jsr Same_Text_GlyphBounds
    lda.l SAME_TEXT_DRAW
    beq Same_Text_Layout_advance
    jsr Same_Text_DrawGlyph
Same_Text_Layout_advance:
    .a16
    .i16
    lda.l SAME_TEXT_PEN_X
    clc
    adc.l SAME_TEXT_ADVANCE
    sta.l SAME_TEXT_PEN_X
    jmp Same_Text_Layout_next

; Match DrawGlyph's signed bearings and clipping without reading pixels.
; DX/DY and COL/ROW are scratch until actual glyph drawing begins.
Same_Text_GlyphBounds:
    .a16
    .i16
    lda.l SAME_TEXT_WIDTH
    bne Same_Text_GlyphBounds__x_size
    rts
Same_Text_GlyphBounds__x_size:
    .a16
    lda.l SAME_TEXT_PEN_X
    clc
    adc.l SAME_TEXT_X
    sta.l SAME_TEXT_DX
    clc
    adc.l SAME_TEXT_WIDTH
    bpl Same_Text_GlyphBounds__x_end_positive
    rts
Same_Text_GlyphBounds__x_end_positive:
    .a16
    cmp #$0100
    bcc Same_Text_GlyphBounds__x_end_clipped
    lda #$0100
Same_Text_GlyphBounds__x_end_clipped:
    .a16
    sta.l SAME_TEXT_COL
    lda.l SAME_TEXT_DX
    bmi Same_Text_GlyphBounds__x_start_clip
    cmp #$0000
    bcs Same_Text_GlyphBounds__x_start_clipped
Same_Text_GlyphBounds__x_start_clip:
    .a16
    lda #$0000
Same_Text_GlyphBounds__x_start_clipped:
    .a16
    cmp.l SAME_TEXT_COL
    bcc Same_Text_GlyphBounds__x_nonempty
    rts
Same_Text_GlyphBounds__x_nonempty:
    .a16
    sta.l SAME_TEXT_DX
    lda.l SAME_TEXT_HEIGHT
    bne Same_Text_GlyphBounds__y_size
    rts
Same_Text_GlyphBounds__y_size:
    .a16
    lda.l SAME_TEXT_PEN_Y
    clc
    adc.l SAME_TEXT_Y
    sta.l SAME_TEXT_DY
    clc
    adc.l SAME_TEXT_HEIGHT
    bpl Same_Text_GlyphBounds__y_end_positive
    rts
Same_Text_GlyphBounds__y_end_positive:
    .a16
    cmp #SAME_VIDEO_TEXT_BOTTOM
    bcc Same_Text_GlyphBounds__y_end_clipped
    lda #SAME_VIDEO_TEXT_BOTTOM
Same_Text_GlyphBounds__y_end_clipped:
    .a16
    sta.l SAME_TEXT_ROW
    lda.l SAME_TEXT_DY
    bmi Same_Text_GlyphBounds__y_start_clip
    cmp #SAME_VIDEO_TEXT_TOP
    bcs Same_Text_GlyphBounds__y_start_clipped
Same_Text_GlyphBounds__y_start_clip:
    .a16
    lda #SAME_VIDEO_TEXT_TOP
Same_Text_GlyphBounds__y_start_clipped:
    .a16
    cmp.l SAME_TEXT_ROW
    bcc Same_Text_GlyphBounds__y_nonempty
    rts
Same_Text_GlyphBounds__y_nonempty:
    .a16
    sta.l SAME_TEXT_DY
    lda.l SAME_TEXT_DX
    cmp.l SAME_TEXT_NEW_LEFT
    bcs Same_Text_GlyphBounds__left
    sta.l SAME_TEXT_NEW_LEFT
Same_Text_GlyphBounds__left:
    .a16
    lda.l SAME_TEXT_DY
    cmp.l SAME_TEXT_NEW_TOP
    bcs Same_Text_GlyphBounds__top
    sta.l SAME_TEXT_NEW_TOP
Same_Text_GlyphBounds__top:
    .a16
    lda.l SAME_TEXT_COL
    cmp.l SAME_TEXT_NEW_RIGHT
    bcc Same_Text_GlyphBounds__right
    sta.l SAME_TEXT_NEW_RIGHT
Same_Text_GlyphBounds__right:
    .a16
    lda.l SAME_TEXT_ROW
    cmp.l SAME_TEXT_NEW_BOTTOM
    bcc Same_Text_GlyphBounds__bottom
    sta.l SAME_TEXT_NEW_BOTTOM
Same_Text_GlyphBounds__bottom:
    .a16
    rts

Same_Text_SignedByte:
    .a16
    .i16
    and #$00FF
    cmp #$0080
    bcc Same_Text_SignedByte_done
    ora #$FF00
Same_Text_SignedByte_done:
    .a16
    .i16
    rts
Same_Text_Newline:
    .a16
    .i16
    lda #$0002
    sta.l SAME_TEXT_PEN_X
    lda.l SAME_TEXT_PEN_Y
    clc
    adc.l SAME_TEXT_SPACING
    sta.l SAME_TEXT_PEN_Y
    rts
Same_Text_GetByte:
    .a16
    .i16
    lda.l SAME_TEXT_INDEX
    cmp.l SAME_TEXT_LENGTH
    bcc Same_Text_GetByte_ok
    sec
    rts
Same_Text_GetByte_ok:
    .a16
    .i16
    tax
    lda.l SAME_TEXT_RAW,x
    and #$00FF
    pha
    txa
    inc
    sta.l SAME_TEXT_INDEX
    pla
    clc
    rts
Same_Text_SelectFont:
    .a16
    .i16
    lda.l SAME_TEXT_CHARSET
    asl
    tax
    lda.l ScummV5_FontDirectory,x
    cmp #$FFFF
    bne Same_Text_SelectFont_ok
    sec
    rts
Same_Text_SelectFont_ok:
    .a16
    .i16
    sta.l SAME_TEXT_FONT
    clc
    adc #$0009
    tax
    lda.l ScummV5_FontRecords,x
    and #$00FF
    sta.l SAME_TEXT_BPP
    lda.l SAME_TEXT_FONT
    clc
    adc #$000F
    tax
    lda.l ScummV5_FontRecords,x
    and #$00FF
    sta.l SAME_TEXT_SPACING
    clc
    rts

Same_Text_DrawGlyph:
    .a16
    .i16
    lda #$0000
    sta.l SAME_TEXT_BITS
    sta.l SAME_TEXT_ROW
Same_Text_DrawGlyph_row:
    .a16
    .i16
    lda.l SAME_TEXT_ROW
    cmp.l SAME_TEXT_HEIGHT
    bcc Same_Text_DrawGlyph_startrow
    rts
Same_Text_DrawGlyph_startrow:
    .a16
    .i16
    clc
    adc.l SAME_TEXT_Y
    clc
    adc.l SAME_TEXT_PEN_Y
    sta.l SAME_TEXT_DY
    lda #$0000
    sta.l SAME_TEXT_COL
Same_Text_DrawGlyph_col:
    .a16
    .i16
    lda.l SAME_TEXT_COL
    cmp.l SAME_TEXT_WIDTH
    bcc Same_Text_DrawGlyph_pixel
    lda.l SAME_TEXT_ROW
    inc
    sta.l SAME_TEXT_ROW
    bra Same_Text_DrawGlyph_row
Same_Text_DrawGlyph_pixel:
    .a16
    .i16
    lda #$0000
    sta.l SAME_TEXT_SLOT
    lda.l SAME_TEXT_BPP
    sta.l SAME_TEXT_TEMP
Same_Text_DrawGlyph_bit:
    .a16
    .i16
    lda.l SAME_TEXT_BITS
    bne Same_Text_DrawGlyph_havebyte
    lda.l SAME_TEXT_SOURCE
    tax
    lda.l ScummV5_FontRecords,x
    and #$00FF
    sta.l SAME_TEXT_BYTE
    inx
    txa
    sta.l SAME_TEXT_SOURCE
    lda #$0008
    sta.l SAME_TEXT_BITS
Same_Text_DrawGlyph_havebyte:
    .a16
    .i16
    lda.l SAME_TEXT_BYTE
    asl
    sta.l SAME_TEXT_BYTE
    and #$0100
    beq Same_Text_DrawGlyph_zero
    lda.l SAME_TEXT_SLOT
    asl
    ora #$0001
    bra Same_Text_DrawGlyph_slot
Same_Text_DrawGlyph_zero:
    .a16
    .i16
    lda.l SAME_TEXT_SLOT
    asl
Same_Text_DrawGlyph_slot:
    .a16
    .i16
    sta.l SAME_TEXT_SLOT
    lda.l SAME_TEXT_BITS
    dec
    sta.l SAME_TEXT_BITS
    lda.l SAME_TEXT_TEMP
    dec
    sta.l SAME_TEXT_TEMP
    bne Same_Text_DrawGlyph_bit
    lda.l SAME_TEXT_SLOT
    beq Same_Text_DrawGlyph_next
    lda.l SAME_TEXT_DY
    cmp #SAME_VIDEO_TEXT_TOP
    bcc Same_Text_DrawGlyph_next
    cmp #SAME_VIDEO_TEXT_BOTTOM
    bcs Same_Text_DrawGlyph_next
    lda.l SAME_TEXT_PEN_X
    clc
    adc.l SAME_TEXT_X
    clc
    adc.l SAME_TEXT_COL
    cmp #$0100
    bcs Same_Text_DrawGlyph_next
    sta.l SAME_TEXT_DX
    lda.l SAME_TEXT_SLOT
    cmp #$0001
    beq Same_Text_DrawGlyph_ink
    clc
    adc #$003A
    clc
    adc.l SAME_TEXT_FONT
    tax
    lda.l ScummV5_FontRecords,x
    and #$00FF
    bra Same_Text_DrawGlyph_store
Same_Text_DrawGlyph_ink:
    .a16
    .i16
    lda.l SAME_TEXT_INK
Same_Text_DrawGlyph_store:
    .a16
    .i16
    pha
    lda.l SAME_TEXT_DY
    xba
    clc
    adc.l SAME_TEXT_DX
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$20
    .a16
Same_Text_DrawGlyph_next:
    .a16
    .i16
    lda.l SAME_TEXT_COL
    inc
    sta.l SAME_TEXT_COL
    jmp Same_Text_DrawGlyph_col
