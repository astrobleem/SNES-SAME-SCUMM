; Experimental native ProgramUnit -> byte-selector binder.
;
; This include is present only in explicitly selected dynamic-residency builds.
; The canonical ID directory is compiler generated.  The selector pool mirrors
; the accepted 48 + 130 allocator policy: D0..FF, then CF..4E.  C4 slot program
; bytes are the live-owner pins; active room bundles and explicit API owners
; use independent bits in the per-binding flags.

SCUMM_RESIDENT_FLAG_VALID       = $01
SCUMM_RESIDENT_FLAG_ROOM_BUNDLE = $02
SCUMM_RESIDENT_FLAG_EXPLICIT    = $04
SCUMM_RESIDENT_FLAG_C4_LIVE     = $08
SCUMM_RESIDENT_SELECTOR_COUNT  = $00B2
SCUMM_RESIDENT_DP_PROGRAM_PTR  = $00F9

; Cold reset. IDs are canonical ProgramUnit IDs; $FFFF is never a valid ID.
ScummV5_Resident_Reset_Far:
    php
    rep #$30
    .a16
    .i16
    lda #$FFFF
    ldx #$0000
ScummV5_Resident_Reset_Far__ids:
    .a16
    .i16
    sta.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    inx
    inx
    cpx #(SCUMM_RESIDENT_SELECTOR_COUNT * 2)
    bcc ScummV5_Resident_Reset_Far__ids
    lda #$0000
    ldx #$0000
ScummV5_Resident_Reset_Far__generations:
    .a16
    .i16
    sta.l SAME_SCUMM_RESIDENT_GENERATIONS,x
    inx
    inx
    cpx #(SCUMM_RESIDENT_SELECTOR_COUNT * 2)
    bcc ScummV5_Resident_Reset_Far__generations
    sep #$20
    .a8
    lda #$00
    ldx #$0000
ScummV5_Resident_Reset_Far__flags:
    .a8
    .i16
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    inx
    cpx #SCUMM_RESIDENT_SELECTOR_COUNT
    bcc ScummV5_Resident_Reset_Far__flags
    lda #$00
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    sta.l SAME_SCUMM_RESIDENT_PEAK_COUNT
    sta.l SAME_SCUMM_RESIDENT_PINNED_COUNT
    sta.l SAME_SCUMM_RESIDENT_PEAK_PINNED
    sta.l SAME_SCUMM_RESIDENT_BIND_COUNT
    sta.l SAME_SCUMM_RESIDENT_REUSE_COUNT
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_LOADS
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RELEASES
    sta.l SAME_SCUMM_RESIDENT_DYNAMIC_LOOKUPS
    sta.l SAME_SCUMM_RESIDENT_EXHAUSTIONS
    sta.l SAME_SCUMM_RESIDENT_STALE_COUNT
    plp
    clc
    rtl

; Input A=u16 canonical ProgramUnit ID. Output A=u8 resident selector, carry
; set. On invalid IDs or exhaustion, carry clears and SAME_SCUMM_ERROR records
; a distinct resolver error; no pinned binding is ever modified.
ScummV5_Resident_ResolveProgramUnit_Far:
    php
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_RESIDENT_REQUEST_ID
    cmp #$FFFF
    beq ScummV5_Resident_ResolveProgramUnit_Far__invalid
    .if SCUMM_RESIDENT_UNIT_COUNT > $0000
    cmp #SCUMM_RESIDENT_UNIT_COUNT
    bcs ScummV5_Resident_ResolveProgramUnit_Far__invalid
    .else
    bra ScummV5_Resident_ResolveProgramUnit_Far__invalid
    .endif
    ldx #$0000
ScummV5_Resident_ResolveProgramUnit_Far__find:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp.l SAME_SCUMM_RESIDENT_REQUEST_ID
    beq ScummV5_Resident_ResolveProgramUnit_Far__found
    inx
    inx
    cpx #(SCUMM_RESIDENT_SELECTOR_COUNT * 2)
    bcc ScummV5_Resident_ResolveProgramUnit_Far__find
    ; Pass one: first empty selector.
    ldx #$0000
ScummV5_Resident_ResolveProgramUnit_Far__free:
    .a16
    .i16
    txa
    lsr
    sta.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    beq ScummV5_Resident_ResolveProgramUnit_Far__candidate
    rep #$20
    .a16
    txa
    asl
    tax
    inx
    inx
    cpx #(SCUMM_RESIDENT_SELECTOR_COUNT * 2)
    bcc ScummV5_Resident_ResolveProgramUnit_Far__free
    ; Pass two: first binding with no explicit/bundle pin and no live C4 owner.
    ldx #$0000
