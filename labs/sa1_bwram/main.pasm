; Copyright-free SAME Phase 6B SA-1 BW-RAM storage carrier proof.
; The SA-1 CPU is explicitly held in reset and executes no code.
.snes

.include "../../runtime/snes/generated/abi.inc.pasm"
.include "../../runtime/snes/kernel/hardware.pasm"
.include "../../runtime/snes/kernel/memory.pasm"

CCNT      = $2200
BMAPS     = $2224
SBWE      = $2226
BWPA      = $2228
BG1SC     = $2107
BG12NBA   = $210B
BG1HOFS   = $210D
BG1VOFS   = $210E
MOSAIC    = $2106
CGWSEL    = $2130
CGADSUB   = $2131
SETINI    = $2133

SURFACE_PROOF_STATUS             = $7E1000
SURFACE_PROOF_STAGE              = $7E1001
SURFACE_PROOF_PROTECTION_FLAGS   = $7E1002
SURFACE_PROOF_ALIAS_FLAGS        = $7E1003
SURFACE_PROOF_DISTINCT_FLAGS     = $7E1004
SURFACE_PROOF_SHADOW_FLAGS       = $7E1005
SURFACE_PROOF_CCNT_SHADOW        = $7E1006
SURFACE_PROOF_BMAPS_SHADOW       = $7E1007
SURFACE_PROOF_SBWE_SHADOW        = $7E1008
SURFACE_PROOF_BWPA_SHADOW        = $7E1009
SURFACE_PROOF_NMI_COUNT          = $7E100A
SURFACE_PROOF_ACTIVE_DMA         = $7E100B
SURFACE_PROOF_ERRORS             = $7E100C
SURFACE_PROOF_PROTECTED_ORIGINAL = $7E1010
SURFACE_PROOF_PROTECTED_AFTER    = $7E1011
SURFACE_PROOF_BYPASS_AFTER       = $7E1012
SURFACE_PROOF_ALIAS_SCRATCH      = $7E1013
SURFACE_PROOF_BANK40_SCRATCH     = $7E1014
SURFACE_PROOF_BANK41_SCRATCH     = $7E1015
SURFACE_PROOF_UPLOAD_OFFSET      = $7E1016

SURFACE_PROOF_MAGIC = $B6
SURFACE_PROOF_DONE  = $FF

.bank 0
.org $8000
SurfaceProof_Reset:
    sei
    clc
    xce
    rep #$30
    .a16
    .i16
    lda #$1FFF
    tcs
    sep #$20
    .a8
    stz NMITIMEN
    stz MDMAEN
    stz HDMAEN
    lda #$80
    sta INIDISP

    lda #SURFACE_PROOF_MAGIC
    sta.l SURFACE_PROOF_STATUS
    lda #$00
    sta.l SURFACE_PROOF_STAGE
    sta.l SURFACE_PROOF_PROTECTION_FLAGS
    sta.l SURFACE_PROOF_ALIAS_FLAGS
    sta.l SURFACE_PROOF_DISTINCT_FLAGS
    sta.l SURFACE_PROOF_SHADOW_FLAGS
    sta.l SURFACE_PROOF_NMI_COUNT
    sta.l SURFACE_PROOF_ACTIVE_DMA
    sta.l SURFACE_PROOF_ERRORS

    ; CCNT bit 5 keeps the SA-1 processor reset asserted.
    lda #$20
    sta CCNT
    sta.l SURFACE_PROOF_CCNT_SHADOW

    ; BWPA=3 protects 256<<3 = 2048 low bytes while SBWE.7 remains clear.
    lda #$03
    sta BWPA
    sta.l SURFACE_PROOF_BWPA_SHADOW
    stz SBWE
    lda #$00
    sta.l SURFACE_PROOF_SBWE_SHADOW
    stz BMAPS
    sta.l SURFACE_PROOF_BMAPS_SHADOW

    lda #$01
    sta.l SURFACE_PROOF_STAGE
    jsr SurfaceProof_TestProtection
    jsr SurfaceProof_CopySurface
    jsr SurfaceProof_CopyTileShadow
    jsr SurfaceProof_CopyCgramShadow
    jsr SurfaceProof_TestBankDistinct
    jsr SurfaceProof_TestTileIsolation
    jsr SurfaceProof_TestAliases

    lda #$02
    sta.l SURFACE_PROOF_STAGE
    jsr SurfaceProof_InitPpu
    jsr Same_Dma_Reset
    jsr Same_Video_Reset
    jsr SurfaceProof_ForcedBlankUploads

    ; Queue one normal active-display tile transfer through the production
    ; channel-7 queue. NMI owns its commit.
    jsr SurfaceProof_QueueActiveTile
    lda #$81
    sta NMITIMEN
    lda #$0F
    sta INIDISP

