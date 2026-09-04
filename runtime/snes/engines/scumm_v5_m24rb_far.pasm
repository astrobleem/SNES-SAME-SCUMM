; M24R-B1 cold SCUMM room lifecycle closure.
; Included only after main.pasm selects bank 9. DBR remains the engine-wide
; bank-zero value; all WRAM/ROM operands are explicit long accesses.
; M23A lifecycle trace codes: 1 request, 2 validated, 3 old EXCD,
; 4 room-local retirement, 5 activate, 6 register EXCD, 7 register LSCR,
; 8 schedule ENCD, 9 begin ENCD, 10 finish ENCD.
ScummV5_M24RB_Far_Trace:
    sep #$20
    .a8
    sep #$10
    .i8
    pha
    lda.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    cmp #$0E
    bcs ScummV5_M24RB_Far_Trace__full
    tax
    pla
    sta.l SAME_SCUMM_M23A_LIFECYCLE,x
    txa
    inc
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    rep #$10
    .i16
    rts
ScummV5_M24RB_Far_Trace__full:
    .a8
    .i8
    pla
    rep #$10
    .i16
    rts

.if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
; Source-root repair for the authored room-42 Sophia placement.  Some room
; entry paths retain the C14 identity/room record but lose the auxiliary C31
; coordinates during neutral initialization; restore only the source-defined
; ENCD placement before the next semantic sentence is consumed.
ScummV5_Scenario_Fixture_EnsureActor2Room42_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    bne ScummV5_Scenario_Fixture_EnsureActor2Room42_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_POSITIONS+8
    ora.l SAME_SCUMM_C31_POSITIONS+10
    bne ScummV5_Scenario_Fixture_EnsureActor2Room42_Far__done16
    lda #$00B8
    sta.l SAME_SCUMM_C31_POSITIONS+8
    lda #$0065
    sta.l SAME_SCUMM_C31_POSITIONS+10
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING+2
    lda #$07
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+2
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+2
ScummV5_Scenario_Fixture_EnsureActor2Room42_Far__done16:
    sep #$20
    .a8
ScummV5_Scenario_Fixture_EnsureActor2Room42_Far__done:
    rtl
.endif

.if SAME_BUILD_SCUMM_M23C
; Bounded profile driver: once the authentic room-49 flush has made its music
; audibly owned, retain thirty playing frames and request the generated target
; room through the normal asynchronous resource/lifecycle path.
ScummV5_M24RB_Far_Driver:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    ; Keep the source-root actor auxiliary record coherent after the room
    ; entry scheduler has finished its neutral service pass.
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23C_PHASE
    cmp #$01
    beq ScummV5_M24RB_Far_Driver__wait_music
    .if SAME_BUILD_M24RB
    cmp #$04
    beq ScummV5_M24RB_Far_Driver__wait_marker
    cmp #$05
    bne ScummV5_M24RB_Far_Driver__not_m24rb_wait_room
    jmp ScummV5_M24RB_Far_Driver__wait_room_phase
ScummV5_M24RB_Far_Driver__not_m24rb_wait_room:
    .a8
    cmp #$07
    bne ScummV5_M24RB_Far_Driver__not_m24rb_frame_end
    jmp ScummV5_M24RB_Far_Driver__frame_end
ScummV5_M24RB_Far_Driver__not_m24rb_frame_end:
    .a8
    cmp #$08
    bne ScummV5_M24RB_Far_Driver__not_m24rb_wait_fade
    jmp ScummV5_M24RB_Far_Driver__wait_fade
ScummV5_M24RB_Far_Driver__not_m24rb_wait_fade:
    .endif
    clc
    rts
ScummV5_M24RB_Far_Driver__wait_music:
    .a8
    lda.l SAME_TAD_STATE
    cmp #SAME_TAD_STATE_PLAYING
    bne ScummV5_M24RB_Far_Driver__done
    lda.l SAME_TAD_READY
    beq ScummV5_M24RB_Far_Driver__done
    lda.l SAME_SCUMM_M23C_READY_WAIT
    inc
    sta.l SAME_SCUMM_M23C_READY_WAIT
    cmp #$1E
    bcc ScummV5_M24RB_Far_Driver__done
    .if SAME_BUILD_M24RB
    jsr ScummV5_M24RB_Far_ScheduleLocal
    bcs ScummV5_M24RB_Far_Driver__done
    lda #$04
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    clc
    rts
    .else
    lda #$02
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23C_TRANSITION_REQUESTED
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    lda #SCUMM_M23C_TARGET_ROOM
    jsr ScummV5_M24RB_Far_RequestRoom
    rts
    .endif
