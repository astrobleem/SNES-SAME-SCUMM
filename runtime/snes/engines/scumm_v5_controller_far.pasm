; Generic SCUMM controller presentation/input bridge. It consumes the normal
; SAME input latch, performs source-backed hotspot/verb selection, and
; publishes through the ordinary SCUMM sentence mailbox. Fixture-only startup
; and visual hooks remain explicitly gated below. It never writes C20 or game
; state directly.

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

; Room installation is the generic lifetime boundary for controller-local
; interaction state.  It does not inspect room numbers and does not cancel
; the canonical sentence mailbox; it only prevents a selection, HUD request,
; or cursor render cache from leaking across the newly installed room.
ScummV5_Controller_ResetInteractionOnRoomInstall_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_INPUT_TALK_OWNED_VALID
    sta.l SAME_SCUMM_CONTROLLER_ROOM_READY
    sta.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    sta.l SAME_SCUMM_INTERACTION_FLAGS
    sta.l SAME_SCUMM_INTERACTION_INDEX
    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_RETRY
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    sta.l SAME_SCUMM_INTERACTION_OBJECT
    sta.l SAME_SCUMM_INTERACTION_X
    sta.l SAME_SCUMM_INTERACTION_Y
    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    plp
    rtl

ScummV5_Controller_Frame_Far:
    php
    rep #$30
    .a16
    .i16
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    jsl ScummV5_ActorPose_ServiceCancel_Far
    .endif
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
    ; The room-68 acknowledgement/request path is fixture policy.  Once it
    ; has handed off through the ordinary room lifecycle, the controller
    ; below is generic and may consume any active cooked room's CDHD/VERB
    ; records.  It must not encode room 42 as the interaction boundary.
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$44
    beq ScummV5_Controller_Frame__room68
    .endif
    jmp ScummV5_Controller_Frame__generic_ready
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
ScummV5_Controller_Frame__generic_ready:
    sep #$20
    .a8
    ; Input_Poll tags every edge sampled while dialogue is active. Keep the
    ; token while talk remains active; after Talk_Stop, consume and drop the
    ; same edge before it can act on a retained selection. A newer edge has
    ; a different sequence and remains eligible.
    lda.l SAME_INPUT_TALK_OWNED_VALID
    beq ScummV5_Controller_Frame__talk_edge_unowned
    rep #$20
    .a16
    lda.l SAME_INPUT_EDGE_SEQUENCE
    cmp.l SAME_INPUT_TALK_OWNED_SEQUENCE
    sep #$20
    .a8
    bne ScummV5_Controller_Frame__talk_edge_superseded
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Controller_Frame__talk_edge_talk_stopped
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__talk_edge_talk_stopped:
    .a8
    lda #$00
    sta.l SAME_INPUT_TALK_OWNED_VALID
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__talk_edge_superseded:
    lda.l SAME_SCUMM_TALK_ACTIVE
    beq ScummV5_Controller_Frame__talk_edge_after_stop
    rep #$20
    .a16
    lda.l SAME_INPUT_EDGE_SEQUENCE
    sta.l SAME_INPUT_TALK_OWNED_SEQUENCE
    sep #$20
    .a8
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__talk_edge_after_stop:
    .a8
    lda #$00
    sta.l SAME_INPUT_TALK_OWNED_VALID
ScummV5_Controller_Frame__talk_edge_unowned:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_CONTROLLER
    ; The established room-installed callback arms interaction service after
    ; resetting room-local state. This is a lifecycle latch, not a room
    ; number or fixture-object policy.
    lda.l SAME_SCUMM_CONTROLLER_ROOM_READY
    bne ScummV5_Controller_Frame__fixture_armed
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__fixture_armed:
    .endif
    ; Logical room zero is the engine's null-scene sentinel on this v5
    ; runtime.  It is not a Fate room policy; all installed authored rooms
    ; remain eligible, including rooms added after the original fixture.
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_Controller_Frame__room_identity_ready
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__room_identity_ready:
    ; A null scene is the engine's generic pre-room sentinel.  Keep the
    ; controller inert until an authored room record has been installed;
    ; this is lifecycle state, not a Fate room-number policy.
    lda.l SAME_SCUMM_C22_NULL_SCENE
    beq ScummV5_Controller_Frame__scene_ready
    jmp ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__scene_ready:
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
    ; An action owns input until the ordinary SCUMM sentence lifecycle has
    ; released it.  This is deliberately independent of object state: a
    ; Look/Talk/Use action may be state-neutral, may not talk, and may not
    ; move an actor at all.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$02
    bne ScummV5_Controller_Frame__input_ready
    jmp ScummV5_Controller_Frame__action_pending
ScummV5_Controller_Frame__input_ready:
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
    jsl ScummV5_Controller_InvalidateSelectionOnCursorMove_Far
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
    jsl ScummV5_Controller_InvalidateSelectionOnCursorMove_Far
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
    jsl ScummV5_Controller_InvalidateSelectionOnCursorMove_Far
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
    jsl ScummV5_Controller_InvalidateSelectionOnCursorMove_Far
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
    jmp ScummV5_Controller_Frame__action_pending
ScummV5_Controller_Frame__mode_not_2:
    sep #$20
    .a8
    cmp #$03
    beq ScummV5_Controller_Frame__select_secondary
    cmp #$04
    beq ScummV5_Controller_Frame__select_secondary_ready
    cmp #$01
    beq ScummV5_Controller_Frame__mode_select_verb
    jmp ScummV5_Controller_Frame__mode_select_fallback
ScummV5_Controller_Frame__mode_select_verb:
    jmp ScummV5_Controller_Frame__select_verb

; Mode 3 is a generic secondary-object hover state.  B explicitly requests
; this state from a selected verb; one-object verbs remain unchanged and A
; submits them directly.  The active-room source hit-test remains the only
; source of object identity.
ScummV5_Controller_Frame__select_secondary:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    bne ScummV5_Controller_Frame__select_secondary_press
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__select_secondary_press:
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
    sbc #$0064
    sta.l SAME_SCUMM_INTERACTION_Y
    jsl ScummV5_Generic_Object_HitTest_Far
    bcc ScummV5_Controller_Frame__secondary_miss
    sep #$20
    .a8
    lda #$33
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    rep #$20
    .a16
    lda.l SAME_SCUMM_INTERACTION_OBJECT
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_CONTROLLER_MODE
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__secondary_miss:
    sep #$20
    .a8
    lda #$32
    sta.l SAME_SCUMM_CONTROLLER_DIAG
    jmp ScummV5_Controller_Frame__hud

ScummV5_Controller_Frame__select_secondary_ready:
    rep #$20
    .a16
    lda.l SAME_INPUT_PRESSED
    and #$0080
    bne ScummV5_Controller_Frame__select_secondary_submit
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__select_secondary_submit:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    lda.l SAME_SCUMM_CONTROLLER_VERB
    sta.l SAME_SCUMM_SENTENCE_API_VERB
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT1
    lda #$01
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
    sep #$20
    .a8
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
    bcc ScummV5_Controller_Frame__walk_miss
    brl ScummV5_Controller_Frame__hit_ok
ScummV5_Controller_Frame__walk_miss:
    ; A primary click on empty room space is the ordinary SCUMM walk command.
    ; It is deliberately separate from the sentence mailbox: object verbs
    ; still require an authored hit/verb, while a blank-room click starts the
    ; current ego's canonical box-routed movement request.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    beq ScummV5_Controller_Frame__walk_mode_ready
    brl ScummV5_Controller_Frame__walk_miss_done
ScummV5_Controller_Frame__walk_mode_ready:
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23B_VARIABLES+2 ; VAR_EGO
    and #$00FF
    cmp #$0020
    bcc ScummV5_Controller_Frame__walk_actor_in_range
    brl ScummV5_Controller_Frame__walk_miss_done
ScummV5_Controller_Frame__walk_actor_in_range:
    sep #$20
    .a8
    sta.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax                             ; ego actor * 64-byte C14 record
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    beq ScummV5_Controller_Frame__walk_miss_done
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_Controller_Frame__walk_miss_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_INTERACTION_X
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    lda.l SAME_SCUMM_INTERACTION_Y
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    ; Match the canonical walkActorTo opcode: actors that ignore boxes use a
    ; direct leg; ordinary actors resolve the point against active BOXD.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    beq ScummV5_Controller_Frame__walk_follow_boxes
    rep #$20
    .a16
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    lda.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    lda.l SAME_SCUMM_MOVE_ACTOR
    tax
    lda #$FF
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    bra ScummV5_Controller_Frame__walk_start
ScummV5_Controller_Frame__walk_follow_boxes:
    jsl ScummV5_PutActor_Adjust_Far
ScummV5_Controller_Frame__walk_start:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MOVE_QUERY_DIR
    jsr ScummV5_Movement_StartNormalized_Far
