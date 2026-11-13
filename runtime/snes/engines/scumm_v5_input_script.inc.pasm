; VAR_VERB_SCRIPT (32) raw input mailbox, independent of C20/variable 33.
; Queue: A16 click area, X16 value, Y16 mode. C=1 owns the input (including
; disabled/busy input); C=0 only when no authored callback is installed.
; Process allocates one ordinary C4 activation. The scheduler/cache, not
; the controller, fetches and executes its code and retains resource waits.
ScummV5_Input_Queue_Far:
    .if SAME_BUILD_SCUMM_M23B
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_M23B_VARIABLES+(32 * 2)
    bne ScummV5_Input_Queue__installed
    pla
    clc
    rtl
ScummV5_Input_Queue__installed:
    cmp #$0100
    bcc ScummV5_Input_Queue__number_valid
    pla
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
    jsl ScummV5_Camera_FarCall_SetError
    sec
    rtl
ScummV5_Input_Queue__number_valid:
    .a16
    lda.l SAME_SCUMM_C7_USERPUT_STATE
    beq ScummV5_Input_Queue__ignored
    bmi ScummV5_Input_Queue__ignored
    lda.l SAME_SCUMM_INPUT_EDGE_VALID
    and #$00FF
    beq ScummV5_Input_Queue__new_edge
    lda.l SAME_INPUT_EDGE_SEQUENCE
    cmp.l SAME_SCUMM_INPUT_EDGE
    beq ScummV5_Input_Queue__ignored
ScummV5_Input_Queue__new_edge:
    lda.l SAME_SCUMM_INPUT_PENDING
    and #$00FF
    bne ScummV5_Input_Queue__ignored
    pla
    cmp #$0001
    bcc ScummV5_Input_Queue__bad
    cmp #$0006
    bcs ScummV5_Input_Queue__bad
    cpy #$0003
    bcs ScummV5_Input_Queue__bad
    sta.l SAME_SCUMM_INPUT_AREA
    txa
    sta.l SAME_SCUMM_INPUT_VALUE
    tya
    sta.l SAME_SCUMM_INPUT_MODE
    lda.l SAME_INPUT_EDGE_SEQUENCE
    sta.l SAME_SCUMM_INPUT_EDGE
    lda.l SAME_SCUMM_INPUT_ACCEPTED
    inc
    sta.l SAME_SCUMM_INPUT_ACCEPTED
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_VARIABLES+(32 * 2)
    sta.l SAME_SCUMM_INPUT_SCRIPT
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_INPUT_ROOM
    lda #$01
    sta.l SAME_SCUMM_INPUT_PENDING
    sta.l SAME_SCUMM_INPUT_EDGE_VALID
    rep #$20
    .a16
    sec
    rtl
ScummV5_Input_Queue__ignored:
    .a16
    pla
    sec
    rtl
ScummV5_Input_Queue__bad:
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
    jsl ScummV5_Camera_FarCall_SetError
    rep #$20
    .a16
    sec
    rtl
    .else
    clc
    rtl
    .endif

ScummV5_Input_Process_Far:
    php
    rep #$10
    .i16
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_INPUT_PENDING
    bne ScummV5_Input_Process__pending
    jmp ScummV5_Input_Process__done
ScummV5_Input_Process__pending:
    lda.l SAME_SCUMM_INPUT_ROOM
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    beq ScummV5_Input_Process__same_room
    jmp ScummV5_Input_Process__consume
ScummV5_Input_Process__same_room:
    ; Normal nonrecursive runScript semantics, never a direct bytecode call.
    lda.l SAME_SCUMM_INPUT_SCRIPT
    jsl ScummV5_Camera_FarCall_StopNumber
    ldx #$0001
ScummV5_Input_Process__scan:
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Input_Process__slot
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Input_Process__slot
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Input_Process__scan
    lda #SCUMM_ERR_SLOT_CAPACITY
    jmp ScummV5_Input_Process__error
