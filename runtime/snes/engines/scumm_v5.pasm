; Independent SCUMM v5 semantic nucleus.  The ROM-resident conformance script
; is generated from copyright-free fixture bytes and checked against upstream
; ScummVM opcode/operand semantics.  This code contains no game, cursor, room,
; actor, Monkey, PPU, DMA, audio, or storage policy.
SCUMM_V5_ENGINE_ID = SAME_ENGINE_SCUMM_V5
SCUMM_V5_SAVE_SCHEMA = $0001
SCUMM_V5_MAX_SCRIPT_SLOTS = $0019

SCUMM_VM_RUNNING = $01
SCUMM_VM_YIELDED = $02
SCUMM_VM_DELAYED = $03
SCUMM_VM_STOPPED = $04
SCUMM_VM_ERROR   = $FF

SCUMM_ERR_NONE          = $00
SCUMM_ERR_PC_RANGE      = $01
SCUMM_ERR_VARIABLE      = $02
SCUMM_ERR_OPCODE        = $03
SCUMM_ERR_BUDGET        = $04
SCUMM_ERR_DELAY_RANGE   = $05
SCUMM_ERR_DIVIDE_ZERO   = $06
SCUMM_ERR_FIXTURE       = $07
SCUMM_ERR_BIT_VARIABLE  = $08
SCUMM_ERR_SLOT_CAPACITY = $09
SCUMM_ERR_LOCAL         = $0A
SCUMM_ERR_SCRIPT        = $0B
SCUMM_ERR_ARGUMENTS     = $0C
SCUMM_ERR_SERVICE       = $0D
SCUMM_ERR_STRING        = $0E
SCUMM_ERR_ROOM_OPS      = $0F
SCUMM_ERR_RESOURCE      = $10
SCUMM_ERR_ACTOR_OPS     = $11
SCUMM_ERR_CAMERA_FOLLOW = $12
SCUMM_ERR_SET_CLASS     = $13
SCUMM_ERR_VERB_OPS      = $14
SCUMM_ERR_EXPRESSION    = $15
SCUMM_ERR_CUTSCENE     = $16
SCUMM_ERR_SENTENCE     = $17
SCUMM_ERR_DRAW_OBJECT  = $18
SCUMM_ERR_SOUND_KLUDGE = $19
SCUMM_ERR_SAVE_VERBS   = $1A
SCUMM_ERR_ANIMATE_ACTOR = $1B

ScummV5_Engine_Boot:
    php
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_FIXTURE_REQUEST
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_RETURN_MODE
    sta.l SAME_SCUMM_C18_NESTED
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_PC,x
    inx
    inx
    cpx #SAME_SCUMM_STATE_SIZE
    bcc ScummV5_Engine_Boot__clear
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear_c4:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    inx
    cpx #SAME_SCUMM_C4_STATE_SIZE
    bcc ScummV5_Engine_Boot__clear_c4
    jsr ScummV5_C7_ResetState
    jsr ScummV5_C8_ResetState
    jsr ScummV5_C10_ResetState
    jsr ScummV5_C11_ResetState
    jsr ScummV5_C12_InvalidateState
    jsr ScummV5_C13_InvalidateState
    jsr ScummV5_C14_InvalidateState
    jsr ScummV5_C15_ResetState
    jsr ScummV5_C16_InvalidateState
    jsr ScummV5_C17_InvalidateState
    jsr ScummV5_C19_ResetState
    jsr ScummV5_C20_ResetState
    jsr ScummV5_C21_ResetState
    jsr ScummV5_C22_ResetState
    jsr ScummV5_C23_ResetState
    jsr ScummV5_C25_ResetState
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    plp
    clc
    rts

ScummV5_Engine_Frame:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_REQUEST
    cmp.l SAME_SCUMM_FIXTURE_ACTIVE
    bne ScummV5_Engine_Frame__fixture_changed
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__fixture_changed:
    .a8
    cmp #SCUMM_C2_FIXTURE_COUNT
    bcc ScummV5_Engine_Frame__select_fixture
    lda #SCUMM_ERR_FIXTURE
    jsr ScummV5_SetError
    jmp ScummV5_Engine_Frame__error
ScummV5_Engine_Frame__select_fixture:
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Frame__clear_fixture_state:
    .a16
    .i16
    sta.l SAME_SCUMM_PC,x
    inx
    inx
    cpx #SAME_SCUMM_STATE_SIZE
    bcc ScummV5_Engine_Frame__clear_fixture_state
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    beq ScummV5_Engine_Frame__reset_c7_state
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_Engine_Frame__c7_state_ready
ScummV5_Engine_Frame__reset_c7_state:
    jsr ScummV5_C7_ResetState
ScummV5_Engine_Frame__c7_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_Engine_Frame__c8_state_ready
    jsr ScummV5_C8_ResetState
ScummV5_Engine_Frame__c8_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_Engine_Frame__c9_state_ready
    jsr ScummV5_C4_ResetState
ScummV5_Engine_Frame__c9_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_Engine_Frame__c10_state_ready
    jsr ScummV5_C10_ResetState
ScummV5_Engine_Frame__c10_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_Engine_Frame__c11_state_ready
    jsr ScummV5_C11_ResetState
ScummV5_Engine_Frame__c11_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_Engine_Frame__c12_state_ready
    jsr ScummV5_C12_ResetState
ScummV5_Engine_Frame__c12_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_Engine_Frame__c13_state_ready
    jsr ScummV5_C13_ResetState
ScummV5_Engine_Frame__c13_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    beq ScummV5_Engine_Frame__reset_c14_state
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    bne ScummV5_Engine_Frame__c14_state_ready
ScummV5_Engine_Frame__reset_c14_state:
    jsr ScummV5_C14_ResetState
ScummV5_Engine_Frame__c14_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_Engine_Frame__c15_state_ready
    jsr ScummV5_C15_ResetState
ScummV5_Engine_Frame__c15_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    bne ScummV5_Engine_Frame__c16_state_ready
    jsr ScummV5_C16_ResetState
ScummV5_Engine_Frame__c16_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    beq ScummV5_Engine_Frame__reset_c17_state
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_Engine_Frame__c17_state_ready
ScummV5_Engine_Frame__reset_c17_state:
    jsr ScummV5_C17_ResetState
ScummV5_Engine_Frame__c17_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_Engine_Frame__c19_state_ready
    jsr ScummV5_C19_ResetState
ScummV5_Engine_Frame__c19_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_Engine_Frame__c20_state_ready
    jsr ScummV5_C20_ResetState
ScummV5_Engine_Frame__c20_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    bne ScummV5_Engine_Frame__c21_state_ready
    jsr ScummV5_C21_ResetState
ScummV5_Engine_Frame__c21_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    bne ScummV5_Engine_Frame__c22_state_ready
    jsr ScummV5_C22_ResetState
ScummV5_Engine_Frame__c22_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_Engine_Frame__c23_state_ready
    jsr ScummV5_C23_ResetState
ScummV5_Engine_Frame__c23_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_Engine_Frame__c24_state_ready
    jsr ScummV5_C19_ResetState
ScummV5_Engine_Frame__c24_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_Engine_Frame__c25_state_ready
    jsr ScummV5_C25_ResetState
ScummV5_Engine_Frame__c25_state_ready:
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    beq ScummV5_Engine_Frame__init_c3
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    beq ScummV5_Engine_Frame__init_c4_lifecycle
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    beq ScummV5_Engine_Frame__init_c4_capacity
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    beq ScummV5_Engine_Frame__init_c5_scheduler
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_Engine_Frame__check_init_c6_missing
    jmp ScummV5_Engine_Frame__init_c6_scheduler
ScummV5_Engine_Frame__check_init_c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_Engine_Frame__check_init_c6_capacity
    jmp ScummV5_Engine_Frame__init_c6_missing
ScummV5_Engine_Frame__check_init_c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_Engine_Frame__init_done
    jmp ScummV5_Engine_Frame__init_c6_capacity
ScummV5_Engine_Frame__init_done:
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c3:
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_SLOT0_STATUS
    sta.l SAME_SCUMM_SLOT1_STATUS
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c4_lifecycle:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c4_capacity:
    .a8
    jsr ScummV5_C4_ResetState
    ldx #$0000
    lda #SCUMM_VM_RUNNING
ScummV5_Engine_Frame__fill_c4_capacity:
    .a8
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Engine_Frame__fill_c4_capacity
    lda #SCUMM_V5_MAX_SCRIPT_SLOTS
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda #SCUMM_C2_FIXTURE_C4_CAPACITY
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c5_scheduler:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C5_SCHEDULER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_scheduler:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C6_SCHEDULER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_missing:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C6_MISSING
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_capacity:
    .a8
    jsr ScummV5_C4_ResetState
    ldx #$0000
    lda #SCUMM_VM_RUNNING
ScummV5_Engine_Frame__fill_c6_capacity:
    .a8
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Engine_Frame__fill_c6_capacity
    lda #SCUMM_V5_MAX_SCRIPT_SLOTS
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda #SCUMM_C2_FIXTURE_C6_CAPACITY
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
ScummV5_Engine_Frame__fixture_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    beq ScummV5_Engine_Frame__run_c3
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    beq ScummV5_Engine_Frame__run_c4
    bra ScummV5_Engine_Frame__single_fixture
ScummV5_Engine_Frame__run_c3:
    jmp ScummV5_C3_Scheduler_Frame
ScummV5_Engine_Frame__run_c4:
    jmp ScummV5_C4_Scheduler_Frame
ScummV5_Engine_Frame__single_fixture:
    .a8
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
ScummV5_Engine_RunSelected:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_FRAME_OPS

    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    bne ScummV5_Engine_Frame__check_error_status
    jmp ScummV5_Engine_Frame__return_success
ScummV5_Engine_Frame__check_error_status:
    .a8
    cmp #SCUMM_VM_ERROR
    bne ScummV5_Engine_Frame__check_delay_state
    jmp ScummV5_Engine_Frame__error

ScummV5_Engine_Frame__check_delay_state:
    rep #$20
    .a16
    lda.l SAME_SCUMM_DELAY
    beq ScummV5_Engine_Frame__start
    dec
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Engine_Frame__start:
    rep #$30
    .a16
    .i16
    lda #SAME_SCUMM_MAX_OPS_PER_FRAME
    sta.l SAME_SCUMM_BUDGET
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS

ScummV5_Engine_Frame__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_next
    dec
    sta.l SAME_SCUMM_C18_NESTED
    clc
    rts
ScummV5_Engine_Frame__outer_next:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_BUDGET
    bne ScummV5_Engine_Frame__budget_available
    jmp ScummV5_Engine_Frame__budget_error
ScummV5_Engine_Frame__budget_available:
    .a16
    .i16
    dec
    sta.l SAME_SCUMM_BUDGET
    jsr ScummV5_FetchByte
    bcc ScummV5_Engine_Frame__opcode_fetched
    jmp ScummV5_Engine_Frame__error
ScummV5_Engine_Frame__opcode_fetched:
    sta.l SAME_SCUMM_LAST_OPCODE
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    inc
    sta.l SAME_SCUMM_FRAME_OPS
    lda.l SAME_SCUMM_TOTAL_OPS
    inc
    sta.l SAME_SCUMM_TOTAL_OPS

ScummV5_DispatchCurrentOpcode:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$00
    bne ScummV5_Engine_Frame__check_break
    jmp ScummV5_Op_Stop
ScummV5_Engine_Frame__check_break:
    .a8
    cmp #$80
    bne ScummV5_Engine_Frame__check_move_direct
    jmp ScummV5_Op_BreakHere
ScummV5_Engine_Frame__check_move_direct:
    .a8
    cmp #$1A
    beq ScummV5_Engine_Frame__dispatch_move
    cmp #$9A
    bne ScummV5_Engine_Frame__check_add
ScummV5_Engine_Frame__dispatch_move:
    jmp ScummV5_Op_Move
ScummV5_Engine_Frame__check_add:
    .a8
    cmp #$5A
    beq ScummV5_Engine_Frame__dispatch_add
    cmp #$DA
    bne ScummV5_Engine_Frame__check_subtract
ScummV5_Engine_Frame__dispatch_add:
    jmp ScummV5_Op_Add
ScummV5_Engine_Frame__check_subtract:
    .a8
    cmp #$3A
    beq ScummV5_Engine_Frame__dispatch_subtract
    cmp #$BA
    bne ScummV5_Engine_Frame__check_multiply
ScummV5_Engine_Frame__dispatch_subtract:
    jmp ScummV5_Op_Subtract
ScummV5_Engine_Frame__check_multiply:
    .a8
    cmp #$1B
    beq ScummV5_Engine_Frame__dispatch_multiply
    cmp #$9B
    bne ScummV5_Engine_Frame__check_divide
ScummV5_Engine_Frame__dispatch_multiply:
    jmp ScummV5_Op_Multiply
ScummV5_Engine_Frame__check_divide:
    .a8
    cmp #$5B
    beq ScummV5_Engine_Frame__dispatch_divide
    cmp #$DB
    bne ScummV5_Engine_Frame__check_and
ScummV5_Engine_Frame__dispatch_divide:
    jmp ScummV5_Op_Divide
ScummV5_Engine_Frame__check_and:
    .a8
    cmp #$17
    beq ScummV5_Engine_Frame__dispatch_and
    cmp #$97
    bne ScummV5_Engine_Frame__check_or
ScummV5_Engine_Frame__dispatch_and:
    jmp ScummV5_Op_And
ScummV5_Engine_Frame__check_or:
    .a8
    cmp #$57
    beq ScummV5_Engine_Frame__dispatch_or
    cmp #$D7
    bne ScummV5_Engine_Frame__check_increment
ScummV5_Engine_Frame__dispatch_or:
    jmp ScummV5_Op_Or
ScummV5_Engine_Frame__check_increment:
    .a8
    cmp #$46
    bne ScummV5_Engine_Frame__check_decrement
    jmp ScummV5_Op_Increment
ScummV5_Engine_Frame__check_decrement:
    .a8
    cmp #$C6
    bne ScummV5_Engine_Frame__check_compare
    jmp ScummV5_Op_Decrement
ScummV5_Engine_Frame__check_compare:
    .a8
    and #$7F
    cmp #$48
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$08
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$44
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$78
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$38
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$04
    bne ScummV5_Engine_Frame__check_zero_compare
ScummV5_Engine_Frame__dispatch_compare:
    jmp ScummV5_Op_Compare
ScummV5_Engine_Frame__check_zero_compare:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$28
    beq ScummV5_Engine_Frame__dispatch_zero_compare
    cmp #$A8
    bne ScummV5_Engine_Frame__check_jump
ScummV5_Engine_Frame__dispatch_zero_compare:
    jmp ScummV5_Op_CompareZero
ScummV5_Engine_Frame__check_jump:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$18
    bne ScummV5_Engine_Frame__check_delay
    jmp ScummV5_Op_JumpRelative
ScummV5_Engine_Frame__check_delay:
    .a8
    cmp #$2E
    bne ScummV5_Engine_Frame__check_delay_variable
    jmp ScummV5_Op_Delay
ScummV5_Engine_Frame__check_delay_variable:
    .a8
    cmp #$2B
    bne ScummV5_Engine_Frame__check_start_music
    jmp ScummV5_Op_DelayVariable
ScummV5_Engine_Frame__check_start_music:
    .a8
    cmp #$02
    beq ScummV5_Engine_Frame__dispatch_start_music
    cmp #$82
    bne ScummV5_Engine_Frame__check_stop_music
ScummV5_Engine_Frame__dispatch_start_music:
    jmp ScummV5_Op_StartMusic
ScummV5_Engine_Frame__check_stop_music:
    .a8
    cmp #$20
    bne ScummV5_Engine_Frame__check_start_sound
    jmp ScummV5_Op_StopMusic
ScummV5_Engine_Frame__check_start_sound:
    .a8
    cmp #$1C
    beq ScummV5_Engine_Frame__dispatch_start_sound
    cmp #$9C
    bne ScummV5_Engine_Frame__check_stop_sound
ScummV5_Engine_Frame__dispatch_start_sound:
    jmp ScummV5_Op_StartSound
ScummV5_Engine_Frame__check_stop_sound:
    .a8
    cmp #$3C
    beq ScummV5_Engine_Frame__dispatch_stop_sound
    cmp #$BC
    bne ScummV5_Engine_Frame__check_start_script
ScummV5_Engine_Frame__dispatch_stop_sound:
    jmp ScummV5_Op_StopSound
ScummV5_Engine_Frame__check_start_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$0A
    bne ScummV5_Engine_Frame__check_stop_script
    jmp ScummV5_Op_StartScript
ScummV5_Engine_Frame__check_stop_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$62
    bne ScummV5_Engine_Frame__check_freeze_scripts
    jmp ScummV5_Op_StopScript
ScummV5_Engine_Frame__check_freeze_scripts:
    .a8
    cmp #$60
    bne ScummV5_Engine_Frame__check_script_running
    jmp ScummV5_Op_FreezeScripts
ScummV5_Engine_Frame__check_script_running:
    .a8
    cmp #$68
    bne ScummV5_Engine_Frame__check_chain_script
    jmp ScummV5_Op_IsScriptRunning
ScummV5_Engine_Frame__check_chain_script:
    .a8
    cmp #$42
    bne ScummV5_Engine_Frame__check_set_var_range
    jmp ScummV5_Op_ChainScript
ScummV5_Engine_Frame__check_set_var_range:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$26
    bne ScummV5_Engine_Frame__check_room_ops
    jmp ScummV5_Op_SetVarRange
ScummV5_Engine_Frame__check_room_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$33
    bne ScummV5_Engine_Frame__check_random
    jmp ScummV5_Op_RoomOps
ScummV5_Engine_Frame__check_random:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$16
    bne ScummV5_Engine_Frame__check_pseudo_room
    jmp ScummV5_Op_GetRandom
ScummV5_Engine_Frame__check_pseudo_room:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$CC
    bne ScummV5_Engine_Frame__check_resource_routines
    jmp ScummV5_Op_PseudoRoom
ScummV5_Engine_Frame__check_resource_routines:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$0C
    bne ScummV5_Engine_Frame__check_actor_ops
    jmp ScummV5_Op_ResourceRoutines
ScummV5_Engine_Frame__check_actor_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$13
    bne ScummV5_Engine_Frame__check_actor_follow_camera
    jmp ScummV5_Op_ActorOps
ScummV5_Engine_Frame__check_actor_follow_camera:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$52
    bne ScummV5_Engine_Frame__check_set_class
    jmp ScummV5_Op_ActorFollowCamera
ScummV5_Engine_Frame__check_set_class:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$5D
    bne ScummV5_Engine_Frame__check_verb_ops
    jmp ScummV5_Op_SetClass
ScummV5_Engine_Frame__check_verb_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$7A
    bne ScummV5_Engine_Frame__check_expression
    jmp ScummV5_Op_VerbOps
ScummV5_Engine_Frame__check_expression:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$AC
    bne ScummV5_Engine_Frame__check_string_ops
    jmp ScummV5_Op_Expression
ScummV5_Engine_Frame__check_string_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$27
    bne ScummV5_Engine_Frame__check_cursor_command
    jmp ScummV5_Op_StringOps
ScummV5_Engine_Frame__check_cursor_command:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$2C
    bne ScummV5_Engine_Frame__check_cutscene
    jmp ScummV5_Op_CursorCommand

; Keep new, comparatively rare families at the tail of the linear dispatch.
; This preserves the established per-frame timing of the common C1-C18 path.
ScummV5_Engine_Frame__check_cutscene:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$40
    beq ScummV5_Engine_Frame__dispatch_cutscene
    cmp #$C0
    beq ScummV5_Engine_Frame__dispatch_cutscene
    cmp #$58
    bne ScummV5_Engine_Frame__check_do_sentence
ScummV5_Engine_Frame__dispatch_cutscene:
    jmp ScummV5_Op_CutsceneDispatch
ScummV5_Engine_Frame__check_do_sentence:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$19
    bne ScummV5_Engine_Frame__check_draw_object
    jmp ScummV5_Op_DoSentence
ScummV5_Engine_Frame__check_draw_object:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$05
    bne ScummV5_Engine_Frame__check_load_room
    jmp ScummV5_Op_DrawObject
ScummV5_Engine_Frame__check_load_room:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$72
    bne ScummV5_Engine_Frame__check_print
    jmp ScummV5_Op_LoadRoom
ScummV5_Engine_Frame__check_print:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$14
    beq ScummV5_Engine_Frame__dispatch_print
    cmp #$94
    beq ScummV5_Engine_Frame__dispatch_print
    cmp #$D8
    beq ScummV5_Engine_Frame__dispatch_print
    cmp #$4C
    bne ScummV5_Engine_Frame__check_save_restore_verbs
    jmp ScummV5_Op_SoundKludge
ScummV5_Engine_Frame__check_save_restore_verbs:
    .a8
    cmp #$AB
    bne ScummV5_Engine_Frame__check_animate_actor
    jmp ScummV5_Op_SaveRestoreVerbs
ScummV5_Engine_Frame__check_animate_actor:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$11
    bne ScummV5_Engine_Frame__opcode_error
    jmp ScummV5_Op_AnimateActor
ScummV5_Engine_Frame__dispatch_print:
    jmp ScummV5_Op_Print

ScummV5_Engine_Frame__opcode_error:
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
    bra ScummV5_Engine_Frame__error

ScummV5_Engine_Frame__budget_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_BUDGET
    jsr ScummV5_SetError

ScummV5_Engine_Frame__error:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_error_check
    dec
    sta.l SAME_SCUMM_C18_NESTED
    sec
    rts
ScummV5_Engine_Frame__outer_error_check:
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_error
    sec
    rts
ScummV5_Engine_Frame__outer_error:
    plp
    sec
    rts
ScummV5_Engine_Frame__complete_success:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_complete_check
    dec
    sta.l SAME_SCUMM_C18_NESTED
    clc
    rts