ScummV5_M24RB_Far_Driver__done:
    clc
    rts

.if SAME_BUILD_M24RB
ScummV5_M24RB_Far_Driver__wait_marker:
    .a8
    ; Authentic LSCR commands are drained at the engine frame boundary, not
    ; by adding a synthetic soundKludge[-1] instruction.
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    beq ScummV5_M24RB_Far_Driver__marker_poll
    lda #$01
    sta.l SAME_M24RB_FRAME_END_ACTIVE
    jsl ScummV5_M24RB_FarCall_C25Flush
    lda.l SAME_M24RB_FRAME_END_FLUSHES
    inc
    sta.l SAME_M24RB_FRAME_END_FLUSHES
ScummV5_M24RB_Far_Driver__marker_poll:
    .a8
    lda.l APUIO1
    cmp #$88
    bne ScummV5_M24RB_Far_Driver__done
    lda.l SAME_M24RB_MARKER_COUNT
    bne ScummV5_M24RB_Far_Driver__done
    inc
    sta.l SAME_M24RB_MARKER_COUNT
    lda #$02
    sta.l SAME_M24RB_LOGICAL82_STATE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    clc
    adc #SAME_M24RB_PHASE_DELAY
    sta.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    lda #$05
    sta.l SAME_SCUMM_M23C_PHASE
    clc
    rts
ScummV5_M24RB_Far_Driver__wait_room_phase:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    bcc ScummV5_M24RB_Far_Driver__done
    lda #$02
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23C_TRANSITION_REQUESTED
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    lda #SCUMM_M23C_TARGET_ROOM
    jsr ScummV5_M24RB_Far_RequestRoom
    rts
ScummV5_M24RB_Far_Driver__frame_end:
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    bne ScummV5_M24RB_Far_Driver__frame_end_pending
    jmp ScummV5_M24RB_Far_Driver__done
ScummV5_M24RB_Far_Driver__frame_end_pending:
    .a8
    lda #$01
    sta.l SAME_M24RB_FRAME_END_ACTIVE
    jsl ScummV5_M24RB_FarCall_C25Flush
    lda.l SAME_M24RB_FRAME_END_FLUSHES
    inc
    sta.l SAME_M24RB_FRAME_END_FLUSHES
    lda #$08
    sta.l SAME_SCUMM_M23C_PHASE
    clc
    rts
ScummV5_M24RB_Far_Driver__wait_fade:
    .a8
    lda.l SAME_M24RA_COMPLETE_FRAME
    bne ScummV5_M24RB_Far_Driver__fade_complete
    jmp ScummV5_M24RB_Far_Driver__done
ScummV5_M24RB_Far_Driver__fade_complete:
    lda.l SAME_M24RB_FADE_COMPLETE_COUNT
    beq ScummV5_M24RB_Far_Driver__fade_not_recorded
    jmp ScummV5_M24RB_Far_Driver__done
ScummV5_M24RB_Far_Driver__fade_not_recorded:
    .a8
    inc
    sta.l SAME_M24RB_FADE_COMPLETE_COUNT
    lda #$04
    sta.l SAME_M24RB_LOGICAL82_STATE
    lda #SAME_M24RB_LAYER_SOUND
    jsl ScummV5_M24RB_FarCall_ClearSfx
    clc
    rts

ScummV5_M24RB_Far_ScheduleLocal:
    sep #$20
    .a8
    .i16
    lda.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_COUNT
    lda.l SAME_SCUMM_C4_SLOT_STATUS+1
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS1
    lda.l SAME_SCUMM_C4_SLOT_STATUS+2
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS2
    lda #SAME_M24RB_LOCAL_SCRIPT
    jsl ScummV5_M24RB_FarCall_ResolveLocal
    bcc ScummV5_M24RB_Far_ScheduleLocal__error
    sta.l SAME_SCUMM_FETCH_BYTE
    ldx #$0001
