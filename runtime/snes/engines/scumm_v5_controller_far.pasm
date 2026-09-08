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
    beq ScummV5_Controller_Frame__raw_input_done
    sta.l SAME_SCUMM_CONTROLLER_INPUT_RAW
ScummV5_Controller_Frame__raw_input_done:
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
    and #$0080 ; SNES A button in the auto-joypad word
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
    ; This fixture runs in bank 9.  The bank-0 ScummV5_RequestRoom helper
    ; is an RTS entry and cannot be reached with JSR while PBR remains 9.
    ; Use the existing same-bank far lifecycle entry instead.
    jsl ScummV5_M23A_RequestRoom_FarEntry
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
    ; Mode 4 is the fixture's inspect-talk ownership state.  Talk_Stop clears
    ; the logical message, but the controller must explicitly hand control
    ; back to its ordinary hover state before the next input edge.  Keep this
    ; transition semantic and target-neutral; presentation will consume the
    ; new HUD-dirty state in the normal late visual phase.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$04
    bne ScummV5_Controller_Frame__talk_mode_ready
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_Frame__talk_mode_ready:
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

    ; Establish the cursor at the current source actor position.  Selection
    ; below is entirely driven by active-room CDHD/VERB metadata.
    lda.l SAME_SCUMM_CONTROLLER_MODE
    bne ScummV5_Controller_Frame__mode_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    bne ScummV5_Controller_Frame__mode_ready16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    lda.l SAME_SCUMM_C31_POSITIONS+6
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
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
    cmp #$05
    bne ScummV5_Controller_Frame__mode_not_5
    jmp ScummV5_Controller_Frame__release_hud
ScummV5_Controller_Frame__mode_not_5:
    sep #$20
    .a8
    cmp #$06
    bne ScummV5_Controller_Frame__mode_select
    jmp ScummV5_Controller_Frame__submit_inspect
ScummV5_Controller_Frame__mode_select:
    sep #$20
    .a8
    cmp #$01
    bne ScummV5_Controller_Frame__mode_select_fallback
    jmp ScummV5_Controller_Frame__select_verb
ScummV5_Controller_Frame__mode_select_fallback:
    ; A resolves the cursor against the active room's source-backed CDHD
    ; records, then discovers the object's explicit authored VERB entries.
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    ora.l SAME_SCUMM_INTERACTION_LIMIT ; fixture diagnostic: retain edge bits
    sta.l SAME_SCUMM_INTERACTION_LIMIT
    lda.l SAME_INPUT_PRESSED
    and #$0080 ; SNES A button in the auto-joypad word
    bne ScummV5_Controller_Frame__cursor_x_low_ok
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__cursor_x_low_ok:
    sep #$20
    .a8
    lda #$31
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    clc
    adc.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    sta.l SAME_SCUMM_INTERACTION_X
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    clc
    adc.l SAME_SCUMM_CAMERA_CURRENT_Y
    sec
    sbc #$0064 ; v5 room viewport origin; vertical camera is not scrolled
    sta.l SAME_SCUMM_INTERACTION_Y
    jsl ScummV5_Generic_Object_HitTest_Far
    bcs ScummV5_Controller_Frame__hit_ok
    sep #$20
    .a8
    lda #$32
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    ora #$20
    sta.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    brl ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__hit_ok:
    sep #$20
    .a8
    lda #$33
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    ora #$40
    sta.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    rep #$20
    .a16
    lda.l SAME_SCUMM_INTERACTION_OBJECT
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    jsl ScummV5_Generic_Verb_First_Far
    bcs ScummV5_Controller_Frame__verb_ok
    sep #$20
    .a8
    lda #$34
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    lda.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    ora #$10
    sta.l SAME_SCUMM_CONTROLLER_DIAG_INPUT
    brl ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__verb_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_VERB_RESULT
    sta.l SAME_SCUMM_CONTROLLER_VERB
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
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    lda #$0000
    sta.l SAME_SCUMM_VERB_ID
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_VERB_ID
    jsl ScummV5_Generic_Verb_Next_Far
    bcc ScummV5_Controller_Frame__select_verb_a
    sep #$20
    .a8
    lda.l SAME_SCUMM_VERB_RESULT
    sta.l SAME_SCUMM_CONTROLLER_VERB
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_Frame__select_verb_a:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080 ; SNES A button in the auto-joypad word
    bne ScummV5_Controller_Frame__select_verb_a_pressed
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__select_verb_a_pressed:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    sep #$20
    .a8
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
    jmp ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__check_opened:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_STATES,x
    bne ScummV5_Controller_Frame__opened
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__opened:
    sep #$20
    .a8
    ; Release the previous HUD layer before authored inspection talk owns
    ; the same target-neutral text service.  The two-step mode waits for the
    ; existing overlay transaction to become writable, then waits for the
    ; hide transaction to finish before exposing Inspect.
    lda #$05
    sta.l SAME_SCUMM_CONTROLLER_MODE
    jmp ScummV5_Controller_Frame__done