ScummV5_Resident_ResolveProgramUnit_Far__evict:
    .a16
    .i16
    txa
    lsr
    sta.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #(SCUMM_RESIDENT_FLAG_ROOM_BUNDLE | SCUMM_RESIDENT_FLAG_EXPLICIT)
    bne ScummV5_Resident_ResolveProgramUnit_Far__evict_next
    jsr ScummV5_Resident_IndexToSelector
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_IsSelectorLive
    bcs ScummV5_Resident_ResolveProgramUnit_Far__evict_next
    bra ScummV5_Resident_ResolveProgramUnit_Far__candidate
ScummV5_Resident_ResolveProgramUnit_Far__evict_next:
    rep #$20
    .a16
    txa
    asl
    tax
    inx
    inx
    cpx #(SCUMM_RESIDENT_SELECTOR_COUNT * 2)
    bcc ScummV5_Resident_ResolveProgramUnit_Far__evict
    sep #$20
    .a8
    ; These are u16 counters.  Never silently wrap after 255 binds.
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_EXHAUSTIONS
    inc
    sta.l SAME_SCUMM_RESIDENT_EXHAUSTIONS
    sep #$20
    .a8
    lda #SCUMM_ERR_RESIDENCY_EXHAUSTED
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl
ScummV5_Resident_ResolveProgramUnit_Far__invalid:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl
ScummV5_Resident_ResolveProgramUnit_Far__found:
    rep #$20
    .a16
    txa
    lsr
    tax
    jsr ScummV5_Resident_IndexToSelector
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    plp
    sec
    rtl
ScummV5_Resident_ResolveProgramUnit_Far__candidate:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_REQUEST_ID
    sta.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    lda.l SAME_SCUMM_RESIDENT_GENERATIONS,x
    inc
    bne ScummV5_Resident_ResolveProgramUnit_Far__generation_ready
    lda #$0001
ScummV5_Resident_ResolveProgramUnit_Far__generation_ready:
    sta.l SAME_SCUMM_RESIDENT_GENERATIONS,x
    ; ProgramUnit IDs are 16-bit. After the request ID load, A's hidden B
    ; accumulator byte may be nonzero; widen the pool-index load before TAX so
    ; it cannot leak that stale high byte into the flags-table index.
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    bne ScummV5_Resident_ResolveProgramUnit_Far__reuse
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    cmp.l SAME_SCUMM_RESIDENT_PEAK_COUNT
    bcc ScummV5_Resident_ResolveProgramUnit_Far__new_peak_done
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    sta.l SAME_SCUMM_RESIDENT_PEAK_COUNT
ScummV5_Resident_ResolveProgramUnit_Far__new_peak_done:
    sep #$20
    .a8
    bra ScummV5_Resident_ResolveProgramUnit_Far__set_valid
ScummV5_Resident_ResolveProgramUnit_Far__reuse:
    lda.l SAME_SCUMM_RESIDENT_REUSE_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_REUSE_COUNT
    sep #$20
    .a8
ScummV5_Resident_ResolveProgramUnit_Far__set_valid:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda #SCUMM_RESIDENT_FLAG_VALID
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BIND_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_BIND_COUNT
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    jsr ScummV5_Resident_IndexToSelector
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    plp
    sec
    rtl

; Input X=pool index (0..177), output A=selector byte. Pool order is exactly
; the established primary and overflow allocator order.
ScummV5_Resident_IndexToSelector:
    rep #$20
    .a16
    txa
    cmp #$0030
    bcs ScummV5_Resident_IndexToSelector__overflow
    clc
    adc #$00D0
    sep #$20
    .a8
    rts
ScummV5_Resident_IndexToSelector__overflow:
    .a16
    txa
    eor #$FFFF
    inc
    clc
    adc #$00FF
    ; Pool index 48 maps to $CF; index 177 maps to $4E.
    sep #$20
    .a8
    rts

; Input A=selector byte. Carry set if an active scheduler slot owns it.
; C19 overrides, cutscene frames, nested parents and room continuations all
; retain their owning activation slot, so they inherit this pin without
; decorative duplicate counters.
ScummV5_Resident_IsSelectorLive:
    ; The caller's deterministic eviction scan carries its pool cursor in X.
    ; Preserve it across this C4-slot scan so a live binding cannot redirect
    ; the next candidate to an unrelated selector.
    phx
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    ldx #$0000
ScummV5_Resident_IsSelectorLive__slot:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Resident_IsSelectorLive__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Resident_IsSelectorLive__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_Resident_IsSelectorLive__next
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    cmp.l SAME_SCUMM_RESIDENT_SELECTOR
    beq ScummV5_Resident_IsSelectorLive__yes
