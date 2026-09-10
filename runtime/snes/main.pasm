; ============================================================================
; SAME engine host bootstrap — S-CPU services and reusable engine lifecycle
; Assembled only with Chad's astrobleem/poppy fork.
; ============================================================================
.snes

.include "generated/abi.inc.pasm"
.include "generated/build_config.inc.pasm"
.if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
.include "generated/scumm_v5_variables.inc.pasm"
.endif
.include "generated/carrier_constants.inc.pasm"
.include "generated/video_backend_constants.inc.pasm"
.include "generated/video_overlay_constants.inc.pasm"
.include "kernel/hardware.pasm"

.include "kernel/memory.pasm"
.if SAME_BUILD_M24RA
.include "generated/m24ra_tad_layout.inc.pasm"
.else
.include "../../audio/fate_s6/fate_tad_layout.inc.pasm"
.endif

.bank 0
.org $8000
reset:
    ; Persistent reset-vector diagnostic; this runs before kernel/engine state
    ; is initialized and therefore distinguishes a CPU reset from room 0.
    ; The diagnostic region is outside all engine state and clear ranges.
    sep #$20
    .a8
    php
    pla
    sta.l SAME_RESET_DIAG_LAST_P
    rep #$20
    .a16
    lda.l SAME_RESET_DIAG_COOKIE
    cmp #$A55A
    beq reset_diag_valid
    .a16
    .i16
    ldx #$0000
    .a16
    .i16
reset_diag_clear:
    .a16
    .i16
    lda #$0000
    sta.l SAME_RESET_DIAG_BASE,x
    inx
    inx
    cpx #$0020
    bcc reset_diag_clear
    lda #$A55A
    sta.l SAME_RESET_DIAG_COOKIE
reset_diag_valid:
    .a16
    .i16
    lda.l SAME_RESET_DIAG_COUNT
    inc
    sta.l SAME_RESET_DIAG_COUNT
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_RESET_DIAG_STAGE
    rep #$30
    .a16
    .i16
    tsc
    sta.l SAME_RESET_DIAG_LAST_S
    tdc
    sta.l SAME_RESET_DIAG_LAST_D
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_RESET_DIAG_FRAME
    sep #$20
    .a8
    phb
    pla
    sta.l SAME_RESET_DIAG_LAST_DBR
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_RESET_DIAG_ROOM
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_RESET_DIAG_PROGRAM
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_RESET_DIAG_SLOT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_RESET_DIAG_SCRIPT_PC
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

.include "generated/carrier_boot.inc.pasm"

    jsr Same_Kernel_Init
    jsr Same_Engine_Boot
    ; TAD's one-time IPL upload spans several raw video periods. Boot the
    ; semantic engine first so debugger-visible state is deterministic while
    ; interrupts and display remain disabled during that required transfer.
    jsr Same_Audio_Reset
    jsr Same_Kernel_DrainEvents
.include "generated/video_backend_boot.inc.pasm"
.include "generated/video_overlay_boot.inc.pasm"
.if SAME_VIDEO_BACKEND_LEGACY
    .if SAME_BUILD_SCUMM_M23A
    jsl Same_K1_Fixture_QueueInitial_Far
    .else
    jsr Same_K1_Fixture_QueueInitial
    .endif
.endif
    jsr Same_Video_Commit

    sep #$20
    .a8
    ; The blocking IPL upload can finish at any raster position. Arm NMI only
    ; at the start of active display so the first semantic frame receives a
    ; complete CPU budget instead of being sampled halfway through execution.
reset_wait_vblank:
    .a8
    lda HVBJOY
    and #$80
    beq reset_wait_vblank
reset_wait_active:
    .a8
    lda HVBJOY
    and #$80
    bne reset_wait_active
    lda #$81 ; NMI + automatic joypad read
    sta NMITIMEN
    lda #$0F
    sta INIDISP
    sta.l SAME_VIDEO_DISPLAY_SHADOW
    ; This final fixture is intentionally forced-blank-only.  It is queued
    ; after display enable so K1 can prove NMI defers it during active display.
.if SAME_VIDEO_BACKEND_LEGACY
    .if SAME_BUILD_SCUMM_M23A
    jsl Same_K1_Fixture_QueueDeferred_Far
    .else
    jsr Same_K1_Fixture_QueueDeferred
    .endif
.endif

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
    lda.l SAME_RESET_DIAG_NMI
    inc
    sta.l SAME_RESET_DIAG_NMI
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
    php
    rep #$30
    .a16
    pha
    sep #$20
    .a8
    lda.l SAME_RESET_DIAG_IRQ
    inc
    sta.l SAME_RESET_DIAG_IRQ
    rep #$20
    .a16
    pla
    plp
    rti