ScummV5_Controller_Frame__release_hud:
    sep #$20
    .a8
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    jsl Same_VideoText_CanWrite_Far
    bcc ScummV5_Controller_Frame__release_ready
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__release_ready:
    sep #$20
    .a8
    jsl Same_VideoText_Hide_Far
    lda #$06
    sta.l SAME_SCUMM_CONTROLLER_MODE
    .else
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_MODE
    .endif
    jmp ScummV5_Controller_Frame__done

ScummV5_Controller_Frame__submit_inspect:
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    jsl Same_VideoText_CanWrite_Far
    bcc ScummV5_Controller_Frame__inspect_text_ready
    brl ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__inspect_text_ready:
    .endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    lda #$0000
    sta.l SAME_SCUMM_VERB_ID
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_VERB_ID
    jsl ScummV5_Generic_Verb_Next_Far
    bcc ScummV5_Controller_Frame__done
    sep #$20
    .a8
    lda.l SAME_SCUMM_VERB_RESULT
    sta.l SAME_SCUMM_CONTROLLER_VERB
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    jmp ScummV5_Controller_Frame__done

ScummV5_Controller_Frame__select_inspect:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080 ; SNES A button in the auto-joypad word
    beq ScummV5_Controller_Frame__hud
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    sep #$20
    .a8
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
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    ; Authored C23 owns the BG2 talk layer while a message is active.
    lda.l SAME_SCUMM_TALK_ACTIVE
    bne ScummV5_Controller_Frame__done
    jsl ScummV5_Controller_ShowHud_Far
    .endif
ScummV5_Controller_Frame__done:
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE && !(SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $04)
    ; Diagnostic pre-ordering variant: retain the historical controller-phase
    ; actor render so the ordering family can be bisected independently.
    jsl ScummV5_Controller_RenderActor_Far
    .endif
    ; Input/controller semantics end here.  Actor presentation consumes the
    ; coherent desired snapshot from ScummV5_Visual_Frame_Far, after the
    ; movement/scheduler phase, so a single logical frame cannot compose two
    ; different actor snapshots.
    plp
    rtl

; Publish semantic actor state after movement has committed its complete
; record. A non-room-42 frame is intentionally inert.
ScummV5_Controller_PublishActorVisual_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_PublishActorVisual__room_ok
    jmp ScummV5_Controller_PublishActorVisual__done
ScummV5_Controller_PublishActorVisual__room_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+4
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_X
    lda.l SAME_SCUMM_C31_POSITIONS+6
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    lda.l SAME_SCUMM_PUT_ACTOR_DEST_X+2
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    ; C31 position and destination are committed before the movement flag is
    ; refreshed on this path.  Derive the visual pose from the coherent
    ; position/destination pair as well as the flag; otherwise the first
    ; position change publishes a standing pose at the new position, starts a
    ; long presentation conversion, and the actual walking snapshot arrives
    ; only after movement has completed.  FFFF is the authored no-destination
    ; sentinel, so it cannot make an idle actor appear to walk.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING+1
    beq ScummV5_Controller_PublishActorVisual__check_destination
    jmp ScummV5_Controller_PublishActorVisual__moving
ScummV5_Controller_PublishActorVisual__check_destination:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    cmp #$FFFF
    bne ScummV5_Controller_PublishActorVisual__destination_valid
    ; Movement update publishes position before destination on one ordinary
    ; scheduler path.  Once a visible snapshot exists, a changed position
    ; paired with the no-destination sentinel is an incomplete record, not a
    ; coherent teleport/standing state.  Retain the last desired snapshot so
    ; the next frame can publish the position and destination together.
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    beq ScummV5_Controller_PublishActorVisual__standing
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_X
    bne ScummV5_Controller_PublishActorVisual__done
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_Y
    bne ScummV5_Controller_PublishActorVisual__done
    bra ScummV5_Controller_PublishActorVisual__standing
