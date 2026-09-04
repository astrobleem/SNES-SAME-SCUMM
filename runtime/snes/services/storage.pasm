; Storage ABI endpoint placeholder.  SAME package directory reads and MSU-1 seeks
; land here; no target may access MSU registers directly once this backend exists.
Same_Storage_Reset:
.if SAME_BUILD_SCUMM_M20
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SAVE_STATUS
    sta.l SAME_SAVE_LAST_ERROR
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SAVE_WRITE_COUNT
    sta.l SAME_SAVE_LOAD_COUNT
    sta.l SAME_SAVE_REJECT_COUNT
.endif
    rts

Same_Storage_Handle:
 .if SAME_BUILD_SCUMM_M23A
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_STORAGE_OP_READ
    bne Same_Storage_Handle__m23a_done
    lda.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    cmp #SAME_ENDPOINT_PROFILE
    bne Same_Storage_Handle__m23a_done
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp.l SAME_SCUMM_M23A_PENDING_ROOM
    bne Same_Storage_Handle__m23a_failed
    jsr ScummV5_M23A_FindRoom
    bcs Same_Storage_Handle__m23a_failed
    sta.l SAME_SCUMM_M23A_PENDING_RECORD
    .if SAME_BUILD_M24RB || SAME_BUILD_SCUMM_PHASE6HB
    jsl ScummV5_M23A_ValidateRecord_FarEntry
    .else
    jsr ScummV5_M23A_ValidateRecord
    .endif
    bcs Same_Storage_Handle__m23a_failed
    rep #$20
    .a16
    lda #$0104 ; observed SAME Storage READ service/opcode
    sta.l SAME_SCUMM_M23A_BYTE
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_VALIDATION_COUNT
    inc
    sta.l SAME_SCUMM_M23A_VALIDATION_COUNT
    lda #$02
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_Trace_FarEntry
    .else
    jsr ScummV5_M23A_Trace
    .endif
    lda #$05
    sta.l SAME_SCUMM_M23A_PHASE
    rts
Same_Storage_Handle__m23a_failed:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_M23A_PENDING_RECORD
    lda #$06
    sta.l SAME_SCUMM_M23A_PHASE
Same_Storage_Handle__m23a_done:
 .endif
    rts

Same_Save_Handle:
.if SAME_BUILD_SCUMM_M20
    php
    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    cmp #SAME_SAVE_OP_WRITE_SLOT
    beq Same_Save_Handle__write
    cmp #SAME_SAVE_OP_READ_SLOT
    beq Same_Save_Handle__read
    lda #SAME_SAVE_ERROR_OPERATION
    jmp Same_Save_Reject

Same_Save_Handle__write:
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp #$0063
    beq Same_Save_Handle__write_slot_ok
    sep #$20
    .a8
    lda #SAME_SAVE_ERROR_SLOT
    jmp Same_Save_Reject
Same_Save_Handle__write_slot_ok:
    jsr Same_Save_BuildEnvelope
    bcs Same_Save_Handle__write_failed
    ; Invalidate the SRAM record before copying it. The first magic byte is
    ; committed last, so an interrupted write cannot become loadable.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SAVE_STORAGE_BASE
    rep #$10
    .i16
    ldx #$0001
Same_Save_Handle__write_copy:
    .a8
    .i16
    lda.l SAME_SAVE_STAGING,x
    sta.l SAME_SAVE_STORAGE_BASE,x
    inx
    cpx #SAME_SAVE_RECORD_SIZE
    bcc Same_Save_Handle__write_copy
    lda.l SAME_SAVE_STAGING
    sta.l SAME_SAVE_STORAGE_BASE
    rep #$20
    .a16
    lda.l SAME_SAVE_WRITE_COUNT
    inc
    sta.l SAME_SAVE_WRITE_COUNT
    sep #$20
    .a8
    lda #SAME_SAVE_STATUS_WRITTEN
    sta.l SAME_SAVE_STATUS
    lda #SAME_SAVE_ERROR_NONE
    sta.l SAME_SAVE_LAST_ERROR
    plp
    rts
Same_Save_Handle__write_failed:
    sep #$20
    .a8
    lda #SAME_SAVE_ERROR_PAYLOAD
    jmp Same_Save_Reject

