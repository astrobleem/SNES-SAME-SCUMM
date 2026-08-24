; ============================================================================
; SAME kernel DMA queue — bounded NMI commit with kernel-owned channel 7
;
; Neutral mechanisms extracted from the current local Monkey and BOR donors:
; publish descriptors last, drain only in the PPU commit window, cap vblank
; bytes, and keep hardware channel selection entirely inside the kernel.
; ============================================================================
SAME_DMA_TYPE_VRAM          = $00
SAME_DMA_TYPE_OAM           = $01
SAME_DMA_TYPE_CGRAM         = $02
SAME_DMA_TYPE_MASK          = $03
SAME_DMA_FLAG_FORCED_BLANK  = $40
SAME_DMA_FLAG_ACTIVE        = $80

; Descriptor offsets: length, target, type/flags, source low, source bank.
SAME_DMA_SLOT_LENGTH        = $00
SAME_DMA_SLOT_TARGET        = $02
SAME_DMA_SLOT_TYPE          = $04
SAME_DMA_SLOT_SOURCE_LO     = $05
SAME_DMA_SLOT_SOURCE_BANK   = $07

Same_Dma_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_DMA_CURRENT_SLOT
    sta.l SAME_DMA_PENDING
    sta.l SAME_DMA_COMMITTED
    sta.l SAME_DMA_DEFERRED_BLANK
    sta.l SAME_DMA_DEFERRED_BUDGET
    sta.l SAME_DMA_REJECTED
    sta.l SAME_DMA_FRAME_BYTES
    ldx #$0000
Same_Dma_Reset__clear:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_DMA_QUEUE,x
    inx
    inx
    cpx #SAME_DMA_QUEUE_SLOTS*SAME_DMA_QUEUE_SLOT_SIZE
    bcc Same_Dma_Reset__clear
    plp
    rts

; Caller fills SAME_DMA_REQUEST_*.  Carry clear means queued; carry set means
; invalid/full.  IRQ masking plus active-last publication prevents NMI from
; observing a half-written descriptor.
Same_Dma_Enqueue:
    php
    sei
    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_REQUEST_LENGTH
    beq Same_Dma_Enqueue__reject
    cmp #SAME_DMA_FRAME_BUDGET+1
    bcs Same_Dma_Enqueue__reject
    sep #$20
    .a8
    lda.l SAME_DMA_REQUEST_TYPE_FLAGS
    and #SAME_DMA_TYPE_MASK
    cmp #$03
    bcs Same_Dma_Enqueue__reject

    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_CURRENT_SLOT
    and #SAME_DMA_QUEUE_MASK
    tax
    ldy #SAME_DMA_QUEUE_SLOTS
Same_Dma_Enqueue__scan:
    sep #$20
    .a8
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    and #SAME_DMA_FLAG_ACTIVE
    beq Same_Dma_Enqueue__found
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_DMA_QUEUE_SLOT_SIZE
    and #SAME_DMA_QUEUE_MASK
    tax
    dey
    bne Same_Dma_Enqueue__scan
    bra Same_Dma_Enqueue__reject

Same_Dma_Enqueue__found:
    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_REQUEST_LENGTH
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_LENGTH,x
    lda.l SAME_DMA_REQUEST_TARGET
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TARGET,x
    lda.l SAME_DMA_REQUEST_SOURCE_LO
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_SOURCE_LO,x
    sep #$20
    .a8
    lda.l SAME_DMA_REQUEST_SOURCE_BANK
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_SOURCE_BANK,x
    lda.l SAME_DMA_REQUEST_TYPE_FLAGS
    ora #SAME_DMA_FLAG_ACTIVE
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    rep #$20
    .a16
    lda.l SAME_DMA_PENDING
    inc
    sta.l SAME_DMA_PENDING
    plp
    clc
    rts

Same_Dma_Enqueue__reject:
    rep #$20
    .a16
    lda.l SAME_DMA_REJECTED
    inc
    sta.l SAME_DMA_REJECTED
    plp
    sec
    rts

; Called only by Same_Video_Commit in NMI or reset-time forced blank.
Same_Dma_ProcessQueue:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_DMA_FRAME_BYTES
    lda.l SAME_DMA_CURRENT_SLOT