ScummV5_Resident_IsSelectorLive__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Resident_IsSelectorLive__slot
    plx
    clc
    rts
ScummV5_Resident_IsSelectorLive__yes:
    plx
    sec
    rts

; Public explicit pin API. A=selector. Room-bundle pins are separate so room
; release cannot accidentally clear a caller-owned pin.
ScummV5_Resident_PinProgram_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    lda #SCUMM_RESIDENT_FLAG_EXPLICIT
    bra ScummV5_Resident_SetPin_Far
ScummV5_Resident_PinRoomBundle_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    lda #SCUMM_RESIDENT_FLAG_ROOM_BUNDLE
ScummV5_Resident_SetPin_Far:
    sta.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    bcc ScummV5_Resident_SetPin_Far__bad
    rep #$20
    .a16
    txa
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp #$FFFF
    beq ScummV5_Resident_SetPin_Far__bad16
    ; The loaded canonical ID may have set the hidden high accumulator byte.
    ; Use the full pool-index word for the X16 flags lookup.
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_SetPin_Far__bad
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    ora.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    plp
    clc
    rtl
ScummV5_Resident_SetPin_Far__bad16:
    sep #$20
    .a8
ScummV5_Resident_SetPin_Far__bad:
    plp
    sec
    rtl

ScummV5_Resident_UnpinProgram_Far:
    ; A8=selector; X8=pin mask.  The convenience API below clears the
    ; explicit-owner bit; room release uses the room-bundle-specific entry.
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    lda #SCUMM_RESIDENT_FLAG_EXPLICIT
    eor #$FF
    sta.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    ; SelectorToIndex returns a 16-bit index and therefore leaves M=1. The
    ; carry result survives SEP, but byte flag loads below must be A8.
    sep #$20
    .a8
    bcc ScummV5_Resident_UnpinProgram_Far__bad
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_UnpinProgram_Far__bad
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    plp
    clc
    rtl
ScummV5_Resident_UnpinProgram_Far__bad:
    plp
    sec
    rtl

ScummV5_Resident_UnpinRoomBundle_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    lda #SCUMM_RESIDENT_FLAG_ROOM_BUNDLE
    eor #$FF
    sta.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    sep #$20
    .a8
    bcc ScummV5_Resident_UnpinProgram_Far__bad
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_UnpinProgram_Far__bad
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and.l SAME_SCUMM_RESIDENT_FLAGS_SCRATCH
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    plp
    clc
    rtl

; Validate a saved diagnostic/reference token. Input selector is in the common
; scratch byte and expected canonical ID/generation are explicit, so a stale
; handle can never execute the program which later reused its selector.
ScummV5_Resident_ValidateReference_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    bcc ScummV5_Resident_ValidateReference_Far__stale
    rep #$20
    .a16
    txa
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp.l SAME_SCUMM_RESIDENT_EXPECTED_ID
    bne ScummV5_Resident_ValidateReference_Far__stale16
    lda.l SAME_SCUMM_RESIDENT_GENERATIONS,x
    cmp.l SAME_SCUMM_RESIDENT_EXPECTED_GENERATION
    bne ScummV5_Resident_ValidateReference_Far__stale16
    plp
    clc
    rtl
ScummV5_Resident_ValidateReference_Far__stale16:
    sep #$20
    .a8
ScummV5_Resident_ValidateReference_Far__stale:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_STALE_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_STALE_COUNT
    sep #$20
    .a8
    plp
    sec
    rtl

; Convert pool index in A16 to a pool index from the incoming byte selector.
; Carry clear means the byte is outside the exact current allocator pool.
ScummV5_Resident_SelectorToIndex:
    sep #$20
    .a8
    cmp #$D0
    bcc ScummV5_Resident_SelectorToIndex__overflow
    rep #$20
    .a16
    and #$00FF
    sec
    sbc #$00D0
    sta.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sec
    rts
ScummV5_Resident_SelectorToIndex__overflow:
    .a8
    cmp #$4E
    bcc ScummV5_Resident_SelectorToIndex__invalid
    cmp #$D0
    bcs ScummV5_Resident_SelectorToIndex__invalid
    rep #$20
    .a16
    and #$00FF
    eor #$FFFF
    inc
    ; $FF - selector yields pool index 48..177 for $CF..$4E.
    clc
    adc #$00FF
    sta.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sec
    rts
ScummV5_Resident_SelectorToIndex__invalid:
    clc
    rts

