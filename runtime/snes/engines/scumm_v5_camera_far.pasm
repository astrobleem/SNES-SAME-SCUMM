; Canonical v5 camera lifecycle in the source-bound far-code bank.

; Canonical v5 $12/$92 panCameraTo: set the destination and let the normal
; camera phase converge.  This is distinct from $32/$B2 setCameraAt, which
; snaps immediately and may run the scroll callback.
ScummV5_Op_PanCameraTo_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_PanCameraTo_Far__variable
    jsl ScummV5_Camera_FarCall_FetchWord
    bcc ScummV5_Op_PanCameraTo_Far__ready
    jml ScummV5_Op__error
ScummV5_Op_PanCameraTo_Far__variable:
    jsl ScummV5_Camera_FarCall_FetchWord
    bcs ScummV5_Op_PanCameraTo_Far__error
    jsl ScummV5_Camera_FarCall_ReadVariable
    bcs ScummV5_Op_PanCameraTo_Far__error
ScummV5_Op_PanCameraTo_Far__ready:
    rep #$20
    .a16
    sta.l SAME_SCUMM_CAMERA_DEST_X
    sta.l SAME_SCUMM_CAMERA_REQUEST_X
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    lda #$01
    sta.l SAME_SCUMM_CAMERA_UPDATE_PENDING
    jml ScummV5_Engine_Frame__next
ScummV5_Op_PanCameraTo_Far__error:
    jml ScummV5_Op__error

; Canonical v5 $32/$B2 setCameraAt.  $72/$F2 remain loadRoom opcodes.
ScummV5_Op_SetCameraAt_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_CAMERA_PC_BEFORE
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_SetCameraAt_Far__variable
    jsl ScummV5_Camera_FarCall_FetchWord
    bcc ScummV5_Op_SetCameraAt_Far__operand_ready
    jml ScummV5_Op__error
ScummV5_Op_SetCameraAt_Far__variable:
    .a8
    jsl ScummV5_Camera_FarCall_FetchWord
    bcs ScummV5_Op_SetCameraAt_Far__operand_error
    .if SAME_BUILD_SCUMM_M23B
    rep #$30
    .a16
    .i16
    cmp #SAME_SCUMM_VARIABLE_COUNT
    bcs ScummV5_Op_SetCameraAt_Far__operand_error16
    asl
    tax
    lda.l SAME_SCUMM_M23B_VARIABLES,x
    bra ScummV5_Op_SetCameraAt_Far__operand_ready
    .else
    jsl ScummV5_Camera_FarCall_ReadVariable
    bcc ScummV5_Op_SetCameraAt_Far__operand_ready
    .endif
ScummV5_Op_SetCameraAt_Far__operand_error16:
    sep #$20
    .a8
ScummV5_Op_SetCameraAt_Far__operand_error:
    jml ScummV5_Op__error
ScummV5_Op_SetCameraAt_Far__operand_ready:
    rep #$20
    .a16
    sta.l SAME_SCUMM_CAMERA_REQUEST_X
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_CAMERA_DEST_X
    cmp.l SAME_SCUMM_C10_SCROLL_MIN
    bcs ScummV5_Op_SetCameraAt_Far__minimum_ok
    lda.l SAME_SCUMM_C10_SCROLL_MIN
ScummV5_Op_SetCameraAt_Far__minimum_ok:
    cmp.l SAME_SCUMM_C10_SCROLL_MAX
    bcc ScummV5_Op_SetCameraAt_Far__maximum_ok
    lda.l SAME_SCUMM_C10_SCROLL_MAX
ScummV5_Op_SetCameraAt_Far__maximum_ok:
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_CAMERA_PC_AFTER
    lda.l SAME_SCUMM_CAMERA_IMMEDIATE_COUNT
    inc
    sta.l SAME_SCUMM_CAMERA_IMMEDIATE_COUNT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    lda #$01
    sta.l SAME_SCUMM_CAMERA_UPDATE_PENDING
    jsl ScummV5_Camera_RunScrollScript_Far
    bcs ScummV5_Op_SetCameraAt_Far__callback_error
    jml ScummV5_Engine_Frame__next
