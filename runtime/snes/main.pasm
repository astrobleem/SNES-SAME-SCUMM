; ============================================================================
; SAME engine host bootstrap — S-CPU services and reusable engine lifecycle
; Assembled only with Chad's astrobleem/poppy fork.
; ============================================================================
.snes

.include "generated/abi.inc.pasm"
.include "kernel/hardware.pasm"
.include "kernel/memory.pasm"

.bank 0
.org $8000
reset:
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
    stz BGMODE
    stz TM
    stz TS
    lda #$01
    sta MEMSEL

    jsr Same_Kernel_Init
    jsr Same_Engine_Boot
    jsr Same_Kernel_DrainEvents
    jsr Same_K1_Fixture_QueueInitial
    jsr Same_Video_Commit

    sep #$20
    .a8
    lda #$81 ; NMI + automatic joypad read
    sta NMITIMEN
    lda #$0F
    sta INIDISP
    sta.l SAME_VIDEO_DISPLAY_SHADOW
    ; This final fixture is intentionally forced-blank-only.  It is queued
    ; after display enable so K1 can prove NMI defers it during active display.
    jsr Same_K1_Fixture_QueueDeferred

Same_Main_Loop:
    sep #$20
    .a8
    wai
    jsr Same_Frame_Run
    bra Same_Main_Loop

nmi_handler:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    phk
    plb
    sep #$20
    .a8
    lda RDNMI
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    inc
    sta.l SAME_FRAME_COUNTER
    jsr Same_Video_Commit
    plb
    ply
    plx
    pla
    plp
    rti

irq_handler:
    rti
cop_handler:
    rti
brk_handler:
    rti

.include "kernel/events.pasm"
.include "kernel/dma.pasm"
.include "engine/host.pasm"
.include "services/input.pasm"
.include "services/video.pasm"
.include "services/audio.pasm"
.include "services/storage.pasm"
.include "kernel/frame.pasm"
.include "engines/scumm_v5.pasm"
.include "engines/agi_v2.pasm"
.include "generated/active_engine.inc.pasm"
.include "targets/demo.pasm"

; Emit the internal LoROM header directly.  Poppy's current SNES header builder
; owns the entire $FFC0-$FFFF block and overwrites source-defined vectors, so the
; host follows the working Superman flow: assemble the exact image, then let the
; build finalizer calculate the checksum pair.
.org $FFC0
.byte $53,$41,$4D,$45,$20,$45,$4E,$47,$49,$4E,$45,$20,$48,$4F,$53,$54
.byte $20,$20,$20,$20,$20 ; "SAME ENGINE HOST" padded to 21 bytes
.byte $20 ; slow LoROM
.byte $00 ; ROM only
.byte $05 ; 32 KiB ROM size code
.byte $00 ; no cartridge RAM
.byte $01 ; North America
.byte $00 ; developer/licensee
.byte $00 ; version
.word $0000 ; checksum complement, finalized after assembly
.word $0000 ; checksum, finalized after assembly

.org $FFE0
.word $0000
.word $0000
.word cop_handler
.word brk_handler
.word $0000
.word nmi_handler
.word reset
.word irq_handler

.org $FFF0
.word $0000
.word $0000
.word cop_handler
.word $0000
.word $0000
.word nmi_handler
.word reset
.word irq_handler