; Selector -> canonical directory ID. The ID is written to EXPECTED_ID so the
; result survives the caller's accumulator-width convention. Carry set means
; the selector is currently bound; an empty/stale selector is rejected.
ScummV5_Resident_ProgramUnitForSelector_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    ; SelectorToIndex's successful paths return A16; normalize before reading
    ; the byte-sized residency flags. SEP does not disturb the carry result.
    sep #$20
    .a8
    bcc ScummV5_Resident_ProgramUnitForSelector_Far__bad_selector
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_ProgramUnitForSelector_Far__bad_flags
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp #$FFFF
    beq ScummV5_Resident_ProgramUnitForSelector_Far__bad16
    sta.l SAME_SCUMM_RESIDENT_EXPECTED_ID
    plp
    sec
    rtl
ScummV5_Resident_ProgramUnitForSelector_Far__bad16:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    bra ScummV5_Resident_ProgramUnitForSelector_Far__bad
ScummV5_Resident_ProgramUnitForSelector_Far__bad_selector:
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    bra ScummV5_Resident_ProgramUnitForSelector_Far__bad
ScummV5_Resident_ProgramUnitForSelector_Far__bad_flags:
    .a8
    lda #$02
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
ScummV5_Resident_ProgramUnitForSelector_Far__bad:
    .a8
    .if SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    sta.l SAME_SCUMM_RESIDENT_DIAG_RETURNED
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    sta.l SAME_SCUMM_RESIDENT_DIAG_POOL_INDEX
    cmp #SCUMM_RESIDENT_SELECTOR_COUNT
    bcs ScummV5_Resident_ProgramUnitForSelector_Far__bad_diag_done
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    sta.l SAME_SCUMM_RESIDENT_DIAG_SCRATCH
ScummV5_Resident_ProgramUnitForSelector_Far__bad_diag_done:
    sep #$20
    .a8
    .endif
    lda #$02
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    .if SAME_BUILD_SCUMM_AUTHENTIC_BOOTSTRAP
    ; Native conformance breadcrumb: identify which generic VM caller supplied
    ; the invalid ephemeral handle. This is observational and profile-neutral.
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_ERROR_PROGRAM
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_ERROR_OPCODE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_ERROR_SLOT
    ; The PHP at this routine's entry is the top stack byte; the rejecting
    ; caller's JSL return frame begins at S+2. Keep it in bounded diagnostic
    ; scratch so a stale selector report identifies its actual VM call site.
    rep #$10
    .i16
    tsx
    sep #$20
    .a8
    lda 2,s
    sta.l SAME_SCUMM_RESIDENT_ERROR_CALLER_PC
    lda 3,s
    sta.l SAME_SCUMM_RESIDENT_ERROR_CALLER_PC+1
    lda 4,s
    sta.l SAME_SCUMM_RESIDENT_ERROR_CALLER_BANK
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_ERROR_PC
    sep #$20
    .a8
    .endif
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Input A=u16 canonical ProgramUnit ID; output A=u8 selector and carry set.
; Used by bundle release to remove only the matching room ownership pin.
ScummV5_Resident_FindSelectorForProgramUnit_Far:
    php
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_RESIDENT_REQUEST_ID
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
ScummV5_Resident_FindSelectorForProgramUnit_Far__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
    cmp #SCUMM_RESIDENT_SELECTOR_COUNT
    bcs ScummV5_Resident_FindSelectorForProgramUnit_Far__missing
    lda.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp.l SAME_SCUMM_RESIDENT_REQUEST_ID
    beq ScummV5_Resident_FindSelectorForProgramUnit_Far__found
    lda.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
    inc
    sta.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
    bra ScummV5_Resident_FindSelectorForProgramUnit_Far__loop
ScummV5_Resident_FindSelectorForProgramUnit_Far__found:
    lda.l SAME_SCUMM_RESIDENT_LOOKUP_INDEX
    tax
    jsr ScummV5_Resident_IndexToSelector
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    plp
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    sec
    rtl
ScummV5_Resident_FindSelectorForProgramUnit_Far__missing:
    plp
    clc
    rtl

; Resolve a dynamic StartScript target through the generated source-number
; directory. Candidate globals are not prebound; only this requested target is.
ScummV5_Resident_ResolveGlobalScript_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_GLOBAL_SCRIPT
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_DYNAMIC_LOOKUPS
    inc
    sta.l SAME_SCUMM_RESIDENT_DYNAMIC_LOOKUPS
    sep #$20
    .a8
    ldx #$0000
