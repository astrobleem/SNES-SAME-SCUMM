Same_Video_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_VIDEO_BACKDROP_SHADOW
    sep #$20
    .a8
    lda #$80
    sta.l SAME_VIDEO_DISPLAY_SHADOW
    plp
    rts

; Called only from NMI while the PPU commit window is owned by the kernel.
Same_Video_Commit:
    php
    jsr Same_Dma_ProcessQueue
    sep #$20
    .a8
    stz CGADD
    lda.l SAME_VIDEO_BACKDROP_SHADOW
    sta CGDATA
    lda.l SAME_VIDEO_BACKDROP_SHADOW+1
    sta CGDATA
    plp
    rts

Same_Video_Handle:
    php
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_VIDEO_OP_SET_BACKDROP
    bne Same_Video_Handle__done
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    and #$7FFF
    sta.l SAME_VIDEO_BACKDROP_SHADOW
Same_Video_Handle__done:
    plp
    rts

; K1 transfer fixtures exercise the public semantic request seam.  They live in
; unused PPU memory and never name or configure a DMA channel.
Same_K1_Fixture_QueueInitial:
    php
    rep #$30
    .a16
    .i16
    lda #Same_K1_Vram_Data
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$7000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0010
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue

    rep #$20
    .a16
    lda #Same_K1_Cgram_Data
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$01E0
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0008
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_CGRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue

    rep #$20
    .a16
    lda #Same_K1_Oam_Data
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$0000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0008
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_OAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue

    rep #$20
    .a16
    lda #Same_K1_ForcedBlank_Sentinel
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$7020
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0008
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    plp
    rts

Same_K1_Fixture_QueueDeferred:
    php
    rep #$30
    .a16
    .i16
    lda #Same_K1_ForcedBlank_Data
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$7020
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0008
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM|SAME_DMA_FLAG_FORCED_BLANK
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    plp
    rts

Same_K1_Vram_Data:
    .byte $11,$22,$33,$44,$55,$66,$77,$88,$99,$AA,$BB,$CC,$DD,$EE,$F0,$0F
Same_K1_Cgram_Data:
    .byte $1F,$00,$E0,$03,$00,$7C,$FF,$7F
Same_K1_Oam_Data:
    .byte $18,$F0,$25,$30,$38,$F0,$26,$30
Same_K1_ForcedBlank_Sentinel:
    .byte $00,$00,$00,$00,$00,$00,$00,$00
Same_K1_ForcedBlank_Data:
    .byte $DE,$AD,$BE,$EF,$4B,$31,$00,$01