Same_Save_Handle__read:
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    cmp #$0063
    beq Same_Save_Handle__read_slot_ok
    sep #$20
    .a8
    lda #SAME_SAVE_ERROR_SLOT
    jmp Same_Save_Reject
Same_Save_Handle__read_slot_ok:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
Same_Save_Handle__read_copy:
    .a8
    .i16
    lda.l SAME_SAVE_STORAGE_BASE,x
    sta.l SAME_SAVE_STAGING,x
    inx
    cpx #SAME_SAVE_RECORD_SIZE
    bcc Same_Save_Handle__read_copy
    jsr Same_Save_ValidateEnvelope
    bcs Same_Save_Handle__read_failed
    jsr Same_ActiveEngine_ValidateCompiledMusic
    bcs Same_Save_Handle__read_failed
    ; No engine or audio state has changed above this point.
    jsr Same_ActiveEngine_ApplyCompiledMusic
    bcs Same_Save_Handle__read_apply_failed
    rep #$20
    .a16
    lda.l SAME_SAVE_LOAD_COUNT
    inc
    sta.l SAME_SAVE_LOAD_COUNT
    sep #$20
    .a8
    lda #SAME_SAVE_STATUS_LOADED
    sta.l SAME_SAVE_STATUS
    lda #SAME_SAVE_ERROR_NONE
    sta.l SAME_SAVE_LAST_ERROR
    plp
    rts
Same_Save_Handle__read_apply_failed:
    sep #$20
    .a8
    lda #SAME_SAVE_ERROR_QUEUE
    jmp Same_Save_Reject
Same_Save_Handle__read_failed:
    sep #$20
    .a8
    lda #SAME_SAVE_ERROR_VALIDATION
    jmp Same_Save_Reject

; Rejects preserve all engine/audio state. A contains the observable reason.
Same_Save_Reject:
    .a8
    sta.l SAME_SAVE_LAST_ERROR
    lda #SAME_SAVE_STATUS_REJECTED
    sta.l SAME_SAVE_STATUS
    rep #$20
    .a16
    lda.l SAME_SAVE_REJECT_COUNT
    inc
    sta.l SAME_SAVE_REJECT_COUNT
    plp
    rts
.else
    rts
.endif

; Carrier-neutral cold-boot probe used only by the persistence conformance
; personality. Carry set means the envelope magic is present; the normal load
; service still performs schema, identity, and CRC validation.
.if SAME_BUILD_SCUMM_SAVE_PERSISTENCE_VALIDATOR
Same_Save_HasEnvelopeMagic:
    php
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
Same_Save_HasEnvelopeMagic__loop:
    .a8
    lda.l SAME_SAVE_STORAGE_BASE,x
    cmp.l Same_Save_Magic,x
    bne Same_Save_HasEnvelopeMagic__missing
    inx
    cpx #$0008
    bcc Same_Save_HasEnvelopeMagic__loop
    plp
    sec
    rts
Same_Save_HasEnvelopeMagic__missing:
    plp
    clc
    rts
.endif ; SAME_BUILD_SCUMM_SAVE_PERSISTENCE_VALIDATOR

.if SAME_BUILD_SCUMM_M20
SAME_SAVE_STATUS_IDLE       = $00
SAME_SAVE_STATUS_WRITTEN    = $01
SAME_SAVE_STATUS_LOADED     = $02
SAME_SAVE_STATUS_REJECTED   = $FF
SAME_SAVE_ERROR_NONE        = $00
SAME_SAVE_ERROR_OPERATION   = $01
SAME_SAVE_ERROR_SLOT        = $02
SAME_SAVE_ERROR_PAYLOAD     = $03
SAME_SAVE_ERROR_VALIDATION  = $04
SAME_SAVE_ERROR_QUEUE       = $05
SAME_SAVE_HEADER_SIZE       = $0058
.if SAME_BUILD_SCUMM_M21
.if SAME_BUILD_SCUMM_M22
SAME_SAVE_PAYLOAD_SIZE      = $00FC
.else
SAME_SAVE_PAYLOAD_SIZE      = $0074
.endif
.else
SAME_SAVE_PAYLOAD_SIZE      = $0054
.endif

