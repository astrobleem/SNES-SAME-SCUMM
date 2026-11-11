; Production Mode-3 indexed-surface backend. Selected only with the reset-held
; SA-1/BW-RAM carrier. All active-display PPU writes remain in the existing
; NMI-owned DMA service.
.bank 15
.org $8000

Same_Mode3_BitMasks:
    .byte $01,$02,$04,$08,$10,$20,$40,$80
Same_Mode3_InverseBitMasks:
    .byte $FE,$FD,$FB,$F7,$EF,$DF,$BF,$7F
Same_Mode3_ScreenBitMasks:
    .byte $80,$40,$20,$10,$08,$04,$02,$01

Same_Mode3_Reset_Far:
    php
    jsl Same_Mode3_Retained_Reset_Far
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
Same_Mode3_Reset__clear_staging:
    .a16
    sta.l SAME_MODE3_CANDIDATE_TILES,x
    inx
    inx
    .if SAME_BUILD_SCUMM_MSU1_PROGRAMS && SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    ; Live room metadata owns the fixture/reserved tail after publication.
    cpx #SAME_MODE3_FIXTURE-SAME_MODE3_CANDIDATE_TILES
    .else
    cpx #SAME_MODE3_FIXTURE+SAME_MODE3_FIXTURE_SIZE-SAME_MODE3_CANDIDATE_TILES
    .endif
    bcc Same_Mode3_Reset__clear_staging
    ldx #$0012
Same_Mode3_Reset__clear_control:
    .a16
    sta.l SAME_BWRAM_BACKEND_BASE,x
    inx
    inx
    cpx #SAME_MODE3_CONTROL_SIZE
    bcc Same_Mode3_Reset__clear_control
    ; Clear the bounded service-pipeline witness in the unused tail of the
    ; backend reservation.  It is diagnostic state only and never part of the
    ; SCUMM surface contract.
    ldx #$0000
Same_Mode3_Reset__clear_video_diag:
    .a16
    .i16
    sta.l SAME_VIDEO_DIAG_BASE,x
    inx
    cpx #$0046
    bcc Same_Mode3_Reset__clear_video_diag
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #SAME_BWRAM_VIDEO_SURFACE_STATE-SAME_BWRAM_BACKEND_BASE
Same_Mode3_Reset__clear_surface_facade:
    .a16
    .i16
    sta.l SAME_BWRAM_BACKEND_BASE,x
    inx
    inx
    cpx #SAME_BWRAM_VIDEO_SURFACE_STATE-SAME_BWRAM_BACKEND_BASE+SAME_VIDEO_SURFACE_STATE_SIZE
    bcc Same_Mode3_Reset__clear_surface_facade
    .endif
    sep #$20
    .a8
    lda #SAME_VIDEO_BACKEND_ID
    sta.l SAME_MODE3_CONTROL_BACKEND_ID
    lda #SAME_MODE3_STATE_IDLE
    sta.l SAME_MODE3_CONTROL_STATE
    stz BGMODE
    lda #$03
    sta BGMODE
    .if SAME_VIDEO_OVERLAY_BG2
    lda #$70
    .else
    lda #$79 ; 64x32 map at byte $F000, 920 character slots below $E600
    .endif
    sta BG1SC
    stz BG12NBA
    .if SAME_VIDEO_OVERLAY_BG2
    ; The selected backend owns the overlay character-base policy.  Keep it
    ; paired with the mode-3 reset rather than requiring an engine write.
    lda #$70
    sta BG12NBA
    .endif
    stz MOSAIC
    stz CGWSEL
    stz CGADSUB
    stz SETINI
    stz TM
    stz TS
    stz BG1HOFS
    stz BG1HOFS
    ; Match the independently accepted Phase-6A Mode-3 realization: the
    ; normal BG fetch origin is one scanline ahead of logical surface row 0.
    lda #$FF
    sta BG1VOFS
    lda #$03
    sta BG1VOFS
    lda #$01
    sta TM
    plp
    rtl

; Queue the immutable fixed tilemap through the production DMA queue, then
; realize generation one through the same conversion/queue/commit state
; machine used after display enable.
Same_Mode3_Boot_Realize_Far:
    php
    .if SAME_BUILD_SCUMM_ROOM_VISUAL && !SAME_BUILD_M24RB && !SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
    jsl ScummV5_InitialVisual_Bootstrap_Far
    .endif
    rep #$30
    .a16
    .i16
    .if SAME_VIDEO_OVERLAY_BG2
    lda #Same_Mode3_StaticTilemap
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$E000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    .else
    lda #Same_Mode3_RetainedTilemap
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$F000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    .endif
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM|SAME_DMA_FLAG_FORCED_BLANK
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcc Same_Mode3_Boot_Realize__first_map
    brl Same_Mode3_Boot_Realize__error
Same_Mode3_Boot_Realize__first_map:
    .a8
    .if SAME_VIDEO_OVERLAY_BG2 == 0
    rep #$20
    .a16
    lda #Same_Mode3_RetainedTilemap
    clc
    adc #$0800
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$F800
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM|SAME_DMA_FLAG_FORCED_BLANK
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcc Same_Mode3_Boot_Realize__map_ready
    brl Same_Mode3_Boot_Realize__error
Same_Mode3_Boot_Realize__map_ready:
    .a8
    .endif
    jsl Same_Mode3_Video_Commit_Far
    ; M24R-B starts SCUMM's room lifecycle separately and deliberately does
    ; not request the legacy initial visual here.  The static tilemap DMA is
    ; nevertheless complete after this commit; waiting for committed surface
    ; generation one would manufacture a backend error before any room visual
    ; can be published.  Room-install/camera publication owns that later
    ; surface generation.
    .if SAME_BUILD_M24RB || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
    plp
    rtl
    .endif
    rep #$20
    .a16
    lda #$4000
    sta.l SAME_MODE3_WORK_TIMEOUT
Same_Mode3_Boot_Realize__loop:
    jsr Same_Mode3_Step
    jsl Same_Mode3_Video_Commit_Far
    rep #$20
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0001
    bne Same_Mode3_Boot_Realize__continue
    lda.l SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI
    bne Same_Mode3_Boot_Realize__continue
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    beq Same_Mode3_Boot_Realize__done
Same_Mode3_Boot_Realize__continue:
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_TIMEOUT
    dec
    sta.l SAME_MODE3_WORK_TIMEOUT
    bne Same_Mode3_Boot_Realize__loop
Same_Mode3_Boot_Realize__error:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_MODE3_CONTROL_LAST_ERROR
    lda #SAME_MODE3_STATE_ERROR
    sta.l SAME_MODE3_CONTROL_STATE
Same_Mode3_Boot_Realize__done:
    plp
    rtl

Same_Mode3_Handle_Far:
    php
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_VIDEO_OP_SURFACE_DIRTY
    bne Same_Mode3_Handle__check_palette_diag
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_DIRTY_HANDLES
    inc
    sta.l SAME_VIDEO_DIAG_DIRTY_HANDLES
    sep #$20
    .a8
    bra Same_Mode3_Handle__dirty
Same_Mode3_Handle__check_palette_diag:
    sep #$20
    .a8
    cmp #SAME_VIDEO_OP_PALETTE_WRITE
    bne Same_Mode3_Handle__check_present_diag
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_PALETTE_HANDLES
    inc
    sta.l SAME_VIDEO_DIAG_PALETTE_HANDLES
    sep #$20
    .a8
    bra Same_Mode3_Handle__palette
Same_Mode3_Handle__check_present_diag:
    sep #$20
    .a8
    cmp #SAME_VIDEO_OP_PRESENT
    bne Same_Mode3_Handle__other
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_PRESENT_HANDLES
    inc
    sta.l SAME_VIDEO_DIAG_PRESENT_HANDLES
    sep #$20
    .a8
    bra Same_Mode3_Handle__present
Same_Mode3_Handle__other:
    sep #$20
    .a8
    cmp #SAME_VIDEO_OP_SET_BACKDROP
    bne Same_Mode3_Handle__done
    lda #$02
    sta.l SAME_MODE3_CONTROL_LAST_ERROR
    bra Same_Mode3_Handle__done
