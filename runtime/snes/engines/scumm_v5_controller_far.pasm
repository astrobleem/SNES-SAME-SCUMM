; Fixture-gated controller presentation/input bridge for the source-backed
; Fate room-42 locker scene. It consumes the normal SAME input latch, performs
; a small source-backed hotspot/verb selection, and publishes through the
; ordinary SCUMM sentence mailbox. It never writes C20 or game state directly.

.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
; The labeled room-68 -> room-42 scenario starts after the earlier authored
; transition which normally initializes string 30.  Global 144's first
; string operations use IDs $1E/$1F; preserve those source-visible
; prerequisites through C8 storage during fixture boot.  This does not
; construct a script slot, PC, mailbox record, or object state.
ScummV5_Controller_SeedRoom42SourceStrings_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sep #$20
    .a8
    lda #$99
    sta.l SAME_SCUMM_C8_SIZES+$1E
    sta.l SAME_SCUMM_C8_SIZES+$1F
    ldx #$0000
    lda #$64
ScummV5_Controller_SeedRoom42SourceStrings_Far__fill:
    .i16
    sta.l SAME_SCUMM_C8_DATA+$1E00,x
    sta.l SAME_SCUMM_C8_DATA+$1F00,x
    inx
    cpx #$0099
    bne ScummV5_Controller_SeedRoom42SourceStrings_Far__fill
    ; A/X/Y were saved at 16-bit width.  Restore that width before pulling
    ; them; otherwise PLA would consume one byte and corrupt the caller's
    ; return stack.  PLP below restores the caller's original widths.
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

.endif

ScummV5_Controller_Frame_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    xba
    sep #$20
    .a8
    ora.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    sta.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_CONTROLLER_DIAG_ROOM
    lda.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_CONTROLLER_DIAG_PHASE
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_Frame__room_ok
    cmp #$44
    beq ScummV5_Controller_Frame__room_ok
    plp
    rtl
ScummV5_Controller_Frame__room_ok:
    sep #$20
    .a8
    ; The controller build is a labeled room-42 scenario.  Once the normal
    ; room-68 fixture root has installed, hand off through the ordinary room
    ; request/lifecycle API; no script slot, PC, mailbox, or object state is
    ; constructed by this bridge.
    cmp #$44
    beq ScummV5_Controller_Frame__room68
    jmp ScummV5_Controller_Frame__room42_check
ScummV5_Controller_Frame__room68:
    sep #$20
    .a8
    ; Room-68 title text is a real logical message.  In the controller
    ; scenario an A edge is the normal user acknowledgement; route it through
    ; the existing talk-stop lifecycle so ownership/completion bookkeeping is
    ; preserved before the room-42 handoff is requested.
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Controller_Frame__room68_phase
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    beq ScummV5_Controller_Frame__room68_phase16
    sep #$20
    .a8
    jsr ScummV5_Talk_Stop_Far
ScummV5_Controller_Frame__room68_phase:
    sep #$20
    .a8
ScummV5_Controller_Frame__room68_phase16:
    sep #$20
    .a8
    lda #$11
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_M23A_PHASE
    beq ScummV5_Controller_Frame__room68_idle
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__room68_idle:
    sep #$20
    .a8
ScummV5_Controller_Frame__room68_request:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    lda #$2A
    jsr ScummV5_RequestRoom
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__room42_check:
    sep #$20
    .a8
    cmp #$2A
    beq ScummV5_Controller_Frame__room42
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__room42:
    sep #$20
    .a8
    lda #$22
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    ; Phase values 0/2 are both accepted stable room-lifecycle states on
    ; this profile.  The controller is additionally gated by cutscene,
    ; talk, C20, and sentence-pending state below; do not reject an input
    ; boundary solely because the entry callback is still publishing phase.
    bra ScummV5_Controller_Frame__phase_ok
ScummV5_Controller_Frame__phase_ok:
    lda.l SAME_SCUMM_C19_STACK_POINTER
    beq ScummV5_Controller_Frame__stack_ok
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__stack_ok:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Controller_Frame__talk_ok
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__talk_ok:
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_C20_COUNT
    beq ScummV5_Controller_Frame__queue_ok
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__queue_ok:
    sep #$20
    .a8
    lda #$05
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_SENTENCE_API_PENDING
    beq ScummV5_Controller_Frame__ready
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__ready:
    sep #$20
    .a8
    lda #$06
    sta.l SAME_SCUMM_CONTROLLER_DIAG

    ; Establish the source-backed scene cursor once at the accepted room-42
    ; actor checkpoint. The cursor moves from the actor toward the authored
    ; locker hotspot; it is not a validator mailbox write.
    lda.l SAME_SCUMM_CONTROLLER_MODE
    bne ScummV5_Controller_Frame__mode_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    bne ScummV5_Controller_Frame__mode_ready16
    lda #$0091
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    lda #$0070
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_VERB
    lda #$EA
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_OBJECT+1
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    lda #$07
    sta.l SAME_SCUMM_CONTROLLER_DIAG
