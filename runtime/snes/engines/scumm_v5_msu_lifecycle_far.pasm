; Lifecycle-slot support for a nested child waiting on a checked MSU ProgramUnit
; page.  This lives in the existing far room-service bank so the generic
; feature does not consume the nearly-full bank-zero interpreter window.
; Return A=1/C=0 while the recorded child is still waiting, A=0/C=0 when the
; room lifecycle may continue, or C=1 after stale ownership/child failure.
ScummV5_M23A_RunPendingLifecycleChild_FarEntry:
    ; The direct ENCD/EXCD runner owns slot zero, but its checked-read child
    ; may itself have parked at StartScript. Service the deepest exact ticket,
    ; not the first parent repeatedly. No unrelated activation runs here.
    jsl ScummV5_M23A_SelectLifecycleChild_Far
    bcc ScummV5_M23A_RunPendingLifecycleChild_FarEntry__selected
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__stale
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__selected:
    .a8
    cmp #$00
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__has_child
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__no_child
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__has_child:
    .a8
    .i16
    ; Y is the immediate ticket owner. Keep it on the native stack across
    ; VM calls, which are allowed to overwrite all scheduler scratch fields.
    phy
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__identity_valid:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    cmp #SCUMM_VM_ERROR
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__status_not_error
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__child_error
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__status_not_error:
    .a8
    cmp #SCUMM_VM_STOPPED
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__not_stopped
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__clear
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__not_stopped:
    .a8
    cmp #SCUMM_VM_YIELDED
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__needs_service
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__clear
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__needs_service:
    .a8
    ; Run the selected descendant. Slot zero is rehydrated on every return.
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    rep #$30
    .a16
    .i16
    and #$00FF
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
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    jsl ScummV5_MsuProgram_SuspendActive_Far
    jsl ScummV5_M23A_RunSelected_FarThunk
    php
    jsl ScummV5_M23A_SaveCurrentSlot_FarThunk
    plp
    bcc ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_ok
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__child_error
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_ERROR
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_not_error
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__child_error
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_not_error:
    .a8
    cmp #SCUMM_VM_RUNNING
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_not_running
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__still_waiting
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__run_not_running:
    .a8
    cmp #SCUMM_VM_WAIT_RESOURCE
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__clear
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__still_waiting

ScummV5_M23A_RunPendingLifecycleChild_FarEntry__clear:
    rep #$10
    .i16
    .a8
    ply
    tyx
    lda #$00
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM,x
    ; A descendant reached its source boundary. Its immediate parent must
    ; resume next, before the lifecycle root is allowed past StartScript.
    cpx #$0000
    beq ScummV5_M23A_RunPendingLifecycleChild_FarEntry__restore_parent
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__wait_unstacked
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__restore_parent:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda #$00
    clc
    rtl

ScummV5_M23A_RunPendingLifecycleChild_FarEntry__no_child:
    .a8
    lda #$00
    clc
    rtl

ScummV5_M23A_RunPendingLifecycleChild_FarEntry__still_waiting:
    rep #$10
    .i16
    ply
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__wait_unstacked:
    .a8
    lda #SCUMM_VM_WAIT_RESOURCE
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda #$01
    clc
    rtl

ScummV5_M23A_RunPendingLifecycleChild_FarEntry__child_error:
    rep #$10
    .i16
    ply
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__error_unstacked:
    .a8
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    sec
    rtl

ScummV5_M23A_RunPendingLifecycleChild_FarEntry__stale:
    .a8
    lda #SCUMM_ERR_RESOURCE
    jsl ScummV5_M23A_SetError_FarThunk
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__error_unstacked

; A8/X16/Y16: A=1, X=child, Y=immediate parent, C=0; A=0 if no
; lifecycle dependency; C=1 for out-of-range, stale selector, or cyclic chain.
; The hop bound is the existing C4 capacity. All addresses remain slot-bounded.
ScummV5_M23A_SelectLifecycleChild_Far:
    rep #$30
    .a16
    .i16
    ldx #$0000
; Additional entry for a normal C4 lifecycle-hook root (X16).
ScummV5_M23A_SelectPendingChild_Far:
    ldy #SCUMM_V5_MAX_SCRIPT_SLOTS
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    bne ScummV5_M23A_SelectLifecycleChild__edge
    clc
    rtl
ScummV5_M23A_SelectLifecycleChild__edge:
    .a8
    .i16
    dec
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcs ScummV5_M23A_SelectLifecycleChild__invalid
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    phx
    lda.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM,x
    pha
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    pla
    cmp.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    bne ScummV5_M23A_SelectLifecycleChild__stale
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    cmp #SCUMM_VM_WAIT_RESOURCE
    bne ScummV5_M23A_SelectLifecycleChild__chosen
    lda.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    beq ScummV5_M23A_SelectLifecycleChild__chosen
    ; Preserve the child in X while discarding its parent's saved index.
    rep #$20
    .a16
    pla
    sep #$20
    .a8
    dey
    beq ScummV5_M23A_SelectLifecycleChild__invalid
    lda.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    bra ScummV5_M23A_SelectLifecycleChild__edge
ScummV5_M23A_SelectLifecycleChild__chosen:
    .a8
    .i16
    ply
    lda #$01
    clc
    rtl
ScummV5_M23A_SelectLifecycleChild__stale:
    .a8
    .i16
    plx
ScummV5_M23A_SelectLifecycleChild__invalid:
    .a8
    sec
    rtl