ScummV5_Controller_Frame__walk_miss_done:
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
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
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
    and #$0040 ; B enters generic secondary-object selection
    beq ScummV5_Controller_Frame__select_verb_cycle
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_MODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    jmp ScummV5_Controller_Frame__hud
ScummV5_Controller_Frame__select_verb_cycle:
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
    ; This is a semantic controller action. Authored talk ownership is gated
    ; before selection above; a failed/stale HUD presentation must not consume
    ; or suppress the user's sentence once that talk has ended.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID
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

ScummV5_Controller_Frame__action_pending:
    ; The sentence mailbox is consumed before C20 is spawned.  C20 and talk
    ; ownership are therefore both part of the generic completion boundary.
    sep #$20
    .a8
    lda.l SAME_SCUMM_SENTENCE_API_PENDING
    bne ScummV5_Controller_Frame__done
    lda.l SAME_SCUMM_C20_COUNT
    bne ScummV5_Controller_Frame__done
    lda.l SAME_SCUMM_TALK_ACTIVE
    bne ScummV5_Controller_Frame__done
    lda.l SAME_SCUMM_C19_STACK_POINTER
    bne ScummV5_Controller_Frame__done
    ; C31 movement is optional for the standalone controller service.  Its
    ; invalidated state deliberately does not promise cleared movement bytes;
    ; only an initialized actor-placement service may hold ACTION_PENDING.
    lda.l SAME_SCUMM_C31_INITIALIZED
    beq ScummV5_Controller_Frame__action_pending_reentry
    lda.l SAME_SCUMM_C31_ROOM
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_Controller_Frame__action_pending_reentry
    lda.l SAME_SCUMM_C31_MOVING+1
    bne ScummV5_Controller_Frame__done
ScummV5_Controller_Frame__action_pending_reentry:
    ; Do not let a stale selection become the next action. Re-run the generic
    ; source hit-test and authored-verb query at the current cursor.
    jsl ScummV5_Controller_RefreshSelection_Far
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    jmp ScummV5_Controller_Frame__done

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
    ; The target-neutral text service may reject a publish while the prior
    ; overlay generation is still converting.  Clear its per-call status,
    ; publish the current runtime C17/object names, and retain the request
    ; when publication was rejected.  This is a generic service retry; it
    ; does not inspect a particular verb, object, or object state.
    lda #$00
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    jsl ScummV5_Controller_ShowHud_Far
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    beq ScummV5_Controller_Frame__hud_done
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_Frame__hud_done:
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

; Revalidate the current cursor after an authored sentence completes.  The
; controller never assumes that an object survived, remained visible, or
; retained its verb set merely because it was selected before the action.
ScummV5_Controller_RefreshSelection_Far:
    php
    rep #$30
    .a16
    .i16
    ; Revalidate semantic selection by its source object record.  The cursor
    ; is presentation/input state and may have moved or been redrawn while
    ; the sentence was executing; re-hit-testing it would conflate display
    ; coordinates with the selected object's lifecycle.
    jsl ScummV5_Generic_Object_ValidateSelected_Far
    bcc ScummV5_Controller_RefreshSelection__clear
    ; ValidateSelected returns A8 on success.  Keep its carry result above,
    ; then restore the word width before copying the selected object ID and
    ; clearing the secondary-object word.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    jsl ScummV5_Generic_Verb_First_Far
    bcc ScummV5_Controller_RefreshSelection__clear
    sep #$20
    .a8
    lda.l SAME_SCUMM_VERB_RESULT
    sta.l SAME_SCUMM_CONTROLLER_VERB
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    plp
    rtl
ScummV5_Controller_RefreshSelection__clear:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_VERB
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_CONTROLLER_OBJECT+1
    sta.l SAME_SCUMM_VERB_OBJECT
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    plp
    rtl

; Moving the cursor after an action starts a new generic object-selection
; transaction.  Do not leave the previous object's verb selection active
; while the cursor is over another source object.  This is semantic state,
; not a room/object policy: the next A edge will run the normal CDHD hit test.
ScummV5_Controller_InvalidateSelectionOnCursorMove_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_MODE
    cmp #$03
    beq ScummV5_Controller_InvalidateSelectionOnCursorMove__secondary
    cmp #$04
    beq ScummV5_Controller_InvalidateSelectionOnCursorMove__secondary
    cmp #$01
    bne ScummV5_Controller_InvalidateSelectionOnCursorMove__done
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_VERB
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_OBJECT
    sta.l SAME_SCUMM_CONTROLLER_OBJECT+1
    sta.l SAME_SCUMM_VERB_OBJECT
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    jmp ScummV5_Controller_InvalidateSelectionOnCursorMove__done
ScummV5_Controller_InvalidateSelectionOnCursorMove__secondary:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_CONTROLLER_MODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SENTENCE_API_OBJECT2
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
ScummV5_Controller_InvalidateSelectionOnCursorMove__done:
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; Before C14's first semantic initialization its actor records are not a
    ; valid rendering source.  In particular, cold WRAM bytes must not be
    ; interpreted as a visible actor/costume and sent to the checked pose
    ; resolver (which would correctly reject a nonexistent directory key).
    ; Publish an empty visual snapshot until ordinary ActorOps initializes
    ; C14.  Room installation separately retires any prior surface damage.
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Controller_PublishActorVisual__c14_ready
    lda #$00
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    jml ScummV5_Controller_PublishActorVisual__done
ScummV5_Controller_PublishActorVisual__c14_ready:
    rep #$20
    .a16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_X
    lda.l SAME_SCUMM_C31_POSITIONS+2,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    .else
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
    .endif
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    rep #$20
    .a16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    lda.l SAME_SCUMM_MOVE_DEST_Y,x
    sta.l SAME_SCUMM_ACTOR_POSE_DEST_Y
    .else
    lda.l SAME_SCUMM_PUT_ACTOR_DEST_X+2
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_DEST
    lda.l SAME_SCUMM_MOVE_DEST_Y+2
    sta.l SAME_SCUMM_ACTOR_POSE_DEST_Y
    .endif
    ; C31 position and destination are committed before the movement flag is
    ; refreshed on this path.  Derive the visual pose from the coherent
    ; position/destination pair as well as the flag; otherwise the first
    ; position change publishes a standing pose at the new position, starts a
    ; long presentation conversion, and the actual walking snapshot arrives
    ; only after movement has completed.  FFFF is the authored no-destination
    ; sentinel, so it cannot make an idle actor appear to walk.
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ldx #SCUMM_V5_ACTOR_RENDER_ID
    lda.l SAME_SCUMM_C31_MOVING,x
    .else
    lda.l SAME_SCUMM_C31_MOVING+1
    .endif
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
    beq ScummV5_Controller_PublishActorVisual__same_x
    jml ScummV5_Controller_PublishActorVisual__done
ScummV5_Controller_PublishActorVisual__same_x:
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_Y
    beq ScummV5_Controller_PublishActorVisual__same_y
    jml ScummV5_Controller_PublishActorVisual__done
ScummV5_Controller_PublishActorVisual__same_y:
    .a16
    bra ScummV5_Controller_PublishActorVisual__standing
ScummV5_Controller_PublishActorVisual__destination_valid:
    cmp.l SAME_SCUMM_CONTROLLER_DESIRED_X
    beq ScummV5_Controller_PublishActorVisual__compare_destination_y
    jmp ScummV5_Controller_PublishActorVisual__moving
ScummV5_Controller_PublishActorVisual__compare_destination_y:
    lda.l SAME_SCUMM_ACTOR_POSE_DEST_Y
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; The host costume model advances its chore step with committed actor
    ; movement, while animateActor frame requests also advance over logical
    ; ticks. Movement advances walk cels; stationary explicit chores retain
    ; the time-driven step selected below rather than being reset here.
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    bne ScummV5_Controller_PublishActorVisual__movement_step_active
    lda.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+SCUMM_V5_ACTOR_RENDER_ID
    beq ScummV5_Controller_PublishActorVisual__reset_step
    rep #$20
    .a16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    cmp #$F4
    bcc ScummV5_Controller_PublishActorVisual__store_sample
    cmp #$FC
    bcc ScummV5_Controller_PublishActorVisual__store_sample
    bra ScummV5_Controller_PublishActorVisual__reset_step
ScummV5_Controller_PublishActorVisual__movement_step_active:
    lda.l SAME_SCUMM_ACTOR_POSE_OBSERVED
    beq ScummV5_Controller_PublishActorVisual__store_sample
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    cmp.l SAME_SCUMM_ACTOR_POSE_LAST_X
    bne ScummV5_Controller_PublishActorVisual__advance_step
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    cmp.l SAME_SCUMM_ACTOR_POSE_LAST_Y
    beq ScummV5_Controller_PublishActorVisual__store_sample