ScummV5_Op_SetCameraAt_Far__callback_error:
    jml ScummV5_Op__error

ScummV5_Camera_RunScrollScript_Far:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_M23B_VARIABLES+(27 * 2)
    bne ScummV5_Camera_RunScrollScript_Far__have_script
    jmp ScummV5_Camera_RunScrollScript_Far__none
ScummV5_Camera_RunScrollScript_Far__have_script:
    sta.l SAME_SCUMM_CAMERA_SCROLL_SCRIPT
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_VARIABLES+(2 * 2)
    sta.l SAME_SCUMM_M23B_VARIABLES+(2 * 2)
    sep #$20
    .a8
    lda.l SAME_SCUMM_CAMERA_SCROLL_SCRIPT
    jsl ScummV5_Camera_FarCall_StopNumber
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Camera_RunScrollScript_Far__capacity
    jmp ScummV5_Camera_RunScrollScript_Far__error
ScummV5_Camera_RunScrollScript_Far__capacity:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C4_SCAN_SLOT
ScummV5_Camera_RunScrollScript_Far__scan:
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Camera_RunScrollScript_Far__slot_in_range
    jmp ScummV5_Camera_RunScrollScript_Far__error
ScummV5_Camera_RunScrollScript_Far__slot_in_range:
    .a8
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Camera_RunScrollScript_Far__found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Camera_RunScrollScript_Far__found
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    inc
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    bra ScummV5_Camera_RunScrollScript_Far__scan
ScummV5_Camera_RunScrollScript_Far__found:
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    tax
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_CAMERA_SCROLL_SCRIPT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp #SCUMM_V5_NUM_GLOBAL_SCRIPTS
    bcc ScummV5_Camera_RunScrollScript_Far__global
    jsl ScummV5_Camera_FarCall_ResolveLocal
    bcs ScummV5_Camera_RunScrollScript_Far__program
    bra ScummV5_Camera_RunScrollScript_Far__mapping_error
ScummV5_Camera_RunScrollScript_Far__global:
    .a8
    jsl ScummV5_Camera_FarCall_ResolveGlobal
    bcs ScummV5_Camera_RunScrollScript_Far__program
ScummV5_Camera_RunScrollScript_Far__mapping_error:
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    jmp ScummV5_Camera_RunScrollScript_Far__error
ScummV5_Camera_RunScrollScript_Far__program:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    jsl ScummV5_SlotMarkOrdinaryScript_Far
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    xba
    lsr
    lsr
    tax
    lda #$0000
    ldy #$0000
ScummV5_Camera_RunScrollScript_Far__clear_locals:
    .a16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Camera_RunScrollScript_Far__clear_locals
    jsl ScummV5_Camera_FarCall_RunNestedChild
    bcs ScummV5_Camera_RunScrollScript_Far__error
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_SCROLL_SCRIPT_COUNT
    inc
    sta.l SAME_SCUMM_CAMERA_SCROLL_SCRIPT_COUNT
    sep #$20
    .a8
ScummV5_Camera_RunScrollScript_Far__none:
    clc
    rtl
ScummV5_Camera_RunScrollScript_Far__error:
    .a8
    lda #SCUMM_ERR_SCRIPT
    jsl ScummV5_Camera_FarCall_SetError
    sec
    rtl
    .else
    clc
    rtl
    .endif

ScummV5_Camera_ResetState_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Camera_ResetState_Far__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_CAMERA_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_CAMERA_STATE_SIZE
    bcc ScummV5_Camera_ResetState_Far__clear
    lda #$00A0
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_CAMERA_DEST_X
    sta.l SAME_SCUMM_CAMERA_LAST_X
    lda #$0064
    sta.l SAME_SCUMM_CAMERA_CURRENT_Y
    sta.l SAME_SCUMM_CAMERA_DEST_Y
    sta.l SAME_SCUMM_CAMERA_LAST_Y
    lda #$0027
    sta.l SAME_SCUMM_CAMERA_SCREEN_END_STRIP
    clc
    rtl