ScummV5_M24RB_Far_ScheduleLocal__scan:
    sep #$20
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_M24RB_Far_ScheduleLocal__found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_M24RB_Far_ScheduleLocal__found
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M24RB_Far_ScheduleLocal__scan
    bra ScummV5_M24RB_Far_ScheduleLocal__error
ScummV5_M24RB_Far_ScheduleLocal__found:
    sep #$20
    .a8
    .i16
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_CHOSEN
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #SAME_M24RB_LOCAL_SCRIPT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_M24RB_LSCR_SCHEDULED
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    clc
    rts
ScummV5_M24RB_Far_ScheduleLocal__error:
    sec
    rts
.endif

.endif

; Install the canonical SCUMM null room without asking profile storage for a
; non-existent record. Global script slots survive; room-owned slots retire.
ScummV5_M24RB_Far_CommitNullRoom:
    sep #$20
    .a8
    jsl ScummV5_M24RB_FarCall_ResetSentenceQueue
    rep #$10
    .i16
    ldx #$0000
ScummV5_M24RB_Far_CommitNullRoom__retire:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_M24RB_Far_CommitNullRoom__next
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_M24RB_Far_CommitNullRoom__next
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
ScummV5_M24RB_Far_CommitNullRoom__next:
    sep #$20
    .a8
    rep #$10
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M24RB_Far_CommitNullRoom__retire
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_C4_SLOT_WHERE
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS
    sta.l SAME_SCUMM_M23A_PENDING_RECORD
    sta.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda #$FF
    sta.l SAME_SCUMM_M23A_ACTIVE_RECORD
    lda #$01
    sta.l SAME_SCUMM_C22_NULL_SCENE
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    rts

; Input A=logical room. Acquisition is asynchronous through SAME Storage READ;
; only the storage service validates profile-owned generated data.
ScummV5_M24RB_Far_RequestRoom:
    sep #$20
    .a8
    sta.l $7E5452
    lda.l $7E5450
    inc
    sta.l $7E5450
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    sta.l $7E5453
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l $7E5454
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E5455
    sep #$20
    .a8
    lda.l $7E5452
    sta.l SAME_SCUMM_M23A_PENDING_ROOM
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23A_RETURN_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_M23A_RETURN_PC
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_M23A_PHASE
    lda.l SAME_SCUMM_M23A_REQUEST_COUNT
    inc
    sta.l SAME_SCUMM_M23A_REQUEST_COUNT
    lda #$01
    jsr ScummV5_M24RB_Far_Trace
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    bne ScummV5_M24RB_Far_RequestRoom__queue
    jsr ScummV5_M24RB_Far_CommitNullRoom
    clc
    rts
ScummV5_M24RB_Far_RequestRoom__queue:
    sep #$20
    .a8
    jsl ScummV5_M24RB_FarCall_StageEngine
    lda #SAME_SERVICE_STORAGE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_STORAGE_OP_READ
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_PROFILE
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsl ScummV5_M24RB_FarCall_EventPush
    bcc ScummV5_M24RB_Far_RequestRoom__queued
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    lda #SCUMM_ERR_SERVICE
    .if SAME_BUILD_SCUMM_M23B
    pha
    lda #$02
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    pla
    .endif
    jsl ScummV5_M24RB_FarCall_SetError
    sec
    rts
ScummV5_M24RB_Far_RequestRoom__queued:
    sep #$20
    .a8
    clc
    rts

; Called only after the storage backend has completed all record checks.
ScummV5_M24RB_Far_ResourceReady:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$FF
    bne ScummV5_M24RB_Far_ResourceReady__check_exit
    jmp ScummV5_M24RB_Far_CommitRoom
ScummV5_M24RB_Far_ResourceReady__check_exit:
    .a8
    lda.l SAME_SCUMM_M23A_EXIT_PROGRAM
    bne ScummV5_M24RB_Far_ResourceReady__run_exit
    jmp ScummV5_M24RB_Far_CommitRoom