ScummV5_Controller_Frame__mode_ready16:
    sep #$20
    .a8
ScummV5_Controller_Frame__mode_ready:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0100
    beq ScummV5_Controller_Frame__right_done
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc #$0002
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    rep #$20
    .a16
ScummV5_Controller_Frame__right_done:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0200
    beq ScummV5_Controller_Frame__left_done
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sec
    sbc #$0002
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    rep #$20
    .a16
ScummV5_Controller_Frame__left_done:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0800
    beq ScummV5_Controller_Frame__up_done
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sec
    sbc #$0002
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    rep #$20
    .a16
ScummV5_Controller_Frame__up_done:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0400
    beq ScummV5_Controller_Frame__down_done
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    clc
    adc #$0002
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    rep #$20
    .a16
ScummV5_Controller_Frame__down_done:
    rep #$20
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$02
    bne ScummV5_Controller_Frame__mode_not_2
    jmp ScummV5_Controller_Frame__check_opened
ScummV5_Controller_Frame__mode_not_2:
    sep #$20
    .a8
    cmp #$03
    bne ScummV5_Controller_Frame__mode_not_3
    jmp ScummV5_Controller_Frame__select_inspect
ScummV5_Controller_Frame__mode_not_3:
    sep #$20
    .a8
    cmp #$01
    bne ScummV5_Controller_Frame__mode_select
    jmp ScummV5_Controller_Frame__select_verb
ScummV5_Controller_Frame__mode_select:

    ; A selects the authored object only when the cursor is inside the
    ; source-backed CDHD hotspot used by object 490.
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    bne ScummV5_Controller_Frame__cursor_x_low_ok
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_x_low_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    cmp #$00BE
    bcs ScummV5_Controller_Frame__cursor_x_low_pass
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_x_low_pass:
    rep #$20
    .a16
    cmp #$00F1
    bcc ScummV5_Controller_Frame__cursor_x_high_ok
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_x_high_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    cmp #$004C
    bcs ScummV5_Controller_Frame__cursor_y_low_ok
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_y_low_ok:
    rep #$20
    .a16
    cmp #$0080
    bcc ScummV5_Controller_Frame__cursor_y_high_ok
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_y_high_ok:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    jmp ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__select_verb:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$4000
    beq ScummV5_Controller_Frame__select_verb_a
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_STATES+$01EA
    beq ScummV5_Controller_Frame__verb_open
    lda #$09
    sta.l SAME_SCUMM_CONTROLLER_VERB
    bra ScummV5_Controller_Frame__verb_dirty
ScummV5_Controller_Frame__verb_open:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_VERB
ScummV5_Controller_Frame__verb_dirty:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_Frame__select_verb_a:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    bne ScummV5_Controller_Frame__select_verb_a_pressed
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__select_verb_a_pressed:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    lda #$EA
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1
    lda #$00
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
    lda.l SAME_SCUMM_CONTROLLER_SUBMISSIONS
    inc
    sta.l SAME_SCUMM_CONTROLLER_SUBMISSIONS
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_CONTROLLER_LAST_ACTION
    lda #$02
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    bra ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__check_opened:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_STATES+$01EA
    beq ScummV5_Controller_Frame__hud
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$09
    sta.l SAME_SCUMM_CONTROLLER_VERB
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    bra ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__select_inspect:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    beq ScummV5_Controller_Frame__hud
    sep #$20
    .a8
    lda #$09
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    lda #$EA
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1+1
    lda #$00
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2+1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
    lda.l SAME_SCUMM_CONTROLLER_SUBMISSIONS
    inc
    sta.l SAME_SCUMM_CONTROLLER_SUBMISSIONS
    sta.l SAME_SCUMM_CONTROLLER_LAST_ACTION
    lda #$04
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    bra ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__hud:
    ; The semantic path is independent of presentation. The existing talk
    ; overlay is used only as the bounded scene HUD when no authored message
    ; owns it; normal C23/Talk owns the same renderer during dialogue.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    beq ScummV5_Controller_Frame__done
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    .if SAME_VIDEO_OVERLAY_BG2
    ; Authored C23 owns the BG2 talk layer while a message is active.
    lda.l SAME_SCUMM_TALK_ACTIVE
    bne ScummV5_Controller_Frame__done
    jsl ScummV5_Controller_ShowHud_Far
    .endif