Same_Save_BuildEnvelope:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
Same_Save_BuildEnvelope__clear:
    .a8
    .i16
    lda #$00
    sta.l SAME_SAVE_STAGING,x
    inx
    cpx #SAME_SAVE_RECORD_SIZE
    bcc Same_Save_BuildEnvelope__clear
    ldx #$0000
Same_Save_BuildEnvelope__magic:
    .a8
    .i16
    lda.l Same_Save_Magic,x
    sta.l SAME_SAVE_STAGING,x
    inx
    cpx #$0008
    bcc Same_Save_BuildEnvelope__magic
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SAVE_STAGING+$08
    lda #SCUMM_V5_SAVE_SCHEMA
    sta.l SAME_SAVE_STAGING+$0C
    lda #$0000
    sta.l SAME_SAVE_STAGING+$0E
    lda #SAME_SAVE_PAYLOAD_SIZE
    sta.l SAME_SAVE_STAGING+$50
    lda #$0000
    sta.l SAME_SAVE_STAGING+$52
    sep #$20
    .a8
    ldx #$0000
Same_Save_BuildEnvelope__engine:
    .a8
    .i16
    lda.l Same_Save_EngineIdentity,x
    sta.l SAME_SAVE_STAGING+$10,x
    lda.l Same_Save_GameIdentity,x
    sta.l SAME_SAVE_STAGING+$30,x
    inx
    cpx #$0020
    bcc Same_Save_BuildEnvelope__engine
    jsr Same_ActiveEngine_SaveCompiledMusic
    bcs Same_Save_BuildEnvelope__failed
    jsr Same_Save_CrcPayload
    sep #$20
    .a8
    lda.l SAME_SAVE_CRC0
    sta.l SAME_SAVE_STAGING+$54
    lda.l SAME_SAVE_CRC1
    sta.l SAME_SAVE_STAGING+$55
    lda.l SAME_SAVE_CRC2
    sta.l SAME_SAVE_STAGING+$56
    lda.l SAME_SAVE_CRC3
    sta.l SAME_SAVE_STAGING+$57
    clc
    rts
Same_Save_BuildEnvelope__failed:
    sec
    rts

Same_Save_ValidateEnvelope:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
Same_Save_ValidateEnvelope__magic:
    .a8
    .i16
    lda.l SAME_SAVE_STAGING,x
    cmp.l Same_Save_Magic,x
    bne Same_Save_ValidateEnvelope__bad_early
    inx
    cpx #$0008
    bcc Same_Save_ValidateEnvelope__magic
    bra Same_Save_ValidateEnvelope__header
Same_Save_ValidateEnvelope__bad_early:
    sec
    rts
Same_Save_ValidateEnvelope__header:
    rep #$20
    .a16
    lda.l SAME_SAVE_STAGING+$08
    cmp #$0001
    bne Same_Save_ValidateEnvelope__bad16
    lda.l SAME_SAVE_STAGING+$0A
    bne Same_Save_ValidateEnvelope__bad16
    lda.l SAME_SAVE_STAGING+$0C
    cmp #SCUMM_V5_SAVE_SCHEMA
    bne Same_Save_ValidateEnvelope__bad16
    lda.l SAME_SAVE_STAGING+$0E
    bne Same_Save_ValidateEnvelope__bad16
    lda.l SAME_SAVE_STAGING+$50
    cmp #SAME_SAVE_PAYLOAD_SIZE
    bne Same_Save_ValidateEnvelope__bad16
    lda.l SAME_SAVE_STAGING+$52
    bne Same_Save_ValidateEnvelope__bad16
    sep #$20
    .a8
    ldx #$0000