ScummV5_Engine_Frame__outer_complete_check:
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_complete_success
    clc
    rts
ScummV5_Engine_Frame__outer_complete_success:
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    inc
    sta.l SAME_SCUMM_FRAME_COUNT
ScummV5_Engine_Frame__return_success:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_return_success
    clc
    rts
ScummV5_Engine_Frame__outer_return_success:
    plp
    clc
    rts

; C3's two-slot fixture uses the same decoder one slot at a time. Each slot's
; PC, delay, and status are restored before execution and saved afterward;
; variables and total operation count are intentionally shared VM state.
ScummV5_C3_Scheduler_Frame:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SCHED_OPS

    lda.l SAME_SCUMM_SLOT0_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_SLOT0_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_SLOT0_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SLOT0
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    jsr ScummV5_Engine_RunSelected
    bcc ScummV5_C3_Scheduler_Frame__slot0_done
    jmp ScummV5_C3_Scheduler_Frame__error
ScummV5_C3_Scheduler_Frame__slot0_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SLOT0_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_SLOT0_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_SCHED_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SLOT0_STATUS

    rep #$20
    .a16
    lda.l SAME_SCUMM_SLOT1_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_SLOT1_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_SLOT1_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SLOT1
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    jsr ScummV5_Engine_RunSelected
    bcc ScummV5_C3_Scheduler_Frame__slot1_done
    jmp ScummV5_C3_Scheduler_Frame__error
ScummV5_C3_Scheduler_Frame__slot1_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SLOT1_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_SLOT1_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SLOT1_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SCHEDULER
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C3_Scheduler_Frame__error:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    jmp ScummV5_Engine_Frame__error

; C4 owns a fixed 25-entry slot table. Slot zero carries the fixture's parent
; script; startScript allocates the first dead entry from slots 1..24.
ScummV5_C4_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C4_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    inx
    cpx #SAME_SCUMM_C4_STATE_SIZE
    bcc ScummV5_C4_ResetState__loop
    sep #$20
    .a8
    rts

ScummV5_C4_Scheduler_Frame:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    ldx #$0000
ScummV5_C4_Scheduler_Frame__clear_didexec:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_Scheduler_Frame__clear_didexec
    lda #$00
    sta.l SAME_SCUMM_C4_SCHED_SLOT
ScummV5_C4_Scheduler_Frame__next_slot:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_Scheduler_Frame__slot_in_range
    jmp ScummV5_C4_Scheduler_Frame__complete
ScummV5_C4_Scheduler_Frame__slot_in_range:
    .a8
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_C4_Scheduler_Frame__advance
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_C4_Scheduler_Frame__advance
    cmp #SCUMM_VM_ERROR
    beq ScummV5_C4_Scheduler_Frame__advance
    lda.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    bne ScummV5_C4_Scheduler_Frame__advance
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    bne ScummV5_C4_Scheduler_Frame__advance
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    plp
    bcs ScummV5_C4_Scheduler_Frame__error
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCHED_OPS
    clc
    adc.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_SCHED_OPS
ScummV5_C4_Scheduler_Frame__advance:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    inc
    sta.l SAME_SCUMM_C4_SCHED_SLOT
    jmp ScummV5_C4_Scheduler_Frame__next_slot
ScummV5_C4_Scheduler_Frame__complete:
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_C4_Scheduler_Frame__stopped
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C4_Scheduler_Frame__stopped:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C4_Scheduler_Frame__error:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    jmp ScummV5_Engine_Frame__error

ScummV5_C4_SaveCurrentSlot:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    rts

ScummV5_C4_RunNestedChild:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_PARENT_STATUS
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_C4_PARENT_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_PARENT_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_PARENT_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_C4_PARENT_OPS
    jsr ScummV5_C4_SaveCurrentSlot
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
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
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_C4_PARENT_OPS
    sta.l SAME_SCUMM_C4_PARENT_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_PARENT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_PARENT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_PARENT_DELAY
    sta.l SAME_SCUMM_DELAY
    lda.l SAME_SCUMM_C4_PARENT_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    plp
    bcc ScummV5_C4_RunNestedChild__success
    sep #$20
    .a8
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rts
ScummV5_C4_RunNestedChild__success:
    clc
    rts

; Run a freshly allocated replacement without restoring the retired caller.
; Separate operation scratch preserves an enclosing startScript parent frame.
ScummV5_C4_RunAllocatedNoParent:
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_C4_CHAIN_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
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
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_C4_CHAIN_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    plp
    rts

; Stop every live global/local script with the requested number. A8 holds the
; number on entry. Script zero is handled by the opcode as self-stop.
ScummV5_C4_StopNumber:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    ldx #$0000
ScummV5_C4_StopNumber__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_C4_StopNumber__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_C4_StopNumber__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_C4_StopNumber__next
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp.l SAME_SCUMM_CONDITION
    bne ScummV5_C4_StopNumber__next
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_C4_StopNumber__current
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_C4_StopNumber__current:
    .a8
    .i16
    txa
    cmp.l SAME_SCUMM_C4_CURRENT_SLOT
    bne ScummV5_C4_StopNumber__next
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
ScummV5_C4_StopNumber__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_StopNumber__scan
    lda.l SAME_SCUMM_CONDITION
    rts

ScummV5_Engine_Suspend:
    clc
    rts
ScummV5_Engine_Resume:
    clc
    rts
ScummV5_Engine_Shutdown:
    clc
    rts

; ---------------------------------------------------------------------------
; Opcode handlers
; ---------------------------------------------------------------------------
ScummV5_Op_RoomOps:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_RoomOps__subop_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_Op_RoomOps__dispatch_02
    jmp ScummV5_Op_RoomOps__scroll
ScummV5_Op_RoomOps__dispatch_02:
    .a8
    cmp #$02
    bne ScummV5_Op_RoomOps__dispatch_03
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__dispatch_03:
    .a8
    cmp #$03
    bne ScummV5_Op_RoomOps__dispatch_04
    jmp ScummV5_Op_RoomOps__screen
ScummV5_Op_RoomOps__dispatch_04:
    .a8
    cmp #$04
    bne ScummV5_Op_RoomOps__dispatch_05
    jmp ScummV5_Op_RoomOps__palette
ScummV5_Op_RoomOps__dispatch_05:
    .a8
    cmp #$05
    bne ScummV5_Op_RoomOps__dispatch_06
    jmp ScummV5_Op_RoomOps__shake_on
ScummV5_Op_RoomOps__dispatch_06:
    .a8
    cmp #$06
    bne ScummV5_Op_RoomOps__dispatch_07
    jmp ScummV5_Op_RoomOps__shake_off
ScummV5_Op_RoomOps__dispatch_07:
    .a8
    cmp #$07
    bne ScummV5_Op_RoomOps__dispatch_08
    jmp ScummV5_Op_RoomOps__scale
ScummV5_Op_RoomOps__dispatch_08:
    .a8
    cmp #$08
    bne ScummV5_Op_RoomOps__dispatch_09
    jmp ScummV5_Op_RoomOps__intensity
ScummV5_Op_RoomOps__dispatch_09:
    .a8
    cmp #$09
    bne ScummV5_Op_RoomOps__dispatch_0a
    jmp ScummV5_Op_RoomOps__savegame
ScummV5_Op_RoomOps__dispatch_0a:
    .a8
    cmp #$0A
    bne ScummV5_Op_RoomOps__dispatch_0b
    jmp ScummV5_Op_RoomOps__fade
ScummV5_Op_RoomOps__dispatch_0b:
    .a8
    cmp #$0B
    bne ScummV5_Op_RoomOps__dispatch_0c
    jmp ScummV5_Op_RoomOps__rgb
ScummV5_Op_RoomOps__dispatch_0c:
    .a8
    cmp #$0C
    bne ScummV5_Op_RoomOps__dispatch_0d
    jmp ScummV5_Op_RoomOps__shadow
ScummV5_Op_RoomOps__dispatch_0d:
    .a8
    cmp #$0D
    bne ScummV5_Op_RoomOps__dispatch_0e
    jmp ScummV5_Op_RoomOps__save_string
ScummV5_Op_RoomOps__dispatch_0e:
    .a8
    cmp #$0E
    bne ScummV5_Op_RoomOps__dispatch_0f
    jmp ScummV5_Op_RoomOps__load_string
ScummV5_Op_RoomOps__dispatch_0f:
    .a8
    cmp #$0F
    bne ScummV5_Op_RoomOps__dispatch_10
    jmp ScummV5_Op_RoomOps__transform
ScummV5_Op_RoomOps__dispatch_10:
    .a8
    cmp #$10
    bne ScummV5_Op_RoomOps__dispatch_invalid
    jmp ScummV5_Op_RoomOps__cycle
ScummV5_Op_RoomOps__dispatch_invalid:
    jmp ScummV5_Op_RoomOps__invalid

ScummV5_Op_RoomOps__scroll:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_1
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_1:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_2
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_2:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_ROOM_WIDTH
    sec
    sbc #$00A0
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$00A0
    bcs ScummV5_Op_RoomOps__scroll_min_half
    lda #$00A0
ScummV5_Op_RoomOps__scroll_min_half:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_RoomOps__scroll_min_ready
    lda.l SAME_SCUMM_OPERAND
ScummV5_Op_RoomOps__scroll_min_ready:
    .a16
    sta.l SAME_SCUMM_C10_SCROLL_MIN
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$00A0
    bcs ScummV5_Op_RoomOps__scroll_max_half
    lda #$00A0
ScummV5_Op_RoomOps__scroll_max_half:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_RoomOps__scroll_max_ready
    lda.l SAME_SCUMM_OPERAND
ScummV5_Op_RoomOps__scroll_max_ready:
    sta.l SAME_SCUMM_C10_SCROLL_MAX
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__screen:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_3
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_3:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_4
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_4:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp.l SAME_SCUMM_C10_PARAM1
    bcc ScummV5_Op_RoomOps__screen_ordered
    beq ScummV5_Op_RoomOps__screen_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__screen_ordered:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$00C9
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_1
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_1:
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SCREEN_TOP
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SCREEN_BOTTOM
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__palette:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_5
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_5:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_6
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_6:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_7
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_7:
    .a16
    sta.l SAME_SCUMM_C10_PARAM2
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_2
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_2:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_3
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_3:
    .a16
    lda.l SAME_SCUMM_C10_PARAM2
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_4
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_4:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_8
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_8:
    .a8
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_9
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_9:
    .a8
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_C10_MarkPalette
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    asl
    clc
    adc.l SAME_SCUMM_PRODUCT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_PALETTE_RGB,x
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_PALETTE_RGB+1,x
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_PALETTE_RGB+2,x
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__shake_on:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C10_SHAKE
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__shake_off:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C10_SHAKE
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__scale:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_10
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_10:
    .a8
    sta.l SAME_SCUMM_C10_PARAM0
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_11
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_11:
    .a8
    sta.l SAME_SCUMM_C10_PARAM1
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_12
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_12:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_13
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_13:
    .a8
    sta.l SAME_SCUMM_C10_PARAM2
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_14
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_14:
    .a8
    sta.l SAME_SCUMM_C10_PARAM3
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_15
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_15:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_16
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_16:
    .a8
    cmp #$01
    bcs ScummV5_Op_RoomOps__invalid_bcc_ok_1
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcc_ok_1:
    .a8
    cmp #$05
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_5
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_5:
    dec
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SCALE_SLOTS,x
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+1,x
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+2,x
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+3,x
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__intensity:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_17
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_17:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY
    sta.l SAME_SCUMM_C10_INTENSITY+1
    sta.l SAME_SCUMM_C10_INTENSITY+2
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_18
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_18:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY+3
    lda #$20
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_19
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_19:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY+4
    lda.l SAME_SCUMM_C10_INTENSITY+3
    cmp.l SAME_SCUMM_C10_INTENSITY+4
    bcs ScummV5_Op_RoomOps__done_bcc_skip_1
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__done_bcc_skip_1:
    bne ScummV5_Op_RoomOps__done_beq_skip_1
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__done_beq_skip_1:
    jmp ScummV5_Op_RoomOps__invalid

ScummV5_Op_RoomOps__savegame:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_20
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_20:
    .a8
    sta.l SAME_SCUMM_C10_SAVE_FLAG
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_21
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_21:
    .a8
    lda #$63
    sta.l SAME_SCUMM_C10_SAVE_SLOT
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__fade:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_22
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_22:
    .a16
    sta.l SAME_SCUMM_C10_FADE
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__rgb:
    sep #$20
    .a8
    lda #$00
    bra ScummV5_Op_RoomOps__five_colors
ScummV5_Op_RoomOps__shadow:
    sep #$20
    .a8
    lda #$01
ScummV5_Op_RoomOps__five_colors:
    sta.l SAME_SCUMM_C10_PARAM4
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_23
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_23:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_24
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_24:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_25
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_25:
    .a16
    sta.l SAME_SCUMM_C10_PARAM2
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_6
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_6:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_7
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_7:
    .a16
    lda.l SAME_SCUMM_C10_PARAM2
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_8
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_8:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_26
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_26:
    .a8
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_27
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_27:
    .a8
    sta.l SAME_SCUMM_C10_PARAM3
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_28
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_28:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_Op_RoomOps__five_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__five_ordered:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM4
    cmp #$00
    beq ScummV5_Op_RoomOps__store_rgb
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SHADOW
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SHADOW+1
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_SHADOW+2
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_SHADOW+3
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_SHADOW+4
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__store_rgb:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_RGB_INTENSITY
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+1
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+2
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+3
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+4
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__save_string:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_29
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_29:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C10_ReadFilename
    bcc ScummV5_Op_RoomOps__error_ok_30
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_30:
    .a8
    jsr ScummV5_C10_SaveAuxString
    bcc ScummV5_Op_RoomOps__error_ok_31
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_31:
    .a8
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__load_string:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_32
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_32:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C10_ReadFilename
    bcc ScummV5_Op_RoomOps__error_ok_33
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_33:
    .a8
    jsr ScummV5_C10_LoadAuxString
    bcc ScummV5_Op_RoomOps__error_ok_34
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_34:
    .a8
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__transform:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_35
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_35:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_36
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_36:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_37
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_37:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+1
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_38
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_38:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+2
    cmp.l SAME_SCUMM_C10_TRANSFORM+1
    bcs ScummV5_Op_RoomOps__transform_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__transform_ordered:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_39
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_39:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_40
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_40:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+3
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__cycle:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_41
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_41:
    .a8
    cmp #$01
    bcs ScummV5_Op_RoomOps__invalid_bcc_ok_2
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcc_ok_2:
    .a8
    cmp #$11
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_9
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_9:
    .a8
    dec
    sta.l SAME_SCUMM_C10_PARAM0
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_42
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_42:
    .a8
    jsr ScummV5_C10_StoreCycleDelay
    bcc ScummV5_Op_RoomOps__error_ok_43
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_43:
    .a8
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ROOM_OPS
    jsr ScummV5_SetError
ScummV5_Op_RoomOps__error:
    jmp ScummV5_Op__error
ScummV5_Op_RoomOps__done:
    sep #$20
    .a8
    lda #$33
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_GetRandom:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_GetRandom__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_GetRandom__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_GetRandom__maximum_ok
    jmp ScummV5_Op__error
ScummV5_Op_GetRandom__maximum_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C11_MAXIMUM
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C11_MAXIMUM
    lda.l SAME_SCUMM_C11_RANDOM_STATE
    lsr
    bcc ScummV5_Op_GetRandom__state_ready
    eor #$B400
ScummV5_Op_GetRandom__state_ready:
    .a16
    sta.l SAME_SCUMM_C11_RANDOM_STATE
    xba
    and #$00FF
    sta.l SAME_SCUMM_C11_SAMPLE
    lda.l SAME_SCUMM_C11_MAXIMUM
    cmp #$00FF
    beq ScummV5_Op_GetRandom__full_byte
    inc
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C11_SAMPLE
ScummV5_Op_GetRandom__reduce:
    .a16
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_GetRandom__store
    sec
    sbc.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_GetRandom__reduce
ScummV5_Op_GetRandom__full_byte:
    .a16
    lda.l SAME_SCUMM_C11_SAMPLE
ScummV5_Op_GetRandom__store:
    .a16
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_PseudoRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C12_INITIALIZED
    bne ScummV5_Op_PseudoRoom__state_ready
    jsr ScummV5_C12_ResetState
ScummV5_Op_PseudoRoom__state_ready:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_PseudoRoom__error
    sta.l SAME_SCUMM_C12_ROOM
ScummV5_Op_PseudoRoom__next:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_PseudoRoom__error
    beq ScummV5_Op_PseudoRoom__done
    bpl ScummV5_Op_PseudoRoom__next
    and #$7F
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C12_ROOM
    sta.l SAME_SCUMM_C12_MAPPER,x
    bra ScummV5_Op_PseudoRoom__next
ScummV5_Op_PseudoRoom__done:
    .a8
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_PseudoRoom__error:
    jmp ScummV5_Op__error

ScummV5_Op_ResourceRoutines:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_INITIALIZED
    bne ScummV5_Op_ResourceRoutines__state_ready
    jsr ScummV5_C13_ResetState
ScummV5_Op_ResourceRoutines__state_ready:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_ResourceRoutines__selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__selector_ok:
    .a8
    sta.l SAME_SCUMM_C13_SELECTOR
    and #$3F
    sta.l SAME_SCUMM_C13_OPERATION
    cmp #$11
    bne ScummV5_Op_ResourceRoutines__not_clear_heap
    jmp ScummV5_Op_ResourceRoutines__done
ScummV5_Op_ResourceRoutines__not_clear_heap:
    .a8
    cmp #$01
    bcs ScummV5_Op_ResourceRoutines__minimum_ok
    jmp ScummV5_Op_ResourceRoutines__invalid
ScummV5_Op_ResourceRoutines__minimum_ok:
    .a8
    cmp #$15
    bcc ScummV5_Op_ResourceRoutines__maximum_ok
    jmp ScummV5_Op_ResourceRoutines__invalid
ScummV5_Op_ResourceRoutines__maximum_ok:
    .a8
    cmp #$14
    bne ScummV5_Op_ResourceRoutines__not_object
    jmp ScummV5_Op_ResourceRoutines__object
ScummV5_Op_ResourceRoutines__not_object:
    .a8
    lda.l SAME_SCUMM_C13_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ResourceRoutines__resource_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__resource_ok:
    .a8
    sta.l SAME_SCUMM_C13_RESOURCE
    lda.l SAME_SCUMM_C13_OPERATION
    cmp #$05
    bcc ScummV5_Op_ResourceRoutines__load_kind
    cmp #$09
    bcc ScummV5_Op_ResourceRoutines__nuke_kind
    cmp #$0D
    bcc ScummV5_Op_ResourceRoutines__lock_kind
    cmp #$11
    bcc ScummV5_Op_ResourceRoutines__unlock_kind
    cmp #$12
    beq ScummV5_Op_ResourceRoutines__charset_load
    ; Operation $13 is the only remaining valid non-object operation.
    lda #$04
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_ClearLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__load_kind:
    .a8
    dec
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_SetLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__nuke_kind:
    .a8
    sec
    sbc #$05
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_ClearLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__lock_kind:
    .a8
    sec
    sbc #$09
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_SetLocked
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__unlock_kind:
    .a8
    sec
    sbc #$0D
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_ClearLocked
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__charset_load:
    .a8
    lda #$04
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_SetLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__object:
    .a8
    lda.l SAME_SCUMM_C13_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ResourceRoutines__object_room_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__object_room_ok:
    .a8
    sta.l SAME_SCUMM_C13_RESOURCE
    lda #$03
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    lda.l SAME_SCUMM_C13_SELECTOR
    and #$40
    beq ScummV5_Op_ResourceRoutines__object_direct
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ResourceRoutines__operand_error
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_Op_ResourceRoutines__operand_error
    bra ScummV5_Op_ResourceRoutines__object_id_ok
ScummV5_Op_ResourceRoutines__object_direct:
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ResourceRoutines__operand_error
ScummV5_Op_ResourceRoutines__object_id_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C13_LAST_OBJECT_ID
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_RESOURCE
    sta.l SAME_SCUMM_C13_LAST_OBJECT_ROOM
    jsr ScummV5_C13_SetLoaded
ScummV5_Op_ResourceRoutines__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__invalid:
    .a8
    lda #SCUMM_ERR_RESOURCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

; Normalize high-bit room IDs through the C12 pseudo-room table before they
; become cache or lock keys. Other resource kinds pass through unchanged.
ScummV5_C13_MapRoomKind:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_KIND
    cmp #$03
    bne ScummV5_C13_MapRoomKind__done
    lda.l SAME_SCUMM_C13_RESOURCE
    bpl ScummV5_C13_MapRoomKind__done
    lda.l SAME_SCUMM_C12_INITIALIZED
    bne ScummV5_C13_MapRoomKind__mapper_ready
    jsr ScummV5_C12_ResetState
ScummV5_C13_MapRoomKind__mapper_ready:
    rep #$10
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_RESOURCE
    and #$7F
    tax
    lda.l SAME_SCUMM_C12_MAPPER,x
    sta.l SAME_SCUMM_C13_RESOURCE
ScummV5_C13_MapRoomKind__done:
    rts

; Return X=kind*32+resource/8 and retain the corresponding bit mask.
ScummV5_C13_BitAddress:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C13_KIND
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C13_RESOURCE
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    lsr
    lsr
    lsr
    clc
    adc.l SAME_SCUMM_LHS
    tax
    sep #$20
    .a8
    rts

ScummV5_C13_SetLoaded:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_C13_LOADED,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C13_LOADED,x
    rts

ScummV5_C13_ClearLoaded:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C13_LOADED,x
    sta.l SAME_SCUMM_C13_LOADED,x
    rts

