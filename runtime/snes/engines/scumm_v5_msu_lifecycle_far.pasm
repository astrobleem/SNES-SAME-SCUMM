; Lifecycle-slot support for a nested child waiting on a checked MSU ProgramUnit
; page.  This lives in the existing far room-service bank so the generic
; feature does not consume the nearly-full bank-zero interpreter window.
; Return A=1/C=0 while the recorded child is still waiting, A=0/C=0 when the
; room lifecycle may continue, or C=1 after stale ownership/child failure.
ScummV5_M23A_RunPendingLifecycleChild_FarEntry:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT
    bne ScummV5_M23A_RunPendingLifecycleChild_FarEntry__has_child
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__no_child
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__has_child:
    .a8
    dec
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M23A_RunPendingLifecycleChild_FarEntry__slot_valid
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__stale
ScummV5_M23A_RunPendingLifecycleChild_FarEntry__slot_valid:
    .a8
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    cmp.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM
    beq ScummV5_M23A_RunPendingLifecycleChild_FarEntry__identity_valid
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__stale
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
    ; Run only the exact child retained by the M23B nesting frame.  The
    ; lifecycle parent remains slot zero and is rehydrated on the next pass.
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
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
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM
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
    jmp ScummV5_M23A_RunPendingLifecycleChild_FarEntry__child_error