Same_Mode3_Handle__dirty:
    jsr Same_Mode3_HandleDirty
    bra Same_Mode3_Handle__done
Same_Mode3_Handle__palette:
    jsr Same_Mode3_HandlePalette
    bra Same_Mode3_Handle__done
Same_Mode3_Handle__present:
    jsr Same_Mode3_HandlePresent
Same_Mode3_Handle__done:
    plp
    rtl

Same_Mode3_Step_Far:
    php
    rep #$20
    .a16
    lda.l SAME_VIDEO_DIAG_BACKEND_STEPS
    inc
    sta.l SAME_VIDEO_DIAG_BACKEND_STEPS
    jsr Same_Mode3_Step
    plp
    rtl

; The selected backend owns a small bounded per-frame conversion budget.  Keep
; the budget here so the kernel/SCUMM layers only invoke the neutral generated
; frame hook.
Same_Mode3_Frame_Far:
    php
    jsl Same_Mode3_Step_Far
    jsl Same_Mode3_Step_Far
    jsl Same_Mode3_Step_Far
    jsl Same_Mode3_Step_Far
    plp
    rtl

Same_Mode3_Step:
    sep #$20
    .a8
    .if SAME_VIDEO_OVERLAY_BG2
    ; Reassert the selected overlay character base at the backend frame
    ; boundary; SCUMM never needs to touch this hardware register.
    lda #$70
    sta BG12NBA
    .endif
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_CONVERTING
    beq Same_Mode3_Step__converting
    cmp #SAME_MODE3_STATE_QUEUEING
    beq Same_Mode3_Step__queueing
    cmp #SAME_MODE3_STATE_WAITING_DMA
    beq Same_Mode3_Step__waiting
    cmp #SAME_MODE3_STATE_COMPLETE
    beq Same_Mode3_Step__complete
    rts
Same_Mode3_Step__converting:
    jsr Same_Mode3_ProcessPaletteCandidates
    jsr Same_Mode3_ProcessTileCandidates
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    bne Same_Mode3_Step__return
    lda.l SAME_MODE3_CONTROL_SCAN_PALETTE
    cmp #$0100
    bcc Same_Mode3_Step__return
    sep #$20
    .a8
    lda #SAME_MODE3_STATE_QUEUEING
    sta.l SAME_MODE3_CONTROL_STATE
    rts
Same_Mode3_Step__queueing:
    jsr Same_Mode3_QueueBatch
    rts
Same_Mode3_Step__waiting:
    jsr Same_Mode3_ObserveBatch
    rts
Same_Mode3_Step__complete:
    jsr Same_Mode3_Retained_Complete
    bcs Same_Mode3_Step__return
    sep #$20
    .a8
    lda #$01
    sta.l SAME_BWRAM_CONTROL_SURFACE_VALID
    sta.l SAME_BWRAM_CONTROL_TILE_VALID
    sta.l SAME_BWRAM_CONTROL_CGRAM_VALID
    rep #$20
    .a16
    lda.l SAME_BWRAM_CONTROL_PENDING_GENERATION
    sta.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    lda.l SAME_MODE3_CONTROL_PENDING_GENERATION_HI
    sta.l SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    lda #SAME_MODE3_STATE_IDLE
    sta.l SAME_MODE3_CONTROL_STATE
Same_Mode3_Step__return:
    rts

; --------------------------------------------------------------------------
; Packet decoding

Same_Mode3_HandleDirty:
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    beq Same_Mode3_HandleDirty__unlocked
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_REJECTED_DIRTY
    inc
    sta.l SAME_MODE3_CONTROL_REJECTED_DIRTY
    rts
Same_Mode3_HandleDirty__unlocked:
    rep #$30
    .a16
    .i16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    bne Same_Mode3_HandleDirty__width_ok
    brl Same_Mode3_HandleDirty__reject
Same_Mode3_HandleDirty__width_ok:
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    bne Same_Mode3_HandleDirty__height_ok
    brl Same_Mode3_HandleDirty__reject
Same_Mode3_HandleDirty__height_ok:
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp #$0100
    bcc Same_Mode3_HandleDirty__x_ok
    brl Same_Mode3_HandleDirty__done
Same_Mode3_HandleDirty__x_ok:
    .a16
    sta.l SAME_MODE3_WORK_X0
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    cmp #$00E0
    bcc Same_Mode3_HandleDirty__y_ok
    brl Same_Mode3_HandleDirty__done
Same_Mode3_HandleDirty__y_ok:
    .a16
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sec
    sbc.l SAME_MODE3_WORK_X0
    cmp.l SAME_MODE3_WORK_TEMP
    bcc Same_Mode3_HandleDirty__x_clamped
    lda.l SAME_MODE3_WORK_TEMP
Same_Mode3_HandleDirty__x_clamped:
    .a16
    clc
    adc.l SAME_MODE3_WORK_X0
    dec
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_X1
    lda.l SAME_MODE3_WORK_X0
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_X0
    lda #$00E0
    sec
    sbc.l SAME_MODE3_WORK_Y0
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    cmp.l SAME_MODE3_WORK_TEMP
    bcc Same_Mode3_HandleDirty__y_size
    lda.l SAME_MODE3_WORK_TEMP
Same_Mode3_HandleDirty__y_size:
    clc
    adc.l SAME_MODE3_WORK_Y0
    dec
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_Y1
    lda.l SAME_MODE3_WORK_Y0
    lsr
    lsr
    lsr
    sta.l SAME_MODE3_WORK_Y0
Same_Mode3_HandleDirty__row:
    .a16
    lda.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_RUN_COUNT
    lda.l MODE3_R_ACTIVE
    and #$00FF
    beq Same_Mode3_HandleDirty__row_end_ready
    lda.l SAME_MODE3_WORK_Y0
    cmp #$0018
    bcs Same_Mode3_HandleDirty__row_end_ready
    lda.l MODE3_R_NEXT
    and #$0007
    beq Same_Mode3_HandleDirty__row_end_ready
    lda.l SAME_MODE3_WORK_RUN_COUNT
    inc
    sta.l SAME_MODE3_WORK_RUN_COUNT
Same_Mode3_HandleDirty__row_end_ready:
    .a16
    lda.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_COLUMN
Same_Mode3_HandleDirty__column:
    .a16
    jsr Same_Mode3_Retained_MapDirtyTile
    sta.l SAME_MODE3_WORK_TILE
    lda.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_SetCandidateTile
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_COLUMN
    cmp.l SAME_MODE3_WORK_RUN_COUNT
    beq Same_Mode3_HandleDirty__next_row
    inc
    sta.l SAME_MODE3_WORK_COLUMN
    bra Same_Mode3_HandleDirty__column
Same_Mode3_HandleDirty__next_row:
    lda.l SAME_MODE3_WORK_Y0
    cmp.l SAME_MODE3_WORK_Y1
    beq Same_Mode3_HandleDirty__done
    inc
    sta.l SAME_MODE3_WORK_Y0
    bra Same_Mode3_HandleDirty__row
Same_Mode3_HandleDirty__done:
    rts
Same_Mode3_HandleDirty__reject:
    lda.l SAME_MODE3_CONTROL_REJECTED_DIRTY
    inc
    sta.l SAME_MODE3_CONTROL_REJECTED_DIRTY
    rts

Same_Mode3_HandlePalette:
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    beq Same_Mode3_HandlePalette__unlocked
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_REJECTED_PALETTE
    inc
    sta.l SAME_MODE3_CONTROL_REJECTED_PALETTE
    rts
Same_Mode3_HandlePalette__unlocked:
    rep #$30
    .a16
    .i16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    ora.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    bne Same_Mode3_HandlePalette__reject
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp #$0100
    bcs Same_Mode3_HandlePalette__reject
    sta.l SAME_MODE3_WORK_INDEX
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    beq Same_Mode3_HandlePalette__reject
    clc
    adc.l SAME_MODE3_WORK_INDEX
    bcs Same_Mode3_HandlePalette__reject
    cmp #$0101
    bcs Same_Mode3_HandlePalette__reject
    sta.l SAME_MODE3_WORK_LIMIT