ScummV5_M24RB_Far_ResourceReady__run_exit:
    .a8
    jsr ScummV5_M24RB_Far_BeginRoomScript
    lda #$01
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$02
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    lda.l SAME_SCUMM_M23A_EXIT_COUNT
    inc
    sta.l SAME_SCUMM_M23A_EXIT_COUNT
    lda #$03
    jsr ScummV5_M24RB_Far_Trace
    clc
    rts

.if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && !SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
ScummV5_Scenario_Fixture_InstallActor_Far:
    ; Reusable engine-owned checkpoint setup. The validator never writes actor
    ; table, position, walkbox, or scheduler state.
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C14_INITIALIZED
    sta.l SAME_SCUMM_C31_INITIALIZED
    rep #$20
    .a16
    lda #$018F
    sta.l SAME_SCUMM_C31_POSITIONS+4
    lda #$0074
    sta.l SAME_SCUMM_C31_POSITIONS+6
    sep #$20
    .a8
    lda #$0B
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+1
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+1
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING+1
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT+64
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+64
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM+64
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_FIXTURE_READY
    rtl
.endif

; Input A=compiled script descriptor program. Slot zero is the scheduler-owned
; ENCD/EXCD frame; room-local allocations remain in slots 1..24.
ScummV5_M24RB_Far_BeginRoomScript:
    sep #$20
    .a8
    sta.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    ; A room entry runs as the outer engine frame. Nested startScript calls
    ; save this zero and select return mode one only around their child call.
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_C4_SLOT_DELAY
    sep #$20
    .a8
    rts

ScummV5_M24RB_Far_EndRoomScript:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_M24RB_Far_EndRoomScript__done
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_M24RB_Far_EndRoomScript__done:
    rts

ScummV5_M24RB_Far_CommitRoom:
    sep #$20
    .a8
    ; Pending sentences belong to the outgoing room. Drop them at the same
    ; generic room boundary as cutscene state so the next API sentence starts
    ; at queue record zero instead of replaying an old room action first.
    jsl ScummV5_M24RB_FarCall_ResetSentenceQueue
    ; A room load aborts the nested invocation that requested it. Retire both
    ; the immediate load caller and its saved parent before the new room can
    ; allocate a sentence launcher into either stale slot.
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    beq ScummV5_M24RB_Far_CommitRoom__no_parent_abort
    tax
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_M24RB_Far_CommitRoom__no_parent_abort
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
ScummV5_M24RB_Far_CommitRoom__no_parent_abort:
    .a8
    lda.l SAME_SCUMM_LOAD_EGO_CALLER_SLOT
    beq ScummV5_M24RB_Far_CommitRoom__no_caller_abort
    tax
    ; Global scripts retain their slot across a room load.  Only a room-owned
    ; caller is aborted by the room boundary; slot_rooms alone is not enough
    ; because ordinary global allocations carry the active room as context.
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_M24RB_Far_CommitRoom__no_caller_abort
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
ScummV5_M24RB_Far_CommitRoom__no_caller_abort:
    .a8
    lda #$00
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_RETURN_MODE
    ; Room changes abort the nested invocation above. C19 remains under the
    ; ordinary cutscene begin/end contract; resetting it here would discard a
    ; valid sentence-script lifecycle state before its first fetch.
    rep #$10
    .i16
    ldx #$0001
ScummV5_M24RB_Far_CommitRoom__retire:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    bne ScummV5_M24RB_Far_CommitRoom__retire_next
    lda.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    beq ScummV5_M24RB_Far_CommitRoom__retire_next
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_M24RB_Far_CommitRoom__retire_next
    lda #$00
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_M24RB_Far_CommitRoom__retired
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_M24RB_Far_CommitRoom__retired:
    lda.l SAME_SCUMM_M23A_RETIRE_COUNT
    inc
    sta.l SAME_SCUMM_M23A_RETIRE_COUNT