ScummV5_Controller_PublishActorVisual__advance_step:
    sep #$20
    .a8
    ; Use the compiler-derived chore loop bounds, not a fixed power-of-two
    ; mask. Costume loops may begin after one-shot commands and may have any
    ; length (including six or four steps).
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    beq ScummV5_Controller_PublishActorVisual__movement_step_unseeded
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    clc
    adc.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    bcs ScummV5_Controller_PublishActorVisual__movement_step_limit_max
    dec
    bra ScummV5_Controller_PublishActorVisual__movement_step_limit_ready
ScummV5_Controller_PublishActorVisual__movement_step_limit_max:
    .a8
    lda #$FF
ScummV5_Controller_PublishActorVisual__movement_step_limit_ready:
    .a8
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    cmp.l SAME_SCUMM_ACTOR_POSE_RESULT
    bcs ScummV5_Controller_PublishActorVisual__movement_step_wrap
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    inc
    bra ScummV5_Controller_PublishActorVisual__movement_step_ready
ScummV5_Controller_PublishActorVisual__movement_step_wrap:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    bra ScummV5_Controller_PublishActorVisual__movement_step_ready
ScummV5_Controller_PublishActorVisual__movement_step_unseeded:
    .a8
    ; Keep the request at source step zero until the selected frame has loaded
    ; its own loop metadata. This prevents stale bounds from another frame
    ; from selecting an absent pose during an animation transition.
    lda #$00
ScummV5_Controller_PublishActorVisual__movement_step_ready:
    .a8
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    bra ScummV5_Controller_PublishActorVisual__store_sample
ScummV5_Controller_PublishActorVisual__reset_step:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
ScummV5_Controller_PublishActorVisual__store_sample:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_OBSERVED
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_Y
    .endif
    rep #$20
    .a16
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda #SCUMM_V5_ACTOR_RENDER_ID
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    .else
    ldx #$0040
    .endif
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    rep #$20
    .a16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_ACTOR_FACINGS,x
    .else
    lda.l SAME_SCUMM_ACTOR_FACINGS+2
    .endif
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_Controller_PublishActorVisual__not_in_room
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    bra ScummV5_Controller_PublishActorVisual__visible_ready
ScummV5_Controller_PublishActorVisual__not_in_room:
    .a8
    lda #$00
ScummV5_Controller_PublishActorVisual__visible_ready:
    .else
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+64
    .endif
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    bne ScummV5_Controller_PublishActorVisual__walk_frame
    lda.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION+SCUMM_V5_ACTOR_RENDER_ID
    beq ScummV5_Controller_PublishActorVisual__stand_frame
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    cmp #$F4
    bcc ScummV5_Controller_PublishActorVisual__selected_frame
    cmp #$FC
    bcs ScummV5_Controller_PublishActorVisual__stand_frame
    ; Direction-only animateActor requests preserve the last selected chore.
    lda.l SAME_SCUMM_ACTOR_POSE_LAST_FRAME
    bra ScummV5_Controller_PublishActorVisual__selected_frame
ScummV5_Controller_PublishActorVisual__walk_frame:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x
    bra ScummV5_Controller_PublishActorVisual__selected_frame
ScummV5_Controller_PublishActorVisual__stand_frame:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
ScummV5_Controller_PublishActorVisual__selected_frame:
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    ; Direction index follows ScummV5Costume.direction_index exactly.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    cmp #$0047
    bcc ScummV5_Controller_PublishActorVisual__direction_3
    cmp #$006E
    bcc ScummV5_Controller_PublishActorVisual__direction_1
    cmp #$00FC
    bcc ScummV5_Controller_PublishActorVisual__direction_2
    cmp #$0122
    bcc ScummV5_Controller_PublishActorVisual__direction_0
ScummV5_Controller_PublishActorVisual__direction_3:
    sep #$20
    .a8
    lda #$03
    bra ScummV5_Controller_PublishActorVisual__direction_ready
ScummV5_Controller_PublishActorVisual__direction_1:
    sep #$20
    .a8
    lda #$01
    bra ScummV5_Controller_PublishActorVisual__direction_ready
ScummV5_Controller_PublishActorVisual__direction_2:
    sep #$20
    .a8
    lda #$02
    bra ScummV5_Controller_PublishActorVisual__direction_ready
ScummV5_Controller_PublishActorVisual__direction_0:
    sep #$20
    .a8
    lda #$00
ScummV5_Controller_PublishActorVisual__direction_ready:
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    cmp.l SAME_SCUMM_ACTOR_POSE_LAST_FRAME
    beq ScummV5_Controller_PublishActorVisual__same_pose_frame
    jml ScummV5_Controller_PublishActorVisual__reset_pose_step
ScummV5_Controller_PublishActorVisual__same_pose_frame:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    cmp.l SAME_SCUMM_ACTOR_POSE_LAST_DIRECTION
    beq ScummV5_Controller_PublishActorVisual__same_pose_direction
    jml ScummV5_Controller_PublishActorVisual__reset_pose_step
ScummV5_Controller_PublishActorVisual__same_pose_direction:
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    cmp.l SAME_SCUMM_ACTOR_POSE_LAST_COSTUME
    bne ScummV5_Controller_PublishActorVisual__reset_pose_step
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    beq ScummV5_Controller_PublishActorVisual__reset_pose_step
    ; The host advances costume commands at actorOps.animSpeed logical ticks.
    ; Stationary visible actors animate too; movement only selects walk chore.
    ; A zero native byte retains the engine default cadence of one tick.
    lda.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    inc
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIM_SPEED,x
    bne ScummV5_Controller_PublishActorVisual__animation_speed_ready
    lda #$01
ScummV5_Controller_PublishActorVisual__animation_speed_ready:
    cmp.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    bcc ScummV5_Controller_PublishActorVisual__advance_pose_step
    beq ScummV5_Controller_PublishActorVisual__advance_pose_step
    bra ScummV5_Controller_PublishActorVisual__save_pose_key
ScummV5_Controller_PublishActorVisual__advance_pose_step:
    .a8
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; Keep the in-flight pose key immutable until its checked bytes have been
    ; composed and the matching surface generation has been presented. The
    ; renderer clears POSE_STATE only after that commit. Advancing here while
    ; a read is pending repeatedly cancels ordinary animation requests and
    ; can prevent any actor frame from ever becoming visible.
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    bne ScummV5_Controller_PublishActorVisual__save_pose_key
    .endif
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    beq ScummV5_Controller_PublishActorVisual__pose_step_unseeded
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    clc
    adc.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    bcs ScummV5_Controller_PublishActorVisual__pose_step_limit_max
    dec
    bra ScummV5_Controller_PublishActorVisual__pose_step_limit_ready
ScummV5_Controller_PublishActorVisual__pose_step_limit_max:
    .a8
    lda #$FF
ScummV5_Controller_PublishActorVisual__pose_step_limit_ready:
    .a8
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    cmp.l SAME_SCUMM_ACTOR_POSE_RESULT
    bcs ScummV5_Controller_PublishActorVisual__step_wrap
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    inc
    bra ScummV5_Controller_PublishActorVisual__step_increment_ready
ScummV5_Controller_PublishActorVisual__step_wrap:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
ScummV5_Controller_PublishActorVisual__step_increment_ready:
    .a8
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    bra ScummV5_Controller_PublishActorVisual__save_pose_key
ScummV5_Controller_PublishActorVisual__pose_step_unseeded:
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    bra ScummV5_Controller_PublishActorVisual__save_pose_key
ScummV5_Controller_PublishActorVisual__reset_pose_step:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
ScummV5_Controller_PublishActorVisual__save_pose_key:
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_FRAME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_DIRECTION
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_COSTUME
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    jsl ScummV5_ActorPose_Cancel_Far
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    sta.l SAME_SCUMM_ACTOR_POSE_OBSERVED
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_ACTOR_RENDER_PALETTE_GENERATION
    lda #$0000
    sta.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sep #$20
    .a8
    .endif
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

.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE || SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; The late visual service may run before the scheduler has published its
    ; first coherent actor snapshot.  C14 is the owner of costume/facing
    ; semantics; until it is initialized, cold controller bytes are not a
    ; valid pose key and must not reach the checked pose-directory resolver.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Controller_RenderActor__c14_ready
    jml ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__c14_ready:
    .a8
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_ROOM_READY
    bne ScummV5_Controller_RenderActor__room_ok
    .else
    ; The legacy fixture compositor remains constrained to its authored test
    ; scene. Production actor rendering is room-agnostic and uses ROOM_READY.
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    beq ScummV5_Controller_RenderActor__room_ok
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_COSTUME
    bne ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_VISIBLE
    bne ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_POSE_FRAME
    bne ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_POSE_STEP
    bne ScummV5_Controller_RenderActor__changed
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_FACING
    bne ScummV5_Controller_RenderActor__changed
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    cmp.l SAME_SCUMM_ACTOR_RENDER_PALETTE_GENERATION
    bne ScummV5_Controller_RenderActor__changed
    .elseif SAME_SCUMM_CONTROLLER_BEHAVIOR_MASK & $01
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; An incomplete multi-span composition must be rebuilt from the room
    ; surface before retrying. Only a fully composed surface may be republished
    ; directly after a transient PRESENT failure.
    lda.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    bne ScummV5_Controller_RenderActor__retry_present_only
    jmp ScummV5_Controller_RenderActor__changed
