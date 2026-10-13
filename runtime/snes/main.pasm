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
.include "generated/tad_layout.inc.pasm"

.bank 0
.org $8000
reset:
    ; Establish native-mode accumulator/index widths before any 16-bit
    ; immediate or reset diagnostic runs. The CPU enters from the reset vector
    ; in emulation mode, where REP #$20 cannot switch the accumulator width.
    sei
    clc
    xce
    .if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    ; Temporary diagnostic trap: on a second reset-entry pass, stop before
    ; TCS erases the incoming stack/mode evidence. This is confined to the
    ; synthetic-bootstrap investigation build and is not production behavior.
    sep #$20
    .a8
    php
    pla
    sta.l SAME_RESET_DIAG_LAST_P
    rep #$30
    .a16
    .i16
    tsc
    sta.l SAME_RESET_DIAG_LAST_S
    sep #$20
    .a8
    lda #$FE
    sta.l SAME_RESET_DIAG_STAGE
    rep #$20
    .a16
    lda.l SAME_RESET_DIAG_COOKIE
    cmp #$A55A
    bne reset__diagnostic_continue
    lda.l SAME_RESET_DIAG_COUNT
    cmp #$0001
    bne reset__diagnostic_continue
    stp
reset__diagnostic_continue:
    .endif
    rep #$30
    .a16
    .i16
    lda #$1FFF
    tcs

    ; Persistent reset-vector diagnostic; this runs before kernel/engine state
    ; is initialized and therefore distinguishes a CPU reset from room 0.
    ; The diagnostic region is outside all engine state and clear ranges.
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    lda #$00
    sta.l SAME_SCUMM_SYNTHETIC_BOOTSTRAP_REQUESTED
    .endif
    .if SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP
    lda #$00
    sta.l SAME_SCUMM_AUTHENTIC_BOOTSTRAP_STARTED
    .endif
.if SAME_BUILD_RESET_DIAGNOSTICS
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
.endif

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
.if SAME_BUILD_SCUMM_RESIDENCY_DIAGNOSTIC
    ; Dedicated control ROM: run allocator safety assertions before the first
    ; semantic frame, then stop so no gameplay fixture can obscure the result.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RESIDENT_DIAG_RETURNED
    jsl ScummV5_Resident_RunAcceptanceControl_Far
    lda #$A5
    sta.l SAME_SCUMM_RESIDENT_DIAG_RETURNED
Same_Scumm_Residency_Diagnostic_Halt:
    bra Same_Scumm_Residency_Diagnostic_Halt
.endif
.if SAME_BUILD_SCUMM_M25A_PENDING_ONLY
    ; Copyright-free near-route transaction control. Boot the synthetic source
    ; room through the production near RequestRoom and Storage event path; the
    ; validator later submits its tested requests through the public mailbox.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_PENDING_DIAG_COUNT
    sta.l SAME_SCUMM_PENDING_DIAG_STAGE
    sta.l SAME_SCUMM_PENDING_DIAG_INJECT_MODE
    sta.l SAME_SCUMM_PENDING_DIAG_INJECT_TARGET
    sta.l SAME_SCUMM_PENDING_DIAG_INJECTED
    sta.l SAME_SCUMM_PENDING_DIAG_INJECT_ROUTE
    sta.l SAME_SCUMM_PENDING_DIAG_INJECT_ORIGIN
    sta.l SAME_SCUMM_ROOM_REQUEST_API_PENDING
    sta.l SAME_SCUMM_M23A_REQUEST_API_ACTIVE
    lda #$31
    jsr ScummV5_RequestRoom
.endif
.if SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE && !SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE_NO_ROOT_ROOM
    ; Standalone conformance root: enter the normal room-request lifecycle
    ; after engine state is initialized, without writing active-room state.
    sep #$20
    .a8
    lda #$01
    jsr ScummV5_RequestRoom
.endif
    ; TAD's one-time IPL upload spans several raw video periods. Boot the
    ; semantic engine first so debugger-visible state is deterministic while
    ; interrupts and display remain disabled during that required transfer.
    .if !SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
    jsr Same_Audio_Reset
    .endif
    jsr Same_Kernel_DrainEvents