Same_Dma_ProcessQueue__next:
    rep #$30
    .a16
    .i16
    and #SAME_DMA_QUEUE_MASK
    sta.l SAME_DMA_CURRENT_SLOT
    tax
    sep #$20
    .a8
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    and #SAME_DMA_FLAG_ACTIVE
    bne Same_Dma_ProcessQueue__active
    brl Same_Dma_ProcessQueue__done
Same_Dma_ProcessQueue__active:
    sep #$20
    .a8

    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    and #SAME_DMA_FLAG_FORCED_BLANK
    beq Same_Dma_ProcessQueue__budget
    lda.l SAME_VIDEO_DISPLAY_SHADOW
    and #$80
    bne Same_Dma_ProcessQueue__budget
    rep #$20
    .a16
    lda.l SAME_DMA_DEFERRED_BLANK
    inc
    sta.l SAME_DMA_DEFERRED_BLANK
    bra Same_Dma_ProcessQueue__done

Same_Dma_ProcessQueue__budget:
    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_FRAME_BYTES
    clc
    adc.l SAME_DMA_QUEUE+SAME_DMA_SLOT_LENGTH,x
    cmp #SAME_DMA_FRAME_BUDGET+1
    bcc Same_Dma_ProcessQueue__dispatch
    lda.l SAME_DMA_DEFERRED_BUDGET
    inc
    sta.l SAME_DMA_DEFERRED_BUDGET
    bra Same_Dma_ProcessQueue__done

Same_Dma_ProcessQueue__dispatch:
    rep #$30
    .a16
    .i16
    sta.l SAME_DMA_FRAME_BYTES
    sep #$20
    .a8
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    and #SAME_DMA_TYPE_MASK
    cmp #SAME_DMA_TYPE_VRAM
    beq Same_Dma_ProcessQueue__vram
    cmp #SAME_DMA_TYPE_OAM
    beq Same_Dma_ProcessQueue__oam
    jsr Same_Dma_TransferCgram
    bra Same_Dma_ProcessQueue__complete
Same_Dma_ProcessQueue__vram:
    sep #$20
    .a8
    jsr Same_Dma_TransferVram
    bra Same_Dma_ProcessQueue__complete
Same_Dma_ProcessQueue__oam:
    sep #$20
    .a8
    jsr Same_Dma_TransferOam

Same_Dma_ProcessQueue__complete:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TYPE,x
    rep #$20
    .a16
    lda.l SAME_DMA_PENDING
    dec
    sta.l SAME_DMA_PENDING
    lda.l SAME_DMA_COMMITTED
    inc
    sta.l SAME_DMA_COMMITTED
    lda.l SAME_DMA_CURRENT_SLOT
    clc
    adc #SAME_DMA_QUEUE_SLOT_SIZE
    brl Same_Dma_ProcessQueue__next

Same_Dma_ProcessQueue__done:
    plp
    rts

Same_Dma_LoadCommon:
    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_SOURCE_LO,x
    sta A1T7L
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_LENGTH,x
    sta DAS7L
    sep #$20
    .a8
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_SOURCE_BANK,x
    sta A1B7
    rts

Same_Dma_TransferVram:
    jsr Same_Dma_LoadCommon
    sep #$20
    .a8
    lda #$80
    sta VMAIN
    lda #$01
    sta DMAP7
    lda #$18
    sta BBAD7
    rep #$20
    .a16
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TARGET,x
    lsr
    sta VMADDL
    sep #$20
    .a8
    lda #$80
    sta MDMAEN
    rts

Same_Dma_TransferOam:
    jsr Same_Dma_LoadCommon
    sep #$20
    .a8
    lda #$00
    sta DMAP7
    lda #$04
    sta BBAD7
    rep #$20
    .a16
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TARGET,x
    lsr
    sta OAMADDL
    sep #$20
    .a8
    lda #$80
    sta MDMAEN
    rts

Same_Dma_TransferCgram:
    jsr Same_Dma_LoadCommon
    sep #$20
    .a8
    lda #$00
    sta DMAP7
    lda #$22
    sta BBAD7
    rep #$20
    .a16
    lda.l SAME_DMA_QUEUE+SAME_DMA_SLOT_TARGET,x
    lsr
    sep #$20
    .a8
    sta CGADD
    lda #$80
    sta MDMAEN
    rts