ScummV5_Controller_PublishActorVisual__destination_valid:
    cmp.l SAME_SCUMM_CONTROLLER_DESIRED_X
    beq ScummV5_Controller_PublishActorVisual__compare_destination_y
    jmp ScummV5_Controller_PublishActorVisual__moving
ScummV5_Controller_PublishActorVisual__compare_destination_y:
    lda.l SAME_SCUMM_MOVE_DEST_Y+2
    cmp.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    beq ScummV5_Controller_PublishActorVisual__standing
    bra ScummV5_Controller_PublishActorVisual__moving
ScummV5_Controller_PublishActorVisual__moving:
    sep #$20
    .a8
    lda #$01
    bra ScummV5_Controller_PublishActorVisual__pose_done
ScummV5_Controller_PublishActorVisual__standing:
    sep #$20
    .a8
    lda #$00
ScummV5_Controller_PublishActorVisual__pose_done:
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_ACTORS+64+SAME_SCUMM_C14_A_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    lda.l SAME_SCUMM_ACTOR_FACINGS+2
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    lda.l SAME_SCUMM_C14_ACTORS+64+SAME_SCUMM_C14_A_VISIBLE
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
ScummV5_Controller_PublishActorVisual__done:
    plp
    rtl

; Room installation owns cache lifetime. This is called by the generic room
; visual lifecycle, so startup/other rooms cannot inherit a fixture snapshot.
ScummV5_Controller_ResetVisualCache_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ROOM
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    .if SAME_SCUMM_CONTROLLER_WITNESS
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_VALID
    .endif
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_RETRY
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VISIBLE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    sta.l SAME_SCUMM_CONTROLLER_RENDER_FACING
    plp
    rtl

; Compose the source-backed costume.2 stand/walk pose over the indexed room
; surface.  This is deliberately a surface compositor: actor state selects
; the cooked pose, while the existing surface service retains palette and
; presentation ownership.  A room rebuild precedes each actor-state change so
; pixels from the previous pose are restored by the normal room compositor.
.if SAME_VIDEO_SURFACE_AVAILABLE
ScummV5_Controller_RenderActor_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_RENDER_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_RENDER_ENTRIES
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    beq ScummV5_Controller_RenderActor__entry_diag_done
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_RENDER_MOVING_ENTRIES
    inc
    sta.l SAME_VIDEO_DIAG_RENDER_MOVING_ENTRIES
ScummV5_Controller_RenderActor__entry_diag_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_VIDEO_DIAG_RENDER_DESIRED
    ; ACTIVE_ROOM is a byte field.  Keep the comparison byte-wide so the
    ; adjacent pending-record byte cannot become part of the room identity.
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_RenderActor__room_ok
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl
ScummV5_Controller_RenderActor__room_ok:
    ; Position is not a complete visual cache key: an actor can change from
    ; standing to walking without moving during the first logical step.
    sep #$20
    .a8
    .if SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $01
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT
    beq ScummV5_Controller_RenderActor__pose_same
    jmp ScummV5_Controller_RenderActor__changed
    .endif
ScummV5_Controller_RenderActor__pose_same:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_X
    bne ScummV5_Controller_RenderActor__x_diff
    jmp ScummV5_Controller_RenderActor__x_same
ScummV5_Controller_RenderActor__x_diff:
    jmp ScummV5_Controller_RenderActor__changed
ScummV5_Controller_RenderActor__x_same:
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_Y
    bne ScummV5_Controller_RenderActor__y_diff
    jmp ScummV5_Controller_RenderActor__y_same
ScummV5_Controller_RenderActor__y_diff:
    jmp ScummV5_Controller_RenderActor__changed
ScummV5_Controller_RenderActor__y_same:
    sep #$20
    .a8
    .if SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $01
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_COSTUME
    bne ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_VISIBLE
    bne ScummV5_Controller_RenderActor__changed
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_FACING
    bne ScummV5_Controller_RenderActor__changed
    .endif
    sep #$20
    .a8
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    beq ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    beq ScummV5_Controller_RenderActor__retry_done
    jsl Same_VideoSurface_CanWrite_Far
    bcs ScummV5_Controller_RenderActor__retry_done
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
    lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    bne ScummV5_Controller_RenderActor__bounded_compose
    brl ScummV5_Controller_RenderActor__full_compose
