; Cold K1 semantic transfer fixture routines for source-bound SCUMM builds.
; The immutable payload remains in bank zero, preserving its DMA source bank.

Same_K1_Fixture_QueueInitial_Far:
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
    jsl Same_K1_Dma_Enqueue_Far

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
    jsl Same_K1_Dma_Enqueue_Far

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
    jsl Same_K1_Dma_Enqueue_Far

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
    jsl Same_K1_Dma_Enqueue_Far
    plp
    rtl

Same_K1_Fixture_QueueDeferred_Far:
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
    jsl Same_K1_Dma_Enqueue_Far
    plp
    rtl