Same_Mode3_HandlePalette__loop:
    lda.l SAME_MODE3_WORK_INDEX
    jsr Same_Mode3_SetCandidatePalette
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    cmp.l SAME_MODE3_WORK_LIMIT
    bcc Same_Mode3_HandlePalette__loop
    rts
Same_Mode3_HandlePalette__reject:
    lda.l SAME_MODE3_CONTROL_REJECTED_PALETTE
    inc
    sta.l SAME_MODE3_CONTROL_REJECTED_PALETTE
    rts

Same_Mode3_HandlePresent:
    sep #$20
    .a8
    lda.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    beq Same_Mode3_HandlePresent__state
    brl Same_Mode3_HandlePresent__reject
Same_Mode3_HandlePresent__state:
    .a8
    lda.l SAME_MODE3_CONTROL_STATE
    cmp #SAME_MODE3_STATE_IDLE
    beq Same_Mode3_HandlePresent__args
    brl Same_Mode3_HandlePresent__reject
Same_Mode3_HandlePresent__args:
    .a8
    lda.l MODE3_R_ACTIVE
    beq Same_Mode3_HandlePresent__retained_ready
    lda.l MODE3_R_PHASE
    cmp #$01
    bne Same_Mode3_HandlePresent__retained_ready
    lda.l MODE3_R_VALIDATED
    cmp #$01
    beq Same_Mode3_HandlePresent__retained_ready
    brl Same_Mode3_HandlePresent__reject
Same_Mode3_HandlePresent__retained_ready:
    .a8
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    ora.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    beq Same_Mode3_HandlePresent__arg1_valid
    brl Same_Mode3_HandlePresent__reject16
Same_Mode3_HandlePresent__arg1_valid:
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    ora.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    bne Same_Mode3_HandlePresent__arg0_valid
    brl Same_Mode3_HandlePresent__reject16
Same_Mode3_HandlePresent__arg0_valid:
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    cmp.l SAME_MODE3_CONTROL_COMMITTED_GENERATION_HI
    bcs Same_Mode3_HandlePresent__generation_hi_valid
    brl Same_Mode3_HandlePresent__reject16
Same_Mode3_HandlePresent__generation_hi_valid:
    bne Same_Mode3_HandlePresent__accept
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    bcs Same_Mode3_HandlePresent__generation_lo_not_less
    brl Same_Mode3_HandlePresent__reject16
Same_Mode3_HandlePresent__generation_lo_not_less:
    bne Same_Mode3_HandlePresent__generation_valid
    brl Same_Mode3_HandlePresent__reject16
Same_Mode3_HandlePresent__generation_valid:
Same_Mode3_HandlePresent__accept:
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_BWRAM_CONTROL_PENDING_GENERATION
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    sta.l SAME_MODE3_CONTROL_PENDING_GENERATION_HI
    lda #$0000
    sta.l SAME_MODE3_CONTROL_SCAN_TILE
    sta.l SAME_MODE3_CONTROL_SCAN_PALETTE
    sta.l SAME_MODE3_CONTROL_INFLIGHT_COUNT
    lda.l MODE3_R_ACTIVE
    and #$00FF
    beq Same_Mode3_HandlePresent__reset_counts
    lda.l MODE3_R_PHASE
    and #$00FF
    cmp #$0001
    beq Same_Mode3_HandlePresent__keep_restored
Same_Mode3_HandlePresent__reset_counts:
    .a16
    lda #$0000
    sta.l SAME_MODE3_CONTROL_PENDING_COUNT
    sta.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    sta.l SAME_MODE3_CONTROL_UNCHANGED_COUNT
Same_Mode3_HandlePresent__keep_restored:
    .a16
    lda #$0000
    sta.l SAME_MODE3_CONTROL_QUEUED_TILE_BYTES
    sta.l SAME_MODE3_CONTROL_QUEUED_CGRAM_BYTES
    sta.l SAME_MODE3_CONTROL_BATCH_COUNT
    sta.l SAME_MODE3_CONTROL_LAST_ERROR
    ; A full presentation with an invalid tile shadow must upload every
    ; character tile, including all-zero tiles. Otherwise blank SC5VIS tiles
    ; can be elided as "unchanged" in the shadow while VRAM still contains
    ; power-on/stale bytes. A producer that overwrites the aliased tile shadow
    ; invalidates TILE_VALID at the surface replacement boundary.
    sep #$20
    .a8
    lda.l SAME_BWRAM_CONTROL_TILE_VALID
    bne Same_Mode3_HandlePresent__tile_shadow_valid
    lda #$FF
    ldx #$0000
Same_Mode3_HandlePresent__invalidate_all_tiles:
    .a8
    .i16
    cpx #$0070 ; 896 cold visible characters, no unvalidated guard bytes
    bcc Same_Mode3_HandlePresent__cold_candidate
    lda #$00
Same_Mode3_HandlePresent__cold_candidate:
    .a8
    sta.l SAME_MODE3_CANDIDATE_TILES,x
    inx
    cpx #SAME_MODE3_CANDIDATE_TILES_SIZE
    bcc Same_Mode3_HandlePresent__invalidate_all_tiles
    rep #$20
    .a16
    lda #$0380 ; cold visible tile count
    sta.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    bra Same_Mode3_HandlePresent__tile_candidates_ready
Same_Mode3_HandlePresent__tile_shadow_valid:
    rep #$20
    .a16
Same_Mode3_HandlePresent__tile_candidates_ready:
    lda.l SAME_MODE3_CONTROL_ACCEPTED_PRESENT
    inc
    sta.l SAME_MODE3_CONTROL_ACCEPTED_PRESENT
    sep #$20
    .a8
    lda #$01
    sta.l SAME_MODE3_CONTROL_SURFACE_LOCKED
    lda #SAME_MODE3_STATE_CONVERTING
    sta.l SAME_MODE3_CONTROL_STATE
    rts
Same_Mode3_HandlePresent__reject:
    rep #$20
    .a16
Same_Mode3_HandlePresent__reject16:
    lda.l SAME_MODE3_CONTROL_REJECTED_PRESENT
    inc
    sta.l SAME_MODE3_CONTROL_REJECTED_PRESENT
    rts

; --------------------------------------------------------------------------
; Candidate and pending bitsets

Same_Mode3_SetCandidateTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_TILES,x
    and.l SAME_MODE3_WORK_MASK
    bne Same_Mode3_SetCandidateTile__done
    lda.l SAME_MODE3_CANDIDATE_TILES,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_CANDIDATE_TILES,x
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
Same_Mode3_SetCandidateTile__done:
    rts

Same_Mode3_SetCandidatePalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_PALETTE,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_CANDIDATE_PALETTE,x
    rts

; A16 index input. Carry set if the named bit is present.
Same_Mode3_TestCandidateTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_TILES,x
    and.l SAME_MODE3_WORK_MASK
    beq Same_Mode3_TestCandidateTile__no
    sec
    rts
Same_Mode3_TestCandidateTile__no:
    clc
    rts

Same_Mode3_ClearCandidateTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_InverseBitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_TILES,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_CANDIDATE_TILES,x
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    dec
    sta.l SAME_MODE3_CONTROL_CANDIDATE_COUNT
    rts

Same_Mode3_SetPendingTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_TILES,x
    and.l SAME_MODE3_WORK_MASK
    bne Same_Mode3_SetPendingTile__done
    lda.l SAME_MODE3_PENDING_TILES,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_PENDING_TILES,x
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_PENDING_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_PENDING_COUNT
Same_Mode3_SetPendingTile__done:
    rts

; Input index A16, carry set when pending and not already in flight.
Same_Mode3_TestAvailableTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_TILES,x
    and.l SAME_MODE3_WORK_MASK
    beq Same_Mode3_TestAvailableTile__no
    lda.l SAME_MODE3_INFLIGHT_TILES,x
    and.l SAME_MODE3_WORK_MASK
    bne Same_Mode3_TestAvailableTile__no
    sec
    rts
Same_Mode3_TestAvailableTile__no:
    clc
    rts