ScummV5_Resident_ResolveGlobalScript_Far__loop:
    .a8
    .i16
    cpx #SCUMM_RESIDENT_GLOBAL_COUNT
    bcs ScummV5_Resident_ResolveGlobalScript_Far__missing
    lda.l ScummV5_Resident_GlobalScriptNumbers,x
    cmp.l SAME_SCUMM_RESIDENT_GLOBAL_SCRIPT
    beq ScummV5_Resident_ResolveGlobalScript_Far__found
    inx
    bra ScummV5_Resident_ResolveGlobalScript_Far__loop
ScummV5_Resident_ResolveGlobalScript_Far__found:
    rep #$20
    .a16
    txa
    asl
    tax
    lda.l ScummV5_Resident_GlobalProgramUnitIds,x
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcs ScummV5_Resident_ResolveGlobalScript_Far__resolved
    plp
    clc
    rtl
ScummV5_Resident_ResolveGlobalScript_Far__resolved:
    plp
    sec
    rtl
ScummV5_Resident_ResolveGlobalScript_Far__missing:
    .a8
    lda #SCUMM_ERR_SCRIPT
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Resolve an LSCR number in the currently active resource record.
ScummV5_Resident_ResolveLocalScript_Far:
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    jml ScummV5_LiveRoom_ResolveLocalScript_Far
.endif
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_LOCAL_SCRIPT
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #SCUMM_M23A_ROOM_COUNT
    bcs ScummV5_Resident_ResolveLocalScript_Far__missing
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_Resident_RoomLocalOffsets,x
    sta.l SAME_SCUMM_RESIDENT_LOCAL_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    tax
    lda.l ScummV5_Resident_RoomLocalCounts,x
    sta.l SAME_SCUMM_RESIDENT_LOCAL_REMAINING
    rep #$20
    .a16
ScummV5_Resident_ResolveLocalScript_Far__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_LOCAL_REMAINING
    beq ScummV5_Resident_ResolveLocalScript_Far__missing
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_LOCAL_OFFSET
    tax
    sep #$20
    .a8
    lda.l ScummV5_Resident_RoomLocalNumbers,x
    cmp.l SAME_SCUMM_RESIDENT_LOCAL_SCRIPT
    beq ScummV5_Resident_ResolveLocalScript_Far__found
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_LOCAL_OFFSET
    inc
    sta.l SAME_SCUMM_RESIDENT_LOCAL_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_LOCAL_REMAINING
    dec
    sta.l SAME_SCUMM_RESIDENT_LOCAL_REMAINING
    bra ScummV5_Resident_ResolveLocalScript_Far__loop
ScummV5_Resident_ResolveLocalScript_Far__found:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_LOCAL_OFFSET
    asl
    tax
    lda.l ScummV5_Resident_RoomLocalUnitIds,x
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcs ScummV5_Resident_ResolveLocalScript_Far__resolved
    plp
    clc
    rtl
ScummV5_Resident_ResolveLocalScript_Far__resolved:
    plp
    sec
    rtl
ScummV5_Resident_ResolveLocalScript_Far__missing:
    .a8
    lda #SCUMM_ERR_SCRIPT
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Explicit bounded diagnostic census for resident and compiler-owned pins.
; Live C4-slot ownership is sampled by the native acceptance observer and is
; checked directly by the allocator before eviction; this routine deliberately
; does not mutate/scan scheduler state.
ScummV5_Resident_RefreshDiagnostics:
    php
    rep #$30
    .a16
    .i16
    phx
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    sta.l SAME_SCUMM_RESIDENT_PINNED_COUNT
    ldx #$0000
ScummV5_Resident_RefreshDiagnostics__count:
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_RefreshDiagnostics__next
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #(SCUMM_RESIDENT_FLAG_ROOM_BUNDLE | SCUMM_RESIDENT_FLAG_EXPLICIT)
    beq ScummV5_Resident_RefreshDiagnostics__next
ScummV5_Resident_RefreshDiagnostics__pinned:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_PINNED_COUNT
    inc
    sta.l SAME_SCUMM_RESIDENT_PINNED_COUNT
ScummV5_Resident_RefreshDiagnostics__next:
    rep #$20
    .a16
    inx
    cpx #SCUMM_RESIDENT_SELECTOR_COUNT
    bcc ScummV5_Resident_RefreshDiagnostics__count
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    cmp.l SAME_SCUMM_RESIDENT_PEAK_COUNT
    bcc ScummV5_Resident_RefreshDiagnostics__peak_pinned
    sta.l SAME_SCUMM_RESIDENT_PEAK_COUNT
