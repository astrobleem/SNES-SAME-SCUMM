; Generated complete BMAPS alias comparison for seven 8 KiB surface bands.
SurfaceProof_TestAliases:
    sep #$20
    .a8
    rep #$10
    .i16
    lda #$00
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    lda #$01
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias1_Compare:
    .a8
    .i16
    lda.l $402000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias1_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias1_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias1_Compare
    lda.l $403FFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $403FFE
    cmp.l $007FFE
    bne SurfaceProof_Alias1_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $403FFE
    lda.l $403FFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $403FFF
    bne SurfaceProof_Alias1_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$01
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias1_Done
SurfaceProof_Alias1_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $403FFE
    bra SurfaceProof_Alias1_Fail
SurfaceProof_Alias1_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias1_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias1_Done:
    .a8
    .i16
    lda #$02
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias2_Compare:
    .a8
    .i16
    lda.l $404000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias2_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias2_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias2_Compare
    lda.l $405FFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $405FFE
    cmp.l $007FFE
    bne SurfaceProof_Alias2_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $405FFE
    lda.l $405FFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $405FFF
    bne SurfaceProof_Alias2_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$02
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias2_Done
SurfaceProof_Alias2_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $405FFE
    bra SurfaceProof_Alias2_Fail
SurfaceProof_Alias2_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias2_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias2_Done:
    .a8
    .i16
    lda #$03
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias3_Compare:
    .a8
    .i16
    lda.l $406000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias3_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias3_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias3_Compare
    lda.l $407FFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $407FFE
    cmp.l $007FFE
    bne SurfaceProof_Alias3_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $407FFE
    lda.l $407FFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $407FFF
    bne SurfaceProof_Alias3_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$04
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias3_Done
SurfaceProof_Alias3_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $407FFE
    bra SurfaceProof_Alias3_Fail
SurfaceProof_Alias3_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias3_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias3_Done:
    .a8
    .i16
    lda #$04
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias4_Compare:
    .a8
    .i16
    lda.l $408000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias4_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias4_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias4_Compare
    lda.l $409FFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $409FFE
    cmp.l $007FFE
    bne SurfaceProof_Alias4_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $409FFE
    lda.l $409FFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $409FFF
    bne SurfaceProof_Alias4_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$08
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias4_Done
SurfaceProof_Alias4_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $409FFE
    bra SurfaceProof_Alias4_Fail
SurfaceProof_Alias4_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias4_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias4_Done:
    .a8
    .i16
    lda #$05
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias5_Compare:
    .a8
    .i16
    lda.l $40A000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias5_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias5_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias5_Compare
    lda.l $40BFFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $40BFFE
    cmp.l $007FFE
    bne SurfaceProof_Alias5_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40BFFE
    lda.l $40BFFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $40BFFF
    bne SurfaceProof_Alias5_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$10
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias5_Done
SurfaceProof_Alias5_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40BFFE
    bra SurfaceProof_Alias5_Fail
SurfaceProof_Alias5_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias5_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias5_Done:
    .a8
    .i16
    lda #$06
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias6_Compare:
    .a8
    .i16
    lda.l $40C000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias6_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias6_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias6_Compare
    lda.l $40DFFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $40DFFE
    cmp.l $007FFE
    bne SurfaceProof_Alias6_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40DFFE
    lda.l $40DFFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $40DFFF
    bne SurfaceProof_Alias6_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$20
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias6_Done
SurfaceProof_Alias6_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40DFFE
    bra SurfaceProof_Alias6_Fail
SurfaceProof_Alias6_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias6_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias6_Done:
    .a8
    .i16
    lda #$07
    sta BMAPS
    ldx #$0000
SurfaceProof_Alias7_Compare:
    .a8
    .i16
    lda.l $40E000,x
    cmp.l $006000,x
    bne SurfaceProof_Alias7_Fail
    cmp.l $806000,x
    bne SurfaceProof_Alias7_Fail
    inx
    cpx #$2000
    bcc SurfaceProof_Alias7_Compare
    lda.l $40FFFE
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$5A
    sta.l $40FFFE
    cmp.l $007FFE
    bne SurfaceProof_Alias7_RestoreDirectFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40FFFE
    lda.l $40FFFF
    sta.l SURFACE_PROOF_ALIAS_SCRATCH
    eor #$A5
    sta.l $007FFF
    cmp.l $40FFFF
    bne SurfaceProof_Alias7_RestoreWindowFail
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
    lda.l SURFACE_PROOF_ALIAS_FLAGS
    ora #$40
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    bra SurfaceProof_Alias7_Done
SurfaceProof_Alias7_RestoreDirectFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $40FFFE
    bra SurfaceProof_Alias7_Fail
SurfaceProof_Alias7_RestoreWindowFail:
    lda.l SURFACE_PROOF_ALIAS_SCRATCH
    sta.l $007FFF
SurfaceProof_Alias7_Fail:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
SurfaceProof_Alias7_Done:
    .a8
    .i16
    stz BMAPS
    lda #$00
    sta.l SURFACE_PROOF_BMAPS_SHADOW
    rts
