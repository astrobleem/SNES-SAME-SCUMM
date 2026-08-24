; ============================================================================
; SAME-VDP SNES static-frame player
; Assembled with Chad's fork: https://github.com/astrobleem/poppy
; Required ancestor: ec005c196eedabf7d0c25ff6336398c427dd43ac
; ============================================================================

.system:snes

.snes_name "SAME VDP LAB"
.snes_map_mode LOROM
.snes_rom_speed SLOW
.snes_rom_type ROM
.snes_rom_size 3
.snes_ram_size 0
.snes_region NORTH_AMERICA
.snes_developer "SA"
.snes_version 0

.include "generated/assets.inc.pasm"

INIDISP  = $2100
BGMODE   = $2105
MOSAIC   = $2106
BG1SC    = $2107
BG12NBA  = $210b
BG1HOFS  = $210d
BG1VOFS  = $210e
VMAIN    = $2115
VMADDL   = $2116
VMADDH   = $2117
VMDATAL  = $2118
CGADD    = $2121
CGDATA   = $2122
TM       = $212c
TS       = $212d
CGWSEL   = $2130
CGADSUB  = $2131
SETINI   = $2133
NMITIMEN = $4200
MDMAEN   = $420b
HDMAEN   = $420c
RDNMI    = $4210
DMAP0    = $4300
BBAD0    = $4301
A1T0L    = $4302
A1T0H    = $4303
A1B0     = $4304
DAS0L    = $4305
DAS0H    = $4306

.org $808000
reset:
    sei
    clc
    xce
    rep #$30
    lda #$1fff
    tcs
    sep #$20
    stz NMITIMEN
    stz MDMAEN
    stz HDMAEN
    lda #$80
    sta INIDISP

    jsr init_ppu
    jsr load_palette
    jsr load_tiles
    jsr load_tilemap

    lda #$81
    sta NMITIMEN
    lda #$0f
    sta INIDISP

@forever:
    wai
    bra @forever

init_ppu:
    sep #$20
    lda #$01
    sta BGMODE
    stz MOSAIC
    lda #$60
    sta BG1SC
    stz BG12NBA
    stz BG1HOFS
    stz BG1HOFS
    stz BG1VOFS
    stz BG1VOFS
    lda #$01
    sta TM
    stz TS
    stz CGWSEL
    stz CGADSUB
    stz SETINI
    rts

load_palette:
    sep #$20
    stz CGADD
    stz DMAP0
    lda #$22
    sta BBAD0
    lda #<palette_data
    sta A1T0L
    lda #>palette_data
    sta A1T0H
    lda #^palette_data
    sta A1B0
    lda #<SAME_CGRAM_BYTES
    sta DAS0L
    lda #>SAME_CGRAM_BYTES
    sta DAS0H
    lda #$01
    sta MDMAEN
    rts

load_tiles:
    sep #$20
    lda #$80
    sta VMAIN
    lda #<SAME_TILE_VRAM
    sta VMADDL
    lda #>SAME_TILE_VRAM
    sta VMADDH
    lda #$01
    sta DMAP0
    lda #$18
    sta BBAD0
    lda #<tile_data
    sta A1T0L
    lda #>tile_data
    sta A1T0H
    lda #^tile_data
    sta A1B0
    lda #<SAME_TILE_BYTES
    sta DAS0L
    lda #>SAME_TILE_BYTES
    sta DAS0H
    lda #$01
    sta MDMAEN
    rts

load_tilemap:
    sep #$20
    lda #$80
    sta VMAIN
    lda #<SAME_MAP_VRAM
    sta VMADDL
    lda #>SAME_MAP_VRAM
    sta VMADDH
    lda #$01
    sta DMAP0
    lda #$18
    sta BBAD0
    lda #<tilemap_data
    sta A1T0L
    lda #>tilemap_data
    sta A1T0H
    lda #^tilemap_data
    sta A1B0
    lda #<SAME_MAP_BYTES
    sta DAS0L
    lda #>SAME_MAP_BYTES
    sta DAS0H
    lda #$01
    sta MDMAEN
    rts

nmi_handler:
    sep #$20
    lda RDNMI
    rti

irq_handler:
    rti

cop_handler:
    rti

brk_handler:
    rti

; Assets remain well below one LoROM bank in milestone 0.
.org $818000
palette_data:
    .incbin "generated/palette.cgram"
tile_data:
    .incbin "generated/tiles.4bpp"
tilemap_data:
    .incbin "generated/tilemap.bin"

.org $80ffe0
.word $0000
.word $0000
.word cop_handler
.word brk_handler
.word $0000
.word nmi_handler
.word reset
.word irq_handler

.org $80fff0
.word $0000
.word $0000
.word cop_handler
.word $0000
.word $0000
.word nmi_handler
.word reset
.word irq_handler