Same_Mode3_SetInflightTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_INFLIGHT_TILES,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_INFLIGHT_TILES,x
    rts

Same_Mode3_ClearPendingInflightTile:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_InverseBitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_TILES,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_PENDING_TILES,x
    lda.l SAME_MODE3_INFLIGHT_TILES,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_INFLIGHT_TILES,x
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_PENDING_COUNT
    dec
    sta.l SAME_MODE3_CONTROL_PENDING_COUNT
    rts

; Palette bitset helpers mirror tile helpers but have no public count.
Same_Mode3_TestCandidatePalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    beq Same_Mode3_TestCandidatePalette__no
    sec
    rts
Same_Mode3_TestCandidatePalette__no:
    clc
    rts

Same_Mode3_ClearCandidatePalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_InverseBitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_CANDIDATE_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_CANDIDATE_PALETTE,x
    rts

Same_Mode3_SetPendingPalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_PALETTE,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_PENDING_PALETTE,x
    rts

Same_Mode3_TestAvailablePalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    beq Same_Mode3_TestAvailablePalette__no
    lda.l SAME_MODE3_INFLIGHT_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    bne Same_Mode3_TestAvailablePalette__no
    sec
    rts
Same_Mode3_TestAvailablePalette__no:
    clc
    rts

Same_Mode3_SetInflightPalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_BitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_INFLIGHT_PALETTE,x
    ora.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_INFLIGHT_PALETTE,x
    rts

Same_Mode3_ClearPendingInflightPalette:
    rep #$30
    .a16
    .i16
    sta.l SAME_MODE3_WORK_INDEX
    and #$0007
    tax
    sep #$20
    .a8
    lda.l Same_Mode3_InverseBitMasks,x
    sta.l SAME_MODE3_WORK_MASK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_PENDING_PALETTE,x
    lda.l SAME_MODE3_INFLIGHT_PALETTE,x
    and.l SAME_MODE3_WORK_MASK
    sta.l SAME_MODE3_INFLIGHT_PALETTE,x
    rts

; --------------------------------------------------------------------------
; Palette and tile conversion

; Skip an empty bitset byte in one operation instead of testing its eight
; bits separately. A16 is the current in-range index; C=1 retains that index
; for the existing per-bit test, C=0 advances to the next byte. Bounds remain
; owned by the callers. X is scratch; Y/DBR/stack and all bitsets are preserved.
; Available bytes exclude in-flight DMA exactly like TestAvailable*.
Same_Mode3_SeekCandidateTileByte:
    .a16
    .i16
    pha
    lsr
    lsr
    lsr
    tax
    lda.l SAME_MODE3_CANDIDATE_TILES,x
    and #$00FF
    bne Same_Mode3_SeekCandidateTileByte__nonempty
    pla
    and #$FFF8
    clc
    adc #$0008
    clc
    rts
Same_Mode3_SeekCandidateTileByte__nonempty:
    .a16
    pla
    sec
    rts

Same_Mode3_SeekCandidatePaletteByte:
    .a16
    .i16
    pha
    lsr
    lsr
    lsr
    tax
    lda.l SAME_MODE3_CANDIDATE_PALETTE,x
    and #$00FF
    bne Same_Mode3_SeekCandidatePaletteByte__nonempty
    pla
    and #$FFF8
    clc
    adc #$0008
    clc
    rts
Same_Mode3_SeekCandidatePaletteByte__nonempty:
    .a16
    pla
    sec
    rts

Same_Mode3_SeekAvailableTileByte:
    .a16
    .i16
    pha
    lsr
    lsr
    lsr
    tax
    lda.l SAME_MODE3_INFLIGHT_TILES,x
    eor #$FFFF
    and.l SAME_MODE3_PENDING_TILES,x
    and #$00FF
    bne Same_Mode3_SeekAvailableTileByte__nonempty
    pla
    and #$FFF8
    clc
    adc #$0008
    clc
    rts
Same_Mode3_SeekAvailableTileByte__nonempty:
    .a16
    pla
    sec
    rts

Same_Mode3_SeekAvailablePaletteByte:
    .a16
    .i16
    pha
    lsr
    lsr
    lsr
    tax
    lda.l SAME_MODE3_INFLIGHT_PALETTE,x
    eor #$FFFF
    and.l SAME_MODE3_PENDING_PALETTE,x
    and #$00FF
    bne Same_Mode3_SeekAvailablePaletteByte__nonempty
    pla
    and #$FFF8
    clc
    adc #$0008
    clc
    rts
Same_Mode3_SeekAvailablePaletteByte__nonempty:
    .a16
    pla
    sec
    rts


Same_Mode3_ProcessPaletteCandidates:
    rep #$30
    .a16
    .i16
Same_Mode3_ProcessPaletteCandidates__next:
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_PALETTE
    cmp #$0100
    bcs Same_Mode3_ProcessPaletteCandidates__done
    jsr Same_Mode3_SeekCandidatePaletteByte
    sta.l SAME_MODE3_CONTROL_SCAN_PALETTE
    bcc Same_Mode3_ProcessPaletteCandidates__next
    jsr Same_Mode3_TestCandidatePalette
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_PALETTE
    bcc Same_Mode3_ProcessPaletteCandidates__advance
    jsr Same_Mode3_ConvertPaletteEntry
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_PALETTE
    jsr Same_Mode3_ClearCandidatePalette
Same_Mode3_ProcessPaletteCandidates__advance:
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_PALETTE
    inc
    sta.l SAME_MODE3_CONTROL_SCAN_PALETTE
    bra Same_Mode3_ProcessPaletteCandidates__next
Same_Mode3_ProcessPaletteCandidates__done:
    rts

Same_Mode3_ConvertPaletteEntry:
    sta.l SAME_MODE3_WORK_INDEX
    asl
    clc
    adc.l SAME_MODE3_WORK_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_MODE3_LIVE_PALETTE,x
    lsr
    lsr
    lsr
    rep #$20
    .a16
    and #$001F
    sta.l SAME_MODE3_WORK_PALETTE_WORD
    sep #$20
    .a8
    lda.l SAME_MODE3_LIVE_PALETTE+$01,x
    lsr
    lsr
    lsr
    rep #$20
    .a16
    and #$001F
    asl
    asl
    asl
    asl
    asl
    ora.l SAME_MODE3_WORK_PALETTE_WORD
    sta.l SAME_MODE3_WORK_PALETTE_WORD
    sep #$20
    .a8
    lda.l SAME_MODE3_LIVE_PALETTE+$02,x
    lsr
    lsr
    lsr
    rep #$20
    .a16
    and #$001F
    xba
    asl
    asl
    ora.l SAME_MODE3_WORK_PALETTE_WORD
    sta.l SAME_MODE3_WORK_PALETTE_WORD
    lda.l SAME_MODE3_WORK_INDEX
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_BWRAM_CONTROL_CGRAM_VALID
    beq Same_Mode3_ConvertPaletteEntry__changed
    rep #$20
    .a16
    lda.l SAME_BWRAM_CGRAM_SHADOW_BASE,x
    cmp.l SAME_MODE3_WORK_PALETTE_WORD
    beq Same_Mode3_ConvertPaletteEntry__done
Same_Mode3_ConvertPaletteEntry__changed:
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_PALETTE_WORD
    sta.l SAME_BWRAM_CGRAM_SHADOW_BASE,x
    lda.l SAME_MODE3_WORK_INDEX
    jsr Same_Mode3_SetPendingPalette
Same_Mode3_ConvertPaletteEntry__done:
    rts

Same_Mode3_ProcessTileCandidates:
    rep #$30
    .a16
    .i16
    lda #SAME_VIDEO_ACTIVE_CONVERT_TILE_BUDGET
    sta.l SAME_MODE3_WORK_LIMIT