ScummV5_C13_SetLocked:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_C13_LOCKED,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C13_LOCKED,x
    rts

ScummV5_C13_ClearLocked:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C13_LOCKED,x
    sta.l SAME_SCUMM_C13_LOCKED,x
    rts

ScummV5_Op_ActorFollowCamera:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_ActorFollowCamera__variable
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorFollowCamera__operand_error
    rep #$20
    .a16
    and #$00FF
    bra ScummV5_Op_ActorFollowCamera__fetched
ScummV5_Op_ActorFollowCamera__variable:
    .a8
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ActorFollowCamera__operand_error
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_ActorFollowCamera__fetched
ScummV5_Op_ActorFollowCamera__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ActorFollowCamera__fetched:
    rep #$20
    .a16
    cmp #$0020
    bcc ScummV5_Op_ActorFollowCamera__valid
    sep #$20
    .a8
    lda #SCUMM_ERR_CAMERA_FOLLOW
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_ActorFollowCamera__valid:
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C15_CAMERA_FOLLOWS
    lda #$01
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    lda #$00
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    jmp ScummV5_Engine_Frame__next

; Canonical v5 $5D/$DD setClass. Object ids remain full u16 values and each
; selector is a direct/variable word whose low seven bits name class 1..32.
; Bit 7 sets the class, its absence removes it, and raw zero clears all.
ScummV5_Op_SetClass:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_INITIALIZED
    bne ScummV5_Op_SetClass__state_ready
    jsr ScummV5_C16_ResetState
ScummV5_Op_SetClass__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_SetClass__object_variable
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__object_direct_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_direct_ok:
    bra ScummV5_Op_SetClass__object_ready
ScummV5_Op_SetClass__object_variable:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__object_reference_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_reference_ok:
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SetClass__object_ready
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_ready:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_OBJECT
ScummV5_Op_SetClass__selector_loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetClass__selector_fetched
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__selector_fetched:
    .a8
    cmp #$FF
    bne ScummV5_Op_SetClass__selector_present
    jmp ScummV5_Op_SetClass__done
ScummV5_Op_SetClass__selector_present:
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__class_fetched
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__class_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_CLASS
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    bpl ScummV5_Op_SetClass__class_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SetClass__class_variable_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__class_variable_ok:
    sta.l SAME_SCUMM_C16_CLASS
ScummV5_Op_SetClass__class_ready:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    bne ScummV5_Op_SetClass__nonzero
    jmp ScummV5_Op_SetClass__clear_all
ScummV5_Op_SetClass__nonzero:
    .a16
    and #$007F
    bne ScummV5_Op_SetClass__class_nonzero
    jmp ScummV5_Op_SetClass__invalid
ScummV5_Op_SetClass__class_nonzero:
    .a16
    cmp #$0021
    bcc ScummV5_Op_SetClass__class_valid
    jmp ScummV5_Op_SetClass__invalid
ScummV5_Op_SetClass__class_valid:
    jsr ScummV5_C16_FindRecord
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_CLASS
    bmi ScummV5_Op_SetClass__set
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__clear_present
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_present:
    jsr ScummV5_C16_ClassAddress
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_MASK_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_BIT_MASK
    eor #$FF
    and.l SAME_SCUMM_C16_RECORDS,x
    sta.l SAME_SCUMM_C16_RECORDS,x
    jsr ScummV5_C16_FreeIfEmpty
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__set:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__set_address
    lda.l SAME_SCUMM_C16_FREE_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SetClass__invalid
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT,x
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_PRESENT,x
ScummV5_Op_SetClass__set_address:
    jsr ScummV5_C16_ClassAddress
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_MASK_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS,x
    ora.l SAME_SCUMM_C16_BIT_MASK
    sta.l SAME_SCUMM_C16_RECORDS,x
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_all:
    jsr ScummV5_C16_FindRecord
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__clear_all_present
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_all_present:
    jsr ScummV5_C16_ClearRecord
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SetClass__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_SetClass__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_SET_CLASS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

; Locate the object record and first reusable slot in one bounded scan.
ScummV5_C16_FindRecord:
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    sta.l SAME_SCUMM_C16_FREE_OFFSET
    ldx #$0000
ScummV5_C16_FindRecord__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_PRESENT,x
    bne ScummV5_C16_FindRecord__occupied
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_C16_FindRecord__next
    txa
    sta.l SAME_SCUMM_C16_FREE_OFFSET
    bra ScummV5_C16_FindRecord__next
ScummV5_C16_FindRecord__occupied:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT,x
    cmp.l SAME_SCUMM_C16_OBJECT
    bne ScummV5_C16_FindRecord__next
    txa
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    rts
ScummV5_C16_FindRecord__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C16_RECORD_STRIDE
    tax
    cpx #$1000
    bcc ScummV5_C16_FindRecord__loop
    rts

; Convert class 1..32 to the byte and bit within the selected record mask.
ScummV5_C16_ClassAddress:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_CLASS
    and #$007F
    dec
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_C16_BIT_MASK
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    clc
    adc #SAME_SCUMM_C16_R_MASK
    adc.l SAME_SCUMM_C16_RECORD_OFFSET
    sta.l SAME_SCUMM_C16_MASK_OFFSET
    rts

ScummV5_C16_ClearRecord:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda #$0000
    sta.l SAME_SCUMM_C16_RECORDS,x
    sta.l SAME_SCUMM_C16_RECORDS+2,x
    sta.l SAME_SCUMM_C16_RECORDS+4,x
    sta.l SAME_SCUMM_C16_RECORDS+6,x
    rts

ScummV5_C16_FreeIfEmpty:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C16_RECORDS+4,x
    ora.l SAME_SCUMM_C16_RECORDS+6,x
    bne ScummV5_C16_FreeIfEmpty__done
    jsr ScummV5_C16_ClearRecord
ScummV5_C16_FreeIfEmpty__done:
    rts

; Canonical v5 $7A/$FA verbOps. Configuration remains engine-owned; the
; video/input adapters decide when and how to draw or hit-test the resulting
; verb records.
ScummV5_Op_VerbOps:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_INITIALIZED
    bne ScummV5_Op_VerbOps__state_ready
    jsr ScummV5_C17_ResetState
ScummV5_Op_VerbOps__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C17_SUBOP
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__verb_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__verb_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_VERB
    jsr ScummV5_C17_RecordOffset
ScummV5_Op_VerbOps__loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_VerbOps__selector_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__selector_ok:
    .a8
    cmp #$FF
    bne ScummV5_Op_VerbOps__selector_present
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_VerbOps__selector_present:
    .a8
    sta.l SAME_SCUMM_C17_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_Op_VerbOps__check_name
    jmp ScummV5_Op_VerbOps__image
ScummV5_Op_VerbOps__check_name:
    .a8
    cmp #$02
    bne ScummV5_Op_VerbOps__check_color
    jmp ScummV5_Op_VerbOps__name
ScummV5_Op_VerbOps__check_color:
    .a8
    cmp #$03
    bne ScummV5_Op_VerbOps__check_hicolor
    jmp ScummV5_Op_VerbOps__color
ScummV5_Op_VerbOps__check_hicolor:
    .a8
    cmp #$04
    bne ScummV5_Op_VerbOps__check_at
    jmp ScummV5_Op_VerbOps__hicolor
ScummV5_Op_VerbOps__check_at:
    .a8
    cmp #$05
    bne ScummV5_Op_VerbOps__check_on
    jmp ScummV5_Op_VerbOps__at
ScummV5_Op_VerbOps__check_on:
    .a8
    cmp #$06
    bne ScummV5_Op_VerbOps__check_off
    jmp ScummV5_Op_VerbOps__on
ScummV5_Op_VerbOps__check_off:
    .a8
    cmp #$07
    bne ScummV5_Op_VerbOps__check_delete
    jmp ScummV5_Op_VerbOps__off
ScummV5_Op_VerbOps__check_delete:
    .a8
    cmp #$08
    bne ScummV5_Op_VerbOps__check_new
    jmp ScummV5_Op_VerbOps__delete
ScummV5_Op_VerbOps__check_new:
    .a8
    cmp #$09
    bne ScummV5_Op_VerbOps__check_dimcolor
    jmp ScummV5_Op_VerbOps__new
ScummV5_Op_VerbOps__check_dimcolor:
    .a8
    cmp #$10
    bne ScummV5_Op_VerbOps__check_dim
    jmp ScummV5_Op_VerbOps__dimcolor
ScummV5_Op_VerbOps__check_dim:
    .a8
    cmp #$11
    bne ScummV5_Op_VerbOps__check_key
    jmp ScummV5_Op_VerbOps__dim
ScummV5_Op_VerbOps__check_key:
    .a8
    cmp #$12
    bne ScummV5_Op_VerbOps__check_center
    jmp ScummV5_Op_VerbOps__key
ScummV5_Op_VerbOps__check_center:
    .a8
    cmp #$13
    bne ScummV5_Op_VerbOps__check_name_string
    jmp ScummV5_Op_VerbOps__center
ScummV5_Op_VerbOps__check_name_string:
    .a8
    cmp #$14
    bne ScummV5_Op_VerbOps__check_object
    jmp ScummV5_Op_VerbOps__name_string
ScummV5_Op_VerbOps__check_object:
    .a8
    cmp #$16
    bne ScummV5_Op_VerbOps__check_background
    jmp ScummV5_Op_VerbOps__object
ScummV5_Op_VerbOps__check_background:
    .a8
    cmp #$17
    beq ScummV5_Op_VerbOps__background_selected
    jmp ScummV5_Op_VerbOps__invalid
ScummV5_Op_VerbOps__background_selected:
    jmp ScummV5_Op_VerbOps__background

ScummV5_Op_VerbOps__image:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__image_operand_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__image_operand_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Op_VerbOps__image_done
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda.l SAME_SCUMM_C17_CURRENT_ROOM
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_ROOM,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_OBJECT,x
ScummV5_Op_VerbOps__image_done:
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__name:
    jsr ScummV5_C17_CopyInlineName
    bcc ScummV5_Op_VerbOps__name_done
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_done:
    jsr ScummV5_C17_MarkText
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__color:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__color_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__color_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_COLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__hicolor:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__hicolor_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__hicolor_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_HICOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__at:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__at_left_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__at_left_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__at_top_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__at_top_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_LEFT,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_ORIG_LEFT,x
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TOP,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__on:
    .a8
    lda #$01
    bra ScummV5_Op_VerbOps__store_mode
ScummV5_Op_VerbOps__off:
    .a8
    lda #$00
    bra ScummV5_Op_VerbOps__store_mode
ScummV5_Op_VerbOps__dim:
    .a8
    lda #$02
ScummV5_Op_VerbOps__store_mode:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__delete:
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__new:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    bne ScummV5_Op_VerbOps__new_defaults
    jsr ScummV5_C17_ClearRecord
    jsr ScummV5_C17_RecordX
ScummV5_Op_VerbOps__new_defaults:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    lda #$02
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_COLOR,x
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_HICOLOR,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_KEY,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CENTER,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda #$08
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_DIMCOLOR,x
    lda.l SAME_SCUMM_C7_CHARSET_ID
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CHARSET,x
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__dimcolor:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__dimcolor_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__dimcolor_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_DIMCOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__key:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__key_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__key_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_KEY,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__center:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CENTER,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__name_string:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__name_string_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_string_ok:
    jsr ScummV5_C17_CopyStringName
    bcc ScummV5_Op_VerbOps__name_string_done
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_string_done:
    jsr ScummV5_C17_MarkText
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__object:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__object_id_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__object_id_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__object_room_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__object_room_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Op_VerbOps__object_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    cmp.l SAME_SCUMM_C17_PARAM0
    beq ScummV5_Op_VerbOps__object_done
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_OBJECT,x
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_ROOM,x
ScummV5_Op_VerbOps__object_done:
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__background:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__background_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__background_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_BKCOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_VERB_OPS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_VerbOps__operand_error:
    jmp ScummV5_Op__error

ScummV5_C17_FetchByteParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C17_SUBOP
    beq ScummV5_C17_FetchByteParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C17_FetchByteParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C17_FetchByteParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C17_FetchByteParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C17_FetchByteParam__done:
    rts

ScummV5_C17_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C17_SUBOP
    beq ScummV5_C17_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C17_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C17_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C17_FetchWordParam__done:
    rts

ScummV5_C17_RecordOffset:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C17_PARAM0
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_LHS
    asl
    clc
    adc.l SAME_SCUMM_LHS
    sta.l SAME_SCUMM_C17_RECORD_OFFSET
    rts

ScummV5_C17_RecordX:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    rts

ScummV5_C17_ClearRecord:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    clc
    adc #SAME_SCUMM_C17_VERB_STRIDE
    sta.l SAME_SCUMM_C17_PARAM1
ScummV5_C17_ClearRecord__loop:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS,x
    inx
    inx
    txa
    cmp.l SAME_SCUMM_C17_PARAM1
    bcc ScummV5_C17_ClearRecord__loop
    rts

ScummV5_C17_MarkText:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    rts

ScummV5_C17_CopyInlineName:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
ScummV5_C17_CopyInlineName__loop:
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    cmp #SAME_SCUMM_C17_NAME_MAX
    bcc ScummV5_C17_CopyInlineName__room
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyInlineName__room:
    jsr ScummV5_FetchByte
    bcc ScummV5_C17_CopyInlineName__fetched
    rts
ScummV5_C17_CopyInlineName__fetched:
    .a8
    jsr ScummV5_C17_StoreNameByte
    lda.l SAME_SCUMM_C17_CONTROL_ARGS
    beq ScummV5_C17_CopyInlineName__ordinary
    cmp #$FF
    beq ScummV5_C17_CopyInlineName__control_code
    bra ScummV5_C17_CopyInlineName__argument
ScummV5_C17_CopyInlineName__ordinary:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C17_CopyInlineName__done
    cmp #$FF
    bne ScummV5_C17_CopyInlineName__loop
    lda #$FF
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__argument:
    dec
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__control_code:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$02
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$03
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$08
    beq ScummV5_C17_CopyInlineName__no_arguments
    lda #$02
    bra ScummV5_C17_CopyInlineName__set_arguments
ScummV5_C17_CopyInlineName__no_arguments:
    .a8
    lda #$00
ScummV5_C17_CopyInlineName__set_arguments:
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__done:
    jsr ScummV5_C17_SetNameLength
    clc
    rts

; A contains a canonical string resource id. Missing/out-of-u8 resources nuke
; the verb name; present resources are copied through their encoded terminator.
ScummV5_C17_CopyStringName:
    rep #$30
    .a16
    .i16
    cmp #$0100
    bcc ScummV5_C17_CopyStringName__id_ok
    jmp ScummV5_C17_CopyStringName__absent
ScummV5_C17_CopyStringName__id_ok:
    .a16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_C17_CopyStringName__present
    jmp ScummV5_C17_CopyStringName__absent8
ScummV5_C17_CopyStringName__present:
    sta.l SAME_SCUMM_C17_PARAM1
    txa
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
ScummV5_C17_CopyStringName__loop:
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    cmp.l SAME_SCUMM_C17_PARAM1
    bcc ScummV5_C17_CopyStringName__within_resource
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyStringName__within_resource:
    .a8
    cmp #SAME_SCUMM_C17_NAME_MAX
    bcc ScummV5_C17_CopyStringName__within_name
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyStringName__within_name:
    rep #$30
    .a16
    .i16
    and #$00FF
    clc
    adc.l SAME_SCUMM_C17_PARAM0
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    jsr ScummV5_C17_StoreNameByte
    lda.l SAME_SCUMM_C17_CONTROL_ARGS
    beq ScummV5_C17_CopyStringName__ordinary
    cmp #$FF
    beq ScummV5_C17_CopyStringName__control_code
    bra ScummV5_C17_CopyStringName__argument
ScummV5_C17_CopyStringName__ordinary:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C17_CopyStringName__done
    cmp #$FF
    bne ScummV5_C17_CopyStringName__loop
    lda #$FF
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__argument:
    dec
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__control_code:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$02
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$03
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$08
    beq ScummV5_C17_CopyStringName__no_arguments
    lda #$02
    bra ScummV5_C17_CopyStringName__set_arguments
ScummV5_C17_CopyStringName__no_arguments:
    .a8
    lda #$00
ScummV5_C17_CopyStringName__set_arguments:
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__done:
    jsr ScummV5_C17_SetNameLength
    clc
    rts
ScummV5_C17_CopyStringName__absent8:
    rep #$20
    .a16
ScummV5_C17_CopyStringName__absent:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    clc
    rts

; Store A into the current record name and advance the bounded byte cursor.
ScummV5_C17_StoreNameByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_NAME_INDEX
    and #$00FF
    clc
    adc #SAME_SCUMM_C17_V_NAME
    adc.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C17_VERBS,x
    lda.l SAME_SCUMM_C17_NAME_INDEX
    inc
    sta.l SAME_SCUMM_C17_NAME_INDEX
    rts

ScummV5_C17_SetNameLength:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    rts

ScummV5_C17_NameError:
    sep #$20
    .a8
    lda #SCUMM_ERR_VERB_OPS
    jsr ScummV5_SetError
    sec
    rts

; Canonical v5 $AC expression. The bytecode is reverse-Polish and uses a
; shared 256-entry signed 32-bit stack; only the final destination write
; narrows back to the v5 variable width.
ScummV5_Op_Expression:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Expression__destination_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__destination_ok:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_C18_DESTINATION
    lda #$0000
    sta.l SAME_SCUMM_C18_SP
ScummV5_Op_Expression__loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Expression__token_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__token_ok:
    .a8
    cmp #$FF
    bne ScummV5_Op_Expression__token_present
    jmp ScummV5_Op_Expression__finish
ScummV5_Op_Expression__token_present:
    .a8
    sta.l SAME_SCUMM_C18_TOKEN
    and #$1F
    cmp #$01
    bne ScummV5_Op_Expression__check_add
    jmp ScummV5_Op_Expression__push
ScummV5_Op_Expression__check_add:
    .a8
    cmp #$02
    bne ScummV5_Op_Expression__check_subtract
    jmp ScummV5_Op_Expression__add
ScummV5_Op_Expression__check_subtract:
    .a8
    cmp #$03
    bne ScummV5_Op_Expression__check_multiply
    jmp ScummV5_Op_Expression__subtract
ScummV5_Op_Expression__check_multiply:
    .a8
    cmp #$04
    bne ScummV5_Op_Expression__check_divide
    jmp ScummV5_Op_Expression__multiply
ScummV5_Op_Expression__check_divide:
    .a8
    cmp #$05
    bne ScummV5_Op_Expression__check_normal
    jmp ScummV5_Op_Expression__divide
ScummV5_Op_Expression__check_normal:
    .a8
    cmp #$06
    bne ScummV5_Op_Expression__reserved
    jmp ScummV5_Op_Expression__normal
ScummV5_Op_Expression__reserved:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__push:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_TOKEN
    sta.l SAME_SCUMM_LAST_OPCODE
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Expression__push_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__push_ok:
    jsr ScummV5_C18_PushWord
    bcc ScummV5_Op_Expression__push_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__push_done:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__add:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__add_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__add_ready:
    rep #$20
    .a16
    clc
    lda.l SAME_SCUMM_C18_LHS_LO
    adc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    adc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__subtract:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__subtract_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__subtract_ready:
    rep #$20
    .a16
    sec
    lda.l SAME_SCUMM_C18_LHS_LO
    sbc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    sbc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__multiply:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__multiply_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__multiply_ready:
    jsr ScummV5_C18_Multiply
    bra ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__divide:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__divide_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__divide_ready:
    jsr ScummV5_C18_Divide
    bcc ScummV5_Op_Expression__push_result
    jmp ScummV5_Op__error

ScummV5_Op_Expression__push_result:
    jsr ScummV5_C18_PushResult
    bcc ScummV5_Op_Expression__result_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__result_done:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__normal:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Expression__normal_fetched
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_fetched:
    .a8
    sta.l SAME_SCUMM_LAST_OPCODE
    lda.l SAME_SCUMM_C18_NESTED
    cmp #$FF
    bne ScummV5_Op_Expression__normal_depth_ok
    jmp ScummV5_C18_Error
ScummV5_Op_Expression__normal_depth_ok:
    .a8
    inc
    sta.l SAME_SCUMM_C18_NESTED
    jsr ScummV5_DispatchCurrentOpcode
    bcc ScummV5_Op_Expression__normal_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_done:
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_Expression__normal_value
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_value:
    jsr ScummV5_C18_PushWord
    bcc ScummV5_Op_Expression__normal_pushed
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_pushed:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__finish:
    jsr ScummV5_C18_PopResult
    bcc ScummV5_Op_Expression__finish_value
    jmp ScummV5_Op__error
ScummV5_Op_Expression__finish_value:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_DESTINATION
    sta.l SAME_SCUMM_RESULT_OFFSET
    lda.l SAME_SCUMM_C18_RESULT_LO
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

; Push signed A16 as a 32-bit expression value.
ScummV5_C18_PushWord:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_C18_RESULT_LO
    bmi ScummV5_C18_PushWord__negative
    lda #$0000
    bra ScummV5_C18_PushWord__high
ScummV5_C18_PushWord__negative:
    .a16
    lda #$FFFF
ScummV5_C18_PushWord__high:
    .a16
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_C18_PushResult

ScummV5_C18_PushResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C18_SP
    cmp #SAME_SCUMM_C18_STACK_SIZE
    bcc ScummV5_C18_PushResult__room
    jmp ScummV5_C18_Error
ScummV5_C18_PushResult__room:
    .a16
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_STACK,x
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_STACK+2,x
    txa
    clc
    adc #$0004
    sta.l SAME_SCUMM_C18_SP
    clc
    rts

ScummV5_C18_PopResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C18_SP
    cmp #$0004
    bcs ScummV5_C18_PopResult__present
    jmp ScummV5_C18_Error
