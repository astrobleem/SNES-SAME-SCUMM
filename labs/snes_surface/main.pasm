; Copyright-free SAME Phase 6A Mode-3 indexed-surface proof.
.snes

INIDISP  = $2100
BGMODE   = $2105
MOSAIC   = $2106
BG1SC    = $2107
BG12NBA  = $210B
BG1HOFS  = $210D
BG1VOFS  = $210E
VMAIN    = $2115
VMADDL   = $2116
VMADDH   = $2117
CGADD    = $2121
TM       = $212C
TS       = $212D
CGWSEL   = $2130
CGADSUB  = $2131
SETINI   = $2133
NMITIMEN = $4200
MDMAEN   = $420B
HDMAEN   = $420C
RDNMI    = $4210
DMAP0    = $4300
BBAD0    = $4301
A1T0L    = $4302
A1T0H    = $4303
A1B0     = $4304
DAS0L    = $4305
DAS0H    = $4306

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

    jsr SurfaceProof_InitPpu
    jsr SurfaceProof_LoadTilesFirst
    jsr SurfaceProof_LoadTilesSecond
    jsr SurfaceProof_LoadTilemap
    jsr SurfaceProof_LoadPalette

    lda #$81
    sta NMITIMEN
    lda #$0F
    sta INIDISP

SurfaceProof_Forever:
    wai
    bra SurfaceProof_Forever

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
    ; The normal BG fetch origin is one scanline ahead of logical row zero.
    ; A 10-bit -1 offset aligns screen row 0 with source row 0.
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

SurfaceProof_LoadTilesFirst:
    lda #$00
    sta VMADDL
    sta VMADDH
    lda #<SurfaceProof_TilesFirst
    sta A1T0L
    lda #>SurfaceProof_TilesFirst
    sta A1T0H
    lda #$01
    sta A1B0
    lda #$00
    sta DAS0L
    lda #$70
    sta DAS0H
    bra SurfaceProof_DmaVram

SurfaceProof_LoadTilesSecond:
    lda #$00
    sta VMADDL
    lda #$38
    sta VMADDH
    lda #<SurfaceProof_TilesSecond
    sta A1T0L
    lda #>SurfaceProof_TilesSecond
    sta A1T0H
    lda #$02
    sta A1B0
    lda #$00
    sta DAS0L
    lda #$70
    sta DAS0H
    bra SurfaceProof_DmaVram

SurfaceProof_LoadTilemap:
    lda #$00
    sta VMADDL
    lda #$70
    sta VMADDH
    lda #<SurfaceProof_Tilemap
    sta A1T0L
    lda #>SurfaceProof_Tilemap
    sta A1T0H
    lda #$02
    sta A1B0
    lda #$00
    sta DAS0L
    lda #$08
    sta DAS0H

SurfaceProof_DmaVram:
    .a8
    lda #$80
    sta VMAIN
    lda #$01
    sta DMAP0
    lda #$18
    sta BBAD0
    lda #$01
    sta MDMAEN
    rts

SurfaceProof_LoadPalette:
    stz CGADD
    stz DMAP0
    lda #$22
    sta BBAD0
    lda #<SurfaceProof_Palette
    sta A1T0L
    lda #>SurfaceProof_Palette
    sta A1T0H
    lda #$02
    sta A1B0
    lda #$00
    sta DAS0L
    lda #$02
    sta DAS0H
    lda #$01
    sta MDMAEN
    rts

SurfaceProof_Nmi:
    sep #$20
    .a8
    lda RDNMI
    rti

SurfaceProof_Irq:
    rti
SurfaceProof_Cop:
    rti
SurfaceProof_Brk:
    rti

.org $FFC0
.byte $53,$41,$4D,$45,$20,$49,$4E,$44,$45,$58,$38,$20,$4D,$4F,$44,$45
.byte $33,$20,$20,$20,$20 ; "SAME INDEX8 MODE3" padded to 21 bytes
.byte $20 ; slow LoROM
.byte $00 ; ROM only
.byte $07 ; 128 KiB
.byte $00 ; no cartridge RAM
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