cop_handler:
    php
    rep #$30
    .a16
    pha
    sep #$20
    .a8
    lda.l SAME_RESET_DIAG_COP
    inc
    sta.l SAME_RESET_DIAG_COP
    rep #$20
    .a16
    pla
    plp
    rti
brk_handler:
    php
    rep #$30
    .a16
    pha
    sep #$20
    .a8
    lda.l SAME_RESET_DIAG_BRK
    inc
    sta.l SAME_RESET_DIAG_BRK
    rep #$20
    .a16
    pla
    plp
    rti

.include "kernel/events.pasm"
.include "kernel/dma.pasm"
.include "engine/host.pasm"
.include "services/input.pasm"
.include "services/video.pasm"
.include "services/audio.pasm"
.include "services/storage.pasm"
.include "kernel/frame.pasm"
.if SAME_BUILD_SCUMM_M22
.include "generated/music_sections.inc.pasm"
.endif
.if SAME_BUILD_SCUMM_M23A
.include "generated/scumm_v5_rooms.inc.pasm"
.endif
.include "engines/scumm_v5.pasm"
.include "engines/agi_v2.pasm"
.include "generated/active_engine.inc.pasm"
.include "targets/demo.pasm"

; Keep the fixed LoROM header/vector window visible in every assembly map.
; Bank 0 code must leave deliberate slack before $FFC0.
SAME_BANK0_CODE_END = *
SAME_BANK0_FREE_BYTES = $FFC0 - *
.assert SAME_BANK0_FREE_BYTES >= $0020, "bank 0 requires at least 32 bytes before header"

; Emit the internal LoROM header directly.  Poppy's current SNES header builder
; owns the entire $FFC0-$FFFF block and overwrites source-defined vectors, so the
; host follows the working Superman flow: assemble the exact image, then let the
; build finalizer calculate the checksum pair.
.org $FFC0
.byte $53,$41,$4D,$45,$20,$45,$4E,$47,$49,$4E,$45,$20,$48,$4F,$53,$54
.byte $20,$20,$20,$20,$20 ; "SAME ENGINE HOST" padded to 21 bytes
.include "generated/carrier_header.inc.pasm"
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

; TAD protocol-v20 loader, driver, common BRR data, and reviewed Fate songs
; arrangement. Generated deterministically before assembly.
.bank 1
.org $8000
Same_Tad_AudioData:
    .incbin "../../build/fate-audio/fate-tad-bank1.bin"
.bank 2
.org $8000
Same_Tad_AudioData_High:
    .incbin "../../build/fate-audio/fate-tad-bank2.bin"
Same_Tad_BlankSong:
    .byte $00
.if SAME_BUILD_SCUMM_M23A
.include "generated/scumm_v5_room_data.inc.pasm"
.if SAME_BUILD_M24RB
; M24R-B1 cold helper closure. Profile room payloads currently occupy banks 3-8;
; bank 9 is reserved for validator/lifecycle code and remains below 32 KiB.
.bank 9
.org $8000
.if SAME_BUILD_SCUMM_PHASE6LA1D == $01
; Validation-only C2 payload is cold data.  Keep its canonical labels for the
; bank-zero fixture dispatcher while placing the cohesive block in bank 9.
.include "generated/scumm_v5_conformance_far.inc.pasm"
.endif
.endif
.if SAME_BUILD_M24RB || SAME_BUILD_SCUMM_PHASE6HB
.include "generated/scumm_v5_room_validator_far.inc.pasm"
.endif
.if SAME_BUILD_M24RB
.include "engines/scumm_v5_m24rb_far.pasm"
.endif
.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
.include "engines/scumm_v5_controller_far.pasm"
.endif
; With M24R-B this follows its bank-9 closure; otherwise it follows generated
; room data in that data bank. Either placement keeps the cold handler out of
; bank 0 without duplicating its source include.
.include "engines/scumm_v5_matrix_far.pasm"
.include "engines/scumm_v5_camera_far.pasm"
.if SAME_VIDEO_BACKEND_LEGACY
.include "services/video_k1_far.pasm"
.endif
ScummV5_M24RB_FarCodeEnd:
.endif
.include "generated/carrier_code.inc.pasm"
.include "generated/video_backend_code.inc.pasm"
.include "generated/video_overlay_code.inc.pasm"
.include "generated/scumm_v5_font.inc.pasm"
.if SAME_VIDEO_OVERLAY_BG2
.include "services/video_overlay_surface.pasm"
.endif
.if SAME_BUILD_SCUMM_ROOM_VISUAL
.include "generated/scumm_v5_room_visuals.inc.pasm"
.if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
.include "generated/scumm_v5_actor_sprite.inc.pasm"
.include "generated/scumm_v5_object_sprite.inc.pasm"
.endif
.include "services/video_surface.pasm"
.include "engines/scumm_v5_visual.pasm"
.endif