ScummV5_Controller_RenderActor__bounded_compose:
    ; Restore only the union of the cached and current actor bounds.  The
    ; surface service owns clipping and room-source projection.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    bcs ScummV5_Controller_RenderActor__damage_x0_done
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
ScummV5_Controller_RenderActor__damage_x0_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    clc
    adc #$0020
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    clc
    adc #$0020
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    bcc ScummV5_Controller_RenderActor__damage_x1_done
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
ScummV5_Controller_RenderActor__damage_x1_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_Y
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    bcs ScummV5_Controller_RenderActor__damage_y0_done
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
ScummV5_Controller_RenderActor__damage_y0_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_Y
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc #$0040
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc #$0040
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    bcc ScummV5_Controller_RenderActor__damage_y1_done
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
ScummV5_Controller_RenderActor__damage_y1_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    sec
    sbc.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    sec
    sbc.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    ; RestoreRect takes packed pixel-space arguments: A=(y<<8)|x and
    ; X=(height<<8)|width.
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    and #$00FF
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    and #$00FF
    xba
    ora.l SAME_SCUMM_CONTROLLER_RENDER_DST
    pha
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    and #$00FF
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    and #$00FF
    xba
    ora.l SAME_SCUMM_CONTROLLER_RENDER_DST
    tax
    pla
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_A
    txa
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_X
    tax
    lda.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_A
    jsl Same_VideoSurface_RestoreRect_Far
    bcs ScummV5_Controller_RenderActor__restore_retry
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE
    jmp ScummV5_Controller_RenderActor__compose_actor
ScummV5_Controller_RenderActor__restore_retry:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__full_compose:
    sep #$20
    .a8
    ; The installed room visual is already the committed background when the
    ; initial actor pass is allowed to run. Restore only the actor rectangle
    ; instead of rebuilding the full 256x224 room inside one logical frame.
    ; This is still a target-neutral pixel-space surface operation.
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    clc
    adc #$0020
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0037
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    clc
    adc #$0040
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    sec
    sbc.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    sec
    sbc.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    sta.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    and #$00FF
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    and #$00FF
    xba
    ora.l SAME_SCUMM_CONTROLLER_RENDER_DST
    pha
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    and #$00FF
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DST
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    and #$00FF
    xba
    ora.l SAME_SCUMM_CONTROLLER_RENDER_DST
    tax
    pla
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_A
    txa
    sta.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_X
    tax
    lda.l SAME_SCUMM_CONTROLLER_RESTORE_CALL_A
    jsl Same_VideoSurface_RestoreRect_Far
    bcc ScummV5_Controller_RenderActor__compose_actor
    brl ScummV5_Controller_RenderActor__full_compose_retry
ScummV5_Controller_RenderActor__compose_actor:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0010
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
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
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ACTOR_BASE

    ; Frame zero is the source-defined standing pose. A moving actor uses the
    ; source-backed walking pose. Pose choice follows logical actor state, not
    ; a controller/validator frame counter, so a committed presentation can
    ; never regress to standing merely because observation crossed a phase.
    sep #$20
    .a8
    ; The late compositor consumes the coherent desired snapshot.  The live
    ; C31 movement byte and controller mode can belong to different logical
    ; phases; neither may force a pose before PublishActorVisual has published
    ; the corresponding actor state.
    lda.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_MODE_SAMPLE
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_RENDER_MOVING_SAMPLE
    bne ScummV5_Controller_RenderActor__walk
    ; Keep the destination sample diagnostic-only; it is not a pose selector.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DEST_SAMPLE
    lda.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    beq ScummV5_Controller_RenderActor__stand
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_X
    bne ScummV5_Controller_RenderActor__walk
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_Y
    bne ScummV5_Controller_RenderActor__walk
    jmp ScummV5_Controller_RenderActor__stand
ScummV5_Controller_RenderActor__walk:
    sep #$20
    .a8
    ; DESIRED_SELECT is the semantic snapshot published after movement.  The
    ; compositor must not rewrite it while selecting an attempted cooked
    ; frame: a busy/rejected PRESENT must leave the latest desired state
    ; intact for the next retry.
    rep #$20
    .a16
    lda #$0800
    bra ScummV5_Controller_RenderActor__frame_base