Same_Save_ValidateEnvelope__identity:
    .a8
    .i16
    lda.l SAME_SAVE_STAGING+$10,x
    cmp.l Same_Save_EngineIdentity,x
    bne Same_Save_ValidateEnvelope__bad
    lda.l SAME_SAVE_STAGING+$30,x
    cmp.l Same_Save_GameIdentity,x
    bne Same_Save_ValidateEnvelope__bad
    inx
    cpx #$0020
    bcc Same_Save_ValidateEnvelope__identity
    jsr Same_Save_CrcPayload
    lda.l SAME_SAVE_CRC0
    cmp.l SAME_SAVE_STAGING+$54
    bne Same_Save_ValidateEnvelope__bad
    lda.l SAME_SAVE_CRC1
    cmp.l SAME_SAVE_STAGING+$55
    bne Same_Save_ValidateEnvelope__bad
    lda.l SAME_SAVE_CRC2
    cmp.l SAME_SAVE_STAGING+$56
    bne Same_Save_ValidateEnvelope__bad
    lda.l SAME_SAVE_CRC3
    cmp.l SAME_SAVE_STAGING+$57
    bne Same_Save_ValidateEnvelope__bad
    clc
    rts
Same_Save_ValidateEnvelope__bad16:
    sep #$20
    .a8
Same_Save_ValidateEnvelope__bad:
    sec
    rts

; Reflected CRC-32 over the fixed payload, polynomial EDB88320. Scratch lives
; in four otherwise-unused bytes after the staging record.
SAME_SAVE_CRC0 = SAME_SAVE_STAGING+SAME_SAVE_RECORD_SIZE
SAME_SAVE_CRC1 = SAME_SAVE_CRC0+1
SAME_SAVE_CRC2 = SAME_SAVE_CRC0+2
SAME_SAVE_CRC3 = SAME_SAVE_CRC0+3
SAME_SAVE_CRC_BITS = SAME_SAVE_CRC0+4

Same_Save_CrcPayload:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SAVE_CRC0
    sta.l SAME_SAVE_CRC1
    sta.l SAME_SAVE_CRC2
    sta.l SAME_SAVE_CRC3
    rep #$10
    .i16
    ldx #SAME_SAVE_HEADER_SIZE
Same_Save_CrcPayload__byte:
    .a8
    .i16
    lda.l SAME_SAVE_STAGING,x
    eor.l SAME_SAVE_CRC0
    sta.l SAME_SAVE_CRC0
    lda #$08
    sta.l SAME_SAVE_CRC_BITS
Same_Save_CrcPayload__bit:
    .a8
    lda.l SAME_SAVE_CRC3
    lsr
    sta.l SAME_SAVE_CRC3
    lda.l SAME_SAVE_CRC2
    ror
    sta.l SAME_SAVE_CRC2
    lda.l SAME_SAVE_CRC1
    ror
    sta.l SAME_SAVE_CRC1
    lda.l SAME_SAVE_CRC0
    ror
    sta.l SAME_SAVE_CRC0
    bcc Same_Save_CrcPayload__no_xor
    lda.l SAME_SAVE_CRC0
    eor #$20
    sta.l SAME_SAVE_CRC0
    lda.l SAME_SAVE_CRC1
    eor #$83
    sta.l SAME_SAVE_CRC1
    lda.l SAME_SAVE_CRC2
    eor #$B8
    sta.l SAME_SAVE_CRC2
    lda.l SAME_SAVE_CRC3
    eor #$ED
    sta.l SAME_SAVE_CRC3
Same_Save_CrcPayload__no_xor:
    .a8
    lda.l SAME_SAVE_CRC_BITS
    dec
    sta.l SAME_SAVE_CRC_BITS
    bne Same_Save_CrcPayload__bit
    inx
    cpx #SAME_SAVE_RECORD_SIZE
    bcc Same_Save_CrcPayload__byte
    lda.l SAME_SAVE_CRC0
    eor #$FF
    sta.l SAME_SAVE_CRC0
    lda.l SAME_SAVE_CRC1
    eor #$FF
    sta.l SAME_SAVE_CRC1
    lda.l SAME_SAVE_CRC2
    eor #$FF
    sta.l SAME_SAVE_CRC2
    lda.l SAME_SAVE_CRC3
    eor #$FF
    sta.l SAME_SAVE_CRC3
    rts

Same_Save_Magic:
    .byte $53,$41,$4D,$45,$53,$41,$56,$00 ; SAMESAV\0
.include "../generated/save_identity.inc.pasm"
.endif

Same_Jobs_Handle:
    rts