ScummV5_M24RB_Far_CommitRoom__retire_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M24RB_Far_CommitRoom__retire
    lda #$04
    jsr ScummV5_M24RB_Far_Trace
    lda.l SAME_SCUMM_M23A_PENDING_RECORD
    sta.l SAME_SCUMM_M23A_ACTIVE_RECORD
    jsl ScummV5_Matrix_LoadActiveRoom_Far
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    tax
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    sta.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && !SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    ; Engine-owned reusable scenario setup; validators supply no actor table,
    ; room, slot, or PC state.
    jsl ScummV5_Scenario_Fixture_InstallActor_Far
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    ; Source-root scenarios still need the ordinary zeroed actor/movement
    ; services before the first authored room-entry opcode runs.  Do not seed
    ; an actor position here: room/script bytecode owns that state.  The
    ; initialized flags make this a one-time service setup, not a room-entry
    ; reset that could erase authored placement on later loads.
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_M24RB_Far_CommitRoom__source_c14_done
    rep #$30
    .a16
    .i16
    ldx #$0000
    lda #$0000
ScummV5_M24RB_Far_CommitRoom__source_c14_clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C14_ACTORS,x
    inx
    inx
    cpx #$0820
    bcc ScummV5_M24RB_Far_CommitRoom__source_c14_clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C14_INITIALIZED
ScummV5_M24RB_Far_CommitRoom__source_c14_done:
    lda.l SAME_SCUMM_C31_INITIALIZED
    bne ScummV5_M24RB_Far_CommitRoom__source_c31_done
    rep #$30
    .a16
    .i16
    ldx #$0000
    lda #$0000
ScummV5_M24RB_Far_CommitRoom__source_c31_clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C31_STATE,x
    inx
    inx
    cpx #$00A4
    bcc ScummV5_M24RB_Far_CommitRoom__source_c31_clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C31_INITIALIZED
ScummV5_M24RB_Far_CommitRoom__source_c31_done:
    ; The source room-1 ENCD placement is (actor 1, 145, 112).  The startup
    ; scenario begins before that room-entry record, so establish its
    ; source-backed incoming actor state once through the engine-owned setup;
    ; subsequent room commits only follow the actor's room identity and leave
    ; the authored position untouched.
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT
    bne ScummV5_M24RB_Far_CommitRoom__source_actor_ready
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT+64
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+64
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING+1
    ; The source-backed (145,112) position is in physical room-42 BOXD
    ; walkbox 7. Preserve valid incoming membership for later authored
    ; walkActorToObject routing; this remains scenario-root setup only.
    lda #$07
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+1
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+1
    rep #$20
    .a16
    lda #$0091
    sta.l SAME_SCUMM_C31_POSITIONS+4
    lda #$0070
    sta.l SAME_SCUMM_C31_POSITIONS+6
    ; Source-root actor 2 is Sophia (costume 28 in the authored startup
    ; actor table).  Room-42 ENCD supplies her room/position placement when
    ; object 488 is in its source-defined initial state; seed only the
    ; engine-owned actor record and neutral movement state here so that ENCD
    ; can perform that normal placement.
    sep #$20
    .a8
    lda #$1C
    sta.l SAME_SCUMM_C14_ACTORS+128
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT+128
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE+128
    sta.l SAME_SCUMM_C31_MOVING+2
    lda #$07
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+2
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+2
    rep #$20
    .a16
    lda #$00B8
    sta.l SAME_SCUMM_C31_POSITIONS+8
    lda #$0065
    sta.l SAME_SCUMM_C31_POSITIONS+10