ScummV5_Resident_RefreshDiagnostics__peak_pinned:
    lda.l SAME_SCUMM_RESIDENT_PINNED_COUNT
    cmp.l SAME_SCUMM_RESIDENT_PEAK_PINNED
    bcc ScummV5_Resident_RefreshDiagnostics__done
    sta.l SAME_SCUMM_RESIDENT_PEAK_PINNED
ScummV5_Resident_RefreshDiagnostics__done:
    plx
    plp
    rts

; Explicit diagnostic sampling point for native acceptance tooling.
ScummV5_Resident_RefreshDiagnostics_Far:
    jsr ScummV5_Resident_RefreshDiagnostics
    rtl

; Eagerly bind and room-pin every selector-bearing ProgramUnit in one bundle.
; On failure, unwind the partial bundle and leave an explicit resolver error.
ScummV5_Resident_LoadRoomBundle_Far:
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    jml ScummV5_LiveRoom_LoadBundle_Far
.endif
    php
    sep #$20
    .a8
    cmp #ScummV5_Resident_RoomBundleCount
    bcc ScummV5_Resident_LoadRoomBundle_Far__record_valid
    jmp ScummV5_Resident_LoadRoomBundle_Far__bad
ScummV5_Resident_LoadRoomBundle_Far__record_valid:
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_Resident_RoomBundleOffsets,x
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    tax
    lda.l ScummV5_Resident_RoomBundleCounts,x
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    rep #$20
    .a16
ScummV5_Resident_LoadRoomBundle_Far__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    beq ScummV5_Resident_LoadRoomBundle_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    asl
    tax
    lda.l ScummV5_Resident_RoomBundleUnitIds,x
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcc ScummV5_Resident_LoadRoomBundle_Far__rollback
    jsl ScummV5_Resident_PinRoomBundle_Far
    bcc ScummV5_Resident_LoadRoomBundle_Far__pinned
    ; Keep resolver and pin failures distinguishable.  PinRoomBundle's carry
    ; contract is clear-on-success, so this site identifies a selector that
    ; resolved but could not be made bundle-owned before rollback.
    lda #$05
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    bra ScummV5_Resident_LoadRoomBundle_Far__rollback
ScummV5_Resident_LoadRoomBundle_Far__pinned:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    dec
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    bra ScummV5_Resident_LoadRoomBundle_Far__loop
ScummV5_Resident_LoadRoomBundle_Far__done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_LOADS
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_LOADS
    plp
    sec
    rtl
ScummV5_Resident_LoadRoomBundle_Far__rollback:
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    jsl ScummV5_Resident_ReleaseRoomBundle_Far
    plp
    clc
    rtl
ScummV5_Resident_LoadRoomBundle_Far__bad:
    .a8
    lda #$03
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Remove only the room-bundle ownership pins for one record. Live activations
; and independent explicit pins remain protected by their own owners.
ScummV5_Resident_ReleaseRoomBundle_Far:
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    jml ScummV5_LiveRoom_ReleaseBundle_Far
.endif
    php
    sep #$20
    .a8
    cmp #ScummV5_Resident_RoomBundleCount
    bcs ScummV5_Resident_ReleaseRoomBundle_Far__bad
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_Resident_RoomBundleOffsets,x
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RECORD
    tax
    lda.l ScummV5_Resident_RoomBundleCounts,x
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
ScummV5_Resident_ReleaseRoomBundle_Far__loop:
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    beq ScummV5_Resident_ReleaseRoomBundle_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    asl
    tax
    lda.l ScummV5_Resident_RoomBundleUnitIds,x
    jsl ScummV5_Resident_FindSelectorForProgramUnit_Far
    bcc ScummV5_Resident_ReleaseRoomBundle_Far__next
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsl ScummV5_Resident_UnpinRoomBundle_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsl ScummV5_Resident_ReleaseIfUnowned_Far
ScummV5_Resident_ReleaseRoomBundle_Far__next:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    dec
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    bra ScummV5_Resident_ReleaseRoomBundle_Far__loop
ScummV5_Resident_ReleaseRoomBundle_Far__done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RELEASES
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RELEASES
    plp
    sec
    rtl