ScummV5_Controller_RenderActor__stand:
    sep #$20
    .a8
    ; Keep the published semantic pose immutable during composition.
    rep #$20
    .a16
    ; TEMP diagnostic: retain the selected standing value here; target
    ; selection tracing below distinguishes branch entry from later storage.
    lda #$0000
ScummV5_Controller_RenderActor__frame_base:
    rep #$20
    .a16
    sta.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ACTOR_FRAME
    ; Batch the actor's indexed pixels through the target-neutral surface
    ; service.  The previous path made 2048 far calls for every pose, which
    ; could starve the mainline before it reached the single PRESENT.
    sep #$20
    .a8
    lda #$00
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda #$80
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda #SCUMM_V5_ACTOR_SPRITE_BANK
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_BASE
    pha
    lda #$4020
    tax
    ; BlitIndexedRect takes A=(y<<8)|x, X=(height<<8)|width, and
    ; Y=source offset.  Keep the packed destination in A; loading the
    ; source into A here used to send the source offset as the destination
    ; and produced the striped actor at the wrong surface location.
    lda.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    tay
    pla
    jsl Same_VideoSurface_BlitIndexedRect_Far
    bcc ScummV5_Controller_RenderActor__blit_ok
    brl ScummV5_Controller_RenderActor__present_retry
ScummV5_Controller_RenderActor__blit_ok:

    ; Add the source-backed locker OBIM through the same indexed surface
    ; compositor before publishing.  State 1 is the authored opened form,
    ; so the ordinary room compose leaves the locker image absent.
    jsl ScummV5_Controller_RenderLocker_Far
    jsl ScummV5_Controller_DrawCursor_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_ACTIVE
    beq ScummV5_Controller_RenderActor__full_present
    jsl Same_VideoSurface_PushDamagePresent_Far
    bra ScummV5_Controller_RenderActor__present_result
ScummV5_Controller_RenderActor__full_compose_retry:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__full_present:
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_PushDirtyPresent_Far
ScummV5_Controller_RenderActor__present_result:
    sep #$20
    .a8
    bcc ScummV5_Controller_RenderActor__present_success
    brl ScummV5_Controller_RenderActor__present_retry
ScummV5_Controller_RenderActor__present_success:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    ; The fixture hook is interested in the in-flight walk proof.  Do not
    ; generate asynchronous notifications for the many ordinary standing
    ; redraws; a successful moving publication remains the exact witness.
    .if SAME_SCUMM_CONTROLLER_WITNESS
    ; The late compositor consumes the coherent desired snapshot.  The live
    ; movement byte may already have been cleared by the next scheduler phase;
    ; rereading it here would reject a successful walking composition.
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_VIDEO_DIAG_WITNESS_MOVING
    lda.l SAME_VIDEO_DIAG_WITNESS_ATTEMPTS
    inc
    sta.l SAME_VIDEO_DIAG_WITNESS_ATTEMPTS
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    beq ScummV5_Controller_RenderActor__skip_moving_witness
    ; The witness is a post-success publication record.  Capture the
    ; semantic state and the exact generation allocated by the accepted
    ; PRESENT; rejected/busy paths branch above and never reach this block.
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_FRAME
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_Y
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DEST_X
    lda.l SAME_SCUMM_MOVE_DEST_Y+2
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DEST_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_X
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_X
    lda.l SAME_VIDEO_SURFACE_DAMAGE_Y
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_Y
    lda.l SAME_VIDEO_SURFACE_DAMAGE_WIDTH
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_W
    lda.l SAME_VIDEO_SURFACE_DAMAGE_HEIGHT
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_DAMAGE_H
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_PRESENT
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_POSE
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_MOVING
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_VALID
    ; Publish the serial last so a write hook observes a complete witness.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_WITNESS_SERIAL
    inc
    sta.l SAME_SCUMM_CONTROLLER_WITNESS_SERIAL
    bra ScummV5_Controller_RenderActor__witness_done
    .endif
ScummV5_Controller_RenderActor__skip_moving_witness:
    .if SAME_SCUMM_CONTROLLER_WITNESS
    lda.l SAME_VIDEO_DIAG_WITNESS_SKIPS
    inc
    sta.l SAME_VIDEO_DIAG_WITNESS_SKIPS
    .endif