ScummV5_Input_Process__slot:
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    lda.l SAME_SCUMM_INPUT_SCRIPT
    cmp #SCUMM_V5_NUM_GLOBAL_SCRIPTS
    bcc ScummV5_Input_Process__global
    jsl ScummV5_Camera_FarCall_ResolveLocal
    bra ScummV5_Input_Process__resolved
ScummV5_Input_Process__global:
    jsl ScummV5_Camera_FarCall_ResolveGlobal
ScummV5_Input_Process__resolved:
    bcs ScummV5_Input_Process__program
    lda #SCUMM_ERR_SCRIPT
    jmp ScummV5_Input_Process__error
ScummV5_Input_Process__program:
    sta.l SAME_SCUMM_INPUT_SELECTOR
    lda.l SAME_SCUMM_INPUT_SCRIPT
    sta.l SAME_SCUMM_CONDITION
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jsl ScummV5_SlotMarkOrdinaryScript_Far
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    txa
    sta.l SAME_SCUMM_INPUT_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    lda.l SAME_SCUMM_INPUT_SCRIPT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_INPUT_SELECTOR
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_INPUT_ROOM
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
    lda.l SAME_SCUMM_INPUT_SLOT
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    lda #$0000
    ldy #$0000
ScummV5_Input_Process__locals:
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Input_Process__locals
    txa
    sec
    sbc #(SAME_SCUMM_LOCAL_COUNT * 2)
    tax
    lda.l SAME_SCUMM_INPUT_AREA
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    lda.l SAME_SCUMM_INPUT_VALUE
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    lda.l SAME_SCUMM_INPUT_MODE
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    lda.l SAME_SCUMM_INPUT_ALLOCATED
    inc
    sta.l SAME_SCUMM_INPUT_ALLOCATED
    lda.l SAME_SCUMM_INPUT_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Input_Process__consume:
    lda #$00
    sta.l SAME_SCUMM_INPUT_PENDING
ScummV5_Input_Process__done:
    .endif
    plp
    rtl
    .if SAME_BUILD_SCUMM_M23B
ScummV5_Input_Process__error:
    jsl ScummV5_Camera_FarCall_SetError
    jmp ScummV5_Input_Process__consume
    .endif

; Controller scene coordinates are virtual-screen logical pixels. Publish
; original v5 mouse globals before the next ordinary hover/callback pass.
ScummV5_Input_Scene_Far:
    rep #$30
    .a16
    .i16
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sta.l SAME_SCUMM_M23B_VARIABLES+(44 * 2)
    clc
    adc.l SAME_SCUMM_CAMERA_VSCREEN_XSTART
    sta.l SAME_SCUMM_M23B_VARIABLES+(20 * 2)
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    sta.l SAME_SCUMM_M23B_VARIABLES+(45 * 2)
    clc
    adc.l SAME_SCUMM_CAMERA_CURRENT_Y
    sec
    sbc #$0064
    sta.l SAME_SCUMM_M23B_VARIABLES+(21 * 2)
    lda.l SAME_INPUT_PRESSED
    and #$8080 ; A/B: primary/secondary pointer, not menu/cursor controls
    beq ScummV5_Input_Scene__none
    ldy #$0001
    and #$0080
    bne ScummV5_Input_Scene__button
    ldy #$0002
ScummV5_Input_Scene__button:
    lda.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    cmp.l SAME_SCUMM_C10_SCREEN_TOP
    bcc ScummV5_Input_Scene__verb_screen
    cmp.l SAME_SCUMM_C10_SCREEN_BOTTOM
    bcs ScummV5_Input_Scene__verb_screen
    lda #$0002
    bra ScummV5_Input_Scene__queue
ScummV5_Input_Scene__verb_screen:
    lda #$0001
ScummV5_Input_Scene__queue:
    ldx #$0000
    jml ScummV5_Input_Queue_Far
    .endif
ScummV5_Input_Scene__none:
    clc
    rtl