ScummV5_Controller_RenderActor__retry_present_only:
    .a8
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    beq ScummV5_Controller_RenderActor__compose_ready
    jsl ScummV5_ActorPose_Ensure_Far
    bcs ScummV5_Controller_RenderActor__compose_ready
    ; A checked read is pending, unavailable, or failed. Never draw the old
    ; pose under a new canonical actor state and never fall back to ROM pixels.
    jmp ScummV5_Controller_RenderActor__done
ScummV5_Controller_RenderActor__compose_ready:
    .endif
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
    sbc #$0020
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0020
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
    sbc #$0020
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    clc
    adc #$0040
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc #$0020
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    clc
    adc #$0040
    cmp.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    bcc ScummV5_Controller_RenderActor__damage_x1_done
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
ScummV5_Controller_RenderActor__damage_x1_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_RENDER_Y
    sec
    sbc #$0040
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0040
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
    sbc #$0040
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc #$0048
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0040
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    clc
    adc #$0048
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
    sbc #$0020
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X0
    clc
    adc #$0040
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_X1
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc #$0040
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    lda.l SAME_SCUMM_CONTROLLER_RENDER_DAMAGE_Y0
    clc
    adc #$0048
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    jsl ScummV5_ActorPose_Compose_Far
    bcc ScummV5_Controller_RenderActor__blit_ok
    brl ScummV5_Controller_RenderActor__present_retry
    .else
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

    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; The source-backed pose is already validated into the bounded WRAM cache.
    lda #$0000
    .else
    ; Legacy controller fixture: retain its two baked ROM-backed poses.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    bne ScummV5_Controller_RenderActor__legacy_walk
    rep #$20
    .a16
    lda #$0000
    bra ScummV5_Controller_RenderActor__frame_base
ScummV5_Controller_RenderActor__legacy_walk:
    rep #$20
    .a16
    lda #$0800
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda #$00
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda #$10
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda #$7E
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    .else
    lda #$00
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda #$80
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda #SCUMM_V5_ACTOR_SPRITE_BANK
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ldy #$0000
    .else
    lda.l SAME_SCUMM_CONTROLLER_RENDER_SRC
    tay
    .endif
    pla
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    beq ScummV5_Controller_RenderActor__blit_ok
    rep #$20
    .a16
    .endif
    jsl Same_VideoSurface_BlitIndexedRect_Far
    bcc ScummV5_Controller_RenderActor__blit_ok
    brl ScummV5_Controller_RenderActor__present_retry
    .endif
ScummV5_Controller_RenderActor__blit_ok:

    ; Add the source-backed locker OBIM through the same indexed surface
    ; compositor before publishing.  State 1 is the authored opened form,
    ; so the ordinary room compose leaves the locker image absent.
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    jsl ScummV5_Controller_RenderLocker_Far
    jsl ScummV5_Controller_DrawCursor_Far
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    ; All source spans have now been synchronously copied to the surface.
    ; Actor scratch was released by Compose_Far; no pixel pointer survives.
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    .endif
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
    .if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_CONTROLLER_RENDER_POSE_FRAME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_CONTROLLER_RENDER_POSE_STEP
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_ACTOR_RENDER_PALETTE_GENERATION
    sep #$20
    .a8
    .endif
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

.if SAME_BUILD_SCUMM_MSU1_ACTOR_RENDERER
; Resolve a source pose/chunk row and fetch its checked source-slot bytes into
; the pending-room scratch. Actor ownership is exclusive with ROOM ownership;
; executable cache pages remain untouched. Carry is set only after this
; immutable request ticket has passed the provider's CRC validation.
ScummV5_ActorPose_Ensure_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    cmp #$01
    beq ScummV5_ActorPose_Ensure__request
    cmp #$02
    bne ScummV5_ActorPose_Ensure__not_cached
    jml ScummV5_ActorPose_Ensure__cached
ScummV5_ActorPose_Ensure__not_cached:
    .a8
    cmp #$03
    bne ScummV5_ActorPose_Ensure__not_cancelled
    jml ScummV5_ActorPose_Ensure__cancelled
ScummV5_ActorPose_Ensure__not_cancelled:
    .a8
    cmp #$FF
    bne ScummV5_ActorPose_Ensure__unknown_state
    jml ScummV5_ActorPose_Ensure__return
ScummV5_ActorPose_Ensure__unknown_state:
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jml ScummV5_ActorPose_Ensure__provider

ScummV5_ActorPose_Ensure__request:
    .a8
    jsl ScummV5_ActorPose_ProviderMatches_Far
    bcs ScummV5_ActorPose_Ensure__request_valid
    jml ScummV5_ActorPose_Ensure__lost_request
ScummV5_ActorPose_Ensure__request_valid:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_ActorPose_Ensure__request_not_reading
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__request_not_reading:
    .a8
    cmp #SAME_MSU1_STATE_READ_OK
    beq ScummV5_ActorPose_Ensure__request_done
    cmp #SAME_MSU1_STATE_ERROR
    bne ScummV5_ActorPose_Ensure__request_not_error
    jml ScummV5_ActorPose_Ensure__read_error
ScummV5_ActorPose_Ensure__request_not_error:
    .a8
    cmp #SAME_MSU1_STATE_INITIALIZING
    bne ScummV5_ActorPose_Ensure__request_not_initializing
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__request_not_initializing:
    .a8
    cmp #SAME_MSU1_STATE_TAIL_CHECK
    bne ScummV5_ActorPose_Ensure__request_other_state
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__request_other_state:
    .a8
    jml ScummV5_ActorPose_Ensure__lost_request

ScummV5_ActorPose_Ensure__request_done:
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    cmp.l SAME_SCUMM_ACTOR_POSE_COSTUME
    beq ScummV5_ActorPose_Ensure__request_same_costume
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__request_same_costume:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    cmp.l SAME_SCUMM_ACTOR_POSE_FRAME
    beq ScummV5_ActorPose_Ensure__request_same_frame
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__request_same_frame:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    cmp.l SAME_SCUMM_ACTOR_POSE_DIRECTION
    beq ScummV5_ActorPose_Ensure__request_same_direction
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__request_same_direction:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    cmp.l SAME_SCUMM_ACTOR_POSE_ACCEPTED_STEP
    beq ScummV5_ActorPose_Ensure__request_same_step
    jml ScummV5_ActorPose_Ensure__discard_completed
ScummV5_ActorPose_Ensure__request_same_step:
    .a8
    jsl ScummV5_ActorPose_MapPalette_Far
    bcc ScummV5_ActorPose_Ensure__mapped
    jml ScummV5_ActorPose_Ensure__read_error
ScummV5_ActorPose_Ensure__mapped:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    jml ScummV5_ActorPose_Ensure__return

ScummV5_ActorPose_Ensure__cached:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    beq ScummV5_ActorPose_Ensure__cached_empty
    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne ScummV5_ActorPose_Ensure__stale_cache
    lda.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    cmp.l SAME_SCUMM_ACTOR_POSE_GENERATION
    bne ScummV5_ActorPose_Ensure__stale_cache
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    bne ScummV5_ActorPose_Ensure__stale_cache
    bra ScummV5_ActorPose_Ensure__cached_key
ScummV5_ActorPose_Ensure__cached_empty:
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne ScummV5_ActorPose_Ensure__stale_cache
    lda.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    cmp.l SAME_SCUMM_ACTOR_POSE_GENERATION
    bne ScummV5_ActorPose_Ensure__stale_cache
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    bne ScummV5_ActorPose_Ensure__stale_cache
ScummV5_ActorPose_Ensure__cached_key:
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    cmp.l SAME_SCUMM_ACTOR_POSE_COSTUME
    beq ScummV5_ActorPose_Ensure__cached_same_costume
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__cached_same_costume:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    cmp.l SAME_SCUMM_ACTOR_POSE_FRAME
    beq ScummV5_ActorPose_Ensure__cached_same_frame
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__cached_same_frame:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    cmp.l SAME_SCUMM_ACTOR_POSE_DIRECTION
    beq ScummV5_ActorPose_Ensure__cached_same_direction
    jml ScummV5_ActorPose_Ensure__restart
ScummV5_ActorPose_Ensure__cached_same_direction:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    cmp.l SAME_SCUMM_ACTOR_POSE_ACCEPTED_STEP
    beq ScummV5_ActorPose_Ensure__cached_same_step
    jml ScummV5_ActorPose_Ensure__discard_completed