ScummV5_Controller_RenderActor__witness_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_Y
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    sta.l SAME_SCUMM_CONTROLLER_RENDER_FACING
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COSTUME
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VISIBLE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__present_retry:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_RETRY
    .if !(SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $02)
    ; Diagnostic pre-fix variant: emulate the historical incorrect cache
    ; commit after a rejected PRESENT for the independent bisect.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_Y
    .endif
    ; The attempted composition is not accepted state.  Leave the old
    ; position/pose key intact; the next writable frame retries the latest
    ; semantic state instead of pretending this generation was rendered.
ScummV5_Controller_RenderActor__done:
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

; Minimal data-driven room-object presentation for the controller fixture.
; Pixels are cooked from room 42's OBIM/SMAP; the surface service retains
; palette conversion, dirty publication, and presentation ownership.
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
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_STATES,x
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
    jsl Same_VideoSurface_WriteIndexedPixel_Far
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

.if SAME_VIDEO_SURFACE_AVAILABLE
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
    jsl Same_VideoSurface_WriteIndexedPixel_Far
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
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Controller_RenderCursor__changed_idle
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
    jsl Same_VideoSurface_WriteIndexedPixel_Far
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

.if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
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
    bne ScummV5_Controller_ShowHud__mode_not_verb
    jmp ScummV5_Controller_ShowHud__verb
ScummV5_Controller_ShowHud__mode_not_verb:
    sep #$20
    .a8
    cmp #$03
    bne ScummV5_Controller_ShowHud__mode_not_inspect
    jmp ScummV5_Controller_ShowHud__inspect
ScummV5_Controller_ShowHud__mode_not_inspect:
    sep #$20
    .a8
    cmp #$02
    bne ScummV5_Controller_ShowHud__mode_not_walk
    jmp ScummV5_Controller_ShowHud__walk
ScummV5_Controller_ShowHud__mode_not_walk:
    sep #$20
    .a8
    cmp #$04
    bne ScummV5_Controller_ShowHud__hover_mode
    jmp ScummV5_Controller_ShowHud__done
ScummV5_Controller_ShowHud__hover_mode:
    sep #$20
    .a8
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
    ; Keep this tiny fixture copy interrupt-safe and source-correct.  The
    ; selected HUD labels live in this code bank; the former MVN used a stale
    ; hard-coded source bank, so it copied unrelated ROM into the logical talk
    ; buffer and sent the overlay path through undefined text data.  A bounded
    ; byte copy retains the selected X source pointer and uses the current
    ; code bank explicitly.  It is also short enough that the normal NMI
    ; boundary remains independent of a block-move DBR/X/Y transition.
    lda.l SAME_SCUMM_TALK_RAW_LENGTH
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    phb
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$30
    .a16
    .i16
    ldx #$0000
    ldy #$0000
ScummV5_Controller_ShowHud__copy_loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$01
    bne ScummV5_Controller_ShowHud__copy_mode_not_verb
    jmp ScummV5_Controller_ShowHud__copy_verb
ScummV5_Controller_ShowHud__copy_mode_not_verb:
    sep #$20
    .a8
    cmp #$02
    bne ScummV5_Controller_ShowHud__copy_mode_not_walk
    jmp ScummV5_Controller_ShowHud__copy_walk
ScummV5_Controller_ShowHud__copy_mode_not_walk:
    sep #$20
    .a8
    cmp #$03
    bne ScummV5_Controller_ShowHud__copy_hover
    jmp ScummV5_Controller_ShowHud__copy_inspect
ScummV5_Controller_ShowHud__copy_hover:
    lda.l ScummV5_Controller_HudHover,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_verb:
    lda.l ScummV5_Controller_HudVerb,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_walk:
    lda.l ScummV5_Controller_HudWalk,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_inspect:
    lda.l ScummV5_Controller_HudInspect,x
ScummV5_Controller_ShowHud__copy_store:
    sta.w $7A30,y
    rep #$20
    .a16
    inx
    iny
    lda.l SAME_OVERLAY_PRODUCER_TEMP
    dec
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    bne ScummV5_Controller_ShowHud__copy_loop
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
    .if SAME_VIDEO_TEXT_SERVICE_AVAILABLE
    jsl Same_VideoText_ShowSegment_Far
    .endif
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