.if !SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
.include "generated/video_backend_boot.inc.pasm"
.endif
.include "generated/video_overlay_boot.inc.pasm"
.if SAME_VIDEO_BACKEND_LEGACY
    .if SAME_BUILD_SCUMM_M23A || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
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
    .if SAME_BUILD_SCUMM_M23A || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
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

.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
; Compare stack depth at equivalent call boundaries in the synthetic startup
; diagnostic only. This does not touch production execution personalities.
Same_Reset_Diag_CheckStack:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_RESET_DIAG_SP_STAGE
    bne Same_Reset_Diag_CheckStack__compare
    lda.l SAME_RESET_DIAG_SP_CURRENT
    sta.l SAME_RESET_DIAG_SP_ENTRY
    bra Same_Reset_Diag_CheckStack__balanced
Same_Reset_Diag_CheckStack__compare:
    lda.l SAME_RESET_DIAG_SP_ENTRY
    cmp.l SAME_RESET_DIAG_SP_CURRENT
    beq Same_Reset_Diag_CheckStack__balanced
    lda.l SAME_RESET_DIAG_SP_FAILURES
    inc
    sta.l SAME_RESET_DIAG_SP_FAILURES
    pla
    plp
    sec
    rts
Same_Reset_Diag_CheckStack__balanced:
    pla
    plp
    clc
    rts
Same_Reset_Diag_CheckInputStack:
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_RESET_DIAG_INPUT_SP_STAGE
    bne Same_Reset_Diag_CheckInputStack__compare
    lda.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    sta.l SAME_RESET_DIAG_INPUT_SP_ENTRY
    bra Same_Reset_Diag_CheckInputStack__balanced
Same_Reset_Diag_CheckInputStack__compare:
    lda.l SAME_RESET_DIAG_INPUT_SP_ENTRY
    cmp.l SAME_RESET_DIAG_INPUT_SP_CURRENT
    beq Same_Reset_Diag_CheckInputStack__balanced
    lda.l SAME_RESET_DIAG_INPUT_SP_FAILURES
    inc
    sta.l SAME_RESET_DIAG_INPUT_SP_FAILURES
    pla
    plp
    sec
    rts
Same_Reset_Diag_CheckInputStack__balanced:
    pla
    plp
    clc
    rts
Same_Reset_Diag_StackFailure:
    stp
.endif

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
.if SAME_BUILD_NMI_DIAGNOSTIC_COUNTER
.if SAME_BUILD_RESET_DIAGNOSTICS
    lda.l SAME_RESET_DIAG_NMI
    inc
    sta.l SAME_RESET_DIAG_NMI
.endif
.endif
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
.if SAME_BUILD_RESET_DIAGNOSTICS
    lda.l SAME_RESET_DIAG_IRQ
    inc
    sta.l SAME_RESET_DIAG_IRQ
.endif
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
.if SAME_BUILD_RESET_DIAGNOSTICS
    lda.l SAME_RESET_DIAG_COP
    inc
    sta.l SAME_RESET_DIAG_COP
.endif
    rep #$20
    .a16
    pla
    plp
    rti
brk_handler:
.if SAME_BUILD_SCUMM_SYNTHETIC_BOOTSTRAP
    ; Capture the native interrupt frame before changing S, then freeze. These
    ; fields are diagnostic-only in the synthetic-bootstrap personality.
    rep #$30
    .a16
    .i16
    sta.l SAME_RESET_DIAG_LAST_A
    txa
    sta.l SAME_RESET_DIAG_LAST_X
    tya
    sta.l SAME_RESET_DIAG_LAST_Y
    tsc
    sta.l SAME_RESET_DIAG_LAST_S
    tax
    sep #$20
    .a8
    lda.l $000001,x
    sta.l SAME_RESET_DIAG_LAST_P
    lda.l $000002,x
    sta.l SAME_RESET_DIAG_LAST_PC
    lda.l $000003,x
    sta.l SAME_RESET_DIAG_LAST_PC+1
    lda.l $000004,x
    sta.l SAME_RESET_DIAG_LAST_PBR
    ; Copy the hardware frame and caller stack bytes while the interrupt S is
    ; still live. Use two long pointers because 65816 has no long,Y store.
    rep #$20
    .a16
    tsc
    inc
    sta.l SAME_RESET_DIAG_STACK_SOURCE
    lda #$0000
    tcd
    lda.l SAME_RESET_DIAG_STACK_SOURCE
    sta $00
    lda #$0000
    sta $02
    ; Keep the copied frame beside the reset diagnostic record. This pointer
    ; must track SAME_RESET_DIAG_STACK when the reserved high-WRAM block moves.
    lda #$F491
    sta $04
    sep #$20
    .a8
    lda #$7F
    sta $06
    ldy #$0000