ScummV5_ActorPose_Ensure__cached_same_step:
    .a8
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    jml ScummV5_ActorPose_Ensure__return

ScummV5_ActorPose_Ensure__stale_cache:
    .a8
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jml ScummV5_ActorPose_Ensure__provider
ScummV5_ActorPose_Ensure__restart:
    .a8
    ; A changed pose key may replace a completed checked pose, but only after
    ; the provider has left its transfer states (the caller reaches here from
    ; READ_OK or a READY cache). A live asynchronous destination is never
    ; released or reused early.
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
ScummV5_ActorPose_Ensure__provider:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READY
    beq ScummV5_ActorPose_Ensure__find
    cmp #SAME_MSU1_STATE_READ_OK
    beq ScummV5_ActorPose_Ensure__find
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_ActorPose_Ensure__provider_not_reading
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_not_reading:
    .a8
    cmp #SAME_MSU1_STATE_INITIALIZING
    bne ScummV5_ActorPose_Ensure__provider_not_initializing
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_not_initializing:
    .a8
    cmp #SAME_MSU1_STATE_TAIL_CHECK
    bne ScummV5_ActorPose_Ensure__provider_not_tail_check
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_not_tail_check:
    .a8
    cmp #SAME_MSU1_STATE_ERROR
    bne ScummV5_ActorPose_Ensure__provider_not_error
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_not_error:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    cmp #$FF
    beq ScummV5_ActorPose_Ensure__provider_no_program_read
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_no_program_read:
    .a8
    lda.l SAME_SCUMM_MSU_ROOM_STATE
    cmp #SCUMM_MSU_ROOM_REQUESTED
    bne ScummV5_ActorPose_Ensure__provider_room_not_requested
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_room_not_requested:
    .a8
    cmp #SCUMM_MSU_ROOM_READING
    bne ScummV5_ActorPose_Ensure__provider_room_not_reading
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_room_not_reading:
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    beq ScummV5_ActorPose_Ensure__provider_page_unpinned
    jml ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__provider_page_unpinned:
    .a8
    jml ScummV5_ActorPose_Ensure__find

ScummV5_ActorPose_Ensure__find:
    rep #$20
    .a16
    ldx #$0000
ScummV5_ActorPose_Ensure__find_loop:
    .a16
    .i16
    cpx #(SCUMM_V5_ACTOR_POSE_COUNT*SCUMM_V5_ACTOR_POSE_RECORD_SIZE)
    bcc ScummV5_ActorPose_Ensure__find_in_range
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__find_in_range:
    .a16
    .i16
    txa
    sta.l SAME_SCUMM_ACTOR_POSE_ROW
    sep #$20
    .a8
    lda.l ScummV5_ActorPoseDirectory,x
    cmp.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    bne ScummV5_ActorPose_Ensure__next
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    cmp.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    bne ScummV5_ActorPose_Ensure__next
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    cmp.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    bne ScummV5_ActorPose_Ensure__next
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    cmp.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    beq ScummV5_ActorPose_Ensure__row_found_v2
ScummV5_ActorPose_Ensure__next:
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #SCUMM_V5_ACTOR_POSE_RECORD_SIZE
    tax
    brl ScummV5_ActorPose_Ensure__find_loop

ScummV5_ActorPose_Ensure__row_found_v2:
    ; Pose record v2: key[4], palette, loop[2], first-chunk/count[4],
    ; signed half-open bounds[8], reserved[5].
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #$0005
    tax
    sep #$20
    .a8
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #$0004
    tax
    sep #$20
    .a8
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_INDEX
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_PALETTE_INDEX
    and #$00FF
    asl
    sta.l SAME_SCUMM_ACTOR_PALETTE_ROW
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_ACTOR_PALETTE_ROW
    sta.l SAME_SCUMM_ACTOR_PALETTE_ROW ; index * 34
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #$000B
    tax
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_BOUNDS_LEFT
    inx
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_BOUNDS_TOP
    inx
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_BOUNDS_RIGHT
    inx
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_POSE_BOUNDS_BOTTOM
    jsl ScummV5_ActorPose_ValidateBounds_Far
    bcc ScummV5_ActorPose_Ensure__bounds_valid
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__bounds_valid:
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #$0007
    tax
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_CHUNK_FIRST
    inx
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    cmp #$0001
    beq ScummV5_ActorPose_Ensure__chunk_count_valid
    cmp #$0000
    beq ScummV5_ActorPose_Ensure__empty_pose
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__empty_pose:
    ; Empty decoded poses are valid transparent frames. They have a complete
    ; semantic pose key but own no scratch buffer and issue no provider read.
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_ACTOR_POSE_COSTUME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_ACTOR_POSE_FRAME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    sta.l SAME_SCUMM_ACTOR_POSE_DIRECTION
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_ACTOR_POSE_ACCEPTED_STEP
    rep #$20
    .a16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    jml ScummV5_ActorPose_Ensure__return
ScummV5_ActorPose_Ensure__chunk_count_valid:
    ; Current authentic costume selection measures at one bounded chunk per
    ; pose. Larger generic poses remain representable in the package and are
    ; explicitly rejected until the incremental multi-chunk compositor lands.
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_CHUNK_FIRST
    cmp #SCUMM_V5_ACTOR_CHUNK_COUNT
    bcc ScummV5_ActorPose_Ensure__chunk_directory_index_ok
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__chunk_directory_index_ok:
    lda.l SAME_SCUMM_ACTOR_CHUNK_FIRST
    asl
    asl
    asl
    asl
    tax
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_SCUMM_ACTOR_SPAN_FIRST
    inx
    inx
    lda.l ScummV5_ActorPoseChunkDirectory,x
    sta.l SAME_SCUMM_ACTOR_SPAN_COUNT
    lda.l SAME_SCUMM_ACTOR_SPAN_FIRST
    and #$F000
    xba
    lsr
    lsr
    lsr
    lsr
    sta.l SAME_SCUMM_ACTOR_SPAN_PAGE
    lda.l SAME_SCUMM_ACTOR_SPAN_FIRST
    and #$0FFF
    asl
    asl
    asl
    sta.l SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET
    lda.l SAME_SCUMM_ACTOR_SPAN_COUNT
    bne ScummV5_ActorPose_Ensure__span_count_nonzero
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__span_count_nonzero:
    .a16
    cmp #$0801
    bcc ScummV5_ActorPose_Ensure__span_count_ok
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__span_count_ok:
    ; SPAN_PAGE is a byte immediately followed by SPAN_LOCAL_OFFSET. Compare
    ; only that byte: an A16 read would fold the offset's low byte into the
    ; page number and reject valid descriptors (or accept malformed ones).
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SPAN_PAGE
    cmp #SCUMM_V5_ACTOR_SPAN_BANK_COUNT
    bcc ScummV5_ActorPose_Ensure__span_page_ok
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__span_page_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET
    sta.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    lda.l SAME_SCUMM_ACTOR_SPAN_COUNT
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    bcc ScummV5_ActorPose_Ensure__span_range_no_wrap
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__span_range_no_wrap:
    .a16
    cmp #$8001
    bcc ScummV5_ActorPose_Ensure__span_range_ok
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__span_range_ok:
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bne ScummV5_ActorPose_Ensure__chunk_length_nonzero
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__chunk_length_nonzero:
    .a16
    cmp #$0801
    bcc ScummV5_ActorPose_Ensure__chunk_length_ok
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__chunk_length_ok:
    .a16
    lda.l SAME_MSU1_REQUEST_OFFSET
    clc
    adc #SAME_MSU1_SECTION_SC5ACT_OFFSET_LOW_WORD
    sta.l SAME_MSU1_REQUEST_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    adc #SAME_MSU1_SECTION_SC5ACT_OFFSET_HIGH_WORD
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    lda.l SAME_SCUMM_ACTOR_PALETTE_ROW
    tax
    sep #$20
    .a8
    lda.l ScummV5_ActorPaletteDirectory,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_SIZE
    inx
    lda.l ScummV5_ActorPaletteDirectory,x
    beq ScummV5_ActorPose_Ensure__palette_high_zero
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__palette_high_zero:
    lda.l SAME_SCUMM_ACTOR_PALETTE_SIZE
    bne ScummV5_ActorPose_Ensure__palette_nonzero
    jml ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__palette_nonzero:
    .a8
    cmp #$21
    bcc ScummV5_ActorPose_Ensure__palette_valid
    jmp ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__palette_valid:
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_OFFSET
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET+2
    lda.l SAME_MSU1_EXPECTED_CRC
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC
    lda.l SAME_MSU1_EXPECTED_CRC+2
    sta.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC+2
    lda.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    sta.l SAME_MSU1_REQUEST_LENGTH
    lda #$0000
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    inc
    bne ScummV5_ActorPose_Ensure__ticket_epoch
    inc