Same_Mode3_ProcessTileCandidates__scan:
    .a16
    lda.l SAME_MODE3_WORK_LIMIT
    beq Same_Mode3_ProcessTileCandidates__done
    lda.l SAME_MODE3_CONTROL_SCAN_TILE
    cmp #SAME_MODE3_TILE_COUNT
    bcs Same_Mode3_ProcessTileCandidates__done
    jsr Same_Mode3_SeekCandidateTileByte
    sta.l SAME_MODE3_CONTROL_SCAN_TILE
    bcc Same_Mode3_ProcessTileCandidates__scan
    jsr Same_Mode3_TestCandidateTile
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_TILE
    bcc Same_Mode3_ProcessTileCandidates__advance
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_EncodeViewportTile
    jsr Same_Mode3_CommitViewportTile
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_ClearCandidateTile
    lda.l SAME_MODE3_WORK_LIMIT
    dec
    sta.l SAME_MODE3_WORK_LIMIT
Same_Mode3_ProcessTileCandidates__advance:
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_SCAN_TILE
    inc
    sta.l SAME_MODE3_CONTROL_SCAN_TILE
    bra Same_Mode3_ProcessTileCandidates__scan
Same_Mode3_ProcessTileCandidates__done:
    rts

; Exact 8bpp plane order, gathered one row at a time. Eight shifts replace
; each plane byte completely, including zero pixels; no scratch clear needed.
; X is the source pixel offset, Y the planar row offset. The eight temporary
; planes alias only backend-owned rectangle scratch ($18..$1F), which is dead
; after candidate construction. No actor/cache/surface allocation is borrowed.
; DBR=$41 makes absolute ROL legal (65816 has no absolute-long ROL).
Same_Mode3_TileScratchLow = SAME_MODE3_TILE_SCRATCH & $FFFF
Same_Mode3_TileShadowLow = SAME_BWRAM_TILE_SHADOW_BASE & $FFFF
Same_Mode3_RowPlanes = SAME_MODE3_WORK_X0 & $FFFF
Same_Mode3_EncodeTile:
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_TILE
    pha
    and #$001F
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_SOURCE
    pla
    and #$FFE0
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_SOURCE
    tax
    ldy #$0000
Same_Mode3_EncodeTile__row:
    sep #$20
    .a8
    lda #$08
    sta.l SAME_MODE3_WORK_COLUMN
Same_Mode3_EncodeTile__column:
    lda.l SAME_BWRAM_SURFACE_BASE,x
    lsr
    rol.w Same_Mode3_RowPlanes+0
    lsr
    rol.w Same_Mode3_RowPlanes+1
    lsr
    rol.w Same_Mode3_RowPlanes+2
    lsr
    rol.w Same_Mode3_RowPlanes+3
    lsr
    rol.w Same_Mode3_RowPlanes+4
    lsr
    rol.w Same_Mode3_RowPlanes+5
    lsr
    rol.w Same_Mode3_RowPlanes+6
    lsr
    rol.w Same_Mode3_RowPlanes+7
    inx
    lda.l SAME_MODE3_WORK_COLUMN
    dec
    sta.l SAME_MODE3_WORK_COLUMN
    bne Same_Mode3_EncodeTile__column
    phx
    tyx
    lda.l SAME_MODE3_WORK_X0+0
    sta.l SAME_MODE3_TILE_SCRATCH+$00,x
    lda.l SAME_MODE3_WORK_X0+1
    sta.l SAME_MODE3_TILE_SCRATCH+$01,x
    lda.l SAME_MODE3_WORK_X0+2
    sta.l SAME_MODE3_TILE_SCRATCH+$10,x
    lda.l SAME_MODE3_WORK_X0+3
    sta.l SAME_MODE3_TILE_SCRATCH+$11,x
    lda.l SAME_MODE3_WORK_X0+4
    sta.l SAME_MODE3_TILE_SCRATCH+$20,x
    lda.l SAME_MODE3_WORK_X0+5
    sta.l SAME_MODE3_TILE_SCRATCH+$21,x
    lda.l SAME_MODE3_WORK_X0+6
    sta.l SAME_MODE3_TILE_SCRATCH+$30,x
    lda.l SAME_MODE3_WORK_X0+7
    sta.l SAME_MODE3_TILE_SCRATCH+$31,x
    plx
    iny
    iny
    cpy #$0010
    beq Same_Mode3_EncodeTile__done
    rep #$20
    .a16
    txa
    clc
    adc #$00F8
    tax
    brl Same_Mode3_EncodeTile__row
Same_Mode3_EncodeTile__done:
    plb
    rep #$30
    .a16
    .i16
    rts

; Compare/copy aligned words within the existing bank-$41 tile shadow. Both
; regions are even-sized and bounded by the tile index; no speculative read
; crosses the 64-byte tile. DBR is restored before the pending-bit helper.
Same_Mode3_CommitEncodedTile:
    phb
    sep #$20
    .a8
    lda #$41
    pha
    plb
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_TILE
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_TEMP
    tax
    ldy #$0000
    sep #$20
    .a8
    lda.l SAME_BWRAM_CONTROL_TILE_VALID
    beq Same_Mode3_CommitEncodedTile__copy
    rep #$20
    .a16
Same_Mode3_CommitEncodedTile__compare:
    .a16
    .i16
    lda.w Same_Mode3_TileScratchLow,y
    cmp.w Same_Mode3_TileShadowLow,x
    bne Same_Mode3_CommitEncodedTile__copy
    inx
    inx
    iny
    iny
    cpy #$0040
    bcc Same_Mode3_CommitEncodedTile__compare
    lda.l SAME_MODE3_CONTROL_UNCHANGED_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_UNCHANGED_COUNT
    plb
    rts
Same_Mode3_CommitEncodedTile__copy:
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_TEMP
    tax
    ldy #$0000
Same_Mode3_CommitEncodedTile__copy_loop:
    .a16
    .i16
    lda.w Same_Mode3_TileScratchLow,y
    sta.w Same_Mode3_TileShadowLow,x
    inx
    inx
    iny
    iny
    cpy #$0040
    bcc Same_Mode3_CommitEncodedTile__copy_loop
    plb
    lda.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_SetPendingTile
    rep #$20
    .a16
    lda.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    rts

; --------------------------------------------------------------------------
; Deterministic palette-first queueing and commit observation

Same_Mode3_QueueBatch:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_MODE3_CONTROL_BATCH_BYTES
    sta.l SAME_MODE3_CONTROL_RECORD_COUNT
    sta.l SAME_MODE3_CONTROL_INFLIGHT_COUNT
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_QueueBatch__palette_scan:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0100
    bcc Same_Mode3_QueueBatch__palette_in_range
    brl Same_Mode3_QueueBatch__tile_begin
Same_Mode3_QueueBatch__palette_in_range:
    jsr Same_Mode3_SeekAvailablePaletteByte
    sta.l SAME_MODE3_WORK_INDEX
    bcs Same_Mode3_QueueBatch__palette_byte_nonempty
    brl Same_Mode3_QueueBatch__palette_scan
Same_Mode3_QueueBatch__palette_byte_nonempty:
    jsr Same_Mode3_TestAvailablePalette
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    bcs Same_Mode3_QueueBatch__palette_run
    inc
    sta.l SAME_MODE3_WORK_INDEX
    bra Same_Mode3_QueueBatch__palette_scan
Same_Mode3_QueueBatch__palette_run:
    .a16
    sta.l SAME_MODE3_WORK_RUN_START
    lda #$0000
    sta.l SAME_MODE3_WORK_RUN_COUNT
Same_Mode3_QueueBatch__palette_extend:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0100
    bcs Same_Mode3_QueueBatch__palette_queue
    jsr Same_Mode3_TestAvailablePalette
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    bcc Same_Mode3_QueueBatch__palette_queue
    lda.l SAME_MODE3_WORK_RUN_COUNT
    inc
    sta.l SAME_MODE3_WORK_RUN_COUNT
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    bra Same_Mode3_QueueBatch__palette_extend
Same_Mode3_QueueBatch__palette_queue:
    .a16
    lda.l SAME_MODE3_WORK_RUN_COUNT
    ; A pending-bit transition can be observed between the scan and the
    ; extension test (for example while an earlier palette batch is being
    ; retired).  Never enqueue a zero-length DMA request or retry the same
    ; index forever; advance the bounded scan cursor and continue.
    beq Same_Mode3_QueueBatch__palette_empty_run
    asl
    sta.l SAME_MODE3_WORK_TEMP
    clc
    adc.l SAME_MODE3_CONTROL_BATCH_BYTES
    cmp #SAME_DMA_FRAME_BUDGET+1
    bcs Same_Mode3_QueueBatch__tile_begin
    jsr Same_Mode3_QueuePaletteRun
    bcc Same_Mode3_QueueBatch__palette_queued
    brl Same_Mode3_QueueBatch__finish
