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
    lda #$00
    sta.l SAME_VIDEO_BG1_CONFIG_VALID
    sta.l SAME_VIDEO_BG1_MODE
    sta.l SAME_VIDEO_BG1_SCREEN
    sta.l SAME_VIDEO_BG1_CHARS
    sta.l SAME_VIDEO_MAIN_LAYERS
.include "../generated/video_backend_reset.inc.pasm"
.include "../generated/video_overlay_reset.inc.pasm"
    plp
    rts

; Called only from NMI while the PPU commit window is owned by the kernel.
Same_Video_Commit:
    php
.include "../generated/video_backend_commit.inc.pasm"
    jsr Same_Dma_ProcessQueue
    sep #$20
    .a8
    lda.l SAME_VIDEO_BG1_CONFIG_VALID
    beq Same_Video_Commit__palette
    lda.l SAME_VIDEO_BG1_MODE
    sta BGMODE
    lda.l SAME_VIDEO_BG1_SCREEN
    sta BG1SC
    lda.l SAME_VIDEO_BG1_CHARS
    sta BG12NBA
    lda.l SAME_VIDEO_MAIN_LAYERS
    sta TM
Same_Video_Commit__palette:
    lda.l SAME_VIDEO_DISPLAY_SHADOW
    sta INIDISP
    stz CGADD
    lda.l SAME_VIDEO_BACKDROP_SHADOW
    sta CGDATA
    lda.l SAME_VIDEO_BACKDROP_SHADOW+1
    sta CGDATA
    plp
    rts

; NMI-owned BG1 setup request. A16 packs BGMODE in the low byte and BG1SC in
; the high byte; X16 packs BG12NBA low and TM high. The caller never touches
; PPU registers directly. The shadows are applied by Same_Video_Commit.
Same_Video_ConfigureBg1:
    php
    rep #$30
    .a16
    .i16
    sta.l SAME_VIDEO_BG1_MODE
    txa
    sta.l SAME_VIDEO_BG1_CHARS
    sep #$20
    .a8
    lda #$01
    sta.l SAME_VIDEO_BG1_CONFIG_VALID
    plp
    rts

; Generic BGR555 backdrop/palette-zero shadow request. Useful when a loaded
; palette owns color zero; the NMI commit keeps CGRAM entry 0 consistent.
Same_Video_SetBackdrop:
    php
    rep #$20
    .a16
    and #$7FFF
    sta.l SAME_VIDEO_BACKDROP_SHADOW
    plp
    rts

; NMI-owned display request. Clients change only the shadow; Same_Video_Commit
; applies INIDISP in the kernel's PPU commit window.
Same_Video_SetDisplay:
    php
    sep #$20
    .a8
    sta.l SAME_VIDEO_DISPLAY_SHADOW
    plp
    rts

Same_Video_Handle:
    php
.include "../generated/video_overlay_service.inc.pasm"
.include "../generated/video_backend_service.inc.pasm"
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
.if SAME_VIDEO_BACKEND_LEGACY
.if !SAME_BUILD_SCUMM_M23A
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
.else
; Source-bound SCUMM builds keep the K1 queueing routines in their far-code
; bank so the canonical interpreter does not collide with the bank-0 header.
Same_K1_Dma_Enqueue_Far:
    jsr Same_Dma_Enqueue
    rtl
.endif

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
.endif

.if SAME_VIDEO_BACKEND_MODE3
; Far backend code remains outside bank zero, but reuses the one production
; event and DMA implementation through these bounded call adapters.
Same_Mode3_Dma_Enqueue_Far:
    jsr Same_Dma_Enqueue
    rtl
Same_Mode3_Video_Commit_Far:
    jsr Same_Video_Commit
    rtl
Same_Mode3_Event_Stage_Far:
    jsr Same_Event_StageEngine
    rtl
Same_Mode3_Event_Push_Far:
    jsr Same_Event_Push
    rtl
Same_Mode3_Kernel_DrainEvents_Far:
    php
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_SERVICE_CALLS
    inc
    sta.l SAME_VIDEO_DIAG_SERVICE_CALLS
    sep #$20
    .a8
    .if SAME_VIDEO_OVERLAY_BG2
    lda #$70
    sta BG12NBA
    .endif
    jsr Same_Kernel_DrainEvents
    rep #$20
    .a16
    lda.l SAME_EVENT_HEAD
    sta.l SAME_VIDEO_DIAG_SERVICE_LAST_HEAD
    lda.l SAME_EVENT_TAIL
    sta.l SAME_VIDEO_DIAG_SERVICE_LAST_TAIL
    lda.l SAME_EVENT_COUNT
    sta.l SAME_VIDEO_DIAG_SERVICE_LAST_COUNT
Same_Mode3_Kernel_DrainEvents_Far__done:
    plp
    rtl
; Neutral alias to the selected backend's synchronous service entry.
Same_VideoSurface_ServiceEvents_Far = Same_Mode3_Kernel_DrainEvents_Far
.if SAME_BUILD_SCUMM_ROOM_VISUAL
ScummV5_Visual_RequestRoom_Far:
    .if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR
    jsl ScummV5_M23A_RequestRoom_FarEntry
    .else
    jsr ScummV5_M23A_RequestRoom
    .endif
    rtl
ScummV5_Visual_ResourceReady_Far:
    .if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR
    jsl ScummV5_M23A_ResourceReady_FarEntry
    .else
    jsr ScummV5_M23A_ResourceReady
    .endif
    rtl
.endif
.endif
