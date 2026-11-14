; Source cutscene callbacks use the SAME ordinary allocator/nested scheduler
; as StartScript. These are tail entries, not JSL helpers: no orphan return
; frame may remain when the allocator yields to checked storage.
ScummV5_Cutscene_ClearArgs_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Cutscene_ClearArgs__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_ARGS,x
    inx
    inx
    cpx #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcc ScummV5_Cutscene_ClearArgs__loop
    rtl

ScummV5_Cutscene_StartCallback_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_VARIABLES+(35 * 2)
    beq ScummV5_Cutscene_Callback__absent
    cmp #$0100
    bcs ScummV5_Cutscene_Callback__invalid
    sep #$20
    .a8
    pha
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C19_SCRIPT_INDEX
    pla
    bra ScummV5_Cutscene_Callback__dispatch
ScummV5_Cutscene_EndCallback_Far:
    jsl ScummV5_Cutscene_ClearArgs_Far
    rep #$20
    .a16
    lda.l SAME_SCUMM_C19_ARGUMENT0
    sta.l SAME_SCUMM_C4_ARGS
    lda.l SAME_SCUMM_VARIABLES+(36 * 2)
    beq ScummV5_Cutscene_Callback__absent
    cmp #$0100
    bcs ScummV5_Cutscene_Callback__invalid
    sep #$20
    .a8
ScummV5_Cutscene_Callback__dispatch:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    sta.l SAME_SCUMM_LAST_OPCODE
    jml ScummV5_Op_StartScript__normal_args_done
ScummV5_Cutscene_Callback__absent:
    .a16
    jml ScummV5_Engine_Frame__next
ScummV5_Cutscene_Callback__invalid:
    .a16
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
    jsl ScummV5_Camera_FarCall_SetError
    jml ScummV5_Op__error