ScummV5_ActorPose_Ensure__ticket_epoch:
    sta.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    lda.l SAME_SCUMM_ACTOR_TICKET_SERIAL
    inc
    bne ScummV5_ActorPose_Ensure__ticket_serial
    inc
ScummV5_ActorPose_Ensure__ticket_serial:
    sta.l SAME_SCUMM_ACTOR_TICKET_SERIAL
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_NONE
    beq ScummV5_ActorPose_Ensure__scratch_free
    jmp ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__scratch_free:
    .a8
    lda #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    lda #<SAME_SCUMM_ACTOR_POSE_BUFFER
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_SCUMM_ACTOR_POSE_BUFFER
    sta.l SAME_MSU1_DESTINATION+1
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
    sta.l SAME_MSU1_DESTINATION+2
    rep #$20
    .a16
    lda #SAME_SCUMM_ACTOR_POSE_BUFFER_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    sta.l SAME_MSU1_FLAGS
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_ACTOR_POSE_COSTUME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_ACTOR_POSE_FRAME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    sta.l SAME_SCUMM_ACTOR_POSE_DIRECTION
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_ACTOR_POSE_ACCEPTED_STEP
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jsl Same_Msu1_ReadBegin_FarEntry
    bcs ScummV5_ActorPose_Ensure__read_error
    bra ScummV5_ActorPose_Ensure__pending

ScummV5_ActorPose_Ensure__lost_request:
    .a8
    ; A ticket mismatch does not authorize reuse while the provider may still
    ; be writing its destination. Drain the provider first; room requests have
    ; priority and will claim the shared staging only after this owner clears.
    lda #$03
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jsl ScummV5_ActorPose_ServiceCancel_Far
    bra ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__discard_completed:
    .a8
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    bra ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__read_error:
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    bra ScummV5_ActorPose_Ensure__error
ScummV5_ActorPose_Ensure__error:
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    lda #$FF
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    bra ScummV5_ActorPose_Ensure__return
ScummV5_ActorPose_Ensure__pending:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_RESULT
    bra ScummV5_ActorPose_Ensure__return
ScummV5_ActorPose_Ensure__cancelled:
    jsl ScummV5_ActorPose_ServiceCancel_Far
    bra ScummV5_ActorPose_Ensure__pending
ScummV5_ActorPose_Ensure__return:
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    lda.l SAME_SCUMM_ACTOR_POSE_RESULT
    beq ScummV5_ActorPose_Ensure__carry_clear
    sec
    rtl
ScummV5_ActorPose_Ensure__carry_clear:
    clc
    rtl

; Validate signed half-open pose bounds against the generic 64x72 damage
; envelope (x=-32..32, y=-64..8). Equality is valid for an empty pose.
ScummV5_ActorPose_ValidateBounds_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_LEFT
    eor #$8000
    cmp #$7FE0
    bcc ScummV5_ActorPose_ValidateBounds__bad
    cmp #$8021
    bcs ScummV5_ActorPose_ValidateBounds__bad
    sta.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_RIGHT
    eor #$8000
    cmp #$7FE0
    bcc ScummV5_ActorPose_ValidateBounds__bad
    cmp #$8021
    bcs ScummV5_ActorPose_ValidateBounds__bad
    cmp.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    bcc ScummV5_ActorPose_ValidateBounds__bad
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_TOP
    eor #$8000
    cmp #$7FC0
    bcc ScummV5_ActorPose_ValidateBounds__bad
    cmp #$8009
    bcs ScummV5_ActorPose_ValidateBounds__bad
    sta.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_BOTTOM
    eor #$8000
    cmp #$7FC0
    bcc ScummV5_ActorPose_ValidateBounds__bad
    cmp #$8009
    bcs ScummV5_ActorPose_ValidateBounds__bad
    cmp.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    bcc ScummV5_ActorPose_ValidateBounds__bad
    pla
    plp
    clc
    rtl
ScummV5_ActorPose_ValidateBounds__bad:
    pla
    plp
    sec
    rtl

; Map checked nonzero source palette slots to final indexed colors in the
; ACTOR-owned scratch. This runs only after the provider's whole-chunk CRC and
; immutable ticket have been accepted. Output color zero remains opaque.
ScummV5_ActorPose_MapPalette_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    beq ScummV5_ActorPose_MapPalette__owner_ok
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__owner_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bne ScummV5_ActorPose_MapPalette__length_nonzero
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__length_nonzero:
    .a16
    cmp #SAME_SCUMM_ACTOR_POSE_BUFFER_SIZE+1
    bcc ScummV5_ActorPose_MapPalette__length_bounded
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__length_bounded:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_ACTOR_PIXEL_CURSOR
ScummV5_ActorPose_MapPalette__loop:
    .a16
    lda.l SAME_SCUMM_ACTOR_PIXEL_CURSOR
    cmp.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bcc ScummV5_ActorPose_MapPalette__loop_body
    jml ScummV5_ActorPose_MapPalette__done
ScummV5_ActorPose_MapPalette__loop_body:
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
    bne ScummV5_ActorPose_MapPalette__slot_nonzero
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__slot_nonzero:
    sta.l SAME_SCUMM_ACTOR_PALETTE_SLOT
    cmp.l SAME_SCUMM_ACTOR_PALETTE_SIZE
    bcc ScummV5_ActorPose_MapPalette__slot_in_palette
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__slot_in_palette:
    .a8
    cmp #$20
    bcc ScummV5_ActorPose_MapPalette__slot_representable
    jml ScummV5_ActorPose_MapPalette__bad
ScummV5_ActorPose_MapPalette__slot_representable:
    .a8
    and #$07
    tax
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_MASK_BIT
    lda.l SAME_SCUMM_ACTOR_PALETTE_SLOT
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID,x
    and.l SAME_SCUMM_ACTOR_PALETTE_MASK_BIT
    beq ScummV5_ActorPose_MapPalette__costume_color
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_PALETTE_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+(SCUMM_V5_ACTOR_RENDER_ID*$40)+SAME_SCUMM_C14_A_PALETTE,x
    bra ScummV5_ActorPose_MapPalette__store_color
ScummV5_ActorPose_MapPalette__costume_color:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_PALETTE_SLOT
    and #$00FF
    clc
    adc.l SAME_SCUMM_ACTOR_PALETTE_ROW
    adc #$0002
    tax
    sep #$20
    .a8
    lda.l ScummV5_ActorPaletteDirectory,x
ScummV5_ActorPose_MapPalette__store_color:
    .a8
    sta.l SAME_SCUMM_ACTOR_PALETTE_COLOR
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_PIXEL_CURSOR
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_PALETTE_COLOR
    sta.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_PIXEL_CURSOR
    inc
    sta.l SAME_SCUMM_ACTOR_PIXEL_CURSOR
    brl ScummV5_ActorPose_MapPalette__loop
ScummV5_ActorPose_MapPalette__done:
    .a16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_ActorPose_MapPalette__bad:
    .a8
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; Fetch one 8-byte signed span descriptor from the generated banked ROM table.
; PAGE and byte cursor were range-checked before any surface write.
ScummV5_ActorPose_LoadSpan_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SPAN_PAGE
    clc
    adc #SCUMM_V5_ACTOR_SPAN_FIRST_BANK
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    tax
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_X
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_Y
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    plb
    ply
    plx
    pla
    plp
    clc
    rtl

; Compose one complete checked source pose into the existing indexed surface.
; The current FATE costume directory has at most one <=2 KiB chunk per pose;
; larger directory entries fail explicitly until the asynchronous multi-chunk
; presentation state machine is extended. No code-cache page or ROM pixel
; fallback is used here.
ScummV5_ActorPose_Compose_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    bne ScummV5_ActorPose_Compose__visible
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    jml ScummV5_ActorPose_Compose__complete
ScummV5_ActorPose_Compose__visible:
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    cmp #$02
    beq ScummV5_ActorPose_Compose__ready
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__ready:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    beq ScummV5_ActorPose_Compose__room_epoch_ok
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__room_epoch_ok:
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    cmp.l SAME_SCUMM_ACTOR_POSE_GENERATION
    beq ScummV5_ActorPose_Compose__costume_epoch_ok
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__costume_epoch_ok:
    .a16
    lda.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    bne ScummV5_ActorPose_Compose__chunk_nonempty
    jml ScummV5_ActorPose_Compose__empty
