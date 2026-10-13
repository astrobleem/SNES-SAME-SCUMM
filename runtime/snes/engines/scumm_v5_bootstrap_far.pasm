; Optional, source-neutral cold-start diagnostic. Keep the body in the far
; service bank so enabling it does not consume the fixed bank-zero header gap.
ScummV5_AuthenticBootstrap_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    sep #$20
    .a8
    lda.l SAME_SCUMM_AUTHENTIC_BOOTSTRAP_STARTED
    beq ScummV5_AuthenticBootstrap_Far__not_started
    jmp ScummV5_AuthenticBootstrap_Far__unchanged
ScummV5_AuthenticBootstrap_Far__not_started:
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    beq ScummV5_AuthenticBootstrap_Far__phase_idle
    jmp ScummV5_AuthenticBootstrap_Far__unchanged
ScummV5_AuthenticBootstrap_Far__phase_idle:
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$FF
    beq ScummV5_AuthenticBootstrap_Far__record_empty
    jmp ScummV5_AuthenticBootstrap_Far__unchanged
ScummV5_AuthenticBootstrap_Far__record_empty:
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_AuthenticBootstrap_Far__unchanged

    lda #SCUMM_V5_AUTHENTIC_BOOT_SCRIPT
    .if SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
    ; The first activation follows the same canonical resolver path as every
    ; later StartScript; no static selector is manufactured for the bootstrap.
    jsl ScummV5_Resident_ResolveGlobalScript_Far
    .else
    jsl ScummV5_M23A_ResolveGlobalScript_Far_Address
    .endif
    bcs ScummV5_AuthenticBootstrap_Far__resolved
    jmp ScummV5_AuthenticBootstrap_Far__error

ScummV5_AuthenticBootstrap_Far__resolved:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM+1
    lda #SCUMM_V5_AUTHENTIC_BOOT_SCRIPT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER+1
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS+1
    lda #SCUMM_WIO_GLOBAL
    sta.l SAME_SCUMM_C4_SLOT_WHERE+1
    lda #$00
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS+1
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC+1
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT+1
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE+1
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT+1
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC+2
    sta.l SAME_SCUMM_C4_SLOT_DELAY+2
    ldx #$0040
ScummV5_AuthenticBootstrap_Far__clear_locals:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    cpx #$0080
    bcc ScummV5_AuthenticBootstrap_Far__clear_locals
    lda #SCUMM_V5_AUTHENTIC_BOOT_ARGUMENT
    sta.l SAME_SCUMM_C4_SLOT_LOCALS+$0040
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C22_NULL_SCENE
    sta.l SAME_SCUMM_AUTHENTIC_BOOTSTRAP_STARTED
    lda #$00
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    sta.l SAME_SCUMM_C22_OBJECT_COUNT
    sta.l SAME_SCUMM_C22_QUEUE_COUNT
ScummV5_AuthenticBootstrap_Far__unchanged:
    rep #$30
    .a16
    .i16
    plx
    pla
    plp
    clc
    rtl
ScummV5_AuthenticBootstrap_Far__error:
    rep #$30
    .a16
    .i16
    plx
    pla
    plp
    sec
    rtl