Same_Mode3_QueueBatch__palette_empty_run:
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    brl Same_Mode3_QueueBatch__palette_scan
Same_Mode3_QueueBatch__palette_queued:
    .a16
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    cmp #SAME_DMA_QUEUE_SLOTS
    bcc Same_Mode3_QueueBatch__palette_more
    brl Same_Mode3_QueueBatch__finish
Same_Mode3_QueueBatch__palette_more:
    brl Same_Mode3_QueueBatch__palette_scan
Same_Mode3_QueueBatch__tile_begin:
    rep #$30
    .a16
    .i16
    ; Keep a palette batch distinct from character DMA. This retains strict
    ; palette-first ordering and gives each PPU target one committed batch.
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    beq Same_Mode3_QueueBatch__tiles_only
    brl Same_Mode3_QueueBatch__finish
Same_Mode3_QueueBatch__tiles_only:
    .a16
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_QueueBatch__tile_scan:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #SAME_MODE3_TILE_COUNT
    bcc Same_Mode3_QueueBatch__tile_in_range
    brl Same_Mode3_QueueBatch__finish
Same_Mode3_QueueBatch__tile_in_range:
    jsr Same_Mode3_SeekAvailableTileByte
    sta.l SAME_MODE3_WORK_INDEX
    bcs Same_Mode3_QueueBatch__tile_byte_nonempty
    brl Same_Mode3_QueueBatch__tile_scan
Same_Mode3_QueueBatch__tile_byte_nonempty:
    jsr Same_Mode3_TestAvailableTile
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    bcs Same_Mode3_QueueBatch__tile_run
    inc
    sta.l SAME_MODE3_WORK_INDEX
    brl Same_Mode3_QueueBatch__tile_scan
Same_Mode3_QueueBatch__tile_run:
    .a16
    sta.l SAME_MODE3_WORK_RUN_START
    lda #$0000
    sta.l SAME_MODE3_WORK_RUN_COUNT
Same_Mode3_QueueBatch__tile_extend:
    .a16
    ; A DMA descriptor cannot cross the split guard-column shadow.
    lda.l SAME_MODE3_WORK_RUN_COUNT
    beq Same_Mode3_QueueBatch__tile_source_ok
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0380
    beq Same_Mode3_QueueBatch__tile_queue
    cmp #$038B
    beq Same_Mode3_QueueBatch__tile_queue
Same_Mode3_QueueBatch__tile_source_ok:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #SAME_MODE3_TILE_COUNT
    bcs Same_Mode3_QueueBatch__tile_queue
    jsr Same_Mode3_TestAvailableTile
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    bcc Same_Mode3_QueueBatch__tile_queue
    lda.l SAME_MODE3_CONTROL_BATCH_BYTES
    clc
    adc #$0040
    sta.l SAME_MODE3_WORK_TEMP
    lda.l SAME_MODE3_WORK_RUN_COUNT
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_TEMP
    cmp #SAME_DMA_FRAME_BUDGET+1
    bcs Same_Mode3_QueueBatch__tile_queue
    lda.l SAME_MODE3_WORK_RUN_COUNT
    inc
    sta.l SAME_MODE3_WORK_RUN_COUNT
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    bra Same_Mode3_QueueBatch__tile_extend
Same_Mode3_QueueBatch__tile_queue:
    .a16
    lda.l SAME_MODE3_WORK_RUN_COUNT
    beq Same_Mode3_QueueBatch__finish
    jsr Same_Mode3_QueueTileRun
    bcs Same_Mode3_QueueBatch__finish
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    cmp #SAME_DMA_QUEUE_SLOTS
    bcs Same_Mode3_QueueBatch__finish
    brl Same_Mode3_QueueBatch__tile_scan
Same_Mode3_QueueBatch__finish:
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    beq Same_Mode3_QueueBatch__no_batch
    jsl Same_Dma_GetFence_Far
    sta.l SAME_MODE3_CONTROL_EXPECTED_DMA
    lda.l SAME_MODE3_CONTROL_BATCH_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_BATCH_COUNT
    sep #$20
    .a8
    lda #SAME_MODE3_STATE_WAITING_DMA
    sta.l SAME_MODE3_CONTROL_STATE
    rts
Same_Mode3_QueueBatch__no_batch:
    lda.l SAME_MODE3_CONTROL_PENDING_COUNT
    bne Same_Mode3_QueueBatch__retry
    jsr Same_Mode3_AnyPendingPalette
    bcs Same_Mode3_QueueBatch__retry
    sep #$20
    .a8
    lda #SAME_MODE3_STATE_COMPLETE
    sta.l SAME_MODE3_CONTROL_STATE
    rts
Same_Mode3_QueueBatch__retry:
    lda.l SAME_MODE3_CONTROL_RETRY_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_RETRY_COUNT
    rts

Same_Mode3_QueuePaletteRun:
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_RUN_START
    asl
    clc
    adc #SAME_BWRAM_CGRAM_SHADOW_BASE_LO
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda.l SAME_MODE3_WORK_RUN_START
    asl
    sta.l SAME_DMA_REQUEST_TARGET
    lda.l SAME_MODE3_WORK_RUN_COUNT
    asl
    sta.l SAME_DMA_REQUEST_LENGTH
    sta.l SAME_MODE3_WORK_TEMP
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_CGRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Mode3_QueuePaletteRun__failed
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_RUN_START
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_QueuePaletteRun__mark:
    lda.l SAME_MODE3_WORK_INDEX
    jsr Same_Mode3_SetInflightPalette
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    lda.l SAME_MODE3_WORK_RUN_START
    clc
    adc.l SAME_MODE3_WORK_RUN_COUNT
    cmp.l SAME_MODE3_WORK_INDEX
    bne Same_Mode3_QueuePaletteRun__mark
    lda #SAME_MODE3_INFLIGHT_TYPE_PALETTE
    jsr Same_Mode3_RecordInflight
    lda.l SAME_MODE3_WORK_TEMP
    clc
    adc.l SAME_MODE3_CONTROL_BATCH_BYTES
    sta.l SAME_MODE3_CONTROL_BATCH_BYTES
    lda.l SAME_MODE3_CONTROL_QUEUED_CGRAM_BYTES
    clc
    adc.l SAME_MODE3_WORK_TEMP
    sta.l SAME_MODE3_CONTROL_QUEUED_CGRAM_BYTES
    clc
    rts
Same_Mode3_QueuePaletteRun__failed:
    rep #$20
    .a16
    sec
    rts

Same_Mode3_QueueTileRun:
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_WORK_RUN_START
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    sta.l SAME_DMA_REQUEST_TARGET
    lda.l SAME_MODE3_WORK_RUN_COUNT
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_DMA_REQUEST_LENGTH
    sta.l SAME_MODE3_WORK_TEMP
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_RUN_START
    cmp #$0380
    bcc Same_Mode3_QueueTileRun__source_ready
    sec
    sbc #$0380
    cmp #$000B
    bcs Same_Mode3_QueueTileRun__tail
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_BWRAM_RETAINED_GUARD_HEAD&$FFFF
    bra Same_Mode3_QueueTileRun__guard_source