ScummV5_Controller_Frame__done:
    plp
    rtl

; Compose the source-backed costume.2 stand/walk pose over the indexed room
; surface.  This is deliberately a surface compositor: actor state selects
; the cooked pose, while the existing surface service retains palette, DMA,
; and PPU ownership.  A room rebuild precedes each actor-state change so
; pixels from the previous pose are restored by the normal room compositor.
.if SAME_VIDEO_OVERLAY_BG2
ScummV5_Controller_RenderActor_Far:
    php
    rep #$30
    .a16
    .i16
    ; ACTIVE_ROOM is a byte field.  Keep the comparison byte-wide so the
    ; adjacent pending-record byte cannot become part of the room identity.
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_RenderActor__room_ok
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    plp
    rtl
ScummV5_Controller_RenderActor__room_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_X
    bne ScummV5_Controller_RenderActor__x_diff
    jmp ScummV5_Controller_RenderActor__x_same
ScummV5_Controller_RenderActor__x_diff:
    jmp ScummV5_Controller_RenderActor__changed
ScummV5_Controller_RenderActor__x_same:
    lda.l SAME_SCUMM_C31_POSITIONS+6
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_Y
    bne ScummV5_Controller_RenderActor__y_diff
    jmp ScummV5_Controller_RenderActor__y_same
ScummV5_Controller_RenderActor__y_diff:
    jmp ScummV5_Controller_RenderActor__changed
ScummV5_Controller_RenderActor__y_same:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    beq ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    beq ScummV5_Controller_RenderActor__retry_done
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_IDLE
    bne ScummV5_Controller_RenderActor__retry_done
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    bne ScummV5_Controller_RenderActor__retry_done
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_PushDirtyPresent_Far
    bcs ScummV5_Controller_RenderActor__retry_done
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    dec
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    ; This publish contains the complete indexed surface, including the
    ; cursor already painted by the cursor pass.  Do not schedule a second
    ; full-surface conversion for that same cursor paint.
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_RETRY
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
ScummV5_Controller_RenderActor__retry_done:
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__changed:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_ComposeRoom_Far
    bcc ScummV5_Controller_RenderActor__compose_ok
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__compose_ok:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda.l SAME_SCUMM_C31_POSITIONS+6
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE

    ; Frame zero is the source-defined standing pose. During movement select
    ; the second cooked pose on alternating frame-counter phases.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING+1
    beq ScummV5_Controller_RenderActor__stand
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    lsr
    lsr
    lsr
    and #$0001
    beq ScummV5_Controller_RenderActor__stand
    lda #$0800
    bra ScummV5_Controller_RenderActor__frame_base
ScummV5_Controller_RenderActor__stand:
    rep #$20
    .a16
    lda #$0000
ScummV5_Controller_RenderActor__frame_base:
    rep #$20
    .a16
    sta.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
ScummV5_Controller_RenderActor__row:
    rep #$20
    .a16
    ; Keep SRC as the immutable frame base.  The previous implementation
    ; added each row's offset back into SRC, making the source advance by
    ; 0+32+64+... and eventually read past the cooked pose.  FRAME is the
    ; per-row source cursor; the pixel loop may then use it without changing
    ; the frame base needed by the next row.
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
ScummV5_Controller_RenderActor__pixel:
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    tax
    sep #$20
    .a8
    lda.l ScummV5_ActorSprite_Data,x
    beq ScummV5_Controller_RenderActor__transparent
    sta.l SAME_SCUMM_CONTROLLER_RENDER_FRAME
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    tax
    lda.l SAME_SCUMM_CONTROLLER_RENDER_FRAME
    sta.l SAME_BWRAM_SURFACE_BASE,x
ScummV5_Controller_RenderActor__transparent:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
    cmp #$0020
    bcc ScummV5_Controller_RenderActor__pixel
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    cmp #$0040
    bcc ScummV5_Controller_RenderActor__row

    ; Add the source-backed locker OBIM through the same indexed surface
    ; compositor before publishing.  State 1 is the authored opened form,
    ; so the ordinary room compose leaves the locker image absent.
    jsl ScummV5_Controller_RenderLocker_Far
    jsl ScummV5_Controller_DrawCursor_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_PushDirtyPresent_Far
    bcs ScummV5_Controller_RenderActor__present_retry
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    bra ScummV5_Controller_RenderActor__present_record
ScummV5_Controller_RenderActor__present_retry:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
ScummV5_Controller_RenderActor__present_record:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sta.l SAME_SCUMM_CONTROLLER_RENDER_X
    lda.l SAME_SCUMM_C31_POSITIONS+6
    sta.l SAME_SCUMM_CONTROLLER_RENDER_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