ScummV5_ActorPose_Compose__chunk_nonempty:
    .a16
    cmp #$0001
    beq ScummV5_ActorPose_Compose__one_chunk
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__one_chunk:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    beq ScummV5_ActorPose_Compose__owner_ok
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__owner_ok:
    .a8
    rep #$20
    .a16
    ; Project the logical actor foot through the established surface viewport.
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_ACTOR_FOOT_SCREEN_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    sec
    sbc.l SAME_SCUMM_C14_ACTORS+(SCUMM_V5_ACTOR_RENDER_ID*$40)+SAME_SCUMM_C14_A_ELEVATION
    sta.l SAME_SCUMM_ACTOR_FOOT_SCREEN_Y
    ; Validate every span before touching the surface. A malformed descriptor
    ; therefore cannot publish a prefix of an actor.
    lda.l SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_COUNT
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
ScummV5_ActorPose_Compose__validate_loop:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    bne ScummV5_ActorPose_Compose__validate_body
    jml ScummV5_ActorPose_Compose__validated
ScummV5_ActorPose_Compose__validate_body:
    jsl ScummV5_ActorPose_LoadSpan_Far
    lda.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    bne ScummV5_ActorPose_Compose__span_nonempty
    jml ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__span_nonempty:
    .a16
    cmp #$0801
    bcc ScummV5_ActorPose_Compose__span_length_ok
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__span_length_ok:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    bcc ScummV5_ActorPose_Compose__source_no_wrap
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__source_no_wrap:
    .a16
    cmp.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bcc ScummV5_ActorPose_Compose__source_in_chunk
    beq ScummV5_ActorPose_Compose__source_in_chunk
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__source_in_chunk:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    eor #$8000
    sta.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_LEFT
    eor #$8000
    cmp.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    bcc ScummV5_ActorPose_Compose__x_after_left
    beq ScummV5_ActorPose_Compose__x_after_left
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__x_after_left:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    eor #$8000
    sta.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_RIGHT
    eor #$8000
    cmp.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    bcs ScummV5_ActorPose_Compose__x_before_right
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__x_before_right:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    eor #$8000
    sta.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_TOP
    eor #$8000
    cmp.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    bcc ScummV5_ActorPose_Compose__y_after_top
    beq ScummV5_ActorPose_Compose__y_after_top
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__y_after_top:
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_BOUNDS_BOTTOM
    eor #$8000
    cmp.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    bcs ScummV5_ActorPose_Compose__bottom_not_before_y
    jml ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__bottom_not_before_y:
    .a16
    bne ScummV5_ActorPose_Compose__y_before_bottom
    jml ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__y_before_bottom:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    clc
    adc #$0008
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    dec
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    brl ScummV5_ActorPose_Compose__validate_loop
ScummV5_ActorPose_Compose__validated:
    .a16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_ActorPose_Compose__surface_ready
    jmp ScummV5_ActorPose_Compose__retry
ScummV5_ActorPose_Compose__surface_ready:
    .a16
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES && (SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D)
    ; Save the checked room pixels under this pose before any actor span writes.
    ; The surface service bounds the snapshot by the exact active-record tail.
    jsl Same_VideoSurface_CaptureActorUnderlay_Far
    bcc ScummV5_ActorPose_Compose__underlay_ready
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__underlay_ready:
    .a16
.endif
    ; The pending window is the checked source, not a retained actor cache.
    sep #$20
    .a8
    lda #<SAME_SCUMM_ACTOR_POSE_BUFFER
    sta SAME_VIDEO_SURFACE_DP_SOURCE
    lda #>SAME_SCUMM_ACTOR_POSE_BUFFER
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$01
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
    sta SAME_VIDEO_SURFACE_DP_SOURCE+$02
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_LOCAL_OFFSET
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_COUNT
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
ScummV5_ActorPose_Compose__draw_loop:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    bne ScummV5_ActorPose_Compose__draw_body
    jml ScummV5_ActorPose_Compose__draw_done
ScummV5_ActorPose_Compose__draw_body:
    jsl ScummV5_ActorPose_LoadSpan_Far
    lda.l SAME_SCUMM_ACTOR_FOOT_SCREEN_Y
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_Y
    bpl ScummV5_ActorPose_Compose__draw_y_nonnegative
    jml ScummV5_ActorPose_Compose__draw_skip
ScummV5_ActorPose_Compose__draw_y_nonnegative:
    .a16
    cmp #$00E0
    bcc ScummV5_ActorPose_Compose__draw_y_in_range
    jml ScummV5_ActorPose_Compose__draw_skip
ScummV5_ActorPose_Compose__draw_y_in_range:
    .a16
    sta.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    lda.l SAME_SCUMM_ACTOR_FOOT_SCREEN_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_X
    sta.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    bmi ScummV5_ActorPose_Compose__draw_skip
    cmp #$0100
    bcc ScummV5_ActorPose_Compose__right_ready
    lda #$0100
ScummV5_ActorPose_Compose__right_ready:
    .a16
    sta.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    lda.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    bmi ScummV5_ActorPose_Compose__left_zero
    cmp #$0100
    bcs ScummV5_ActorPose_Compose__draw_skip
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
    bra ScummV5_ActorPose_Compose__left_ready
ScummV5_ActorPose_Compose__left_zero:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
ScummV5_ActorPose_Compose__left_ready:
    .a16
    lda.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    cmp.l SAME_SCUMM_ACTOR_CLIP_LEFT
    bcc ScummV5_ActorPose_Compose__draw_skip
    beq ScummV5_ActorPose_Compose__draw_skip
    sec
    sbc.l SAME_SCUMM_ACTOR_CLIP_LEFT
    sta.l SAME_SCUMM_ACTOR_CLIP_COUNT
    lda.l SAME_SCUMM_ACTOR_CLIP_LEFT
    sec
    sbc.l SAME_SCUMM_ACTOR_SPAN_RAW_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    sta.l SAME_SCUMM_ACTOR_CLIP_SOURCE
    clc
    adc.l SAME_SCUMM_ACTOR_CLIP_COUNT
    bcc ScummV5_ActorPose_Compose__clip_source_no_wrap
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__clip_source_no_wrap:
    .a16
    cmp.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bcc ScummV5_ActorPose_Compose__clip_source_valid
    beq ScummV5_ActorPose_Compose__clip_source_valid
    jmp ScummV5_ActorPose_Compose__invalid
ScummV5_ActorPose_Compose__clip_source_valid:
    .a16
    lda.l SAME_SCUMM_ACTOR_CLIP_COUNT
    tax
    lda.l SAME_SCUMM_ACTOR_CLIP_SOURCE
    tay
    lda.l SAME_SCUMM_ACTOR_POSE_VALIDATE_TEMP
    xba
    and #$FF00
    ora.l SAME_SCUMM_ACTOR_CLIP_LEFT
    jsl Same_VideoSurface_BlitCheckedOpaqueRun_Far
    bcc ScummV5_ActorPose_Compose__draw_skip
    jmp ScummV5_ActorPose_Compose__retry
ScummV5_ActorPose_Compose__draw_skip:
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    clc
    adc #$0008
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    dec
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    brl ScummV5_ActorPose_Compose__draw_loop
ScummV5_ActorPose_Compose__draw_done:
    .a16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
ScummV5_ActorPose_Compose__complete:
    .a8
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_ActorPose_Compose__empty:
    .a16
    sep #$20
    .a8
    jmp ScummV5_ActorPose_Compose__draw_done
ScummV5_ActorPose_Compose__retry:
    .a16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl
ScummV5_ActorPose_Compose__invalid:
    .a8
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    lda #$FF
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; The provider has one global cursor. Accept completion only if its full
; section offset, CRC, length, and destination still identify this pose.
ScummV5_ActorPose_ProviderMatches_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_OFFSET
    cmp.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    cmp.l SAME_SCUMM_ACTOR_POSE_REQUEST_OFFSET+2
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_EXPECTED_CRC
    cmp.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_EXPECTED_CRC+2
    cmp.l SAME_SCUMM_ACTOR_POSE_REQUEST_CRC+2
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    bne ScummV5_ActorPose_ProviderMatches__no
    ; DESTINATION is a 24-bit pointer. Compare its three bytes in A8 mode;
    ; the earlier A16 loads compared a 16-bit value such as $13C4 with the
    ; one-byte <address immediate $C4 and rejected every valid actor ticket.
    sep #$20
    .a8
    lda.l SAME_MSU1_DESTINATION
    cmp #<SAME_SCUMM_ACTOR_POSE_BUFFER
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_DESTINATION+1
    cmp #>SAME_SCUMM_ACTOR_POSE_BUFFER
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_MSU1_DESTINATION+2
    cmp #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    bne ScummV5_ActorPose_ProviderMatches__no
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne ScummV5_ActorPose_ProviderMatches__no
    lda.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    cmp.l SAME_SCUMM_ACTOR_POSE_GENERATION
    bne ScummV5_ActorPose_ProviderMatches__no
    plp
    sec
    rtl
ScummV5_ActorPose_ProviderMatches__no:
    plp
    clc
    rtl