ScummV5_C18_PopResult__present:
    .a16
    sec
    sbc #$0004
    sta.l SAME_SCUMM_C18_SP
    tax
    lda.l SAME_SCUMM_C18_STACK,x
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_STACK+2,x
    sta.l SAME_SCUMM_C18_RESULT_HI
    clc
    rts

ScummV5_C18_PopOperands:
    jsr ScummV5_C18_PopResult
    bcs ScummV5_C18_PopOperands__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_RHS_HI
    jsr ScummV5_C18_PopResult
    bcs ScummV5_C18_PopOperands__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_LHS_HI
    clc
ScummV5_C18_PopOperands__done:
    rts

; Lower 32 bits of the canonical signed-int product (two's-complement shift/add).
ScummV5_C18_Multiply:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_RESULT_HI
    sep #$20
    .a8
    lda #$20
    sta.l SAME_SCUMM_C18_LOOP
ScummV5_C18_Multiply__loop:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    and #$0001
    beq ScummV5_C18_Multiply__shift
    clc
    lda.l SAME_SCUMM_C18_RESULT_LO
    adc.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    adc.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
ScummV5_C18_Multiply__shift:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_HI
    lsr
    sta.l SAME_SCUMM_C18_RHS_HI
    lda.l SAME_SCUMM_C18_RHS_LO
    ror
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_LHS_LO
    asl
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    rol
    sta.l SAME_SCUMM_C18_LHS_HI
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_LOOP
    dec
    sta.l SAME_SCUMM_C18_LOOP
    bne ScummV5_C18_Multiply__loop
    rts

; Signed 32-bit quotient, truncating toward zero.
ScummV5_C18_Divide:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    ora.l SAME_SCUMM_C18_RHS_HI
    bne ScummV5_C18_Divide__nonzero
    sep #$20
    .a8
    lda #SCUMM_ERR_DIVIDE_ZERO
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C18_Divide__nonzero:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C18_SIGN
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_HI
    bpl ScummV5_C18_Divide__lhs_positive
    jsr ScummV5_C18_NegateLhs
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C18_SIGN
ScummV5_C18_Divide__lhs_positive:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_HI
    bpl ScummV5_C18_Divide__rhs_positive
    jsr ScummV5_C18_NegateRhs
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_SIGN
    eor #$01
    sta.l SAME_SCUMM_C18_SIGN
ScummV5_C18_Divide__rhs_positive:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    sep #$20
    .a8
    lda #$20
    sta.l SAME_SCUMM_C18_LOOP
ScummV5_C18_Divide__loop:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    asl
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    rol
    sta.l SAME_SCUMM_C18_LHS_HI
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    rol
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    rol
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    cmp.l SAME_SCUMM_C18_RHS_HI
    bcc ScummV5_C18_Divide__next
    bne ScummV5_C18_Divide__subtract
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    cmp.l SAME_SCUMM_C18_RHS_LO
    bcc ScummV5_C18_Divide__next
ScummV5_C18_Divide__subtract:
    .a16
    sec
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    sbc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    sbc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    lda.l SAME_SCUMM_C18_LHS_LO
    inc
    sta.l SAME_SCUMM_C18_LHS_LO
ScummV5_C18_Divide__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_LOOP
    dec
    sta.l SAME_SCUMM_C18_LOOP
    bne ScummV5_C18_Divide__loop
    lda.l SAME_SCUMM_C18_SIGN
    beq ScummV5_C18_Divide__positive
    jsr ScummV5_C18_NegateLhs
ScummV5_C18_Divide__positive:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    clc
    rts

ScummV5_C18_NegateLhs:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    eor #$FFFF
    clc
    adc #$0001
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    eor #$FFFF
    adc #$0000
    sta.l SAME_SCUMM_C18_LHS_HI
    rts

ScummV5_C18_NegateRhs:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    eor #$FFFF
    clc
    adc #$0001
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_RHS_HI
    eor #$FFFF
    adc #$0000
    sta.l SAME_SCUMM_C18_RHS_HI
    rts

ScummV5_C18_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_EXPRESSION
    jsr ScummV5_SetError
    sec
    rts

ScummV5_C19_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C19_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C19_STACK_POINTER,x
    inx
    inx
    cpx #SAME_SCUMM_C19_STATE_SIZE
    bcc ScummV5_C19_ResetState__loop
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C19_SCRIPT_INDEX
    rts

ScummV5_Op_CutsceneDispatch:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$40
    beq ScummV5_Op_Cutscene
    cmp #$C0
    bne ScummV5_Op_CutsceneDispatch__override
    jmp ScummV5_Op_EndCutscene
ScummV5_Op_CutsceneDispatch__override:
    jmp ScummV5_Op_BeginOverride

ScummV5_Op_Cutscene:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C19_ARGUMENT0
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_ARG_COUNT
ScummV5_Op_Cutscene__next_argument:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Cutscene__selector_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_Cutscene__arguments_done
    sta.l SAME_SCUMM_C19_SELECTOR
    lda.l SAME_SCUMM_C4_ARG_COUNT
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_Cutscene__argument_room
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__argument_room:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_Cutscene__word_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__word_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$80
    beq ScummV5_Op_Cutscene__value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_Cutscene__variable_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__variable_ok:
    .a16
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_Cutscene__value_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    bne ScummV5_Op_Cutscene__argument_counted
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C19_ARGUMENT0
ScummV5_Op_Cutscene__argument_counted:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    inc
    sta.l SAME_SCUMM_C4_ARG_COUNT
    bra ScummV5_Op_Cutscene__next_argument
ScummV5_Op_Cutscene__arguments_done:
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    cmp #$04
    bcc ScummV5_Op_Cutscene__stack_room
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__stack_room:
    inc
    sta.l SAME_SCUMM_C19_STACK_POINTER
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C19_ARGUMENT0
    sta.l SAME_SCUMM_C19_DATA,x
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    cmp #$FF
    bne ScummV5_Op_Cutscene__depth_room
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__depth_room:
    inc
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_EndCutscene:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    bne ScummV5_Op_EndCutscene__active
    jmp ScummV5_C19_Error
ScummV5_Op_EndCutscene__active:
    sta.l SAME_SCUMM_C19_SELECTOR
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_EndCutscene__first_depth_done
    dec
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
ScummV5_Op_EndCutscene__first_depth_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C19_OVERRIDE_PC,x
    beq ScummV5_Op_EndCutscene__override_done
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_EndCutscene__second_depth_done
    dec
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
ScummV5_Op_EndCutscene__second_depth_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$00FF
    asl
    tax
ScummV5_Op_EndCutscene__override_done:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_VARIABLES+(5 * 2)
    lda.l SAME_SCUMM_C19_SELECTOR
    tax
    lda #$00
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
    lda.l SAME_SCUMM_C19_STACK_POINTER
    dec
    sta.l SAME_SCUMM_C19_STACK_POINTER
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_BeginOverride:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_BeginOverride__flag_ok
    jmp ScummV5_C19_Error
ScummV5_Op_BeginOverride__flag_ok:
    .a8
    sta.l SAME_SCUMM_C19_SELECTOR
ScummV5_Op_BeginOverride__active:
    .a8
    lda.l SAME_SCUMM_C19_SELECTOR
    beq ScummV5_Op_BeginOverride__clear
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_STACK_POINTER
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    tax
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    bra ScummV5_Op_BeginOverride__variable
ScummV5_Op_BeginOverride__clear:
    .a8
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_STACK_POINTER
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    tax
    lda #$00
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
ScummV5_Op_BeginOverride__variable:
    .a8
    lda #$00
    sta.l SAME_SCUMM_VARIABLES+(5 * 2)
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_BeginOverride__error:
    jmp ScummV5_C19_Error

ScummV5_C19_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_CUTSCENE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C20_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C20_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C20_COUNT,x
    inx
    inx
    cpx #SAME_SCUMM_C20_STATE_SIZE
    bcc ScummV5_C20_ResetState__loop
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C20_INITIALIZED
    rts

ScummV5_Op_DoSentence:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_INITIALIZED
    bne ScummV5_Op_DoSentence__ready
    jsr ScummV5_C20_ResetState
ScummV5_Op_DoSentence__ready:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_DoSentence__verb_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__verb_ok:
    .a8
    sta.l SAME_SCUMM_C20_VERB
    cmp #$FE
    bne ScummV5_Op_DoSentence__objects
    lda #$00
    sta.l SAME_SCUMM_C20_COUNT
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_DoSentence__objects:
    .a8
    lda #$40
    jsr ScummV5_C20_FetchWordParam
    bcc ScummV5_Op_DoSentence__object_a_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__object_a_ok:
    .a16
    sta.l SAME_SCUMM_C20_OBJECT_A
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C20_FetchWordParam
    bcc ScummV5_Op_DoSentence__object_b_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__object_b_ok:
    .a16
    sta.l SAME_SCUMM_C20_OBJECT_B
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    cmp #SAME_SCUMM_C20_RECORD_COUNT
    bcc ScummV5_Op_DoSentence__room
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__room:
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_VERB
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    lda #$00
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C20_OBJECT_A
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_A,x
    lda.l SAME_SCUMM_C20_OBJECT_B
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_B,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    inc
    sta.l SAME_SCUMM_C20_COUNT
    jmp ScummV5_Engine_Frame__next

ScummV5_C20_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_LAST_OPCODE
    beq ScummV5_C20_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C20_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C20_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C20_FetchWordParam__done:
    rts

ScummV5_C20_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SENTENCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C21_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C21_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C21_INITIALIZED,x
    inx
    inx
    cpx #SAME_SCUMM_C21_STATE_SIZE
    bcc ScummV5_C21_ResetState__clear
    ; Object 100: movable target.
    lda #$0064
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID
    lda #$0008
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT
    lda #$0014
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X
    lda #$001E
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y
    ; Objects 101 and 102 overlap exactly before object 101 is drawn.
    lda #$0065
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_ID
    lda #$0028
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_X
    lda #$0030
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_HEIGHT
    lda #$0032
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WALK_X
    lda #$003C
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WALK_Y
    lda #$0066
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_ID
    lda #$0028
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_X
    lda #$0030
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_HEIGHT
    lda #$0046
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WALK_X
    lda #$0050
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WALK_Y
    sep #$20
    .a8
    lda #$07
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_STATE
    lda #$03
    sta.l SAME_SCUMM_C21_RECORD_COUNT
    lda #$01
    sta.l SAME_SCUMM_C21_INITIALIZED
    rts

ScummV5_Op_DrawObject:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_INITIALIZED
    bne ScummV5_Op_DrawObject__ready
    jsr ScummV5_C21_ResetState
ScummV5_Op_DrawObject__ready:
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_DrawObject__object_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__object_ok:
    .a16
    sta.l SAME_SCUMM_C21_OBJECT
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_DrawObject__selector_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__selector_ok:
    .a8
    sta.l SAME_SCUMM_C21_SELECTOR
    lda #$00
    sta.l SAME_SCUMM_C21_POSITIONED
    lda #$01
    sta.l SAME_SCUMM_C21_STATE
    lda.l SAME_SCUMM_C21_SELECTOR
    and #$1F
    cmp #$01
    beq ScummV5_Op_DrawObject__at
    cmp #$02
    beq ScummV5_Op_DrawObject__state
    cmp #$1F
    beq ScummV5_Op_DrawObject__lookup
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__at:
    .a8
    lda #$80
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__x_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__x_ok:
    .a16
    sta.l SAME_SCUMM_C21_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__y_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__y_ok:
    .a16
    sta.l SAME_SCUMM_C21_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C21_POSITIONED
    bra ScummV5_Op_DrawObject__lookup
ScummV5_Op_DrawObject__state:
    .a8
    lda #$80
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__state_value
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__state_value:
    rep #$20
    .a16
    cmp #$0100
    bcc ScummV5_Op_DrawObject__state_range
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__state_range:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C21_STATE
ScummV5_Op_DrawObject__lookup:
    rep #$30
    .a16
    .i16
    ldx #$0000
ScummV5_Op_DrawObject__lookup_loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID,x
    cmp.l SAME_SCUMM_C21_OBJECT
    beq ScummV5_Op_DrawObject__found
    txa
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    tax
    cpx #(SAME_SCUMM_C21_MAX_RECORDS * SAME_SCUMM_C21_RECORD_STRIDE)
    bcc ScummV5_Op_DrawObject__lookup_loop
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_DrawObject__found:
    txa
    sta.l SAME_SCUMM_C21_TARGET_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_POSITIONED
    beq ScummV5_Op_DrawObject__queue
    rep #$20
    .a16
    lda.l SAME_SCUMM_C21_X
    asl
    asl
    asl
    sta.l SAME_SCUMM_C21_X
    sec
    sbc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X,x
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X,x
    lda.l SAME_SCUMM_C21_X
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    lda.l SAME_SCUMM_C21_Y
    asl
    asl
    asl
    sta.l SAME_SCUMM_C21_Y
    sec
    sbc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y,x
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y,x
    lda.l SAME_SCUMM_C21_Y
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
ScummV5_Op_DrawObject__queue:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_QUEUE_COUNT
    cmp #SAME_SCUMM_C21_MAX_QUEUE
    bcc ScummV5_Op_DrawObject__queue_space
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__queue_space:
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C21_OBJECT
    sta.l SAME_SCUMM_C21_QUEUE,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_QUEUE_COUNT
    inc
    sta.l SAME_SCUMM_C21_QUEUE_COUNT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C21_TARGET_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    sta.l SAME_SCUMM_C21_RECT_X
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    sta.l SAME_SCUMM_C21_RECT_Y
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH,x
    sta.l SAME_SCUMM_C21_RECT_WIDTH
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT,x
    sta.l SAME_SCUMM_C21_RECT_HEIGHT
    ldx #$0000
ScummV5_Op_DrawObject__overlap_loop:
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    cmp.l SAME_SCUMM_C21_RECT_X
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    cmp.l SAME_SCUMM_C21_RECT_Y
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH,x
    cmp.l SAME_SCUMM_C21_RECT_WIDTH
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT,x
    cmp.l SAME_SCUMM_C21_RECT_HEIGHT
    bne ScummV5_Op_DrawObject__overlap_next
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_STATE,x
    rep #$30
    .a16
    .i16
ScummV5_Op_DrawObject__overlap_next:
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    tax
    cpx #(SAME_SCUMM_C21_MAX_RECORDS * SAME_SCUMM_C21_RECORD_STRIDE)
    bcc ScummV5_Op_DrawObject__overlap_loop
    lda.l SAME_SCUMM_C21_TARGET_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_STATE
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_STATE,x
    jmp ScummV5_Engine_Frame__next

ScummV5_C21_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C21_SELECTOR
    beq ScummV5_C21_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C21_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C21_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C21_FetchWordParam__done:
    rts

ScummV5_C21_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_DRAW_OBJECT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C22_ResetState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C22_INITIALIZED
    sta.l SAME_SCUMM_C22_TRANSITION_COUNT
    sta.l SAME_SCUMM_C22_NULL_SCENE
    lda #$44
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda #$03
    sta.l SAME_SCUMM_C22_OBJECT_COUNT
    lda #$02
    sta.l SAME_SCUMM_C22_QUEUE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C22_INITIALIZED
    rts

ScummV5_Op_LoadRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C22_INITIALIZED
    bne ScummV5_Op_LoadRoom__ready
    jsr ScummV5_C22_ResetState
ScummV5_Op_LoadRoom__ready:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_LoadRoom__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_LoadRoom__operand_ok:
    .a8
    bpl ScummV5_Op_LoadRoom__resolved
    and #$7F
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C12_MAPPER,x
ScummV5_Op_LoadRoom__resolved:
    .a8
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda.l SAME_SCUMM_C22_TRANSITION_COUNT
    inc
    sta.l SAME_SCUMM_C22_TRANSITION_COUNT
    lda #$00
    sta.l SAME_SCUMM_C22_OBJECT_COUNT
    sta.l SAME_SCUMM_C22_QUEUE_COUNT
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_Op_LoadRoom__null
    lda #$00
    sta.l SAME_SCUMM_C22_NULL_SCENE
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_LoadRoom__null:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C22_NULL_SCENE
    jmp ScummV5_Engine_Frame__next

ScummV5_C23_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C23_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C23_INITIALIZED,x
    inx
    inx
    cpx #SAME_SCUMM_C23_STATE_SIZE
    bcc ScummV5_C23_ResetState__clear
    ldx #$0000
ScummV5_C23_ResetState__slot:
    .a16
    .i16
    lda #$0002
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    lda #$0005
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    lda #$013F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    lda #$0000
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    rep #$20
    .a16
    txa
    clc
    adc #SAME_SCUMM_C23_SLOT_STRIDE
    tax
    cpx #(4 * SAME_SCUMM_C23_SLOT_STRIDE)
    bcc ScummV5_C23_ResetState__slot
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C23_INITIALIZED
    rts

ScummV5_Op_Print:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_INITIALIZED
    bne ScummV5_Op_Print__ready
    jsr ScummV5_C23_ResetState
ScummV5_Op_Print__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$D8
    bne ScummV5_Op_Print__fetch_actor
    lda #$01
    bra ScummV5_Op_Print__actor
ScummV5_Op_Print__fetch_actor:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_Print__actor
    jmp ScummV5_Op__error
ScummV5_Op_Print__actor:
    .a8
    sta.l SAME_SCUMM_C23_ACTOR
    ldx #$0000
    cmp #$FC
    bne ScummV5_Op_Print__slot2
    ldx #$0021
    lda #$03
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot2:
    .a8
    cmp #$FD
    bne ScummV5_Op_Print__slot1
    ldx #$0016
    lda #$02
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot1:
    .a8
    cmp #$FE
    bne ScummV5_Op_Print__slot0
    ldx #$000B
    lda #$01
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot0:
    .a8
    lda #$00
ScummV5_Op_Print__slot_ready:
    sta.l SAME_SCUMM_C23_LAST_SLOT
    rep #$20
    .a16
    txa
    sta.l SAME_SCUMM_C23_SLOT_OFFSET
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_HEIGHT
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_CHARSET
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_FLAGS,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
ScummV5_Op_Print__selector:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Print__selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__selector_ok:
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    cmp #$FF
    bne ScummV5_Op_Print__not_default
    jmp ScummV5_Op_Print__save_default
ScummV5_Op_Print__not_default:
    .a8
    and #$0F
    beq ScummV5_Op_Print__at
    cmp #$01
    beq ScummV5_Op_Print__color
    cmp #$02
    beq ScummV5_Op_Print__clipped
    cmp #$03
    bne ScummV5_Op_Print__not_erase
    jmp ScummV5_Op_Print__unsupported_pair
ScummV5_Op_Print__not_erase:
    .a8
    cmp #$04
    beq ScummV5_Op_Print__center
    cmp #$06
    bne ScummV5_Op_Print__not_left
    jmp ScummV5_Op_Print__left
ScummV5_Op_Print__not_left:
    .a8
    cmp #$07
    bne ScummV5_Op_Print__not_overhead
    jmp ScummV5_Op_Print__overhead
ScummV5_Op_Print__not_overhead:
    .a8
    cmp #$08
    bne ScummV5_Op_Print__not_voice
    jmp ScummV5_Op_Print__unsupported_pair
ScummV5_Op_Print__not_voice:
    .a8
    cmp #$0F
    bne ScummV5_Op_Print__unknown
    jmp ScummV5_Op_Print__text
ScummV5_Op_Print__unknown:
    .a8
    jmp ScummV5_C23_Error
ScummV5_Op_Print__at:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__at_x
    jmp ScummV5_Op__error
ScummV5_Op_Print__at_x:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__at_y
    jmp ScummV5_Op__error
ScummV5_Op_Print__at_y:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FD
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__color:
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_Print__color_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__color_ok:
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__clipped:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__clipped_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__clipped_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    sep #$20
    .a8
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__center:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FD
    ora #$01
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__left:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FC
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__overhead:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    ora #$02
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__unsupported_pair:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcs ScummV5_Op_Print__unsupported_error
    lda #$40
    jsr ScummV5_C23_FetchWordParam
ScummV5_Op_Print__unsupported_error:
    jmp ScummV5_C23_Error
ScummV5_Op_Print__save_default:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C23_SLOT_OFFSET
    tax
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_HEIGHT
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_CHARSET
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_FLAGS,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Print__text:
    .a8
    lda.l SAME_SCUMM_C23_ACTOR
    sta.l SAME_SCUMM_C23_LAST_ACTOR
    lda.l SAME_SCUMM_C23_MESSAGE_COUNT
    inc
    sta.l SAME_SCUMM_C23_MESSAGE_COUNT
    lda #$00
    sta.l SAME_SCUMM_C23_RAW_INDEX
ScummV5_Op_Print__text_loop:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_Print__text_error
    jsr ScummV5_C23_StoreTextByte
    bcc ScummV5_Op_Print__text_first_stored
    jmp ScummV5_C23_Error
ScummV5_Op_Print__text_first_stored:
    .a8
    cmp #$00
    beq ScummV5_Op_Print__text_done
    cmp #$FF
    bne ScummV5_Op_Print__text_loop
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_Print__text_error
    jsr ScummV5_C23_StoreTextByte
    bcs ScummV5_C23_Error
    cmp #$01
    beq ScummV5_Op_Print__text_loop
    cmp #$02
    beq ScummV5_Op_Print__text_loop
    cmp #$03
    beq ScummV5_Op_Print__text_loop
    cmp #$08
    beq ScummV5_Op_Print__text_loop
    ldy #$0002
ScummV5_Op_Print__text_args:
    .a8
    .i16
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_Print__text_error
    jsr ScummV5_C23_StoreTextByte
    bcs ScummV5_C23_Error
    dey
    bne ScummV5_Op_Print__text_args
    bra ScummV5_Op_Print__text_loop
ScummV5_Op_Print__text_done:
    .a8
    lda.l SAME_SCUMM_C23_RAW_INDEX
    sta.l SAME_SCUMM_C23_LAST_LENGTH
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Print__text_error:
    jmp ScummV5_Op__error

ScummV5_C23_FetchWordParam:
    sep #$20
    .a8
    and.l SAME_SCUMM_C23_SELECTOR
    beq ScummV5_C23_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C23_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C23_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C23_FetchWordParam__done:
    rts

ScummV5_C23_StoreTextByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    lda.l SAME_SCUMM_C23_RAW_INDEX
    cmp #$10
    bcc ScummV5_C23_StoreTextByte__space
    sec
    rts
ScummV5_C23_StoreTextByte__space:
    .a8
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_C23_LAST_RAW,x
    lda.l SAME_SCUMM_C23_RAW_INDEX
    inc
    sta.l SAME_SCUMM_C23_RAW_INDEX
    lda.l SAME_SCUMM_C23_SELECTOR
    clc
    rts

ScummV5_C23_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_ActorOps:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_ActorOps__ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_ActorOps__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ActorOps__actor_fetched
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_Op_ActorOps__actor_ok
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__actor_ok:
    sta.l SAME_SCUMM_C14_ACTOR
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_ActorOps__loop
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_ActorOps__loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_ActorOps__subop_fetched
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__subop_fetched:
    .a8
    cmp #$FF
    bne ScummV5_Op_ActorOps__subop_present
    jmp ScummV5_Op_ActorOps__done
ScummV5_Op_ActorOps__subop_present:
    .a8
    sta.l SAME_SCUMM_C14_SUBOP
    sta.l SAME_SCUMM_C7_SUBOP
    and #$1F
    cmp #$18
    bcc ScummV5_Op_ActorOps__subop_in_range
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__subop_in_range:
    .a8
    cmp #$0F
    bne ScummV5_Op_ActorOps__subop_valid
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__subop_valid:
    .a8
    ; Poppy's current location pass undercounts JMP (abs,x) by one byte even
    ; though the emitter writes the correct three-byte 65C816 instruction.
    ; Keep this explicit dispatch chain until that assembler defect is fixed;
    ; otherwise every following label (including the active-engine ABI) points
    ; one byte before its emitted code.
    cmp #$00
    bne ScummV5_Op_ActorOps__dispatch_01
    jmp ScummV5_Op_ActorOps__dummy
ScummV5_Op_ActorOps__dispatch_01:
    .a8
    cmp #$01
    bne ScummV5_Op_ActorOps__dispatch_02
    jmp ScummV5_Op_ActorOps__costume
ScummV5_Op_ActorOps__dispatch_02:
    .a8
    cmp #$02
    bne ScummV5_Op_ActorOps__dispatch_03
    jmp ScummV5_Op_ActorOps__speed
ScummV5_Op_ActorOps__dispatch_03:
    .a8
    cmp #$03
    bne ScummV5_Op_ActorOps__dispatch_04
    jmp ScummV5_Op_ActorOps__sound
ScummV5_Op_ActorOps__dispatch_04:
    .a8
    cmp #$04
    bne ScummV5_Op_ActorOps__dispatch_05
    jmp ScummV5_Op_ActorOps__walk
ScummV5_Op_ActorOps__dispatch_05:
    .a8
    cmp #$05
    bne ScummV5_Op_ActorOps__dispatch_06
    jmp ScummV5_Op_ActorOps__talk
ScummV5_Op_ActorOps__dispatch_06:
    .a8
    cmp #$06
    bne ScummV5_Op_ActorOps__dispatch_07
    jmp ScummV5_Op_ActorOps__stand
ScummV5_Op_ActorOps__dispatch_07:
    .a8
    cmp #$07
    bne ScummV5_Op_ActorOps__dispatch_08
    jmp ScummV5_Op_ActorOps__animation
ScummV5_Op_ActorOps__dispatch_08:
    .a8
    cmp #$08
    bne ScummV5_Op_ActorOps__dispatch_09
    jmp ScummV5_Op_ActorOps__default
ScummV5_Op_ActorOps__dispatch_09:
    .a8
    cmp #$09
    bne ScummV5_Op_ActorOps__dispatch_0a
    jmp ScummV5_Op_ActorOps__elevation
ScummV5_Op_ActorOps__dispatch_0a:
    .a8
    cmp #$0A
    bne ScummV5_Op_ActorOps__dispatch_0b
    jmp ScummV5_Op_ActorOps__anim_default
ScummV5_Op_ActorOps__dispatch_0b:
    .a8
    cmp #$0B
    bne ScummV5_Op_ActorOps__dispatch_0c
    jmp ScummV5_Op_ActorOps__palette
ScummV5_Op_ActorOps__dispatch_0c:
    .a8
    cmp #$0C
    bne ScummV5_Op_ActorOps__dispatch_0d
    jmp ScummV5_Op_ActorOps__talk_color
ScummV5_Op_ActorOps__dispatch_0d:
    .a8
    cmp #$0D
    bne ScummV5_Op_ActorOps__dispatch_0e
    jmp ScummV5_Op_ActorOps__name
ScummV5_Op_ActorOps__dispatch_0e:
    .a8
    cmp #$0E
    bne ScummV5_Op_ActorOps__dispatch_10
    jmp ScummV5_Op_ActorOps__init
ScummV5_Op_ActorOps__dispatch_10:
    .a8
    cmp #$10
    bne ScummV5_Op_ActorOps__dispatch_11
    jmp ScummV5_Op_ActorOps__width
ScummV5_Op_ActorOps__dispatch_11:
    .a8
    cmp #$11
    bne ScummV5_Op_ActorOps__dispatch_12
    jmp ScummV5_Op_ActorOps__scale
ScummV5_Op_ActorOps__dispatch_12:
    .a8
    cmp #$12
    bne ScummV5_Op_ActorOps__dispatch_13
    jmp ScummV5_Op_ActorOps__never_clip
ScummV5_Op_ActorOps__dispatch_13:
    .a8
    cmp #$13
    bne ScummV5_Op_ActorOps__dispatch_14
    jmp ScummV5_Op_ActorOps__always_clip
ScummV5_Op_ActorOps__dispatch_14:
    .a8
    cmp #$14
    bne ScummV5_Op_ActorOps__dispatch_15
    jmp ScummV5_Op_ActorOps__ignore_boxes
ScummV5_Op_ActorOps__dispatch_15:
    .a8
    cmp #$15
    bne ScummV5_Op_ActorOps__dispatch_16
    jmp ScummV5_Op_ActorOps__follow_boxes
ScummV5_Op_ActorOps__dispatch_16:
    .a8
    cmp #$16
    bne ScummV5_Op_ActorOps__dispatch_17
    jmp ScummV5_Op_ActorOps__anim_speed
ScummV5_Op_ActorOps__dispatch_17:
    jmp ScummV5_Op_ActorOps__shadow
ScummV5_Op_ActorOps__dispatch_invalid:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__error_top:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__done_top:
    jmp ScummV5_Op_ActorOps__done
ScummV5_Op_ActorOps__dummy:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    brl ScummV5_Op_ActorOps__param_done
ScummV5_Op_ActorOps__costume:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME,x
    brl ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__speed:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_X,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    brl ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__sound:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_SOUND
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__walk:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_WALK_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__stand:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_STAND_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__talk_color:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_TALK_COLOR
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__init:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_INIT_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__width:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_WIDTH
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__always_clip:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_FORCE_CLIP
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__anim_speed:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_ANIM_SPEED
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__shadow:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_SHADOW
ScummV5_Op_ActorOps__one_byte:
    phy
    jsr ScummV5_C14_FetchByte
    ply
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
    tya
    clc
    adc.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_mid:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__talk:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__animation:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    lda #$20
    jsr ScummV5_C14_FetchByte
ScummV5_Op_ActorOps__param_done:
    bcs ScummV5_Op_ActorOps__error_mid
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__default:
    jsr ScummV5_C14_DefaultActor
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__elevation:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchWord
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_C14_BaseX
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sep #$20
    .a8
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__anim_default:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_INIT_FRAME,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x
    lda #$03
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
    lda #$04
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda #$05
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_palette:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__invalid_palette:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__palette:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_palette
    cmp #$20
    bcs ScummV5_Op_ActorOps__invalid_palette
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_palette
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    clc
    adc #SAME_SCUMM_C14_A_PALETTE
    adc.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_name:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__invalid_name:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__name:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    xba
    sta.l SAME_SCUMM_C14_NAME_BASE
    lda #$0000
    sta.l SAME_SCUMM_C14_NAME_INDEX
ScummV5_Op_ActorOps__name_loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    bcs ScummV5_Op_ActorOps__invalid_name
    cmp #$00
    beq ScummV5_Op_ActorOps__name_done
    cmp #$FF
    bne ScummV5_Op_ActorOps__name_loop
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    sta.l SAME_SCUMM_CONDITION
    cmp #$01
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$02
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$03
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$08
    beq ScummV5_Op_ActorOps__name_loop
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    bra ScummV5_Op_ActorOps__name_loop
ScummV5_Op_ActorOps__name_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_NAME_INDEX
    sta.l SAME_SCUMM_C14_NAME_SIZES,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__scale:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__operand_error
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__operand_error
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_BOX_SCALE,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__never_clip:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__ignore_boxes:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__follow_boxes:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ActorOps__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ActorOps__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ACTOR_OPS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_AnimateActor:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_AnimateActor__ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_AnimateActor__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_AnimateActor__operand_error
    cmp #$20
    bcs ScummV5_Op_AnimateActor__invalid
    sta.l SAME_SCUMM_C14_ACTOR
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_AnimateActor__operand_error
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_AnimateActor__store
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_AnimateActor__store:
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_AnimateActor__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_AnimateActor__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ANIMATE_ACTOR
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C14_FetchByte:
    sep #$20
    .a8
    jmp ScummV5_C7_FetchFlaggedByte

ScummV5_C14_FetchWord:
    sep #$20
    .a8
    and.l SAME_SCUMM_C14_SUBOP
    beq ScummV5_C14_FetchWord__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C14_FetchWord__done
    jmp ScummV5_ReadVariableReference
ScummV5_C14_FetchWord__direct:
    jmp ScummV5_FetchWord
ScummV5_C14_FetchWord__done:
    rts

ScummV5_C14_BaseX:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    rts

ScummV5_C14_StoreNameByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_NAME_INDEX
    cmp #$00FF
    bcs ScummV5_C14_StoreNameByte__full
    clc
    adc.l SAME_SCUMM_C14_NAME_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_NAMES,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_NAME_INDEX
    inc
    sta.l SAME_SCUMM_C14_NAME_INDEX
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    clc
    rts
ScummV5_C14_StoreNameByte__full:
    sep #$20
    .a8
    sec
    rts

ScummV5_C14_DefaultActor:
    jsr ScummV5_C14_BaseX
    lda #$08
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_X,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SOUND,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION+1,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIM_SPEED,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SHADOW,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_INIT_FRAME,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x
    lda #$03
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
    lda #$04
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda #$05
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    lda #$0F
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_COLOR,x
    lda #$18
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WIDTH,x
    lda #$FF
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_BOX_SCALE,x
    rts

ScummV5_C10_FetchByteParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C10_SUBOP
    beq ScummV5_C10_FetchByteParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C10_FetchByteParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C10_FetchByteParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C10_FetchByteParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C10_FetchByteParam__done:
    rts

ScummV5_C10_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C10_SUBOP
    beq ScummV5_C10_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C10_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C10_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C10_FetchWordParam__done:
    rts

ScummV5_C10_MarkPalette:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PALETTE_PRESENT,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_PALETTE_PRESENT,x
    lda.l SAME_SCUMM_CONDITION
    clc
    rts

ScummV5_C10_ReadFilename:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
ScummV5_C10_ReadFilename__loop:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_C10_ReadFilename__done
    beq ScummV5_C10_ReadFilename__terminal
    ldx #$0000
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    cmp #$3F
    bcs ScummV5_C10_ReadFilename__error
    tax
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_REQUEST_NAME,x
    lda.l SAME_SCUMM_CONDITION
    inc
    sta.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    bra ScummV5_C10_ReadFilename__loop
ScummV5_C10_ReadFilename__terminal:
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    bne ScummV5_C10_ReadFilename__success
ScummV5_C10_ReadFilename__error:
    .a8
    lda #SCUMM_ERR_ROOM_OPS
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C10_ReadFilename__success:
    clc
ScummV5_C10_ReadFilename__done:
    rts

ScummV5_C10_SaveAuxString:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    tax
    lda.l SAME_SCUMM_C8_SIZES,x
    beq ScummV5_C10_SaveAuxString__error
    sta.l SAME_SCUMM_C10_AUX_SIZE
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    sta.l SAME_SCUMM_C10_AUX_NAME_SIZE
    tax
ScummV5_C10_SaveAuxString__copy_name:
    dex
    bmi ScummV5_C10_SaveAuxString__name_done
    lda.l SAME_SCUMM_C10_REQUEST_NAME,x
    sta.l SAME_SCUMM_C10_AUX_NAME,x
    bra ScummV5_C10_SaveAuxString__copy_name
ScummV5_C10_SaveAuxString__name_done:
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_SOURCE_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C10_PARAM3
    ldx #$0000
ScummV5_C10_SaveAuxString__copy_data:
    rep #$20
    .a16
    txa
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_C10_SaveAuxString__success
    sta.l SAME_SCUMM_C10_PARAM4
    clc
    adc.l SAME_SCUMM_C8_SOURCE_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C10_PARAM4
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C10_AUX_DATA,x
    inx
    bra ScummV5_C10_SaveAuxString__copy_data
ScummV5_C10_SaveAuxString__error:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C10_SaveAuxString__success:
    clc
    rts

ScummV5_C10_LoadAuxString:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    beq ScummV5_C10_LoadAuxString__absent
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    cmp.l SAME_SCUMM_C10_AUX_NAME_SIZE
    bne ScummV5_C10_LoadAuxString__absent
    tax
ScummV5_C10_LoadAuxString__compare_name:
    dex
    bmi ScummV5_C10_LoadAuxString__matched
    lda.l SAME_SCUMM_C10_REQUEST_NAME,x
    cmp.l SAME_SCUMM_C10_AUX_NAME,x
    bne ScummV5_C10_LoadAuxString__absent
    bra ScummV5_C10_LoadAuxString__compare_name
ScummV5_C10_LoadAuxString__matched:
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    tax
    lda.l SAME_SCUMM_C10_AUX_SIZE
    sta.l SAME_SCUMM_C8_SIZES,x
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C10_PARAM3
    ldx #$0000
ScummV5_C10_LoadAuxString__copy_data:
    rep #$20
    .a16
    txa
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_C10_LoadAuxString__absent
    sta.l SAME_SCUMM_C10_PARAM4
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM4
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C8_DATA,x
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C10_PARAM4
    tax
    inx
    bra ScummV5_C10_LoadAuxString__copy_data
ScummV5_C10_LoadAuxString__absent:
    clc
    rts

ScummV5_C10_StoreCycleDelay:
    sep #$20
    .a8
    beq ScummV5_C10_StoreCycleDelay__zero
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_LOOP
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
ScummV5_C10_StoreCycleDelay__denominator:
    .a16
    lda.l SAME_SCUMM_OPERAND
    clc
    adc #$004C
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_C10_StoreCycleDelay__denominator
    lda #$4000
    ldy #$0000
ScummV5_C10_StoreCycleDelay__divide:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_C10_StoreCycleDelay__quotient
    sec
    sbc.l SAME_SCUMM_OPERAND
    iny
    bra ScummV5_C10_StoreCycleDelay__divide
ScummV5_C10_StoreCycleDelay__quotient:
    tya
    bra ScummV5_C10_StoreCycleDelay__store
ScummV5_C10_StoreCycleDelay__zero:
    rep #$20
    .a16
    lda #$0000
ScummV5_C10_StoreCycleDelay__store:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C10_PARAM0
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C10_CYCLE_DELAYS,x
    clc
    rts

ScummV5_C10_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C10_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C10_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C10_STATE_SIZE
    bcc ScummV5_C10_ResetState__clear
    lda #$00A0
    sta.l SAME_SCUMM_C10_SCROLL_MIN
    sta.l SAME_SCUMM_C10_SCROLL_MAX
    lda #$00C8
    sta.l SAME_SCUMM_C10_SCREEN_BOTTOM
    lda #$0280
    sta.l SAME_SCUMM_C10_ROOM_WIDTH
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C10_INTENSITY
    sta.l SAME_SCUMM_C10_INTENSITY+1
    sta.l SAME_SCUMM_C10_INTENSITY+2
    sta.l SAME_SCUMM_C10_INTENSITY+4
    sta.l SAME_SCUMM_C10_RGB_INTENSITY
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+1
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+2
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+4
    sta.l SAME_SCUMM_C10_SHADOW
    sta.l SAME_SCUMM_C10_SHADOW+1
    sta.l SAME_SCUMM_C10_SHADOW+2
    sta.l SAME_SCUMM_C10_SHADOW+4
    clc
    rts

ScummV5_C11_ResetState:
    rep #$20
    .a16
    lda #$ACE1
    sta.l SAME_SCUMM_C11_RANDOM_STATE
    lda #$0000
    sta.l SAME_SCUMM_C11_MAXIMUM
    sta.l SAME_SCUMM_C11_SAMPLE
    rts

ScummV5_C12_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C12_ROOM
    ldx #$0000
ScummV5_C12_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C12_MAPPER,x
    inx
    inx
    cpx #$0080
    bcc ScummV5_C12_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C12_INITIALIZED
    rts

ScummV5_C12_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C12_INITIALIZED
    rts

ScummV5_C13_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C13_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C13_LOADED,x
    inx
    inx
    cpx #SAME_SCUMM_C13_STATE_SIZE
    bcc ScummV5_C13_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C13_INITIALIZED
    rts

ScummV5_C13_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C13_INITIALIZED
    rts

ScummV5_C14_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C14_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C14_ACTORS,x
    inx
    inx
    cpx #$0820
    bcc ScummV5_C14_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C14_INITIALIZED
    rts

ScummV5_C14_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C14_INITIALIZED
    rts

ScummV5_C15_ResetState:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C15_CAMERA_FOLLOWS
    lda #$00
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    lda #$01
    sta.l SAME_SCUMM_C15_INITIALIZED
    rts

ScummV5_C16_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C16_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C16_RECORDS,x
    inx
    inx
    cpx #$1000
    bcc ScummV5_C16_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C16_INITIALIZED
    rts

ScummV5_C16_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C16_INITIALIZED
    rts

ScummV5_C17_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C17_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C17_VERBS,x
    inx
    inx
    cpx #$6000
    bcc ScummV5_C17_ResetState__loop
    ldx #$0000
ScummV5_C17_ResetState__saved_loop:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C26_SAVED_STRIDE
    tax
    cpx #(SAME_SCUMM_C26_SAVED_STRIDE * SAME_SCUMM_C26_SAVED_COUNT)
    bcc ScummV5_C17_ResetState__saved_loop
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_INITIALIZED
    lda #$00
    sta.l SAME_SCUMM_C17_CURRENT_ROOM
    rts

ScummV5_C17_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_INITIALIZED
    rts

; Canonical v5 $AB saveRestoreVerbs. The four following bytes are deliberately
; direct operands: upstream consumes flag-aware operands but switches on the
; exact sub-op byte, so high-bit variants fail after consuming their operands.
; Saved verbs occupy physical slots independent of the dense active C17 table.
ScummV5_Op_SaveRestoreVerbs:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_INITIALIZED
    bne ScummV5_Op_SaveRestoreVerbs__state_ready
    jsr ScummV5_C17_ResetState
ScummV5_Op_SaveRestoreVerbs__state_ready:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__operation_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__operation_ok:
    sta.l SAME_SCUMM_C26_OPERATION
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__first_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__first_ok:
    sta.l SAME_SCUMM_C26_FIRST
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__last_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__last_ok:
    sta.l SAME_SCUMM_C26_LAST
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__bank_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__bank_ok:
    .a8
    sta.l SAME_SCUMM_C26_BANK
    lda.l SAME_SCUMM_C26_OPERATION
    cmp #$01
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    cmp #$02
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    cmp #$03
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    jmp ScummV5_C26_Error
ScummV5_Op_SaveRestoreVerbs__range_check:
    lda.l SAME_SCUMM_C26_FIRST
    cmp.l SAME_SCUMM_C26_LAST
    bcc ScummV5_Op_SaveRestoreVerbs__range_loop
    beq ScummV5_Op_SaveRestoreVerbs__range_loop
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SaveRestoreVerbs__range_loop:
    .a8
    lda.l SAME_SCUMM_C26_FIRST
    sta.l SAME_SCUMM_C17_VERB
    jsr ScummV5_C17_RecordOffset
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    sta.l SAME_SCUMM_C26_ACTIVE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_OPERATION
    cmp #$01
    beq ScummV5_Op_SaveRestoreVerbs__save
    cmp #$02
    beq ScummV5_Op_SaveRestoreVerbs__restore
    jmp ScummV5_Op_SaveRestoreVerbs__delete

ScummV5_Op_SaveRestoreVerbs__save:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    bne ScummV5_Op_SaveRestoreVerbs__save_bank
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_bank:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    bne ScummV5_Op_SaveRestoreVerbs__save_present
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_present:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    beq ScummV5_Op_SaveRestoreVerbs__save_active
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_active:
    jsr ScummV5_C26_FindSaved
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SaveRestoreVerbs__save_slot
    jmp ScummV5_C26_Error
ScummV5_Op_SaveRestoreVerbs__save_slot:
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    lda.l SAME_SCUMM_C26_FIRST
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_VERB,x
    jsr ScummV5_C26_CopyActiveToSaved
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    clc
    adc #(SAME_SCUMM_C26_S_PAYLOAD + SAME_SCUMM_C17_V_SAVE_ID)
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_BANK
    sta.l SAME_SCUMM_C26_SAVED,x
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+1,x
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_SaveRestoreVerbs__next

ScummV5_Op_SaveRestoreVerbs__restore:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    beq ScummV5_Op_SaveRestoreVerbs__next
    jsr ScummV5_C26_FindSaved
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SaveRestoreVerbs__next
    jsr ScummV5_C17_ClearRecord
    jsr ScummV5_C26_CopySavedToActive
    jsr ScummV5_C17_RecordX
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    jmp ScummV5_Op_SaveRestoreVerbs__next

ScummV5_Op_SaveRestoreVerbs__delete:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    bne ScummV5_Op_SaveRestoreVerbs__delete_saved
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__delete_saved:
    jsr ScummV5_C26_FindSaved
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SaveRestoreVerbs__next
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x

ScummV5_Op_SaveRestoreVerbs__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_FIRST
    cmp.l SAME_SCUMM_C26_LAST
    beq ScummV5_Op_SaveRestoreVerbs__done
    inc
    sta.l SAME_SCUMM_C26_FIRST
    jmp ScummV5_Op_SaveRestoreVerbs__range_loop
ScummV5_Op_SaveRestoreVerbs__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SaveRestoreVerbs__operand_error:
    jmp ScummV5_Op__error

; Scan every saved slot so the first free offset is available even when an
; earlier matching saved identity exists. The first physical match is canonical.
ScummV5_C26_FindSaved:
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_C26_FREE_OFFSET
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
    ldx #$0000
ScummV5_C26_FindSaved__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    bne ScummV5_C26_FindSaved__occupied
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_C26_FindSaved__next
    txa
    sta.l SAME_SCUMM_C26_FREE_OFFSET
    bra ScummV5_C26_FindSaved__next
ScummV5_C26_FindSaved__occupied:
    .a8
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_VERB,x
    cmp.l SAME_SCUMM_C26_FIRST
    bne ScummV5_C26_FindSaved__next
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PAYLOAD+SAME_SCUMM_C17_V_SAVE_ID+1,x
    bne ScummV5_C26_FindSaved__next
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PAYLOAD+SAME_SCUMM_C17_V_SAVE_ID,x
    cmp.l SAME_SCUMM_C26_BANK
    bne ScummV5_C26_FindSaved__next
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    bne ScummV5_C26_FindSaved__next
    txa
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
ScummV5_C26_FindSaved__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C26_SAVED_STRIDE
    tax
    cpx #(SAME_SCUMM_C26_SAVED_STRIDE * SAME_SCUMM_C26_SAVED_COUNT)
    bcc ScummV5_C26_FindSaved__loop
    rts

ScummV5_C26_CopyActiveToSaved:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C26_COPY_INDEX
ScummV5_C26_CopyActiveToSaved__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc.l SAME_SCUMM_C26_ACTIVE_OFFSET
    tax
    lda.l SAME_SCUMM_C17_VERBS,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc #SAME_SCUMM_C26_S_PAYLOAD
    adc.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C26_SAVED,x
    lda.l SAME_SCUMM_C26_COPY_INDEX
    inc
    inc
    sta.l SAME_SCUMM_C26_COPY_INDEX
    cmp #SAME_SCUMM_C17_VERB_STRIDE
    bcc ScummV5_C26_CopyActiveToSaved__loop
    rts

ScummV5_C26_CopySavedToActive:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C26_COPY_INDEX
ScummV5_C26_CopySavedToActive__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc #SAME_SCUMM_C26_S_PAYLOAD
    adc.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    lda.l SAME_SCUMM_C26_SAVED,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc.l SAME_SCUMM_C26_ACTIVE_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C17_VERBS,x
    lda.l SAME_SCUMM_C26_COPY_INDEX
    inc
    inc
    sta.l SAME_SCUMM_C26_COPY_INDEX
    cmp #SAME_SCUMM_C17_VERB_STRIDE
    bcc ScummV5_C26_CopySavedToActive__loop
    rts

ScummV5_C26_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SAVE_VERBS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_SetVarRange:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_SetVarRange__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__result_ok:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetVarRange__count_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__count_ok:
    rep #$20
    .a16
    and #$00FF
    bne ScummV5_Op_SetVarRange__count_nonzero
    lda #$0100
ScummV5_Op_SetVarRange__count_nonzero:
    sta.l SAME_SCUMM_C9_COUNT
ScummV5_Op_SetVarRange__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_SetVarRange__word
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetVarRange__byte_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__byte_ok:
    rep #$20
    .a16
    and #$00FF
    bra ScummV5_Op_SetVarRange__store
ScummV5_Op_SetVarRange__word:
    rep #$20
    .a16
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetVarRange__store
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__store:
    .a16
    jsr ScummV5_WriteResultValue
    lda.l SAME_SCUMM_C9_COUNT
    dec
    sta.l SAME_SCUMM_C9_COUNT
    beq ScummV5_Op_SetVarRange__done
    jsr ScummV5_C9_AdvanceResult
    bcc ScummV5_Op_SetVarRange__loop
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__done:
    jmp ScummV5_Engine_Frame__next

; Advance the resolved destination while retaining its global/local/bit class.
; Packed bit indices have canonical 12-bit wrap; globals and locals fail when
; a consecutive range crosses their storage boundary.
ScummV5_C9_AdvanceResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_C9_AdvanceResult__bit
    bmi ScummV5_C9_AdvanceResult__local
    clc
    adc #$0002
    cmp #(SAME_SCUMM_VARIABLE_COUNT * 2)
    bcc ScummV5_C9_AdvanceResult__save
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C9_AdvanceResult__local:
    .a16
    and #$003F
    cmp #$003E
    bne ScummV5_C9_AdvanceResult__local_room
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C9_AdvanceResult__local_room:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    clc
    adc #$0002
    bra ScummV5_C9_AdvanceResult__save
ScummV5_C9_AdvanceResult__bit:
    .a16
    and #$0FFF
    inc
    and #$0FFF
    ora #$4000
ScummV5_C9_AdvanceResult__save:
    .a16
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts

; C25 implements canonical v5 soundKludge word-varargs. Non--1 commands are
; retained across ticks; command -1 drains them in order and emits one final
; normalized FLUSH packet. The supported neutral subset is iMUSE commands
; 6 (master volume), 8 (start sound), 9 (stop sound), and 10/11 (stop all).
ScummV5_C25_ResetState:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_C25_FLUSH_COUNT
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    sep #$20
    .a8
    sta.l SAME_SCUMM_C25_WORD_INDEX
    rts

ScummV5_Op_SoundKludge:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C25_PENDING_COUNT
ScummV5_Op_SoundKludge__next_word:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SoundKludge__selector_ok
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_SoundKludge__words_done
    sta.l SAME_SCUMM_C25_SELECTOR
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    cmp #SAME_SCUMM_C25_MAX_WORDS
    bcc ScummV5_Op_SoundKludge__word_room
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__word_room:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SoundKludge__word_ok
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__word_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    and #$80
    beq ScummV5_Op_SoundKludge__value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SoundKludge__variable_ok
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__variable_ok:
    .a16
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_SoundKludge__value_ready:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C25_PENDING_WORDS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    inc
    sta.l SAME_SCUMM_C25_PENDING_COUNT
    jmp ScummV5_Op_SoundKludge__next_word

ScummV5_Op_SoundKludge__words_done:
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    bne ScummV5_Op_SoundKludge__nonempty
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__nonempty:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_PENDING_WORDS
    cmp #$FFFF
    bne ScummV5_Op_SoundKludge__queue
    jmp ScummV5_C25_Flush

ScummV5_Op_SoundKludge__queue:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    cmp #SAME_SCUMM_C25_MAX_COMMANDS
    bcc ScummV5_Op_SoundKludge__queue_room
    jmp ScummV5_C25_Error
ScummV5_Op_SoundKludge__queue_room:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_C25_QUEUE,x
    lda #$00
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
ScummV5_Op_SoundKludge__copy_word:
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    cmp.l SAME_SCUMM_C25_PENDING_COUNT
    bcs ScummV5_Op_SoundKludge__queued
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C25_PENDING_WORDS,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    and #$00FF
    asl
    inc
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C25_QUEUE,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    inc
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    bra ScummV5_Op_SoundKludge__copy_word
ScummV5_Op_SoundKludge__queued:
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    inc
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    jmp ScummV5_Engine_Frame__next

ScummV5_C25_Flush:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_PENDING_COUNT
    lda #$00
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
ScummV5_C25_Flush__next_command:
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    cmp.l SAME_SCUMM_C25_PENDING_COUNT
    bcc ScummV5_C25_Flush__command_present
    jmp ScummV5_C25_Flush__complete
ScummV5_C25_Flush__command_present:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_C25_SELECTOR
    lda #$00
    sta.l SAME_SCUMM_C25_WORD_INDEX
ScummV5_C25_Flush__copy_history:
    .a8
    lda.l SAME_SCUMM_C25_WORD_INDEX
    cmp.l SAME_SCUMM_C25_SELECTOR
    bcs ScummV5_C25_Flush__dispatch
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    sta.l SAME_SCUMM_OPERAND
    inc
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_OPERAND
    tax
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C25_LAST_WORDS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_WORD_INDEX
    inc
    sta.l SAME_SCUMM_C25_WORD_INDEX
    bra ScummV5_C25_Flush__copy_history

ScummV5_C25_Flush__dispatch:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    inc
    tax
    lda.l SAME_SCUMM_C25_QUEUE,x
    cmp #$0006
    beq ScummV5_C25_Flush__master_volume
    cmp #$0008
    beq ScummV5_C25_Flush__start_sound
    cmp #$0009
    beq ScummV5_C25_Flush__stop_sound
    cmp #$000A
    beq ScummV5_C25_Flush__dispatch_stop_all
    cmp #$000B
    bne ScummV5_C25_Flush__dispatch_error
ScummV5_C25_Flush__dispatch_stop_all:
    jmp ScummV5_C25_Flush__stop_all
ScummV5_C25_Flush__dispatch_error:
    jmp ScummV5_C25_Error

ScummV5_C25_Flush__master_volume:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__master_count_ok
    jmp ScummV5_C25_Error
ScummV5_C25_Flush__master_count_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp #$0080
    bcc ScummV5_C25_Flush__master_range_ok
    jmp ScummV5_C25_Error
ScummV5_C25_Flush__master_range_ok:
    asl
    beq ScummV5_C25_Flush__master_scaled
    inc
ScummV5_C25_Flush__master_scaled:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda #$0000
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MASTER_VOLUME
    jsr ScummV5_C25_EmitAudio
    bcs ScummV5_C25_Flush__master_service_error
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__master_service_error:
    jmp ScummV5_C25_ServiceError

ScummV5_C25_Flush__start_sound:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__start_count_ok
    jmp ScummV5_C25_Error
ScummV5_C25_Flush__start_count_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_OPERAND
    lda #$0080
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_PLAY
    jsr ScummV5_C25_EmitAudio
    bcc ScummV5_C25_Flush__command_done
    jmp ScummV5_C25_ServiceError

ScummV5_C25_Flush__stop_sound:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__stop_count_ok
    jmp ScummV5_C25_Error
ScummV5_C25_Flush__stop_count_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_OPERAND
    lda #$0000
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_STOP
    jsr ScummV5_C25_EmitAudio
    bcc ScummV5_C25_Flush__command_done
    jmp ScummV5_C25_ServiceError

ScummV5_C25_Flush__stop_all:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$01
    beq ScummV5_C25_Flush__stop_all_count_ok
    jmp ScummV5_C25_Error
ScummV5_C25_Flush__stop_all_count_ok:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MUSIC_STOP
    jsr ScummV5_C25_EmitAudio
    bcc ScummV5_C25_Flush__stop_all_music_ok
    jmp ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_all_music_ok:
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_STOP
    jsr ScummV5_C25_EmitAudio
    bcc ScummV5_C25_Flush__stop_all_sfx_ok
    jmp ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_all_sfx_ok:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SPEECH_STOP
    jsr ScummV5_C25_EmitAudio
    bcs ScummV5_C25_ServiceError

ScummV5_C25_Flush__command_done:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    inc
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    jmp ScummV5_C25_Flush__next_command

ScummV5_C25_Flush__complete:
    .a8
    lda.l SAME_SCUMM_C25_FLUSH_COUNT
    inc
    sta.l SAME_SCUMM_C25_FLUSH_COUNT
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_FLUSH
    jsr ScummV5_C25_EmitAudio
    bcs ScummV5_C25_ServiceError
    jmp ScummV5_Engine_Frame__next

; Input: A8 normalized audio opcode, operand/condition are arg0/arg1.
ScummV5_C25_EmitAudio:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C25_SELECTOR
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda.l SAME_SCUMM_C25_SELECTOR
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    rts

ScummV5_C25_ServiceError:
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
    jsr ScummV5_SetError
    sec
    jmp ScummV5_Engine_Frame__error

ScummV5_C25_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SOUND_KLUDGE
    jsr ScummV5_SetError
    sec
    jmp ScummV5_Engine_Frame__error

ScummV5_Op_StartMusic:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartMusic__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartMusic__operand_ok:
    sta.l SAME_SCUMM_CONDITION
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0001
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_Op_StartMusic__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StartMusic__queued:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StopMusic:
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    jsr Same_Event_Push
    bcc ScummV5_Op_StopMusic__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StopMusic__queued:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StartSound:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartSound__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartSound__operand_ok:
    sta.l SAME_SCUMM_CONDITION
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_SFX_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0080
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_Op_StartSound__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StartSound__queued:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StopSound:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StopSound__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StopSound__operand_ok:
    sta.l SAME_SCUMM_CONDITION
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_SFX_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bcc ScummV5_Op_StopSound__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StopSound__queued:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op__service_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_Stop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_Stop__cutscene_clear
    jmp ScummV5_C19_Error
ScummV5_Op_Stop__cutscene_clear:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Op_Stop__complete
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    beq ScummV5_Op_Stop__c4_slot
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    beq ScummV5_Op_Stop__c4_slot
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    beq ScummV5_Op_Stop__c4_slot
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    beq ScummV5_Op_Stop__c4_slot
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    beq ScummV5_Op_Stop__c4_slot
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_Op_Stop__complete
ScummV5_Op_Stop__c4_slot:
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_Stop__complete
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_Stop__complete:
    .a8
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_BreakHere:
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_Move:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Move__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Move__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Move__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Move__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Add:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Add__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Add__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Add__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Add__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadResultValue
    clc
    adc.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Subtract:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Subtract__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Subtract__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Subtract__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Subtract__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadResultValue
    sec
    sbc.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Multiply:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Multiply__ready
    jmp ScummV5_Op__error
ScummV5_Op_Multiply__ready:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_PRODUCT
    lda #$0010
    sta.l SAME_SCUMM_LOOP
ScummV5_Op_Multiply__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_OPERAND
    and #$0001
    beq ScummV5_Op_Multiply__no_add
    lda.l SAME_SCUMM_PRODUCT
    clc
    adc.l SAME_SCUMM_LHS
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Multiply__no_add:
    lda.l SAME_SCUMM_LHS
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    lsr
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_Op_Multiply__loop
    lda.l SAME_SCUMM_PRODUCT
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Divide:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Divide__operands_ready
    jmp ScummV5_Op__error
ScummV5_Op_Divide__operands_ready:
    lda.l SAME_SCUMM_OPERAND
    bne ScummV5_Op_Divide__nonzero
    sep #$20
    .a8
    lda #SCUMM_ERR_DIVIDE_ZERO
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Divide__nonzero:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    eor.l SAME_SCUMM_OPERAND
    and #$8000
    beq ScummV5_Op_Divide__same_sign
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
    bra ScummV5_Op_Divide__sign_ready
ScummV5_Op_Divide__same_sign:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
ScummV5_Op_Divide__sign_ready:
    .a16
    lda.l SAME_SCUMM_LHS
    bpl ScummV5_Op_Divide__lhs_positive
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_LHS
ScummV5_Op_Divide__lhs_positive:
    .a16
    lda.l SAME_SCUMM_OPERAND
    bpl ScummV5_Op_Divide__rhs_positive
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_Divide__rhs_positive:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PRODUCT
    sta.l SAME_SCUMM_REMAINDER
    lda #$0010
    sta.l SAME_SCUMM_LOOP
ScummV5_Op_Divide__loop:
    lda.l SAME_SCUMM_LHS
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_REMAINDER
    rol
    sta.l SAME_SCUMM_REMAINDER
    lda.l SAME_SCUMM_PRODUCT
    asl
    sta.l SAME_SCUMM_PRODUCT
    lda.l SAME_SCUMM_REMAINDER
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_Divide__next_bit
    sbc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_REMAINDER
    lda.l SAME_SCUMM_PRODUCT
    ora #$0001
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Divide__next_bit:
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_Op_Divide__loop
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_Divide__store
    rep #$20
    .a16
    lda.l SAME_SCUMM_PRODUCT
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Divide__store:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PRODUCT
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_And:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_And__ready
    jmp ScummV5_Op__error
ScummV5_Op_And__ready:
    lda.l SAME_SCUMM_LHS
    and.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_Binary__store

ScummV5_Op_Or:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Or__ready
    jmp ScummV5_Op__error
ScummV5_Op_Or__ready:
    lda.l SAME_SCUMM_LHS
    ora.l SAME_SCUMM_OPERAND
ScummV5_Op_Binary__store:
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Increment:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Increment__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Increment__result_ok:
    .a16
    .i16
    jsr ScummV5_ReadResultValue
    inc
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Decrement:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Decrement__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Decrement__result_ok:
    jsr ScummV5_ReadResultValue
    dec
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Compare:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Compare__operands_ready
    jmp ScummV5_Op__error
ScummV5_Op_Compare__operands_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$48
    beq ScummV5_Op_Compare__equal
    cmp #$08
    beq ScummV5_Op_Compare__not_equal
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    eor #$8000
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$44
    beq ScummV5_Op_Compare__less
    cmp #$78
    beq ScummV5_Op_Compare__greater
    cmp #$38
    beq ScummV5_Op_Compare__less_equal
    bra ScummV5_Op_Compare__greater_equal
ScummV5_Op_Compare__equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    beq ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__not_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bne ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__less:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__greater:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__less_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bcs ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__greater_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_Compare__true
ScummV5_Op_Compare__false:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONDITION
    bra ScummV5_Op_Compare__offset
ScummV5_Op_Compare__true:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_Compare__offset:
    jsr ScummV5_ApplyConditionOffset
    bcc ScummV5_Op_Compare__done
    jmp ScummV5_Op__error
ScummV5_Op_Compare__done:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_CompareZero:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_CompareZero__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_CompareZero__result_ok:
    jsr ScummV5_ReadResultValue
    bne ScummV5_Op_CompareZero__nonzero
    sep #$20
    .a8
    lda #$01
    bra ScummV5_Op_CompareZero__select
ScummV5_Op_CompareZero__nonzero:
    sep #$20
    .a8
    lda #$00
ScummV5_Op_CompareZero__select:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$28
    beq ScummV5_Op_CompareZero__offset
    lda.l SAME_SCUMM_CONDITION
    eor #$01
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_CompareZero__offset:
    jsr ScummV5_ApplyConditionOffset
    bcc ScummV5_Op_CompareZero__done
    jmp ScummV5_Op__error
ScummV5_Op_CompareZero__done:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_JumpRelative:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_JumpRelative__offset_ok
    jmp ScummV5_Op__error
ScummV5_Op_JumpRelative__offset_ok:
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_PC
    clc
    adc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_PC
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Delay:
    rep #$30
    .a16
    .i16
    ; Delay is a three-byte little-endian operand in SCUMM v5.  Decode the
    ; complete operand here instead of nesting three byte-fetch subroutines;
    ; the VM tick can then be pre-empted by NMI without carrying a deep helper
    ; return stack across the interrupt.
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sec
    sbc #$0002
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_Op_Delay__in_range
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Delay__in_range:
    sep #$20
    .a8
    inx
    inx
    jsr ScummV5_FetchSelectedByteAtX
    dex
    dex
    cmp #$00
    beq ScummV5_Op_Delay__high_valid
    lda #SCUMM_ERR_DELAY_RANGE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Delay__high_valid:
    jsr ScummV5_FetchSelectedByteAtX
    sta.l SAME_SCUMM_OPERAND
    inx
    jsr ScummV5_FetchSelectedByteAtX
    dex
    sta.l SAME_SCUMM_OPERAND+1
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_DELAY
    txa
    clc
    adc #$0003
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_DelayVariable:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_DelayVariable__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_DelayVariable__result_ok:
    .a16
    .i16
    jsr ScummV5_ReadResultValue
    bpl ScummV5_Op_DelayVariable__store
    lda #$0000
ScummV5_Op_DelayVariable__store:
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_StartScript:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_StartScript__c4
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__c4:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_StartScript__number_stored:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_ARG_COUNT
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Op_StartScript__clear_args:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_ARGS,x
    inx
    inx
    cpx #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcc ScummV5_Op_StartScript__clear_args
ScummV5_Op_StartScript__next_arg:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StartScript__arg_selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_StartScript__args_done
    pha
    lda.l SAME_SCUMM_C4_ARG_COUNT
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_StartScript__arg_room
    pla
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_room:
    .a8
    pla
    and #$80
    pha
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_StartScript__arg_word_ok
    sep #$20
    .a8
    pla
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_word_ok:
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    pla
    beq ScummV5_Op_StartScript__arg_value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_StartScript__arg_variable_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_variable_ok:
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_StartScript__arg_value_ready:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_ARG_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_ARGS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    inc
    sta.l SAME_SCUMM_C4_ARG_COUNT
    bra ScummV5_Op_StartScript__next_arg
ScummV5_Op_StartScript__args_done:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__normal_args_done
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_StartScript__chain_retired
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_StartScript__chain_retired:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_Op_StartScript__chain_target
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_StartScript__chain_target:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_FLAGS
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__normal_args_done:
    .a8
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_Op_StartScript__has_script
    jmp ScummV5_Op_StartScript__no_script
ScummV5_Op_StartScript__has_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$40
    bne ScummV5_Op_StartScript__allocate
    lda.l SAME_SCUMM_CONDITION
    jsr ScummV5_C4_StopNumber
ScummV5_Op_StartScript__allocate:
    .a8
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_StartScript__scan
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__scan:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C4_SCAN_SLOT
ScummV5_Op_StartScript__scan_next:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcs ScummV5_Op_StartScript__capacity_error
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_StartScript__found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StartScript__found
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    inc
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    bra ScummV5_Op_StartScript__scan_next
ScummV5_Op_StartScript__capacity_error:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__capacity_error_code
    lda #$42
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__capacity_error_code:
    .a8
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__found:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    tax
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp #$02
    beq ScummV5_Op_StartScript__program2
    cmp #$03
    beq ScummV5_Op_StartScript__program3
    cmp #$04
    beq ScummV5_Op_StartScript__program4
    cmp #$05
    beq ScummV5_Op_StartScript__program5
    cmp #$06
    beq ScummV5_Op_StartScript__program6
    cmp #$07
    beq ScummV5_Op_StartScript__program7
    cmp #$0A
    beq ScummV5_Op_StartScript__program10
    cmp #$0B
    beq ScummV5_Op_StartScript__program11
    cmp #$0C
    beq ScummV5_Op_StartScript__program12
    cmp #$0D
    beq ScummV5_Op_StartScript__program13
ScummV5_Op_StartScript__mapping_error:
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__mapping_error_code
    lda #$42
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__mapping_error_code:
    .a8
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__program2:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD2
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program3:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD3
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program4:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD4
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program5:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD5
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program6:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD6
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program7:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD7
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program10:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_CHAIN10
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program11:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_CHAIN11
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program12:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_TARGET12
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program13:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_TARGET13
ScummV5_Op_StartScript__program_ready:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$20
    beq ScummV5_Op_StartScript__freeze_flag_ready
    lda #$01
ScummV5_Op_StartScript__freeze_flag_ready:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$40
    beq ScummV5_Op_StartScript__recursive_flag_ready
    lda #$01
ScummV5_Op_StartScript__recursive_flag_ready:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    lda #$00
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
    sta.l SAME_SCUMM_RESULT_OFFSET
    tax
    lda #$0000
    ldy #$0000
ScummV5_Op_StartScript__clear_locals:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_StartScript__clear_locals
    lda.l SAME_SCUMM_RESULT_OFFSET
    tax
    ldy #$0000
ScummV5_Op_StartScript__copy_args:
    .a16
    .i16
    cpy #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcs ScummV5_Op_StartScript__locals_ready
    tya
    tax
    lda.l SAME_SCUMM_C4_ARGS,x
    sta.l SAME_SCUMM_OPERAND
    tya
    clc
    adc.l SAME_SCUMM_RESULT_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    iny
    iny
    bra ScummV5_Op_StartScript__copy_args
ScummV5_Op_StartScript__locals_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__run_nested
    jsr ScummV5_C4_RunAllocatedNoParent
    php
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    plp
    bcc ScummV5_Op_StartScript__chain_complete
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__chain_complete:
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_StartScript__run_nested:
    jsr ScummV5_C4_RunNestedChild
    bcc ScummV5_Op_StartScript__nested_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__nested_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StartScript__parent_stopped
ScummV5_Op_StartScript__no_script:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_StartScript__parent_stopped:
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_ChainScript:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_ChainScript__c6
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_ChainScript__c6:
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    beq ScummV5_Op_ChainScript__no_freeze_flag
    lda #$20
ScummV5_Op_ChainScript__no_freeze_flag:
    .a8
    sta.l SAME_SCUMM_C4_CHAIN_FLAGS
    lda.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    beq ScummV5_Op_ChainScript__flags_ready
    lda.l SAME_SCUMM_C4_CHAIN_FLAGS
    ora #$40
    sta.l SAME_SCUMM_C4_CHAIN_FLAGS
ScummV5_Op_ChainScript__flags_ready:
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_ChainScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_ChainScript__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda #$01
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jmp ScummV5_Op_StartScript__number_stored

ScummV5_Op_StopScript:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StopScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_StopScript__number_ok:
    .a8
    beq ScummV5_Op_StopScript__self
    jsr ScummV5_C4_StopNumber
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StopScript__complete
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_StopScript__self:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_StopScript__self_counted
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_StopScript__self_counted:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
ScummV5_Op_StopScript__complete:
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_FreezeScripts:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    beq ScummV5_Op_FreezeScripts__c20
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_FreezeScripts__c5
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__c5:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_FreezeScripts__flag_ok
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__flag_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_FreezeScripts__unfreeze
    ldx #$0000
ScummV5_Op_FreezeScripts__freeze_scan:
    .a8
    .i16
    txa
    cmp.l SAME_SCUMM_C4_CURRENT_SLOT
    beq ScummV5_Op_FreezeScripts__freeze_next
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_FreezeScripts__freeze_next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_FreezeScripts__freeze_next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_Op_FreezeScripts__freeze_next
    lda.l SAME_SCUMM_CONDITION
    bmi ScummV5_Op_FreezeScripts__freeze_slot
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    bne ScummV5_Op_FreezeScripts__freeze_next
ScummV5_Op_FreezeScripts__freeze_slot:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    inc
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
ScummV5_Op_FreezeScripts__freeze_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_FreezeScripts__freeze_scan
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FreezeScripts__unfreeze:
    .a8
    .i16
    ldx #$0000
ScummV5_Op_FreezeScripts__unfreeze_scan:
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    beq ScummV5_Op_FreezeScripts__unfreeze_next
    dec
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
ScummV5_Op_FreezeScripts__unfreeze_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_FreezeScripts__unfreeze_scan
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_FreezeScripts__c20:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_FreezeScripts__c20_flag_ok
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__c20_flag_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_C20_COUNT
    beq ScummV5_Op_FreezeScripts__c20_done
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    asl
    sta.l SAME_SCUMM_OPERAND
    ldx #$0000
ScummV5_Op_FreezeScripts__c20_loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_FreezeScripts__c20_unfreeze
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    cmp #$FF
    beq ScummV5_Op_FreezeScripts__c20_error
    inc
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    bra ScummV5_Op_FreezeScripts__c20_next
ScummV5_Op_FreezeScripts__c20_unfreeze:
    .a8
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    beq ScummV5_Op_FreezeScripts__c20_next
    dec
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
ScummV5_Op_FreezeScripts__c20_next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C20_RECORD_STRIDE
    tax
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_FreezeScripts__c20_loop
ScummV5_Op_FreezeScripts__c20_done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FreezeScripts__c20_error:
    .a8
    lda #SCUMM_ERR_SENTENCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_IsScriptRunning:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_IsScriptRunning__c5
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__c5:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_IsScriptRunning__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__result_ok:
    sep #$20
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_IsScriptRunning__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    ldx #$0000
ScummV5_Op_IsScriptRunning__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_IsScriptRunning__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_IsScriptRunning__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_Op_IsScriptRunning__next
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_IsScriptRunning__true
ScummV5_Op_IsScriptRunning__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_IsScriptRunning__scan
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_IsScriptRunning__true:
    rep #$20
    .a16
    lda #$0001
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op__error:
    jmp ScummV5_Engine_Frame__error

ScummV5_Op_CursorCommand:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_CursorCommand__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__subop_ok:
    .a8
    sta.l SAME_SCUMM_C7_SUBOP
    and #$1F
    cmp #$01
    beq ScummV5_Op_CursorCommand__cursor_on
    cmp #$02
    beq ScummV5_Op_CursorCommand__cursor_off
    cmp #$03
    beq ScummV5_Op_CursorCommand__userput_on
    cmp #$04
    beq ScummV5_Op_CursorCommand__userput_off
    cmp #$05
    beq ScummV5_Op_CursorCommand__cursor_soft_on
    cmp #$06
    beq ScummV5_Op_CursorCommand__cursor_soft_off
    cmp #$07
    beq ScummV5_Op_CursorCommand__userput_soft_on
    cmp #$08
    bne ScummV5_Op_CursorCommand__check_image
    jmp ScummV5_Op_CursorCommand__userput_soft_off
ScummV5_Op_CursorCommand__check_image:
    .a8
    cmp #$0A
    bne ScummV5_Op_CursorCommand__check_hotspot
    jmp ScummV5_Op_CursorCommand__image
ScummV5_Op_CursorCommand__check_hotspot:
    .a8
    cmp #$0B
    bne ScummV5_Op_CursorCommand__check_cursor_id
    jmp ScummV5_Op_CursorCommand__hotspot
ScummV5_Op_CursorCommand__check_cursor_id:
    .a8
    cmp #$0C
    bne ScummV5_Op_CursorCommand__check_charset_id
    jmp ScummV5_Op_CursorCommand__cursor_id
ScummV5_Op_CursorCommand__check_charset_id:
    .a8
    cmp #$0D
    bne ScummV5_Op_CursorCommand__check_colors
    jmp ScummV5_Op_CursorCommand__charset_id
ScummV5_Op_CursorCommand__check_colors:
    .a8
    cmp #$0E
    bne ScummV5_Op_CursorCommand__unknown
    jmp ScummV5_Op_CursorCommand__colors
ScummV5_Op_CursorCommand__unknown:
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__cursor_on:
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_off:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_on:
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_off:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_soft_on:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_CURSOR_STATE
    inc
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_soft_off:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_CURSOR_STATE
    dec
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_soft_on:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_USERPUT_STATE
    inc
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_soft_off:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_USERPUT_STATE
    dec
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__image:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__image_first_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__image_first_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_IMAGE
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__image_second_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__image_second_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_CHAR
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__hotspot:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_first_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_first_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_CURSOR
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_second_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_second_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_X
    lda #$20
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_third_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_third_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_Y
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_id:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__cursor_id_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__cursor_id_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_ID
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__charset_id:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__charset_id_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__charset_id_ok:
    .a8
    sta.l SAME_SCUMM_C7_CHARSET_ID
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__colors:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C7_COLOR_COUNT
ScummV5_Op_CursorCommand__color_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_CursorCommand__color_selector_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_CursorCommand__done
    sta.l SAME_SCUMM_C7_PARAM_INDEX
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    cmp #$10
    bcc ScummV5_Op_CursorCommand__color_room
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    bra ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_room:
    .a8
    lda.l SAME_SCUMM_C7_PARAM_INDEX
    and #$80
    beq ScummV5_Op_CursorCommand__color_direct
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_CursorCommand__color_variable_ref_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_variable_ref_ok:
    .a16
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_CursorCommand__color_store
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_direct:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_CursorCommand__color_store
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_store:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C7_COLORS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    inc
    sta.l SAME_SCUMM_C7_COLOR_COUNT
    bra ScummV5_Op_CursorCommand__color_loop
ScummV5_Op_CursorCommand__error:
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__done:
    sep #$20
    .a8
    lda #$2C
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StringOps:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__subop_ok:
    .a8
    sta.l SAME_SCUMM_C8_SUBOP
    and #$1F
    cmp #$01
    beq ScummV5_Op_StringOps__load
    cmp #$02
    bne ScummV5_Op_StringOps__check_set
    jmp ScummV5_Op_StringOps__copy
ScummV5_Op_StringOps__check_set:
    .a8
    cmp #$03
    bne ScummV5_Op_StringOps__check_get
    jmp ScummV5_Op_StringOps__set
ScummV5_Op_StringOps__check_get:
    .a8
    cmp #$04
    bne ScummV5_Op_StringOps__check_create
    jmp ScummV5_Op_StringOps__get
ScummV5_Op_StringOps__check_create:
    .a8
    cmp #$05
    bne ScummV5_Op_StringOps__unknown
    jmp ScummV5_Op_StringOps__create
ScummV5_Op_StringOps__unknown:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_StringOps__load:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__load_id_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__load_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_byte_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_byte_ok:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_stored
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_stored:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    lda.l SAME_SCUMM_C8_VALUE
    beq ScummV5_Op_StringOps__load_done
    cmp #$FF
    beq ScummV5_Op_StringOps__load_control
    bra ScummV5_Op_StringOps__load_loop
ScummV5_Op_StringOps__load_control:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_control_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_control_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_control_stored
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_control_stored:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    lda.l SAME_SCUMM_C8_VALUE
    cmp #$01
    beq ScummV5_Op_StringOps__load_loop
    cmp #$02
    beq ScummV5_Op_StringOps__load_loop
    cmp #$03
    beq ScummV5_Op_StringOps__load_loop
    cmp #$08
    beq ScummV5_Op_StringOps__load_loop
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_arg1_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg1_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_arg1_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg1_ok:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_arg2_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg2_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_arg2_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg2_ok:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    jmp ScummV5_Op_StringOps__load_loop
ScummV5_Op_StringOps__load_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    sta.l SAME_SCUMM_C8_SIZES,x
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__create:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__create_id_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__create_size_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_size_ok:
    .a8
    sta.l SAME_SCUMM_C8_LENGTH
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_LENGTH
    sta.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__create_nonempty
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__create_nonempty:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__create_loop:
    .a8
    lda #$00
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__create_stored
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_stored:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    cmp.l SAME_SCUMM_C8_LENGTH
    bcc ScummV5_Op_StringOps__create_loop
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__copy:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__copy_dest_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__copy_dest_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__copy_source_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__copy_source_ok:
    .a8
    sta.l SAME_SCUMM_C8_SECOND_ID
    cmp.l SAME_SCUMM_C8_STRING_ID
    bne ScummV5_Op_StringOps__copy_distinct
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__copy_distinct:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_SECOND_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    sta.l SAME_SCUMM_C8_LENGTH
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_LENGTH
    sta.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__copy_nonempty
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__copy_nonempty:
    .a8
    lda.l SAME_SCUMM_C8_SECOND_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_SOURCE_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__copy_loop:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_SOURCE_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C8_DATA,x
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    cmp.l SAME_SCUMM_C8_LENGTH
    bcc ScummV5_Op_StringOps__copy_loop
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__set:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_id_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_index_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_index_ok:
    .a8
    sta.l SAME_SCUMM_C8_INDEX
    lda #$20
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_value_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_value_ok:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__set_present
    jmp ScummV5_Op_StringOps__missing
ScummV5_Op_StringOps__set_present:
    .a8
    cmp.l SAME_SCUMM_C8_INDEX
    bcc ScummV5_Op_StringOps__set_oob
    beq ScummV5_Op_StringOps__set_oob
    lda.l SAME_SCUMM_C8_VALUE
    jsr ScummV5_C8_StoreValueAtIndex
    bcs ScummV5_Op_StringOps__error
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__set_oob:
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__get:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_StringOps__error
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcs ScummV5_Op_StringOps__error
    sta.l SAME_SCUMM_C8_STRING_ID
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcs ScummV5_Op_StringOps__error
    sta.l SAME_SCUMM_C8_INDEX
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    beq ScummV5_Op_StringOps__missing
    cmp.l SAME_SCUMM_C8_INDEX
    bcc ScummV5_Op_StringOps__get_zero
    beq ScummV5_Op_StringOps__get_zero
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    rep #$20
    .a16
    and #$00FF
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__get_zero:
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__missing:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__error:
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__done:
    sep #$20
    .a8
    lda #$27
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_C8_FetchParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    and.l SAME_SCUMM_C8_SUBOP
    beq ScummV5_C8_FetchParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C8_FetchParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C8_FetchParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C8_FetchParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C8_FetchParam__done:
    rts

ScummV5_C8_BaseForId:
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    rts

ScummV5_C8_SetDestBase:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    rts

ScummV5_C8_StoreValueAtIndex:
    rep #$30
    .a16
    .i16
    and #$00FF
    tay
    sep #$20
    .a8
    sta.l SAME_SCUMM_C8_PENDING
    lda.l SAME_SCUMM_C8_INDEX
    cmp #SAME_SCUMM_C8_MAX_BYTES
    bcc ScummV5_C8_StoreValueAtIndex__room
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C8_StoreValueAtIndex__room:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_DATA,x
    and #$FF00
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C8_PENDING
    and #$00FF
    ora.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C8_DATA,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_PENDING
    clc
    rts

ScummV5_C8_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C8_ResetState__clear_sizes:
    .a16
    .i16
    sta.l SAME_SCUMM_C8_SIZES,x
    inx
    inx
    cpx #SAME_SCUMM_C8_SIZE_TABLE_BYTES
    bcc ScummV5_C8_ResetState__clear_sizes
    rts

ScummV5_C7_FetchFlaggedByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C7_PARAM_INDEX
    and.l SAME_SCUMM_C7_SUBOP
    beq ScummV5_C7_FetchFlaggedByte__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C7_FetchFlaggedByte__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C7_FetchFlaggedByte__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C7_FetchFlaggedByte__direct:
    jmp ScummV5_FetchByte
ScummV5_C7_FetchFlaggedByte__done:
    rts

ScummV5_C7_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C7_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C7_CURSOR_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C7_STATE_SIZE
    bcc ScummV5_C7_ResetState__clear
    lda #$0001
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    rts

; ---------------------------------------------------------------------------
; Decoder helpers. C1-C3 use sixteen globals; C4 additionally resolves the v5
; $4000 local namespace into the current slot's 32-word local block.
; ---------------------------------------------------------------------------
ScummV5_ReadBinaryOperands:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_ReadBinaryOperands__done
    jsr ScummV5_ReadResultValue
    sta.l SAME_SCUMM_LHS
    jsr ScummV5_FetchVarOrDirectWord
    bcs ScummV5_ReadBinaryOperands__done
    sta.l SAME_SCUMM_OPERAND
    clc
ScummV5_ReadBinaryOperands__done:
    rts

ScummV5_ApplyConditionOffset:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcs ScummV5_ApplyConditionOffset__done
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_ApplyConditionOffset__success
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    clc
    adc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_PC
ScummV5_ApplyConditionOffset__success:
    clc
ScummV5_ApplyConditionOffset__done:
    rts

ScummV5_ReadResultOffset:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcc ScummV5_ReadResultOffset__reference_fetched
    rts
ScummV5_ReadResultOffset__reference_fetched:
    .a16
    .i16
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_LHS
    and #$2000
    beq ScummV5_ReadResultOffset__direct
    lda.l SAME_SCUMM_LHS
    and #$0FFF
    sta.l SAME_SCUMM_PRODUCT
    jsr ScummV5_FetchWord
    bcc ScummV5_ReadResultOffset__index_fetched
    rts
ScummV5_ReadResultOffset__index_fetched:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    and #$2000
    beq ScummV5_ReadResultOffset__literal_index
    lda.l SAME_SCUMM_OPERAND
    and #$DFFF
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_ReadResultOffset__add_index
    rts
ScummV5_ReadResultOffset__literal_index:
    .a16
    lda.l SAME_SCUMM_OPERAND
    and #$0FFF
ScummV5_ReadResultOffset__add_index:
    clc
    adc.l SAME_SCUMM_PRODUCT
    bra ScummV5_ReadResultOffset__range_check
ScummV5_ReadResultOffset__direct:
    .a16
    lda.l SAME_SCUMM_LHS
    and #$0FFF
ScummV5_ReadResultOffset__range_check:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LHS
    bit #$8000
    bne ScummV5_ReadResultOffset__bit_range
    bit #$4000
    bne ScummV5_ReadResultOffset__local_range
    lda.l SAME_SCUMM_OPERAND
    cmp #SAME_SCUMM_VARIABLE_COUNT
    bcc ScummV5_ReadResultOffset__global_valid
ScummV5_ReadResultOffset__variable_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__bit_range:
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp #$1000
    bcc ScummV5_ReadResultOffset__bit_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_BIT_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__bit_valid:
    .a16
    ora #$4000
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts
ScummV5_ReadResultOffset__local_range:
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_ReadResultOffset__local_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__local_valid:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    xba
    lsr
    lsr
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_LHS
    ora #$8000
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts
ScummV5_ReadResultOffset__global_valid:
    lda.l SAME_SCUMM_OPERAND
    asl
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
ScummV5_ReadResultOffset__done:
    rts

ScummV5_FetchVarOrDirectWord:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    bne ScummV5_FetchVarOrDirectWord__variable
    rep #$30
    .a16
    .i16
    jmp ScummV5_FetchWord
ScummV5_FetchVarOrDirectWord__variable:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcs ScummV5_FetchVarOrDirectWord__done
    jmp ScummV5_ReadVariableReference
ScummV5_FetchVarOrDirectWord__done:
    rts

ScummV5_FetchVarOrDirectByte:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    bne ScummV5_FetchVarOrDirectByte__variable
    jmp ScummV5_FetchByte
ScummV5_FetchVarOrDirectByte__variable:
    jsr ScummV5_FetchWord
    bcs ScummV5_FetchVarOrDirectByte__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_FetchVarOrDirectByte__done
    sep #$20
    .a8
    clc
ScummV5_FetchVarOrDirectByte__done:
    rts

ScummV5_ReadVariableReference:
    rep #$30
    .a16
    .i16
    bit #$8000
    bne ScummV5_ReadVariableReference__bit
    bit #$4000
    bne ScummV5_ReadVariableReference__local
    cmp #SAME_SCUMM_VARIABLE_COUNT
    bcc ScummV5_ReadVariableReference__global_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__bit:
    .a16
    and #$7FFF
    cmp #$1000
    bcc ScummV5_ReadVariableReference__bit_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_BIT_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__bit_valid:
    jmp ScummV5_C7_ReadBit
ScummV5_ReadVariableReference__global_valid:
    .a16
    .i16
    asl
    tax
    lda.l SAME_SCUMM_VARIABLES,x
    clc
    rts
ScummV5_ReadVariableReference__local:
    .a16
    and #$0FFF
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_ReadVariableReference__local_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__local_valid:
    .a16
    asl
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    xba
    lsr
    lsr
    clc
    adc.l SAME_SCUMM_OPERAND
    tax
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    clc
    rts

ScummV5_ReadResultValue:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_ReadResultValue__bit
    bmi ScummV5_ReadResultValue__local
    tax
    lda.l SAME_SCUMM_VARIABLES,x
    rts
ScummV5_ReadResultValue__local:
    .a16
    and #$7FFF
    tax
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    rts
ScummV5_ReadResultValue__bit:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    and #$0FFF
    jmp ScummV5_C7_ReadBit

ScummV5_WriteResultValue:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_WriteResultValue__bit
    bmi ScummV5_WriteResultValue__local
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_VARIABLES,x
    rts
ScummV5_WriteResultValue__local:
    .a16
    and #$7FFF
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    rts
ScummV5_WriteResultValue__bit:
    jmp ScummV5_C7_WriteBitResult

ScummV5_C7_ReadBit:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_BITS,x
    and.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C7_ReadBit__zero
    rep #$20
    .a16
    lda #$0001
    clc
    rts
ScummV5_C7_ReadBit__zero:
    rep #$20
    .a16
    lda #$0000
    clc
    rts

ScummV5_C7_WriteBitResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    and #$0FFF
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_OPERAND
    beq ScummV5_C7_WriteBitResult__clear
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_BITS,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C7_BITS,x
    rep #$20
    .a16
    rts
ScummV5_C7_WriteBitResult__clear:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C7_BITS,x
    sta.l SAME_SCUMM_C7_BITS,x
    rep #$20
    .a16
    rts

ScummV5_C7_BitMasks:
    .byte $01,$02,$04,$08,$10,$20,$40,$80

ScummV5_FetchWord:
    rep #$10
    .i16
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_FetchWord__done
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_FetchByte
    bcs ScummV5_FetchWord__done
    sta.l SAME_SCUMM_OPERAND+1
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    clc
ScummV5_FetchWord__done:
    rts

ScummV5_FetchByte:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_FetchByte__valid
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_FetchByte__valid:
    sep #$20
    .a8
    jsr ScummV5_FetchSelectedByteAtX
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    txa
    inc
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    clc
    rts

ScummV5_GetProgramSize:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    cmp #SCUMM_C2_FIXTURE_EXTENDED
    bne ScummV5_GetProgramSize__unknown
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_EXTENDED_SIZE
    rts
ScummV5_GetProgramSize__unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_UNKNOWN_OPCODE
    bne ScummV5_GetProgramSize__bad_variable
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_UNKNOWN_OPCODE_SIZE
    rts
ScummV5_GetProgramSize__bad_variable:
    .a8
    cmp #SCUMM_C2_FIXTURE_BAD_VARIABLE
    bne ScummV5_GetProgramSize__truncated
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_BAD_VARIABLE_SIZE
    rts
ScummV5_GetProgramSize__truncated:
    .a8
    cmp #SCUMM_C2_FIXTURE_TRUNCATED_OPERAND
    bne ScummV5_GetProgramSize__budget
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_TRUNCATED_OPERAND_SIZE
    rts
ScummV5_GetProgramSize__budget:
    .a8
    cmp #SCUMM_C2_FIXTURE_BUDGET_EXHAUSTION
    bne ScummV5_GetProgramSize__divide_zero
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_BUDGET_EXHAUSTION_SIZE
    rts
ScummV5_GetProgramSize__divide_zero:
    .a8
    cmp #SCUMM_C2_FIXTURE_DIVISION_BY_ZERO
    bne ScummV5_GetProgramSize__jump_escape
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_DIVISION_BY_ZERO_SIZE
    rts
ScummV5_GetProgramSize__jump_escape:
    .a8
    cmp #SCUMM_C2_FIXTURE_JUMP_ESCAPE
    bne ScummV5_GetProgramSize__delay_range
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_JUMP_ESCAPE_SIZE
    rts
ScummV5_GetProgramSize__delay_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_DELAY_RANGE
    bne ScummV5_GetProgramSize__c3_operands
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_DELAY_RANGE_SIZE
    rts
ScummV5_GetProgramSize__c3_operands:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_OPERANDS
    bne ScummV5_GetProgramSize__c3_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_OPERANDS_SIZE
    rts
ScummV5_GetProgramSize__c3_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    bne ScummV5_GetProgramSize__c3_slot0
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c3_slot0:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT0
    bne ScummV5_GetProgramSize__c3_slot1
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SLOT0_SIZE
    rts
ScummV5_GetProgramSize__c3_slot1:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT1
    bne ScummV5_GetProgramSize__c3_bit
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SLOT1_SIZE
    rts
ScummV5_GetProgramSize__c3_bit:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_BIT_VARIABLE
    bne ScummV5_GetProgramSize__c4_lifecycle
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_BIT_VARIABLE_SIZE
    rts
ScummV5_GetProgramSize__c4_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    bne ScummV5_GetProgramSize__c4_child2
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_LIFECYCLE_SIZE
    rts
ScummV5_GetProgramSize__c4_child2:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD2
    bne ScummV5_GetProgramSize__c4_child3
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD2_SIZE
    rts
ScummV5_GetProgramSize__c4_child3:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD3
    bne ScummV5_GetProgramSize__c4_child4
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD3_SIZE
    rts
ScummV5_GetProgramSize__c4_child4:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD4
    bne ScummV5_GetProgramSize__c4_capacity
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD4_SIZE
    rts
ScummV5_GetProgramSize__c4_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    bne ScummV5_GetProgramSize__c5_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CAPACITY_SIZE
    rts
ScummV5_GetProgramSize__c5_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    bne ScummV5_GetProgramSize__c5_child5
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c5_child5:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD5
    bne ScummV5_GetProgramSize__c5_child6
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD5_SIZE
    rts
ScummV5_GetProgramSize__c5_child6:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD6
    bne ScummV5_GetProgramSize__c5_child7
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD6_SIZE
    rts
ScummV5_GetProgramSize__c5_child7:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD7
    bne ScummV5_GetProgramSize__c6_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD7_SIZE
    rts
ScummV5_GetProgramSize__c6_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_GetProgramSize__c6_chain10
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c6_chain10:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN10
    bne ScummV5_GetProgramSize__c6_target12
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CHAIN10_SIZE
    rts
ScummV5_GetProgramSize__c6_target12:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET12
    bne ScummV5_GetProgramSize__c6_chain11
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_TARGET12_SIZE
    rts
ScummV5_GetProgramSize__c6_chain11:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN11
    bne ScummV5_GetProgramSize__c6_target13
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CHAIN11_SIZE
    rts
ScummV5_GetProgramSize__c6_target13:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET13
    bne ScummV5_GetProgramSize__c6_missing
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_TARGET13_SIZE
    rts
ScummV5_GetProgramSize__c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_GetProgramSize__c6_capacity
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_MISSING_SIZE
    rts
ScummV5_GetProgramSize__c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_GetProgramSize__s5_binding
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CAPACITY_SIZE
    rts
ScummV5_GetProgramSize__s5_binding:
    .a8
    cmp #SCUMM_C2_FIXTURE_S5_BINDING
    bne ScummV5_GetProgramSize__c7_cursor_bits
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_S5_BINDING_SIZE
    rts
ScummV5_GetProgramSize__c7_cursor_bits:
    .a8
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    bne ScummV5_GetProgramSize__c8_string_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C7_CURSOR_BITS_SIZE
    rts
ScummV5_GetProgramSize__c8_string_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_GetProgramSize__c9_set_var_range
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C8_STRING_OPS_SIZE
    rts
ScummV5_GetProgramSize__c9_set_var_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_GetProgramSize__c10_room_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C9_SET_VAR_RANGE_SIZE
    rts
ScummV5_GetProgramSize__c10_room_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_GetProgramSize__c11_random
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C10_ROOM_OPS_SIZE
    rts
ScummV5_GetProgramSize__c11_random:
    .a8
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_GetProgramSize__c12_pseudo_room
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C11_RANDOM_SIZE
    rts
ScummV5_GetProgramSize__c12_pseudo_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_GetProgramSize__c13_resource_routines
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C12_PSEUDO_ROOM_SIZE
    rts
ScummV5_GetProgramSize__c13_resource_routines:
    .a8
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_GetProgramSize__c14_actor_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C13_RESOURCE_ROUTINES_SIZE
    rts
ScummV5_GetProgramSize__c14_actor_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    bne ScummV5_GetProgramSize__c15_actor_follow_camera
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C14_ACTOR_OPS_SIZE
    rts
ScummV5_GetProgramSize__c15_actor_follow_camera:
    .a8
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_GetProgramSize__c16_set_class
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C15_ACTOR_FOLLOW_CAMERA_SIZE
    rts
ScummV5_GetProgramSize__c16_set_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    bne ScummV5_GetProgramSize__c17_verb_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C16_SET_CLASS_SIZE
    rts
ScummV5_GetProgramSize__c17_verb_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    bne ScummV5_GetProgramSize__c18_expression
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C17_VERB_OPS_SIZE
    rts
ScummV5_GetProgramSize__c18_expression:
    .a8
    cmp #SCUMM_C2_FIXTURE_C18_EXPRESSION
    bne ScummV5_GetProgramSize__c19_cutscene
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C18_EXPRESSION_SIZE
    rts
ScummV5_GetProgramSize__c19_cutscene:
    .a8
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_GetProgramSize__c20_do_sentence
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C19_CUTSCENE_SIZE
    rts
ScummV5_GetProgramSize__c20_do_sentence:
    .a8
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_GetProgramSize__c21_draw_object
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C20_DO_SENTENCE_SIZE
    rts
ScummV5_GetProgramSize__c21_draw_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    bne ScummV5_GetProgramSize__c22_null_room
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C21_DRAW_OBJECT_SIZE
    rts
ScummV5_GetProgramSize__c22_null_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    bne ScummV5_GetProgramSize__c23_print
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C22_NULL_ROOM_SIZE
    rts
ScummV5_GetProgramSize__c23_print:
    .a8
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_GetProgramSize__c24_override_sentinel
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C23_PRINT_SIZE
    rts
ScummV5_GetProgramSize__c24_override_sentinel:
    .a8
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_GetProgramSize__c25_sound_kludge
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C24_OVERRIDE_SENTINEL_SIZE
    rts
ScummV5_GetProgramSize__c25_sound_kludge:
    .a8
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_GetProgramSize__c26_save_restore_verbs
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C25_SOUND_KLUDGE_SIZE
    rts
ScummV5_GetProgramSize__c26_save_restore_verbs:
    .a8
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_GetProgramSize__c28_animate_actor
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C26_SAVE_RESTORE_VERBS_SIZE
    rts
ScummV5_GetProgramSize__c28_animate_actor:
    .a8
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    bne ScummV5_GetProgramSize__c1
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C28_ANIMATE_ACTOR_SIZE
    rts
ScummV5_GetProgramSize__c1:
    rep #$20
    .a16
    lda #SCUMM_V5_CONFORMANCE_PROGRAM_SIZE
    rts

ScummV5_FetchSelectedByteAtX:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    cmp #SCUMM_C2_FIXTURE_EXTENDED
    bne ScummV5_FetchSelectedByteAtX__unknown
    lda.l ScummV5_C2_Program_extended,x
    rts
ScummV5_FetchSelectedByteAtX__unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_UNKNOWN_OPCODE
    bne ScummV5_FetchSelectedByteAtX__bad_variable
    lda.l ScummV5_C2_Program_unknown_opcode,x
    rts
ScummV5_FetchSelectedByteAtX__bad_variable:
    .a8
    cmp #SCUMM_C2_FIXTURE_BAD_VARIABLE
    bne ScummV5_FetchSelectedByteAtX__truncated
    lda.l ScummV5_C2_Program_bad_variable,x
    rts
ScummV5_FetchSelectedByteAtX__truncated:
    .a8
    cmp #SCUMM_C2_FIXTURE_TRUNCATED_OPERAND
    bne ScummV5_FetchSelectedByteAtX__budget
    lda.l ScummV5_C2_Program_truncated_operand,x
    rts
ScummV5_FetchSelectedByteAtX__budget:
    .a8
    cmp #SCUMM_C2_FIXTURE_BUDGET_EXHAUSTION
    bne ScummV5_FetchSelectedByteAtX__divide_zero
    lda.l ScummV5_C2_Program_budget_exhaustion,x
    rts
ScummV5_FetchSelectedByteAtX__divide_zero:
    .a8
    cmp #SCUMM_C2_FIXTURE_DIVISION_BY_ZERO
    bne ScummV5_FetchSelectedByteAtX__jump_escape
    lda.l ScummV5_C2_Program_division_by_zero,x
    rts
ScummV5_FetchSelectedByteAtX__jump_escape:
    .a8
    cmp #SCUMM_C2_FIXTURE_JUMP_ESCAPE
    bne ScummV5_FetchSelectedByteAtX__delay_range
    lda.l ScummV5_C2_Program_jump_escape,x
    rts
ScummV5_FetchSelectedByteAtX__delay_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_DELAY_RANGE
    bne ScummV5_FetchSelectedByteAtX__c3_operands
    lda.l ScummV5_C2_Program_delay_range,x
    rts
ScummV5_FetchSelectedByteAtX__c3_operands:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_OPERANDS
    bne ScummV5_FetchSelectedByteAtX__c3_scheduler
    lda.l ScummV5_C2_Program_c3_operands,x
    rts
ScummV5_FetchSelectedByteAtX__c3_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c3_slot0
    lda.l ScummV5_C2_Program_c3_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c3_slot0:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT0
    bne ScummV5_FetchSelectedByteAtX__c3_slot1
    lda.l ScummV5_C2_Program_c3_slot0,x
    rts
ScummV5_FetchSelectedByteAtX__c3_slot1:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT1
    bne ScummV5_FetchSelectedByteAtX__c3_bit
    lda.l ScummV5_C2_Program_c3_slot1,x
    rts
ScummV5_FetchSelectedByteAtX__c3_bit:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_BIT_VARIABLE
    bne ScummV5_FetchSelectedByteAtX__c4_lifecycle
    lda.l ScummV5_C2_Program_c3_bit_variable,x
    rts
ScummV5_FetchSelectedByteAtX__c4_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    bne ScummV5_FetchSelectedByteAtX__c4_child2
    lda.l ScummV5_C2_Program_c4_lifecycle,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child2:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD2
    bne ScummV5_FetchSelectedByteAtX__c4_child3
    lda.l ScummV5_C2_Program_c4_child2,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child3:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD3
    bne ScummV5_FetchSelectedByteAtX__c4_child4
    lda.l ScummV5_C2_Program_c4_child3,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child4:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD4
    bne ScummV5_FetchSelectedByteAtX__c4_capacity
    lda.l ScummV5_C2_Program_c4_child4,x
    rts
ScummV5_FetchSelectedByteAtX__c4_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    bne ScummV5_FetchSelectedByteAtX__c5_scheduler
    lda.l ScummV5_C2_Program_c4_capacity,x
    rts
ScummV5_FetchSelectedByteAtX__c5_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c5_child5
    lda.l ScummV5_C2_Program_c5_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child5:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD5
    bne ScummV5_FetchSelectedByteAtX__c5_child6
    lda.l ScummV5_C2_Program_c5_child5,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child6:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD6
    bne ScummV5_FetchSelectedByteAtX__c5_child7
    lda.l ScummV5_C2_Program_c5_child6,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child7:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD7
    bne ScummV5_FetchSelectedByteAtX__c6_scheduler
    lda.l ScummV5_C2_Program_c5_child7,x
    rts
ScummV5_FetchSelectedByteAtX__c6_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c6_chain10
    lda.l ScummV5_C2_Program_c6_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c6_chain10:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN10
    bne ScummV5_FetchSelectedByteAtX__c6_target12
    lda.l ScummV5_C2_Program_c6_chain10,x
    rts
ScummV5_FetchSelectedByteAtX__c6_target12:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET12
    bne ScummV5_FetchSelectedByteAtX__c6_chain11
    lda.l ScummV5_C2_Program_c6_target12,x
    rts
ScummV5_FetchSelectedByteAtX__c6_chain11:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN11
    bne ScummV5_FetchSelectedByteAtX__c6_target13
    lda.l ScummV5_C2_Program_c6_chain11,x
    rts
ScummV5_FetchSelectedByteAtX__c6_target13:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET13
    bne ScummV5_FetchSelectedByteAtX__c6_missing
    lda.l ScummV5_C2_Program_c6_target13,x
    rts
ScummV5_FetchSelectedByteAtX__c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_FetchSelectedByteAtX__c6_capacity
    lda.l ScummV5_C2_Program_c6_missing,x
    rts
ScummV5_FetchSelectedByteAtX__c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_FetchSelectedByteAtX__s5_binding
    lda.l ScummV5_C2_Program_c6_capacity,x
    rts
ScummV5_FetchSelectedByteAtX__s5_binding:
    .a8
    cmp #SCUMM_C2_FIXTURE_S5_BINDING
    bne ScummV5_FetchSelectedByteAtX__c7_cursor_bits
    lda.l ScummV5_C2_Program_s5_binding,x
    rts
ScummV5_FetchSelectedByteAtX__c7_cursor_bits:
    .a8
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    bne ScummV5_FetchSelectedByteAtX__c8_string_ops
    lda.l ScummV5_C2_Program_c7_cursor_bits,x
    rts
ScummV5_FetchSelectedByteAtX__c8_string_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_FetchSelectedByteAtX__c9_set_var_range
    lda.l ScummV5_C2_Program_c8_string_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c9_set_var_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_FetchSelectedByteAtX__c10_room_ops
    lda.l ScummV5_C2_Program_c9_set_var_range,x
    rts
ScummV5_FetchSelectedByteAtX__c10_room_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_FetchSelectedByteAtX__c11_random
    lda.l ScummV5_C2_Program_c10_room_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c11_random:
    .a8
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_FetchSelectedByteAtX__c12_pseudo_room
    lda.l ScummV5_C2_Program_c11_random,x
    rts
ScummV5_FetchSelectedByteAtX__c12_pseudo_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_FetchSelectedByteAtX__c13_resource_routines
    lda.l ScummV5_C2_Program_c12_pseudo_room,x
    rts
ScummV5_FetchSelectedByteAtX__c13_resource_routines:
    .a8
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_FetchSelectedByteAtX__c14_actor_ops
    lda.l ScummV5_C2_Program_c13_resource_routines,x
    rts
ScummV5_FetchSelectedByteAtX__c14_actor_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    bne ScummV5_FetchSelectedByteAtX__c15_actor_follow_camera
    lda.l ScummV5_C2_Program_c14_actor_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c15_actor_follow_camera:
    .a8
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_FetchSelectedByteAtX__c16_set_class
    lda.l ScummV5_C2_Program_c15_actor_follow_camera,x
    rts
ScummV5_FetchSelectedByteAtX__c16_set_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    bne ScummV5_FetchSelectedByteAtX__c17_verb_ops
    lda.l ScummV5_C2_Program_c16_set_class,x
    rts
ScummV5_FetchSelectedByteAtX__c17_verb_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    bne ScummV5_FetchSelectedByteAtX__c18_expression
    lda.l ScummV5_C2_Program_c17_verb_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c18_expression:
    .a8
    cmp #SCUMM_C2_FIXTURE_C18_EXPRESSION
    bne ScummV5_FetchSelectedByteAtX__c19_cutscene
    lda.l ScummV5_C2_Program_c18_expression,x
    rts
ScummV5_FetchSelectedByteAtX__c19_cutscene:
    .a8
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_FetchSelectedByteAtX__c20_do_sentence
    lda.l ScummV5_C2_Program_c19_cutscene,x
    rts
ScummV5_FetchSelectedByteAtX__c20_do_sentence:
    .a8
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_FetchSelectedByteAtX__c21_draw_object
    lda.l ScummV5_C2_Program_c20_do_sentence,x
    rts
ScummV5_FetchSelectedByteAtX__c21_draw_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    bne ScummV5_FetchSelectedByteAtX__c22_null_room
    lda.l ScummV5_C2_Program_c21_draw_object,x
    rts
ScummV5_FetchSelectedByteAtX__c22_null_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    bne ScummV5_FetchSelectedByteAtX__c23_print
    lda.l ScummV5_C2_Program_c22_null_room,x
    rts
ScummV5_FetchSelectedByteAtX__c23_print:
    .a8
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_FetchSelectedByteAtX__c24_override_sentinel
    lda.l ScummV5_C2_Program_c23_print,x
    rts
ScummV5_FetchSelectedByteAtX__c24_override_sentinel:
    .a8
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_FetchSelectedByteAtX__c25_sound_kludge
    lda.l ScummV5_C2_Program_c24_override_sentinel,x
    rts
ScummV5_FetchSelectedByteAtX__c25_sound_kludge:
    .a8
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_FetchSelectedByteAtX__c26_save_restore_verbs
    lda.l ScummV5_C2_Program_c25_sound_kludge,x
    rts
ScummV5_FetchSelectedByteAtX__c26_save_restore_verbs:
    .a8
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_FetchSelectedByteAtX__c28_animate_actor
    lda.l ScummV5_C2_Program_c26_save_restore_verbs,x
    rts
ScummV5_FetchSelectedByteAtX__c28_animate_actor:
    .a8
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    bne ScummV5_FetchSelectedByteAtX__c1
    lda.l ScummV5_C2_Program_c28_animate_actor,x
    rts
ScummV5_FetchSelectedByteAtX__c1:
    lda.l ScummV5_Conformance_Program,x
    rts

ScummV5_SetError:
    sep #$20
    .a8
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    rts

.include "../generated/scumm_v5_conformance.inc.pasm"