ScummV5_Resident_ReleaseRoomBundle_Far__bad:
    .a8
    lda #$04
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; A=selector. Once a room pin is removed, immediately make the binding empty
; only if no independent pin and no live C4 activation still owns the byte.
; This mirrors the compiler simulator's room-release contract and lets the
; incoming room consume reclaimed selector slots before scanning cold entries.
ScummV5_Resident_ReleaseIfUnowned_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_SelectorToIndex
    bcc ScummV5_Resident_ReleaseIfUnowned_Far__done
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #SCUMM_RESIDENT_FLAG_VALID
    beq ScummV5_Resident_ReleaseIfUnowned_Far__done
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    and #(SCUMM_RESIDENT_FLAG_ROOM_BUNDLE | SCUMM_RESIDENT_FLAG_EXPLICIT)
    bne ScummV5_Resident_ReleaseIfUnowned_Far__done
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsr ScummV5_Resident_IsSelectorLive
    bcs ScummV5_Resident_ReleaseIfUnowned_Far__done
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    txa
    asl
    tax
    lda #$FFFF
    sta.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_POOL_INDEX
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RESIDENT_FLAGS,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
    beq ScummV5_Resident_ReleaseIfUnowned_Far__done
    dec
    sta.l SAME_SCUMM_RESIDENT_CURRENT_COUNT
ScummV5_Resident_ReleaseIfUnowned_Far__done:
    plp
    rtl

.if SAME_BUILD_SCUMM_RESIDENCY_DIAGNOSTIC
; Dedicated native safety control. It pins every selector, verifies exhaustion
; is non-destructive, then releases/reuses D0 and rejects the stale (ID,gen)
; token before allowing the harness ROM to halt. This is not production boot
; behavior and never runs in ordinary dynamic-residency builds.
ScummV5_Resident_RunAcceptanceControl_Far:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_DIAG_STATUS
    sta.l SAME_SCUMM_RESIDENT_DIAG_STALE_REJECTED
    sta.l SAME_SCUMM_RESIDENT_DIAG_REBOUND_GENERATION
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    sta.l SAME_SCUMM_RESIDENT_DIAG_POOL_INDEX
    sta.l SAME_SCUMM_RESIDENT_DIAG_SCRATCH
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_DIAG_REBOUND_SELECTOR
    sta.l SAME_SCUMM_RESIDENT_DIAG_TABLE_UNCHANGED
    sta.l SAME_SCUMM_RESIDENT_DIAG_EXHAUSTION_ERROR
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
ScummV5_Resident_RunAcceptanceControl_Far__bind_pin:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcs ScummV5_Resident_RunAcceptanceControl_Far__bind_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail1
ScummV5_Resident_RunAcceptanceControl_Far__bind_ok:
    sep #$20
    .a8
    jsl ScummV5_Resident_PinProgram_Far
    bcc ScummV5_Resident_RunAcceptanceControl_Far__pin_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail2
ScummV5_Resident_RunAcceptanceControl_Far__pin_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    inc
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    cmp #SCUMM_RESIDENT_SELECTOR_COUNT
    bcc ScummV5_Resident_RunAcceptanceControl_Far__bind_pin

    ; Pool order and mappings must still be one-to-one after all 178 binds.
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
ScummV5_Resident_RunAcceptanceControl_Far__verify:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    asl
    tax
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS,x
    cmp.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    beq ScummV5_Resident_RunAcceptanceControl_Far__verify_id_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail3
ScummV5_Resident_RunAcceptanceControl_Far__verify_id_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_GENERATIONS,x
    cmp #$0001
    beq ScummV5_Resident_RunAcceptanceControl_Far__verify_generation_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail4
ScummV5_Resident_RunAcceptanceControl_Far__verify_generation_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    tax
    sep #$20
    .a8
    .i16
    lda.l SAME_SCUMM_RESIDENT_FLAGS,x
    cmp #(SCUMM_RESIDENT_FLAG_VALID | SCUMM_RESIDENT_FLAG_EXPLICIT)
    beq ScummV5_Resident_RunAcceptanceControl_Far__verify_flags_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail5
ScummV5_Resident_RunAcceptanceControl_Far__verify_flags_ok:
    .a8
    .i16
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    inc
    sta.l SAME_SCUMM_RESIDENT_DIAG_INDEX
    cmp #SCUMM_RESIDENT_SELECTOR_COUNT
    bcc ScummV5_Resident_RunAcceptanceControl_Far__verify
    jsr ScummV5_Resident_RefreshDiagnostics
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_DIAG_TABLE_UNCHANGED

    ; The 179th simultaneously pinned identity fails explicitly.
    rep #$20
    .a16
    lda #SCUMM_RESIDENT_SELECTOR_COUNT
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcc ScummV5_Resident_RunAcceptanceControl_Far__exhausted
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail6
ScummV5_Resident_RunAcceptanceControl_Far__exhausted:
    sep #$20
    .a8
    lda.l SAME_SCUMM_ERROR
    sta.l SAME_SCUMM_RESIDENT_DIAG_EXHAUSTION_ERROR
    cmp #SCUMM_ERR_RESIDENCY_EXHAUSTED
    beq ScummV5_Resident_RunAcceptanceControl_Far__error_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail7
