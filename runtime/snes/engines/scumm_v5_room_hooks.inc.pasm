; v5 VAR_EXIT_SCRIPT/EXIT_SCRIPT2 and ENTRY_SCRIPT/ENTRY_SCRIPT2.
; Ordinary C4 activations; no synthetic bytecode, permanent selector or IO lease.
; Phase7 parks only the room transaction until the hook reaches a source
; scheduling boundary. Checked-code waits are not source yields.
ScummV5_RoomHook_Reset_Far:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_RoomHook_Reset__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_ROOM_HOOK_BASE,x
    inx
    inx
    cpx #(SAME_SCUMM_ROOM_HOOK_END-SAME_SCUMM_ROOM_HOOK_BASE)
    bcc ScummV5_RoomHook_Reset__loop
    sep #$20
    .a8
    rtl

; A8 kind1..4. C=1 after error; otherwise A=1 if the transaction is parked.
; DONE is set at acceptance, so async installation cannot repeat a hook.
ScummV5_RoomHook_Arm_Far:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    and #$00FF
    dec
    tax
    sep #$20
    .a8
    lda.l ScummV5_RoomHook_Bits,x
    and.l SAME_SCUMM_ROOM_HOOK_DONE
    beq ScummV5_RoomHook_Arm__new
    lda #$00
    clc
    rtl
ScummV5_RoomHook_Arm__new:
    .a8
    .i16
    lda.l ScummV5_RoomHook_Bits,x
    ora.l SAME_SCUMM_ROOM_HOOK_DONE
    sta.l SAME_SCUMM_ROOM_HOOK_DONE
    txa
    inc
    sta.l SAME_SCUMM_ROOM_HOOK_KIND
    lda.l ScummV5_RoomHook_Variables,x
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_VARIABLES,x
    bne ScummV5_RoomHook_Arm__number
    sep #$20
    .a8
    sta.l SAME_SCUMM_ROOM_HOOK_KIND
    clc
    rtl
ScummV5_RoomHook_Arm__number:
    .a16
    .i16
    cmp #$0100
    bcc ScummV5_RoomHook_Arm__valid
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Arm__valid:
    .a16
    .i16
    sep #$20
    .a8
    sta.l SAME_SCUMM_ROOM_HOOK_NUMBER
    jsl ScummV5_Camera_FarCall_StopNumber
    rep #$10
    .i16
    ldx #$0001
ScummV5_RoomHook_Arm__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_RoomHook_Arm__slot
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_RoomHook_Arm__slot
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_RoomHook_Arm__scan
    lda #SCUMM_ERR_SLOT_CAPACITY
    jml ScummV5_RoomHook_ErrorCode_Far
ScummV5_RoomHook_Arm__slot:
    .a8
    .i16
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_ROOM_HOOK_SLOT
    lda.l SAME_SCUMM_ROOM_HOOK_NUMBER
    cmp #SCUMM_V5_NUM_GLOBAL_SCRIPTS
    bcc ScummV5_RoomHook_Arm__global
    jsl ScummV5_Camera_FarCall_ResolveLocal
    bra ScummV5_RoomHook_Arm__resolved
ScummV5_RoomHook_Arm__global:
    .a8
    .i16
    jsl ScummV5_Camera_FarCall_ResolveGlobal
ScummV5_RoomHook_Arm__resolved:
    .a8
    .i16
    bcs ScummV5_RoomHook_Arm__program
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Arm__program:
    .a8
    .i16
    sta.l SAME_SCUMM_ROOM_HOOK_SELECTOR
    lda.l SAME_SCUMM_ROOM_HOOK_NUMBER
    sta.l SAME_SCUMM_CONDITION
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jsl ScummV5_SlotMarkOrdinaryScript_Far
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_ROOM_HOOK_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ROOM_HOOK_NUMBER
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_ROOM_HOOK_SELECTOR
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    rep #$20
    .a16
    txa
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    lda.l SAME_SCUMM_ROOM_HOOK_SLOT
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    ldy #SAME_SCUMM_LOCAL_COUNT
    lda #$0000
ScummV5_RoomHook_Arm__locals:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    dey
    bne ScummV5_RoomHook_Arm__locals
    lda.l SAME_SCUMM_ROOM_HOOK_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
.if SAME_BUILD_SCUMM_MSU1_PROGRAMS
    jsl ScummV5_MsuProgram_NewActivation_Far
.endif
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #$07
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    clc
    rtl

; Called at the outer frame boundary. A1 means this frame belongs to the
; hook transaction; A0 resumes normal dispatch. No unrelated script runs
; ahead of a hook whose checked executable bytes are still unavailable.
ScummV5_RoomHook_Tick_Far:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$07
    beq ScummV5_RoomHook_Tick__active
    cmp #$00
    bne ScummV5_RoomHook_Tick__idle
    lda.l SAME_SCUMM_M23A_CHAIN_PHASE
    bne ScummV5_RoomHook_Tick__idle
    lda.l SAME_SCUMM_ROOM_HOOK_AFTER_ENTRY
    beq ScummV5_RoomHook_Tick__idle
    lda #$00
    sta.l SAME_SCUMM_ROOM_HOOK_AFTER_ENTRY
    lda #$04
    jml ScummV5_RoomHook_Arm_Far
ScummV5_RoomHook_Tick__idle:
    .a8
    .i16
    lda #$00
    clc
    rtl
ScummV5_RoomHook_Tick__active:
    .a8
    .i16
    rep #$20
    .a16
    lda.l SAME_SCUMM_ROOM_HOOK_EPOCH
    pha
    lda.l SAME_SCUMM_ROOM_HOOK_SLOT
    and #$00FF
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_RoomHook_Tick__slot
    pla
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Tick__slot:
    .a16
    .i16
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ROOM_HOOK_SELECTOR
    cmp.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    beq ScummV5_RoomHook_Tick__owner
    jmp ScummV5_RoomHook_Tick__stale
