; Source-class membership shares the existing far engine service bank.
; No additional WRAM, execution personality, or unbounded lookup.
ScummV5_C16_SourceTestClass_Far:
    jsl ScummV5_C16_QueryMask_Far
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_C16_CLASS
    and #$007F
    dec
    cmp #$0010
    bcs ScummV5_C16_SourceTestClass__high
    tax
    pla
    bra ScummV5_C16_SourceTestClass__shift
ScummV5_C16_SourceTestClass__high:
    .a16
    .i16
    and #$000F
    tax
    pla
    tya
ScummV5_C16_SourceTestClass__shift:
    .a16
    .i16
    cpx #$0000
    beq ScummV5_C16_SourceTestClass__bit
    lsr
    dex
    bra ScummV5_C16_SourceTestClass__shift
ScummV5_C16_SourceTestClass__bit:
    lsr
    rtl


ScummV5_C16_SourceEnsureRecord_Far:
    jsl ScummV5_C16_FindRecord_Far
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_C16_SourceEnsureRecord__ready
    lda.l SAME_SCUMM_C16_FREE_OFFSET
    cmp #$FFFF
    beq ScummV5_C16_SourceEnsureRecord__full
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    phx
    jsl ScummV5_ObjectClass_QueryInitial_Far
    plx
    sta.l SAME_SCUMM_C16_RECORDS+4,x
    tya
    sta.l SAME_SCUMM_C16_RECORDS+6,x
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l SAME_SCUMM_C16_RECORDS+2,x
    lda #$0001
    sta.l SAME_SCUMM_C16_RECORDS,x
ScummV5_C16_SourceEnsureRecord__ready:
    clc
    rtl
ScummV5_C16_SourceEnsureRecord__full:
    sec
    rtl

