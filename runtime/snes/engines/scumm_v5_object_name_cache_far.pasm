; Generic SetObjectName cache writer for resolver-enabled builds.
; Kept in the shared far service bank so the full target-neutral cache remains
; enabled without overflowing the main engine bank.
ScummV5_ObjectNameCache_SetName_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C23_SELECTOR
    lda #$80
    jsl ScummV5_ObjectNameCache_FarCall_FetchWordParam
    bcs ScummV5_ObjectNameCache_SetName_Far__error
    rep #$20
    .a16
    sta.l SAME_SCUMM_OBJECT_NAME_OBJECT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_OBJECT_NAME_INDEX
ScummV5_ObjectNameCache_SetName_Far__string:
    .a8
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcs ScummV5_ObjectNameCache_SetName_Far__error
    jsr ScummV5_ObjectNameCache_StoreByte_Far
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_ObjectNameCache_SetName_Far__done
    cmp #$FF
    bne ScummV5_ObjectNameCache_SetName_Far__string
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcs ScummV5_ObjectNameCache_SetName_Far__error
    jsr ScummV5_ObjectNameCache_StoreByte_Far
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_ObjectNameCache_SetName_Far__string
    cmp #$02
    beq ScummV5_ObjectNameCache_SetName_Far__string
    cmp #$03
    beq ScummV5_ObjectNameCache_SetName_Far__string
    cmp #$08
    beq ScummV5_ObjectNameCache_SetName_Far__string
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcs ScummV5_ObjectNameCache_SetName_Far__error
    jsr ScummV5_ObjectNameCache_StoreByte_Far
    jsl ScummV5_Matrix_FarCall_FetchByte
    bcs ScummV5_ObjectNameCache_SetName_Far__error
    jsr ScummV5_ObjectNameCache_StoreByte_Far
    bra ScummV5_ObjectNameCache_SetName_Far__string
ScummV5_ObjectNameCache_SetName_Far__done:
    .a16
    rep #$20
    .a16
    lda.l SAME_SCUMM_OBJECT_NAME_OBJECT
    and #$07FF
    cmp #SAME_SCUMM_OBJECT_NAME_COUNT
    bcs ScummV5_ObjectNameCache_SetName_Far__done_no_cache
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    inc
    sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
ScummV5_ObjectNameCache_SetName_Far__done_no_cache:
    clc
    rtl
ScummV5_ObjectNameCache_SetName_Far__error:
    .a8
    sec
    rtl

ScummV5_ObjectNameCache_StoreByte_Far:
    sep #$20
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_NAME_OBJECT
    and #$07FF
    cmp #SAME_SCUMM_OBJECT_NAME_COUNT
    bcs ScummV5_ObjectNameCache_StoreByte_Far__discard
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C17_PARAM0
    clc
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    rep #$20
    .a16
    and #$00FF
    adc.l SAME_SCUMM_C17_PARAM0
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_OBJECT_NAMES,x
ScummV5_ObjectNameCache_StoreByte_Far__advance:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    cmp #$1F
    bcs ScummV5_ObjectNameCache_StoreByte_Far__done
    inc
    sta.l SAME_SCUMM_OBJECT_NAME_INDEX
ScummV5_ObjectNameCache_StoreByte_Far__done:
    rtl
ScummV5_ObjectNameCache_StoreByte_Far__discard:
    sep #$20
    .a8
    bra ScummV5_ObjectNameCache_StoreByte_Far__advance