Same_Mode3_QueueTileRun__tail:
    .a16
    sec
    sbc #$000B
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc #SAME_MODE3_GUARD_TAIL&$FFFF
Same_Mode3_QueueTileRun__guard_source:
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    sep #$20
    .a8
    lda #$40
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
Same_Mode3_QueueTileRun__source_ready:
    sep #$20
    .a8
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsl Same_Mode3_Dma_Enqueue_Far
    bcs Same_Mode3_QueueTileRun__failed
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_RUN_START
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_QueueTileRun__mark:
    lda.l SAME_MODE3_WORK_INDEX
    jsr Same_Mode3_SetInflightTile
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    lda.l SAME_MODE3_WORK_RUN_START
    clc
    adc.l SAME_MODE3_WORK_RUN_COUNT
    cmp.l SAME_MODE3_WORK_INDEX
    bne Same_Mode3_QueueTileRun__mark
    lda #SAME_MODE3_INFLIGHT_TYPE_TILE
    jsr Same_Mode3_RecordInflight
    lda.l SAME_MODE3_WORK_TEMP
    clc
    adc.l SAME_MODE3_CONTROL_BATCH_BYTES
    sta.l SAME_MODE3_CONTROL_BATCH_BYTES
    lda.l SAME_MODE3_CONTROL_QUEUED_TILE_BYTES
    clc
    adc.l SAME_MODE3_WORK_TEMP
    sta.l SAME_MODE3_CONTROL_QUEUED_TILE_BYTES
    clc
    rts
Same_Mode3_QueueTileRun__failed:
    rep #$20
    .a16
    sec
    rts

Same_Mode3_RecordInflight:
    sta.l SAME_MODE3_WORK_DESC_TYPE
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    sta.l SAME_MODE3_WORK_INDEX
    asl
    asl
    asl
    tax
    lda.l SAME_MODE3_WORK_DESC_TYPE
    sta.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_TYPE,x
    lda.l SAME_MODE3_WORK_RUN_START
    sta.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_FIRST,x
    lda.l SAME_MODE3_WORK_RUN_COUNT
    sta.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_COUNT,x
    lda.l SAME_MODE3_WORK_TEMP
    sta.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_BYTES,x
    lda.l SAME_MODE3_CONTROL_RECORD_COUNT
    inc
    sta.l SAME_MODE3_CONTROL_RECORD_COUNT
    sta.l SAME_MODE3_CONTROL_INFLIGHT_COUNT
    rts

Same_Mode3_ObserveBatch:
    rep #$30
    .a16
    .i16
    lda.l SAME_DMA_COMMITTED
    sec
    sbc.l SAME_MODE3_CONTROL_EXPECTED_DMA
    bpl Same_Mode3_ObserveBatch__ready
    brl Same_Mode3_ObserveBatch__done
Same_Mode3_ObserveBatch__ready:
    .a16
    lda #$0000
    sta.l SAME_MODE3_WORK_ROW
Same_Mode3_ObserveBatch__record:
    lda.l SAME_MODE3_WORK_ROW
    cmp.l SAME_MODE3_CONTROL_RECORD_COUNT
    bcs Same_Mode3_ObserveBatch__complete
    sta.l SAME_MODE3_WORK_TEMP
    asl
    asl
    asl
    tax
    lda.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_FIRST,x
    sta.l SAME_MODE3_WORK_RUN_START
    lda.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_COUNT,x
    sta.l SAME_MODE3_WORK_RUN_COUNT
    lda.l SAME_MODE3_INFLIGHT_RECORDS+SAME_MODE3_INFLIGHT_TYPE,x
    sta.l SAME_MODE3_WORK_DESC_TYPE
Same_Mode3_ObserveBatch__item:
    .a16
    lda.l SAME_MODE3_WORK_DESC_TYPE
    tax
    lda.l SAME_MODE3_WORK_RUN_START
    cpx #SAME_MODE3_INFLIGHT_TYPE_PALETTE
    beq Same_Mode3_ObserveBatch__palette
    jsr Same_Mode3_ClearPendingInflightTile
    bra Same_Mode3_ObserveBatch__item_done
Same_Mode3_ObserveBatch__palette:
    jsr Same_Mode3_ClearPendingInflightPalette
Same_Mode3_ObserveBatch__item_done:
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_RUN_START
    inc
    sta.l SAME_MODE3_WORK_RUN_START
    lda.l SAME_MODE3_WORK_RUN_COUNT
    dec
    sta.l SAME_MODE3_WORK_RUN_COUNT
    bne Same_Mode3_ObserveBatch__item
    lda.l SAME_MODE3_WORK_ROW
    inc
    sta.l SAME_MODE3_WORK_ROW
    bra Same_Mode3_ObserveBatch__record
Same_Mode3_ObserveBatch__complete:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_MODE3_CONTROL_INFLIGHT_COUNT
    sta.l SAME_MODE3_CONTROL_RECORD_COUNT
    sep #$20
    .a8
    lda #SAME_MODE3_STATE_QUEUEING
    sta.l SAME_MODE3_CONTROL_STATE
Same_Mode3_ObserveBatch__done:
    rts

Same_Mode3_AnyPendingPalette:
    rep #$30
    .a16
    .i16
    ldx #$0000
Same_Mode3_AnyPendingPalette__loop:
    sep #$20
    .a8
    lda.l SAME_MODE3_PENDING_PALETTE,x
    bne Same_Mode3_AnyPendingPalette__yes
    inx
    cpx #SAME_MODE3_PALETTE_BITSET_BYTES
    bcc Same_Mode3_AnyPendingPalette__loop
    clc
    rts
Same_Mode3_AnyPendingPalette__yes:
    sec
    rts

; --------------------------------------------------------------------------
; Copyright-free production fixture

Same_Mode3_Fixture_Boot_Far:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_MODE3_FIXTURE_PHASE
    sta.l SAME_MODE3_FIXTURE_DONE
    ldx #$0000
Same_Mode3_Fixture_Boot__surface:
    .a16
    txa
    sta.l SAME_MODE3_FIXTURE_TEMP
    and #$00FF
    sta.l SAME_MODE3_FIXTURE_ROW
    lda.l SAME_MODE3_FIXTURE_TEMP
    xba
    and #$00FF
    clc
    adc.l SAME_MODE3_FIXTURE_ROW
    sep #$20
    .a8
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$20
    .a16
    inx
    cpx #SAME_BWRAM_SURFACE_SIZE
    bcc Same_Mode3_Fixture_Boot__surface
    ldy #$0000
Same_Mode3_Fixture_Boot__palette:
    tya
    sta.l SAME_MODE3_FIXTURE_TEMP
    asl
    clc
    adc.l SAME_MODE3_FIXTURE_TEMP
    tax
    sep #$20
    .a8
    tya
    sta.l SAME_MODE3_LIVE_PALETTE,x
    eor #$55
    sta.l SAME_MODE3_LIVE_PALETTE+$01,x
    tya
    eor #$FF
    sta.l SAME_MODE3_LIVE_PALETTE+$02,x
    rep #$20
    .a16
    iny
    cpy #$0100
    bcc Same_Mode3_Fixture_Boot__palette
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_LIMIT
    lda #$00E0
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
    lda #$0100
    sta.l SAME_MODE3_WORK_LIMIT
    jsr Same_Mode3_Fixture_PushPalette
    lda #$0001
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0001
    sta.l SAME_MODE3_FIXTURE_PHASE
    plp
    rtl

Same_Mode3_Fixture_Frame_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_FIXTURE_PHASE
    cmp #$0001
    bne Same_Mode3_Fixture_Frame__not_gen2
    brl Same_Mode3_Fixture_Frame__gen2
Same_Mode3_Fixture_Frame__not_gen2:
    .a16
    cmp #$0002
    bne Same_Mode3_Fixture_Frame__not_gen3
    brl Same_Mode3_Fixture_Frame__gen3
Same_Mode3_Fixture_Frame__not_gen3:
    .a16
    cmp #$0003
    bne Same_Mode3_Fixture_Frame__not_gen4
    brl Same_Mode3_Fixture_Frame__gen4
Same_Mode3_Fixture_Frame__not_gen4:
    .a16
    cmp #$0004
    bne Same_Mode3_Fixture_Frame__not_gen5
    brl Same_Mode3_Fixture_Frame__gen5
Same_Mode3_Fixture_Frame__not_gen5:
    .a16
    cmp #$0005
    bne Same_Mode3_Fixture_Frame__not_gen6
    brl Same_Mode3_Fixture_Frame__gen6