ScummV5_Controller_RenderActor__done:
    plp
    rtl

; Minimal data-driven room-object presentation for the controller fixture.
; Pixels are cooked from room 42's OBIM/SMAP; the surface service retains
; palette conversion, dirty publication, and PPU/DMA ownership.
ScummV5_Controller_RenderLocker_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_RenderLocker__room_ok
    jmp ScummV5_Controller_RenderLocker__done
ScummV5_Controller_RenderLocker__room_ok:
    lda.l SAME_SCUMM_OBJECT_STATES+490
    beq ScummV5_Controller_RenderLocker__state_ok
    jmp ScummV5_Controller_RenderLocker__done
ScummV5_Controller_RenderLocker__state_ok:
    rep #$20
    .a16
    lda #$00B8
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda #$0040
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
ScummV5_Controller_RenderLocker__row:
    rep #$20
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
ScummV5_Controller_RenderLocker__pixel:
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    tax
    sep #$20
    .a8
    lda.l ScummV5_ObjectSprite_Data,x
    sta.l SAME_SCUMM_CONTROLLER_RENDER_FRAME
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    tax
    lda.l SAME_SCUMM_CONTROLLER_RENDER_FRAME
    sta.l SAME_BWRAM_SURFACE_BASE,x
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
    cmp #$0010
    bcc ScummV5_Controller_RenderLocker__pixel
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    cmp #$0010
    bcc ScummV5_Controller_RenderLocker__row
ScummV5_Controller_RenderLocker__done:
    plp
    rtl
.endif

.if SAME_VIDEO_OVERLAY_BG2
; Draw the cursor into the same indexed surface composition as the actor.
; This helper intentionally does not publish: the caller owns the single
; room/actor/cursor present transaction.
ScummV5_Controller_DrawCursor_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
ScummV5_Controller_DrawCursor__row:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    asl
    asl
    asl
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
ScummV5_Controller_DrawCursor__pixel:
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    tax
    sep #$20
    .a8
    lda.l ScummV5_Controller_Cursor_Data,x
    beq ScummV5_Controller_DrawCursor__transparent
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    tax
    lda #$000F
    sta.l SAME_BWRAM_SURFACE_BASE,x
ScummV5_Controller_DrawCursor__transparent:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
    cmp #$0008
    bcc ScummV5_Controller_DrawCursor__pixel
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    cmp #$0008
    bcc ScummV5_Controller_DrawCursor__row
    rtl

; Render the engine cursor in the indexed surface.  This is the generic
; source-independent SCUMM arrow used when the source corpus has no separate
; cursor resource; its logical position is the same coordinate consumed by
; the controller hit-test, and the video backend still owns presentation.
ScummV5_Controller_RenderCursor_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_RenderCursor__room_ok
    plp
    rtl
ScummV5_Controller_RenderCursor__room_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    cmp.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_X
    bne ScummV5_Controller_RenderCursor__changed
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    cmp.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_Y
    bne ScummV5_Controller_RenderCursor__changed
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    beq ScummV5_Controller_RenderCursor__changed
    jmp ScummV5_Controller_RenderCursor__done
ScummV5_Controller_RenderCursor__changed:
    ; Restore the room and actor, then draw the cursor over that composed
    ; surface.  The actor helper remains the sole costume compositor.  A
    ; cursor-only redraw must not invalidate an already committed actor pose:
    ; doing so re-enters ComposeRoom while the backend is converting the
    ; previous full frame and can restart conversion indefinitely.
    sep #$20
    .a8
    ; Keep the surface compositor quiescent while the backend owns a full
    ; conversion.  The cached cursor coordinates remain different/invalid,
    ; so this same path retries on the first idle frame without publishing a
    ; competing generation every frame.
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_IDLE
    beq ScummV5_Controller_RenderCursor__changed_idle
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    bne ScummV5_Controller_RenderCursor__changed_deferred
    jmp ScummV5_Controller_RenderCursor__done
ScummV5_Controller_RenderCursor__changed_idle:
ScummV5_Controller_RenderCursor__changed_deferred:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    bne ScummV5_Controller_RenderCursor__actor_ready
    jsl ScummV5_Controller_RenderActor_Far