SurfaceProof_WaitActiveDma:
    wai
    rep #$20
    .a16
    lda.l SAME_DMA_PENDING
    bne SurfaceProof_WaitActiveDma
    sep #$20
    .a8
    lda #$01
    sta.l SURFACE_PROOF_ACTIVE_DMA
    lda #SURFACE_PROOF_DONE
    sta.l SURFACE_PROOF_STAGE

SurfaceProof_Forever:
    wai
    bra SurfaceProof_Forever

SurfaceProof_TestProtection:
    sep #$20
    .a8
    lda.l $4007FF
    sta.l SURFACE_PROOF_PROTECTED_ORIGINAL
    eor #$FF
    sta.l $4007FF
    lda.l $4007FF
    sta.l SURFACE_PROOF_PROTECTED_AFTER
    cmp.l SURFACE_PROOF_PROTECTED_ORIGINAL
    beq SurfaceProof_ProtectionLowOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionLowOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$01
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    lda #$A5
    sta.l $400800
    cmp.l $400800
    beq SurfaceProof_ProtectionFirstWritableOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionFirstWritableOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$02
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    lda #$5A
    sta.l $401000
    cmp.l $401000
    beq SurfaceProof_BackendReserveWritableOk
    brl SurfaceProof_ProtectionError
SurfaceProof_BackendReserveWritableOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$40
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    ; SBWE.7 bypasses BWPA entirely. Restore the protected byte afterward.
    lda #$80
    sta SBWE
    sta.l SURFACE_PROOF_SBWE_SHADOW
    lda.l SURFACE_PROOF_PROTECTED_ORIGINAL
    eor #$FF
    sta.l $4007FF
    lda.l $4007FF
    sta.l SURFACE_PROOF_BYPASS_AFTER
    cmp.l SURFACE_PROOF_PROTECTED_ORIGINAL
    bne SurfaceProof_ProtectionBypassOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionBypassOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTED_ORIGINAL
    sta.l $4007FF
    stz SBWE
    lda #$00
    sta.l SURFACE_PROOF_SBWE_SHADOW
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$04
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    lda #$4F
    sta.l $40FFFF
    cmp.l $40FFFF
    beq SurfaceProof_ProtectionBank40EndOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionBank40EndOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$08
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    lda #$41
    sta.l $410000
    cmp.l $410000
    beq SurfaceProof_ProtectionBank41StartOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionBank41StartOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$10
    sta.l SURFACE_PROOF_PROTECTION_FLAGS

    lda #$EF
    sta.l $41FFFF
    cmp.l $41FFFF
    beq SurfaceProof_ProtectionBank41EndOk
    brl SurfaceProof_ProtectionError
SurfaceProof_ProtectionBank41EndOk:
    .a8
    lda.l SURFACE_PROOF_PROTECTION_FLAGS
    ora #$20
    sta.l SURFACE_PROOF_PROTECTION_FLAGS
    rts

SurfaceProof_ProtectionError:
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
    rts

SurfaceProof_CopySurface:
    rep #$10
    .i16
    sep #$20
    .a8
    ldx #$0000
SurfaceProof_CopySurfaceFirst:
    .a8
    .i16
    lda.l $038000,x
    sta.l $402000,x
    inx
    cpx #$7000
    bcc SurfaceProof_CopySurfaceFirst
    ldx #$0000
SurfaceProof_CopySurfaceSecond:
    .a8
    .i16
    lda.l $048000,x
    sta.l $409000,x
    inx
    cpx #$7000
    bcc SurfaceProof_CopySurfaceSecond
    rts