Same_Mode3_Fixture_Frame__not_gen6:
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen2:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0001
    beq Same_Mode3_Fixture_Frame__gen2_ready
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen2_ready:
    .a16
    ldx #$0020
    jsr Same_Mode3_Fixture_Snapshot
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_LIMIT
    lda #$00E0
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
    lda #$0100
    sta.l SAME_MODE3_WORK_LIMIT
    jsr Same_Mode3_Fixture_PushPalette
    lda #$0002
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0002
    sta.l SAME_MODE3_FIXTURE_PHASE
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen3:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0002
    beq Same_Mode3_Fixture_Frame__gen3_ready
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen3_ready:
    .a16
    ldx #$0040
    jsr Same_Mode3_Fixture_Snapshot
    sep #$20
    .a8
    lda.l SAME_BWRAM_SURFACE_BASE+$0909
    eor #$01
    sta.l SAME_BWRAM_SURFACE_BASE+$0909
    rep #$20
    .a16
    lda #$0009
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0001
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0003
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0003
    sta.l SAME_MODE3_FIXTURE_PHASE
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen4:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0003
    beq Same_Mode3_Fixture_Frame__gen4_ready
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen4_ready:
    .a16
    ldx #$0060
    jsr Same_Mode3_Fixture_Snapshot
    sep #$20
    .a8
    lda.l SAME_MODE3_LIVE_PALETTE+$0003
    eor #$F8
    sta.l SAME_MODE3_LIVE_PALETTE+$0003
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_MODE3_WORK_INDEX
    sta.l SAME_MODE3_WORK_LIMIT
    jsr Same_Mode3_Fixture_PushPalette
    lda #$0004
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0004
    sta.l SAME_MODE3_FIXTURE_PHASE
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen5:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0004
    beq Same_Mode3_Fixture_Frame__gen5_ready
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen5_ready:
    .a16
    ldx #$0080
    jsr Same_Mode3_Fixture_Snapshot
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_Fixture_Frame__gen5_mutate:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_Fixture_ToggleTilePixel
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    cmp #$0021
    bcc Same_Mode3_Fixture_Frame__gen5_mutate
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0100
    sta.l SAME_MODE3_WORK_X1
    lda #$0008
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    lda #$0008
    sta.l SAME_MODE3_WORK_Y0
    lda #$0001
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0005
    jsr Same_Mode3_Fixture_PushPresent
    ; Locked requests are required to fail without replacing generation five.
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    sta.l SAME_MODE3_WORK_Y0
    lda #$0001
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
    lda #$0001
    sta.l SAME_MODE3_WORK_LIMIT
    jsr Same_Mode3_Fixture_PushPalette
    lda #$0006
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0005
    sta.l SAME_MODE3_FIXTURE_PHASE
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen6:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0005
    beq Same_Mode3_Fixture_Frame__gen6_ready
    brl Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__gen6_ready:
    .a16
    ldx #$00A0
    jsr Same_Mode3_Fixture_Snapshot
    lda #$0000
    sta.l SAME_MODE3_WORK_INDEX
Same_Mode3_Fixture_Frame__gen6_loop:
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    cmp #$0008
    bcs Same_Mode3_Fixture_Frame__gen6_last
    asl
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_Fixture_ToggleTilePixel
    lda.l SAME_MODE3_WORK_TILE
    and #$001F
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_X0
    lda #$0000
    sta.l SAME_MODE3_WORK_Y0
    lda #$0001
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda.l SAME_MODE3_WORK_INDEX
    inc
    sta.l SAME_MODE3_WORK_INDEX
    bra Same_Mode3_Fixture_Frame__gen6_loop
Same_Mode3_Fixture_Frame__gen6_last:
    .a16
    lda #$0020
    sta.l SAME_MODE3_WORK_TILE
    jsr Same_Mode3_Fixture_ToggleTilePixel
    lda #$0000
    sta.l SAME_MODE3_WORK_X0
    lda #$0008
    sta.l SAME_MODE3_WORK_Y0
    lda #$0001
    sta.l SAME_MODE3_WORK_X1
    sta.l SAME_MODE3_WORK_Y1
    jsr Same_Mode3_Fixture_PushDirty
    lda #$0006
    jsr Same_Mode3_Fixture_PushPresent
    lda #$0006
    sta.l SAME_MODE3_FIXTURE_PHASE
    bra Same_Mode3_Fixture_Frame__done
Same_Mode3_Fixture_Frame__done:
    .a16
    lda.l SAME_BWRAM_CONTROL_COMMITTED_GENERATION
    cmp #$0006
    bne Same_Mode3_Fixture_Frame__return
    ldx #$00C0
    jsr Same_Mode3_Fixture_Snapshot
    lda #$0001
    sta.l SAME_MODE3_FIXTURE_DONE
Same_Mode3_Fixture_Frame__return:
    jsr Same_Mode3_Retained_Fixture
    plp
    rtl

Same_Mode3_Fixture_ToggleTilePixel:
    lda.l SAME_MODE3_WORK_TILE
    pha
    and #$001F
    asl
    asl
    asl
    sta.l SAME_MODE3_WORK_TEMP
    pla
    and #$FFE0
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_MODE3_WORK_TEMP
    tax
    sep #$20
    .a8
    lda.l SAME_BWRAM_SURFACE_BASE,x
    eor #$01
    sta.l SAME_BWRAM_SURFACE_BASE,x
    rep #$30
    .a16
    .i16
    rts

; Six immutable generation records let the fresh-emulator validator observe
; work that would otherwise be reset by the next accepted PRESENT.
Same_Mode3_Fixture_Snapshot:
    rep #$30
    .a16
    .i16
    lda.l SAME_MODE3_CONTROL_CONVERTED_COUNT
    sta.l SAME_MODE3_FIXTURE+$0000,x
    lda.l SAME_MODE3_CONTROL_UNCHANGED_COUNT
    sta.l SAME_MODE3_FIXTURE+$0002,x
    lda.l SAME_MODE3_CONTROL_QUEUED_TILE_BYTES
    sta.l SAME_MODE3_FIXTURE+$0004,x
    lda.l SAME_MODE3_CONTROL_QUEUED_CGRAM_BYTES
    sta.l SAME_MODE3_FIXTURE+$0006,x
    lda.l SAME_MODE3_CONTROL_BATCH_COUNT
    sta.l SAME_MODE3_FIXTURE+$0008,x
    lda.l SAME_DMA_COMMITTED
    sta.l SAME_MODE3_FIXTURE+$000A,x
    lda.l SAME_MODE3_CONTROL_REJECTED_DIRTY
    sta.l SAME_MODE3_FIXTURE+$000C,x
    lda.l SAME_MODE3_CONTROL_REJECTED_PALETTE
    sta.l SAME_MODE3_FIXTURE+$000E,x
    lda.l SAME_MODE3_CONTROL_REJECTED_PRESENT
    sta.l SAME_MODE3_FIXTURE+$0010,x
    rts

Same_Mode3_Fixture_PushDirty:
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_SURFACE_DIRTY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_X0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_MODE3_WORK_Y0
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    lda.l SAME_MODE3_WORK_X1
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda.l SAME_MODE3_WORK_Y1
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+$02
    jsl Same_Mode3_Event_Push_Far
    rts

Same_Mode3_Fixture_PushPalette:
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_PALETTE_WRITE
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_INDEX
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_MODE3_WORK_LIMIT
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+$02
    jsl Same_Mode3_Event_Push_Far
    rts

Same_Mode3_Fixture_PushPresent:
    sta.l SAME_MODE3_WORK_TEMP
    jsl Same_Mode3_Event_Stage_Far
    sep #$20
    .a8
    lda #SAME_SERVICE_VIDEO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_VIDEO_OP_PRESENT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    rep #$20
    .a16
    lda.l SAME_MODE3_WORK_TEMP
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsl Same_Mode3_Event_Push_Far
    rts

.include "video_mode3_retained.inc.pasm"

Same_Mode3_RetainedTilemap:
    .incbin "../generated/video_backend_mode3_retained_tilemap.bin"

Same_Mode3_StaticTilemap:
    .incbin "../generated/video_backend_mode3_tilemap.bin"