ScummV5_Controller_RenderCursor__actor_ready:

    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
ScummV5_Controller_RenderCursor__row:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    asl
    asl
    asl
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    xba
    and #$FF00
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_DST
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
ScummV5_Controller_RenderCursor__pixel:
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_ROWSRC
    tax
    sep #$20
    .a8
    lda.l ScummV5_Controller_Cursor_Data,x
    beq ScummV5_Controller_RenderCursor__transparent
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    clc
    adc.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    tax
    lda #$000F
    sta.l SAME_BWRAM_SURFACE_BASE,x
ScummV5_Controller_RenderCursor__transparent:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_COL
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COL
    cmp #$0008
    bcc ScummV5_Controller_RenderCursor__pixel
    lda.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    inc
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROW
    cmp #$0008
    bcc ScummV5_Controller_RenderCursor__row

    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_X
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_Y
    sep #$20
    .a8
ScummV5_Controller_RenderCursor__done:
    plp
    rtl

ScummV5_Controller_Cursor_Data:
    .byte $01,$00,$00,$00,$00,$00,$00,$00
    .byte $01,$01,$00,$00,$00,$00,$00,$00
    .byte $01,$00,$01,$00,$00,$00,$00,$00
    .byte $01,$00,$00,$01,$00,$00,$00,$00
    .byte $01,$00,$00,$00,$01,$00,$00,$00
    .byte $01,$00,$00,$00,$00,$01,$00,$00
    .byte $01,$00,$00,$00,$00,$00,$01,$00
    .byte $01,$01,$01,$01,$01,$01,$01,$01
.endif

.if SAME_VIDEO_OVERLAY_BG2
ScummV5_Controller_ShowHud_Far:
    ; Keep the first visual proof deliberately small: a source-neutral cursor
    ; marker and verb prompt. Authored dialogue later replaces it normally.
    ; Anchor the prompt with the same room-to-display transform used by the
    ; controller hit-test.  This keeps the visible selection tied to the
    ; displayed cursor instead of a second hard-coded coordinate system.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    adc #$0020
    sec
    sbc #$000C
    sec
    sbc.l SAME_VIDEO_SURFACE_DEST_X
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sec
    sbc #$0008
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y
    sep #$20
    .a8
    rep #$20
    .a16
    lda #$013F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT
    lda #$0008
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR
    lda #$00
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_FLAGS
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$01
    beq ScummV5_Controller_ShowHud__verb
    cmp #$03
    beq ScummV5_Controller_ShowHud__inspect
    cmp #$02
    beq ScummV5_Controller_ShowHud__walk
    cmp #$04
    beq ScummV5_Controller_ShowHud__done
    ldx #ScummV5_Controller_HudHover
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000D
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__verb:
    sep #$20
    .a8
    ldx #ScummV5_Controller_HudVerb
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000F
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__inspect:
    sep #$20
    .a8
    ldx #ScummV5_Controller_HudInspect
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000A
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__walk:
    sep #$20
    .a8
    ldx #ScummV5_Controller_HudWalk
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000A
ScummV5_Controller_ShowHud__copy:
    sta.l SAME_SCUMM_TALK_RAW_LENGTH
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    dec
    phb
    mvn $7E,$09
    plb
    rep #$20
    .a16
    lda #$00
    sta.l SAME_SCUMM_TALK_SEGMENT_START
    sep #$20
    .a8
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    sta.l SAME_SCUMM_TALK_SEGMENT_LENGTH
    lda #$00
    sta.l SAME_SCUMM_TALK_SEGMENT_GLYPHS
    jsl Same_VideoOverlay_ShowTalkSegment_Far
ScummV5_Controller_ShowHud__done:
    rtl
.endif

ScummV5_Controller_HudHover:
    .byte $3E,$20,$4F,$50,$45,$4E,$20,$4C,$4F,$43,$4B,$45,$52
ScummV5_Controller_HudVerb:
    .byte $41,$3A,$20,$4F,$50,$45,$4E,$20,$59,$3A,$20,$4C,$4F,$4F,$4B
ScummV5_Controller_HudWalk:
    .byte $57,$41,$4C,$4B,$49,$4E,$47,$2E,$2E,$2E
ScummV5_Controller_HudInspect:
    .byte $41,$3A,$20,$49,$4E,$53,$50,$45,$43,$54
ScummV5_Controller_HudLengths:
    .byte $0D,$0F,$0A,$0A