SurfaceProof_CopyTileShadow:
    ldx #$0000
SurfaceProof_CopyTilesFirst:
    .a8
    .i16
    lda.l $018000,x
    sta.l $410000,x
    inx
    cpx #$7000
    bcc SurfaceProof_CopyTilesFirst
    ldx #$0000
SurfaceProof_CopyTilesSecond:
    .a8
    .i16
    lda.l $028000,x
    sta.l $417000,x
    inx
    cpx #$7000
    bcc SurfaceProof_CopyTilesSecond
    rts

SurfaceProof_CopyCgramShadow:
    ldx #$0000
SurfaceProof_CopyCgramLoop:
    .a8
    .i16
    lda.l $02F800,x
    sta.l $41E000,x
    inx
    cpx #$0200
    bcc SurfaceProof_CopyCgramLoop
    rts

SurfaceProof_TestBankDistinct:
    lda.l $402000
    sta.l SURFACE_PROOF_BANK40_SCRATCH
    lda.l $412000
    sta.l SURFACE_PROOF_BANK41_SCRATCH
    lda #$11
    sta.l $402000
    lda #$22
    sta.l $412000
    lda.l $402000
    cmp #$11
    bne SurfaceProof_DistinctError
    lda.l $412000
    cmp #$22
    bne SurfaceProof_DistinctError
    lda.l SURFACE_PROOF_BANK40_SCRATCH
    sta.l $402000
    lda.l SURFACE_PROOF_BANK41_SCRATCH
    sta.l $412000
    lda #$01
    sta.l SURFACE_PROOF_DISTINCT_FLAGS
    rts
SurfaceProof_DistinctError:
    lda.l SURFACE_PROOF_BANK40_SCRATCH
    sta.l $402000
    lda.l SURFACE_PROOF_BANK41_SCRATCH
    sta.l $412000
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
    rts

SurfaceProof_TestTileIsolation:
    ; Mutate tile 11, compare its two neighbors with their ROM sources, then
    ; restore tile 11. Final full-region hashing independently checks all bytes.
    ldx #$0000
SurfaceProof_MutateTile11:
    .a8
    .i16
    lda.l $4102C0,x
    eor #$FF
    sta.l $4102C0,x
    inx
    cpx #$0040
    bcc SurfaceProof_MutateTile11
    ldx #$0000
SurfaceProof_CompareTileNeighbors:
    .a8
    .i16
    lda.l $410280,x
    cmp.l $018280,x
    bne SurfaceProof_ShadowError
    lda.l $410300,x
    cmp.l $018300,x
    bne SurfaceProof_ShadowError
    inx
    cpx #$0040
    bcc SurfaceProof_CompareTileNeighbors
    ldx #$0000
SurfaceProof_RestoreTile11:
    .a8
    .i16
    lda.l $0182C0,x
    sta.l $4102C0,x
    inx
    cpx #$0040
    bcc SurfaceProof_RestoreTile11
    lda #$01
    sta.l SURFACE_PROOF_SHADOW_FLAGS
    rts
SurfaceProof_ShadowError:
    .a8
    .i16
    ldx #$0000
SurfaceProof_RestoreTile11Error:
    .a8
    .i16
    lda.l $0182C0,x
    sta.l $4102C0,x
    inx
    cpx #$0040
    bcc SurfaceProof_RestoreTile11Error
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
    rts

.include "generated/alias-tests.inc.pasm"

SurfaceProof_InitPpu:
    sep #$20
    .a8
    lda #$03
    sta BGMODE
    stz MOSAIC
    lda #$70
    sta BG1SC
    stz BG12NBA
    stz BG1HOFS
    stz BG1HOFS
    lda #$FF
    sta BG1VOFS
    lda #$03
    sta BG1VOFS
    lda #$01
    sta TM
    stz TS
    stz CGWSEL
    stz CGADSUB
    stz SETINI
    rts

SurfaceProof_ForcedBlankUploads:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SURFACE_PROOF_UPLOAD_OFFSET
SurfaceProof_ForcedBlankTileLoop:
    .a16
    .i16
    lda.l SURFACE_PROOF_UPLOAD_OFFSET
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    bcc SurfaceProof_ForcedBlankTileQueued
    brl SurfaceProof_DmaError