ScummV5_Resident_RunAcceptanceControl_Far__error_ok:
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_EXHAUSTIONS
    cmp #$0001
    beq ScummV5_Resident_RunAcceptanceControl_Far__count_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail8
ScummV5_Resident_RunAcceptanceControl_Far__count_ok:
    .a16
    .i16
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE

    ; Unpin D0 only. The next resolve must safely reuse it with generation 2.
    lda #$D0
    jsl ScummV5_Resident_UnpinProgram_Far
    bcc ScummV5_Resident_RunAcceptanceControl_Far__unpin_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail9
ScummV5_Resident_RunAcceptanceControl_Far__unpin_ok:
    .a8
    lda #$03
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    lda #$D0
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_EXPECTED_ID
    lda #$0001
    sta.l SAME_SCUMM_RESIDENT_EXPECTED_GENERATION
    sep #$20
    .a8
    lda #$D0
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    lda #SCUMM_RESIDENT_SELECTOR_COUNT
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcs ScummV5_Resident_RunAcceptanceControl_Far__rebind_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail12
ScummV5_Resident_RunAcceptanceControl_Far__rebind_ok:
    .a16
    .i16
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_DIAG_REBOUND_SELECTOR
    cmp #$D0
    beq ScummV5_Resident_RunAcceptanceControl_Far__rebound_selector_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail13
ScummV5_Resident_RunAcceptanceControl_Far__rebound_selector_ok:
    .a8
    lda #$04
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_UNIT_IDS
    cmp #SCUMM_RESIDENT_SELECTOR_COUNT
    beq ScummV5_Resident_RunAcceptanceControl_Far__rebound_id_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail14
ScummV5_Resident_RunAcceptanceControl_Far__rebound_id_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_RESIDENT_GENERATIONS
    sta.l SAME_SCUMM_RESIDENT_DIAG_REBOUND_GENERATION
    cmp #$0002
    beq ScummV5_Resident_RunAcceptanceControl_Far__rebound_generation_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail15
ScummV5_Resident_RunAcceptanceControl_Far__rebound_generation_ok:
    sep #$20
    .a8
    lda #$05
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    lda #$D0
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsl ScummV5_Resident_ValidateReference_Far
    bcs ScummV5_Resident_RunAcceptanceControl_Far__stale_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail10
ScummV5_Resident_RunAcceptanceControl_Far__stale_ok:
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_DIAG_STALE_REJECTED
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_STALE_COUNT
    cmp #$0001
    beq ScummV5_Resident_RunAcceptanceControl_Far__stale_count_ok
    jmp ScummV5_Resident_RunAcceptanceControl_Far__fail11
ScummV5_Resident_RunAcceptanceControl_Far__stale_count_ok:
    .a16
    .i16
    sep #$20
    .a8
    lda #$06
    sta.l SAME_SCUMM_RESIDENT_DIAG_STAGE
    rep #$20
    .a16
    jsr ScummV5_Resident_RefreshDiagnostics
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_RESIDENT_DIAG_STATUS
    plp
    sec
    rtl

ScummV5_Resident_RunAcceptanceControl_Far__fail1:
    sep #$20
    .a8
    lda #$01
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail2:
    .a8
    lda #$02
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail3:
    sep #$20
    .a8
    lda #$03
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail4:
    sep #$20
    .a8
    lda #$04
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail5:
    .a8
    lda #$05
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail6:
    sep #$20
    .a8
    lda #$06
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail7:
    .a8
    lda #$07
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail8:
    sep #$20
    .a8
    lda #$08
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail9:
    sep #$20
    .a8
    lda #$09
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail10:
    sep #$20
    .a8
    lda #$0A
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail11:
    sep #$20
    .a8
    lda #$0B
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail12:
    sep #$20
    .a8
    lda #$0C
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail13:
    sep #$20
    .a8
    lda #$0D
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail14:
    sep #$20
    .a8
    lda #$0E
    bra ScummV5_Resident_RunAcceptanceControl_Far__failed
ScummV5_Resident_RunAcceptanceControl_Far__fail15:
    sep #$20
    .a8
    lda #$0F
ScummV5_Resident_RunAcceptanceControl_Far__failed:
    sta.l SAME_SCUMM_RESIDENT_DIAG_STATUS
    plp
    clc
    rtl
.endif