.i16
brk_handler__capture_stack:
    .a8
    .i16
    lda [$00],y
    sta [$04],y
    iny
    cpy #SAME_RESET_DIAG_STACK_SIZE
    bcc brk_handler__capture_stack
    stp
.endif
    php
    rep #$30
    .a16
    .i16
    pha
    sep #$20
    .a8
.if SAME_BUILD_RESET_DIAGNOSTICS
    lda.l SAME_RESET_DIAG_BRK
    inc
    sta.l SAME_RESET_DIAG_BRK
.endif
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
.if SAME_BUILD_SCUMM_M23A || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
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

; TAD protocol-v20 loader, driver, and generated music data. These are built
; from the selected profile before assembly; no game audio is bundled here.
.bank 1
.org $8000
Same_Tad_AudioData:
    .incbin "../../build/audio/tad-bank1.bin"
.bank 2
.org $8000
Same_Tad_AudioData_High:
    .incbin "../../build/audio/tad-bank2.bin"
Same_Tad_BlankSong:
    .byte $00
.if SAME_BUILD_SCUMM_M23A || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
.include "generated/scumm_v5_room_data.inc.pasm"
.if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR
; M24R-B1 cold helper closure. Profile room payloads currently occupy banks 3-8;
; bank 9 is reserved for validator/lifecycle code and remains below 32 KiB.
.bank 9
.org $8000
.if SAME_BUILD_SCUMM_PHASE6LA1D == $01 || SAME_BUILD_SCUMM_CONTROLLER_CONFORMANCE
; Validation-only C2 payload is cold data.  Keep its canonical labels for the
; bank-zero fixture dispatcher while placing the cohesive block in bank 9.
.include "generated/scumm_v5_conformance_far.inc.pasm"
.endif
.endif
.if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR || SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_FAR_ROOM_VALIDATOR
.include "generated/scumm_v5_room_validator_far.inc.pasm"
.endif
.if SAME_BUILD_SCUMM_ROOM_SERVICE_FAR
.include "engines/scumm_v5_m24rb_far.pasm"
.endif
.if SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
.include "engines/scumm_v5_object_name_cache_far.pasm"
.endif
.if SAME_BUILD_SCUMM_CONTROLLER
.include "engines/scumm_v5_controller_far.pasm"
.endif
; With M24R-B this follows its bank-9 closure; otherwise it follows generated
; room data in that data bank. Either placement keeps the cold handler out of
; bank 0 without duplicating its source include.
.include "engines/scumm_v5_matrix_far.pasm"
.if SAME_BUILD_SCUMM_DYNAMIC_PROGRAM_RESIDENCY
.include "engines/scumm_v5_resident_resolver.pasm"
.endif
.include "engines/scumm_v5_camera_far.pasm"
.if SAME_VIDEO_BACKEND_LEGACY
.include "services/video_k1_far.pasm"
.endif
ScummV5_M24RB_FarCodeEnd:
.endif
.include "generated/carrier_code.inc.pasm"
.include "generated/video_backend_code.inc.pasm"
.include "generated/video_overlay_code.inc.pasm"
.if SAME_VIDEO_OVERLAY_BG2
.include "generated/scumm_v5_font.inc.pasm"
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