ScummV5_M24RB_Far_CommitRoom__source_actor_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM+128
    ; The startup42 source root includes Sophia's authored room-42 ENCD
    ; placement (actor 2, 184, 101).  Keep that source-backed incoming actor
    ; record intact across the room installation's neutral C31 initialization;
    ; this is fixture setup only, before the normal room-entry program runs.
    cmp #$2A
    bne ScummV5_M24RB_Far_CommitRoom__source_actor_ready_done
    rep #$20
    .a16
    lda #$00B8
    sta.l SAME_SCUMM_C31_POSITIONS+8
    lda #$0065
    sta.l SAME_SCUMM_C31_POSITIONS+10
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING+2
    lda #$07
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX+2
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX+2
ScummV5_M24RB_Far_CommitRoom__source_actor_ready_done:
    .endif
    ; Complete the source-neutral loadRoomWithEgo installation before ENCD.
    ; The decoded request survives retirement of its room-local caller.
    lda.l SAME_SCUMM_LOAD_EGO_ACTIVE
    beq ScummV5_M24RB_Far_CommitRoom__load_ego_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_LOAD_EGO_OBJECT
    sta.l SAME_SCUMM_VARIABLES+(38 * 2)
    sta.l SAME_SCUMM_MOVE_OBJECT
    sep #$20
    .a8
    lda.l SAME_SCUMM_LOAD_EGO_EGO
    sta.l SAME_SCUMM_MOVE_ACTOR
    rep #$20
    .a16
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
    lda.l SAME_SCUMM_LOAD_EGO_ROOM
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    jsl ScummV5_Movement_ObjectWalk_Far
    bcc ScummV5_M24RB_Far_CommitRoom__load_ego_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    sta.l SAME_SCUMM_C31_POSITIONS,x
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    lda.l SAME_SCUMM_MOVE_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    sta.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    sta.l SAME_SCUMM_PUT_ACTOR_DESTBOX,x
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda #$FFFF
    sta.l SAME_SCUMM_PUT_ACTOR_DEST_X,x
ScummV5_M24RB_Far_CommitRoom__load_ego_done:
    sep #$20
    .a8
    lda #$05
    jsr ScummV5_M24RB_Far_Trace
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    tax
    lda.l ScummV5_M23A_RoomScriptCounts,x
    sta.l SAME_SCUMM_M23A_DESCRIPTOR_COUNT
    sta.l SAME_SCUMM_M23A_REGISTER_COUNT
    lda.l ScummV5_M23A_RoomLocalCounts,x
    sta.l SAME_SCUMM_M23A_LOCAL_COUNT
    lda.l ScummV5_M23A_RoomEntryPrograms,x
    sta.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    lda.l ScummV5_M23A_RoomExitPrograms,x
    sta.l SAME_SCUMM_M23A_EXIT_PROGRAM
    sta.l SAME_SCUMM_FETCH_BYTE
    txa
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_M23A_RoomDescriptorChecksums,x
    sta.l SAME_SCUMM_M23A_DESCRIPTOR_CHECKSUM
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_M24RB_Far_CommitRoom__no_exit_registered
    lda #$06
    jsr ScummV5_M24RB_Far_Trace
ScummV5_M24RB_Far_CommitRoom__no_exit_registered:
    .a8
    lda.l SAME_SCUMM_M23A_LOCAL_COUNT
    beq ScummV5_M24RB_Far_CommitRoom__no_locals_registered
    lda #$07
    jsr ScummV5_M24RB_Far_Trace
ScummV5_M24RB_Far_CommitRoom__no_locals_registered:
    .a8
    lda #$08
    jsr ScummV5_M24RB_Far_Trace
    lda.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l ScummV5_M23A_RoomFlags,x
    and #$01
    beq ScummV5_M24RB_Far_CommitRoom__execute
    lda #$03
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    clc
    rts
ScummV5_M24RB_Far_CommitRoom__execute:
    .a8
ScummV5_M24RB_Far_CommitRoom__caller_saved:
    .a8
    lda #$02
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    lda.l SAME_SCUMM_M23A_ENTRY_COUNT
    inc
    sta.l SAME_SCUMM_M23A_ENTRY_COUNT
    lda #$09
    jsr ScummV5_M24RB_Far_Trace
    lda.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    jsr ScummV5_M24RB_Far_BeginRoomScript
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    jsl ScummV5_RoomVisual_Installed_Far
    .endif
    clc
    rts

; Proper long-call entry points. Internal lifecycle calls remain same-bank
; JSR/RTS, while callers in bank 0 use these JSL/RTL boundaries.
ScummV5_M23A_Trace_FarEntry:
    jsr ScummV5_M24RB_Far_Trace
    rtl
ScummV5_M23C_Driver_FarEntry:
    jsr ScummV5_M24RB_Far_Driver
    rtl
ScummV5_M23A_RequestRoom_FarEntry:
    jsr ScummV5_M24RB_Far_RequestRoom
    rtl