SurfaceProof_ForcedBlankTileQueued:
    jsr Same_Video_Commit
    rep #$30
    .a16
    .i16
    lda.l SURFACE_PROOF_UPLOAD_OFFSET
    clc
    adc #$0800
    sta.l SURFACE_PROOF_UPLOAD_OFFSET
    cmp #$E000
    bcc SurfaceProof_ForcedBlankTileLoop

    lda #$F000
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$E000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0800
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$02
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    bcc SurfaceProof_TilemapQueued
    brl SurfaceProof_DmaError
SurfaceProof_TilemapQueued:
    jsr Same_Video_Commit

    rep #$20
    .a16
    lda #$E000
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    lda #$0000
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0200
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_CGRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    bcc SurfaceProof_CgramQueued
    brl SurfaceProof_DmaError
SurfaceProof_CgramQueued:
    jsr Same_Video_Commit
    rts

SurfaceProof_QueueActiveTile:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_DMA_REQUEST_SOURCE_LO
    sta.l SAME_DMA_REQUEST_TARGET
    lda #$0040
    sta.l SAME_DMA_REQUEST_LENGTH
    sep #$20
    .a8
    lda #$41
    sta.l SAME_DMA_REQUEST_SOURCE_BANK
    lda #SAME_DMA_TYPE_VRAM
    sta.l SAME_DMA_REQUEST_TYPE_FLAGS
    jsr Same_Dma_Enqueue
    bcc SurfaceProof_ActiveTileQueued
    brl SurfaceProof_DmaError
SurfaceProof_ActiveTileQueued:
    rts

SurfaceProof_DmaError:
    sep #$20
    .a8
    lda.l SURFACE_PROOF_ERRORS
    inc
    sta.l SURFACE_PROOF_ERRORS
    rts

SurfaceProof_Nmi:
    php
    pha
    phx
    phy
    jsr Same_Video_Commit
    sep #$20
    .a8
    lda.l SURFACE_PROOF_NMI_COUNT
    inc
    sta.l SURFACE_PROOF_NMI_COUNT
    ply
    plx
    pla
    plp
    rti

SurfaceProof_Irq:
    rti
SurfaceProof_Cop:
    rti
SurfaceProof_Brk:
    rti

; Reuse the exact production queue and video commit implementation.
.include "../../runtime/snes/kernel/dma.pasm"
.include "../../runtime/snes/services/video.pasm"

.org $FFC0
.byte $53,$41,$4D,$45,$20,$53,$41,$31,$20,$42,$57,$52,$41,$4D,$20,$50
.byte $52,$4F,$4F,$46,$20 ; "SAME SA1 BWRAM PROOF " (21 bytes)
.byte $23 ; slow LoROM + SA-1 map mode
.byte $35 ; ROM + SA-1 + RAM + battery
.byte $08 ; 256 KiB ROM
.byte $07 ; 128 KiB BW-RAM
.byte $01 ; North America
.byte $00 ; developer/licensee
.byte $00 ; version
.word $0000
.word $0000

.bank 1
.org $8000
SurfaceProof_TilesFirst:
    .incbin "generated/tiles-first.8bpp"

.bank 2
.org $8000
SurfaceProof_TilesSecond:
    .incbin "generated/tiles-second.8bpp"
SurfaceProof_Tilemap:
    .incbin "generated/tilemap.bin"
SurfaceProof_Palette:
    .incbin "generated/palette.cgram"

.bank 3
.org $8000
SurfaceProof_SurfaceFirst:
    .incbin "generated/surface-first.index8"

.bank 4
.org $8000
SurfaceProof_SurfaceSecond:
    .incbin "generated/surface-second.index8"

.bank 0
.org $FFE0
.word $0000
.word $0000
.word SurfaceProof_Cop
.word SurfaceProof_Brk
.word $0000
.word SurfaceProof_Nmi
.word SurfaceProof_Reset
.word SurfaceProof_Irq

.org $FFF0
.word $0000
.word $0000
.word SurfaceProof_Cop
.word $0000
.word $0000
.word SurfaceProof_Nmi
.word SurfaceProof_Reset
.word SurfaceProof_Irq