; Release only an ACTOR-owned scratch after a verified transfer has either
; been discarded or synchronously consumed. Never change executable-cache
; identity, pins, or generations here.
ScummV5_ActorPose_ReleaseBuffer_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ACTOR
    bne ScummV5_ActorPose_ReleaseBuffer__done
    lda #SAME_SCUMM_ACTOR_SCRATCH_OWNER_NONE
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
ScummV5_ActorPose_ReleaseBuffer__done:
    plp
    rtl

; Room installation cancels a pending actor read without releasing its
; destination until the provider is done. The per-frame poll makes the page
; reclaimable even while no drawable room is currently installed.
ScummV5_ActorPose_Cancel_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    cmp #$01
    beq ScummV5_ActorPose_Cancel__pending
    cmp #$02
    beq ScummV5_ActorPose_Cancel__release
    cmp #$03
    beq ScummV5_ActorPose_Cancel__done
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
ScummV5_ActorPose_Cancel__done:
    plp
    rtl
ScummV5_ActorPose_Cancel__pending:
    .a8
    lda #$03
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    plp
    rtl
ScummV5_ActorPose_Cancel__release:
    .a8
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    plp
    rtl

ScummV5_ActorPose_ServiceCancel_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    cmp #$03
    bne ScummV5_ActorPose_ServiceCancel__done
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    beq ScummV5_ActorPose_ServiceCancel__done
    cmp #SAME_MSU1_STATE_INITIALIZING
    beq ScummV5_ActorPose_ServiceCancel__done
    cmp #SAME_MSU1_STATE_TAIL_CHECK
    beq ScummV5_ActorPose_ServiceCancel__done
ScummV5_ActorPose_ServiceCancel__release:
    .a8
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
ScummV5_ActorPose_ServiceCancel__done:
    plp
    rtl
.endif

.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
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
.endif

.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
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

.endif
.endif

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
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    jsl ScummV5_Controller_RenderActor_Far
    .endif
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
; Compose a bounded HUD prompt from the canonical runtime tables:
;   C17 verb record name + object-name bytes written by $54 setObjectName.
; Both strings remain SCUMM encoded; the text service owns decoding and
; presentation. A missing name simply yields the names that are available.
ScummV5_Controller_BuildHudText_Far:
    php
    phb
    sep #$20
    .a8
    lda #$7E
    pha
    plb
    rep #$30
    .a16
    .i16
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    sep #$20
    .a8
    sta.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_VERB
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    asl
    clc
    adc.l SAME_OVERLAY_PRODUCER_TEMP
    sta.l SAME_SCUMM_C17_RECORD_OFFSET
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    bne ScummV5_Controller_BuildHudText__verb_present
    jmp ScummV5_Controller_BuildHudText__unusable
ScummV5_Controller_BuildHudText__verb_present:
    rep #$20
    .a16
    ; The C17 name length was loaded in A8.  Clear the stale high byte before
    ; widening it; otherwise a prior 16-bit value turns a five-byte name into
    ; a 0x0105-byte loop bound and consumes the whole target buffer.
    and #$00FF
    dec
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    clc
    adc #SAME_SCUMM_C17_V_NAME
    tax
    sep #$20
    .a8
ScummV5_Controller_BuildHudText__verb_loop:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    and #$00FF
    ; The target-neutral text buffer is 32 bytes.  Verb text is runtime C17
    ; data, so its authored length must be clipped before the indexed write;
    ; otherwise a long name can alias controller state immediately after the
    ; buffer (including SAME_SCUMM_CONTROLLER_MODE).
    cmp #$0020
    bcc ScummV5_Controller_BuildHudText__verb_bound_ok
    brl ScummV5_Controller_BuildHudText__finish
ScummV5_Controller_BuildHudText__verb_bound_ok:
    tay
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS,x
    ; 65816 has no absolute-long indexed-Y mode.  Preserve the source
    ; cursor in X while using the text index as the destination cursor.
    phx
    tyx
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    plx
    inx
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    inc
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    lda.l SAME_OVERLAY_PRODUCER_TEMP
    dec
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    bne ScummV5_Controller_BuildHudText__verb_loop
ScummV5_Controller_BuildHudText__object:
    ; Separate the two runtime names with an ordinary encoded space when
    ; both are present.
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    beq ScummV5_Controller_BuildHudText__object_no_space
    and #$00FF
    tay
    sep #$20
    .a8
    lda #$20
    phx
    tyx
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    plx
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    inc
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
ScummV5_Controller_BuildHudText__object_no_space:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    and #$07FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
    beq ScummV5_Controller_BuildHudText__finish
    ; OBNA length includes its terminator.  Use the authored length as the
    ; copy bound so a valid source name is not lost to an incidental zero in
    ; the bounded cache.  The cache remains runtime/source-owned; this is
    ; only a presentation copy into the target-neutral text buffer.
    rep #$20
    .a16
    and #$00FF
    dec
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_OBJECT
    and #$07FF
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
ScummV5_Controller_BuildHudText__object_loop:
    rep #$20
    .a16
    lda.l SAME_OVERLAY_PRODUCER_TEMP
    beq ScummV5_Controller_BuildHudText__finish
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    and #$00FF
    tay
    sep #$20
    .a8
    cpy #$001F
    bcs ScummV5_Controller_BuildHudText__finish
    lda.l SAME_SCUMM_OBJECT_NAMES,x
    phx
    tyx
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    plx
    inx
    iny
    rep #$20
    .a16
    tya
    sta.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    lda.l SAME_OVERLAY_PRODUCER_TEMP
    dec
    sta.l SAME_OVERLAY_PRODUCER_TEMP
    bra ScummV5_Controller_BuildHudText__object_loop
ScummV5_Controller_BuildHudText__finish:
    rep #$20
    .a16
    .i16
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_TEXT_INDEX
    and #$00FF
    tay
    sep #$20
    .a8
    lda #$00
    sep #$20
    .a8
    phx
    tyx
    sta.l SAME_VIDEO_TEXT_CONTROLLER_BUFFER,x
    plx
    ; The terminator is stored outside the printable segment.  Keep the
    ; current index as the actual number of initialized printable bytes.
    tya
    sep #$20
    .a8
    sta.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
    sta.l SAME_SCUMM_TALK_RAW_LENGTH
    lda #$01
    sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    ; Zero means the runtime text is usable to ShowHud.  A nonzero value is
    ; reserved for an unavailable/rejected presentation attempt.
    lda #$00
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plb
    plp
    rtl

ScummV5_Controller_BuildHudText__unusable:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
    sta.l SAME_VIDEO_TEXT_CONTROLLER_VALID
    sta.l SAME_SCUMM_TALK_RAW_LENGTH
    lda #$01
    sta.l SAME_SCUMM_TALK_VISUAL_STATUS
    plb
    plp
    rtl

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
    ; The controller HUD is assembled from runtime SCUMM names. The legacy
    ; proof-scene prompt block below is unreachable and retained temporarily
    ; only as a binary-compatibility anchor while generated callers migrate.
    jsl ScummV5_Controller_BuildHudText_Far
    lda.l SAME_SCUMM_TALK_VISUAL_STATUS
    bne ScummV5_Controller_ShowHud__dynamic_unusable
    brl ScummV5_Controller_ShowHud__dynamic_finalize
ScummV5_Controller_ShowHud__dynamic_unusable:
    rtl
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
    ldx #ScummV5_Controller_LegacyPrompt0
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000D
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__verb:
    sep #$20
    .a8
    ldx #ScummV5_Controller_LegacyPrompt1
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000F
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__inspect:
    sep #$20
    .a8
    ldx #ScummV5_Controller_LegacyPrompt2
    ldy #SAME_SCUMM_TALK_RAW
    lda #$000A
    bra ScummV5_Controller_ShowHud__copy
ScummV5_Controller_ShowHud__walk:
    sep #$20
    .a8
    ldx #ScummV5_Controller_LegacyPrompt3
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
    lda.l SAME_VIDEO_TEXT_CONTROLLER_LENGTH
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
    lda.l ScummV5_Controller_LegacyPrompt0,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_verb:
    lda.l ScummV5_Controller_LegacyPrompt1,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_walk:
    lda.l ScummV5_Controller_LegacyPrompt3,x
    bra ScummV5_Controller_ShowHud__copy_store
ScummV5_Controller_ShowHud__copy_inspect:
    lda.l ScummV5_Controller_LegacyPrompt2,x
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
ScummV5_Controller_ShowHud__dynamic_finalize:
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

; Deprecated prompt storage is intentionally blank. The live HUD path above
; reads C17/object-name runtime data instead of proof-scene strings.
ScummV5_Controller_LegacyPrompt0: .byte $00
ScummV5_Controller_LegacyPrompt1: .byte $00
ScummV5_Controller_LegacyPrompt2: .byte $00
ScummV5_Controller_LegacyPrompt3: .byte $00