ScummV5_Camera_Update_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_LHS
    and #$FFF8
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    lda.l SAME_SCUMM_CAMERA_DEST_X
    cmp.l SAME_SCUMM_C10_SCROLL_MIN
    bcs ScummV5_Camera_Update_Far__dest_min_ok
    lda.l SAME_SCUMM_C10_SCROLL_MIN
ScummV5_Camera_Update_Far__dest_min_ok:
    .a16
    cmp.l SAME_SCUMM_C10_SCROLL_MAX
    bcc ScummV5_Camera_Update_Far__dest_max_ok
    lda.l SAME_SCUMM_C10_SCROLL_MAX
ScummV5_Camera_Update_Far__dest_max_ok:
    .a16
    sta.l SAME_SCUMM_CAMERA_DEST_X
    sep #$20
    .a8
    lda.l SAME_SCUMM_C15_CAMERA_MODE
    bne ScummV5_Camera_Update_Far__camera_moved
    rep #$20
    .a16
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_M23B_VARIABLES+(26 * 2)
    .else
    lda #$0000
    .endif
    beq ScummV5_Camera_Update_Far__step
    lda.l SAME_SCUMM_CAMERA_DEST_X
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    bra ScummV5_Camera_Update_Far__camera_moved16
ScummV5_Camera_Update_Far__step:
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    cmp.l SAME_SCUMM_CAMERA_DEST_X
    beq ScummV5_Camera_Update_Far__camera_moved16
    bcs ScummV5_Camera_Update_Far__step_left
    clc
    adc #$0008
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    bra ScummV5_Camera_Update_Far__camera_moved16
ScummV5_Camera_Update_Far__step_left:
    .a16
    sec
    sbc #$0008
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
ScummV5_Camera_Update_Far__camera_moved:
    rep #$20
    .a16
ScummV5_Camera_Update_Far__camera_moved16:
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    cmp #$00A0
    bcs ScummV5_Camera_Update_Far__room_min_ok
    lda #$00A0
ScummV5_Camera_Update_Far__room_min_ok:
    .a16
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
    lda.l SAME_SCUMM_C10_ROOM_WIDTH
    sec
    sbc #$00A0
    cmp.l SAME_SCUMM_CAMERA_CURRENT_X
    bcs ScummV5_Camera_Update_Far__room_max_ok
    sta.l SAME_SCUMM_CAMERA_CURRENT_X
ScummV5_Camera_Update_Far__room_max_ok:
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    lsr
    lsr
    lsr
    sec
    sbc #$0014
    sta.l SAME_SCUMM_CAMERA_SCREEN_START_STRIP
    asl
    asl
    asl
    sta.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    lda.l SAME_SCUMM_CAMERA_SCREEN_START_STRIP
    clc
    adc #$0027
    sta.l SAME_SCUMM_CAMERA_SCREEN_END_STRIP
    sep #$20
    .a8
    lda.l SAME_SCUMM_CAMERA_UPDATE_PENDING
    bne ScummV5_Camera_Update_Far__publish
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_CAMERA_CURRENT_X
    beq ScummV5_Camera_Update_Far__finish
ScummV5_Camera_Update_Far__publish:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_PUBLISH_COUNT
    inc
    sta.l SAME_SCUMM_CAMERA_PUBLISH_COUNT
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    jsl ScummV5_Visual_CameraPublished_Far
    .endif
ScummV5_Camera_Update_Far__finish:
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_CURRENT_X
    sta.l SAME_SCUMM_CAMERA_LAST_X
    lda.l SAME_SCUMM_CAMERA_CURRENT_Y
    sta.l SAME_SCUMM_CAMERA_LAST_Y
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CAMERA_UPDATE_PENDING
    clc
    rtl