ScummV5_RoomHook_Tick__owner:
    .a8
    .i16
    ; Y=FFFF denotes the hook itself; otherwise Y owns a nested IO ticket.
    ldy #$FFFF
.if SAME_BUILD_SCUMM_MSU1_PROGRAMS
    jsl ScummV5_M23A_SelectPendingChild_Far
    bcc ScummV5_RoomHook_Tick__selected
    jmp ScummV5_RoomHook_Tick__stale
ScummV5_RoomHook_Tick__selected:
    .a8
    .i16
    cmp #$00
    bne ScummV5_RoomHook_Tick__have_selected
    ldy #$FFFF
.endif
ScummV5_RoomHook_Tick__have_selected:
    .a8
    .i16
    phy
    phx
    txa
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_RoomHook_Tick__already_stopped
    cmp #SCUMM_VM_ERROR
    beq ScummV5_RoomHook_Tick__already_stopped
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_FRAME_OPS
    sep #$20
    .a8
    jsl ScummV5_C4_RunAllocatedNoParent_FarEntry
ScummV5_RoomHook_Tick__already_stopped:
    .a8
    .i16
    rep #$30
    .a16
    .i16
    plx
    ply
    pla
    cmp.l SAME_SCUMM_ROOM_HOOK_EPOCH
    beq ScummV5_RoomHook_Tick__same_request
    ; The callback requested another room. Its newer transaction owns state.
    sep #$20
    .a8
    lda #$01
    clc
    rtl
ScummV5_RoomHook_Tick__same_request:
    .a8
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_ERROR
    beq ScummV5_RoomHook_Tick__status
    sec
    rtl
ScummV5_RoomHook_Tick__status:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    cmp #SCUMM_VM_ERROR
    bne ScummV5_RoomHook_Tick__not_error
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Tick__not_error:
    .a8
    .i16
    cmp #SCUMM_VM_WAIT_RESOURCE
    beq ScummV5_RoomHook_Tick__waiting
    cmp #SCUMM_VM_RUNNING
    beq ScummV5_RoomHook_Tick__waiting
    cmp #SCUMM_VM_YIELDED
    beq ScummV5_RoomHook_Tick__source_boundary
    cmp #SCUMM_VM_DELAYED
    beq ScummV5_RoomHook_Tick__source_boundary
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_RoomHook_Tick__source_boundary
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Tick__source_boundary:
    .a8
    .i16
    ; Authored yield/delay/stop returns from runScriptNested. Do not wait for
    ; the eventual retirement of a global that deliberately remains active.
    cpy #$FFFF
    beq ScummV5_RoomHook_Tick__complete
.if SAME_BUILD_SCUMM_MSU1_PROGRAMS
    tyx
    lda #$00
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM,x
.endif
ScummV5_RoomHook_Tick__waiting:
    .a8
    .i16
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda #$01
    clc
    rtl
ScummV5_RoomHook_Tick__stale:
    .a8
    .i16
    rep #$20
    .a16
    pla
    jml ScummV5_RoomHook_Error_Far
ScummV5_RoomHook_Tick__complete:
    .a8
    .i16
    lda.l SAME_SCUMM_ROOM_HOOK_KIND
    pha
    lda #$00
    sta.l SAME_SCUMM_ROOM_HOOK_KIND
    sta.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_RETURN_MODE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    pla
    cmp #$01
    beq ScummV5_RoomHook_Tick__exit_before
    cmp #$02
    beq ScummV5_RoomHook_Tick__exit_after
    cmp #$03
    beq ScummV5_RoomHook_Tick__entry_before
    lda #$01
    clc
    rtl
ScummV5_RoomHook_Tick__exit_before:
    .a8
    .i16
    jsl ScummV5_M23A_ResourceReady_FarEntry
    bra ScummV5_RoomHook_Tick__resumed
ScummV5_RoomHook_Tick__exit_after:
    .a8
    .i16
    jsl ScummV5_M23A_CommitRoom_FarEntry
    bra ScummV5_RoomHook_Tick__resumed
ScummV5_RoomHook_Tick__entry_before:
    .a8
    .i16
    ; Slot zero already owns the incoming ENCD. Its initial PC/status must
    ; survive the pre-entry callback. A neutral selector/current-slot pair
    ; would make the direct room runner save the completed hook over ENCD.
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_M23A_PHASE
    clc
ScummV5_RoomHook_Tick__resumed:
    .a8
    .i16
    lda #$01
    rtl
 ; Source ENCD yield returns from startScene while its activation survives.
; Resource waits and running bytecode stay inside the lifecycle transaction.
ScummV5_RoomHook_EntryBoundary_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$02
    bne ScummV5_RoomHook_EntryBoundary__done
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    bne ScummV5_RoomHook_EntryBoundary__done
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_YIELDED
    beq ScummV5_RoomHook_EntryBoundary__yielded
    cmp #SCUMM_VM_DELAYED
    bne ScummV5_RoomHook_EntryBoundary__done
ScummV5_RoomHook_EntryBoundary__yielded:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_SLOT_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_DELAY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
ScummV5_RoomHook_EntryBoundary__done:
    .a8
    clc
    rtl

ScummV5_RoomHook_Error_Far:
    .a8
    .i16
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
ScummV5_RoomHook_ErrorCode_Far:
    .a8
    .i16
    jsl ScummV5_Camera_FarCall_SetError
    sec
    rtl
ScummV5_RoomHook_Bits:
    .a8
    .i16
    .byte $01,$02,$04,$08
ScummV5_RoomHook_Variables:
    .a8
    .i16
    .byte $1E,$1F,$1C,$1D