ScummV5_M23A_ResourceReady_FarEntry:
    jsr ScummV5_M24RB_Far_ResourceReady
    rtl
ScummV5_M23A_EndRoomScript_FarEntry:
    jsr ScummV5_M24RB_Far_EndRoomScript
    rtl
ScummV5_M23A_CommitRoom_FarEntry:
    jsr ScummV5_M24RB_Far_CommitRoom
    rtl

.if SAME_BUILD_SCUMM_M23B
; M25A bounded nested-script context switch. This is the same interpreter and
; authoritative slot table used in bank 0; only the cold suspend/restore
; helper is relocated. DBR-independent state accesses remain explicit long
; accesses, and every bank-0 helper call crosses a JSL/RTL boundary.
ScummV5_M25A_NestFrameX:
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    tax
    rts

ScummV5_M23B_RunNestedChild_FarEntry:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    lda #$01
    jsl ScummV5_M25A_FarCall_Trace
    .endif
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    cmp #SAME_SCUMM_M23B_NEST_MAX_DEPTH
    bcc ScummV5_M25A_RunNestedChild__room
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsl ScummV5_M24RB_FarCall_SetError
    sec
    rtl
ScummV5_M25A_RunNestedChild__room:
    jsr ScummV5_M25A_NestFrameX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_M25A_RunNestedChild__parent_mode_packed
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    ora #$80
ScummV5_M25A_RunNestedChild__parent_mode_packed:
    sta.l SAME_SCUMM_M23B_NEST_FRAMES,x
    phx
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    tax
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23B_NEST_PROGRAMS,x
    rep #$10
    .i16
    plx
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    inc
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    jsl ScummV5_M25A_FarCall_SaveCurrentSlot
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_PROGRAM
    lda.l SAME_SCUMM_C4_PARENT_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_PARENT
    .endif
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    and #$00FF
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    ; A nested script starts at an opcode boundary.  The expression decoder's
    ; transient dispatch depth is not script-owned state; if it leaked from
    ; the parent, Engine_Frame__next would mistake the child's first opcode
    ; for the expression return and unwind immediately.
    lda #$00
    sta.l SAME_SCUMM_C18_NESTED
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    sep #$20
    .a8
    lda #$02
    jsl ScummV5_M25A_FarCall_Trace
    .endif
    jsl ScummV5_M25A_FarCall_RunSelected
    ; Scenario observability: distinguish the child VM's post-run PC from the
    ; slot value written by the far save boundary.  These fields are outside
    ; interpreter state and make nested yield/return failures diagnosable.
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E5638
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l $7E563A
    lda.l SAME_SCUMM_STATUS
    sta.l $7E563B
    .endif
    php
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    sep #$20
    .a8
    lda #$03
    jsl ScummV5_M25A_FarCall_Trace
    .endif
    jsl ScummV5_M25A_FarCall_SaveCurrentSlot
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l $7E563C
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l $7E563E
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    dec
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    jsr ScummV5_M25A_NestFrameX
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sta.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_FRAMES,x
    and #$80
    beq ScummV5_M25A_RunNestedChild__restore_outer_mode
    lda #$01
    bra ScummV5_M25A_RunNestedChild__restore_mode
ScummV5_M25A_RunNestedChild__restore_outer_mode:
    .a8
    lda #$00
ScummV5_M25A_RunNestedChild__restore_mode:
    .a8
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_M23B_NEST_FRAMES,x
    and #$7F
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    phx
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    tax
    lda.l SAME_SCUMM_M23B_NEST_PROGRAMS,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$10
    .i16
    plx
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    lda #$00
    sta.l SAME_SCUMM_C18_NESTED
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    jsr ScummV5_M25A_NestFrameX
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sta.l SAME_SCUMM_FRAME_OPS
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    sep #$20
    .a8
    lda #$04
    jsl ScummV5_M25A_FarCall_Trace
    .endif
    plp
    bcc ScummV5_M25A_RunNestedChild__success
    sep #$20
    .a8
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rtl
ScummV5_M25A_RunNestedChild__success:
    clc
    rtl
.endif
