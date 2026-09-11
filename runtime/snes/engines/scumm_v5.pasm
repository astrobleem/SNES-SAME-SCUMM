; Independent SCUMM v5 semantic nucleus.  The ROM-resident conformance script
; is generated from copyright-free fixture bytes and checked against upstream
; ScummVM opcode/operand semantics.  This code contains no game, cursor, room,
; actor, presentation, audio, or storage policy.
SCUMM_V5_ENGINE_ID = SAME_ENGINE_SCUMM_V5
SCUMM_V5_SAVE_SCHEMA = $0001
SCUMM_V5_MAX_SCRIPT_SLOTS = $0019

SCUMM_VM_RUNNING = $01
SCUMM_VM_YIELDED = $02
SCUMM_VM_DELAYED = $03
SCUMM_VM_STOPPED = $04
SCUMM_VM_ERROR   = $FF
SCUMM_WIO_INVENTORY = $00
SCUMM_WIO_ROOM      = $01
SCUMM_WIO_GLOBAL    = $02
SCUMM_WIO_LOCAL     = $03

SCUMM_ERR_NONE          = $00
SCUMM_ERR_PC_RANGE      = $01
SCUMM_ERR_VARIABLE      = $02
SCUMM_ERR_OPCODE        = $03
SCUMM_ERR_BUDGET        = $04
SCUMM_ERR_DELAY_RANGE   = $05
SCUMM_ERR_DIVIDE_ZERO   = $06
SCUMM_ERR_FIXTURE       = $07
SCUMM_ERR_BIT_VARIABLE  = $08
SCUMM_ERR_SLOT_CAPACITY = $09
SCUMM_ERR_LOCAL         = $0A
SCUMM_ERR_SCRIPT        = $0B
SCUMM_ERR_ARGUMENTS     = $0C
SCUMM_ERR_SERVICE       = $0D
SCUMM_ERR_STRING        = $0E
SCUMM_ERR_ROOM_OPS      = $0F
SCUMM_ERR_RESOURCE      = $10
SCUMM_ERR_ACTOR_OPS     = $11
SCUMM_ERR_CAMERA_FOLLOW = $12
SCUMM_ERR_SET_CLASS     = $13
SCUMM_ERR_VERB_OPS      = $14
SCUMM_ERR_EXPRESSION    = $15
SCUMM_ERR_CUTSCENE     = $16
SCUMM_ERR_SENTENCE     = $17
SCUMM_ERR_DRAW_OBJECT  = $18
SCUMM_ERR_SOUND_KLUDGE = $19
SCUMM_ERR_SAVE_VERBS   = $1A
SCUMM_ERR_ANIMATE_ACTOR = $1B
SCUMM_ERR_ACTOR_FROM_POS = $1C
SCUMM_ERR_PUT_ACTOR_ROOM = $1D
SCUMM_ERR_PUT_ACTOR_OBJECT = $1E
SCUMM_ERR_IF_CLASS       = $1F

ScummV5_Engine_Boot:
    php
    sep #$20
    .a8
    lda.l $7E5451
    inc
    sta.l $7E5451
    lda #$00
    sta.l SAME_SCUMM_FIXTURE_REQUEST
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_RETURN_MODE
    .if SAME_BUILD_SCUMM_M19
    sta.l SAME_SCUMM_C1_HOLD_AFTER
    .endif
    sta.l SAME_SCUMM_C18_NESTED
    .if SAME_BUILD_SCUMM_M19
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .endif
    .if SAME_BUILD_SCUMM_M20
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MUSIC_POSITION
    sta.l SAME_SCUMM_MUSIC_POSITION+2
    sep #$20
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M21
    lda #$00
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    sta.l SAME_SCUMM_M21_ROUTE_COUNT
    sta.l SAME_SCUMM_M21_HISTORY_COUNT
    .endif
    .if SAME_BUILD_SCUMM_M22
    sta.l SAME_SCUMM_M22_CUE_GENERATION
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SAME_SCUMM_M22_ARM_COUNT
    sta.l SAME_SCUMM_M22_CONSUME_COUNT
    sta.l SAME_SCUMM_M22_STALE_COUNT
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
    .endif
    .if SAME_BUILD_SCUMM_M23A
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear_m23a:
    .a16
    .i16
    sta.l SAME_SCUMM_M23A_ACTIVE_RECORD,x
    inx
    inx
    cpx #SAME_SCUMM_M23A_STATE_SIZE
    bcc ScummV5_Engine_Boot__clear_m23a
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_M23A_ACTIVE_RECORD
    sta.l SAME_SCUMM_M23A_PENDING_RECORD
    .endif
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_PC,x
    inx
    inx
    cpx #SAME_SCUMM_STATE_SIZE
    bcc ScummV5_Engine_Boot__clear
    .if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
    jsr ScummV5_ClearGlobalVariables
    .endif
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear_c4:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    inx
    cpx #SAME_SCUMM_C4_STATE_SIZE
    bcc ScummV5_Engine_Boot__clear_c4
    jsr ScummV5_C7_ResetState
    jsr ScummV5_C8_ResetState
    jsr ScummV5_C10_ResetState
    jsr ScummV5_C11_ResetState
    jsr ScummV5_C12_InvalidateState
    jsr ScummV5_C13_InvalidateState
    jsr ScummV5_C14_InvalidateState
    jsr ScummV5_C31_InvalidateState
    jsr ScummV5_C15_ResetState
    jsr ScummV5_Camera_ResetState
    jsr ScummV5_C16_InvalidateState
    jsr ScummV5_C17_InvalidateState
    jsr ScummV5_C19_ResetState
    jsr ScummV5_C20_ResetState
    jsr ScummV5_C21_ResetState
    jsr ScummV5_C22_ResetState
    jsr ScummV5_C23_ResetState
    jsr ScummV5_C25_ResetState
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_SetState_Reset_Far
    .endif
    .if SAME_BUILD_SCUMM_M23B
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR || SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Dedicated validator owns its scheduler from cold boot and enters its
    ; copyright-free cooked room through the ordinary loadRoom fixture.
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__m25a_clear:
    .a16
    .i16
    sta.l SAME_SCUMM_M25A_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_M25A_STATE_SIZE
    bcc ScummV5_Engine_Boot__m25a_clear
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__m25a_clear_variables:
    .a16
    .i16
    sta.l SAME_SCUMM_M23B_VARIABLES,x
    inx
    inx
    .if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
    cpx #SAME_SCUMM_VARIABLE_BYTES
    .else
    cpx #$0400
    .endif
    bcc ScummV5_Engine_Boot__m25a_clear_variables
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Standalone scenario boots do not inherit the debugger's committed-frame
    ; hold from SRAM.  The normal frame lifecycle must remain live after the
    ; room checkpoint becomes ready.
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__clear_scenario:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_SCENARIO_FIXTURE_REQUESTED,x
    inx
    inx
    cpx #$0034
    bcc ScummV5_Engine_Boot__clear_scenario
    sep #$20
    .a8
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C1_HOLD_AFTER
    .if SAME_BUILD_SCUMM_CONTROLLER
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONTROLLER_MODE
    sta.l SAME_SCUMM_CONTROLLER_HUD_DIRTY
    sta.l SAME_SCUMM_CONTROLLER_SUBMISSIONS
    sta.l SAME_SCUMM_CONTROLLER_LAST_ACTION
    sta.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    rep #$20
    .a16
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_X
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_Y
    .endif
    ; A standalone scenario is a fresh semantic session even when the
    ; emulator preserves WRAM across power/reset.  Do not let an old API
    ; mailbox request launch a sentence before the room checkpoint is ready.
    sep #$20
    .a8
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
    sta.l SAME_SCUMM_ROOM_REQUEST_API_PENDING
    sep #$20
    .a8
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_M23B_VARIABLES+(1 * 2) ; VAR_EGO
    lda #$0002
    sta.l SAME_SCUMM_M23B_VARIABLES+(33 * 2) ; VAR_SENTENCE_SCRIPT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_SCENARIO_FIXTURE_REQUESTED
    sta.l SAME_SCUMM_SCENARIO_FIXTURE_READY
    sta.l SAME_SCUMM_M25_START_TRACE_COUNT
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE_COUNT
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_COUNT
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS1
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_STATUS2
    sta.l SAME_SCUMM_SCENARIO_M24RB_ALLOC_CHOSEN
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_OPCODE
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD0
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD1
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD2
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE_COUNT
    sta.l SAME_SCUMM_SCENARIO_START_REQUEST
    sta.l SAME_SCUMM_SCENARIO_SOURCE_ACTOR_INIT
    sta.l SAME_SCUMM_SCENARIO_START_CURRENT
    sta.l SAME_SCUMM_SCENARIO_START_ACTIVE_BEFORE
    sta.l SAME_SCUMM_SCENARIO_START_ACTIVE_AFTER
    sta.l SAME_SCUMM_SCENARIO_START_SCAN
    sta.l SAME_SCUMM_SCENARIO_START_STATUS1
    sta.l SAME_SCUMM_SCENARIO_START_STATUS2
    sta.l SAME_SCUMM_SCENARIO_START_STATUS3
    sta.l SAME_SCUMM_SCENARIO_START_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_START_RESULT
    sta.l SAME_SCUMM_SCENARIO_START_WRITTEN
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_SLOT
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_START_RETURN_PARENT
    ; Diagnostic words must be initialized in 16-bit mode.  Their state is
    ; observational, but an uninitialized high byte can alter trace gating.
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD0
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD1
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD2
    sep #$20
    .a8
    .endif
    lda #$00
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    .if !SAME_BUILD_SCUMM_PHASE6LA1D
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Scenario fixtures enter through the ordinary room request path.  They do
    ; not select a C2 bytecode fixture and do not run the title/game bootstrap.
    .else
    lda #$42
    sta.l SAME_SCUMM_FIXTURE_REQUEST
    lda #$FF
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    .endif
    .endif
    .else
    ; Named M23B pre-Thera fixture: IQ strings are the boot-script's canonical
    ; 153-byte bias-100 arrays. The positive path has bit 425 set and sounds
    ; 80/81 stopped; the negative control instead owns logical sound 81.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_M23B_FIXTURE_APPLIED
    sta.l SAME_SCUMM_M23B_AUTH_FLUSH_SEEN
    sta.l SAME_SCUMM_M23B_AUTH_FLUSH_QUEUE_COUNT
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_FLUSH
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_CONDITION
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    sta.l SAME_SCUMM_M23C_ERROR_SUBOP
    sta.l SAME_SCUMM_M23C_ERROR_PROGRAM
    sta.l SAME_SCUMM_M23C_ERROR_OPCODE
    sta.l $7E5457
    sta.l $7E5458
    sta.l $7E545B
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__m23b_clear_variables:
    .a16
    .i16
    sta.l SAME_SCUMM_M23B_VARIABLES,x
    inx
    inx
    .if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
    cpx #SAME_SCUMM_VARIABLE_BYTES
    .else
    cpx #$0400
    .endif
    bcc ScummV5_Engine_Boot__m23b_clear_variables
    sep #$20
    .a8
    lda #$99
    sta.l SAME_SCUMM_C8_SIZES+$1E
    sta.l SAME_SCUMM_C8_SIZES+$1F
    lda #$64
    rep #$10
    .i16
    ldx #$0000
ScummV5_Engine_Boot__m23b_strings:
    .a8
    .i16
    sta.l SAME_SCUMM_C8_DATA+$1E00,x
    sta.l SAME_SCUMM_C8_DATA+$1F00,x
    inx
    cpx #$0099
    bcc ScummV5_Engine_Boot__m23b_strings
    lda.l SAME_SCUMM_C7_BITS+$35
    ora #$02
    sta.l SAME_SCUMM_C7_BITS+$35
    .if SAME_BUILD_SCUMM_M23B_NEGATIVE
    lda #$51
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .endif
    lda #$01
    sta.l SAME_SCUMM_M23B_FIXTURE_APPLIED
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_FLUSH
    .if SAME_BUILD_SCUMM_M25_MOVEMENT || SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; The movement validation personality advances beyond the already-proven
    ; music flush.  It still enters the complete authentic ENCD at PC zero.
    lda #$00
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_FLUSH
    sta.l SAME_SCUMM_SENTENCE_INJECTED
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_PREREQ_ARMED
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_M23B_VARIABLES+(1 * 2)  ; VAR_EGO
    .if !SAME_BUILD_SCUMM_PHASE6HB
    sta.l $7E2322                            ; historical low-variable mirror
    .endif
    lda #$0002
    sta.l SAME_SCUMM_M23B_VARIABLES+(33 * 2) ; VAR_SENTENCE_SCRIPT
    jsl ScummV5_M25_ResetBitState_Far
    sep #$20
    .a8
    .endif
    .if !SAME_BUILD_SCUMM_PHASE6LA1D
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; The scenario branch uses the room/resource lifecycle, not the legacy C2
    ; nested-script selector.
    .else
    lda #$42
    sta.l SAME_SCUMM_FIXTURE_REQUEST
    lda #$FF
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    .endif
    .endif
    .endif
    .if SAME_BUILD_SCUMM_M23C
    ; Versioned M23C pre-Thera fixture. Object 595's {2,7,14} classes come
    ; directly from the source-bound Fate DOBJ record. Sound 82 is ordinary
    ; logical SFX ownership established before ENCD entry; no command or
    ; branch outcome is injected after execution starts.
    ; Reset the complete sparse table before seeding record zero. Marking a
    ; single record initialized over unspecified cold WRAM made later generic
    ; setClass operations observe phantom occupied records.
    jsr ScummV5_C16_ResetState
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Boot__m23c_clear:
    .a16
    .i16
    sta.l SAME_SCUMM_M23C_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_M23C_STATE_SIZE
    bcc ScummV5_Engine_Boot__m23c_clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_M23C_FIXTURE_APPLIED
    sta.l SAME_SCUMM_C16_INITIALIZED
    lda #$FF
    sta.l SAME_SCUMM_M23C_SOUND80_RESULT
    sta.l SAME_SCUMM_M23C_SOUND82_RESULT
    lda #$01
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_PRESENT
    rep #$20
    .a16
    lda #$0253
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT
    lda #$2042
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_MASK
    lda #$0000
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONTROL
    ora #$0002 ; valid alternate state additionally owns class 18
    .endif
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_MASK+2
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23C_SOUND_CONTROL
    ; Negative control intentionally leaves logical sound 82 stopped.
    .else
    .if SAME_BUILD_SCUMM_PHASE6LA1D
    ; Authentic boot-to-room execution must not manufacture sound-82
    ; ownership before LSCR 208 has requested it.
    .else
    .if SAME_BUILD_M24RB
    ; Authentic LSCR 208 owns the deferred sound; M24R-B must not manufacture
    ; the M23C preflight's already-running control state.
    .else
    lda #$04 ; logical sound 82 -> byte 10, bit 2
    sta.l SAME_SCUMM_M23C_ACTIVE_SFX+$0A
    .endif
    .endif
    .endif
    lda #$00
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_FLUSH
    .if SAME_BUILD_M24RB
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_M24RB_STATE
    sta.l SAME_M24RB_STATE+2
    sta.l SAME_M24RB_STATE+4
    sta.l SAME_M24RB_STATE+6
    sep #$20
    .a8
    .endif
    .endif
    .endif ; SAME_BUILD_SCUMM_M23B
    .if SAME_BUILD_SCUMM_M23A
    lda #$00
    sta.l SAME_SCUMM_LOAD_EGO_ACTIVE
    jsl ScummV5_Talk_Reset_Far
    jsl ScummV5_GetActorWalkbox_Reset_Far
    jsl ScummV5_ObjectOwner_LoadInitial_Far
    ; Object names are runtime $54 state. Clear only the compact length table
    ; at boot; the encoded byte backing may remain untouched because a zero
    ; length makes an entry unavailable to target-neutral clients.
    sep #$20
    .a8
    rep #$10
    .i16
    lda #$00
    ldx #$0000
ScummV5_Engine_Boot__clear_object_name_lengths:
    sep #$20
    .a8
    .i16
    sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
    inx
    cpx #SAME_SCUMM_OBJECT_NAME_COUNT
    bcc ScummV5_Engine_Boot__clear_object_name_lengths
    sep #$20
    .a8
    .endif
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SAVE_PERSISTENCE_VALIDATOR
    ; Copyright-free cold-boot persistence gate. A blank cartridge selects the
    ; normal save script; an existing envelope selects the normal load script.
    ; The load opcode remains responsible for complete identity/CRC validation.
    jsr Same_Save_HasEnvelopeMagic
    bcc ScummV5_Engine_Boot__persistence_save
    lda #SCUMM_C2_FIXTURE_M20_LOAD_MUSIC
    bra ScummV5_Engine_Boot__persistence_selected
ScummV5_Engine_Boot__persistence_save:
    .a8
    lda #SCUMM_C2_FIXTURE_M20_SAVE_MUSIC
ScummV5_Engine_Boot__persistence_selected:
    .a8
    sta.l SAME_SCUMM_FIXTURE_REQUEST
    lda #$FF
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Scenario manifests carry the source DOBJ class masks alongside owners
    ; and states.  Install them through the normal sparse C16 representation
    ; before the first room frame; the validator never writes interpreter RAM.
    jsl ScummV5_ObjectClass_LoadInitial_Far
    lda #$00
    sta.l $7E5700
    sta.l $7E5701
    sta.l $7E5702
    sta.l $7E5704
    sta.l $7E5705
    sta.l $7E57F0
    .endif
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    plp
    clc
    rts

.if SAME_BUILD_SCUMM_PHASE6HB || SAME_BUILD_SCUMM_PHASE6LA1D
; Clear the complete profile-sized dense global namespace.  The historical
; compact state clear still owns (and reserves) $7E2320-$7E233F.
ScummV5_ClearGlobalVariables:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_ClearGlobalVariables__loop:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_VARIABLES,x
    inx
    inx
    cpx #SAME_SCUMM_VARIABLE_BYTES
    bcc ScummV5_ClearGlobalVariables__loop
    rts
.endif

ScummV5_Engine_Frame:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda #$10
    sta.l SAME_RESET_DIAG_STAGE
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
    tsx
    txa
    sta.l SAME_SCUMM_FRAME_ENTRY_STACK
    sep #$20
    .a8
    ; Consume one semantic sentence submitted through the SCUMM-owned API.
    ; This only queues C20 state; normal scheduler dispatch remains in charge.
    lda.l SAME_SCUMM_SENTENCE_API_PENDING
    beq ScummV5_Engine_Frame__sentence_api_done
    sep #$20
    .a8
    lda #$11
    sta.l SAME_RESET_DIAG_STAGE
    rep #$20
    .a16
    jsl ScummV5_QueueSentence
    lda #$00
    sta.l SAME_SCUMM_SENTENCE_API_PENDING
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Mark the accepted semantic sentence boundary.  The fixture prerequisite
    ; is kept alive only after an actual mailbox submission, never during
    ; startup or room installation.
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_PREREQ_ARMED
    ; Apply controlled, source-backed state immediately after the production
    ; mailbox creates its C20 record.  This is the earliest stable fixture
    ; boundary and avoids depending on whether the prepass has already
    ; consumed the record on this frame.
    jsl ScummV5_ObjectClass_ApplyScenarioOverlay_Far
    jsl ScummV5_Bit_ApplyScenarioOverlay_Far
    jsl ScummV5_ObjectState_ApplyScenarioOverlay_Far
    .endif
ScummV5_Engine_Frame__sentence_api_done:
    .a8
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_ROOM_REQUEST_API_PENDING
    beq ScummV5_Engine_Frame__room_request_done
    lda.l SAME_SCUMM_ROOM_REQUEST_API_ROOM
    jsr ScummV5_RequestRoom
    lda #$00
    sta.l SAME_SCUMM_ROOM_REQUEST_API_PENDING
ScummV5_Engine_Frame__room_request_done:
    .endif
    .a8
    ; A semantic sentence may arrive while the resource service is finishing
    ; its previous boundary.  Once the lifecycle is genuinely idle, consume
    ; it at that same engine-owned boundary before the scheduler eligibility
    ; query; the normal end-of-pass call below remains the no-op second check.
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_M23A_PHASE
    bne ScummV5_Engine_Frame__sentence_prepass_done
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Controlled scenario roots may begin from a previously accepted,
    ; source-backed mutation.  Reapply the generic class overlay at the
    ; sentence boundary, after room ENCD/LSCR initialization has completed;
    ; this does not alter normal production boots or validator memory.
    lda.l SAME_SCUMM_C20_COUNT
    beq ScummV5_Engine_Frame__scenario_overlay_done
    jsl ScummV5_ObjectClass_ApplyScenarioOverlay_Far
    jsl ScummV5_Bit_ApplyScenarioOverlay_Far
    jsl ScummV5_ObjectState_ApplyScenarioOverlay_Far
ScummV5_Engine_Frame__scenario_overlay_done:
    .endif
    lda.l SAME_SCUMM_C20_COUNT
    beq ScummV5_Engine_Frame__sentence_prepass_done
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    jsl ScummV5_SentenceProcess_Far
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    ; Sentence processing may normalize bit-table state while launching the
    ; global sentence script. Reapply only for the batch proven nonempty
    ; above, after that processing and before scheduler execution.
    jsl ScummV5_ObjectClass_ApplyScenarioOverlay_Far
    jsl ScummV5_Bit_ApplyScenarioOverlay_Far
    jsl ScummV5_ObjectState_ApplyScenarioOverlay_Far
    bcc ScummV5_Engine_Frame__sentence_prepass_done
    jmp ScummV5_Engine_Frame__m23a_error
ScummV5_Engine_Frame__sentence_prepass_done:
    sep #$20
    .a8
    .endif
    ; Profile-owned title START edge; room loading remains generic.  Input
    ; masks are 16-bit, so keep the accumulator wide through the test.
    .if SAME_BUILD_SCUMM_M23A
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l $7E565F
    cmp #SCUMM_V5_TITLE_START_ROOM
    bne ScummV5_Engine_Frame__title_start_done
    ; The controller service publishes the edge during the NMI boundary after
    ; the engine frame has begun.  The title gate is an idle-state action, so
    ; consume the held START state here; this preserves the production input
    ; seam without losing a one-frame edge between NMI and the frame pass.
    rep #$20
    .a16
    lda.l SAME_INPUT_HELD
    sta.l $7E565C
    bit #$1000
    beq ScummV5_Engine_Frame__title_start_done
    sep #$20
    .a8
    lda #SCUMM_V5_TITLE_TARGET_ROOM
    sta.l $7E565D
    jsr ScummV5_RequestRoom
    lda #$02
    sta.l $7E565E
ScummV5_Engine_Frame__title_start_done:
    sep #$20
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_Talk_FrameBegin_Far
    ; A decoded-but-unsupported script-visible semantic leaves the SCUMM VM
    ; quiescent while the outer SAME frame/video lifecycle remains alive.
    lda.l SAME_SCUMM_ERROR
    beq ScummV5_Engine_Frame__not_blocked
    plp
    clc
    rts
ScummV5_Engine_Frame__not_blocked:
    .a8
    jsl ScummV5_M23A_NormalizeEntryLifecycle_Far
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Request once, from the normal frame boundary, after boot has initialized
    ; services.  The storage/lifecycle code owns installation and ENCD.
    lda.l SAME_SCUMM_SCENARIO_FIXTURE_REQUESTED
    bne ScummV5_Engine_Frame__scenario_request_done
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_FIXTURE_REQUESTED
    lda #SCUMM_V5_SCENARIO_START_ROOM
    jsr ScummV5_RequestRoom
ScummV5_Engine_Frame__scenario_request_done:
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Labeled controller scenario handoff: after the ordinary room-68 root
    ; has installed, request room 42 through the normal lifecycle API. This
    ; fixture startup path does not construct scripts, PCs, sentences, or
    ; object state.
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$04
    bne ScummV5_Engine_Frame__controller_root_done
    lda.l SAME_SCUMM_M23A_PHASE
    bne ScummV5_Engine_Frame__controller_root_done
    lda.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    bne ScummV5_Engine_Frame__controller_root_done
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    lda #$2A
    jsr ScummV5_RequestRoom
ScummV5_Engine_Frame__controller_root_done:
    .endif
    .endif
    .if SAME_BUILD_SCUMM_M22
    jsr ScummV5_M22_ConsumeBoundary
    .endif
    .if SAME_BUILD_SCUMM_M23A
    .if SAME_BUILD_SCUMM_M23C
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR && !SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Dedicated validator owns scheduling; controller fixture retains the
    ; authored startup driver so the visible scene follows the real path.
    .else
    .if SAME_BUILD_SCUMM_M25_MOVEMENT || SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; The accepted interactive path owns its room transition through authentic
    ; bytecode.  The older bounded M23C timing driver remains historical only.
    .else
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23C_Driver_FarEntry
    .else
    jsr ScummV5_M23C_Driver
    .endif
    bcs ScummV5_Engine_Frame__m23a_error
    .endif
    .endif
    .endif
    lda.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_SCENARIO_PHASE_BRANCH
    cmp #$04
    beq ScummV5_Engine_Frame__m23a_wait
    cmp #$05
    beq ScummV5_Engine_Frame__m23a_ready
    cmp #$06
    beq ScummV5_Engine_Frame__m23a_failed
    bra ScummV5_Engine_Frame__m23a_hold_check
ScummV5_Engine_Frame__m23a_ready:
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_ResourceReady_FarEntry
    .else
    jsr ScummV5_M23A_ResourceReady
    .endif
    bcs ScummV5_Engine_Frame__m23a_error
ScummV5_Engine_Frame__m23a_hold_check:
    lda.l SAME_SCUMM_M23A_HOLD
    beq ScummV5_Engine_Frame__m23a_continue
ScummV5_Engine_Frame__m23a_wait:
    plp
    clc
    rts
ScummV5_Engine_Frame__m23a_error:
    plp
    sec
    rts
ScummV5_Engine_Frame__m23a_failed:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda #$E4
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    .endif
    lda #SCUMM_ERR_RESOURCE
    jsr ScummV5_SetError
    plp
    sec
    rts
ScummV5_Engine_Frame__m23a_continue:
    .a8
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$01
    beq ScummV5_Engine_Frame__m23a_run_room_script
    cmp #$02
    beq ScummV5_Engine_Frame__m23a_run_room_script
    jmp ScummV5_Engine_Frame__m23a_driver
ScummV5_Engine_Frame__m23a_run_room_script:
    ; Room ENCD/EXCD owns scheduler slot zero, but nested startScript calls
    ; temporarily leave the shared interpreter registers pointing at a child.
    ; Reload the lifecycle slot on every pass before running it so a child
    ; return cannot resume the room script at the child's stale PC.
    ; First preserve a still-matching room-owner context from the preceding
    ; pass.  This is needed when the direct room path returned through the
    ; common opcode boundary: the live PC has advanced, but the next frame has
    ; not yet rehydrated slot zero.  Never save a context whose program/slot
    ; identity does not match the room owner.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    beq ScummV5_Engine_Frame__m23a_owner_slot_zero
    jmp ScummV5_Engine_Frame__m23a_rehydrate
ScummV5_Engine_Frame__m23a_owner_slot_zero:
    lda.l SAME_SCUMM_PROGRAM_SELECT
    cmp.l SAME_SCUMM_C4_SLOT_PROGRAM
    beq ScummV5_Engine_Frame__m23a_owner_identity_ok
    ; If the selector is neutral after an authored room boundary, slot zero
    ; remains the only valid owner. Recover it only at the outer, non-nested
    ; lifecycle boundary; other mismatches must still rehydrate without a
    ; speculative save.
    sep #$20
    .a8
    cmp #$00
    bne ScummV5_Engine_Frame__m23a_rehydrate
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Engine_Frame__m23a_rehydrate
    lda.l SAME_SCUMM_C18_NESTED
    bne ScummV5_Engine_Frame__m23a_rehydrate
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    beq ScummV5_Engine_Frame__m23a_rehydrate
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    php
    jsr ScummV5_C4_SaveCurrentSlot
    plp
    jmp ScummV5_Engine_Frame__m23a_rehydrate
ScummV5_Engine_Frame__m23a_owner_identity_ok:
    php
    jsr ScummV5_C4_SaveCurrentSlot
    plp
ScummV5_Engine_Frame__m23a_rehydrate:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    lda.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    ; ENCD/EXCD can also resume exactly at the end of their bounded payload.
    ; Normalize slot zero at the lifecycle boundary before the shared fetcher
    ; reports a spurious PC-range error.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_Engine_Frame__m23a_room_runnable
    sep #$20
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Engine_Frame__m23a_room_runnable:
    jmp ScummV5_Engine_RunSelected
ScummV5_Engine_Frame__m23a_driver:
    .a8
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Room installation has committed by this point.  The labeled controller
    ; scenario now hands off from the source-backed room-68 root through the
    ; ordinary room request path.
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$04
    bne ScummV5_Engine_Frame__controller_driver_done
    lda.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    bne ScummV5_Engine_Frame__controller_driver_done
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    lda #$2A
    jsr ScummV5_RequestRoom
ScummV5_Engine_Frame__controller_driver_done:
    sep #$20
    .a8
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$23
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    lda.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    lda.l SAME_SCUMM_SCENARIO_DRIVER_REACHED
    inc
    sta.l SAME_SCUMM_SCENARIO_DRIVER_REACHED
    .endif
    ; Once a room lifecycle script has completed, the normal room lifecycle
    ; returns to idle (phase zero).  If a validated room remains active and
    ; runnable scripts still exist, give the production C4 scheduler sole
    ; ownership of the next logical script pass.  This is the same path used
    ; by the dedicated validators; production room-local and global slots are
    ; not resumed by a separate room/audio-driver policy.
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    .if !SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    jsl ScummV5_M25_MaybeQueueSentence_Far
    bcc ScummV5_Engine_Frame__m23a_driver_queue_ok
    jmp ScummV5_Engine_Frame__m23a_error
    .endif
ScummV5_Engine_Frame__m23a_driver_queue_ok:
    .endif
    ; An idle room may still have a stale non-runnable slot marker, which
    ; legitimately makes SchedulerReady reject a pass.  Sentence ownership is
    ; nevertheless an independent end-of-frame boundary: let C20 allocate its
    ; normal launcher before consulting whether a runnable slot exists.
    .if SAME_BUILD_SCUMM_M23A
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_CALLS
    inc
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_CALLS
    .endif
    jsl ScummV5_SentenceProcess_Far
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C20_COUNT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_LAST_COUNT
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_RETURNS
    inc
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_RETURNS
    .endif
    bcc ScummV5_Engine_Frame__sentence_idle_ready
    jmp ScummV5_Engine_Frame__m23a_error
ScummV5_Engine_Frame__sentence_idle_ready:
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_SCHED_CALLS
    inc
    sta.l SAME_SCUMM_SCENARIO_SCHED_CALLS
    lda.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_SCENARIO_SCHED_PHASE
    lda.l SAME_SCUMM_C4_SLOT_DIDEXEC+1
    sta.l SAME_SCUMM_SCENARIO_SCHED_DIDEXEC
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT+1
    sta.l SAME_SCUMM_SCENARIO_SCHED_FREEZE
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; The sentence launcher can be held behind scheduler eligibility. Apply
    ; the source-backed prerequisite before that gate, but only after the
    ; semantic mailbox has armed it and only while room 42 remains installed.
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_PREREQ_ARMED
    beq ScummV5_Engine_Frame__scenario_ready_overlay_done
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    bne ScummV5_Engine_Frame__scenario_ready_overlay_done
    jsl ScummV5_ObjectClass_ApplyScenarioOverlay_Far
    jsl ScummV5_Bit_ApplyScenarioOverlay_Far
    jsl ScummV5_ObjectState_ApplyScenarioOverlay_Far
ScummV5_Engine_Frame__scenario_ready_overlay_done:
    .a8
    .endif
    jsl ScummV5_SchedulerReady_FarEntry
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$25
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    lda.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    .a8
    lda #$00
    bcc ScummV5_Engine_Frame__scenario_sched_not_ready
    lda #$01
    .a8
ScummV5_Engine_Frame__scenario_sched_not_ready:
    .a8
    sta.l SAME_SCUMM_SCENARIO_SCHED_READY
    .endif
    bcc ScummV5_Engine_Frame__m23a_fixture_driver
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Keep a source-backed sentence prerequisite alive through the scheduler
    ; pass.  This is gated by an actual semantic mailbox submission, so it
    ; cannot affect startup or room installation even if sentence dispatch is
    ; delayed by another active script.
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_PREREQ_ARMED
    beq ScummV5_Engine_Frame__scenario_before_scheduler
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #$2A
    bne ScummV5_Engine_Frame__scenario_before_scheduler
    jsl ScummV5_ObjectClass_ApplyScenarioOverlay_Far
    jsl ScummV5_Bit_ApplyScenarioOverlay_Far
    jsl ScummV5_ObjectState_ApplyScenarioOverlay_Far
ScummV5_Engine_Frame__scenario_before_scheduler:
    .a8
    .endif
    jmp ScummV5_C4_Scheduler_Frame
ScummV5_Engine_Frame__m23a_fixture_driver:
    .a8
    .endif
    lda.l SAME_SCUMM_C1_HOLD_AFTER
    beq ScummV5_Engine_Frame__fixture_check
    lda.l SAME_SCUMM_FRAME_COUNT
    cmp.l SAME_SCUMM_C1_HOLD_AFTER
    bcc ScummV5_Engine_Frame__fixture_check
    plp
    clc
    rts
ScummV5_Engine_Frame__fixture_check:
    .a8
    lda.l SAME_SCUMM_FIXTURE_REQUEST
    cmp.l SAME_SCUMM_FIXTURE_ACTIVE
    bne ScummV5_Engine_Frame__fixture_changed
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__fixture_changed:
    .a8
    cmp #SCUMM_C2_FIXTURE_COUNT
    bcc ScummV5_Engine_Frame__select_fixture
    lda #SCUMM_ERR_FIXTURE
    jsr ScummV5_SetError
    jmp ScummV5_Engine_Frame__error
ScummV5_Engine_Frame__select_fixture:
    sta.l SAME_SCUMM_FIXTURE_ACTIVE
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Engine_Frame__clear_fixture_state:
    .a16
    .i16
    sta.l SAME_SCUMM_PC,x
    inx
    inx
    cpx #SAME_SCUMM_STATE_SIZE
    bcc ScummV5_Engine_Frame__clear_fixture_state
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    beq ScummV5_Engine_Frame__reset_c7_state
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_Engine_Frame__c7_state_ready
ScummV5_Engine_Frame__reset_c7_state:
    jsr ScummV5_C7_ResetState
ScummV5_Engine_Frame__c7_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_Engine_Frame__c8_state_ready
    jsr ScummV5_C8_ResetState
ScummV5_Engine_Frame__c8_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_Engine_Frame__c9_state_ready
    jsr ScummV5_C4_ResetState
ScummV5_Engine_Frame__c9_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_Engine_Frame__c10_state_ready
    jsr ScummV5_C10_ResetState
ScummV5_Engine_Frame__c10_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_Engine_Frame__c11_state_ready
    jsr ScummV5_C11_ResetState
ScummV5_Engine_Frame__c11_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_Engine_Frame__c12_state_ready
    jsr ScummV5_C12_ResetState
ScummV5_Engine_Frame__c12_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_Engine_Frame__c13_state_ready
    jsr ScummV5_C13_ResetState
ScummV5_Engine_Frame__c13_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    beq ScummV5_Engine_Frame__reset_c14_state
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    beq ScummV5_Engine_Frame__reset_c14_state
    cmp #SCUMM_C2_FIXTURE_C29_ACTOR_FROM_POS
    beq ScummV5_Engine_Frame__reset_c14_state
    cmp #SCUMM_C2_FIXTURE_C31_PUT_ACTOR_IN_ROOM
    beq ScummV5_Engine_Frame__reset_c14_state
    cmp #SCUMM_C2_FIXTURE_C32_PUT_ACTOR_AT_OBJECT
    bne ScummV5_Engine_Frame__c14_state_ready
ScummV5_Engine_Frame__reset_c14_state:
    jsr ScummV5_C14_ResetState
ScummV5_Engine_Frame__c14_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C31_PUT_ACTOR_IN_ROOM
    beq ScummV5_Engine_Frame__reset_c31_state
    cmp #SCUMM_C2_FIXTURE_C32_PUT_ACTOR_AT_OBJECT
    bne ScummV5_Engine_Frame__c31_state_ready
ScummV5_Engine_Frame__reset_c31_state:
    jsr ScummV5_C31_ResetState
ScummV5_Engine_Frame__c31_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_Engine_Frame__c15_state_ready
    jsr ScummV5_C15_ResetState
ScummV5_Engine_Frame__c15_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    beq ScummV5_Engine_Frame__reset_c16_state
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS
    beq ScummV5_Engine_Frame__reset_c16_state
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS_MALFORMED
    beq ScummV5_Engine_Frame__reset_c16_state
    .endif
    cmp #SCUMM_C2_FIXTURE_C29_ACTOR_FROM_POS
    beq ScummV5_Engine_Frame__reset_c16_state
    cmp #SCUMM_C2_FIXTURE_C30_FIND_OBJECT
    bne ScummV5_Engine_Frame__c16_state_ready
ScummV5_Engine_Frame__reset_c16_state:
    jsr ScummV5_C16_ResetState
ScummV5_Engine_Frame__c16_state_ready:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; The focused scenario bootstrap may run one of the ordinary C16 reset
    ; gates while installing its room.  Rehydrate source DOBJ classes before
    ; sentence/script execution; this is fixture resource delivery, not a
    ; validator-side state write.
    jsl ScummV5_ObjectClass_LoadInitial_Far
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    beq ScummV5_Engine_Frame__reset_c17_state
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_Engine_Frame__c17_state_ready
ScummV5_Engine_Frame__reset_c17_state:
    jsr ScummV5_C17_ResetState
ScummV5_Engine_Frame__c17_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_Engine_Frame__c19_state_ready
    jsr ScummV5_C19_ResetState
ScummV5_Engine_Frame__c19_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_Engine_Frame__c20_state_ready
    jsr ScummV5_C20_ResetState
ScummV5_Engine_Frame__c20_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    beq ScummV5_Engine_Frame__reset_c21_state
    cmp #SCUMM_C2_FIXTURE_C30_FIND_OBJECT
    beq ScummV5_Engine_Frame__reset_c21_state
    cmp #SCUMM_C2_FIXTURE_C32_PUT_ACTOR_AT_OBJECT
    bne ScummV5_Engine_Frame__c21_state_ready
ScummV5_Engine_Frame__reset_c21_state:
    .a8
    jsr ScummV5_C21_ResetState
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C30_FIND_OBJECT
    bne ScummV5_Engine_Frame__c21_state_ready
    jsr ScummV5_C30_ResetState
ScummV5_Engine_Frame__c21_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    beq ScummV5_Engine_Frame__reset_c22_state
    cmp #SCUMM_C2_FIXTURE_C29_ACTOR_FROM_POS
    bne ScummV5_Engine_Frame__c22_state_ready
    lda #$00
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    bra ScummV5_Engine_Frame__c22_state_ready
ScummV5_Engine_Frame__reset_c22_state:
    jsr ScummV5_C22_ResetState
ScummV5_Engine_Frame__c22_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_Engine_Frame__c23_state_ready
    jsr ScummV5_C23_ResetState
ScummV5_Engine_Frame__c23_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_Engine_Frame__c24_state_ready
    jsr ScummV5_C19_ResetState
ScummV5_Engine_Frame__c24_state_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_Engine_Frame__c25_state_ready
    jsr ScummV5_C25_ResetState
ScummV5_Engine_Frame__c25_state_ready:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23A == 0
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_MATRIX_SET_BOX_FLAGS
    bcc ScummV5_Engine_Frame__matrix_state_ready
    cmp #SCUMM_C2_FIXTURE_MATRIX_UNKNOWN+1
    bcs ScummV5_Engine_Frame__matrix_state_ready
    pha
    jsr ScummV5_Matrix_ResetFixtureState
    pla
    cmp #SCUMM_C2_FIXTURE_MATRIX_MISSING
    bne ScummV5_Engine_Frame__matrix_state_ready
    lda #$00
    sta.l SAME_SCUMM_MATRIX_BOX_COUNT
ScummV5_Engine_Frame__matrix_state_ready:
    sep #$20
    .a8
    .endif
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    beq ScummV5_Engine_Frame__init_c3
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    beq ScummV5_Engine_Frame__init_c4_lifecycle
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    beq ScummV5_Engine_Frame__init_c4_capacity
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    beq ScummV5_Engine_Frame__init_c5_scheduler
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_Engine_Frame__check_init_c6_missing
    jmp ScummV5_Engine_Frame__init_c6_scheduler
ScummV5_Engine_Frame__check_init_c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_Engine_Frame__check_init_c6_capacity
    jmp ScummV5_Engine_Frame__init_c6_missing
ScummV5_Engine_Frame__check_init_c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_Engine_Frame__init_done
    jmp ScummV5_Engine_Frame__init_c6_capacity
ScummV5_Engine_Frame__init_done:
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c3:
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_SLOT0_STATUS
    sta.l SAME_SCUMM_SLOT1_STATUS
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c4_lifecycle:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c4_capacity:
    .a8
    jsr ScummV5_C4_ResetState
    ldx #$0000
    lda #SCUMM_VM_RUNNING
ScummV5_Engine_Frame__fill_c4_capacity:
    .a8
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Engine_Frame__fill_c4_capacity
    lda #SCUMM_V5_MAX_SCRIPT_SLOTS
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda #SCUMM_C2_FIXTURE_C4_CAPACITY
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    jmp ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c5_scheduler:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C5_SCHEDULER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_scheduler:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C6_SCHEDULER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_missing:
    .a8
    jsr ScummV5_C4_ResetState
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #SCUMM_C2_FIXTURE_C6_MISSING
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #$FF
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    bra ScummV5_Engine_Frame__fixture_ready
ScummV5_Engine_Frame__init_c6_capacity:
    .a8
    jsr ScummV5_C4_ResetState
    ldx #$0000
    lda #SCUMM_VM_RUNNING
ScummV5_Engine_Frame__fill_c6_capacity:
    .a8
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Engine_Frame__fill_c6_capacity
    lda #SCUMM_V5_MAX_SCRIPT_SLOTS
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda #SCUMM_C2_FIXTURE_C6_CAPACITY
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
ScummV5_Engine_Frame__fixture_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    beq ScummV5_Engine_Frame__run_c3
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    beq ScummV5_Engine_Frame__run_c4
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    beq ScummV5_Engine_Frame__run_c4
    bra ScummV5_Engine_Frame__single_fixture
ScummV5_Engine_Frame__run_c3:
    jmp ScummV5_C3_Scheduler_Frame
ScummV5_Engine_Frame__run_c4:
    jmp ScummV5_C4_Scheduler_Frame
ScummV5_Engine_Frame__single_fixture:
    .a8
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
ScummV5_Engine_RunSelected:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_FRAME_OPS

    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    bne ScummV5_Engine_Frame__check_error_status
    jmp ScummV5_Engine_Frame__return_success
ScummV5_Engine_Frame__check_error_status:
    .a8
    cmp #SCUMM_VM_ERROR
    bne ScummV5_Engine_Frame__check_delay_state
    jmp ScummV5_Engine_Frame__error

ScummV5_Engine_Frame__check_delay_state:
    rep #$20
    .a16
    lda.l SAME_SCUMM_DELAY
    beq ScummV5_Engine_Frame__start
    dec
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Engine_Frame__start:
    ; C4 resumes are slot-owned.  A nested child returns through a parent
    ; context, so the shared selector may name the parent when control reaches
    ; this common entry.  Rehydrate the selected resource identity before any
    ; bounds query; PC/delay/status are already restored by C4.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    beq ScummV5_Engine_Frame__start_program_ready
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
ScummV5_Engine_Frame__start_program_ready:
    ; A scheduler slot can legitimately resume at the byte immediately after
    ; its terminal opcode (notably an authored global loop's final branch).
    ; Normalize that boundary before FetchByte turns it into a false PC-range
    ; fault.  Room-entry normalization covers slot zero; this covers C4 slots.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_Engine_Frame__start_runnable
    sep #$20
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Engine_Frame__start_runnable:
    rep #$30
    .a16
    .i16
    lda #SAME_SCUMM_MAX_OPS_PER_FRAME
    sta.l SAME_SCUMM_BUDGET
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS

ScummV5_Engine_Frame__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_next
    dec
    sta.l SAME_SCUMM_C18_NESTED
    clc
    rts
ScummV5_Engine_Frame__outer_next:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_BUDGET
    bne ScummV5_Engine_Frame__budget_available
    jmp ScummV5_Engine_Frame__budget_error
ScummV5_Engine_Frame__budget_available:
    .a16
    .i16
    dec
    sta.l SAME_SCUMM_BUDGET
    jsr ScummV5_FetchByte
    bcc ScummV5_Engine_Frame__opcode_fetched
    jmp ScummV5_Engine_Frame__error
ScummV5_Engine_Frame__opcode_fetched:
    sta.l SAME_SCUMM_LAST_OPCODE
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && 1
    sta.l SAME_SCUMM_SCENARIO_LAST_OP_OPCODE
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_LAST_OP_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SCENARIO_LAST_OP_PC
    sep #$20
    .a8
    ; Keep a bounded decoded-instruction ring in fixture-only scratch.
    ; FetchByte has already advanced PC, so PC-1 is the opcode address.
    sep #$20
    .a8
    rep #$10
    .i16
    phx
    pha
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENARIO_OP_TRACE_COUNT
    cmp #$0100
    bcs ScummV5_Engine_Frame__op_trace_done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE+1,x
    sep #$20
    .a8
    pla
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE+3,x
    ; Keep the original opcode on the stack for the common epilogue.
    pha
    lda.l SAME_SCUMM_SCENARIO_OP_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_OP_TRACE_COUNT
    bra ScummV5_Engine_Frame__op_trace_done
ScummV5_Engine_Frame__op_trace_done:
    sep #$20
    .a8
    pla
    plx
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    cmp.l SAME_SCUMM_SCENARIO_CHILD_SLOT
    bne ScummV5_Engine_Frame__scenario_not_child_fetch
    jmp ScummV5_Engine_Frame__scenario_child_fetch
ScummV5_Engine_Frame__scenario_not_child_fetch:
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    beq ScummV5_Engine_Frame__scenario_sentence_fetch
    jmp ScummV5_Engine_Frame__scenario_fetch_done
ScummV5_Engine_Frame__scenario_sentence_fetch:
    .a8
    .i8
    ; The fetch path is the unambiguous proof that the sentence-owned slot
    ; actually executed.  Record it before any nested opcode can alter the
    ; shared selector; this is intentionally observational only.
    lda #$11
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_VM_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_FETCH_COUNT
    pha
    inc
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_FETCH_COUNT
    pla
    sta.l $7E57B0
    rep #$30
    .a16
    .i16
    and #$001F
    asl
    asl
    tax
    lda.l SAME_SCUMM_PC
    dec
    sta.l $7E5710,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l $7E5712,x
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l $7E5713,x
    rep #$20
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    xba
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    sta.l $7E5790
    lda.l SAME_SCUMM_C4_SLOT_LOCALS+2,x
    sta.l $7E5792
    lda.l SAME_SCUMM_C4_SLOT_LOCALS+4,x
    sta.l $7E5794
    lda.l $7E57B0
    cmp #$0006
    bcs ScummV5_Engine_Frame__scenario_sentence_locals_done
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    lda.l $7E5790
    sta.l $7E57C0,x
    lda.l $7E5792
    sta.l $7E57C2,x
    lda.l $7E5794
    sta.l $7E57C4,x
ScummV5_Engine_Frame__scenario_sentence_locals_done:
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_FETCH_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_FETCH_OPCODE
    bra ScummV5_Engine_Frame__scenario_fetch_done
ScummV5_Engine_Frame__scenario_child_fetch:
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_FIRST_FETCH_PROGRAM
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_FIRST_FETCH_OPCODE
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_SCENARIO_FIRST_FETCH_PC
    sep #$20
    ; Keep a bounded child opcode trail in fixture-only scratch.  This is
    ; observational and is separate from the VM and scheduler tables.
    lda.l $7E53E0
    cmp #$20
    bcs ScummV5_Engine_Frame__scenario_child_fetch_done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l $7E53E2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l $7E53E3,x
    sep #$20
    lda.l $7E53E0
    inc
    sta.l $7E5680
ScummV5_Engine_Frame__scenario_child_fetch_done:
    sep #$20
ScummV5_Engine_Frame__scenario_fetch_done:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    jsl ScummV5_M25_DebugOpcode_Far
    .endif
    .if SAME_BUILD_SCUMM_M23C
    .if !SAME_BUILD_M24RB
    jsr ScummV5_M23C_TraceOpcode
    .endif
    .endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    inc
    sta.l SAME_SCUMM_FRAME_OPS
    lda.l SAME_SCUMM_TOTAL_OPS
    inc
    sta.l SAME_SCUMM_TOTAL_OPS

ScummV5_DispatchCurrentOpcode:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$00
    beq ScummV5_Engine_Frame__dispatch_stop
    cmp #$A0
    bne ScummV5_Engine_Frame__check_break
ScummV5_Engine_Frame__dispatch_stop:
    jmp ScummV5_Op_Stop
ScummV5_Engine_Frame__check_break:
    .a8
    cmp #$80
    bne ScummV5_Engine_Frame__check_move_direct
    jmp ScummV5_Op_BreakHere
ScummV5_Engine_Frame__check_move_direct:
    .a8
    cmp #$1A
    beq ScummV5_Engine_Frame__dispatch_move
    cmp #$9A
    bne ScummV5_Engine_Frame__check_add
ScummV5_Engine_Frame__dispatch_move:
    jmp ScummV5_Op_Move
ScummV5_Engine_Frame__check_add:
    .a8
    cmp #$5A
    beq ScummV5_Engine_Frame__dispatch_add
    cmp #$DA
    bne ScummV5_Engine_Frame__check_subtract
ScummV5_Engine_Frame__dispatch_add:
    jmp ScummV5_Op_Add
ScummV5_Engine_Frame__check_subtract:
    .a8
    cmp #$3A
    beq ScummV5_Engine_Frame__dispatch_subtract
    cmp #$BA
    bne ScummV5_Engine_Frame__check_multiply
ScummV5_Engine_Frame__dispatch_subtract:
    jmp ScummV5_Op_Subtract
ScummV5_Engine_Frame__check_multiply:
    .a8
    cmp #$1B
    beq ScummV5_Engine_Frame__dispatch_multiply
    cmp #$9B
    bne ScummV5_Engine_Frame__check_divide
ScummV5_Engine_Frame__dispatch_multiply:
    jmp ScummV5_Op_Multiply
ScummV5_Engine_Frame__check_divide:
    .a8
    cmp #$5B
    beq ScummV5_Engine_Frame__dispatch_divide
    cmp #$DB
    bne ScummV5_Engine_Frame__check_and
ScummV5_Engine_Frame__dispatch_divide:
    jmp ScummV5_Op_Divide
ScummV5_Engine_Frame__check_and:
    .a8
    cmp #$17
    beq ScummV5_Engine_Frame__dispatch_and
    cmp #$97
    bne ScummV5_Engine_Frame__check_or
ScummV5_Engine_Frame__dispatch_and:
    jmp ScummV5_Op_And
ScummV5_Engine_Frame__check_or:
    .a8
    cmp #$57
    beq ScummV5_Engine_Frame__dispatch_or
    cmp #$D7
    bne ScummV5_Engine_Frame__check_increment
ScummV5_Engine_Frame__dispatch_or:
    jmp ScummV5_Op_Or
ScummV5_Engine_Frame__check_increment:
    .a8
    cmp #$46
    bne ScummV5_Engine_Frame__check_decrement
    jmp ScummV5_Op_Increment
ScummV5_Engine_Frame__check_decrement:
    .a8
    cmp #$C6
    bne ScummV5_Engine_Frame__check_compare
    jmp ScummV5_Op_Decrement
ScummV5_Engine_Frame__check_compare:
    .a8
    and #$7F
    cmp #$48
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$08
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$44
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$78
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$38
    beq ScummV5_Engine_Frame__dispatch_compare
    cmp #$04
    bne ScummV5_Engine_Frame__check_zero_compare
ScummV5_Engine_Frame__dispatch_compare:
    jmp ScummV5_Op_Compare
ScummV5_Engine_Frame__check_zero_compare:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$28
    beq ScummV5_Engine_Frame__dispatch_zero_compare
    cmp #$A8
    bne ScummV5_Engine_Frame__check_jump
ScummV5_Engine_Frame__dispatch_zero_compare:
    jmp ScummV5_Op_CompareZero
ScummV5_Engine_Frame__check_jump:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$18
    bne ScummV5_Engine_Frame__check_delay
    jmp ScummV5_Op_JumpRelative
ScummV5_Engine_Frame__check_delay:
    .a8
    cmp #$2E
    bne ScummV5_Engine_Frame__check_delay_variable
    jmp ScummV5_Op_Delay
ScummV5_Engine_Frame__check_delay_variable:
    .a8
    cmp #$2B
    bne ScummV5_Engine_Frame__check_start_music
    jmp ScummV5_Op_DelayVariable
ScummV5_Engine_Frame__check_start_music:
    .a8
    cmp #$02
    beq ScummV5_Engine_Frame__dispatch_start_music
    cmp #$82
    bne ScummV5_Engine_Frame__check_stop_music
ScummV5_Engine_Frame__dispatch_start_music:
    jmp ScummV5_Op_StartMusic
ScummV5_Engine_Frame__check_stop_music:
    .a8
    cmp #$20
    bne ScummV5_Engine_Frame__check_start_sound
    jmp ScummV5_Op_StopMusic
ScummV5_Engine_Frame__check_start_sound:
    .a8
    cmp #$1C
    beq ScummV5_Engine_Frame__dispatch_start_sound
    cmp #$9C
    bne ScummV5_Engine_Frame__check_stop_sound
ScummV5_Engine_Frame__dispatch_start_sound:
    jmp ScummV5_Op_StartSound
ScummV5_Engine_Frame__check_stop_sound:
    .a8
    cmp #$3C
    beq ScummV5_Engine_Frame__dispatch_stop_sound
    cmp #$BC
    .if SAME_BUILD_SCUMM_M19
    bne ScummV5_Engine_Frame__check_sound_running
    .else
    bne ScummV5_Engine_Frame__check_start_script
    .endif
ScummV5_Engine_Frame__dispatch_stop_sound:
    jmp ScummV5_Op_StopSound
    .if SAME_BUILD_SCUMM_M19
ScummV5_Engine_Frame__check_sound_running:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$7C
    bne ScummV5_Engine_Frame__check_start_script
    jmp ScummV5_Op_IsSoundRunning
    .endif
ScummV5_Engine_Frame__check_start_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$0A
    bne ScummV5_Engine_Frame__check_stop_script
    jmp ScummV5_Op_StartScript
ScummV5_Engine_Frame__check_stop_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$62
    bne ScummV5_Engine_Frame__check_freeze_scripts
    jmp ScummV5_Op_StopScript
ScummV5_Engine_Frame__check_freeze_scripts:
    .a8
    cmp #$60
    bne ScummV5_Engine_Frame__check_script_running
    jmp ScummV5_Op_FreezeScripts
ScummV5_Engine_Frame__check_script_running:
    .a8
    cmp #$68
    bne ScummV5_Engine_Frame__check_chain_script
    jmp ScummV5_Op_IsScriptRunning
ScummV5_Engine_Frame__check_chain_script:
    .a8
    cmp #$42
    bne ScummV5_Engine_Frame__check_set_var_range
    jmp ScummV5_Op_ChainScript
ScummV5_Engine_Frame__check_set_var_range:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$26
    bne ScummV5_Engine_Frame__check_room_ops
    jmp ScummV5_Op_SetVarRange
ScummV5_Engine_Frame__check_room_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$33
    bne ScummV5_Engine_Frame__check_random
    jmp ScummV5_Op_RoomOps
ScummV5_Engine_Frame__check_random:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$16
    bne ScummV5_Engine_Frame__check_pseudo_room
    jmp ScummV5_Op_GetRandom
ScummV5_Engine_Frame__check_pseudo_room:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$CC
    bne ScummV5_Engine_Frame__check_resource_routines
    jmp ScummV5_Op_PseudoRoom
ScummV5_Engine_Frame__check_resource_routines:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$0C
    bne ScummV5_Engine_Frame__check_actor_ops
    jmp ScummV5_Op_ResourceRoutines
ScummV5_Engine_Frame__check_actor_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$13
    bne ScummV5_Engine_Frame__check_actor_follow_camera
    jmp ScummV5_Op_ActorOps
ScummV5_Engine_Frame__check_actor_follow_camera:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$12
    beq ScummV5_Engine_Frame__dispatch_pan_camera
    cmp #$92
    beq ScummV5_Engine_Frame__dispatch_pan_camera
    cmp #$32
    beq ScummV5_Engine_Frame__dispatch_set_camera
    cmp #$B2
    bne ScummV5_Engine_Frame__check_actor_follow_camera_opcode
ScummV5_Engine_Frame__dispatch_set_camera:
    jmp ScummV5_Op_SetCameraAt
ScummV5_Engine_Frame__dispatch_pan_camera:
    jml ScummV5_Op_PanCameraTo_Far
ScummV5_Engine_Frame__check_actor_follow_camera_opcode:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$52
    bne ScummV5_Engine_Frame__check_if_class
    jmp ScummV5_Op_ActorFollowCamera
ScummV5_Engine_Frame__check_if_class:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    ; ifClassOfIs is the $1D family ($1D/$9D); $5D/$DD is setClass.
    cmp #$1D
    bne ScummV5_Engine_Frame__check_set_class
    jmp ScummV5_Op_IfClassOfIs
ScummV5_Engine_Frame__check_set_class:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$5D
    bne ScummV5_Engine_Frame__check_verb_ops
    jmp ScummV5_Op_SetClass
ScummV5_Engine_Frame__check_verb_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$7A
    bne ScummV5_Engine_Frame__check_expression
    jmp ScummV5_Op_VerbOps
ScummV5_Engine_Frame__check_expression:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$AC
    bne ScummV5_Engine_Frame__check_string_ops
    jmp ScummV5_Op_Expression
ScummV5_Engine_Frame__check_string_ops:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$27
    bne ScummV5_Engine_Frame__check_cursor_command
    jmp ScummV5_Op_StringOps
ScummV5_Engine_Frame__check_cursor_command:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$2C
    bne ScummV5_Engine_Frame__check_cutscene
    jmp ScummV5_Op_CursorCommand

; Keep new, comparatively rare families at the tail of the linear dispatch.
; This preserves the established per-frame timing of the common C1-C18 path.
ScummV5_Engine_Frame__check_cutscene:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$40
    beq ScummV5_Engine_Frame__dispatch_cutscene
    cmp #$C0
    beq ScummV5_Engine_Frame__dispatch_cutscene
    cmp #$58
    bne ScummV5_Engine_Frame__check_wait
ScummV5_Engine_Frame__dispatch_cutscene:
    jmp ScummV5_Op_CutsceneDispatch

ScummV5_Engine_Frame__check_wait:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$AE
    bne ScummV5_Engine_Frame__check_do_sentence
    jmp ScummV5_Op_Wait
ScummV5_Engine_Frame__check_do_sentence:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$1F
    cmp #$19
    bne ScummV5_Engine_Frame__check_draw_object
    jmp ScummV5_Op_DoSentence
ScummV5_Engine_Frame__check_draw_object:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$05
    bne ScummV5_Engine_Frame__check_load_room
    jmp ScummV5_Op_DrawObject
ScummV5_Engine_Frame__check_load_room:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$72
    beq ScummV5_Engine_Frame__dispatch_load_room
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$24
    bne ScummV5_Engine_Frame__check_print
    jml ScummV5_LoadRoomWithEgo_FarEntry
ScummV5_Engine_Frame__dispatch_load_room:
    jmp ScummV5_Op_LoadRoom
ScummV5_Engine_Frame__check_print:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$14
    beq ScummV5_Engine_Frame__dispatch_print_near
    cmp #$54
    bne ScummV5_Engine_Frame__check_set_object_name_d4
    jmp ScummV5_Op_SetObjectName
ScummV5_Engine_Frame__check_set_object_name_d4:
    .a8
    cmp #$D4
    bne ScummV5_Engine_Frame__check_print_variants
    jmp ScummV5_Op_SetObjectName
ScummV5_Engine_Frame__check_print_variants:
    .a8
    cmp #$94
    beq ScummV5_Engine_Frame__dispatch_print_near
    cmp #$D8
    bne ScummV5_Engine_Frame__check_sound_kludge
ScummV5_Engine_Frame__dispatch_print_near:
    jmp ScummV5_Engine_Frame__dispatch_print
ScummV5_Engine_Frame__check_sound_kludge:
    .a8
    cmp #$4C
    bne ScummV5_Engine_Frame__check_save_restore_verbs
    jmp ScummV5_Op_SoundKludge
ScummV5_Engine_Frame__check_save_restore_verbs:
    .a8
    cmp #$AB
    bne ScummV5_Engine_Frame__check_animate_actor
    jmp ScummV5_Op_SaveRestoreVerbs
ScummV5_Engine_Frame__check_animate_actor:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$43
    bne ScummV5_Engine_Frame__check_actor_x_opcode_c3
    jmp ScummV5_Engine_Frame__dispatch_get_actor_x
ScummV5_Engine_Frame__check_actor_x_opcode_c3:
    .a8
    cmp #$C3
    bne ScummV5_Engine_Frame__check_actor_y_opcode
    jmp ScummV5_Engine_Frame__dispatch_get_actor_x
ScummV5_Engine_Frame__check_actor_y_opcode:
    .a8
    cmp #$23
    bne ScummV5_Engine_Frame__check_actor_y_opcode_a3
    jmp ScummV5_Engine_Frame__dispatch_get_actor_y
ScummV5_Engine_Frame__check_actor_y_opcode_a3:
    .a8
    cmp #$A3
    bne ScummV5_Engine_Frame__check_actor_room_opcode
    jmp ScummV5_Engine_Frame__dispatch_get_actor_y
ScummV5_Engine_Frame__check_actor_room_opcode:
    .a8
    cmp #$03
    bne ScummV5_Engine_Frame__check_actor_room_opcode_not03
    jmp ScummV5_Engine_Frame__dispatch_get_actor_room
ScummV5_Engine_Frame__check_actor_room_opcode_not03:
    .a8
    cmp #$83
    bne ScummV5_Engine_Frame__check_actor_room_opcode_not83
    jmp ScummV5_Engine_Frame__dispatch_get_actor_room
ScummV5_Engine_Frame__check_actor_room_opcode_not83:
    .a8
    and #$3F
    cmp #$0E
    bne ScummV5_Engine_Frame__check_animate_actor_opcode
    jmp ScummV5_Op_PutActorAtObject
ScummV5_Engine_Frame__check_animate_actor_opcode:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$0F
    bne ScummV5_Engine_Frame__check_animate_actor_opcode_real
    jmp ScummV5_Op_GetObjectState
ScummV5_Engine_Frame__check_animate_actor_opcode_real:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$06
    beq ScummV5_Engine_Frame__dispatch_actor_elevation
    brl ScummV5_Engine_Frame__check_animate_actor_opcode_real2
ScummV5_Engine_Frame__dispatch_actor_elevation:
    jmp ScummV5_Op_GetActorElevation
ScummV5_Engine_Frame__check_animate_actor_opcode_real2:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$3B
    beq ScummV5_Engine_Frame__dispatch_actor_scale
    cmp #$BB
    beq ScummV5_Engine_Frame__dispatch_actor_scale
    and #$3F
    cmp #$11
    bne ScummV5_Engine_Frame__check_actor_from_pos
    jmp ScummV5_Op_AnimateActor
ScummV5_Engine_Frame__dispatch_actor_scale:
    jmp ScummV5_Op_GetActorScale
ScummV5_Engine_Frame__check_actor_from_pos:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$15
    bne ScummV5_Engine_Frame__check_face_actor
    jmp ScummV5_Op_ActorFromPos
ScummV5_Engine_Frame__check_face_actor:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$49
    beq ScummV5_Engine_Frame__dispatch_face_actor
    cmp #$09
    bne ScummV5_Engine_Frame__check_put_actor_in_room
ScummV5_Engine_Frame__dispatch_face_actor:
    jmp ScummV5_Op_FaceActor
ScummV5_Engine_Frame__check_put_actor_in_room:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$2D
    bne ScummV5_Engine_Frame__check_find_object
    jmp ScummV5_Op_PutActorInRoom
ScummV5_Engine_Frame__check_find_object:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$3F
    cmp #$35
    bne ScummV5_Engine_Frame__check_matrix_ops
    jmp ScummV5_Op_FindObject
ScummV5_Engine_Frame__check_matrix_ops:
    .a8
    .if SAME_BUILD_SCUMM_M23A
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$AE
    bne ScummV5_Engine_Frame__cold_far
    jsl ScummV5_WaitActor_Call_Far
    bcc ScummV5_Engine_Frame__wait_actor_ok
    jmp ScummV5_Engine_Frame__opcode_error
ScummV5_Engine_Frame__wait_actor_ok:
    .a8
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_YIELDED
    beq ScummV5_Engine_Frame__wait_actor_complete
    jmp ScummV5_Engine_Frame__next
ScummV5_Engine_Frame__wait_actor_complete:
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Engine_Frame__cold_far:
    .a8
    .endif
    jml ScummV5_ColdOpcode_FarEntry
    .else
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$30
    bne ScummV5_Engine_Frame__opcode_error
    jmp ScummV5_Op_MatrixOps
    .endif
ScummV5_Engine_Frame__dispatch_print:
    jmp ScummV5_Op_Print
ScummV5_Engine_Frame__dispatch_get_actor_room:
    jmp ScummV5_Op_GetActorRoom
ScummV5_Engine_Frame__dispatch_get_actor_x:
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_GetActorX_FarEntry
    jml ScummV5_Engine_Frame__next
    .else
    jmp ScummV5_Engine_Frame__opcode_error
    .endif
ScummV5_Engine_Frame__dispatch_get_actor_y:
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_GetActorY_FarEntry
    jmp ScummV5_Engine_Frame__next
    .else
    jmp ScummV5_Engine_Frame__opcode_error
    .endif

ScummV5_Engine_Frame__opcode_error:
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
    bra ScummV5_Engine_Frame__error

ScummV5_Engine_Frame__budget_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_BUDGET
    jsr ScummV5_SetError

ScummV5_Engine_Frame__error:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_error_check
    dec
    sta.l SAME_SCUMM_C18_NESTED
    sec
    rts
ScummV5_Engine_Frame__outer_error_check:
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_error
    sec
    rts
ScummV5_Engine_Frame__outer_error:
    .if SAME_BUILD_SCUMM_M23A
    ; A fail-closed script opcode halts that script, not the engine-global
    ; dialog clock. The outer frame owner still runs the camera phase.
    jsl ScummV5_Talk_ErrorFrameEnd_Far
    .endif
    plp
    sec
    rts
ScummV5_Engine_Frame__complete_success:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_NESTED
    beq ScummV5_Engine_Frame__outer_complete_check
    dec
    sta.l SAME_SCUMM_C18_NESTED
    clc
    rts
ScummV5_Engine_Frame__outer_complete_check:
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_complete_success
    clc
    rts
ScummV5_Engine_Frame__outer_complete_success:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    inc
    sta.l SAME_SCUMM_FRAME_COUNT
    .if SAME_BUILD_SCUMM_M20
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTIVE_MUSIC
    beq ScummV5_Engine_Frame__m20_position_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_MUSIC_POSITION
    inc
    sta.l SAME_SCUMM_MUSIC_POSITION
    bne ScummV5_Engine_Frame__m20_position_done16
    lda.l SAME_SCUMM_MUSIC_POSITION+2
    inc
    sta.l SAME_SCUMM_MUSIC_POSITION+2
ScummV5_Engine_Frame__m20_position_done16:
    sep #$20
    .a8
ScummV5_Engine_Frame__m20_position_done:
    .endif
ScummV5_Engine_Frame__return_success:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Engine_Frame__outer_return_success
    clc
    rts
ScummV5_Engine_Frame__outer_return_success:
    plp
    clc
    rts

; C3's two-slot fixture uses the same decoder one slot at a time. Each slot's
; PC, delay, and status are restored before execution and saved afterward;
; variables and total operation count are intentionally shared VM state.
ScummV5_C3_Scheduler_Frame:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SCHED_OPS

    lda.l SAME_SCUMM_SLOT0_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_SLOT0_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_SLOT0_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SLOT0
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    jsr ScummV5_Engine_RunSelected
    bcc ScummV5_C3_Scheduler_Frame__slot0_done
    jmp ScummV5_C3_Scheduler_Frame__error
ScummV5_C3_Scheduler_Frame__slot0_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SLOT0_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_SLOT0_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_SCHED_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SLOT0_STATUS

    rep #$20
    .a16
    lda.l SAME_SCUMM_SLOT1_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_SLOT1_DELAY
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_SLOT1_STATUS
    sta.l SAME_SCUMM_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SLOT1
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    jsr ScummV5_Engine_RunSelected
    bcc ScummV5_C3_Scheduler_Frame__slot1_done
    jmp ScummV5_C3_Scheduler_Frame__error
ScummV5_C3_Scheduler_Frame__slot1_done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SLOT1_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_SLOT1_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SLOT1_STATUS
    lda #SCUMM_C2_FIXTURE_C3_SCHEDULER
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C3_Scheduler_Frame__error:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    jmp ScummV5_Engine_Frame__error

; C4 owns a fixed 25-entry slot table. Slot zero carries the fixture's parent
; script; startScript allocates the first dead entry from slots 1..24.
ScummV5_C4_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C4_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    inx
    inx
    cpx #SAME_SCUMM_C4_STATE_SIZE
    bcc ScummV5_C4_ResetState__loop
    sep #$20
    .a8
    rts

.if SAME_BUILD_SCUMM_M25A_VALIDATOR
; Observability only: record production scheduler/context state without
; supplying operands, PCs, pointers, or branch results to the interpreter.
; Input A8 is an event code. Records are
; (event,depth,slot,program,u16 PC,status,active-count).
ScummV5_M25A_Trace:
    pha
    php
    rep #$10
    .i16
    phx
    phy
    sep #$20
    .a8
    lda.l SAME_SCUMM_M25A_TRACE_COUNT
    cmp #SAME_SCUMM_M25A_TRACE_CAPACITY
    bcc ScummV5_M25A_Trace__space
    lda #$01
    sta.l SAME_SCUMM_M25A_TRACE_OVERFLOW
    bra ScummV5_M25A_Trace__done
ScummV5_M25A_Trace__space:
    rep #$20
    .a16
    and #$00FF
    asl
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    asl
    tax
    sep #$20
    .a8
    ; Recover the caller's event byte without disturbing its saved stack copy.
    lda 6,s
    sta.l SAME_SCUMM_M25A_TRACE,x
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_M25A_TRACE+1,x
    cmp.l SAME_SCUMM_M25A_MAX_DEPTH
    bcc ScummV5_M25A_Trace__max_done
    sta.l SAME_SCUMM_M25A_MAX_DEPTH
ScummV5_M25A_Trace__max_done:
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_M25A_TRACE+2,x
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M25A_TRACE+3,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_M25A_TRACE+4,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_M25A_TRACE+6,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_M25A_TRACE+7,x
    lda.l SAME_SCUMM_M25A_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_M25A_TRACE_COUNT
ScummV5_M25A_Trace__done:
    rep #$10
    .i16
    ply
    plx
    plp
    pla
    rts
.endif

ScummV5_C4_Scheduler_Frame:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$20
    sta.l SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN
    lda #$26
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    lda.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE_COUNT
    lda.l SAME_SCUMM_SCENARIO_C4_CALLS
    inc
    sta.l SAME_SCUMM_SCENARIO_C4_CALLS
    lda #$00
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_COUNT
    sta.l SAME_SCUMM_SCENARIO_SCHED_MATCH_COUNT
    .endif
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    ldx #$0000
ScummV5_C4_Scheduler_Frame__clear_didexec:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_Scheduler_Frame__clear_didexec
    lda #$00
    sta.l SAME_SCUMM_C4_SCHED_SLOT
ScummV5_C4_Scheduler_Frame__next_slot:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_Scheduler_Frame__slot_in_range
    jmp ScummV5_C4_Scheduler_Frame__complete
ScummV5_C4_Scheduler_Frame__slot_in_range:
    .a8
    ; The preceding slot may have loaded a word-indexed PC into X.  The
    ; scheduler index is a byte slot number here; clear the index high byte
    ; before every byte-table lookup, not only on the first pass.
    sep #$10
    .i8
    tax
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    txa
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_SLOT
    lda.l SAME_SCUMM_SCENARIO_SCHED_SCAN_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_COUNT
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Fixture-only capture of the sentence slot's actual eligibility inputs.
    ; It does not alter scheduler state or VM registers beyond A.
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    beq ScummV5_C4_Scheduler_Frame__sentence_gate_trace_done
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__sentence_gate_trace_done
    lda.l SAME_SCUMM_SCENARIO_SCHED_MATCH_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_SCHED_MATCH_COUNT
    lda #$30
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_STATUS
    lda.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    sta.l SAME_SCUMM_SCENARIO_SCHED_DIDEXEC
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    sta.l SAME_SCUMM_SCENARIO_SCHED_FREEZE
ScummV5_C4_Scheduler_Frame__sentence_gate_trace_done:
    .a8
    .endif
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    bne ScummV5_C4_Scheduler_Frame__status_nonzero
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__status_zero_trace_done
    lda #$31
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE
ScummV5_C4_Scheduler_Frame__status_zero_trace_done:
    .endif
    jmp ScummV5_C4_Scheduler_Frame__advance
ScummV5_C4_Scheduler_Frame__status_nonzero:
    .a8
    cmp #SCUMM_VM_STOPPED
    bne ScummV5_C4_Scheduler_Frame__status_not_stopped
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__status_stopped_trace_done
    lda #$32
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE
ScummV5_C4_Scheduler_Frame__status_stopped_trace_done:
    .endif
    jmp ScummV5_C4_Scheduler_Frame__advance
ScummV5_C4_Scheduler_Frame__status_not_stopped:
    .a8
    cmp #SCUMM_VM_ERROR
    bne ScummV5_C4_Scheduler_Frame__check_didexec
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__status_error_trace_done
    lda #$33
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE
ScummV5_C4_Scheduler_Frame__status_error_trace_done:
    .endif
    jmp ScummV5_C4_Scheduler_Frame__advance
ScummV5_C4_Scheduler_Frame__check_didexec:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    beq ScummV5_C4_Scheduler_Frame__check_freeze
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__didexec_trace_done
    lda #$34
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE
ScummV5_C4_Scheduler_Frame__didexec_trace_done:
    .endif
    jmp ScummV5_C4_Scheduler_Frame__advance
ScummV5_C4_Scheduler_Frame__check_freeze:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    beq ScummV5_C4_Scheduler_Frame__eligible
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__freeze_trace_done
    lda #$35
    sta.l SAME_SCUMM_SCENARIO_SCHED_SCAN_GATE
ScummV5_C4_Scheduler_Frame__freeze_trace_done:
    .endif
    jmp ScummV5_C4_Scheduler_Frame__advance
ScummV5_C4_Scheduler_Frame__eligible:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__eligible_trace_done
    lda #$36
    sta.l SAME_SCUMM_SCENARIO_SCHED_GATE
    lda #$36
    sta.l $7E57A4
ScummV5_C4_Scheduler_Frame__eligible_trace_done:
    .a8
    .endif
    .i8
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    lda #$05
    jsr ScummV5_M25A_Trace
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Capture the sentence owner before entering the shared interpreter.
    ; Nested execution is allowed to change currentScript, so this is keyed
    ; to the scheduler-selected sentence slot rather than the transient
    ; shared context.
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    beq ScummV5_C4_Scheduler_Frame__sentence_trace_before_done
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__sentence_trace_before_done
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT
    sep #$10
    .i8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_VM_PC
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    and #$00FF
    asl
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_STATUS
ScummV5_C4_Scheduler_Frame__sentence_trace_before_done:
    .a8
    ; Restore the original scheduler ABI: RunSelected is entered with an
    ; 8-bit index register after the slot load.
    sep #$10
    .i8
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$21
    sta.l SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN
    .endif
    jsr ScummV5_Engine_RunSelected
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Preserve the exact RunSelected return flags before any observational
    ; diagnostics.  The post-run slot restore below performs comparisons and
    ; table lookups which are allowed to change carry; C4 must propagate the
    ; interpreter's original result, not diagnostic arithmetic.
    php
    pla
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_P
    pha
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_PROGRAM
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_STATUS
    lda.l SAME_SCUMM_ERROR
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_ERROR
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_C4_RETURN_PC
    sep #$20
    .a8
    lda #$22
    sta.l SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN
    .endif
    ; Nested execution may legitimately change the shared current-script
    ; context while returning to the scheduler.  The scheduler-owned slot
    ; selected above remains the authoritative owner for saving the yielded
    ; or stopped result; restore that identity before the common post-run
    ; save/retirement path so a child cannot leave its parent at PC zero.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    beq ScummV5_C4_Scheduler_Frame__sentence_trace_after_done
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__sentence_trace_after_done
    lda #$02
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_CURRENT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_VM_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_STATUS
ScummV5_C4_Scheduler_Frame__sentence_trace_after_done:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Restore the exact RunSelected flags after observational state capture.
    ; The saved processor status is still on the stack from immediately after
    ; RunSelected; the common save/retire path must propagate that result, not
    ; carry modified by diagnostic comparisons and table indexing.
    plp
    .endif
    php
    ; Save the scheduler-selected slot, not whichever nested context the
    ; interpreter left in C4_CURRENT_SLOT.
    jsr ScummV5_C4_SaveSchedulerSlot
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    beq ScummV5_C4_Scheduler_Frame__sentence_trace_save_done
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    cmp.l SAME_SCUMM_SCENARIO_SENTENCE_SLOT
    bne ScummV5_C4_Scheduler_Frame__sentence_trace_save_done
    lda #$03
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_PHASE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    and #$00FF
    asl
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_SLOT_PC
    sep #$20
    .a8
    sep #$10
    .i8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_SCENARIO_SENTENCE_SCHED_STATUS
ScummV5_C4_Scheduler_Frame__sentence_trace_save_done:
    .a8
    .endif
    ; A slot may reach the exact end of its bounded program without executing
    ; an explicit A0 stop (the common delay/jump-loop completion boundary).
    ; Retire that scheduler-owned identity just as Op_Stop does; otherwise the
    ; status is stopped but the number/count keep a phantom live script.
    jsr ScummV5_C4_RetireStoppedSlot
    plp
    bcc ScummV5_C4_Scheduler_Frame__save_result_ok
    jmp ScummV5_C4_Scheduler_Frame__error
ScummV5_C4_Scheduler_Frame__save_result_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCHED_OPS
    clc
    adc.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_SCHED_OPS
ScummV5_C4_Scheduler_Frame__advance:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    inc
    sta.l SAME_SCUMM_C4_SCHED_SLOT
    jmp ScummV5_C4_Scheduler_Frame__next_slot
ScummV5_C4_Scheduler_Frame__complete:
    jsr ScummV5_C4_RecountActive
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCHED_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    .if SAME_BUILD_SCUMM_M23A
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$2B
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    sta.l SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN
    .endif
    jsl ScummV5_SentenceProcess_Far
    bcs ScummV5_C4_Scheduler_Frame__error
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    ; The boot visual pre-installs the room that the legacy lifecycle installs
    ; during frame 1. Match that lifecycle's no-movement-update install frame.
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_COUNT
    cmp #$0001
    beq ScummV5_C4_Scheduler_Frame__visual_install_frame
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$2C
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    sta.l SAME_SCUMM_SCENARIO_C4_ERROR_ORIGIN
    .endif
    jsl ScummV5_Movement_UpdateAll_Far
    bcs ScummV5_C4_Scheduler_Frame__error
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; Publish a coherent post-movement actor snapshot for the late visual
    ; service; this does not compose or publish a surface.
    jsl ScummV5_Controller_PublishActorVisual_Far
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$29
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE && SAME_SCUMM_SCENARIO_SOURCE_ACTOR_STATE
    ; Reconcile the source-backed auxiliary actor after the movement pass, so
    ; the fixture checkpoint observes the authored ENCD placement rather than
    ; a transient neutral C31 record.
    jsl ScummV5_Scenario_Fixture_EnsureActor2Room42_Far
    .endif
    ; C23 owns logical message completion at the end of the normal scheduler
    ; pass.  Talk_FrameBegin advances the delay before script execution;
    ; omitting the matching frame-end phase leaves waitForMessage with an
    ; active message forever (or makes a fixture appear to need auto-clear).
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_Talk_FrameEnd_Far
    .endif
ScummV5_C4_Scheduler_Frame__visual_install_frame:
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_FIXTURE_ACTIVE
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_C4_Scheduler_Frame__stopped
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C4_Scheduler_Frame__stopped:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_C4_Scheduler_Frame__error:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$2A
    sta.l SAME_SCUMM_SCENARIO_FRAME_STAGE
    .endif
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    jmp ScummV5_Engine_Frame__error

ScummV5_C4_SaveCurrentSlot:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l SAME_SCUMM_SCENARIO_SAVE_STATUS
    .endif
    rts

; Save the slot selected by the scheduler after RunSelected returns.  This is
; deliberately separate from SaveCurrentSlot: nested execution owns the
; shared current-script context, while the scheduler owns the slot whose
; continuation must survive the frame boundary.
ScummV5_C4_SaveSchedulerSlot:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sep #$10
    .i8
    tax
    rep #$30
    .a16
    .i16
    txa
    and #$00FF
    asl
    tax
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Diagnostic only: prove whether the shared interpreter context still
    ; belongs to the scheduler-selected slot before saving its continuation.
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_SAVE_SHARED_PROGRAM
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sta.l SAME_SCUMM_SCENARIO_SAVE_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_SAVE_SLOT_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_SAVE_SHARED_PC
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_SCENARIO_SAVE_SLOT_PC
    sep #$20
    .a8
    .endif
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SCHED_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    rts

ScummV5_C4_RetireStoppedSlot:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    cmp #SCUMM_VM_STOPPED
    bne ScummV5_C4_RetireStoppedSlot__done
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    beq ScummV5_C4_RetireStoppedSlot__done
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_C4_RetireStoppedSlot__done
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_C4_RetireStoppedSlot__done:
    rts

; Keep the aggregate live-count derived from the authoritative slot table.
; Nested completion and room retirement can change several slots in one
; frame, so incremental accounting alone can retain a phantom script.
ScummV5_C4_RecountActive:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
    ldy #$0000
ScummV5_C4_RecountActive__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_C4_RecountActive__advance
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_C4_RecountActive__advance
    cmp #SCUMM_VM_ERROR
    beq ScummV5_C4_RecountActive__advance
    iny
ScummV5_C4_RecountActive__advance:
    rep #$10
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_RecountActive__next
    tya
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    rts

ScummV5_C4_RunNestedChild:
    .if SAME_BUILD_SCUMM_M23B
    .if SAME_BUILD_M24RB
    jmp ScummV5_M25A_RunNestedChildFar
    .else
    jmp ScummV5_M23B_RunNestedChild
    .endif
    .endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    lda.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_PARENT_STATUS
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_C4_PARENT_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C4_PARENT_PC
    lda.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_PARENT_DELAY
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_C4_PARENT_OPS
    jsr ScummV5_C4_SaveCurrentSlot
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_C4_PARENT_OPS
    sta.l SAME_SCUMM_C4_PARENT_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_PARENT_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_PARENT_PC
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_PARENT_DELAY
    sta.l SAME_SCUMM_DELAY
    lda.l SAME_SCUMM_C4_PARENT_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    plp
    bcc ScummV5_C4_RunNestedChild__success
    sep #$20
    .a8
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rts
ScummV5_C4_RunNestedChild__success:
    clc
    rts

.if SAME_BUILD_SCUMM_M23B
; Canonical startScript runs a newly allocated child immediately.  The caller
; stack is bounded by the 25-slot scheduler: with one current script, at most
; 24 parents can be suspended.  Slot-owned state remains in the slot table;
; each frame retains only the parent slot and its accumulated operation count.
.if SAME_BUILD_M24RB
; M25A keeps the hot opcode dispatcher in bank 0, but the bounded context
; switch is a cold startScript helper. The integrated Fate build calls the
; coherent far implementation through one proper long-call boundary.
ScummV5_M25A_RunNestedChildFar:
    jsl ScummV5_M23B_RunNestedChild_FarEntry
    rts
.else
ScummV5_M23B_NestFrameX:
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    tax
    rts

ScummV5_M23B_RunNestedChild:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    cmp #SAME_SCUMM_M23B_NEST_MAX_DEPTH
    bcc ScummV5_M23B_RunNestedChild__room
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsr ScummV5_SetError
    sec
    rts
ScummV5_M23B_RunNestedChild__room:
    jsr ScummV5_M23B_NestFrameX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_M23B_RunNestedChild__parent_mode_packed
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    ora #$80
ScummV5_M23B_RunNestedChild__parent_mode_packed:
    sta.l SAME_SCUMM_M23B_NEST_FRAMES,x
    phx
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    tax
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23B_NEST_PROGRAMS,x
    rep #$10
    .i16
    plx
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    inc
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    jsr ScummV5_C4_SaveCurrentSlot
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    lda #$01
    sta.l SAME_SCUMM_RETURN_MODE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    dec
    sta.l SAME_SCUMM_M23B_NEST_DEPTH
    jsr ScummV5_M23B_NestFrameX
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sta.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_FRAMES,x
    and #$80
    beq ScummV5_M23B_RunNestedChild__restore_outer_mode
    lda #$01
    bra ScummV5_M23B_RunNestedChild__restore_mode
ScummV5_M23B_RunNestedChild__restore_outer_mode:
    .a8
    lda #$00
ScummV5_M23B_RunNestedChild__restore_mode:
    .a8
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_M23B_NEST_FRAMES,x
    and #$7F
    sta.l SAME_SCUMM_C4_PARENT_SLOT
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    phx
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    tax
    lda.l SAME_SCUMM_M23B_NEST_PROGRAMS,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$10
    .i16
    plx
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_PARENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    jsr ScummV5_M23B_NestFrameX
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23B_NEST_FRAMES+1,x
    sta.l SAME_SCUMM_FRAME_OPS
    plp
    bcc ScummV5_M23B_RunNestedChild__success
    sep #$20
    .a8
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    sec
    rts
ScummV5_M23B_RunNestedChild__success:
    clc
    rts
.endif
.endif

.if SAME_BUILD_SCUMM_M23C
.if !SAME_BUILD_M24RB
; Capture source-program identity, opcode-start PC, and opcode without
; influencing dispatch. Tracing begins only after the generated room target
; is active, so the bounded buffer covers its complete acceptance prefix and
; nested global-script execution.
ScummV5_M23C_TraceOpcode:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    beq ScummV5_M23C_TraceOpcode__room
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    lda.l SAME_SCUMM_SENTENCE_INJECTED
    bne ScummV5_M23C_TraceOpcode__room
    .endif
    rts
ScummV5_M23C_TraceOpcode__room:
    .a8
    lda.l SAME_SCUMM_M23C_TRACE_COUNT
    cmp #SAME_SCUMM_M23C_TRACE_CAPACITY
    bcc ScummV5_M23C_TraceOpcode__space
    lda #$01
    sta.l SAME_SCUMM_M23C_TRACE_OVERFLOW
    rts
ScummV5_M23C_TraceOpcode__space:
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23C_TRACE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    dec
    sta.l SAME_SCUMM_M23C_TRACE+1,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_M23C_TRACE+3,x
    lda.l SAME_SCUMM_M23C_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_M23C_TRACE_COUNT
    rts
.endif
.endif

; Run a freshly allocated replacement without restoring the retired caller.
; Separate operation scratch preserves an enclosing startScript parent frame.
ScummV5_C4_RunAllocatedNoParent:
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    sta.l SAME_SCUMM_C4_CHAIN_OPS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_PC
    lda.l SAME_SCUMM_C4_SLOT_DELAY,x
    sta.l SAME_SCUMM_DELAY
    jsr ScummV5_Engine_RunSelected
    php
    jsr ScummV5_C4_SaveCurrentSlot
    rep #$20
    .a16
    lda.l SAME_SCUMM_FRAME_OPS
    clc
    adc.l SAME_SCUMM_C4_CHAIN_OPS
    sta.l SAME_SCUMM_FRAME_OPS
    plp
    rts

; Stop every live global/local script with the requested number. A8 holds the
; number on entry. Script zero is handled by the opcode as self-stop.
ScummV5_C4_StopNumber:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    ldx #$0000
ScummV5_C4_StopNumber__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_C4_StopNumber__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_C4_StopNumber__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_C4_StopNumber__next
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp.l SAME_SCUMM_CONDITION
    bne ScummV5_C4_StopNumber__next
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_C4_StopNumber__current
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_C4_StopNumber__current:
    .a8
    .i16
    txa
    cmp.l SAME_SCUMM_C4_CURRENT_SLOT
    bne ScummV5_C4_StopNumber__next
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
ScummV5_C4_StopNumber__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_C4_StopNumber__scan
    lda.l SAME_SCUMM_CONDITION
    rts

ScummV5_Engine_Suspend:
    clc
    rts
ScummV5_Engine_Resume:
    clc
    rts
ScummV5_Engine_Shutdown:
    clc
    rts

; ---------------------------------------------------------------------------
; Opcode handlers
; ---------------------------------------------------------------------------
ScummV5_Op_MatrixOps:
    .if SAME_BUILD_SCUMM_M23A == 0
    jsr ScummV5_MatrixOps_Core
    bcc ScummV5_Op_MatrixOps__inline_success
    jmp ScummV5_Op__error
ScummV5_Op_MatrixOps__inline_success:
    jmp ScummV5_Engine_Frame__next
    .endif

.if SAME_BUILD_SCUMM_M23A == 0
ScummV5_MatrixOps_Core:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_MatrixOps_Core__error
    sta.l SAME_SCUMM_C10_SUBOP
    sta.l SAME_SCUMM_MATRIX_LAST_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_MatrixOps_Core__unsupported
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcs ScummV5_MatrixOps_Core__error
    sta.l SAME_SCUMM_MATRIX_LAST_BOX
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcs ScummV5_MatrixOps_Core__error
    sta.l SAME_SCUMM_MATRIX_LAST_FLAGS
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    cmp #$FF
    beq ScummV5_MatrixOps_Core__success
    lda.l SAME_SCUMM_MATRIX_BOX_COUNT
    beq ScummV5_MatrixOps_Core__success
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    cmp.l SAME_SCUMM_MATRIX_BOX_COUNT
    bcs ScummV5_MatrixOps_Core__bad_box
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_MATRIX_LAST_FLAGS
    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS,x
    lda.l SAME_SCUMM_MATRIX_EXEC_COUNT
    inc
    sta.l SAME_SCUMM_MATRIX_EXEC_COUNT
    jsr ScummV5_MatrixOps_Trace
ScummV5_MatrixOps_Core__success:
    clc
    rts
ScummV5_MatrixOps_Core__unsupported:
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
ScummV5_MatrixOps_Core__error:
    sec
    rts
ScummV5_MatrixOps_Core__bad_box:
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    sec
    rts

; Diagnostic evidence only: record exact decoded instruction boundaries.
ScummV5_MatrixOps_Trace:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_TRACE_COUNT
    cmp #SAME_SCUMM_MATRIX_TRACE_CAPACITY
    bcs ScummV5_MatrixOps_Trace__done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_LAST_SUBOP
    sta.l SAME_SCUMM_MATRIX_TRACE,x
    lda.l SAME_SCUMM_MATRIX_LAST_BOX
    sta.l SAME_SCUMM_MATRIX_TRACE+1,x
    lda.l SAME_SCUMM_MATRIX_LAST_FLAGS
    sta.l SAME_SCUMM_MATRIX_TRACE+2,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sec
    sbc #$0004
    sta.l SAME_SCUMM_MATRIX_TRACE+3,x
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_MATRIX_TRACE+5,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_MATRIX_TRACE_COUNT
ScummV5_MatrixOps_Trace__done:
    rts
.endif

.if SAME_BUILD_SCUMM_M23A == 0
ScummV5_Matrix_ResetFixtureState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Matrix_ResetFixtureState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_MATRIX_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_MATRIX_STATE_SIZE
    bcc ScummV5_Matrix_ResetFixtureState__clear
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_MATRIX_BOX_COUNT
    lda #$11
    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS+1
    lda #$22
    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS+2
    rts
.endif

ScummV5_Op_RoomOps:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_RoomOps__subop_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_Op_RoomOps__dispatch_02
    jmp ScummV5_Op_RoomOps__scroll
ScummV5_Op_RoomOps__dispatch_02:
    .a8
    cmp #$02
    bne ScummV5_Op_RoomOps__dispatch_03
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__dispatch_03:
    .a8
    cmp #$03
    bne ScummV5_Op_RoomOps__dispatch_04
    jmp ScummV5_Op_RoomOps__screen
ScummV5_Op_RoomOps__dispatch_04:
    .a8
    cmp #$04
    bne ScummV5_Op_RoomOps__dispatch_05
    jmp ScummV5_Op_RoomOps__palette
ScummV5_Op_RoomOps__dispatch_05:
    .a8
    cmp #$05
    bne ScummV5_Op_RoomOps__dispatch_06
    jmp ScummV5_Op_RoomOps__shake_on
ScummV5_Op_RoomOps__dispatch_06:
    .a8
    cmp #$06
    bne ScummV5_Op_RoomOps__dispatch_07
    jmp ScummV5_Op_RoomOps__shake_off
ScummV5_Op_RoomOps__dispatch_07:
    .a8
    cmp #$07
    bne ScummV5_Op_RoomOps__dispatch_08
    jmp ScummV5_Op_RoomOps__scale
ScummV5_Op_RoomOps__dispatch_08:
    .a8
    cmp #$08
    bne ScummV5_Op_RoomOps__dispatch_09
    jmp ScummV5_Op_RoomOps__intensity
ScummV5_Op_RoomOps__dispatch_09:
    .a8
    cmp #$09
    bne ScummV5_Op_RoomOps__dispatch_0a
    jmp ScummV5_Op_RoomOps__savegame
ScummV5_Op_RoomOps__dispatch_0a:
    .a8
    cmp #$0A
    bne ScummV5_Op_RoomOps__dispatch_0b
    jmp ScummV5_Op_RoomOps__fade
ScummV5_Op_RoomOps__dispatch_0b:
    .a8
    cmp #$0B
    bne ScummV5_Op_RoomOps__dispatch_0c
    jmp ScummV5_Op_RoomOps__rgb
ScummV5_Op_RoomOps__dispatch_0c:
    .a8
    cmp #$0C
    bne ScummV5_Op_RoomOps__dispatch_0d
    jmp ScummV5_Op_RoomOps__shadow
ScummV5_Op_RoomOps__dispatch_0d:
    .a8
    cmp #$0D
    bne ScummV5_Op_RoomOps__dispatch_0e
    jmp ScummV5_Op_RoomOps__save_string
ScummV5_Op_RoomOps__dispatch_0e:
    .a8
    cmp #$0E
    bne ScummV5_Op_RoomOps__dispatch_0f
    jmp ScummV5_Op_RoomOps__load_string
ScummV5_Op_RoomOps__dispatch_0f:
    .a8
    cmp #$0F
    bne ScummV5_Op_RoomOps__dispatch_10
    jmp ScummV5_Op_RoomOps__transform
ScummV5_Op_RoomOps__dispatch_10:
    .a8
    cmp #$10
    bne ScummV5_Op_RoomOps__dispatch_invalid
    jmp ScummV5_Op_RoomOps__cycle
ScummV5_Op_RoomOps__dispatch_invalid:
    jmp ScummV5_Op_RoomOps__invalid

ScummV5_Op_RoomOps__scroll:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_1
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_1:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_2
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_2:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_ROOM_WIDTH
    sec
    sbc #$00A0
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$00A0
    bcs ScummV5_Op_RoomOps__scroll_min_half
    lda #$00A0
ScummV5_Op_RoomOps__scroll_min_half:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_RoomOps__scroll_min_ready
    lda.l SAME_SCUMM_OPERAND
ScummV5_Op_RoomOps__scroll_min_ready:
    .a16
    sta.l SAME_SCUMM_C10_SCROLL_MIN
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$00A0
    bcs ScummV5_Op_RoomOps__scroll_max_half
    lda #$00A0
ScummV5_Op_RoomOps__scroll_max_half:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_RoomOps__scroll_max_ready
    lda.l SAME_SCUMM_OPERAND
ScummV5_Op_RoomOps__scroll_max_ready:
    sta.l SAME_SCUMM_C10_SCROLL_MAX
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__screen:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_3
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_3:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_4
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_4:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp.l SAME_SCUMM_C10_PARAM1
    bcc ScummV5_Op_RoomOps__screen_ordered
    beq ScummV5_Op_RoomOps__screen_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__screen_ordered:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$00C9
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_1
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_1:
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SCREEN_TOP
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SCREEN_BOTTOM
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__palette:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_5
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_5:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_6
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_6:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_7
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_7:
    .a16
    sta.l SAME_SCUMM_C10_PARAM2
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_2
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_2:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_3
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_3:
    .a16
    lda.l SAME_SCUMM_C10_PARAM2
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_4
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_4:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_8
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_8:
    .a8
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_9
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_9:
    .a8
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_C10_MarkPalette
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_SCUMM_PRODUCT
    asl
    clc
    adc.l SAME_SCUMM_PRODUCT
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_PALETTE_RGB,x
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_PALETTE_RGB+1,x
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_PALETTE_RGB+2,x
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__shake_on:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C10_SHAKE
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__shake_off:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C10_SHAKE
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__scale:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_10
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_10:
    .a8
    sta.l SAME_SCUMM_C10_PARAM0
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_11
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_11:
    .a8
    sta.l SAME_SCUMM_C10_PARAM1
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_12
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_12:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_13
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_13:
    .a8
    sta.l SAME_SCUMM_C10_PARAM2
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_14
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_14:
    .a8
    sta.l SAME_SCUMM_C10_PARAM3
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_15
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_15:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_16
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_16:
    .a8
    cmp #$01
    bcs ScummV5_Op_RoomOps__invalid_bcc_ok_1
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcc_ok_1:
    .a8
    cmp #$05
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_5
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_5:
    dec
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SCALE_SLOTS,x
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+1,x
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+2,x
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_SCALE_SLOTS+3,x
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__intensity:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_17
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_17:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY
    sta.l SAME_SCUMM_C10_INTENSITY+1
    sta.l SAME_SCUMM_C10_INTENSITY+2
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_18
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_18:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY+3
    lda #$20
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_19
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_19:
    .a8
    sta.l SAME_SCUMM_C10_INTENSITY+4
    lda.l SAME_SCUMM_C10_INTENSITY+3
    cmp.l SAME_SCUMM_C10_INTENSITY+4
    bcs ScummV5_Op_RoomOps__done_bcc_skip_1
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__done_bcc_skip_1:
    bne ScummV5_Op_RoomOps__done_beq_skip_1
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__done_beq_skip_1:
    jmp ScummV5_Op_RoomOps__invalid

ScummV5_Op_RoomOps__savegame:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_20
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_20:
    .a8
    sta.l SAME_SCUMM_C10_SAVE_FLAG
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_21
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_21:
    .a8
    lda #$63
    sta.l SAME_SCUMM_C10_SAVE_SLOT
    .if SAME_BUILD_SCUMM_M20
    lda.l SAME_SCUMM_C10_SAVE_FLAG
    cmp #$01
    beq ScummV5_Op_RoomOps__savegame_write
    cmp #$02
    beq ScummV5_Op_RoomOps__savegame_load
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__savegame_load:
    .a8
    lda #SAME_SAVE_OP_READ_SLOT
    bra ScummV5_Op_RoomOps__savegame_emit
ScummV5_Op_RoomOps__savegame_write:
    .a8
    lda #SAME_SAVE_OP_WRITE_SLOT
ScummV5_Op_RoomOps__savegame_emit:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_SAVE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda.l SAME_SCUMM_C10_SUBOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_KERNEL
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda #$0063
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bcc ScummV5_Op_RoomOps__savegame_queued
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
    .if SAME_BUILD_SCUMM_M23B
    pha
    lda #$01
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    pla
    .endif
    jsr ScummV5_SetError
    sec
    jmp ScummV5_Engine_Frame__error
ScummV5_Op_RoomOps__savegame_queued:
    .endif
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__fade:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_22
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_22:
    .a16
    sta.l SAME_SCUMM_C10_FADE
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__rgb:
    sep #$20
    .a8
    lda #$00
    bra ScummV5_Op_RoomOps__five_colors
ScummV5_Op_RoomOps__shadow:
    sep #$20
    .a8
    lda #$01
ScummV5_Op_RoomOps__five_colors:
    sta.l SAME_SCUMM_C10_PARAM4
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_23
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_23:
    .a16
    sta.l SAME_SCUMM_C10_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_24
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_24:
    .a16
    sta.l SAME_SCUMM_C10_PARAM1
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C10_FetchWordParam
    bcc ScummV5_Op_RoomOps__error_ok_25
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_25:
    .a16
    sta.l SAME_SCUMM_C10_PARAM2
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_6
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_6:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_7
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_7:
    .a16
    lda.l SAME_SCUMM_C10_PARAM2
    cmp #$0100
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_8
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_8:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_26
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_26:
    .a8
    sep #$20
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_27
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_27:
    .a8
    sta.l SAME_SCUMM_C10_PARAM3
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_28
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_28:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_Op_RoomOps__five_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__five_ordered:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM4
    cmp #$00
    beq ScummV5_Op_RoomOps__store_rgb
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_SHADOW
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_SHADOW+1
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_SHADOW+2
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_SHADOW+3
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_SHADOW+4
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__store_rgb:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_C10_RGB_INTENSITY
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+1
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+2
    lda.l SAME_SCUMM_C10_PARAM3
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+3
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+4
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__save_string:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_29
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_29:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C10_ReadFilename
    bcc ScummV5_Op_RoomOps__error_ok_30
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_30:
    .a8
    jsr ScummV5_C10_SaveAuxString
    bcc ScummV5_Op_RoomOps__error_ok_31
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_31:
    .a8
    jmp ScummV5_Op_RoomOps__done
ScummV5_Op_RoomOps__load_string:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_32
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_32:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C10_ReadFilename
    bcc ScummV5_Op_RoomOps__error_ok_33
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_33:
    .a8
    jsr ScummV5_C10_LoadAuxString
    bcc ScummV5_Op_RoomOps__error_ok_34
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_34:
    .a8
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__transform:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_35
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_35:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_36
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_36:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_37
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_37:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+1
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_38
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_38:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+2
    cmp.l SAME_SCUMM_C10_TRANSFORM+1
    bcs ScummV5_Op_RoomOps__transform_ordered
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__transform_ordered:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_RoomOps__error_ok_39
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_39:
    .a8
    sta.l SAME_SCUMM_C10_SUBOP
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_40
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_40:
    .a8
    sta.l SAME_SCUMM_C10_TRANSFORM+3
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__cycle:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_41
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_41:
    .a8
    cmp #$01
    bcs ScummV5_Op_RoomOps__invalid_bcc_ok_2
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcc_ok_2:
    .a8
    cmp #$11
    bcc ScummV5_Op_RoomOps__invalid_bcs_ok_9
    jmp ScummV5_Op_RoomOps__invalid
ScummV5_Op_RoomOps__invalid_bcs_ok_9:
    .a8
    dec
    sta.l SAME_SCUMM_C10_PARAM0
    lda #$40
    jsr ScummV5_C10_FetchByteParam
    bcc ScummV5_Op_RoomOps__error_ok_42
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_42:
    .a8
    jsr ScummV5_C10_StoreCycleDelay
    bcc ScummV5_Op_RoomOps__error_ok_43
    jmp ScummV5_Op_RoomOps__error
ScummV5_Op_RoomOps__error_ok_43:
    .a8
    jmp ScummV5_Op_RoomOps__done

ScummV5_Op_RoomOps__invalid:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_SUBOP
    sta.l SAME_SCUMM_M23C_ERROR_SUBOP
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23C_ERROR_PROGRAM
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_M23C_ERROR_OPCODE
    lda #$31
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    lda #SCUMM_ERR_ROOM_OPS
    jsr ScummV5_SetError
ScummV5_Op_RoomOps__error:
    jmp ScummV5_Op__error
ScummV5_Op_RoomOps__done:
    sep #$20
    .a8
    lda #$33
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_GetRandom:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_GetRandom__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_GetRandom__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_GetRandom__maximum_ok
    jmp ScummV5_Op__error
ScummV5_Op_GetRandom__maximum_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C11_MAXIMUM
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C11_MAXIMUM
    lda.l SAME_SCUMM_C11_RANDOM_STATE
    lsr
    bcc ScummV5_Op_GetRandom__state_ready
    eor #$B400
ScummV5_Op_GetRandom__state_ready:
    .a16
    sta.l SAME_SCUMM_C11_RANDOM_STATE
    xba
    and #$00FF
    sta.l SAME_SCUMM_C11_SAMPLE
    lda.l SAME_SCUMM_C11_MAXIMUM
    cmp #$00FF
    beq ScummV5_Op_GetRandom__full_byte
    inc
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C11_SAMPLE
ScummV5_Op_GetRandom__reduce:
    .a16
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_GetRandom__store
    sec
    sbc.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_GetRandom__reduce
ScummV5_Op_GetRandom__full_byte:
    .a16
    lda.l SAME_SCUMM_C11_SAMPLE
ScummV5_Op_GetRandom__store:
    .a16
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_PseudoRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C12_INITIALIZED
    bne ScummV5_Op_PseudoRoom__state_ready
    jsr ScummV5_C12_ResetState
ScummV5_Op_PseudoRoom__state_ready:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_PseudoRoom__error
    sta.l SAME_SCUMM_C12_ROOM
ScummV5_Op_PseudoRoom__next:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_PseudoRoom__error
    beq ScummV5_Op_PseudoRoom__done
    bpl ScummV5_Op_PseudoRoom__next
    and #$7F
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C12_ROOM
    sta.l SAME_SCUMM_C12_MAPPER,x
    bra ScummV5_Op_PseudoRoom__next
ScummV5_Op_PseudoRoom__done:
    .a8
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_PseudoRoom__error:
    jmp ScummV5_Op__error

ScummV5_Op_ResourceRoutines:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_INITIALIZED
    bne ScummV5_Op_ResourceRoutines__state_ready
    jsr ScummV5_C13_ResetState
ScummV5_Op_ResourceRoutines__state_ready:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_ResourceRoutines__selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__selector_ok:
    .a8
    sta.l SAME_SCUMM_C13_SELECTOR
    and #$3F
    sta.l SAME_SCUMM_C13_OPERATION
    cmp #$11
    bne ScummV5_Op_ResourceRoutines__not_clear_heap
    jmp ScummV5_Op_ResourceRoutines__done
ScummV5_Op_ResourceRoutines__not_clear_heap:
    .a8
    cmp #$01
    bcs ScummV5_Op_ResourceRoutines__minimum_ok
    jmp ScummV5_Op_ResourceRoutines__invalid
ScummV5_Op_ResourceRoutines__minimum_ok:
    .a8
    cmp #$15
    bcc ScummV5_Op_ResourceRoutines__maximum_ok
    jmp ScummV5_Op_ResourceRoutines__invalid
ScummV5_Op_ResourceRoutines__maximum_ok:
    .a8
    cmp #$14
    bne ScummV5_Op_ResourceRoutines__not_object
    jmp ScummV5_Op_ResourceRoutines__object
ScummV5_Op_ResourceRoutines__not_object:
    .a8
    lda.l SAME_SCUMM_C13_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ResourceRoutines__resource_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__resource_ok:
    .a8
    sta.l SAME_SCUMM_C13_RESOURCE
    lda.l SAME_SCUMM_C13_OPERATION
    cmp #$05
    bcc ScummV5_Op_ResourceRoutines__load_kind
    cmp #$09
    bcc ScummV5_Op_ResourceRoutines__nuke_kind
    cmp #$0D
    bcc ScummV5_Op_ResourceRoutines__lock_kind
    cmp #$11
    bcc ScummV5_Op_ResourceRoutines__unlock_kind
    cmp #$12
    beq ScummV5_Op_ResourceRoutines__charset_load
    ; Operation $13 is the only remaining valid non-object operation.
    lda #$04
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_ClearLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__load_kind:
    .a8
    dec
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_SetLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__nuke_kind:
    .a8
    sec
    sbc #$05
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_ClearLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__lock_kind:
    .a8
    sec
    sbc #$09
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_SetLocked
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__unlock_kind:
    .a8
    sec
    sbc #$0D
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    jsr ScummV5_C13_ClearLocked
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__charset_load:
    .a8
    lda #$04
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_SetLoaded
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__object:
    .a8
    lda.l SAME_SCUMM_C13_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ResourceRoutines__object_room_ok
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__object_room_ok:
    .a8
    sta.l SAME_SCUMM_C13_RESOURCE
    lda #$03
    sta.l SAME_SCUMM_C13_KIND
    jsr ScummV5_C13_MapRoomKind
    lda.l SAME_SCUMM_C13_SELECTOR
    and #$40
    beq ScummV5_Op_ResourceRoutines__object_direct
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ResourceRoutines__operand_error
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_Op_ResourceRoutines__operand_error
    bra ScummV5_Op_ResourceRoutines__object_id_ok
ScummV5_Op_ResourceRoutines__object_direct:
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ResourceRoutines__operand_error
ScummV5_Op_ResourceRoutines__object_id_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C13_LAST_OBJECT_ID
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_RESOURCE
    sta.l SAME_SCUMM_C13_LAST_OBJECT_ROOM
    jsr ScummV5_C13_SetLoaded
ScummV5_Op_ResourceRoutines__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ResourceRoutines__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ResourceRoutines__invalid:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda #$E5
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    .endif
    lda #SCUMM_ERR_RESOURCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

; v5 wait sub-op family.  The authored transition uses forCamera ($03).
; Camera completion is owned by the presentation service, so consuming the
; sub-op and yielding preserves the scheduler boundary without inventing a
; second camera state machine in the SCUMM core.
ScummV5_Op_Wait:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Wait__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Wait__operand_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_SUBOP
    and #$1F
    cmp #$01
    beq ScummV5_Op_Wait__actor
    cmp #$02
    beq ScummV5_Op_Wait__message
    cmp #$03
    bne ScummV5_Op_Wait__not_camera
    jmp ScummV5_Op_Wait__camera
ScummV5_Op_Wait__not_camera:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Wait__actor:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_SUBOP
    and #$80
    beq ScummV5_Op_Wait__actor_direct
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_Wait__actor_word_ok
    jmp ScummV5_Op__error
ScummV5_Op_Wait__actor_word_ok:
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_Wait__actor_var_ok
    jmp ScummV5_Op__error
ScummV5_Op_Wait__actor_var_ok:
    bra ScummV5_Op_Wait__actor_test
ScummV5_Op_Wait__actor_direct:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Wait__actor_direct_ok
    jmp ScummV5_Op__error
ScummV5_Op_Wait__actor_direct_ok:
ScummV5_Op_Wait__actor_test:
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_MOVING,x
    beq ScummV5_Op_Wait__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_SUBOP
    and #$0080
    beq ScummV5_Op_Wait__rewind_direct
    lda.l SAME_SCUMM_PC
    sec
    sbc #$0004
    sta.l SAME_SCUMM_PC
    bra ScummV5_Op_Wait__yield
ScummV5_Op_Wait__rewind_direct:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    sec
    ; Direct waitForActor is AE,sub-op,actor: rewind the complete
    ; three-byte instruction so the next scheduler pass re-enters the
    ; generic wait decoder.  Rewinding only the operand pair leaves PC on
    ; the sub-op byte and desynchronizes the enclosing script.
    sbc #$0003
    sta.l SAME_SCUMM_PC
ScummV5_Op_Wait__yield:
    .if SAME_BUILD_SCUMM_M23A
    ; Match breakHere's established suspension boundary: publish the fully
    ; decoded PC/program context before returning control to C4.
    jsl ScummV5_LoadRoomWithEgo_Postamble_Far
    .endif
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_Wait__message:
    ; Headless mode removes only presentation ownership.  Logical message
    ; lifetime remains owned by the talk service, so the authored wait must
    ; observe the same active/complete state as production.
    lda.l SAME_SCUMM_TALK_ACTIVE
    bne ScummV5_Op_Wait__yield_simple
    bra ScummV5_Op_Wait__done
ScummV5_Op_Wait__camera:
    ; Camera destination convergence is represented by the generic camera
    ; service; its wait is a scheduler yield until the next presentation pass.
ScummV5_Op_Wait__yield_simple:
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_Wait__done:
    jmp ScummV5_Engine_Frame__next

; faceActor (including flagged actor/target operands).  Facing is a
; presentation-side mutation; the interpreter must still consume both
; source-defined operands before returning to the scheduler.
ScummV5_Op_FaceActor:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_FaceActor__byte_ok
    jmp ScummV5_Op__error
ScummV5_Op_FaceActor__byte_ok:
    sep #$20
    .a8
    lda #$40
    ; The second operand is the canonical flagged WORD target.  Consuming
    ; only its low byte leaves the high byte to be dispatched as the next
    ; opcode (often $00/stop), which falsely trips the active-cutscene
    ; retirement guard before the authored $C0 endCutscene.  Keep operand
    ; width aligned with the host v5 faceActor implementation.
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_FaceActor__word_ok
    jmp ScummV5_Op__error
ScummV5_Op_FaceActor__word_ok:
    jmp ScummV5_Engine_Frame__next

; Normalize high-bit room IDs through the C12 pseudo-room table before they
; become cache or lock keys. Other resource kinds pass through unchanged.
ScummV5_C13_MapRoomKind:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_KIND
    cmp #$03
    bne ScummV5_C13_MapRoomKind__done
    lda.l SAME_SCUMM_C13_RESOURCE
    bpl ScummV5_C13_MapRoomKind__done
    lda.l SAME_SCUMM_C12_INITIALIZED
    bne ScummV5_C13_MapRoomKind__mapper_ready
    jsr ScummV5_C12_ResetState
ScummV5_C13_MapRoomKind__mapper_ready:
    rep #$10
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_C13_RESOURCE
    and #$7F
    tax
    lda.l SAME_SCUMM_C12_MAPPER,x
    sta.l SAME_SCUMM_C13_RESOURCE
ScummV5_C13_MapRoomKind__done:
    rts

; Return X=kind*32+resource/8 and retain the corresponding bit mask.
ScummV5_C13_BitAddress:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C13_KIND
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C13_RESOURCE
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    lsr
    lsr
    lsr
    clc
    adc.l SAME_SCUMM_LHS
    tax
    sep #$20
    .a8
    rts

ScummV5_C13_SetLoaded:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_C13_LOADED,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C13_LOADED,x
    rts

ScummV5_C13_ClearLoaded:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C13_LOADED,x
    sta.l SAME_SCUMM_C13_LOADED,x
    rts

ScummV5_C13_SetLocked:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_C13_LOCKED,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C13_LOCKED,x
    rts

ScummV5_C13_ClearLocked:
    jsr ScummV5_C13_BitAddress
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C13_LOCKED,x
    sta.l SAME_SCUMM_C13_LOCKED,x
    rts

ScummV5_Op_ActorFollowCamera:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_ActorFollowCamera__variable
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorFollowCamera__operand_error
    rep #$20
    .a16
    and #$00FF
    bra ScummV5_Op_ActorFollowCamera__fetched
ScummV5_Op_ActorFollowCamera__variable:
    .a8
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_ActorFollowCamera__operand_error
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_ActorFollowCamera__fetched
ScummV5_Op_ActorFollowCamera__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ActorFollowCamera__fetched:
    rep #$20
    .a16
    cmp #$0020
    bcc ScummV5_Op_ActorFollowCamera__valid
    sep #$20
    .a8
    lda #SCUMM_ERR_CAMERA_FOLLOW
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_ActorFollowCamera__valid:
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C15_CAMERA_FOLLOWS
    lda #$01
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    lda #$00
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    jmp ScummV5_Engine_Frame__next

; Canonical v5 $32/$B2 setCameraAt.  $72/$F2 remain the distinct loadRoom
; opcodes from the authoritative v5 table.
ScummV5_Op_SetCameraAt:
    jml ScummV5_Op_SetCameraAt_Far

; Canonical v5 $1D/$9D ifClassOfIs. Each selector is consumed before the
; relative branch. Bit 7 requires membership; its absence requires non-
; membership. Object/class storage is shared with canonical setClass.
ScummV5_Op_IfClassOfIs:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_INITIALIZED
    bne ScummV5_Op_IfClassOfIs__state_ready
    jsr ScummV5_C16_ResetState
ScummV5_Op_IfClassOfIs__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bpl ScummV5_Op_IfClassOfIs__object_direct
    jmp ScummV5_Op_IfClassOfIs__object_variable
ScummV5_Op_IfClassOfIs__object_direct:
    .a8
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_IfClassOfIs__object_direct_error
    jmp ScummV5_Op_IfClassOfIs__object_ready
ScummV5_Op_IfClassOfIs__object_direct_error:
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__object_variable:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_IfClassOfIs__object_variable_fetched
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__object_variable_fetched:
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_IfClassOfIs__object_ready
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__object_ready:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_OBJECT
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_IfClassOfIs__selector_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_IfClassOfIs__selector_fetched
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__selector_fetched:
    .a8
    cmp #$FF
    bne ScummV5_Op_IfClassOfIs__selector_present
    jmp ScummV5_Op_IfClassOfIs__branch
ScummV5_Op_IfClassOfIs__selector_present:
    sta.l SAME_SCUMM_C25_SELECTOR
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_IfClassOfIs__class_fetched
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__class_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_CLASS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    bpl ScummV5_Op_IfClassOfIs__class_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_IfClassOfIs__class_variable_ok
    jmp ScummV5_Op_IfClassOfIs__error
ScummV5_Op_IfClassOfIs__class_variable_ok:
    sta.l SAME_SCUMM_C16_CLASS
ScummV5_Op_IfClassOfIs__class_ready:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    and #$007F
    bne ScummV5_Op_IfClassOfIs__class_nonzero
    jmp ScummV5_Op_IfClassOfIs__invalid
ScummV5_Op_IfClassOfIs__class_nonzero:
    .a16
    cmp #$0021
    bcc ScummV5_Op_IfClassOfIs__class_valid
    jmp ScummV5_Op_IfClassOfIs__invalid
ScummV5_Op_IfClassOfIs__class_valid:
    .a16
    jsr ScummV5_C16_FindRecord
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_IfClassOfIs__absent
    jsr ScummV5_C16_ClassAddress
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_MASK_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS,x
    and.l SAME_SCUMM_C16_BIT_MASK
    beq ScummV5_Op_IfClassOfIs__absent
    lda #$01
    bra ScummV5_Op_IfClassOfIs__membership_ready
ScummV5_Op_IfClassOfIs__absent:
    sep #$20
    .a8
    lda #$00
ScummV5_Op_IfClassOfIs__membership_ready:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    lda.l SAME_SCUMM_C16_CLASS
    and #$80
    beq ScummV5_Op_IfClassOfIs__requires_absent
    lda.l SAME_SCUMM_FETCH_BYTE
    bne ScummV5_Op_IfClassOfIs__selector_done
    bra ScummV5_Op_IfClassOfIs__mismatch
ScummV5_Op_IfClassOfIs__requires_absent:
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_Op_IfClassOfIs__selector_done
ScummV5_Op_IfClassOfIs__mismatch:
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_IfClassOfIs__selector_done:
    jmp ScummV5_Op_IfClassOfIs__selector_loop
ScummV5_Op_IfClassOfIs__branch:
    ; Authored-room differential evidence: retain the final object/class
    ; predicate and its branch decision without changing the generic opcode.
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l $7E5470
    lda.l SAME_SCUMM_C16_CLASS
    sta.l $7E5472
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l $7E5474
    lda.l SAME_SCUMM_CONDITION
    sta.l $7E568E
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l $7E568F
    lda.l SAME_SCUMM_C16_CLASS
    sta.l $7E5691
    lda.l $7E57F0
    and #$0007
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l $7E5800,x
    lda.l SAME_SCUMM_C16_CLASS
    sta.l $7E5802,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l $7E5804,x
    lda.l $7E57F0
    inc
    sta.l $7E57F0
    .if SAME_BUILD_SCUMM_M23C
    lda.l SAME_SCUMM_M23C_CLASS_EVAL_COUNT
    inc
    sta.l SAME_SCUMM_M23C_CLASS_EVAL_COUNT
    lda.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_IfClassOfIs__branch_counted
    lda.l SAME_SCUMM_M23C_CLASS_TRUE_COUNT
    inc
    sta.l SAME_SCUMM_M23C_CLASS_TRUE_COUNT
ScummV5_Op_IfClassOfIs__branch_counted:
    .endif
    jsr ScummV5_ApplyConditionOffset
    bcs ScummV5_Op_IfClassOfIs__error
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_IfClassOfIs__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_IF_CLASS
    jsr ScummV5_SetError
ScummV5_Op_IfClassOfIs__error:
    jmp ScummV5_Op__error

; Canonical v5 $5D/$DD setClass. Object ids remain full u16 values and each
; selector is a direct/variable word whose low seven bits name class 1..32.
; Bit 7 sets the class, its absence removes it, and raw zero clears all.
ScummV5_Op_SetClass:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_INITIALIZED
    bne ScummV5_Op_SetClass__state_ready
    jsr ScummV5_C16_ResetState
ScummV5_Op_SetClass__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_SetClass__object_variable
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__object_direct_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_direct_ok:
    bra ScummV5_Op_SetClass__object_ready
ScummV5_Op_SetClass__object_variable:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__object_reference_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_reference_ok:
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SetClass__object_ready
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__object_ready:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_OBJECT
    sta.l $7E5476
ScummV5_Op_SetClass__selector_loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetClass__selector_fetched
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__selector_fetched:
    .a8
    cmp #$FF
    bne ScummV5_Op_SetClass__selector_present
    jmp ScummV5_Op_SetClass__done
ScummV5_Op_SetClass__selector_present:
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetClass__class_fetched
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__class_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C16_CLASS
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    bpl ScummV5_Op_SetClass__class_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SetClass__class_variable_ok
    jmp ScummV5_Op_SetClass__operand_error
ScummV5_Op_SetClass__class_variable_ok:
    sta.l SAME_SCUMM_C16_CLASS
ScummV5_Op_SetClass__class_ready:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_CLASS
    sta.l $7E5478
    bne ScummV5_Op_SetClass__nonzero
    jmp ScummV5_Op_SetClass__clear_all
ScummV5_Op_SetClass__nonzero:
    .a16
    and #$007F
    bne ScummV5_Op_SetClass__class_nonzero
    jmp ScummV5_Op_SetClass__invalid
ScummV5_Op_SetClass__class_nonzero:
    .a16
    cmp #$0021
    bcc ScummV5_Op_SetClass__class_valid
    jmp ScummV5_Op_SetClass__invalid
ScummV5_Op_SetClass__class_valid:
    jsr ScummV5_C16_FindRecord
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_CLASS
    bmi ScummV5_Op_SetClass__set
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__clear_present
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_present:
    jsr ScummV5_C16_ClassAddress
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_MASK_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_BIT_MASK
    eor #$FF
    and.l SAME_SCUMM_C16_RECORDS,x
    sta.l SAME_SCUMM_C16_RECORDS,x
    jsr ScummV5_C16_FreeIfEmpty
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__set:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__set_address
    lda.l SAME_SCUMM_C16_FREE_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SetClass__invalid
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C16_OBJECT
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT,x
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_PRESENT,x
ScummV5_Op_SetClass__set_address:
    jsr ScummV5_C16_ClassAddress
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_MASK_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS,x
    ora.l SAME_SCUMM_C16_BIT_MASK
    sta.l SAME_SCUMM_C16_RECORDS,x
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_all:
    jsr ScummV5_C16_FindRecord
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SetClass__clear_all_present
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__clear_all_present:
    jsr ScummV5_C16_ClearRecord
    jmp ScummV5_Op_SetClass__selector_loop
ScummV5_Op_SetClass__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SetClass__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_SetClass__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_SET_CLASS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

; Locate the object record and first reusable slot in one bounded scan.
; Generated room/scenario data lives in a separate LoROM bank.  Keep the
; bank-local implementation below, but expose the normal JSL/RTL adapter for
; generated far helpers rather than letting them issue a bank-relative JSR.
ScummV5_C16_FindRecord_Far:
    jsr ScummV5_C16_FindRecord
    rtl

ScummV5_C16_FindRecord:
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    sta.l SAME_SCUMM_C16_FREE_OFFSET
    ldx #$0000
ScummV5_C16_FindRecord__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_PRESENT,x
    bne ScummV5_C16_FindRecord__occupied
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_C16_FindRecord__next
    txa
    sta.l SAME_SCUMM_C16_FREE_OFFSET
    bra ScummV5_C16_FindRecord__next
ScummV5_C16_FindRecord__occupied:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT,x
    cmp.l SAME_SCUMM_C16_OBJECT
    bne ScummV5_C16_FindRecord__next
    txa
    sta.l SAME_SCUMM_C16_RECORD_OFFSET
    rts
ScummV5_C16_FindRecord__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C16_RECORD_STRIDE
    tax
    cpx #$1000
    bcc ScummV5_C16_FindRecord__loop
    rts

; Convert class 1..32 to the byte and bit within the selected record mask.
ScummV5_C16_ClassAddress:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_CLASS
    and #$007F
    dec
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_C16_BIT_MASK
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    clc
    adc #SAME_SCUMM_C16_R_MASK
    adc.l SAME_SCUMM_C16_RECORD_OFFSET
    sta.l SAME_SCUMM_C16_MASK_OFFSET
    rts

ScummV5_C16_ClearRecord:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda #$0000
    sta.l SAME_SCUMM_C16_RECORDS,x
    sta.l SAME_SCUMM_C16_RECORDS+2,x
    sta.l SAME_SCUMM_C16_RECORDS+4,x
    sta.l SAME_SCUMM_C16_RECORDS+6,x
    rts

ScummV5_C16_FreeIfEmpty:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C16_RECORDS+4,x
    ora.l SAME_SCUMM_C16_RECORDS+6,x
    bne ScummV5_C16_FreeIfEmpty__done
    jsr ScummV5_C16_ClearRecord
ScummV5_C16_FreeIfEmpty__done:
    rts

; Canonical v5 $7A/$FA verbOps. Configuration remains engine-owned; the
; video/input adapters decide when and how to draw or hit-test the resulting
; verb records.
ScummV5_Op_VerbOps:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_INITIALIZED
    bne ScummV5_Op_VerbOps__state_ready
    jsr ScummV5_C17_ResetState
ScummV5_Op_VerbOps__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C17_SUBOP
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__verb_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__verb_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_VERB
    jsr ScummV5_C17_RecordOffset
ScummV5_Op_VerbOps__loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_VerbOps__selector_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__selector_ok:
    .a8
    cmp #$FF
    bne ScummV5_Op_VerbOps__selector_present
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_VerbOps__selector_present:
    .a8
    sta.l SAME_SCUMM_C17_SUBOP
    and #$1F
    cmp #$01
    bne ScummV5_Op_VerbOps__check_name
    jmp ScummV5_Op_VerbOps__image
ScummV5_Op_VerbOps__check_name:
    .a8
    cmp #$02
    bne ScummV5_Op_VerbOps__check_color
    jmp ScummV5_Op_VerbOps__name
ScummV5_Op_VerbOps__check_color:
    .a8
    cmp #$03
    bne ScummV5_Op_VerbOps__check_hicolor
    jmp ScummV5_Op_VerbOps__color
ScummV5_Op_VerbOps__check_hicolor:
    .a8
    cmp #$04
    bne ScummV5_Op_VerbOps__check_at
    jmp ScummV5_Op_VerbOps__hicolor
ScummV5_Op_VerbOps__check_at:
    .a8
    cmp #$05
    bne ScummV5_Op_VerbOps__check_on
    jmp ScummV5_Op_VerbOps__at
ScummV5_Op_VerbOps__check_on:
    .a8
    cmp #$06
    bne ScummV5_Op_VerbOps__check_off
    jmp ScummV5_Op_VerbOps__on
ScummV5_Op_VerbOps__check_off:
    .a8
    cmp #$07
    bne ScummV5_Op_VerbOps__check_delete
    jmp ScummV5_Op_VerbOps__off
ScummV5_Op_VerbOps__check_delete:
    .a8
    cmp #$08
    bne ScummV5_Op_VerbOps__check_new
    jmp ScummV5_Op_VerbOps__delete
ScummV5_Op_VerbOps__check_new:
    .a8
    cmp #$09
    bne ScummV5_Op_VerbOps__check_dimcolor
    jmp ScummV5_Op_VerbOps__new
ScummV5_Op_VerbOps__check_dimcolor:
    .a8
    cmp #$10
    bne ScummV5_Op_VerbOps__check_dim
    jmp ScummV5_Op_VerbOps__dimcolor
ScummV5_Op_VerbOps__check_dim:
    .a8
    cmp #$11
    bne ScummV5_Op_VerbOps__check_key
    jmp ScummV5_Op_VerbOps__dim
ScummV5_Op_VerbOps__check_key:
    .a8
    cmp #$12
    bne ScummV5_Op_VerbOps__check_center
    jmp ScummV5_Op_VerbOps__key
ScummV5_Op_VerbOps__check_center:
    .a8
    cmp #$13
    bne ScummV5_Op_VerbOps__check_name_string
    jmp ScummV5_Op_VerbOps__center
ScummV5_Op_VerbOps__check_name_string:
    .a8
    cmp #$14
    bne ScummV5_Op_VerbOps__check_object
    jmp ScummV5_Op_VerbOps__name_string
ScummV5_Op_VerbOps__check_object:
    .a8
    cmp #$16
    bne ScummV5_Op_VerbOps__check_background
    jmp ScummV5_Op_VerbOps__object
ScummV5_Op_VerbOps__check_background:
    .a8
    cmp #$17
    beq ScummV5_Op_VerbOps__background_selected
    jmp ScummV5_Op_VerbOps__invalid
ScummV5_Op_VerbOps__background_selected:
    jmp ScummV5_Op_VerbOps__background

ScummV5_Op_VerbOps__image:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__image_operand_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__image_operand_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Op_VerbOps__image_done
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda.l SAME_SCUMM_C17_CURRENT_ROOM
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_ROOM,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_OBJECT,x
ScummV5_Op_VerbOps__image_done:
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__name:
    jsr ScummV5_C17_CopyInlineName
    bcc ScummV5_Op_VerbOps__name_done
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_done:
    jsr ScummV5_C17_MarkText
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__color:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__color_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__color_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_COLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__hicolor:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__hicolor_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__hicolor_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_HICOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__at:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__at_left_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__at_left_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__at_top_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__at_top_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_LEFT,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_ORIG_LEFT,x
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TOP,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__on:
    .a8
    lda #$01
    bra ScummV5_Op_VerbOps__store_mode
ScummV5_Op_VerbOps__off:
    .a8
    lda #$00
    bra ScummV5_Op_VerbOps__store_mode
ScummV5_Op_VerbOps__dim:
    .a8
    lda #$02
ScummV5_Op_VerbOps__store_mode:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__delete:
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__new:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    bne ScummV5_Op_VerbOps__new_defaults
    jsr ScummV5_C17_ClearRecord
    jsr ScummV5_C17_RecordX
ScummV5_Op_VerbOps__new_defaults:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    lda #$02
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_COLOR,x
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_HICOLOR,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_MODE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_KEY,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CENTER,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda #$08
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_DIMCOLOR,x
    lda.l SAME_SCUMM_C7_CHARSET_ID
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CHARSET,x
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__dimcolor:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__dimcolor_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__dimcolor_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_DIMCOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__key:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__key_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__key_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_KEY,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__center:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_CENTER,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__name_string:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__name_string_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_string_ok:
    jsr ScummV5_C17_CopyStringName
    bcc ScummV5_Op_VerbOps__name_string_done
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__name_string_done:
    jsr ScummV5_C17_MarkText
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__object:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchWordParam
    bcc ScummV5_Op_VerbOps__object_id_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__object_id_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__object_room_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__object_room_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    beq ScummV5_Op_VerbOps__object_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    cmp.l SAME_SCUMM_C17_PARAM0
    beq ScummV5_Op_VerbOps__object_done
    lda.l SAME_SCUMM_C17_PARAM0
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_OBJECT,x
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_ROOM,x
ScummV5_Op_VerbOps__object_done:
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__background:
    .a8
    lda #$80
    jsr ScummV5_C17_FetchByteParam
    bcc ScummV5_Op_VerbOps__background_ok
    jmp ScummV5_Op_VerbOps__operand_error
ScummV5_Op_VerbOps__background_ok:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C17_PARAM1
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_PARAM1
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_BKCOLOR,x
    jmp ScummV5_Op_VerbOps__loop

ScummV5_Op_VerbOps__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_VERB_OPS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_VerbOps__operand_error:
    jmp ScummV5_Op__error

ScummV5_C17_FetchByteParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C17_SUBOP
    beq ScummV5_C17_FetchByteParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C17_FetchByteParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C17_FetchByteParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C17_FetchByteParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C17_FetchByteParam__done:
    rts

ScummV5_C17_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C17_SUBOP
    beq ScummV5_C17_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C17_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C17_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C17_FetchWordParam__done:
    rts

ScummV5_C17_RecordOffset:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C17_PARAM0
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_LHS
    asl
    clc
    adc.l SAME_SCUMM_LHS
    sta.l SAME_SCUMM_C17_RECORD_OFFSET
    rts

ScummV5_C17_RecordX:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    rts

ScummV5_C17_ClearRecord:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    clc
    adc #SAME_SCUMM_C17_VERB_STRIDE
    sta.l SAME_SCUMM_C17_PARAM1
ScummV5_C17_ClearRecord__loop:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS,x
    inx
    inx
    txa
    cmp.l SAME_SCUMM_C17_PARAM1
    bcc ScummV5_C17_ClearRecord__loop
    rts

ScummV5_C17_MarkText:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_TYPE,x
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_PRESENT,x
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_IMAGE_INDEX,x
    rts

ScummV5_C17_CopyInlineName:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
ScummV5_C17_CopyInlineName__loop:
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    cmp #SAME_SCUMM_C17_NAME_MAX
    bcc ScummV5_C17_CopyInlineName__room
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyInlineName__room:
    jsr ScummV5_FetchByte
    bcc ScummV5_C17_CopyInlineName__fetched
    rts
ScummV5_C17_CopyInlineName__fetched:
    .a8
    jsr ScummV5_C17_StoreNameByte
    lda.l SAME_SCUMM_C17_CONTROL_ARGS
    beq ScummV5_C17_CopyInlineName__ordinary
    cmp #$FF
    beq ScummV5_C17_CopyInlineName__control_code
    bra ScummV5_C17_CopyInlineName__argument
ScummV5_C17_CopyInlineName__ordinary:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C17_CopyInlineName__done
    cmp #$FF
    bne ScummV5_C17_CopyInlineName__loop
    lda #$FF
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__argument:
    dec
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__control_code:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$02
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$03
    beq ScummV5_C17_CopyInlineName__no_arguments
    cmp #$08
    beq ScummV5_C17_CopyInlineName__no_arguments
    lda #$02
    bra ScummV5_C17_CopyInlineName__set_arguments
ScummV5_C17_CopyInlineName__no_arguments:
    .a8
    lda #$00
ScummV5_C17_CopyInlineName__set_arguments:
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyInlineName__loop
ScummV5_C17_CopyInlineName__done:
    jsr ScummV5_C17_SetNameLength
    clc
    rts

; A contains a canonical string resource id. Missing/out-of-u8 resources nuke
; the verb name; present resources are copied through their encoded terminator.
ScummV5_C17_CopyStringName:
    rep #$30
    .a16
    .i16
    cmp #$0100
    bcc ScummV5_C17_CopyStringName__id_ok
    jmp ScummV5_C17_CopyStringName__absent
ScummV5_C17_CopyStringName__id_ok:
    .a16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_C17_CopyStringName__present
    jmp ScummV5_C17_CopyStringName__absent8
ScummV5_C17_CopyStringName__present:
    sta.l SAME_SCUMM_C17_PARAM1
    txa
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C17_PARAM0
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
ScummV5_C17_CopyStringName__loop:
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    cmp.l SAME_SCUMM_C17_PARAM1
    bcc ScummV5_C17_CopyStringName__within_resource
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyStringName__within_resource:
    .a8
    cmp #SAME_SCUMM_C17_NAME_MAX
    bcc ScummV5_C17_CopyStringName__within_name
    jmp ScummV5_C17_NameError
ScummV5_C17_CopyStringName__within_name:
    rep #$30
    .a16
    .i16
    and #$00FF
    clc
    adc.l SAME_SCUMM_C17_PARAM0
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    jsr ScummV5_C17_StoreNameByte
    lda.l SAME_SCUMM_C17_CONTROL_ARGS
    beq ScummV5_C17_CopyStringName__ordinary
    cmp #$FF
    beq ScummV5_C17_CopyStringName__control_code
    bra ScummV5_C17_CopyStringName__argument
ScummV5_C17_CopyStringName__ordinary:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C17_CopyStringName__done
    cmp #$FF
    bne ScummV5_C17_CopyStringName__loop
    lda #$FF
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__argument:
    dec
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__control_code:
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$02
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$03
    beq ScummV5_C17_CopyStringName__no_arguments
    cmp #$08
    beq ScummV5_C17_CopyStringName__no_arguments
    lda #$02
    bra ScummV5_C17_CopyStringName__set_arguments
ScummV5_C17_CopyStringName__no_arguments:
    .a8
    lda #$00
ScummV5_C17_CopyStringName__set_arguments:
    sta.l SAME_SCUMM_C17_CONTROL_ARGS
    bra ScummV5_C17_CopyStringName__loop
ScummV5_C17_CopyStringName__done:
    jsr ScummV5_C17_SetNameLength
    clc
    rts
ScummV5_C17_CopyStringName__absent8:
    rep #$20
    .a16
ScummV5_C17_CopyStringName__absent:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    clc
    rts

; Store A into the current record name and advance the bounded byte cursor.
ScummV5_C17_StoreNameByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C17_NAME_INDEX
    and #$00FF
    clc
    adc #SAME_SCUMM_C17_V_NAME
    adc.l SAME_SCUMM_C17_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C17_VERBS,x
    lda.l SAME_SCUMM_C17_NAME_INDEX
    inc
    sta.l SAME_SCUMM_C17_NAME_INDEX
    rts

ScummV5_C17_SetNameLength:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_NAME_INDEX
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_NAME_LENGTH,x
    rts

ScummV5_C17_NameError:
    sep #$20
    .a8
    lda #SCUMM_ERR_VERB_OPS
    jsr ScummV5_SetError
    sec
    rts

; Canonical v5 $AC expression. The bytecode is reverse-Polish and uses a
; shared 256-entry signed 32-bit stack; only the final destination write
; narrows back to the v5 variable width.
ScummV5_Op_Expression:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Expression__destination_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__destination_ok:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_C18_DESTINATION
    lda #$0000
    sta.l SAME_SCUMM_C18_SP
ScummV5_Op_Expression__loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Expression__token_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__token_ok:
    .a8
    cmp #$FF
    bne ScummV5_Op_Expression__token_present
    jmp ScummV5_Op_Expression__finish
ScummV5_Op_Expression__token_present:
    .a8
    sta.l SAME_SCUMM_C18_TOKEN
    and #$1F
    cmp #$01
    bne ScummV5_Op_Expression__check_add
    jmp ScummV5_Op_Expression__push
ScummV5_Op_Expression__check_add:
    .a8
    cmp #$02
    bne ScummV5_Op_Expression__check_subtract
    jmp ScummV5_Op_Expression__add
ScummV5_Op_Expression__check_subtract:
    .a8
    cmp #$03
    bne ScummV5_Op_Expression__check_multiply
    jmp ScummV5_Op_Expression__subtract
ScummV5_Op_Expression__check_multiply:
    .a8
    cmp #$04
    bne ScummV5_Op_Expression__check_divide
    jmp ScummV5_Op_Expression__multiply
ScummV5_Op_Expression__check_divide:
    .a8
    cmp #$05
    bne ScummV5_Op_Expression__check_normal
    jmp ScummV5_Op_Expression__divide
ScummV5_Op_Expression__check_normal:
    .a8
    cmp #$06
    bne ScummV5_Op_Expression__reserved
    jmp ScummV5_Op_Expression__normal
ScummV5_Op_Expression__reserved:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__push:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_TOKEN
    sta.l SAME_SCUMM_LAST_OPCODE
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Expression__push_ok
    jmp ScummV5_Op__error
ScummV5_Op_Expression__push_ok:
    jsr ScummV5_C18_PushWord
    bcc ScummV5_Op_Expression__push_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__push_done:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__add:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__add_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__add_ready:
    rep #$20
    .a16
    clc
    lda.l SAME_SCUMM_C18_LHS_LO
    adc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    adc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__subtract:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__subtract_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__subtract_ready:
    rep #$20
    .a16
    sec
    lda.l SAME_SCUMM_C18_LHS_LO
    sbc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    sbc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__multiply:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__multiply_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__multiply_ready:
    jsr ScummV5_C18_Multiply
    bra ScummV5_Op_Expression__push_result

ScummV5_Op_Expression__divide:
    jsr ScummV5_C18_PopOperands
    bcc ScummV5_Op_Expression__divide_ready
    jmp ScummV5_Op__error
ScummV5_Op_Expression__divide_ready:
    jsr ScummV5_C18_Divide
    bcc ScummV5_Op_Expression__push_result
    jmp ScummV5_Op__error

ScummV5_Op_Expression__push_result:
    jsr ScummV5_C18_PushResult
    bcc ScummV5_Op_Expression__result_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__result_done:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__normal:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Expression__normal_fetched
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_fetched:
    .a8
    sta.l SAME_SCUMM_LAST_OPCODE
    lda.l SAME_SCUMM_C18_NESTED
    cmp #$FF
    bne ScummV5_Op_Expression__normal_depth_ok
    jmp ScummV5_C18_Error
ScummV5_Op_Expression__normal_depth_ok:
    .a8
    inc
    sta.l SAME_SCUMM_C18_NESTED
    jsr ScummV5_DispatchCurrentOpcode
    bcc ScummV5_Op_Expression__normal_done
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_done:
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_Expression__normal_value
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_value:
    jsr ScummV5_C18_PushWord
    bcc ScummV5_Op_Expression__normal_pushed
    jmp ScummV5_Op__error
ScummV5_Op_Expression__normal_pushed:
    jmp ScummV5_Op_Expression__loop

ScummV5_Op_Expression__finish:
    jsr ScummV5_C18_PopResult
    bcc ScummV5_Op_Expression__finish_value
    jmp ScummV5_Op__error
ScummV5_Op_Expression__finish_value:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_DESTINATION
    sta.l SAME_SCUMM_RESULT_OFFSET
    lda.l SAME_SCUMM_C18_RESULT_LO
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

; Push signed A16 as a 32-bit expression value.
ScummV5_C18_PushWord:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_C18_RESULT_LO
    bmi ScummV5_C18_PushWord__negative
    lda #$0000
    bra ScummV5_C18_PushWord__high
ScummV5_C18_PushWord__negative:
    .a16
    lda #$FFFF
ScummV5_C18_PushWord__high:
    .a16
    sta.l SAME_SCUMM_C18_RESULT_HI
    jmp ScummV5_C18_PushResult

ScummV5_C18_PushResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C18_SP
    cmp #SAME_SCUMM_C18_STACK_SIZE
    bcc ScummV5_C18_PushResult__room
    jmp ScummV5_C18_Error
ScummV5_C18_PushResult__room:
    .a16
    tax
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_STACK,x
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_STACK+2,x
    txa
    clc
    adc #$0004
    sta.l SAME_SCUMM_C18_SP
    clc
    rts

ScummV5_C18_PopResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C18_SP
    cmp #$0004
    bcs ScummV5_C18_PopResult__present
    jmp ScummV5_C18_Error
ScummV5_C18_PopResult__present:
    .a16
    sec
    sbc #$0004
    sta.l SAME_SCUMM_C18_SP
    tax
    lda.l SAME_SCUMM_C18_STACK,x
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_STACK+2,x
    sta.l SAME_SCUMM_C18_RESULT_HI
    clc
    rts

ScummV5_C18_PopOperands:
    jsr ScummV5_C18_PopResult
    bcs ScummV5_C18_PopOperands__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_RHS_HI
    jsr ScummV5_C18_PopResult
    bcs ScummV5_C18_PopOperands__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    sta.l SAME_SCUMM_C18_LHS_HI
    clc
ScummV5_C18_PopOperands__done:
    rts

; Lower 32 bits of the canonical signed-int product (two's-complement shift/add).
ScummV5_C18_Multiply:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C18_RESULT_LO
    sta.l SAME_SCUMM_C18_RESULT_HI
    sep #$20
    .a8
    lda #$20
    sta.l SAME_SCUMM_C18_LOOP
ScummV5_C18_Multiply__loop:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    and #$0001
    beq ScummV5_C18_Multiply__shift
    clc
    lda.l SAME_SCUMM_C18_RESULT_LO
    adc.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_RESULT_HI
    adc.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
ScummV5_C18_Multiply__shift:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_HI
    lsr
    sta.l SAME_SCUMM_C18_RHS_HI
    lda.l SAME_SCUMM_C18_RHS_LO
    ror
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_LHS_LO
    asl
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    rol
    sta.l SAME_SCUMM_C18_LHS_HI
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_LOOP
    dec
    sta.l SAME_SCUMM_C18_LOOP
    bne ScummV5_C18_Multiply__loop
    rts

; Signed 32-bit quotient, truncating toward zero.
ScummV5_C18_Divide:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    ora.l SAME_SCUMM_C18_RHS_HI
    bne ScummV5_C18_Divide__nonzero
    sep #$20
    .a8
    lda #SCUMM_ERR_DIVIDE_ZERO
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C18_Divide__nonzero:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C18_SIGN
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_HI
    bpl ScummV5_C18_Divide__lhs_positive
    jsr ScummV5_C18_NegateLhs
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C18_SIGN
ScummV5_C18_Divide__lhs_positive:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_HI
    bpl ScummV5_C18_Divide__rhs_positive
    jsr ScummV5_C18_NegateRhs
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_SIGN
    eor #$01
    sta.l SAME_SCUMM_C18_SIGN
ScummV5_C18_Divide__rhs_positive:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    sep #$20
    .a8
    lda #$20
    sta.l SAME_SCUMM_C18_LOOP
ScummV5_C18_Divide__loop:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    asl
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    rol
    sta.l SAME_SCUMM_C18_LHS_HI
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    rol
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    rol
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    cmp.l SAME_SCUMM_C18_RHS_HI
    bcc ScummV5_C18_Divide__next
    bne ScummV5_C18_Divide__subtract
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    cmp.l SAME_SCUMM_C18_RHS_LO
    bcc ScummV5_C18_Divide__next
ScummV5_C18_Divide__subtract:
    .a16
    sec
    lda.l SAME_SCUMM_C18_REMAINDER_LO
    sbc.l SAME_SCUMM_C18_RHS_LO
    sta.l SAME_SCUMM_C18_REMAINDER_LO
    lda.l SAME_SCUMM_C18_REMAINDER_HI
    sbc.l SAME_SCUMM_C18_RHS_HI
    sta.l SAME_SCUMM_C18_REMAINDER_HI
    lda.l SAME_SCUMM_C18_LHS_LO
    inc
    sta.l SAME_SCUMM_C18_LHS_LO
ScummV5_C18_Divide__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C18_LOOP
    dec
    sta.l SAME_SCUMM_C18_LOOP
    bne ScummV5_C18_Divide__loop
    lda.l SAME_SCUMM_C18_SIGN
    beq ScummV5_C18_Divide__positive
    jsr ScummV5_C18_NegateLhs
ScummV5_C18_Divide__positive:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    sta.l SAME_SCUMM_C18_RESULT_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    sta.l SAME_SCUMM_C18_RESULT_HI
    clc
    rts

ScummV5_C18_NegateLhs:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_LHS_LO
    eor #$FFFF
    clc
    adc #$0001
    sta.l SAME_SCUMM_C18_LHS_LO
    lda.l SAME_SCUMM_C18_LHS_HI
    eor #$FFFF
    adc #$0000
    sta.l SAME_SCUMM_C18_LHS_HI
    rts

ScummV5_C18_NegateRhs:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C18_RHS_LO
    eor #$FFFF
    clc
    adc #$0001
    sta.l SAME_SCUMM_C18_RHS_LO
    lda.l SAME_SCUMM_C18_RHS_HI
    eor #$FFFF
    adc #$0000
    sta.l SAME_SCUMM_C18_RHS_HI
    rts

ScummV5_C18_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_EXPRESSION
    jsr ScummV5_SetError
    sec
    rts

ScummV5_C19_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C19_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C19_STACK_POINTER,x
    inx
    inx
    cpx #SAME_SCUMM_C19_STATE_SIZE
    bcc ScummV5_C19_ResetState__loop
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C19_SCRIPT_INDEX
    rts

ScummV5_Op_CutsceneDispatch:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$40
    beq ScummV5_Op_Cutscene
    cmp #$C0
    bne ScummV5_Op_CutsceneDispatch__override
    jmp ScummV5_Op_EndCutscene
ScummV5_Op_CutsceneDispatch__override:
    jmp ScummV5_Op_BeginOverride

ScummV5_Op_Cutscene:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C19_ARGUMENT0
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_ARG_COUNT
ScummV5_Op_Cutscene__next_argument:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Cutscene__selector_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__selector_ok:
    .a8
    cmp #$FF
    bne ScummV5_Op_Cutscene__not_end
    jmp ScummV5_Op_Cutscene__arguments_done
ScummV5_Op_Cutscene__not_end:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C19_SELECTOR
    lda.l SAME_SCUMM_C4_ARG_COUNT
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_Cutscene__argument_room
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__argument_room:
    sep #$20
    .a8
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_Cutscene__word_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__word_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$80
    beq ScummV5_Op_Cutscene__value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_Cutscene__variable_ok
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__variable_ok:
    .a16
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_Cutscene__value_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    bne ScummV5_Op_Cutscene__argument_counted
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C19_ARGUMENT0
ScummV5_Op_Cutscene__argument_counted:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    inc
    sta.l SAME_SCUMM_C4_ARG_COUNT
    jmp ScummV5_Op_Cutscene__next_argument
ScummV5_Op_Cutscene__arguments_done:
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    cmp #$04
    bcc ScummV5_Op_Cutscene__stack_room
    jmp ScummV5_C19_Error
ScummV5_Op_Cutscene__stack_room:
    inc
    sta.l SAME_SCUMM_C19_STACK_POINTER
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C19_ARGUMENT0
    sta.l SAME_SCUMM_C19_DATA,x
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    cmp #$FF
    bne ScummV5_Op_Cutscene__depth_room
    ; Legacy/reused slots use FF as an uninitialized marker.  Activation is
    ; the generic owner of this per-slot depth, so normalize it here rather
    ; than turning an otherwise valid cutscene into a VM error.
    lda #$00
ScummV5_Op_Cutscene__depth_room:
    inc
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C19_STACK_POINTER
    sta.l $7E5688
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_EndCutscene:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Lifecycle evidence: distinguish an endCutscene handoff from the later
    ; stop/retirement guard without changing VM state.
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l $7E5693
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    sta.l $7E5694
    lda.l SAME_SCUMM_C19_STACK_POINTER
    sta.l $7E5695
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E569B
    sep #$20
    .a8
    .endif
    lda.l SAME_SCUMM_C19_STACK_POINTER
    bne ScummV5_Op_EndCutscene__active
    jmp ScummV5_C19_Error
ScummV5_Op_EndCutscene__active:
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_EndCutscene__find_owner
    dec
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    txa
    sta.l SAME_SCUMM_C19_SELECTOR
    bra ScummV5_Op_EndCutscene__first_depth_done
ScummV5_Op_EndCutscene__find_owner:
    sep #$10
    .i8
    ldx #$00
ScummV5_Op_EndCutscene__find_owner_loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_EndCutscene__find_owner_next
    dec
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    bra ScummV5_Op_EndCutscene__first_depth_done
ScummV5_Op_EndCutscene__find_owner_next:
    sep #$10
    .i8
    inx
    cpx #$19
    bcc ScummV5_Op_EndCutscene__find_owner_loop
ScummV5_Op_EndCutscene__first_depth_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C19_OVERRIDE_PC,x
    beq ScummV5_Op_EndCutscene__override_done
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sep #$10
    .i8
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_EndCutscene__second_depth_done
    dec
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
ScummV5_Op_EndCutscene__second_depth_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_SELECTOR
    and #$00FF
    asl
    tax
ScummV5_Op_EndCutscene__override_done:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_VARIABLES+(5 * 2)
    lda.l SAME_SCUMM_C19_SELECTOR
    tax
    lda #$00
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
    lda.l SAME_SCUMM_C19_STACK_POINTER
    dec
    sta.l SAME_SCUMM_C19_STACK_POINTER
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    sta.l $7E5696
    lda.l SAME_SCUMM_C19_STACK_POINTER
    sta.l $7E5697
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E569D
    sep #$20
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_BeginOverride:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_BeginOverride__flag_ok
    jmp ScummV5_C19_Error
ScummV5_Op_BeginOverride__flag_ok:
    .a8
    sta.l SAME_SCUMM_C19_SELECTOR
ScummV5_Op_BeginOverride__active:
    .a8
    lda.l SAME_SCUMM_C19_SELECTOR
    beq ScummV5_Op_BeginOverride__clear
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_STACK_POINTER
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    tax
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_BeginOverride__error
    bra ScummV5_Op_BeginOverride__variable
ScummV5_Op_BeginOverride__clear:
    .a8
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C19_STACK_POINTER
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C19_OVERRIDE_PC,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    tax
    lda #$00
    sta.l SAME_SCUMM_C19_OVERRIDE_SLOT,x
ScummV5_Op_BeginOverride__variable:
    .a8
    lda #$00
    sta.l SAME_SCUMM_VARIABLES+(5 * 2)
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_BeginOverride__error:
    jmp ScummV5_C19_Error

ScummV5_C19_Error:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Fixture-only parser evidence: retain the exact cutscene operands and
    ; stack state that caused the guard, without touching VM state.
    lda.l SAME_SCUMM_C19_SELECTOR
    sta.l $7E5684
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l $7E5685
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_STACK_POINTER
    sta.l $7E5687
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l $7E5698
    tax
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    sta.l $7E5699
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l $7E569A
    .endif
    ; Preserve the first parser guard and live fetch identity for production
    ; diagnostics; callers still receive the canonical SCUMM error.
    lda #$C1
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_PROGRAM
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_OPCODE
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_GET_WALKBOX_NEXT_PC
    sep #$20
    lda #SCUMM_ERR_CUTSCENE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C20_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C20_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C20_COUNT,x
    inx
    inx
    cpx #SAME_SCUMM_C20_STATE_SIZE
    bcc ScummV5_C20_ResetState__loop
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C20_INITIALIZED
    rts

; Public SCUMM semantic sentence boundary.  Callers provide the decoded
; verb/object tuple in the API mailbox; this routine appends one ordinary C20
; sentence record and never selects or executes a script directly.
ScummV5_QueueSentence:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_INITIALIZED
    bne ScummV5_QueueSentence__ready
    jsr ScummV5_C20_ResetState
ScummV5_QueueSentence__ready:
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    cmp #SAME_SCUMM_C20_RECORD_COUNT
    bcs ScummV5_QueueSentence__full
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    ; X is the record-relative byte offset; the long base below is applied
    ; exactly once by each indexed store.
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_SENTENCE_API_VERB
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l $7E57A0
    .endif
    sta.l SAME_SCUMM_C20_RECORDS,x
    ; Retain the decoded verb in the ordinary global-variable namespace for
    ; generated sentence launchers which use a variable entry selector.
    sta.l SAME_SCUMM_M23B_VARIABLES+(16 * 2)
    sta.l SAME_SCUMM_VARIABLES+(15 * 2)
    lda #$00
    sta.l SAME_SCUMM_C20_RECORDS+1,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_SENTENCE_API_OBJECT1
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l $7E57A1
    .endif
    sta.l SAME_SCUMM_C20_RECORDS+2,x
    lda.l SAME_SCUMM_SENTENCE_API_OBJECT2
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l $7E57A3
    .endif
    sta.l SAME_SCUMM_C20_RECORDS+4,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    inc
    sta.l SAME_SCUMM_C20_COUNT
ScummV5_QueueSentence__full:
    plp
    rtl

; Bank-safe entry used by the controller fixture. It still enters the same
; production C20 producer as semantic mailbox callers; no record is built by
; the controller layer itself.
ScummV5_QueueSentence_FarEntry:
    jsr ScummV5_QueueSentence
    rtl

ScummV5_Op_DoSentence:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_INITIALIZED
    bne ScummV5_Op_DoSentence__ready
    jsr ScummV5_C20_ResetState
ScummV5_Op_DoSentence__ready:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_DoSentence__verb_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__verb_ok:
    .a8
    sta.l SAME_SCUMM_C20_VERB
    cmp #$FE
    bne ScummV5_Op_DoSentence__objects
    lda #$00
    sta.l SAME_SCUMM_C20_COUNT
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_DoSentence__objects:
    .a8
    lda #$40
    jsr ScummV5_C20_FetchWordParam
    bcc ScummV5_Op_DoSentence__object_a_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__object_a_ok:
    .a16
    sta.l SAME_SCUMM_C20_OBJECT_A
    sep #$20
    .a8
    lda #$20
    jsr ScummV5_C20_FetchWordParam
    bcc ScummV5_Op_DoSentence__object_b_ok
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__object_b_ok:
    .a16
    sta.l SAME_SCUMM_C20_OBJECT_B
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    cmp #SAME_SCUMM_C20_RECORD_COUNT
    bcc ScummV5_Op_DoSentence__room
    jmp ScummV5_C20_Error
ScummV5_Op_DoSentence__room:
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_VERB
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_VERB,x
    lda #$00
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C20_OBJECT_A
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_A,x
    lda.l SAME_SCUMM_C20_OBJECT_B
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_OBJECT_B,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C20_COUNT
    inc
    sta.l SAME_SCUMM_C20_COUNT
    jmp ScummV5_Engine_Frame__next

ScummV5_C20_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_LAST_OPCODE
    beq ScummV5_C20_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C20_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C20_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C20_FetchWordParam__done:
    rts

ScummV5_C20_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SENTENCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C21_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C21_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C21_INITIALIZED,x
    inx
    inx
    cpx #SAME_SCUMM_C21_STATE_SIZE
    bcc ScummV5_C21_ResetState__clear
    ; Object 100: movable target.
    lda #$0064
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID
    lda #$0008
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT
    lda #$0014
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X
    lda #$001E
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y
    ; Objects 101 and 102 overlap exactly before object 101 is drawn.
    lda #$0065
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_ID
    lda #$0028
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_X
    lda #$0030
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_HEIGHT
    lda #$0032
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WALK_X
    lda #$003C
    sta.l SAME_SCUMM_C21_RECORDS+$10+SAME_SCUMM_C21_R_WALK_Y
    lda #$0066
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_ID
    lda #$0028
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_X
    lda #$0030
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_Y
    lda #$0010
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WIDTH
    lda #$0018
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_HEIGHT
    lda #$0046
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WALK_X
    lda #$0050
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_WALK_Y
    sep #$20
    .a8
    lda #$07
    sta.l SAME_SCUMM_C21_RECORDS+$20+SAME_SCUMM_C21_R_STATE
    lda #$03
    sta.l SAME_SCUMM_C21_RECORD_COUNT
    lda #$01
    sta.l SAME_SCUMM_C21_INITIALIZED
    rts

ScummV5_Op_DrawObject:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_INITIALIZED
    bne ScummV5_Op_DrawObject__ready
    jsr ScummV5_C21_ResetState
ScummV5_Op_DrawObject__ready:
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_DrawObject__object_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__object_ok:
    .a16
    sta.l SAME_SCUMM_C21_OBJECT
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_DrawObject__selector_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__selector_ok:
    .a8
    sta.l SAME_SCUMM_C21_SELECTOR
    lda #$00
    sta.l SAME_SCUMM_C21_POSITIONED
    lda #$01
    sta.l SAME_SCUMM_C21_STATE
    lda.l SAME_SCUMM_C21_SELECTOR
    and #$1F
    cmp #$01
    beq ScummV5_Op_DrawObject__at
    cmp #$02
    beq ScummV5_Op_DrawObject__state
    cmp #$1F
    beq ScummV5_Op_DrawObject__lookup
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__at:
    .a8
    lda #$80
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__x_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__x_ok:
    .a16
    sta.l SAME_SCUMM_C21_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__y_ok
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__y_ok:
    .a16
    sta.l SAME_SCUMM_C21_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C21_POSITIONED
    bra ScummV5_Op_DrawObject__lookup
ScummV5_Op_DrawObject__state:
    .a8
    lda #$80
    jsr ScummV5_C21_FetchWordParam
    bcc ScummV5_Op_DrawObject__state_value
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__state_value:
    rep #$20
    .a16
    cmp #$0100
    bcc ScummV5_Op_DrawObject__state_range
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__state_range:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C21_STATE
ScummV5_Op_DrawObject__lookup:
    rep #$30
    .a16
    .i16
    ldx #$0000
ScummV5_Op_DrawObject__lookup_loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID,x
    cmp.l SAME_SCUMM_C21_OBJECT
    beq ScummV5_Op_DrawObject__found
    txa
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    tax
    cpx #(SAME_SCUMM_C21_MAX_RECORDS * SAME_SCUMM_C21_RECORD_STRIDE)
    bcc ScummV5_Op_DrawObject__lookup_loop
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_DrawObject__found:
    txa
    sta.l SAME_SCUMM_C21_TARGET_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_POSITIONED
    beq ScummV5_Op_DrawObject__queue
    rep #$20
    .a16
    lda.l SAME_SCUMM_C21_X
    asl
    asl
    asl
    sta.l SAME_SCUMM_C21_X
    sec
    sbc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X,x
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X,x
    lda.l SAME_SCUMM_C21_X
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    lda.l SAME_SCUMM_C21_Y
    asl
    asl
    asl
    sta.l SAME_SCUMM_C21_Y
    sec
    sbc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y,x
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y,x
    lda.l SAME_SCUMM_C21_Y
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
ScummV5_Op_DrawObject__queue:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_QUEUE_COUNT
    cmp #SAME_SCUMM_C21_MAX_QUEUE
    bcc ScummV5_Op_DrawObject__queue_space
    jmp ScummV5_C21_Error
ScummV5_Op_DrawObject__queue_space:
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C21_OBJECT
    sta.l SAME_SCUMM_C21_QUEUE,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_QUEUE_COUNT
    inc
    sta.l SAME_SCUMM_C21_QUEUE_COUNT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C21_TARGET_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    sta.l SAME_SCUMM_C21_RECT_X
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    sta.l SAME_SCUMM_C21_RECT_Y
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH,x
    sta.l SAME_SCUMM_C21_RECT_WIDTH
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT,x
    sta.l SAME_SCUMM_C21_RECT_HEIGHT
    ldx #$0000
ScummV5_Op_DrawObject__overlap_loop:
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    cmp.l SAME_SCUMM_C21_RECT_X
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    cmp.l SAME_SCUMM_C21_RECT_Y
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH,x
    cmp.l SAME_SCUMM_C21_RECT_WIDTH
    bne ScummV5_Op_DrawObject__overlap_next
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT,x
    cmp.l SAME_SCUMM_C21_RECT_HEIGHT
    bne ScummV5_Op_DrawObject__overlap_next
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_STATE,x
    rep #$30
    .a16
    .i16
ScummV5_Op_DrawObject__overlap_next:
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    tax
    cpx #(SAME_SCUMM_C21_MAX_RECORDS * SAME_SCUMM_C21_RECORD_STRIDE)
    bcc ScummV5_Op_DrawObject__overlap_loop
    lda.l SAME_SCUMM_C21_TARGET_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_STATE
    sta.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_STATE,x
    jmp ScummV5_Engine_Frame__next

ScummV5_C21_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C21_SELECTOR
    beq ScummV5_C21_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C21_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C21_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C21_FetchWordParam__done:
    rts

ScummV5_C21_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_DRAW_OBJECT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C22_ResetState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C22_INITIALIZED
    sta.l SAME_SCUMM_C22_TRANSITION_COUNT
    sta.l SAME_SCUMM_C22_NULL_SCENE
    lda #$44
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda #$03
    sta.l SAME_SCUMM_C22_OBJECT_COUNT
    lda #$02
    sta.l SAME_SCUMM_C22_QUEUE_COUNT
    lda #$01
    sta.l SAME_SCUMM_C22_INITIALIZED
    rts

.if SAME_BUILD_SCUMM_M23A
; The source-bound room builds keep the cold matrix handler in a far ROM bank.
; These two adapters preserve the established bank-0 interpreter fetch helpers.
ScummV5_Matrix_FarCall_FetchByte:
    jsr ScummV5_FetchByte
    rtl
ScummV5_Matrix_FarCall_FetchByteParam:
    jsr ScummV5_C10_FetchByteParam
    rtl
ScummV5_PutActor_FarCall_FetchWordParam:
    jsr ScummV5_C10_FetchWordParam
    rtl
ScummV5_LoadRoomWithEgo_FarCall_RequestRoom:
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_RequestRoom_FarEntry
    .else
    jsr ScummV5_M23A_RequestRoom
    .endif
    rtl
ScummV5_RequestRoom:
    ; A=u8 room ID; delegate to the established M23A request lifecycle.
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_RequestRoom_FarEntry
    .else
    jsr ScummV5_M23A_RequestRoom
    .endif
    rts
ScummV5_PutActor_FarCall_DefaultActor:
    jsr ScummV5_C14_DefaultActor
    rtl
ScummV5_GetActorFacing_FarCall_ReadResult:
    jsr ScummV5_ReadResultOffset
    rtl
ScummV5_GetActorFacing_FarCall_ReadValue:
    jsr ScummV5_ReadResultValue
    rtl
ScummV5_GetActorFacing_FarCall_WriteResult:
    jsr ScummV5_WriteResultValue
    rtl
ScummV5_Movement_FarCall_FetchVariableWord:
    jsr ScummV5_FetchWord
    bcs ScummV5_Movement_FarCall_FetchVariableWord__done
    jsr ScummV5_ReadVariableReference
ScummV5_Movement_FarCall_FetchVariableWord__done:
    rtl
ScummV5_Movement_FarCall_FetchVarOrDirectWord:
    jsr ScummV5_FetchVarOrDirectWord
    rtl
ScummV5_StartObject_FarCall_ReadVariable:
    jsr ScummV5_ReadVariableReference
    rtl
ScummV5_Camera_FarCall_StopNumber:
    jsr ScummV5_C4_StopNumber
    rtl
ScummV5_Camera_FarCall_ResolveLocal:
    jsr ScummV5_M23A_ResolveLocalScript
    rtl
ScummV5_Camera_FarCall_ResolveGlobal:
    jsr ScummV5_M23A_ResolveGlobalScript
    rtl
ScummV5_Camera_FarCall_RunNestedChild:
    jsr ScummV5_C4_RunNestedChild
    rtl
ScummV5_Camera_FarCall_SetError:
    jsr ScummV5_SetError
    rtl
ScummV5_Camera_FarCall_FetchWord:
    jsr ScummV5_FetchWord
    rtl
ScummV5_Camera_FarCall_ReadVariable:
    jsr ScummV5_ReadVariableReference
    rtl
ScummV5_Movement_FarCall_Multiply:
    jsr ScummV5_C18_Multiply
    rep #$30
    .a16
    .i16
    rtl
ScummV5_Movement_FarCall_Divide:
    jsr ScummV5_C18_Divide
    rep #$30
    .a16
    .i16
    rtl
.if SAME_BUILD_M24RB
; Cold authentic room lifecycle and M24R-B driver are emitted in ROM bank 9.
; These are ABI adapters for far code calling established bank-0 RTS helpers.
ScummV5_M24RB_FarCall_C25Flush:
    jsr ScummV5_C25_Flush
    rtl
ScummV5_M24RB_FarCall_ClearSfx:
    jsr ScummV5_M23C_ClearSfxActive
    rtl
ScummV5_M24RB_FarCall_ResolveLocal:
    jsr ScummV5_M23A_ResolveLocalScript
    rtl
ScummV5_M24RB_FarCall_StageEngine:
    jsr Same_Event_StageEngine
    rtl
ScummV5_M24RB_FarCall_EventPush:
    jsr Same_Event_Push
    rtl
ScummV5_M24RB_FarCall_SetError:
    jsr ScummV5_SetError
    rtl
ScummV5_M24RB_FarCall_ResetCutscene:
    jsr ScummV5_C19_ResetState
    rtl
ScummV5_M24RB_FarCall_ResetSentenceQueue:
    jsr ScummV5_C20_ResetState
    rtl
.if SAME_BUILD_SCUMM_M23B
ScummV5_M25A_FarCall_SaveCurrentSlot:
    jsr ScummV5_C4_SaveCurrentSlot
    rtl
ScummV5_M25A_FarCall_RunSelected:
    jsr ScummV5_Engine_RunSelected
    rtl
.if SAME_BUILD_SCUMM_M25A_VALIDATOR
ScummV5_M25A_FarCall_Trace:
    jsr ScummV5_M25A_Trace
    rtl
.endif
.endif
.else
; M23A lifecycle trace codes: 1 request, 2 validated, 3 old EXCD,
; 4 room-local retirement, 5 activate, 6 register EXCD, 7 register LSCR,
; 8 schedule ENCD, 9 begin ENCD, 10 finish ENCD.
ScummV5_M23A_Trace:
    sep #$20
    .a8
    sep #$10
    .i8
    pha
    lda.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    cmp #$0E
    bcs ScummV5_M23A_Trace__full
    tax
    pla
    sta.l SAME_SCUMM_M23A_LIFECYCLE,x
    txa
    inc
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    rep #$10
    .i16
    rts
ScummV5_M23A_Trace__full:
    .a8
    .i8
    pla
    rep #$10
    .i16
    rts

.if SAME_BUILD_SCUMM_M23C
.if !SAME_BUILD_M24RB
; Bounded profile driver: once the authentic room-49 flush has made its music
; audibly owned, retain thirty playing frames and request the generated target
; room through the normal asynchronous resource/lifecycle path.
ScummV5_M23C_Driver:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23C_PHASE
    cmp #$01
    beq ScummV5_M23C_Driver__wait_music
    .if SAME_BUILD_M24RB
    cmp #$04
    beq ScummV5_M24RB_Driver__wait_marker
    cmp #$05
    bne ScummV5_M23C_Driver__not_m24rb_wait_room
    jmp ScummV5_M24RB_Driver__wait_room_phase
ScummV5_M23C_Driver__not_m24rb_wait_room:
    .a8
    cmp #$07
    bne ScummV5_M23C_Driver__not_m24rb_frame_end
    jmp ScummV5_M24RB_Driver__frame_end
ScummV5_M23C_Driver__not_m24rb_frame_end:
    .a8
    cmp #$08
    bne ScummV5_M23C_Driver__not_m24rb_wait_fade
    jmp ScummV5_M24RB_Driver__wait_fade
ScummV5_M23C_Driver__not_m24rb_wait_fade:
    .endif
    clc
    rts
ScummV5_M23C_Driver__wait_music:
    .a8
    lda.l SAME_TAD_STATE
    cmp #SAME_TAD_STATE_PLAYING
    bne ScummV5_M23C_Driver__done
    lda.l SAME_TAD_READY
    beq ScummV5_M23C_Driver__done
    lda.l SAME_SCUMM_M23C_READY_WAIT
    inc
    sta.l SAME_SCUMM_M23C_READY_WAIT
    cmp #$1E
    bcc ScummV5_M23C_Driver__done
    .if SAME_BUILD_M24RB
    jsr ScummV5_M24RB_ScheduleLocal
    bcs ScummV5_M23C_Driver__done
    lda #$04
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    clc
    rts
    .else
    lda #$02
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23C_TRANSITION_REQUESTED
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    lda #SCUMM_M23C_TARGET_ROOM
    jsr ScummV5_M23A_RequestRoom
    rts
    .endif
ScummV5_M23C_Driver__done:
    clc
    rts

.if SAME_BUILD_M24RB
ScummV5_M24RB_Driver__wait_marker:
    .a8
    ; Authentic LSCR commands are drained at the engine frame boundary, not
    ; by adding a synthetic soundKludge[-1] instruction.
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    beq ScummV5_M24RB_Driver__marker_poll
    lda #$01
    sta.l SAME_M24RB_FRAME_END_ACTIVE
    jsr ScummV5_C25_Flush
    lda.l SAME_M24RB_FRAME_END_FLUSHES
    inc
    sta.l SAME_M24RB_FRAME_END_FLUSHES
ScummV5_M24RB_Driver__marker_poll:
    .a8
    lda APUIO1
    cmp #$88
    bne ScummV5_M23C_Driver__done
    lda.l SAME_M24RB_MARKER_COUNT
    bne ScummV5_M23C_Driver__done
    inc
    sta.l SAME_M24RB_MARKER_COUNT
    lda #$02
    sta.l SAME_M24RB_LOGICAL82_STATE
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    clc
    adc #SAME_M24RB_PHASE_DELAY
    sta.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    lda #$05
    sta.l SAME_SCUMM_M23C_PHASE
    clc
    rts
ScummV5_M24RB_Driver__wait_room_phase:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    cmp.l SAME_M24RA_TARGET_FRAME
    sep #$20
    .a8
    bcc ScummV5_M23C_Driver__done
    lda #$02
    sta.l SAME_SCUMM_M23C_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23C_TRANSITION_REQUESTED
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    sta.l SAME_SCUMM_M23A_LIFECYCLE_COUNT
    lda #SCUMM_M23C_TARGET_ROOM
    jsr ScummV5_M23A_RequestRoom
    rts
ScummV5_M24RB_Driver__frame_end:
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    bne ScummV5_M24RB_Driver__frame_end_pending
    jmp ScummV5_M23C_Driver__done
ScummV5_M24RB_Driver__frame_end_pending:
    .a8
    lda #$01
    sta.l SAME_M24RB_FRAME_END_ACTIVE
    jsr ScummV5_C25_Flush
    lda.l SAME_M24RB_FRAME_END_FLUSHES
    inc
    sta.l SAME_M24RB_FRAME_END_FLUSHES
    lda #$08
    sta.l SAME_SCUMM_M23C_PHASE
    clc
    rts
ScummV5_M24RB_Driver__wait_fade:
    .a8
    lda.l SAME_M24RA_COMPLETE_FRAME
    bne ScummV5_M24RB_Driver__fade_complete
    jmp ScummV5_M23C_Driver__done
ScummV5_M24RB_Driver__fade_complete:
    lda.l SAME_M24RB_FADE_COMPLETE_COUNT
    beq ScummV5_M24RB_Driver__fade_not_recorded
    jmp ScummV5_M23C_Driver__done
ScummV5_M24RB_Driver__fade_not_recorded:
    .a8
    inc
    sta.l SAME_M24RB_FADE_COMPLETE_COUNT
    lda #$04
    sta.l SAME_M24RB_LOGICAL82_STATE
    lda #SAME_M24RB_LAYER_SOUND
    jsr ScummV5_M23C_ClearSfxActive
    clc
    rts

ScummV5_M24RB_ScheduleLocal:
    sep #$20
    .a8
    .i16
    lda #SAME_M24RB_LOCAL_SCRIPT
    jsr ScummV5_M23A_ResolveLocalScript
    bcc ScummV5_M24RB_ScheduleLocal__error
    sta.l SAME_SCUMM_FETCH_BYTE
    ldx #$0001
ScummV5_M24RB_ScheduleLocal__scan:
    sep #$20
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_M24RB_ScheduleLocal__found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_M24RB_ScheduleLocal__found
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M24RB_ScheduleLocal__scan
    bra ScummV5_M24RB_ScheduleLocal__error
ScummV5_M24RB_ScheduleLocal__found:
    sep #$20
    .a8
    .i16
    txa
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #SAME_M24RB_LOCAL_SCRIPT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    phx
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_SCENARIO_START_WRITTEN
    plx
    .endif
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_M24RB_LSCR_SCHEDULED
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    sep #$20
    .a8
    clc
    rts
ScummV5_M24RB_ScheduleLocal__error:
    sec
    rts
.endif
.endif
.endif

; Input A=logical room. Acquisition is asynchronous through SAME Storage READ;
; only the storage service validates profile-owned generated data.
ScummV5_M23A_RequestRoom:
    sep #$20
    .a8
    sta.l $7E5452
    lda.l $7E5450
    inc
    sta.l $7E5450
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    sta.l $7E5453
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l $7E5454
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E5455
    sep #$20
    .a8
    lda.l $7E5452
    sta.l SAME_SCUMM_M23A_PENDING_ROOM
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_M23A_RETURN_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_M23A_RETURN_PC
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_M23A_PHASE
    lda.l SAME_SCUMM_M23A_REQUEST_COUNT
    inc
    sta.l SAME_SCUMM_M23A_REQUEST_COUNT
    lda #$01
    jsr ScummV5_M23A_Trace
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_STORAGE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_STORAGE_OP_READ
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_PROFILE
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bcc ScummV5_M23A_RequestRoom__queued
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    lda #SCUMM_ERR_SERVICE
    .if SAME_BUILD_SCUMM_M23B
    pha
    lda #$02
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    pla
    .endif
    jsr ScummV5_SetError
    sec
    rts
ScummV5_M23A_RequestRoom__queued:
    sep #$20
    .a8
    clc
    rts

; Called only after the storage backend has completed all record checks.
ScummV5_M23A_ResourceReady:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$FF
    bne ScummV5_M23A_ResourceReady__check_exit
    jmp ScummV5_M23A_CommitRoom
ScummV5_M23A_ResourceReady__check_exit:
    .a8
    lda.l SAME_SCUMM_M23A_EXIT_PROGRAM
    bne ScummV5_M23A_ResourceReady__run_exit
    jmp ScummV5_M23A_CommitRoom
ScummV5_M23A_ResourceReady__run_exit:
    .a8
    jsr ScummV5_M23A_BeginRoomScript
    lda #$01
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$02
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    lda.l SAME_SCUMM_M23A_EXIT_COUNT
    inc
    sta.l SAME_SCUMM_M23A_EXIT_COUNT
    lda #$03
    jsr ScummV5_M23A_Trace
    clc
    rts

; Input A=compiled script descriptor program. Slot zero is the scheduler-owned
; ENCD/EXCD frame; room-local allocations remain in slots 1..24.
ScummV5_M23A_BeginRoomScript:
    sep #$20
    .a8
    sta.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    lda #$00
    sta.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    ; A room entry runs as the outer engine frame. Nested startScript calls
    ; save this zero and select return mode one only around their child call.
    lda #$00
    sta.l SAME_SCUMM_RETURN_MODE
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_DELAY
    sta.l SAME_SCUMM_C4_SLOT_PC
    sta.l SAME_SCUMM_C4_SLOT_DELAY
    sep #$20
    .a8
    rts

ScummV5_M23A_EndRoomScript:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS
    sta.l SAME_SCUMM_C4_SLOT_NUMBER
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_M23A_EndRoomScript__done
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_M23A_EndRoomScript__done:
    rts

ScummV5_M23A_CommitRoom:
    sep #$20
    .a8
    ; A room change is a canonical cutscene-abort boundary.  Do not carry the
    ; previous room's global C19 stack or per-slot override depths into the
    ; continuing scheduler context; the new room owns a fresh lifecycle.
    jsr ScummV5_C19_ResetState
    rep #$10
    .i16
    ldx #$0001
ScummV5_M23A_CommitRoom__retire:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_WHERE,x
    cmp #SCUMM_WIO_ROOM
    beq ScummV5_M23A_CommitRoom__retire_owned
    cmp #SCUMM_WIO_LOCAL
    bne ScummV5_M23A_CommitRoom__retire_next
ScummV5_M23A_CommitRoom__retire_owned:
    .a8
    .i16
    lda.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    beq ScummV5_M23A_CommitRoom__retire_next
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    bne ScummV5_M23A_CommitRoom__retire_next
    lda #$00
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_M23A_CommitRoom__retired
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_M23A_CommitRoom__retired:
    lda.l SAME_SCUMM_M23A_RETIRE_COUNT
    inc
    sta.l SAME_SCUMM_M23A_RETIRE_COUNT
ScummV5_M23A_CommitRoom__retire_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_M23A_CommitRoom__retire
    lda #$04
    jsr ScummV5_M23A_Trace
    lda.l SAME_SCUMM_M23A_PENDING_RECORD
    sta.l SAME_SCUMM_M23A_ACTIVE_RECORD
    jsl ScummV5_Matrix_LoadActiveRoom_Far
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Room installation is the fixture's engine-owned resource boundary.  The
    ; source DOBJ class table is rehydrated here after any cold fixture-state
    ; reset, while subsequent setClass mutations remain runtime-owned.
    jsl ScummV5_ObjectClass_LoadInitial_Far
    .endif
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    tax
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    sta.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda #$05
    jsr ScummV5_M23A_Trace
    sep #$10
    .i8
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    tax
    lda.l ScummV5_M23A_RoomScriptCounts,x
    sta.l SAME_SCUMM_M23A_DESCRIPTOR_COUNT
    sta.l SAME_SCUMM_M23A_REGISTER_COUNT
    lda.l ScummV5_M23A_RoomLocalCounts,x
    sta.l SAME_SCUMM_M23A_LOCAL_COUNT
    lda.l ScummV5_M23A_RoomEntryPrograms,x
    sta.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    lda.l ScummV5_M23A_RoomExitPrograms,x
    sta.l SAME_SCUMM_M23A_EXIT_PROGRAM
    sta.l SAME_SCUMM_FETCH_BYTE
    txa
    rep #$20
    .a16
    and #$00FF
    asl
    tax
    lda.l ScummV5_M23A_RoomDescriptorChecksums,x
    sta.l SAME_SCUMM_M23A_DESCRIPTOR_CHECKSUM
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_M23A_CommitRoom__no_exit_registered
    lda #$06
    jsr ScummV5_M23A_Trace
ScummV5_M23A_CommitRoom__no_exit_registered:
    .a8
    lda.l SAME_SCUMM_M23A_LOCAL_COUNT
    beq ScummV5_M23A_CommitRoom__no_locals_registered
    lda #$07
    jsr ScummV5_M23A_Trace
ScummV5_M23A_CommitRoom__no_locals_registered:
    .a8
    lda #$08
    jsr ScummV5_M23A_Trace
    lda.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l ScummV5_M23A_RoomFlags,x
    and #$01
    beq ScummV5_M23A_CommitRoom__execute
    lda #$03
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    clc
    rts
ScummV5_M23A_CommitRoom__execute:
    .a8
    lda #$02
    sta.l SAME_SCUMM_M23A_PHASE
    lda #$01
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    lda.l SAME_SCUMM_M23A_ENTRY_COUNT
    inc
    sta.l SAME_SCUMM_M23A_ENTRY_COUNT
    lda #$09
    jsr ScummV5_M23A_Trace
    lda.l SAME_SCUMM_M23A_ENTRY_PROGRAM
    jsr ScummV5_M23A_BeginRoomScript
    .if SAME_BUILD_SCUMM_ROOM_VISUAL
    jsl ScummV5_RoomVisual_Installed_Far
    .endif
    .if SAME_BUILD_SCUMM_CONTROLLER_FIXTURE
    ; The resource commit is the first unambiguous point at which the
    ; source-backed room-68 root is installed.  Hand off the labeled scene
    ; through the ordinary request API from here, before any presentation or
    ; input code can observe a half-installed room.
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    cmp #$04
    bne ScummV5_M23A_CommitRoom__controller_done
    lda.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    bne ScummV5_M23A_CommitRoom__controller_done
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_SCENARIO_REQUESTED
    lda #$2A
    jsr ScummV5_RequestRoom
ScummV5_M23A_CommitRoom__controller_done:
    sep #$20
    .a8
    .endif
    clc
    rts
.endif
.endif

ScummV5_Op_LoadRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C22_INITIALIZED
    bne ScummV5_Op_LoadRoom__ready
    jsr ScummV5_C22_ResetState
ScummV5_Op_LoadRoom__ready:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_LoadRoom__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_LoadRoom__operand_ok:
    .a8
    bpl ScummV5_Op_LoadRoom__resolved
    and #$7F
    rep #$10
    .i16
    tax
    lda.l SAME_SCUMM_C12_MAPPER,x
ScummV5_Op_LoadRoom__resolved:
    .a8
    .if SAME_BUILD_SCUMM_M23A
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_RequestRoom_FarEntry
    .else
    jsr ScummV5_M23A_RequestRoom
    .endif
    bcc ScummV5_Op_LoadRoom__m23a_queued
    jmp ScummV5_Op__error
ScummV5_Op_LoadRoom__m23a_queued:
    .a8
    jmp ScummV5_Engine_Frame__complete_success
    .endif
    sta.l SAME_SCUMM_C22_CURRENT_ROOM
    lda.l SAME_SCUMM_C22_TRANSITION_COUNT
    inc
    sta.l SAME_SCUMM_C22_TRANSITION_COUNT
    lda #$00
    sta.l SAME_SCUMM_C22_OBJECT_COUNT
    sta.l SAME_SCUMM_C22_QUEUE_COUNT
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_Op_LoadRoom__null
    lda #$00
    sta.l SAME_SCUMM_C22_NULL_SCENE
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_LoadRoom__null:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C22_NULL_SCENE
    jmp ScummV5_Engine_Frame__next

ScummV5_C23_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C23_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C23_INITIALIZED,x
    inx
    inx
    cpx #SAME_SCUMM_C23_STATE_SIZE
    bcc ScummV5_C23_ResetState__clear
    ldx #$0000
ScummV5_C23_ResetState__slot:
    .a16
    .i16
    lda #$0002
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    lda #$0005
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    lda #$013F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    lda #$0000
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sep #$20
    .a8
    lda #$0F
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    rep #$20
    .a16
    txa
    clc
    adc #SAME_SCUMM_C23_SLOT_STRIDE
    tax
    cpx #(4 * SAME_SCUMM_C23_SLOT_STRIDE)
    bcc ScummV5_C23_ResetState__slot
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C23_INITIALIZED
    rts

ScummV5_Op_Print:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_INITIALIZED
    bne ScummV5_Op_Print__ready
    jsr ScummV5_C23_ResetState
ScummV5_Op_Print__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$D8
    bne ScummV5_Op_Print__fetch_actor
    lda #$01
    bra ScummV5_Op_Print__actor
ScummV5_Op_Print__fetch_actor:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_Print__actor
    jmp ScummV5_Op__error
ScummV5_Op_Print__actor:
    .a8
    sta.l SAME_SCUMM_C23_ACTOR
    ldx #$0000
    cmp #$FC
    bne ScummV5_Op_Print__slot2
    ldx #$0021
    lda #$03
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot2:
    .a8
    cmp #$FD
    bne ScummV5_Op_Print__slot1
    ldx #$0016
    lda #$02
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot1:
    .a8
    cmp #$FE
    bne ScummV5_Op_Print__slot0
    ldx #$000B
    lda #$01
    bra ScummV5_Op_Print__slot_ready
ScummV5_Op_Print__slot0:
    .a8
    lda #$00
ScummV5_Op_Print__slot_ready:
    sta.l SAME_SCUMM_C23_LAST_SLOT
    rep #$20
    .a16
    txa
    sta.l SAME_SCUMM_C23_SLOT_OFFSET
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_HEIGHT
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_CHARSET
    lda.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_FLAGS,x
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
ScummV5_Op_Print__selector:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Print__selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__selector_ok:
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    cmp #$FF
    bne ScummV5_Op_Print__not_default
    jmp ScummV5_Op_Print__save_default
ScummV5_Op_Print__not_default:
    .a8
    and #$0F
    beq ScummV5_Op_Print__at
    cmp #$01
    beq ScummV5_Op_Print__color
    cmp #$02
    beq ScummV5_Op_Print__clipped
    cmp #$03
    bne ScummV5_Op_Print__not_erase
    jmp ScummV5_Op_Print__unsupported_pair
ScummV5_Op_Print__not_erase:
    .a8
    cmp #$04
    beq ScummV5_Op_Print__center
    cmp #$06
    bne ScummV5_Op_Print__not_left
    jmp ScummV5_Op_Print__left
ScummV5_Op_Print__not_left:
    .a8
    cmp #$07
    bne ScummV5_Op_Print__not_overhead
    jmp ScummV5_Op_Print__overhead
ScummV5_Op_Print__not_overhead:
    .a8
    cmp #$08
    bne ScummV5_Op_Print__not_voice
    jmp ScummV5_Op_Print__unsupported_pair
ScummV5_Op_Print__not_voice:
    .a8
    cmp #$0F
    bne ScummV5_Op_Print__unknown
    jmp ScummV5_Op_Print__text
ScummV5_Op_Print__unknown:
    .a8
    jmp ScummV5_C23_Error
ScummV5_Op_Print__at:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__at_x
    jmp ScummV5_Op__error
ScummV5_Op_Print__at_x:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__at_y
    jmp ScummV5_Op__error
ScummV5_Op_Print__at_y:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FD
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__color:
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_Print__color_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__color_ok:
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__clipped:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcc ScummV5_Op_Print__clipped_ok
    jmp ScummV5_Op__error
ScummV5_Op_Print__clipped_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    sep #$20
    .a8
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__center:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FD
    ora #$01
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__left:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    and #$FC
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__overhead:
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    ora #$02
    sta.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    jmp ScummV5_Op_Print__selector
ScummV5_Op_Print__unsupported_pair:
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcs ScummV5_Op_Print__unsupported_error
    lda #$40
    jsr ScummV5_C23_FetchWordParam
ScummV5_Op_Print__unsupported_error:
    jmp ScummV5_C23_Error
ScummV5_Op_Print__save_default:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C23_SLOT_OFFSET
    tax
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_X
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_X,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_Y
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_Y,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_RIGHT
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_RIGHT,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_HEIGHT
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_HEIGHT,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_COLOR
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_COLOR,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_CHARSET
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_CHARSET,x
    lda.l SAME_SCUMM_C23_WORK+SAME_SCUMM_C23_P_FLAGS
    sta.l SAME_SCUMM_C23_SLOTS+SAME_SCUMM_C23_P_FLAGS,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Print__text:
    .a8
    lda.l SAME_SCUMM_C23_ACTOR
    sta.l SAME_SCUMM_C23_LAST_ACTOR
    lda.l SAME_SCUMM_C23_MESSAGE_COUNT
    inc
    sta.l SAME_SCUMM_C23_MESSAGE_COUNT
    lda #$00
    sta.l SAME_SCUMM_C23_RAW_INDEX
ScummV5_Op_Print__text_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Print__text_first_fetched
    jmp ScummV5_Op_Print__text_error
ScummV5_Op_Print__text_first_fetched:
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_Talk_StoreTextByte_Far
    .else
    jsr ScummV5_C23_StoreTextByte
    .endif
    bcc ScummV5_Op_Print__text_first_stored
    jmp ScummV5_C23_Error
ScummV5_Op_Print__text_first_stored:
    .a8
    cmp #$00
    beq ScummV5_Op_Print__text_done
    cmp #$FF
    bne ScummV5_Op_Print__text_loop
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_Print__text_control_fetched
    jmp ScummV5_Op_Print__text_error
ScummV5_Op_Print__text_control_fetched:
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_Talk_StoreTextByte_Far
    .else
    jsr ScummV5_C23_StoreTextByte
    .endif
    bcc ScummV5_Op_Print__text_control_stored
    jmp ScummV5_C23_Error
ScummV5_Op_Print__text_control_stored:
    .a8
    cmp #$01
    beq ScummV5_Op_Print__text_loop
    cmp #$02
    beq ScummV5_Op_Print__text_loop
    cmp #$03
    beq ScummV5_Op_Print__text_loop
    cmp #$08
    beq ScummV5_Op_Print__text_loop
    ldy #$0002
ScummV5_Op_Print__text_args:
    .a8
    .i16
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_Print__text_error
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_Talk_StoreTextByte_Far
    .else
    jsr ScummV5_C23_StoreTextByte
    .endif
    bcc ScummV5_Op_Print__text_control_arg_ok
    jmp ScummV5_C23_Error
ScummV5_Op_Print__text_control_arg_ok:
    dey
    bne ScummV5_Op_Print__text_args
    bra ScummV5_Op_Print__text_loop
ScummV5_Op_Print__text_done:
    .a8
    lda.l SAME_SCUMM_C23_RAW_INDEX
    sta.l SAME_SCUMM_C23_LAST_LENGTH
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_C23_LAST_SLOT
    bne ScummV5_Op_Print__text_no_talk
    jsl ScummV5_Talk_Begin_Far
    bcc ScummV5_Op_Print__talk_started
    ; Unsupported encoded talk controls are a terminal script-visible
    ; blocker, not a malformed machine stack.  Talk_Begin has already marked
    ; this slot ERROR and preserved the exact post-string PC; return through
    ; the ordinary nested-script boundary so later engine phases can run.
    lda.l SAME_SCUMM_ERROR
    cmp #SCUMM_ERR_STRING
    beq ScummV5_Op_Print__text_blocked
    bra ScummV5_Op_Print__text_error
ScummV5_Op_Print__text_blocked:
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_Print__talk_started:
    ; Actor talk establishes a semantic frame boundary.  The following
    ; waitForMessage remains at the already advanced PC and executes on the
    ; next scheduler pass; frame-end can publish the queued visual request
    ; without running unrelated script work ahead of it.
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jsr ScummV5_C4_SaveCurrentSlot
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_FRAME_ENTRY_STACK
    tax
    txs
    plp
    clc
    rts
ScummV5_Op_Print__text_no_talk:
    .endif
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Print__text_error:
    jmp ScummV5_Op__error

; v5 $54/$D4 is setObjectName, not print. The operand is a direct/variable
; object word followed by an inline encoded string. Retain that authored
; encoded name in a bounded runtime table so target-neutral clients can read
; the same object identity without inventing a room-specific label table.
ScummV5_Op_SetObjectName:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcs ScummV5_Op_SetObjectName__error
    rep #$20
    .a16
    sta.l SAME_SCUMM_OBJECT_NAME_OBJECT
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_OBJECT_NAME_INDEX
ScummV5_Op_SetObjectName__string:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_SetObjectName__error
    jsr ScummV5_StoreObjectNameByte
    lda.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_Op_SetObjectName__done
    cmp #$FF
    bne ScummV5_Op_SetObjectName__string
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_SetObjectName__error
    jsr ScummV5_StoreObjectNameByte
    lda.l SAME_SCUMM_FETCH_BYTE
    cmp #$01
    beq ScummV5_Op_SetObjectName__string
    cmp #$02
    beq ScummV5_Op_SetObjectName__string
    cmp #$03
    beq ScummV5_Op_SetObjectName__string
    cmp #$08
    beq ScummV5_Op_SetObjectName__string
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_SetObjectName__error
    jsr ScummV5_StoreObjectNameByte
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_SetObjectName__error
    jsr ScummV5_StoreObjectNameByte
    bra ScummV5_Op_SetObjectName__string
ScummV5_Op_SetObjectName__done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OBJECT_NAME_OBJECT
    and #$07FF
    cmp #SAME_SCUMM_OBJECT_NAME_COUNT
    bcs ScummV5_Op_SetObjectName__done_no_cache
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    inc
    sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SetObjectName__done_no_cache:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SetObjectName__error:
    jmp ScummV5_Op__error

; Store one encoded byte in object_id * 32. The terminator is retained so
; clients can preserve canonical control bytes and use the same decoding path.
ScummV5_StoreObjectNameByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_OBJECT_NAME_OBJECT
    and #$07FF
    cmp #SAME_SCUMM_OBJECT_NAME_COUNT
    bcs ScummV5_StoreObjectNameByte__discard
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C17_PARAM0
    clc
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    rep #$20
    .a16
    and #$00FF
    adc.l SAME_SCUMM_C17_PARAM0
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_OBJECT_NAMES,x
ScummV5_StoreObjectNameByte__advance:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_NAME_INDEX
    cmp #$1F
    bcs ScummV5_StoreObjectNameByte__full
    inc
    sta.l SAME_SCUMM_OBJECT_NAME_INDEX
ScummV5_StoreObjectNameByte__full:
    rts
ScummV5_StoreObjectNameByte__discard:
    sep #$20
    .a8
    bra ScummV5_StoreObjectNameByte__advance

; Canonical v5 $29/$69/$A9/$E9 setOwnerOf.  Owners are mutable runtime
; object state, so queries use the WRAM table initialized from the cooked DOBJ
; owner data at engine boot.
ScummV5_Op_SetOwnerOf:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C23_SELECTOR
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcs ScummV5_Op_SetOwnerOf__error
    rep #$20
    .a16
    tax
    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcs ScummV5_Op_SetOwnerOf__error16
    phx
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_SetOwnerOf__owner_error
    sta.l SAME_SCUMM_OWNER_RESULT
    plx
    rep #$20
    .a16
    sep #$20
    .a8
    sta.l SAME_SCUMM_OBJECT_OWNERS,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SetOwnerOf__owner_error:
    plx
    jmp ScummV5_Op_SetOwnerOf__error
ScummV5_Op_SetOwnerOf__error16:
    sep #$20
    .a8
ScummV5_Op_SetOwnerOf__error:
    jmp ScummV5_Op__error

; Canonical v5 $25/$65/$A5/$E5 pickupObject.  The room operand is consumed
; even in the headless fixture; ownership/state are the semantic effects.
ScummV5_Op_PickupObject:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C23_SELECTOR
    lda #$80
    jsr ScummV5_C23_FetchWordParam
    bcs ScummV5_Op_PickupObject__error
    rep #$20
    .a16
    tax
    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcs ScummV5_Op_PickupObject__error16
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_PickupObject__error
    lda #$01
    sta.l SAME_SCUMM_OBJECT_OWNERS,x
    sta.l SAME_SCUMM_OBJECT_STATES,x
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_PickupObject__error16:
    sep #$20
    .a8
ScummV5_Op_PickupObject__error:
    jmp ScummV5_Op__error

; Canonical v5 $31/$B1 getInventoryCount.  Inventory ownership is the
; mutable object owner table; the result is the number of objects owned by the
; requested actor.
ScummV5_Op_GetInventoryCount:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_GetInventoryCount__error
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    beq ScummV5_Op_GetInventoryCount__actor_direct
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_GetInventoryCount__error
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_Op_GetInventoryCount__error
    bra ScummV5_Op_GetInventoryCount__actor_ready
ScummV5_Op_GetInventoryCount__actor_direct:
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_GetInventoryCount__error
ScummV5_Op_GetInventoryCount__actor_ready:
    sta.l SAME_SCUMM_MOVE_TEMP
    rep #$20
    .a16
    .i16
    ldy #$0000
    ldx #$0000
ScummV5_Op_GetInventoryCount__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_OWNERS,x
    cmp.l SAME_SCUMM_MOVE_TEMP
    bne ScummV5_Op_GetInventoryCount__next
    iny
ScummV5_Op_GetInventoryCount__next:
    rep #$20
    .a16
    .i16
    inx
    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcc ScummV5_Op_GetInventoryCount__loop
    tya
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_GetInventoryCount__error:
    jmp ScummV5_Op__error

; Canonical v5 $3D/$7D/$BD/$FD findInventory(owner,index).  Return the
; source-defined object ID at the requested inventory ordinal, or zero when
; no such entry exists.
ScummV5_Op_FindInventory:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_FindInventory__error
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    beq ScummV5_Op_FindInventory__owner_direct
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_FindInventory__error
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_Op_FindInventory__error
    bra ScummV5_Op_FindInventory__owner_ready
ScummV5_Op_FindInventory__owner_direct:
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_FindInventory__error
ScummV5_Op_FindInventory__owner_ready:
    sta.l SAME_SCUMM_MOVE_TEMP
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$40
    beq ScummV5_Op_FindInventory__index_direct
    jsr ScummV5_FetchWord
    bcs ScummV5_Op_FindInventory__error
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_Op_FindInventory__error
    bra ScummV5_Op_FindInventory__index_ready
ScummV5_Op_FindInventory__index_direct:
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_FindInventory__error
ScummV5_Op_FindInventory__index_ready:
    sta.l SAME_SCUMM_MOVE_TEMP2
    rep #$30
    .a16
    .i16
    ldx #$0000
    ldy #$0000
ScummV5_Op_FindInventory__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_OWNERS,x
    cmp.l SAME_SCUMM_MOVE_TEMP
    bne ScummV5_Op_FindInventory__next
    rep #$20
    .a16
    tya
    cmp.l SAME_SCUMM_MOVE_TEMP2
    beq ScummV5_Op_FindInventory__found
    iny
ScummV5_Op_FindInventory__next:
    rep #$20
    .a16
    .i16
    inx
    cpx #SCUMM_M23A_GLOBAL_OBJECT_COUNT
    bcc ScummV5_Op_FindInventory__loop
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FindInventory__found:
    txa
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FindInventory__error:
    jmp ScummV5_Op__error

ScummV5_C23_FetchWordParam:
    sep #$20
    .a8
    and.l SAME_SCUMM_C23_SELECTOR
    beq ScummV5_C23_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C23_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C23_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C23_FetchWordParam__done:
    rts

.if SAME_BUILD_SCUMM_M23A
.else
ScummV5_C23_StoreTextByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C23_SELECTOR
    lda.l SAME_SCUMM_C23_RAW_INDEX
    cmp #$10
    bcc ScummV5_C23_StoreTextByte__space
    sec
    rts
ScummV5_C23_StoreTextByte__space:
    .a8
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C23_SELECTOR
    sta.l SAME_SCUMM_C23_LAST_RAW,x
    lda.l SAME_SCUMM_C23_RAW_INDEX
    inc
    sta.l SAME_SCUMM_C23_RAW_INDEX
    lda.l SAME_SCUMM_C23_SELECTOR
    clc
    rts
.endif

ScummV5_C23_Error:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$D7
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_ActorOps:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_ActorOps__ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_ActorOps__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_ActorOps__actor_fetched
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_Op_ActorOps__actor_ok
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__actor_ok:
    sta.l SAME_SCUMM_C14_ACTOR
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_ActorOps__loop
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_ActorOps__loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_ActorOps__subop_fetched
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__subop_fetched:
    .a8
    cmp #$FF
    bne ScummV5_Op_ActorOps__subop_present
    jmp ScummV5_Op_ActorOps__done
ScummV5_Op_ActorOps__subop_present:
    .a8
    sta.l SAME_SCUMM_C14_SUBOP
    sta.l SAME_SCUMM_C7_SUBOP
    and #$1F
    cmp #$18
    bcc ScummV5_Op_ActorOps__subop_in_range
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__subop_in_range:
    .a8
    cmp #$0F
    bne ScummV5_Op_ActorOps__subop_valid
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__subop_valid:
    .a8
    ; Poppy's current location pass undercounts JMP (abs,x) by one byte even
    ; though the emitter writes the correct three-byte 65C816 instruction.
    ; Keep this explicit dispatch chain until that assembler defect is fixed;
    ; otherwise every following label (including the active-engine ABI) points
    ; one byte before its emitted code.
    cmp #$00
    bne ScummV5_Op_ActorOps__dispatch_01
    jmp ScummV5_Op_ActorOps__dummy
ScummV5_Op_ActorOps__dispatch_01:
    .a8
    cmp #$01
    bne ScummV5_Op_ActorOps__dispatch_02
    jmp ScummV5_Op_ActorOps__costume
ScummV5_Op_ActorOps__dispatch_02:
    .a8
    cmp #$02
    bne ScummV5_Op_ActorOps__dispatch_03
    jmp ScummV5_Op_ActorOps__speed
ScummV5_Op_ActorOps__dispatch_03:
    .a8
    cmp #$03
    bne ScummV5_Op_ActorOps__dispatch_04
    jmp ScummV5_Op_ActorOps__sound
ScummV5_Op_ActorOps__dispatch_04:
    .a8
    cmp #$04
    bne ScummV5_Op_ActorOps__dispatch_05
    jmp ScummV5_Op_ActorOps__walk
ScummV5_Op_ActorOps__dispatch_05:
    .a8
    cmp #$05
    bne ScummV5_Op_ActorOps__dispatch_06
    jmp ScummV5_Op_ActorOps__talk
ScummV5_Op_ActorOps__dispatch_06:
    .a8
    cmp #$06
    bne ScummV5_Op_ActorOps__dispatch_07
    jmp ScummV5_Op_ActorOps__stand
ScummV5_Op_ActorOps__dispatch_07:
    .a8
    cmp #$07
    bne ScummV5_Op_ActorOps__dispatch_08
    jmp ScummV5_Op_ActorOps__animation
ScummV5_Op_ActorOps__dispatch_08:
    .a8
    cmp #$08
    bne ScummV5_Op_ActorOps__dispatch_09
    jmp ScummV5_Op_ActorOps__default
ScummV5_Op_ActorOps__dispatch_09:
    .a8
    cmp #$09
    bne ScummV5_Op_ActorOps__dispatch_0a
    jmp ScummV5_Op_ActorOps__elevation
ScummV5_Op_ActorOps__dispatch_0a:
    .a8
    cmp #$0A
    bne ScummV5_Op_ActorOps__dispatch_0b
    jmp ScummV5_Op_ActorOps__anim_default
ScummV5_Op_ActorOps__dispatch_0b:
    .a8
    cmp #$0B
    bne ScummV5_Op_ActorOps__dispatch_0c
    jmp ScummV5_Op_ActorOps__palette
ScummV5_Op_ActorOps__dispatch_0c:
    .a8
    cmp #$0C
    bne ScummV5_Op_ActorOps__dispatch_0d
    jmp ScummV5_Op_ActorOps__talk_color
ScummV5_Op_ActorOps__dispatch_0d:
    .a8
    cmp #$0D
    bne ScummV5_Op_ActorOps__dispatch_0e
    jmp ScummV5_Op_ActorOps__name
ScummV5_Op_ActorOps__dispatch_0e:
    .a8
    cmp #$0E
    bne ScummV5_Op_ActorOps__dispatch_10
    jmp ScummV5_Op_ActorOps__init
ScummV5_Op_ActorOps__dispatch_10:
    .a8
    cmp #$10
    bne ScummV5_Op_ActorOps__dispatch_11
    jmp ScummV5_Op_ActorOps__width
ScummV5_Op_ActorOps__dispatch_11:
    .a8
    cmp #$11
    bne ScummV5_Op_ActorOps__dispatch_12
    jmp ScummV5_Op_ActorOps__scale
ScummV5_Op_ActorOps__dispatch_12:
    .a8
    cmp #$12
    bne ScummV5_Op_ActorOps__dispatch_13
    jmp ScummV5_Op_ActorOps__never_clip
ScummV5_Op_ActorOps__dispatch_13:
    .a8
    cmp #$13
    bne ScummV5_Op_ActorOps__dispatch_14
    jmp ScummV5_Op_ActorOps__always_clip
ScummV5_Op_ActorOps__dispatch_14:
    .a8
    cmp #$14
    bne ScummV5_Op_ActorOps__dispatch_15
    jmp ScummV5_Op_ActorOps__ignore_boxes
ScummV5_Op_ActorOps__dispatch_15:
    .a8
    cmp #$15
    bne ScummV5_Op_ActorOps__dispatch_16
    jmp ScummV5_Op_ActorOps__follow_boxes
ScummV5_Op_ActorOps__dispatch_16:
    .a8
    cmp #$16
    bne ScummV5_Op_ActorOps__dispatch_17
    jmp ScummV5_Op_ActorOps__anim_speed
ScummV5_Op_ActorOps__dispatch_17:
    jmp ScummV5_Op_ActorOps__shadow
ScummV5_Op_ActorOps__dispatch_invalid:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__error_top:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__done_top:
    jmp ScummV5_Op_ActorOps__done
ScummV5_Op_ActorOps__dummy:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    brl ScummV5_Op_ActorOps__param_done
ScummV5_Op_ActorOps__costume:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_CONDITION
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME,x
    brl ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__speed:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_top
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_X,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    brl ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__sound:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_SOUND
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__walk:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_WALK_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__stand:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_STAND_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__talk_color:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_TALK_COLOR
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__init:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_INIT_FRAME
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__width:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_WIDTH
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__always_clip:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_FORCE_CLIP
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__anim_speed:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_ANIM_SPEED
    bra ScummV5_Op_ActorOps__one_byte
ScummV5_Op_ActorOps__shadow:
    .a8
    lda #$80
    ldy #SAME_SCUMM_C14_A_SHADOW
ScummV5_Op_ActorOps__one_byte:
    phy
    jsr ScummV5_C14_FetchByte
    ply
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
    tya
    clc
    adc.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_mid:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__talk:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__animation:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_mid
    lda #$20
    jsr ScummV5_C14_FetchByte
ScummV5_Op_ActorOps__param_done:
    bcs ScummV5_Op_ActorOps__error_mid
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__default:
    jsr ScummV5_C14_DefaultActor
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__elevation:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchWord
    bcs ScummV5_Op_ActorOps__error_mid
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_C14_BaseX
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sep #$20
    .a8
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__anim_default:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_INIT_FRAME,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x
    lda #$03
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
    lda #$04
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda #$05
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_palette:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__invalid_palette:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__palette:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_palette
    cmp #$20
    bcs ScummV5_Op_ActorOps__invalid_palette
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__error_palette
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    clc
    adc #SAME_SCUMM_C14_A_PALETTE
    adc.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__error_name:
    jmp ScummV5_Op_ActorOps__operand_error
ScummV5_Op_ActorOps__invalid_name:
    jmp ScummV5_Op_ActorOps__invalid
ScummV5_Op_ActorOps__name:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    xba
    sta.l SAME_SCUMM_C14_NAME_BASE
    lda #$0000
    sta.l SAME_SCUMM_C14_NAME_INDEX
ScummV5_Op_ActorOps__name_loop:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    bcs ScummV5_Op_ActorOps__invalid_name
    cmp #$00
    beq ScummV5_Op_ActorOps__name_done
    cmp #$FF
    bne ScummV5_Op_ActorOps__name_loop
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    sta.l SAME_SCUMM_CONDITION
    cmp #$01
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$02
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$03
    beq ScummV5_Op_ActorOps__name_loop
    cmp #$08
    beq ScummV5_Op_ActorOps__name_loop
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    jsr ScummV5_FetchByte
    bcs ScummV5_Op_ActorOps__error_name
    jsr ScummV5_C14_StoreNameByte
    bra ScummV5_Op_ActorOps__name_loop
ScummV5_Op_ActorOps__name_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_NAME_INDEX
    sta.l SAME_SCUMM_C14_NAME_SIZES,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__scale:
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__operand_error
    sta.l SAME_SCUMM_CONDITION
    lda #$40
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_ActorOps__operand_error
    sta.l SAME_SCUMM_FETCH_BYTE
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_BOX_SCALE,x
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__never_clip:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__ignore_boxes:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__follow_boxes:
    .a8
    jsr ScummV5_C14_BaseX
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    jmp ScummV5_Op_ActorOps__loop
ScummV5_Op_ActorOps__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ActorOps__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_ActorOps__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ACTOR_OPS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_AnimateActor:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_AnimateActor__ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_AnimateActor__ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_AnimateActor__operand_error
    cmp #$20
    bcs ScummV5_Op_AnimateActor__invalid
    sta.l SAME_SCUMM_C14_ACTOR
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_AnimateActor__operand_error
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_AnimateActor__store
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_AnimateActor__store:
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_ActorFacing_ObserveAnimate_Far
    .endif
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_AnimateActor__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_AnimateActor__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ANIMATE_ACTOR
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_ActorFromPos:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_ActorFromPos__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_ActorFromPos__actors_ready:
    .a8
    lda.l SAME_SCUMM_C16_INITIALIZED
    bne ScummV5_Op_ActorFromPos__state_ready
    jsr ScummV5_C16_ResetState
ScummV5_Op_ActorFromPos__state_ready:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_ActorFromPos__result_ok
    jmp ScummV5_Op_ActorFromPos__operand_error
ScummV5_Op_ActorFromPos__result_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C14_SUBOP
    lda #$80
    jsr ScummV5_C14_FetchWord
    bcc ScummV5_Op_ActorFromPos__x_fetched
    jmp ScummV5_Op_ActorFromPos__operand_error
ScummV5_Op_ActorFromPos__x_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C29_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C14_FetchWord
    bcc ScummV5_Op_ActorFromPos__y_fetched
    jmp ScummV5_Op_ActorFromPos__operand_error
ScummV5_Op_ActorFromPos__y_fetched:
    rep #$20
    .a16
    sta.l SAME_SCUMM_C29_Y
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C29_ACTOR
ScummV5_Op_ActorFromPos__scan:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C29_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_ActorFromPos__present
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__present:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    bne ScummV5_Op_ActorFromPos__visible
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__visible:
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_Op_ActorFromPos__room
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__room:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C29_ACTOR
    and #$00FF
    sta.l SAME_SCUMM_C16_OBJECT
    jsr ScummV5_C16_FindRecord
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_ActorFromPos__bounds
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_MASK+3,x
    and #$80
    beq ScummV5_Op_ActorFromPos__bounds
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__bounds:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C29_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_HIT_LEFT,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C29_X
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_ActorFromPos__left_ok
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__left_ok:
    .a16
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_HIT_RIGHT,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C29_X
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    beq ScummV5_Op_ActorFromPos__x_ok
    bcc ScummV5_Op_ActorFromPos__x_ok
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__x_ok:
    .a16
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_HIT_TOP,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C29_Y
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_ActorFromPos__top_ok
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__top_ok:
    .a16
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_HIT_BOTTOM,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C29_Y
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    beq ScummV5_Op_ActorFromPos__found
    bcc ScummV5_Op_ActorFromPos__found
    jmp ScummV5_Op_ActorFromPos__next
ScummV5_Op_ActorFromPos__found:
    .a16
    lda.l SAME_SCUMM_C29_ACTOR
    and #$00FF
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ActorFromPos__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C29_ACTOR
    inc
    sta.l SAME_SCUMM_C29_ACTOR
    cmp #$20
    bcs ScummV5_Op_ActorFromPos__not_found
    jmp ScummV5_Op_ActorFromPos__scan
ScummV5_Op_ActorFromPos__not_found:
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_ActorFromPos__operand_error:
    jmp ScummV5_Op__error

ScummV5_C30_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C30_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C30_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C30_STATE_SIZE
    bcc ScummV5_C30_ResetState__clear
    rts

ScummV5_Op_FindObject:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_INITIALIZED
    bne ScummV5_Op_FindObject__objects_ready
    jsr ScummV5_C21_ResetState
ScummV5_Op_FindObject__objects_ready:
    .a8
    lda.l SAME_SCUMM_C16_INITIALIZED
    bne ScummV5_Op_FindObject__classes_ready
    jsr ScummV5_C16_ResetState
ScummV5_Op_FindObject__classes_ready:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_FindObject__result_ok
    jmp ScummV5_Op_FindObject__operand_error
ScummV5_Op_FindObject__result_ok:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C30_FetchByteOperand
    bcc ScummV5_Op_FindObject__x_ok
    jmp ScummV5_Op_FindObject__operand_error
ScummV5_Op_FindObject__x_ok:
    .a16
    sta.l SAME_SCUMM_C30_X
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C30_FetchByteOperand
    bcc ScummV5_Op_FindObject__y_ok
    jmp ScummV5_Op_FindObject__operand_error
ScummV5_Op_FindObject__y_ok:
    .a16
    sta.l SAME_SCUMM_C30_Y
    lda #$0000
    sta.l SAME_SCUMM_C30_RECORD_OFFSET
ScummV5_Op_FindObject__scan:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C30_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID,x
    bne ScummV5_Op_FindObject__id_present
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__id_present:
    .a16
    .i16
    sta.l SAME_SCUMM_C16_OBJECT
    jsr ScummV5_C16_FindRecord
    lda.l SAME_SCUMM_C16_RECORD_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_FindObject__hierarchy
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_MASK+3,x
    and #$80
    beq ScummV5_Op_FindObject__hierarchy
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__hierarchy:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C30_RECORD_OFFSET
    sta.l SAME_SCUMM_C30_CURRENT_OFFSET
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C30_DEPTH
ScummV5_Op_FindObject__parent:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C30_CURRENT_OFFSET
    lsr
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C30_PARENTS,x
    beq ScummV5_Op_FindObject__bounds
    cmp.l SAME_SCUMM_C21_RECORD_COUNT
    bcc ScummV5_Op_FindObject__parent_valid
    beq ScummV5_Op_FindObject__parent_valid
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__parent_valid:
    sta.l SAME_SCUMM_C30_MASK
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C30_CURRENT_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_PARENT_STATE,x
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_C30_MASK
    dec
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C30_CURRENT_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_STATE,x
    and #$0F
    cmp.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_FindObject__parent_state_ok
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__parent_state_ok:
    lda.l SAME_SCUMM_C30_DEPTH
    inc
    sta.l SAME_SCUMM_C30_DEPTH
    cmp.l SAME_SCUMM_C21_RECORD_COUNT
    bcc ScummV5_Op_FindObject__parent_again
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__parent_again:
    jmp ScummV5_Op_FindObject__parent
ScummV5_Op_FindObject__bounds:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C30_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C30_X
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_FindObject__left_ok
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__left_ok:
    .a16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_X,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WIDTH,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C30_X
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_FindObject__x_ok_bounds
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__x_ok_bounds:
    .a16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C30_Y
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_FindObject__top_ok
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__top_ok:
    .a16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_Y,x
    clc
    adc.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_HEIGHT,x
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_C30_Y
    eor #$8000
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_FindObject__found
    jmp ScummV5_Op_FindObject__next
ScummV5_Op_FindObject__found:
    .a16
    lda.l SAME_SCUMM_C30_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID,x
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FindObject__next:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C30_RECORD_OFFSET
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    sta.l SAME_SCUMM_C30_RECORD_OFFSET
    sta.l SAME_SCUMM_LHS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_RECORD_COUNT
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_FindObject__not_found
    beq ScummV5_Op_FindObject__not_found
    jmp ScummV5_Op_FindObject__scan
ScummV5_Op_FindObject__not_found:
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FindObject__operand_error:
    jmp ScummV5_Op__error

ScummV5_C30_FetchByteOperand:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C30_MASK
    and.l SAME_SCUMM_LAST_OPCODE
    beq ScummV5_C30_FetchByteOperand__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C30_FetchByteOperand__done
    jsr ScummV5_ReadVariableReference
    rts
ScummV5_C30_FetchByteOperand__direct:
    jsr ScummV5_FetchByte
    bcs ScummV5_C30_FetchByteOperand__done
    rep #$20
    .a16
    and #$00FF
    clc
ScummV5_C30_FetchByteOperand__done:
    rts

; Canonical v5 $0F/$8F getObjectState. Object states are global byte values;
; the operand is the normal flagged word object reference and the result uses
; the normal result-variable decoder.
ScummV5_Op_GetObjectState:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_GetObjectState__error
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C14_SUBOP
    lda #$80
    jsr ScummV5_C14_FetchWord
    bcs ScummV5_Op_GetObjectState__error
    rep #$20
    .a16
    cmp #$1000
    bcs ScummV5_Op_GetObjectState__invalid
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_OBJECT_STATES,x
    rep #$20
    .a16
    and #$00FF
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_GetObjectState__invalid:
    sep #$20
    .a8
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
ScummV5_Op_GetObjectState__error:
    jmp ScummV5_Op__error

; Canonical v5 $03/$83 getActorRoom. The original reads its actor-room array;
; ScummVM's bounded oracle returns zero for an invalid actor id. Sparse SAME
; actor records likewise read as the default room zero until initialized.
ScummV5_Op_GetActorRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_GetActorRoom__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_GetActorRoom__actors_ready:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_GetActorRoom__error
    sep #$20
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcs ScummV5_Op_GetActorRoom__error
    cmp #$20
    bcs ScummV5_Op_GetActorRoom__zero
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    beq ScummV5_Op_GetActorRoom__zero
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    bra ScummV5_Op_GetActorRoom__write
ScummV5_Op_GetActorRoom__zero:
    .a8
    lda #$00
ScummV5_Op_GetActorRoom__write:
    .a8
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_GetActorRoom__error:
    jmp ScummV5_Op__error

; Canonical v5 $06/$86 getActorElevation.  The actor operand is the normal
; flagged byte and the result is the existing C14 elevation word.
ScummV5_Op_GetActorElevation:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_GetActorElevation__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_GetActorElevation__actors_ready:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_GetActorElevation__error
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C14_SUBOP
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_GetActorElevation__error
    cmp #$20
    bcs ScummV5_Op_GetActorElevation__zero
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sta.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_GetActorElevation__write
ScummV5_Op_GetActorElevation__zero:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_GetActorElevation__write:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_GetActorElevation__error:
    jmp ScummV5_Op__error

; Canonical v5 $3B/$BB getActorScale.  The actor operand is a flagged byte;
; return the current horizontal scale through the normal result reference.
ScummV5_Op_GetActorScale:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_GetActorScale__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_GetActorScale__actors_ready:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_GetActorScale__error
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C14_FetchByte
    bcs ScummV5_Op_GetActorScale__error
    cmp #$20
    bcs ScummV5_Op_GetActorScale__zero
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_GetActorScale__write
ScummV5_Op_GetActorScale__zero:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_GetActorScale__write:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_GetActorScale__error:
    jmp ScummV5_Op__error

ScummV5_Op_PutActorInRoom:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_PutActorInRoom__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_PutActorInRoom__actors_ready:
    .a8
    lda.l SAME_SCUMM_C31_INITIALIZED
    bne ScummV5_Op_PutActorInRoom__state_ready
    jsr ScummV5_C31_ResetState
ScummV5_Op_PutActorInRoom__state_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_PutActorInRoom__operand_error
    cmp #$20
    bcs ScummV5_Op_PutActorInRoom__invalid_actor
    sta.l SAME_SCUMM_C31_ACTOR
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcs ScummV5_Op_PutActorInRoom__operand_error
    sta.l SAME_SCUMM_C31_ROOM
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_PutActorInRoom__actor_present
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_PutActorInRoom__actor_present:
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_C31_ROOM
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    bne ScummV5_Op_PutActorInRoom__done
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C31_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C31_POSITIONS,x
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C31_ACTOR
    tax
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
ScummV5_Op_PutActorInRoom__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_PutActorInRoom__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_PutActorInRoom__invalid_actor:
    sep #$20
    .a8
    lda #SCUMM_ERR_PUT_ACTOR_ROOM
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_PutActorAtObject:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_INITIALIZED
    bne ScummV5_Op_PutActorAtObject__actors_ready
    jsr ScummV5_C14_ResetState
ScummV5_Op_PutActorAtObject__actors_ready:
    .a8
    lda.l SAME_SCUMM_C31_INITIALIZED
    bne ScummV5_Op_PutActorAtObject__placement_ready
    jsr ScummV5_C31_ResetState
ScummV5_Op_PutActorAtObject__placement_ready:
    .a8
    lda.l SAME_SCUMM_C21_INITIALIZED
    bne ScummV5_Op_PutActorAtObject__objects_ready
    jsr ScummV5_C21_ResetState
ScummV5_Op_PutActorAtObject__objects_ready:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_C7_SUBOP
    sta.l SAME_SCUMM_C14_SUBOP
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_PutActorAtObject__actor_fetched
    jmp ScummV5_Op_PutActorAtObject__operand_error
ScummV5_Op_PutActorAtObject__actor_fetched:
    .a8
    cmp #$20
    bcc ScummV5_Op_PutActorAtObject__actor_valid
    jmp ScummV5_Op_PutActorAtObject__invalid_actor
ScummV5_Op_PutActorAtObject__actor_valid:
    .a8
    sta.l SAME_SCUMM_C32_ACTOR
    lda #$40
    jsr ScummV5_C14_FetchWord
    bcc ScummV5_Op_PutActorAtObject__object_fetched
    jmp ScummV5_Op_PutActorAtObject__operand_error
ScummV5_Op_PutActorAtObject__object_fetched:
    .a16
    sta.l SAME_SCUMM_C32_OBJECT
    lda #$00F0
    sta.l SAME_SCUMM_C32_X
    lda #$0078
    sta.l SAME_SCUMM_C32_Y
    lda #$0000
    sta.l SAME_SCUMM_C32_RECORD_OFFSET
ScummV5_Op_PutActorAtObject__scan:
    .a16
    lda.l SAME_SCUMM_C32_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_ID,x
    cmp.l SAME_SCUMM_C32_OBJECT
    beq ScummV5_Op_PutActorAtObject__found
    lda.l SAME_SCUMM_C32_RECORD_OFFSET
    clc
    adc #SAME_SCUMM_C21_RECORD_STRIDE
    sta.l SAME_SCUMM_C32_RECORD_OFFSET
    sta.l SAME_SCUMM_LHS
    sep #$20
    .a8
    lda.l SAME_SCUMM_C21_RECORD_COUNT
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_PutActorAtObject__place
    beq ScummV5_Op_PutActorAtObject__place
    bra ScummV5_Op_PutActorAtObject__scan
ScummV5_Op_PutActorAtObject__found:
    .a16
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_X,x
    sta.l SAME_SCUMM_C32_X
    lda.l SAME_SCUMM_C21_RECORDS+SAME_SCUMM_C21_R_WALK_Y,x
    sta.l SAME_SCUMM_C32_Y
ScummV5_Op_PutActorAtObject__place:
    .a16
    lda.l SAME_SCUMM_C32_ACTOR
    and #$00FF
    asl
    asl
    tax
    lda.l SAME_SCUMM_C32_X
    sta.l SAME_SCUMM_C31_POSITIONS,x
    lda.l SAME_SCUMM_C32_Y
    sta.l SAME_SCUMM_C31_POSITIONS+2,x
    lda.l SAME_SCUMM_C32_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    bne ScummV5_Op_PutActorAtObject__actor_present
    jsr ScummV5_C14_DefaultActor
ScummV5_Op_PutActorAtObject__actor_present:
    .a8
    jsr ScummV5_C14_BaseX
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    cmp.l SAME_SCUMM_C22_CURRENT_ROOM
    bne ScummV5_Op_PutActorAtObject__not_current
    lda.l SAME_SCUMM_C22_CURRENT_ROOM
    beq ScummV5_Op_PutActorAtObject__not_current
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    bra ScummV5_Op_PutActorAtObject__stop_moving
ScummV5_Op_PutActorAtObject__not_current:
    .a8
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
    beq ScummV5_Op_PutActorAtObject__done
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_VISIBLE,x
ScummV5_Op_PutActorAtObject__stop_moving:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C32_ACTOR
    and #$00FF
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C31_MOVING,x
ScummV5_Op_PutActorAtObject__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_PutActorAtObject__operand_error:
    jmp ScummV5_Op__error
ScummV5_Op_PutActorAtObject__invalid_actor:
    sep #$20
    .a8
    lda #SCUMM_ERR_PUT_ACTOR_OBJECT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_C31_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C31_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C31_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C31_STATE_SIZE
    bcc ScummV5_C31_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C31_INITIALIZED
    rts

ScummV5_C31_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C31_INITIALIZED
    rts

ScummV5_C14_FetchByte:
    sep #$20
    .a8
    jmp ScummV5_C7_FetchFlaggedByte

ScummV5_C14_FetchWord:
    sep #$20
    .a8
    and.l SAME_SCUMM_C14_SUBOP
    beq ScummV5_C14_FetchWord__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C14_FetchWord__done
    jmp ScummV5_ReadVariableReference
ScummV5_C14_FetchWord__direct:
    jmp ScummV5_FetchWord
ScummV5_C14_FetchWord__done:
    rts

ScummV5_C14_BaseX:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_BASE
    tax
    sep #$20
    .a8
    rts

ScummV5_C14_StoreNameByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C14_NAME_INDEX
    cmp #$00FF
    bcs ScummV5_C14_StoreNameByte__full
    clc
    adc.l SAME_SCUMM_C14_NAME_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C14_NAMES,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_C14_NAME_INDEX
    inc
    sta.l SAME_SCUMM_C14_NAME_INDEX
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    clc
    rts
ScummV5_C14_StoreNameByte__full:
    sep #$20
    .a8
    sec
    rts

ScummV5_C14_DefaultActor:
    jsr ScummV5_C14_BaseX
    lda #$08
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_X,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SPEED_Y,x
    lda #$00
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SOUND,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION+1,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_IGNORE_BOXES,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIM_SPEED,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SHADOW,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ANIMATION,x
    lda #$01
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_INIT_FRAME,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_PRESENT,x
    lda #$02
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WALK_FRAME,x
    lda #$03
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
    lda #$04
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_START,x
    lda #$05
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_STOP,x
    lda #$0F
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_TALK_COLOR,x
    lda #$18
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_WIDTH,x
    lda #$FF
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_X,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_SCALE_Y,x
    sta.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_BOX_SCALE,x
    rts

ScummV5_C10_FetchByteParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C10_SUBOP
    beq ScummV5_C10_FetchByteParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C10_FetchByteParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C10_FetchByteParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C10_FetchByteParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C10_FetchByteParam__done:
    rts

ScummV5_C10_FetchWordParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    and.l SAME_SCUMM_C10_SUBOP
    beq ScummV5_C10_FetchWordParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C10_FetchWordParam__done
    jmp ScummV5_ReadVariableReference
ScummV5_C10_FetchWordParam__direct:
    jmp ScummV5_FetchWord
ScummV5_C10_FetchWordParam__done:
    rts

ScummV5_C10_MarkPalette:
    sep #$20
    .a8
    sta.l SAME_SCUMM_CONDITION
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PALETTE_PRESENT,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_PALETTE_PRESENT,x
    lda.l SAME_SCUMM_CONDITION
    clc
    rts

ScummV5_C10_ReadFilename:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
ScummV5_C10_ReadFilename__loop:
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_C10_ReadFilename__done
    beq ScummV5_C10_ReadFilename__terminal
    ldx #$0000
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    cmp #$3F
    bcs ScummV5_C10_ReadFilename__error
    tax
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C10_REQUEST_NAME,x
    lda.l SAME_SCUMM_CONDITION
    inc
    sta.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    bra ScummV5_C10_ReadFilename__loop
ScummV5_C10_ReadFilename__terminal:
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    bne ScummV5_C10_ReadFilename__success
ScummV5_C10_ReadFilename__error:
    .a8
    lda #$32
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    lda #SCUMM_ERR_ROOM_OPS
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C10_ReadFilename__success:
    clc
ScummV5_C10_ReadFilename__done:
    rts

ScummV5_C10_SaveAuxString:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    tax
    lda.l SAME_SCUMM_C8_SIZES,x
    beq ScummV5_C10_SaveAuxString__error
    sta.l SAME_SCUMM_C10_AUX_SIZE
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    sta.l SAME_SCUMM_C10_AUX_NAME_SIZE
    tax
ScummV5_C10_SaveAuxString__copy_name:
    dex
    bmi ScummV5_C10_SaveAuxString__name_done
    lda.l SAME_SCUMM_C10_REQUEST_NAME,x
    sta.l SAME_SCUMM_C10_AUX_NAME,x
    bra ScummV5_C10_SaveAuxString__copy_name
ScummV5_C10_SaveAuxString__name_done:
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_SOURCE_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C10_PARAM3
    ldx #$0000
ScummV5_C10_SaveAuxString__copy_data:
    rep #$20
    .a16
    txa
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_C10_SaveAuxString__success
    sta.l SAME_SCUMM_C10_PARAM4
    clc
    adc.l SAME_SCUMM_C8_SOURCE_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C10_PARAM4
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C10_AUX_DATA,x
    inx
    bra ScummV5_C10_SaveAuxString__copy_data
ScummV5_C10_SaveAuxString__error:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C10_SaveAuxString__success:
    clc
    rts

ScummV5_C10_LoadAuxString:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    beq ScummV5_C10_LoadAuxString__absent
    lda.l SAME_SCUMM_C10_REQUEST_NAME_SIZE
    cmp.l SAME_SCUMM_C10_AUX_NAME_SIZE
    bne ScummV5_C10_LoadAuxString__absent
    tax
ScummV5_C10_LoadAuxString__compare_name:
    dex
    bmi ScummV5_C10_LoadAuxString__matched
    lda.l SAME_SCUMM_C10_REQUEST_NAME,x
    cmp.l SAME_SCUMM_C10_AUX_NAME,x
    bne ScummV5_C10_LoadAuxString__absent
    bra ScummV5_C10_LoadAuxString__compare_name
ScummV5_C10_LoadAuxString__matched:
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    tax
    lda.l SAME_SCUMM_C10_AUX_SIZE
    sta.l SAME_SCUMM_C8_SIZES,x
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_SIZE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C10_PARAM3
    ldx #$0000
ScummV5_C10_LoadAuxString__copy_data:
    rep #$20
    .a16
    txa
    cmp.l SAME_SCUMM_C10_PARAM3
    bcs ScummV5_C10_LoadAuxString__absent
    sta.l SAME_SCUMM_C10_PARAM4
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_AUX_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM4
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C8_DATA,x
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C10_PARAM4
    tax
    inx
    bra ScummV5_C10_LoadAuxString__copy_data
ScummV5_C10_LoadAuxString__absent:
    clc
    rts

ScummV5_C10_StoreCycleDelay:
    sep #$20
    .a8
    beq ScummV5_C10_StoreCycleDelay__zero
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_LOOP
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
ScummV5_C10_StoreCycleDelay__denominator:
    .a16
    lda.l SAME_SCUMM_OPERAND
    clc
    adc #$004C
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_C10_StoreCycleDelay__denominator
    lda #$4000
    ldy #$0000
ScummV5_C10_StoreCycleDelay__divide:
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_C10_StoreCycleDelay__quotient
    sec
    sbc.l SAME_SCUMM_OPERAND
    iny
    bra ScummV5_C10_StoreCycleDelay__divide
ScummV5_C10_StoreCycleDelay__quotient:
    tya
    bra ScummV5_C10_StoreCycleDelay__store
ScummV5_C10_StoreCycleDelay__zero:
    rep #$20
    .a16
    lda #$0000
ScummV5_C10_StoreCycleDelay__store:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C10_PARAM0
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C10_CYCLE_DELAYS,x
    clc
    rts

ScummV5_C10_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C10_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C10_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C10_STATE_SIZE
    bcc ScummV5_C10_ResetState__clear
    lda #$00A0
    sta.l SAME_SCUMM_C10_SCROLL_MIN
    sta.l SAME_SCUMM_C10_SCROLL_MAX
    lda #$00C8
    sta.l SAME_SCUMM_C10_SCREEN_BOTTOM
    lda #$0280
    sta.l SAME_SCUMM_C10_ROOM_WIDTH
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C10_INTENSITY
    sta.l SAME_SCUMM_C10_INTENSITY+1
    sta.l SAME_SCUMM_C10_INTENSITY+2
    sta.l SAME_SCUMM_C10_INTENSITY+4
    sta.l SAME_SCUMM_C10_RGB_INTENSITY
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+1
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+2
    sta.l SAME_SCUMM_C10_RGB_INTENSITY+4
    sta.l SAME_SCUMM_C10_SHADOW
    sta.l SAME_SCUMM_C10_SHADOW+1
    sta.l SAME_SCUMM_C10_SHADOW+2
    sta.l SAME_SCUMM_C10_SHADOW+4
    clc
    rts

ScummV5_C11_ResetState:
    rep #$20
    .a16
    lda #$ACE1
    sta.l SAME_SCUMM_C11_RANDOM_STATE
    lda #$0000
    sta.l SAME_SCUMM_C11_MAXIMUM
    sta.l SAME_SCUMM_C11_SAMPLE
    rts

ScummV5_C12_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C12_ROOM
    ldx #$0000
ScummV5_C12_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C12_MAPPER,x
    inx
    inx
    cpx #$0080
    bcc ScummV5_C12_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C12_INITIALIZED
    rts

ScummV5_C12_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C12_INITIALIZED
    rts

ScummV5_C13_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C13_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C13_LOADED,x
    inx
    inx
    cpx #SAME_SCUMM_C13_STATE_SIZE
    bcc ScummV5_C13_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C13_INITIALIZED
    rts

ScummV5_C13_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C13_INITIALIZED
    rts

ScummV5_C14_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C14_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C14_ACTORS,x
    inx
    inx
    cpx #$0820
    bcc ScummV5_C14_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C14_INITIALIZED
    rts

ScummV5_C14_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C14_INITIALIZED
    rts

ScummV5_C15_ResetState:
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_C15_CAMERA_FOLLOWS
    lda #$00
    sta.l SAME_SCUMM_C15_CAMERA_MODE
    sta.l SAME_SCUMM_C15_MOVING_TO_ACTOR
    lda #$01
    sta.l SAME_SCUMM_C15_INITIALIZED
    rts

ScummV5_Camera_ResetState:
    jsl ScummV5_Camera_ResetState_Far
    rts

; One canonical post-walk camera phase.  Phase 6F deliberately adds only the
; normal-mode path required after setCameraAt; existing follow intent remains
; stored without inventing broader actor-follow visual scrolling.
ScummV5_Camera_Update:
    jsl ScummV5_Camera_Update_Far
    rts

ScummV5_C16_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C16_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C16_RECORDS,x
    inx
    inx
    cpx #$1000
    bcc ScummV5_C16_ResetState__clear
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C16_INITIALIZED
    rts

ScummV5_C16_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C16_INITIALIZED
    rts

ScummV5_C17_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C17_ResetState__loop:
    .a16
    .i16
    sta.l SAME_SCUMM_C17_VERBS,x
    inx
    inx
    cpx #$6000
    bcc ScummV5_C17_ResetState__loop
    ldx #$0000
ScummV5_C17_ResetState__saved_loop:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C26_SAVED_STRIDE
    tax
    cpx #(SAME_SCUMM_C26_SAVED_STRIDE * SAME_SCUMM_C26_SAVED_COUNT)
    bcc ScummV5_C17_ResetState__saved_loop
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C17_INITIALIZED
    lda #$00
    sta.l SAME_SCUMM_C17_CURRENT_ROOM
    rts

ScummV5_C17_InvalidateState:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C17_INITIALIZED
    rts

; Canonical v5 $AB saveRestoreVerbs. The four following bytes are deliberately
; direct operands: upstream consumes flag-aware operands but switches on the
; exact sub-op byte, so high-bit variants fail after consuming their operands.
; Saved verbs occupy physical slots independent of the dense active C17 table.
ScummV5_Op_SaveRestoreVerbs:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_INITIALIZED
    bne ScummV5_Op_SaveRestoreVerbs__state_ready
    jsr ScummV5_C17_ResetState
ScummV5_Op_SaveRestoreVerbs__state_ready:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__operation_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__operation_ok:
    sta.l SAME_SCUMM_C26_OPERATION
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__first_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__first_ok:
    sta.l SAME_SCUMM_C26_FIRST
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__last_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__last_ok:
    sta.l SAME_SCUMM_C26_LAST
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SaveRestoreVerbs__bank_ok
    jmp ScummV5_Op_SaveRestoreVerbs__operand_error
ScummV5_Op_SaveRestoreVerbs__bank_ok:
    .a8
    sta.l SAME_SCUMM_C26_BANK
    lda.l SAME_SCUMM_C26_OPERATION
    cmp #$01
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    cmp #$02
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    cmp #$03
    beq ScummV5_Op_SaveRestoreVerbs__range_check
    jmp ScummV5_C26_Error
ScummV5_Op_SaveRestoreVerbs__range_check:
    lda.l SAME_SCUMM_C26_FIRST
    cmp.l SAME_SCUMM_C26_LAST
    bcc ScummV5_Op_SaveRestoreVerbs__range_loop
    beq ScummV5_Op_SaveRestoreVerbs__range_loop
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SaveRestoreVerbs__range_loop:
    .a8
    lda.l SAME_SCUMM_C26_FIRST
    sta.l SAME_SCUMM_C17_VERB
    jsr ScummV5_C17_RecordOffset
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_RECORD_OFFSET
    sta.l SAME_SCUMM_C26_ACTIVE_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_OPERATION
    cmp #$01
    beq ScummV5_Op_SaveRestoreVerbs__save
    cmp #$02
    beq ScummV5_Op_SaveRestoreVerbs__restore
    jmp ScummV5_Op_SaveRestoreVerbs__delete

ScummV5_Op_SaveRestoreVerbs__save:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    bne ScummV5_Op_SaveRestoreVerbs__save_bank
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_bank:
    jsr ScummV5_C17_RecordX
    sep #$20
    .a8
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_PRESENT,x
    bne ScummV5_Op_SaveRestoreVerbs__save_present
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_present:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    beq ScummV5_Op_SaveRestoreVerbs__save_active
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__save_active:
    jsr ScummV5_C26_FindSaved
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_Op_SaveRestoreVerbs__save_slot
    jmp ScummV5_C26_Error
ScummV5_Op_SaveRestoreVerbs__save_slot:
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    lda.l SAME_SCUMM_C26_FIRST
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_VERB,x
    jsr ScummV5_C26_CopyActiveToSaved
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    clc
    adc #(SAME_SCUMM_C26_S_PAYLOAD + SAME_SCUMM_C17_V_SAVE_ID)
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_BANK
    sta.l SAME_SCUMM_C26_SAVED,x
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+1,x
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_SaveRestoreVerbs__next

ScummV5_Op_SaveRestoreVerbs__restore:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    beq ScummV5_Op_SaveRestoreVerbs__next
    jsr ScummV5_C26_FindSaved
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SaveRestoreVerbs__next
    jsr ScummV5_C17_ClearRecord
    jsr ScummV5_C26_CopySavedToActive
    jsr ScummV5_C17_RecordX
    lda #$0000
    sta.l SAME_SCUMM_C17_VERBS+SAME_SCUMM_C17_V_SAVE_ID,x
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    jmp ScummV5_Op_SaveRestoreVerbs__next

ScummV5_Op_SaveRestoreVerbs__delete:
    .a8
    lda.l SAME_SCUMM_C26_BANK
    bne ScummV5_Op_SaveRestoreVerbs__delete_saved
    jsr ScummV5_C17_ClearRecord
    jmp ScummV5_Op_SaveRestoreVerbs__next
ScummV5_Op_SaveRestoreVerbs__delete_saved:
    jsr ScummV5_C26_FindSaved
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    beq ScummV5_Op_SaveRestoreVerbs__next
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x

ScummV5_Op_SaveRestoreVerbs__next:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_FIRST
    cmp.l SAME_SCUMM_C26_LAST
    beq ScummV5_Op_SaveRestoreVerbs__done
    inc
    sta.l SAME_SCUMM_C26_FIRST
    jmp ScummV5_Op_SaveRestoreVerbs__range_loop
ScummV5_Op_SaveRestoreVerbs__done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_SaveRestoreVerbs__operand_error:
    jmp ScummV5_Op__error

; Scan every saved slot so the first free offset is available even when an
; earlier matching saved identity exists. The first physical match is canonical.
ScummV5_C26_FindSaved:
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_C26_FREE_OFFSET
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
    ldx #$0000
ScummV5_C26_FindSaved__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PRESENT,x
    bne ScummV5_C26_FindSaved__occupied
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_FREE_OFFSET
    cmp #$FFFF
    bne ScummV5_C26_FindSaved__next
    txa
    sta.l SAME_SCUMM_C26_FREE_OFFSET
    bra ScummV5_C26_FindSaved__next
ScummV5_C26_FindSaved__occupied:
    .a8
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_VERB,x
    cmp.l SAME_SCUMM_C26_FIRST
    bne ScummV5_C26_FindSaved__next
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PAYLOAD+SAME_SCUMM_C17_V_SAVE_ID+1,x
    bne ScummV5_C26_FindSaved__next
    lda.l SAME_SCUMM_C26_SAVED+SAME_SCUMM_C26_S_PAYLOAD+SAME_SCUMM_C17_V_SAVE_ID,x
    cmp.l SAME_SCUMM_C26_BANK
    bne ScummV5_C26_FindSaved__next
    rep #$20
    .a16
    lda.l SAME_SCUMM_C26_SAVED_OFFSET
    cmp #$FFFF
    bne ScummV5_C26_FindSaved__next
    txa
    sta.l SAME_SCUMM_C26_SAVED_OFFSET
ScummV5_C26_FindSaved__next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C26_SAVED_STRIDE
    tax
    cpx #(SAME_SCUMM_C26_SAVED_STRIDE * SAME_SCUMM_C26_SAVED_COUNT)
    bcc ScummV5_C26_FindSaved__loop
    rts

ScummV5_C26_CopyActiveToSaved:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C26_COPY_INDEX
ScummV5_C26_CopyActiveToSaved__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc.l SAME_SCUMM_C26_ACTIVE_OFFSET
    tax
    lda.l SAME_SCUMM_C17_VERBS,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc #SAME_SCUMM_C26_S_PAYLOAD
    adc.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C26_SAVED,x
    lda.l SAME_SCUMM_C26_COPY_INDEX
    inc
    inc
    sta.l SAME_SCUMM_C26_COPY_INDEX
    cmp #SAME_SCUMM_C17_VERB_STRIDE
    bcc ScummV5_C26_CopyActiveToSaved__loop
    rts

ScummV5_C26_CopySavedToActive:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_C26_COPY_INDEX
ScummV5_C26_CopySavedToActive__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc #SAME_SCUMM_C26_S_PAYLOAD
    adc.l SAME_SCUMM_C26_SAVED_OFFSET
    tax
    lda.l SAME_SCUMM_C26_SAVED,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C26_COPY_INDEX
    clc
    adc.l SAME_SCUMM_C26_ACTIVE_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C17_VERBS,x
    lda.l SAME_SCUMM_C26_COPY_INDEX
    inc
    inc
    sta.l SAME_SCUMM_C26_COPY_INDEX
    cmp #SAME_SCUMM_C17_VERB_STRIDE
    bcc ScummV5_C26_CopySavedToActive__loop
    rts

ScummV5_C26_Error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SAVE_VERBS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_SetVarRange:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_SetVarRange__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__result_ok:
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetVarRange__count_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__count_ok:
    rep #$20
    .a16
    and #$00FF
    bne ScummV5_Op_SetVarRange__count_nonzero
    lda #$0100
ScummV5_Op_SetVarRange__count_nonzero:
    sta.l SAME_SCUMM_C9_COUNT
ScummV5_Op_SetVarRange__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    bmi ScummV5_Op_SetVarRange__word
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SetVarRange__byte_ok
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__byte_ok:
    rep #$20
    .a16
    and #$00FF
    bra ScummV5_Op_SetVarRange__store
ScummV5_Op_SetVarRange__word:
    rep #$20
    .a16
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SetVarRange__store
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__store:
    .a16
    jsr ScummV5_WriteResultValue
    lda.l SAME_SCUMM_C9_COUNT
    dec
    sta.l SAME_SCUMM_C9_COUNT
    beq ScummV5_Op_SetVarRange__done
    jsr ScummV5_C9_AdvanceResult
    bcc ScummV5_Op_SetVarRange__loop
    jmp ScummV5_Op__error
ScummV5_Op_SetVarRange__done:
    jmp ScummV5_Engine_Frame__next

; Advance the resolved destination while retaining its global/local/bit class.
; Packed bit indices have canonical 12-bit wrap; globals and locals fail when
; a consecutive range crosses their storage boundary.
ScummV5_C9_AdvanceResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_C9_AdvanceResult__bit
    bmi ScummV5_C9_AdvanceResult__local
    bit #$2000
    bne ScummV5_C9_AdvanceResult__global_indexed
    clc
    adc #$0002
    cmp #(SAME_SCUMM_VARIABLE_COUNT * 2)
    bcc ScummV5_C9_AdvanceResult__save
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C9_AdvanceResult__global_indexed:
    ; M23B encodes global variables >= 16 as $2000 | (index * 2).
    ; Advance the index while retaining that namespace marker; comparing the
    ; encoded value directly against the byte-offset capacity falsely rejects
    ; valid ranges such as global 127 -> 128.
    .a16
    and #$1FFF
    clc
    adc #$0002
    cmp #(SAME_SCUMM_VARIABLE_COUNT * 2)
    bcc ScummV5_C9_AdvanceResult__global_indexed_save
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C9_AdvanceResult__global_indexed_save:
    .a16
    ora #$2000
    bra ScummV5_C9_AdvanceResult__save
ScummV5_C9_AdvanceResult__local:
    .a16
    and #$003F
    cmp #$003E
    bne ScummV5_C9_AdvanceResult__local_room
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_C9_AdvanceResult__local_room:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    clc
    adc #$0002
    bra ScummV5_C9_AdvanceResult__save
ScummV5_C9_AdvanceResult__bit:
    .a16
    and #$0FFF
    inc
    and #$0FFF
    ora #$4000
ScummV5_C9_AdvanceResult__save:
    .a16
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts

; C25 implements canonical v5 soundKludge word-varargs. Non--1 commands are
; retained across ticks; command -1 drains them in order and emits one final
; normalized FLUSH packet. The supported neutral subset is iMUSE commands
; 6 (master volume), 8 (start sound), 9 (stop sound), and 10/11 (stop all).
ScummV5_C25_ResetState:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_C25_FLUSH_COUNT
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    sep #$20
    .a8
    sta.l SAME_SCUMM_C25_WORD_INDEX
    ; Reset the complete bounded command store as well as its cursors.  A
    ; frame-end flush may run before the first authored sound command, so a
    ; retained record must never be mistaken for a live queue entry.
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C25_ResetState__clear_queue:
    .a16
    .i16
    sta.l SAME_SCUMM_C25_QUEUE,x
    inx
    inx
    cpx #$0410
    bcc ScummV5_C25_ResetState__clear_queue
    sep #$20
    .a8
    rts

ScummV5_Op_SoundKludge:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C25_PENDING_COUNT
ScummV5_Op_SoundKludge__next_word:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_SoundKludge__selector_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_SoundKludge__words_done
    sta.l SAME_SCUMM_C25_SELECTOR
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    cmp #SAME_SCUMM_C25_MAX_WORDS
    bcc ScummV5_Op_SoundKludge__word_room
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$03
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__word_room:
    .a8
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_SoundKludge__word_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$02
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__word_ok:
    rep #$20
    .a16
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    and #$80
    beq ScummV5_Op_SoundKludge__value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_SoundKludge__variable_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$04
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__variable_ok:
    .a16
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_SoundKludge__value_ready:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C25_PENDING_WORDS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    inc
    sta.l SAME_SCUMM_C25_PENDING_COUNT
    jmp ScummV5_Op_SoundKludge__next_word

ScummV5_Op_SoundKludge__words_done:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_PENDING
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_PENDING_WORDS
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_WORDS
    lda.l SAME_SCUMM_C25_PENDING_WORDS+2
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_WORDS+2
    lda.l SAME_SCUMM_C25_PENDING_WORDS+4
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_WORDS+4
    lda.l SAME_SCUMM_C25_PENDING_WORDS+6
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_WORDS+6
    sep #$20
    .a8
    .endif
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    bne ScummV5_Op_SoundKludge__nonempty
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$05
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__nonempty:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_PENDING_WORDS
    cmp #$FFFF
    bne ScummV5_Op_SoundKludge__queue
    jmp ScummV5_C25_Flush

ScummV5_Op_SoundKludge__queue:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    cmp #SAME_SCUMM_C25_MAX_COMMANDS
    bcc ScummV5_Op_SoundKludge__queue_room
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$06
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_Op_SoundKludge__queue_room:
    ; Capture the record index before any fixture diagnostics.  The pending
    ; payload copy below changes A several times; deriving the queue offset
    ; from that transient value aliases later commands into arbitrary memory.
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    and #$00FF
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_PENDING_WORDS
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_WORDS
    lda.l SAME_SCUMM_C25_PENDING_WORDS+2
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_WORDS+2
    lda.l SAME_SCUMM_C25_PENDING_WORDS+4
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_WORDS+4
    lda.l SAME_SCUMM_C25_PENDING_WORDS+6
    sta.l SAME_SCUMM_SCENARIO_C25_PRODUCER_WORDS+6
    .endif
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_C25_QUEUE,x
    lda #$00
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
ScummV5_Op_SoundKludge__copy_word:
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    cmp.l SAME_SCUMM_C25_PENDING_COUNT
    bcs ScummV5_Op_SoundKludge__queued
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_C25_PENDING_WORDS,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    and #$00FF
    asl
    inc
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C25_QUEUE,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    inc
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    bra ScummV5_Op_SoundKludge__copy_word
ScummV5_Op_SoundKludge__queued:
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    inc
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    .if SAME_BUILD_M24RB
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp #SAME_M24RB_LOCAL_SCRIPT
    bne ScummV5_Op_SoundKludge__m24rb_continue
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    cmp #SAME_M24RB_LSCR_PREFIX_COMMANDS
    bne ScummV5_Op_SoundKludge__m24rb_continue
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_PENDING_WORDS
    cmp #$010F
    bne ScummV5_Op_SoundKludge__m24rb_continue16
    lda.l SAME_SCUMM_C25_PENDING_WORDS+2
    cmp #$FFFF
    bne ScummV5_Op_SoundKludge__m24rb_continue16
    lda #$FFFF
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_SoundKludge__m24rb_continue16:
    sep #$20
    .a8
ScummV5_Op_SoundKludge__m24rb_continue:
    .a8
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_C25_Flush:
.if SAME_BUILD_M24RB && !SAME_BUILD_SCUMM_M20 && !SAME_BUILD_SCUMM_M21 && !SAME_BUILD_SCUMM_M22
    jsl ScummV5_C25_Flush_Far
    rts
ScummV5_C25_Flush_Bank0_Resume:
    .bank 83
    .org $8000
ScummV5_C25_Flush_Far:
.endif
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_PENDING_COUNT
    lda #$00
    sta.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
ScummV5_C25_Flush__next_command:
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    cmp.l SAME_SCUMM_C25_PENDING_COUNT
    bcc ScummV5_C25_Flush__command_present
    jmp ScummV5_C25_Flush__complete
ScummV5_C25_Flush__command_present:
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE,x
    ; A record is one count byte followed by count little-endian words.  Reject
    ; corrupt counts before copying any word; command dispatch below always uses
    ; word zero, never this count byte.
    beq ScummV5_C25_Flush__record_error
    cmp #(SAME_SCUMM_C25_MAX_WORDS + 1)
    bcc ScummV5_C25_Flush__record_count_ok
ScummV5_C25_Flush__record_error:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$07
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_COUNT
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PENDING
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_RECORD
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_RECORD+1
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_RECORD+2
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_RECORD+3
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_RECORD+4
    .endif
    jml ScummV5_C25_Error
ScummV5_C25_Flush__record_count_ok:
    .a8
    sta.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_C25_SELECTOR
    lda #$00
    sta.l SAME_SCUMM_C25_WORD_INDEX
ScummV5_C25_Flush__copy_history:
    .a8
    lda.l SAME_SCUMM_C25_WORD_INDEX
    cmp.l SAME_SCUMM_C25_SELECTOR
    bcs ScummV5_C25_Flush__dispatch
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    sta.l SAME_SCUMM_OPERAND
    inc
    clc
    adc.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_OPERAND
    tax
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C25_LAST_WORDS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_WORD_INDEX
    inc
    sta.l SAME_SCUMM_C25_WORD_INDEX
    bra ScummV5_C25_Flush__copy_history

ScummV5_C25_Flush__dispatch:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_WORDS
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_WORDS+2
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_WORDS+4
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_SCUMM_SCENARIO_C25_OBS_FLUSH_WORDS+6
    .endif
    rep #$30
    .a16
    .i16
    ; Dispatch the normalized word copied into LAST_WORDS above.  The queue
    ; record is byte-packed and its transient X/index state is not part of
    ; the semantic command ABI; using the normalized word also keeps every
    ; command family on the same width-safe path.
    lda.l SAME_SCUMM_C25_LAST_WORDS
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l SAME_SCUMM_SCENARIO_C25_DISPATCH_COMMAND
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_SCENARIO_C25_DISPATCH_OFFSET
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_DISPATCH_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS
    .endif
    .if SAME_BUILD_SCUMM_M21
    cmp #$010C
    bne ScummV5_C25_Flush__not_jump_hook
    jmp ScummV5_C25_Flush__jump_hook
ScummV5_C25_Flush__not_jump_hook:
    .a16
    .endif
    .if SAME_BUILD_SCUMM_M23C
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$D0
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    rep #$20
    .a16
    .endif
    cmp #$0110
    bne ScummV5_C25_Flush__not_clear_queue
    jmp ScummV5_C25_Flush__clear_imuse_queue
ScummV5_C25_Flush__not_clear_queue:
    ; Recognize this encoded command bytewise.  C25 records are byte-packed
    ; at the queue boundary, so command identity must not depend on the
    ; caller's accumulator-width annotation or a stale high byte.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS
    cmp #$07
    bne ScummV5_C25_Flush__not_authored_setup
    lda.l SAME_SCUMM_C25_LAST_WORDS+1
    cmp #$01
    bne ScummV5_C25_Flush__not_authored_setup
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$D2
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    rep #$20
    .a16
    .endif
    jmp ScummV5_C25_Flush__authored_setup
ScummV5_C25_Flush__not_authored_setup:
    rep #$20
    .a16
    ; The fixture-only marker above is observational, but it changes A.  All
    ; subsequent command-family comparisons must use the normalized queued
    ; command again rather than the marker byte.
    lda.l SAME_SCUMM_C25_LAST_WORDS
    .endif
    ; These three iMUSE setup commands are present in the authentic Fate
    ; room scripts.  They are meaningful to the desktop mixer, but have no
    ; independent SNES-side state in the bounded fallback.  Accept their
    ; canonical shapes and consume them without manufacturing an audio
    ; command; malformed records still fail closed below.
    .if !SAME_BUILD_M24RB
    cmp #$0101
    beq ScummV5_C25_Flush__fallback_3
    .a16
    cmp #$0106
    beq ScummV5_C25_Flush__fallback_3
    .a16
    cmp #$010D
    beq ScummV5_C25_Flush__fallback_4
    .a16
    .endif
    .if SAME_BUILD_M24RB
    cmp #$0101
    bne ScummV5_C25_Flush__not_m24rb_priority
    jmp ScummV5_C25_Flush__m24rb_simple
ScummV5_C25_Flush__not_m24rb_priority:
    .a16
    cmp #$0106
    bne ScummV5_C25_Flush__not_m24rb_speed
    jmp ScummV5_C25_Flush__m24rb_simple
ScummV5_C25_Flush__not_m24rb_speed:
    .a16
    cmp #$0107
    bne ScummV5_C25_Flush__not_m24rb_setup
    jmp ScummV5_C25_Flush__m24rb_setup
ScummV5_C25_Flush__not_m24rb_setup:
    .a16
    cmp #$010D
    bne ScummV5_C25_Flush__not_m24rb_fade
    jmp ScummV5_C25_Flush__m24rb_fade
ScummV5_C25_Flush__not_m24rb_fade:
    .a16
    cmp #$010E
    bne ScummV5_C25_Flush__not_m24rb_trigger
    jmp ScummV5_C25_Flush__m24rb_trigger
ScummV5_C25_Flush__not_m24rb_trigger:
    .a16
    cmp #$010F
    bne ScummV5_C25_Flush__not_m24rb_deferred
    jmp ScummV5_C25_Flush__m24rb_deferred
ScummV5_C25_Flush__not_m24rb_deferred:
    .a16
    .endif
    cmp #$0006
    bne ScummV5_C25_Flush__not_master_volume
    jmp ScummV5_C25_Flush__master_volume
ScummV5_C25_Flush__not_master_volume:
    .a16
    .if SAME_BUILD_SCUMM_M21
    cmp #$0108
    bne ScummV5_C25_Flush__not_encoded_start_sound
    jmp ScummV5_C25_Flush__start_sound
ScummV5_C25_Flush__not_encoded_start_sound:
    .a16
    .endif
    cmp #$0008
    bne ScummV5_C25_Flush__not_start_sound
    jmp ScummV5_C25_Flush__start_sound
ScummV5_C25_Flush__not_start_sound:
    .a16
    .if SAME_BUILD_SCUMM_M21
    cmp #$0109
    bne ScummV5_C25_Flush__not_encoded_stop_sound
    jmp ScummV5_C25_Flush__stop_sound
ScummV5_C25_Flush__not_encoded_stop_sound:
    .a16
    .endif
    cmp #$0009
    bne ScummV5_C25_Flush__not_stop_sound
    jmp ScummV5_C25_Flush__stop_sound
ScummV5_C25_Flush__not_stop_sound:
    .a16
    cmp #$000A
    beq ScummV5_C25_Flush__dispatch_stop_all
    cmp #$000B
    bne ScummV5_C25_Flush__dispatch_error
ScummV5_C25_Flush__dispatch_stop_all:
    jmp ScummV5_C25_Flush__stop_all
ScummV5_C25_Flush__dispatch_error:
    ; C25 command identity is a packed little-endian word.  Keep the
    ; compatibility trigger recognizable even when a preceding service helper
    ; returned with a byte-width accumulator; the normalized record remains
    ; the authority for the command, not the caller's transient P state.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS
    ; Keep the packed iMUSE queue-clear command recognizable even if a
    ; service helper returned through an unexpected accumulator width.  The
    ; canonical command is still validated by its normal handler below.
    cmp #$10
    bne ScummV5_C25_Flush__dispatch_error__not_0110_low
    lda.l SAME_SCUMM_C25_LAST_WORDS+1
    cmp #$01
    bne ScummV5_C25_Flush__dispatch_error__not_0110_low
    jmp ScummV5_C25_Flush__clear_imuse_queue
ScummV5_C25_Flush__dispatch_error__not_0110_low:
    rep #$30
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS
    ; The compatibility trigger is likewise recognized from the normalized
    ; packed word below; reloading restores the compare width after the
    ; bytewise probes above.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS
    cmp #$0E
    bne ScummV5_C25_Flush__dispatch_error__not_010E_low
    lda.l SAME_SCUMM_C25_LAST_WORDS+1
    cmp #$01
    beq ScummV5_C25_Flush__m24rb_trigger
ScummV5_C25_Flush__dispatch_error__not_010E_low:
    ; iMUSE command 2/3 are canonical compatibility no-ops in the v5
    ; desktop driver.  Fate emits command 3 during room-42 cutscene setup;
    ; it is a valid one-word command and must not be rejected as an unknown
    ; SNES service operation.
    rep #$30
    .a16
    cmp #$0002
    beq ScummV5_C25_Flush__compat_noop
    .a16
    cmp #$0003
    beq ScummV5_C25_Flush__compat_noop
    ; The comparisons above run in 16-bit accumulator mode.  The fixture
    ; diagnostic byte and the common error path are byte operations; `.a8`
    ; below only informs the assembler and does not change the 65816 mode.
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$08
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error

ScummV5_C25_Flush__compat_noop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    ; The queued record contains the command word itself. Commands 2/3
    ; have no operands, so their canonical record length is one word.
    cmp #$01
    bne ScummV5_C25_Flush__dispatch_error
    ; No audio packet is generated: these commands only update iMUSE's
    ; desktop-side control state, which has no independent SNES equivalent.
    jmp ScummV5_C25_Flush__command_done

.if !SAME_BUILD_M24RB
ScummV5_C25_Flush__fallback_3:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$03
    bne ScummV5_C25_Flush__fallback_error
    jmp ScummV5_C25_Flush__command_done

ScummV5_C25_Flush__fallback_4:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$04
    bne ScummV5_C25_Flush__fallback_error
    jmp ScummV5_C25_Flush__command_done

ScummV5_C25_Flush__fallback_error:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$09
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
.endif

.if SAME_BUILD_M24RB
ScummV5_C25_Flush__m24rb_simple:
    ; Priority/speed are retained in the source-bound compiled arrangement.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$03
    beq ScummV5_C25_Flush__m24rb_simple_valid
    ; Full Fate room-42 setup also emits the canonical four-word form
    ; ($0101,$0101,$008C,$0001).  The bounded SNES compatibility path
    ; consumes the command record as a whole; its trailing source control
    ; word has no separate TAD-side state.
    cmp #$04
    beq ScummV5_C25_Flush__m24rb_simple_valid
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_simple_valid:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    cmp #$0100
    bcc ScummV5_C25_Flush__m24rb_simple_range_ok
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_simple_range_ok:
    sep #$20
    .a8
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_setup:
    ; Fate's room-82 setup uses iMUSE command $0107 as a bounded five-word
    ; control record.  Its desktop mixer effect has no independent SNES
    ; state, but the complete authored record must be consumed before the
    ; subsequent $010E/$010F controls are dispatched.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$05
    beq ScummV5_C25_Flush__m24rb_setup_valid
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_setup_valid:
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_trigger:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$E1
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$03
    beq ScummV5_C25_Flush__m24rb_trigger_valid
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$E2
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_trigger_valid:
    rep #$20
    .a16
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$E3
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    rep #$20
    .a16
    .endif
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    cmp #$0100
    bcc ScummV5_C25_Flush__m24rb_trigger_range_ok
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_trigger_range_ok:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    sta.l SAME_M24RB_TRIGGER_MARKER
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_deferred:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    bcs ScummV5_C25_Flush__m24rb_deferred_count_ok
    jmp ScummV5_C25_Flush__m24rb_error
ScummV5_C25_Flush__m24rb_deferred_count_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp #$FFFF
    beq ScummV5_C25_Flush__m24rb_deferred_done16
    sep #$20
    .a8
    lda.l SAME_M24RB_DEFERRED_COUNT
    inc
    sta.l SAME_M24RB_DEFERRED_COUNT
    ; A nested start has a sound operand only in the canonical three-word form.
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$03
    bne ScummV5_C25_Flush__m24rb_deferred_done
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp #$0008
    bne ScummV5_C25_Flush__m24rb_deferred_done16
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    and #$00FF
    cmp #SAME_M24RB_LAYER_SOUND
    bne ScummV5_C25_Flush__m24rb_deferred_done16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_M24RB_LOGICAL82_STATE
    lda #SAME_M24RB_LAYER_SOUND
    jsl ScummV5_C25_FarCall_SetSfxActive
ScummV5_C25_Flush__m24rb_deferred_done:
    .a8
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_deferred_done16:
    sep #$20
    .a8
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_fade:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$04
    bne ScummV5_C25_Flush__m24rb_error
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    cmp #$0080
    bcs ScummV5_C25_Flush__m24rb_error
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp #SAME_M24RB_LAYER_SOUND
    beq ScummV5_C25_Flush__m24rb_fade_layer
    sep #$20
    .a8
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_fade_layer:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    beq ScummV5_C25_Flush__m24rb_fade_zero
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_fade_zero:
    .a8
    lda #$03
    sta.l SAME_M24RB_LOGICAL82_STATE
    lda #$02
    jsr Same_M24RA_QueueRequest
    bcs ScummV5_C25_Flush__m24rb_error
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__m24rb_error:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$0A
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
.endif

.if SAME_BUILD_SCUMM_M23C
ScummV5_C25_Flush__authored_setup:
    ; Authored Fate setup uses the five-word iMUSE $0107 control record.
    ; Keep the complete bounded record consumed even though its desktop
    ; mixer effect has no separate SNES-side state.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$05
    beq ScummV5_C25_Flush__authored_setup_valid
    jml ScummV5_C25_Error
ScummV5_C25_Flush__authored_setup_valid:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sep #$20
    .a8
    lda #$D3
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jmp ScummV5_C25_Flush__command_done

ScummV5_C25_Flush__clear_imuse_queue:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$D4
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$01
    bne ScummV5_C25_Flush__clear_imuse_error
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$D5
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    lda.l SAME_SCUMM_M23C_CLEAR_QUEUE_COUNT
    inc
    sta.l SAME_SCUMM_M23C_CLEAR_QUEUE_COUNT
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__clear_imuse_error:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$D6
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
.endif

ScummV5_C25_Flush__master_volume:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__master_count_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$0C
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_C25_Flush__master_count_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp #$0080
    bcc ScummV5_C25_Flush__master_range_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$0D
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_C25_Flush__master_range_ok:
    asl
    beq ScummV5_C25_Flush__master_scaled
    inc
ScummV5_C25_Flush__master_scaled:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda #$0000
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MASTER_VOLUME
    jsl ScummV5_C25_FarCall_EmitAudio
    bcs ScummV5_C25_Flush__master_service_error
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__master_service_error:
    jml ScummV5_C25_ServiceError

ScummV5_C25_Flush__start_sound:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__start_count_ok
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$0E
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_C25_Flush__start_count_ok:
    .if SAME_BUILD_SCUMM_M21
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    jsl ScummV5_C25_FarCall_HasRoutes
    bcs ScummV5_C25_Flush__start_unrouted
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_SCUMM_C25_SELECTOR
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0000
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    jsl ScummV5_C25_FarCall_MapRoute
    bcc ScummV5_C25_Flush__start_route_resolved
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$0F
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_SITE
    .endif
    jml ScummV5_C25_Error
ScummV5_C25_Flush__start_route_resolved:
    .a8
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    rep #$20
    .a16
    bra ScummV5_C25_Flush__start_emit
ScummV5_C25_Flush__start_unrouted:
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_PLAY
    sta.l SAME_SCUMM_C25_SELECTOR
    rep #$20
    .a16
    lda #$0080
    sta.l SAME_SCUMM_CONDITION
ScummV5_C25_Flush__start_emit:
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__start_service_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__start_service_ok:
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    cmp #SAME_AUDIO_OP_MUSIC_PLAY
    beq ScummV5_C25_Flush__start_is_music
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__start_is_music:
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    lda #$00
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    lda #$01
    jsr ScummV5_M21_RecordRoute
    lda.l SAME_SCUMM_M21_ROUTE_COUNT
    inc
    sta.l SAME_SCUMM_M21_ROUTE_COUNT
    lda #$03
    jsr ScummV5_M21_RecordRoute
    .if SAME_BUILD_SCUMM_M22
    lda.l SAME_SCUMM_M22_CUE_GENERATION
    inc
    bne ScummV5_C25_Flush__m22_generation_ok
    inc
ScummV5_C25_Flush__m22_generation_ok:
    .a8
    sta.l SAME_SCUMM_M22_CUE_GENERATION
    lda #$00
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CONSUMPTION
    .endif
    jmp ScummV5_C25_Flush__command_done
    .else
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_OPERAND
    lda #$0080
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_PLAY
    jsl ScummV5_C25_FarCall_EmitAudio
    bcs ScummV5_C25_Flush__sfx_play_error
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__sfx_play_error:
    jml ScummV5_C25_ServiceError
    .endif

.if SAME_BUILD_SCUMM_M21
ScummV5_C25_Flush__jump_hook:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$04
    beq ScummV5_C25_Flush__jump_count_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__jump_count_ok:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    beq ScummV5_C25_Flush__jump_class_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__jump_class_ok:
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    and #$FF00
    beq ScummV5_C25_Flush__jump_sound_width_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__jump_sound_width_ok:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp.l SAME_SCUMM_ACTIVE_MUSIC
    beq ScummV5_C25_Flush__jump_owner_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__jump_owner_ok:
    .a8
    .if SAME_BUILD_M24RB
    ; The bounded composite has already consumed hook14/hook7 provenance and
    ; contains the accepted hook8 continuation.  Record the logical hook; do
    ; not issue M22's selector command (TAD command 22 is the accepted async
    ; transition primitive in this build).
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    lda #$01
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    lda #$02
    jsr ScummV5_M21_RecordRoute
    jmp ScummV5_C25_Flush__command_done
    .endif
    .if SAME_BUILD_SCUMM_M22
    ; Query the generated source-bound plan before treating a hook as M21's
    ; immediate compiled-route replacement. Generic code contains no cue,
    ; room, hook, or final-song constants.
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0+1
    lda.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    lda.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1+1
    jsr Same_Music_MapSectionPlan
    bcs ScummV5_C25_Flush__jump_not_section
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0+1
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1+1
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    lda.l SAME_SCUMM_M22_CUE_GENERATION
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
    lda #$01
    sta.l SAME_SCUMM_M22_CONSUMPTION
    lda.l SAME_SCUMM_M22_ARM_COUNT
    inc
    sta.l SAME_SCUMM_M22_ARM_COUNT
    rep #$20
    .a16
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MUSIC_SECTION_SELECT
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__m22_section_emitted
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__m22_section_emitted:
    .a8
    lda #$02
    jsr ScummV5_M21_RecordRoute
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__jump_not_section:
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    .endif
    sta.l SAME_SCUMM_OPERAND
    lda #$00
    sta.l SAME_SCUMM_OPERAND+1
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_SCUMM_CONDITION
    lda #$01
    sta.l SAME_SCUMM_CONDITION+1
    jsl ScummV5_C25_FarCall_StageEngine
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    jsl ScummV5_C25_FarCall_MapRoute
    bcc ScummV5_C25_Flush__jump_route_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__jump_route_ok:
    .a8
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__jump_service_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__jump_service_ok:
    .a8
    lda #$01
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    lda.l SAME_SCUMM_C25_LAST_WORDS+6
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    lda #$02
    jsr ScummV5_M21_RecordRoute
    lda.l SAME_SCUMM_M21_ROUTE_COUNT
    inc
    sta.l SAME_SCUMM_M21_ROUTE_COUNT
    lda #$03
    jsr ScummV5_M21_RecordRoute
    .if SAME_BUILD_SCUMM_M22
    lda #$01
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    lda #$00
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_CONSUMPTION
    .endif
    jmp ScummV5_C25_Flush__command_done
.endif

ScummV5_C25_Flush__stop_sound:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$02
    beq ScummV5_C25_Flush__stop_count_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__stop_count_ok:
    .if SAME_BUILD_SCUMM_M21
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    cmp.l SAME_SCUMM_ACTIVE_MUSIC
    bne ScummV5_C25_Flush__stop_unrouted
    lda #SAME_AUDIO_OP_MUSIC_STOP
    sta.l SAME_SCUMM_C25_SELECTOR
    bra ScummV5_C25_Flush__stop_prepare
ScummV5_C25_Flush__stop_unrouted:
    .a8
    lda #SAME_AUDIO_OP_SFX_STOP
    sta.l SAME_SCUMM_C25_SELECTOR
ScummV5_C25_Flush__stop_prepare:
    .endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_OPERAND
    lda #$0000
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M21
    lda.l SAME_SCUMM_C25_SELECTOR
    .else
    lda #SAME_AUDIO_OP_SFX_STOP
    .endif
    jsl ScummV5_C25_FarCall_EmitAudio
    .if SAME_BUILD_SCUMM_M21
    bcc ScummV5_C25_Flush__stop_service_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_service_ok:
    .a8
    lda.l SAME_SCUMM_C25_SELECTOR
    cmp #SAME_AUDIO_OP_MUSIC_STOP
    beq ScummV5_C25_Flush__stop_is_music
    jmp ScummV5_C25_Flush__command_done
ScummV5_C25_Flush__stop_is_music:
    .a8
    lda #$04
    jsr ScummV5_M21_RecordRoute
    lda #$00
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    .if SAME_BUILD_SCUMM_M22
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
    .endif
    bcc ScummV5_C25_Flush__command_done
    jml ScummV5_C25_ServiceError
    .else
    bcc ScummV5_C25_Flush__command_done
    jml ScummV5_C25_ServiceError
    .endif

ScummV5_C25_Flush__stop_all:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    cmp #$01
    beq ScummV5_C25_Flush__stop_all_count_ok
    jml ScummV5_C25_Error
ScummV5_C25_Flush__stop_all_count_ok:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_MUSIC_STOP
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__stop_all_music_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_all_music_ok:
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SFX_STOP
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__stop_all_sfx_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_all_sfx_ok:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_SPEECH_STOP
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__stop_all_speech_ok
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__stop_all_speech_ok:
    .a8
    .if SAME_BUILD_SCUMM_M21
    lda.l SAME_SCUMM_ACTIVE_MUSIC
    beq ScummV5_C25_Flush__stop_all_route_clear
    lda #$04
    jsr ScummV5_M21_RecordRoute
ScummV5_C25_Flush__stop_all_route_clear:
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    .endif

ScummV5_C25_Flush__command_done:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    inc
    sta.l SAME_SCUMM_C25_COMMAND_INDEX
    jmp ScummV5_C25_Flush__next_command

ScummV5_C25_Flush__complete:
    .a8
    lda.l SAME_SCUMM_C25_FLUSH_COUNT
    inc
    sta.l SAME_SCUMM_C25_FLUSH_COUNT
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_CONDITION
    sep #$20
    .a8
    lda #SAME_AUDIO_OP_FLUSH
    jsl ScummV5_C25_FarCall_EmitAudio
    bcc ScummV5_C25_Flush__complete_emitted
    jml ScummV5_C25_ServiceError
ScummV5_C25_Flush__complete_emitted:
    .a8
    .if SAME_BUILD_M24RB
    lda.l SAME_M24RB_FRAME_END_ACTIVE
    beq ScummV5_C25_Flush__not_frame_end_return
    lda #$00
    sta.l SAME_M24RB_FRAME_END_ACTIVE
    .if SAME_BUILD_M24RB && !SAME_BUILD_SCUMM_M20 && !SAME_BUILD_SCUMM_M21 && !SAME_BUILD_SCUMM_M22
    rtl
    .else
    rts
    .endif
ScummV5_C25_Flush__not_frame_end_return:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M23C
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    beq ScummV5_C25_Flush__m23c_target
    cmp #SCUMM_M23C_SOURCE_ROOM
    bne ScummV5_C25_Flush__complete_continue
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    ; Authentic interactive bytecode immediately follows this batch boundary
    ; with loadRoomWithEgo; do not hand control to the historical M23C driver.
    jmp ScummV5_C25_Flush__complete_continue
    .else
    lda #$01
    sta.l SAME_SCUMM_M23C_ROOM49_READY
    sta.l SAME_SCUMM_M23C_PHASE
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
    .endif
ScummV5_C25_Flush__m23c_target:
    .a8
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_M23C_AUTH_FLUSH_QUEUE_COUNT
    lda #$01
    sta.l SAME_SCUMM_M23C_AUTH_FLUSH_SEEN
    .if SAME_BUILD_M24RB
    lda #$00
    sta.l SAME_SCUMM_M23A_HOLD
    lda #$07
    sta.l SAME_SCUMM_M23C_PHASE
    jml ScummV5_Engine_Frame__next
    .else
    sta.l SAME_SCUMM_M23A_HOLD
    lda #$03
    sta.l SAME_SCUMM_M23C_PHASE
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
    .endif
    .endif
    .if SAME_BUILD_SCUMM_M23B
    lda.l SAME_SCUMM_M23B_HOLD_AFTER_FLUSH
    beq ScummV5_C25_Flush__complete_continue
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_M23B_AUTH_FLUSH_QUEUE_COUNT
    lda #$01
    sta.l SAME_SCUMM_M23B_AUTH_FLUSH_SEEN
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jml ScummV5_Engine_Frame__complete_success
ScummV5_C25_Flush__complete_continue:
    .a8
    .endif
    jml ScummV5_Engine_Frame__next

.if SAME_BUILD_M24RB && !SAME_BUILD_SCUMM_M20 && !SAME_BUILD_SCUMM_M21 && !SAME_BUILD_SCUMM_M22
    .bank 0
    .org ScummV5_C25_Flush_Bank0_Resume
ScummV5_C25_FarCall_EmitAudio:
    jsr ScummV5_C25_EmitAudio
    rtl
ScummV5_C25_FarCall_SetSfxActive:
    jsr ScummV5_M23C_SetSfxActive
    rtl
    .if SAME_BUILD_SCUMM_M21
ScummV5_C25_FarCall_HasRoutes:
    jsr Same_Tad_HasRoutes
    rtl
ScummV5_C25_FarCall_MapRoute:
    jsr Same_Tad_MapRoute
    rtl
    .endif
ScummV5_C25_FarCall_StageEngine:
    jsr Same_Event_StageEngine
    rtl
.endif

.if SAME_BUILD_SCUMM_M22
; Consume only the token emitted by the compiled score boundary and only for
; the cue generation that armed it. Selection already occurred on the S-SMP;
; this records logical one-shot ownership without estimating musical time.
ScummV5_M22_ConsumeBoundary:
    sep #$20
    .a8
    lda.l SAME_SCUMM_M22_CONSUMPTION
    cmp #$01
    bne ScummV5_M22_ConsumeBoundary__done
    lda.l SAME_SCUMM_M22_GENERATION_AT_ARM
    cmp.l SAME_SCUMM_M22_CUE_GENERATION
    bne ScummV5_M22_ConsumeBoundary__stale
    lda.l SAME_TAD_BOUNDARY_TOKEN
    beq ScummV5_M22_ConsumeBoundary__done
    cmp.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    bne ScummV5_M22_ConsumeBoundary__done
    lda.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    lda #$00
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    lda #$02
    sta.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    lda.l SAME_SCUMM_M22_CONSUME_COUNT
    inc
    sta.l SAME_SCUMM_M22_CONSUME_COUNT
    rts
ScummV5_M22_ConsumeBoundary__stale:
    .a8
    lda #$00
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_CONSUMPTION
    lda.l SAME_SCUMM_M22_STALE_COUNT
    inc
    sta.l SAME_SCUMM_M22_STALE_COUNT
ScummV5_M22_ConsumeBoundary__done:
    .a8
    rts
.endif

; Input: A8 normalized audio opcode, operand/condition are arg0/arg1.
ScummV5_C25_EmitAudio:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C25_SELECTOR
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda.l SAME_SCUMM_C25_SELECTOR
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    ; Contract for every C25 caller: preserve the queue result in carry and
    ; return with the accumulator in the handler's declared 8-bit width.
    ; Same_Event_Push is a word-mode service call.  C25 callers immediately
    ; execute byte opcodes regardless of the optional M21 music feature, so
    ; this is an ABI restoration, not M21-specific cleanup.
    sep #$20
    .a8
    rts

.if SAME_BUILD_SCUMM_M21
; A8 operation; the remaining columns snapshot current logical route state.
ScummV5_M21_RecordRoute:
    .a8
    .i16
    ; Preserve the caller's index register: C25 owns X as its queued-command
    ; record offset across helper calls.
    phx
    pha
    lda.l SAME_SCUMM_M21_HISTORY_COUNT
    cmp #SAME_SCUMM_M21_HISTORY_CAPACITY
    bcs ScummV5_M21_RecordRoute__full
    tax
    pla
    sta.l SAME_SCUMM_M21_HISTORY_OP,x
    lda.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_M21_HISTORY_KIND,x
    lda.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_SCUMM_M21_HISTORY_VALUE,x
    lda.l SAME_SCUMM_MUSIC_ROUTE_SONG
    sta.l SAME_SCUMM_M21_HISTORY_SONG,x
    lda.l SAME_SCUMM_ACTIVE_MUSIC
    sta.l SAME_SCUMM_M21_HISTORY_LOGICAL,x
    lda.l SAME_SCUMM_M21_HISTORY_COUNT
    inc
    sta.l SAME_SCUMM_M21_HISTORY_COUNT
    plx
    clc
    rts
ScummV5_M21_RecordRoute__full:
    pla
    plx
    clc
    rts
.endif

ScummV5_C25_ServiceError:
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
    .if SAME_BUILD_SCUMM_M23B
    pha
    lda #$03
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    pla
    .endif
    jsr ScummV5_SetError
    sec
    jmp ScummV5_Engine_Frame__error

ScummV5_C25_Error:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Preserve the complete failing queue record.  The last SCUMM opcode can
    ; belong to the next loop iteration, so C25 diagnostics must identify the
    ; record actually being flushed rather than infer its producer from PC.
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+1
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+2
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+3
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+4
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+5
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+6
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+7
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+8
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+9
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+10
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+11
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+12
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+13
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+14
    inx
    lda.l SAME_SCUMM_C25_QUEUE,x
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE_RECORD+15
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda #$C2
    sta.l SAME_SCUMM_SCENARIO_C25_ENTRY
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    sta.l SAME_SCUMM_SCENARIO_C25_STABLE_INDEX
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_SCENARIO_C25_STABLE_OFFSET
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_STABLE_PENDING
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_STABLE_QUEUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_QUEUE+1
    sta.l SAME_SCUMM_SCENARIO_C25_STABLE_WORD
    sep #$20
    .a8
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_SCENARIO_LAST_OP_PROGRAM
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_LAST_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENARIO_LAST_OP_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_LAST_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENARIO_LAST_OP_OPCODE
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_LAST_OPCODE
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_OPCODE
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_C25_LAST_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_COUNT
    lda.l SAME_SCUMM_C25_COMMAND_INDEX
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_INDEX2
    lda.l SAME_SCUMM_C25_RECORD_OFFSET
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_OFFSET2
    lda.l SAME_SCUMM_C25_PENDING_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_PENDING2
    lda.l SAME_SCUMM_C25_QUEUE_COUNT
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_QUEUE2
    rep #$20
    .a16
    lda.l SAME_SCUMM_C25_QUEUE+1
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD2_0
    lda.l SAME_SCUMM_C25_LAST_WORDS
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD0
    lda.l SAME_SCUMM_C25_LAST_WORDS+2
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD1
    lda.l SAME_SCUMM_C25_LAST_WORDS+4
    sta.l SAME_SCUMM_SCENARIO_C25_ERROR_WORD2
    sep #$20
    .a8
    .endif
    lda #SCUMM_ERR_SOUND_KLUDGE
    jsr ScummV5_SetError
    sec
    jmp ScummV5_Engine_Frame__error

.if SAME_BUILD_SCUMM_M20
; Versioned compiled-music save subrecord. It contains logical SCUMM state and
; immutable catalog/source identities only. The advisory position at +$10 is
; deliberately not honored by cold restore.
SCUMM_M20_PAYLOAD = SAME_SAVE_STAGING+$58
SCUMM_M20_POLICY_RESTART = $0001

ScummV5_M20_SaveCompiledMusic:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
ScummV5_M20_SaveCompiledMusic__magic:
    .a8
    .i16
    lda.l ScummV5_M20_Magic,x
    sta.l SCUMM_M20_PAYLOAD,x
    inx
    cpx #$0008
    bcc ScummV5_M20_SaveCompiledMusic__magic
    rep #$20
    .a16
    .if SAME_BUILD_SCUMM_M21
    .if SAME_BUILD_SCUMM_M22
    lda #$0003
    .else
    lda #$0002
    .endif
    .else
    lda #$0001
    .endif
    sta.l SCUMM_M20_PAYLOAD+$08
    lda #SCUMM_M20_POLICY_RESTART
    sta.l SCUMM_M20_PAYLOAD+$0A
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTIVE_MUSIC
    sta.l SCUMM_M20_PAYLOAD+$0C
    beq ScummV5_M20_SaveCompiledMusic__stopped
    lda #$01
ScummV5_M20_SaveCompiledMusic__stopped:
    .a8
    sta.l SCUMM_M20_PAYLOAD+$0D
    .if SAME_BUILD_SCUMM_M21
    lda.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SCUMM_M20_PAYLOAD+$0E
    lda.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SCUMM_M20_PAYLOAD+$0F
    .else
    lda #$00
    sta.l SCUMM_M20_PAYLOAD+$0E
    sta.l SCUMM_M20_PAYLOAD+$0F
    .endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_MUSIC_POSITION
    sta.l SCUMM_M20_PAYLOAD+$10
    lda.l SAME_SCUMM_MUSIC_POSITION+2
    sta.l SCUMM_M20_PAYLOAD+$12
    sep #$20
    .a8
    ldx #$0000
ScummV5_M20_SaveCompiledMusic__identity:
    .a8
    .i16
    lda.l Same_Save_CatalogIdentity,x
    sta.l SCUMM_M20_PAYLOAD+$14,x
    lda.l Same_Save_SourceIdentity,x
    sta.l SCUMM_M20_PAYLOAD+$34,x
    inx
    cpx #$0020
    bcc ScummV5_M20_SaveCompiledMusic__identity
    .if SAME_BUILD_SCUMM_M21
    jsr ScummV5_M21_FindSavedRoute
    bcc ScummV5_M20_SaveCompiledMusic__route_found
    jmp ScummV5_M20_SaveCompiledMusic__route_bad
ScummV5_M20_SaveCompiledMusic__route_found:
    .a8
    ; X is the route index; multiply by 32 for the identity byte offset.
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    tay
    ldx #$0000
    sep #$20
    .a8
    phb
    phk
    plb
ScummV5_M20_SaveCompiledMusic__route_identity:
    .a8
    .i16
    lda.w Same_Save_RouteIdentities,y
    sta.l SCUMM_M20_PAYLOAD+$54,x
    inx
    iny
    cpx #$0020
    bcc ScummV5_M20_SaveCompiledMusic__route_identity
    plb
    .endif
    .if SAME_BUILD_SCUMM_M22
    lda.l SAME_SCUMM_M22_ROUTE_HISTORY
    beq ScummV5_M20_SaveCompiledMusic__m22_done
    sta.l SCUMM_M20_PAYLOAD+$74
    lda.l SAME_SCUMM_M22_CURRENT_SECTION
    sta.l SCUMM_M20_PAYLOAD+$75
    lda.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SCUMM_M20_PAYLOAD+$76
    lda.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SCUMM_M20_PAYLOAD+$77
    lda.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SCUMM_M20_PAYLOAD+$78
    lda.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SCUMM_M20_PAYLOAD+$79
    lda.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    beq ScummV5_M20_SaveCompiledMusic__m22_selector_stored
    lda #$01
ScummV5_M20_SaveCompiledMusic__m22_selector_stored:
    .a8
    sta.l SCUMM_M20_PAYLOAD+$7A
    ldx #$0000
ScummV5_M20_SaveCompiledMusic__m22_identity:
    .a8
    .i16
    lda.l Same_Save_SectionPlanIdentity,x
    sta.l SCUMM_M20_PAYLOAD+$7C,x
    sta.l SCUMM_M20_PAYLOAD+$BC,x
    lda.l Same_Save_InstrumentBankIdentity,x
    sta.l SCUMM_M20_PAYLOAD+$9C,x
    lda.l Same_Save_RouteHistoryIdentity,x
    sta.l SCUMM_M20_PAYLOAD+$DC,x
    inx
    cpx #$0020
    bcc ScummV5_M20_SaveCompiledMusic__m22_identity
ScummV5_M20_SaveCompiledMusic__m22_done:
    .a8
    .endif
    clc
    rts
    .if SAME_BUILD_SCUMM_M21
ScummV5_M20_SaveCompiledMusic__route_bad:
    sec
    rts
    .endif

ScummV5_M20_ValidateCompiledMusic:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
ScummV5_M20_ValidateCompiledMusic__magic:
    .a8
    .i16
    lda.l SCUMM_M20_PAYLOAD,x
    cmp.l ScummV5_M20_Magic,x
    beq ScummV5_M20_ValidateCompiledMusic__magic_ok
    jmp ScummV5_M20_ValidateCompiledMusic__bad
ScummV5_M20_ValidateCompiledMusic__magic_ok:
    .a8
    .i16
    inx
    cpx #$0008
    bcc ScummV5_M20_ValidateCompiledMusic__magic
    rep #$20
    .a16
    lda.l SCUMM_M20_PAYLOAD+$08
    .if SAME_BUILD_SCUMM_M21
    .if SAME_BUILD_SCUMM_M22
    cmp #$0003
    .else
    cmp #$0002
    .endif
    .else
    cmp #$0001
    .endif
    bne ScummV5_M20_ValidateCompiledMusic__bad16_near
    lda.l SCUMM_M20_PAYLOAD+$0A
    cmp #SCUMM_M20_POLICY_RESTART
    bne ScummV5_M20_ValidateCompiledMusic__bad16_near
    .if !SAME_BUILD_SCUMM_M21
    lda.l SCUMM_M20_PAYLOAD+$0E
    bne ScummV5_M20_ValidateCompiledMusic__bad16_near
    .endif
    sep #$20
    .a8
    lda.l SCUMM_M20_PAYLOAD+$0D
    cmp #$02
    bcs ScummV5_M20_ValidateCompiledMusic__bad_early
    cmp #$01
    beq ScummV5_M20_ValidateCompiledMusic__running
    lda.l SCUMM_M20_PAYLOAD+$0C
    bne ScummV5_M20_ValidateCompiledMusic__bad_early
    bra ScummV5_M20_ValidateCompiledMusic__identity_start
ScummV5_M20_ValidateCompiledMusic__running:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$0C
    .if SAME_BUILD_SCUMM_M21
    cmp #SAME_SAVE_LOGICAL_SOUND
    .else
    cmp #$9A
    .endif
    bne ScummV5_M20_ValidateCompiledMusic__bad_early
ScummV5_M20_ValidateCompiledMusic__identity_start:
    .a8
    ldx #$0000
ScummV5_M20_ValidateCompiledMusic__identity:
    .a8
    .i16
    lda.l SCUMM_M20_PAYLOAD+$14,x
    cmp.l Same_Save_CatalogIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad_early
    lda.l SCUMM_M20_PAYLOAD+$34,x
    cmp.l Same_Save_SourceIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad_early
    inx
    cpx #$0020
    bcc ScummV5_M20_ValidateCompiledMusic__identity
    bra ScummV5_M20_ValidateCompiledMusic__identity_checked
ScummV5_M20_ValidateCompiledMusic__bad16_near:
    sep #$20
    .a8
ScummV5_M20_ValidateCompiledMusic__bad_early:
    jmp ScummV5_M20_ValidateCompiledMusic__bad
ScummV5_M20_ValidateCompiledMusic__identity_checked:
    .a8
    .if SAME_BUILD_SCUMM_M21
    jsr ScummV5_M21_FindPayloadRoute
    bcs ScummV5_M20_ValidateCompiledMusic__bad_early
    rep #$20
    .a16
    txa
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    tay
    ldx #$0000
    sep #$20
    .a8
    phb
    phk
    plb
ScummV5_M20_ValidateCompiledMusic__route_identity:
    .a8
    .i16
    lda.l SCUMM_M20_PAYLOAD+$54,x
    cmp.w Same_Save_RouteIdentities,y
    bne ScummV5_M20_ValidateCompiledMusic__route_identity_bad
    inx
    iny
    cpx #$0020
    bcc ScummV5_M20_ValidateCompiledMusic__route_identity
    plb
    bra ScummV5_M20_ValidateCompiledMusic__route_identity_done
ScummV5_M20_ValidateCompiledMusic__route_identity_bad:
    .a8
    plb
    jmp ScummV5_M20_ValidateCompiledMusic__bad
ScummV5_M20_ValidateCompiledMusic__route_identity_done:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M22
    lda.l SCUMM_M20_PAYLOAD+$74
    bne ScummV5_M20_ValidateCompiledMusic__m22_nonzero
    jmp ScummV5_M20_ValidateCompiledMusic__m22_zero
ScummV5_M20_ValidateCompiledMusic__m22_nonzero:
    .a8
    cmp #$03
    bcc ScummV5_M20_ValidateCompiledMusic__m22_history_ok
    jmp ScummV5_M20_ValidateCompiledMusic__bad
ScummV5_M20_ValidateCompiledMusic__m22_history_ok:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$0E
    cmp #SAME_SAVE_SECTION_ROUTE_KIND
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$0F
    cmp #SAME_SAVE_SECTION_ROUTE_VALUE
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$75
    cmp #$01
    beq ScummV5_M20_ValidateCompiledMusic__m22_section_ok
    cmp #$02
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
ScummV5_M20_ValidateCompiledMusic__m22_section_ok:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$79
    cmp #$03
    bcs ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$7A
    cmp #$02
    bcs ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$7B
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    ; Three accepted logical forms: no hook, armed, or already consumed.
    lda.l SCUMM_M20_PAYLOAD+$79
    beq ScummV5_M20_ValidateCompiledMusic__m22_no_hook
    cmp #$01
    beq ScummV5_M20_ValidateCompiledMusic__m22_armed
    lda.l SCUMM_M20_PAYLOAD+$76
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$75
    cmp #$02
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    bra ScummV5_M20_ValidateCompiledMusic__m22_selected
ScummV5_M20_ValidateCompiledMusic__m22_armed:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$76
    cmp #SAME_SAVE_SECTION_HOOK_VALUE
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$75
    cmp #$01
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
ScummV5_M20_ValidateCompiledMusic__m22_selected:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$77
    cmp #SAME_SAVE_SECTION_BOUNDARY_TOKEN
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$78
    cmp #$02
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    lda.l SCUMM_M20_PAYLOAD+$7A
    cmp #$01
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
    bra ScummV5_M20_ValidateCompiledMusic__m22_identities
ScummV5_M20_ValidateCompiledMusic__m22_no_hook:
    lda.l SCUMM_M20_PAYLOAD+$76
    ora.l SCUMM_M20_PAYLOAD+$78
    ora.l SCUMM_M20_PAYLOAD+$7A
    bne ScummV5_M20_ValidateCompiledMusic__m22_bad_near
ScummV5_M20_ValidateCompiledMusic__m22_identities:
    .a8
    bra ScummV5_M20_ValidateCompiledMusic__m22_identity_begin
ScummV5_M20_ValidateCompiledMusic__m22_bad_near:
    jmp ScummV5_M20_ValidateCompiledMusic__bad
ScummV5_M20_ValidateCompiledMusic__m22_identity_begin:
    .a8
    ldx #$0000
ScummV5_M20_ValidateCompiledMusic__m22_identity:
    .a8
    .i16
    lda.l SCUMM_M20_PAYLOAD+$7C,x
    cmp.l Same_Save_SectionPlanIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad
    lda.l SCUMM_M20_PAYLOAD+$9C,x
    cmp.l Same_Save_InstrumentBankIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad
    lda.l SCUMM_M20_PAYLOAD+$BC,x
    cmp.l Same_Save_SectionPlanIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad
    lda.l SCUMM_M20_PAYLOAD+$DC,x
    cmp.l Same_Save_RouteHistoryIdentity,x
    bne ScummV5_M20_ValidateCompiledMusic__bad
    inx
    cpx #$0020
    bcc ScummV5_M20_ValidateCompiledMusic__m22_identity
    bra ScummV5_M20_ValidateCompiledMusic__m22_done
ScummV5_M20_ValidateCompiledMusic__m22_zero:
    .a8
    ldx #$0000
ScummV5_M20_ValidateCompiledMusic__m22_zero_loop:
    .a8
    lda.l SCUMM_M20_PAYLOAD+$74,x
    bne ScummV5_M20_ValidateCompiledMusic__bad
    inx
    cpx #$0088
    bcc ScummV5_M20_ValidateCompiledMusic__m22_zero_loop
ScummV5_M20_ValidateCompiledMusic__m22_done:
    .a8
    .endif
    clc
    rts
ScummV5_M20_ValidateCompiledMusic__bad16:
    sep #$20
    .a8
ScummV5_M20_ValidateCompiledMusic__bad:
    sec
    rts

ScummV5_M20_ApplyCompiledMusic:
    rep #$20
    .a16
    lda.l SAME_EVENT_COUNT
    .if SAME_BUILD_SCUMM_M22
    cmp #SAME_EVENT_CAPACITY-2
    .else
    cmp #SAME_EVENT_CAPACITY-1
    .endif
    bcc ScummV5_M20_ApplyCompiledMusic__space
    sec
    rts
ScummV5_M20_ApplyCompiledMusic__space:
    .a16
    .if SAME_BUILD_SCUMM_M21
    ; Resolve the validated route before queuing stop/play or changing logical
    ; ownership.  Any impossible catalog mismatch therefore remains fully
    ; transactional.
    lda.l SCUMM_M20_PAYLOAD+$0D
    and #$00FF
    beq ScummV5_M20_ApplyCompiledMusic__route_not_running
    lda.l SCUMM_M20_PAYLOAD+$0C
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda.l SCUMM_M20_PAYLOAD+$0E
    and #$00FF
    xba
    sta.l SAME_SCUMM_CONDITION
    lda.l SCUMM_M20_PAYLOAD+$0F
    and #$00FF
    ora.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_CONDITION
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    sep #$20
    .a8
    lda.l SCUMM_M20_PAYLOAD+$0C
    jsr Same_Tad_MapRoute
    bcc ScummV5_M20_ApplyCompiledMusic__route_resolved
    jmp ScummV5_M20_ApplyCompiledMusic__failed
ScummV5_M20_ApplyCompiledMusic__route_resolved:
    .a8
    sta.l SAME_SCUMM_C25_SELECTOR
ScummV5_M20_ApplyCompiledMusic__route_not_running:
    sep #$20
    .a8
    .endif
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    jsr Same_Event_Push
    bcc ScummV5_M20_ApplyCompiledMusic__stop_queued
    jmp ScummV5_M20_ApplyCompiledMusic__failed
ScummV5_M20_ApplyCompiledMusic__stop_queued:
    .a8
    sep #$20
    .a8
    lda.l SCUMM_M20_PAYLOAD+$0D
    bne ScummV5_M20_ApplyCompiledMusic__running
    jmp ScummV5_M20_ApplyCompiledMusic__stopped
ScummV5_M20_ApplyCompiledMusic__running:
    .a8
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    .if SAME_BUILD_SCUMM_M21
    lda.l SCUMM_M20_PAYLOAD+$0C
    and #$00FF
    .else
    lda #$009A
    .endif
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    .if SAME_BUILD_SCUMM_M21
    lda.l SAME_SCUMM_CONDITION
    .else
    lda #$0001
    .endif
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_M20_ApplyCompiledMusic__play_queued
    jmp ScummV5_M20_ApplyCompiledMusic__failed
ScummV5_M20_ApplyCompiledMusic__play_queued:
    .a16
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M21
    lda.l SCUMM_M20_PAYLOAD+$0C
    .else
    lda #$9A
    .endif
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .if SAME_BUILD_SCUMM_M21
    lda.l SCUMM_M20_PAYLOAD+$0E
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    lda.l SCUMM_M20_PAYLOAD+$0F
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    lda.l SAME_SCUMM_C25_SELECTOR
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    .if SAME_BUILD_SCUMM_M22
    lda.l SAME_SCUMM_M22_CUE_GENERATION
    inc
    bne ScummV5_M20_ApplyCompiledMusic__m22_generation_ok
    inc
ScummV5_M20_ApplyCompiledMusic__m22_generation_ok:
    .a8
    sta.l SAME_SCUMM_M22_CUE_GENERATION
    lda.l SCUMM_M20_PAYLOAD+$74
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    lda.l SCUMM_M20_PAYLOAD+$75
    cmp #$02
    bne ScummV5_M20_ApplyCompiledMusic__m22_current_ok
    lda #$01 ; cold restart begins in the pre-boundary section
ScummV5_M20_ApplyCompiledMusic__m22_current_ok:
    .a8
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    lda.l SCUMM_M20_PAYLOAD+$7A
    beq ScummV5_M20_ApplyCompiledMusic__m22_no_plan
    lda #SAME_SAVE_SECTION_HOOK_VALUE
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    lda #SAME_SAVE_SECTION_BOUNDARY_TOKEN
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    lda #$02
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    lda #$01
    sta.l SAME_SCUMM_M22_CONSUMPTION
    lda.l SAME_SCUMM_M22_CUE_GENERATION
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
    ; Queue the normal semantic section packet after stop and play. The audio
    ; service defers command 22 until the freshly loaded song is playing.
    jsr Same_Event_StageEngine
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_SECTION_SELECT
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda #$0101
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0201
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_M20_ApplyCompiledMusic__section_queued
    jmp ScummV5_M20_ApplyCompiledMusic__failed
ScummV5_M20_ApplyCompiledMusic__section_queued:
    .a16
    sep #$20
    .a8
    bra ScummV5_M20_ApplyCompiledMusic__m22_applied
ScummV5_M20_ApplyCompiledMusic__m22_no_plan:
    .a8
    lda #$00
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
ScummV5_M20_ApplyCompiledMusic__m22_applied:
    .a8
    .endif
    .endif
    bra ScummV5_M20_ApplyCompiledMusic__position
ScummV5_M20_ApplyCompiledMusic__stopped:
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .if SAME_BUILD_SCUMM_M21
    sta.l SAME_SCUMM_MUSIC_ROUTE_KIND
    sta.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    sta.l SAME_SCUMM_MUSIC_ROUTE_SONG
    .if SAME_BUILD_SCUMM_M22
    sta.l SAME_SCUMM_M22_ROUTE_HISTORY
    sta.l SAME_SCUMM_M22_CURRENT_SECTION
    sta.l SAME_SCUMM_M22_PENDING_HOOK
    sta.l SAME_SCUMM_M22_ELIGIBLE_BOUNDARY
    sta.l SAME_SCUMM_M22_SELECTED_CONTINUATION
    sta.l SAME_SCUMM_M22_CONSUMPTION
    sta.l SAME_SCUMM_M22_GENERATION_AT_ARM
    .endif
    .endif
ScummV5_M20_ApplyCompiledMusic__position:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MUSIC_POSITION
    sta.l SAME_SCUMM_MUSIC_POSITION+2
    clc
    rts
ScummV5_M20_ApplyCompiledMusic__failed:
    sec
    rts

ScummV5_M20_Magic:
    .byte $53,$43,$4D,$55,$53,$49,$43,$00 ; SCMUSIC\0
    .if SAME_BUILD_SCUMM_M21
; Return X8 route index for current engine state or payload state.
ScummV5_M21_FindSavedRoute:
    sep #$20
    .a8
    ldx #$0000
ScummV5_M21_FindSavedRoute__next:
    .a8
    .i16
    cpx #SAME_SAVE_ROUTE_COUNT
    bcs ScummV5_M21_FindSavedRoute__missing
    lda.l SAME_SCUMM_MUSIC_ROUTE_KIND
    cmp.l Same_Save_RouteKinds,x
    bne ScummV5_M21_FindSavedRoute__advance
    lda.l SAME_SCUMM_MUSIC_ROUTE_VALUE
    cmp.l Same_Save_RouteValues,x
    beq ScummV5_M21_FindSavedRoute__found
ScummV5_M21_FindSavedRoute__advance:
    inx
    bra ScummV5_M21_FindSavedRoute__next
ScummV5_M21_FindSavedRoute__found:
    clc
    rts
ScummV5_M21_FindSavedRoute__missing:
    sec
    rts

ScummV5_M21_FindPayloadRoute:
    sep #$20
    .a8
    ldx #$0000
ScummV5_M21_FindPayloadRoute__next:
    .a8
    .i16
    cpx #SAME_SAVE_ROUTE_COUNT
    bcs ScummV5_M21_FindPayloadRoute__missing
    lda.l SCUMM_M20_PAYLOAD+$0E
    cmp.l Same_Save_RouteKinds,x
    bne ScummV5_M21_FindPayloadRoute__advance
    lda.l SCUMM_M20_PAYLOAD+$0F
    cmp.l Same_Save_RouteValues,x
    beq ScummV5_M21_FindPayloadRoute__found
ScummV5_M21_FindPayloadRoute__advance:
    inx
    bra ScummV5_M21_FindPayloadRoute__next
ScummV5_M21_FindPayloadRoute__found:
    clc
    rts
ScummV5_M21_FindPayloadRoute__missing:
    sec
    rts
    .endif
.endif

ScummV5_Op_StartMusic:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartMusic__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartMusic__operand_ok:
    sta.l SAME_SCUMM_CONDITION
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0001
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_Op_StartMusic__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StartMusic__queued:
    .if SAME_BUILD_SCUMM_M19
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .endif
    .if SAME_BUILD_SCUMM_M20
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MUSIC_POSITION
    sta.l SAME_SCUMM_MUSIC_POSITION+2
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StopMusic:
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_MUSIC_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    jsr Same_Event_Push
    bcc ScummV5_Op_StopMusic__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StopMusic__queued:
    .if SAME_BUILD_SCUMM_M19
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    .endif
    .if SAME_BUILD_SCUMM_M20
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MUSIC_POSITION
    sta.l SAME_SCUMM_MUSIC_POSITION+2
    .endif
    jmp ScummV5_Engine_Frame__next

.if SAME_BUILD_SCUMM_M23C
; Bounded 256-bit logical SFX ownership used by canonical isSoundRunning.
; Input A8 is the logical sound id. Helpers preserve no scratch registers.
ScummV5_M23C_SfxAddress:
    sep #$20
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    and #$07
    rep #$10
    .i16
    tax
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_C16_BIT_MASK
    lda.l SAME_SCUMM_FETCH_BYTE
    lsr
    lsr
    lsr
    and #$1F
    tax
    rts
ScummV5_M23C_SetSfxActive:
    jsr ScummV5_M23C_SfxAddress
    lda.l SAME_SCUMM_M23C_ACTIVE_SFX,x
    ora.l SAME_SCUMM_C16_BIT_MASK
    sta.l SAME_SCUMM_M23C_ACTIVE_SFX,x
    rts
ScummV5_M23C_ClearSfxActive:
    jsr ScummV5_M23C_SfxAddress
    lda.l SAME_SCUMM_C16_BIT_MASK
    eor #$FF
    and.l SAME_SCUMM_M23C_ACTIVE_SFX,x
    sta.l SAME_SCUMM_M23C_ACTIVE_SFX,x
    rts
ScummV5_M23C_TestSfxActive:
    jsr ScummV5_M23C_SfxAddress
    lda.l SAME_SCUMM_M23C_ACTIVE_SFX,x
    and.l SAME_SCUMM_C16_BIT_MASK
    beq ScummV5_M23C_TestSfxActive__false
    lda #$01
    rts
ScummV5_M23C_TestSfxActive__false:
    .a8
    lda #$00
    rts
.endif

ScummV5_Op_StartSound:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartSound__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartSound__operand_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    .if SAME_BUILD_M24RB
    cmp #SAME_M24RB_PRIMARY_SOUND
    bne ScummV5_Op_StartSound__m24rb_normal
    lda.l SAME_M24RB_LOGICAL82_STATE
    cmp #$02
    bcc ScummV5_Op_StartSound__m24rb_normal
    lda #SAME_M24RB_PRIMARY_SOUND
    sta.l SAME_SCUMM_ACTIVE_MUSIC
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_StartSound__m24rb_normal:
    .a8
    .endif
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_SFX_PLAY
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    lda #$0080
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG1
    jsr Same_Event_Push
    bcc ScummV5_Op_StartSound__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StartSound__queued:
    .if SAME_BUILD_SCUMM_M23C
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    jsr ScummV5_M23C_SetSfxActive
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StopSound:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StopSound__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_StopSound__operand_ok:
    sta.l SAME_SCUMM_CONDITION
    jsr Same_Event_StageEngine
    sep #$20
    .a8
    lda #SAME_SERVICE_AUDIO
    sta.l SAME_EVENT_STAGING+SAME_PKT_SERVICE
    lda #SAME_AUDIO_OP_SFX_STOP
    sta.l SAME_EVENT_STAGING+SAME_PKT_OPCODE
    lda #SAME_ENDPOINT_SPC
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_EVENT_STAGING+SAME_PKT_ARG0
    jsr Same_Event_Push
    bcc ScummV5_Op_StopSound__queued
    jmp ScummV5_Op__service_error
ScummV5_Op_StopSound__queued:
    .if SAME_BUILD_SCUMM_M23C
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    jsr ScummV5_M23C_ClearSfxActive
    .endif
    jmp ScummV5_Engine_Frame__next

    .if SAME_BUILD_SCUMM_M19
; Canonical v5 $7C/$FC isSoundRunning. Logical ownership changes only after a
; required service packet is accepted; compiled song ids and TAD/SPC state are
; deliberately not engine-visible.
ScummV5_Op_IsSoundRunning:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_IsSoundRunning__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsSoundRunning__result_ok:
    sep #$20
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_IsSoundRunning__sound_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsSoundRunning__sound_ok:
    .a8
    cmp #$00
    beq ScummV5_Op_IsSoundRunning__false
    cmp.l SAME_SCUMM_ACTIVE_MUSIC
    beq ScummV5_Op_IsSoundRunning__true
    .if SAME_BUILD_SCUMM_M23C
    jsr ScummV5_M23C_TestSfxActive
    beq ScummV5_Op_IsSoundRunning__false
    bra ScummV5_Op_IsSoundRunning__true
    .else
    bne ScummV5_Op_IsSoundRunning__false
    .endif
ScummV5_Op_IsSoundRunning__true:
    .a8
    .if SAME_BUILD_SCUMM_M23B_NEGATIVE
    lda #$01
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_CONDITION
    .endif
    lda #$01
    bra ScummV5_Op_IsSoundRunning__write
ScummV5_Op_IsSoundRunning__false:
    .a8
    lda #$00
ScummV5_Op_IsSoundRunning__write:
    .a8
    .if SAME_BUILD_SCUMM_M23C
    pha
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    bne ScummV5_Op_IsSoundRunning__m23c_recorded
    lda.l SAME_SCUMM_M23C_SOUND80_RESULT
    cmp #$FF
    bne ScummV5_Op_IsSoundRunning__m23c_second
    pla
    pha
    sta.l SAME_SCUMM_M23C_SOUND80_RESULT
    bra ScummV5_Op_IsSoundRunning__m23c_recorded
ScummV5_Op_IsSoundRunning__m23c_second:
    .a8
    pla
    pha
    sta.l SAME_SCUMM_M23C_SOUND82_RESULT
    .if SAME_BUILD_SCUMM_M23C_SOUND_CONTROL
    bne ScummV5_Op_IsSoundRunning__m23c_recorded
    lda #$01
    sta.l SAME_SCUMM_M23C_SOUND_CONTROL_HOLD
    .endif
ScummV5_Op_IsSoundRunning__m23c_recorded:
    pla
    .endif
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
    .endif

ScummV5_Op__service_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_SERVICE
    .if SAME_BUILD_SCUMM_M23B
    pha
    lda #$04
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    pla
    .endif
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_Stop:
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_STOP_SLOT
    lda.l SAME_SCUMM_SCENARIO_STOP_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_STOP_COUNT
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_STOP_PC
    sep #$20
    .a8
    .endif
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    sep #$10
    .i8
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C19_SLOT_DEPTH,x
    beq ScummV5_Op_Stop__cutscene_clear
    jmp ScummV5_C19_Error
ScummV5_Op_Stop__cutscene_clear:
    .a8
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    bne ScummV5_Op_Stop__c4_slot
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$01
    beq ScummV5_Op_Stop__m23a_exit_complete
    cmp #$02
    beq ScummV5_Op_Stop__m23a_entry_complete
    bra ScummV5_Op_Stop__m23a_not_room_script
ScummV5_Op_Stop__m23a_exit_complete:
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_EndRoomScript_FarEntry
    jsl ScummV5_M23A_CommitRoom_FarEntry
    .else
    jsr ScummV5_M23A_EndRoomScript
    jsr ScummV5_M23A_CommitRoom
    .endif
    bcs ScummV5_Op_Stop__m23a_error
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Stop__m23a_entry_complete:
    .a8
    .if SAME_BUILD_M24RB
    jsl ScummV5_M23A_EndRoomScript_FarEntry
    lda #$0A
    jsl ScummV5_M23A_Trace_FarEntry
    .else
    jsr ScummV5_M23A_EndRoomScript
    lda #$0A
    jsr ScummV5_M23A_Trace
    .endif
    lda #$00
    sta.l SAME_SCUMM_M23A_PHASE
    sta.l SAME_SCUMM_M23A_CURRENT_KIND
    sta.l SAME_SCUMM_RETURN_MODE
    lda.l SAME_SCUMM_M23A_RETURN_PROGRAM
    sta.l SAME_SCUMM_PROGRAM_SELECT
    rep #$20
    .a16
    lda.l SAME_SCUMM_M23A_RETURN_PC
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_Stop__m23a_error:
    jmp ScummV5_Op__error
ScummV5_Op_Stop__m23a_not_room_script:
    .a8
    .endif
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_RETURN_MODE
    beq ScummV5_Op_Stop__complete
    ; Any interpreter entered through a scheduler slot owns that slot.  Stop
    ; retirement is therefore a return-mode rule, not a fixture-ID whitelist.
ScummV5_Op_Stop__c4_slot:
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_STATUS
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l SAME_SCUMM_SCENARIO_STOP_STATUS
    .endif
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_Stop__complete
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_Stop__complete:
    .a8
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_BreakHere:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_LoadRoomWithEgo_Postamble_Far
    .endif
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_Move:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Move__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Move__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Move__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Move__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Add:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Add__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Add__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Add__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Add__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadResultValue
    clc
    adc.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Subtract:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Subtract__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Subtract__result_ok:
    .a16
    .i16
    jsr ScummV5_FetchVarOrDirectWord
    bcc ScummV5_Op_Subtract__operand_ok
    jmp ScummV5_Op__error
ScummV5_Op_Subtract__operand_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadResultValue
    sec
    sbc.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Multiply:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Multiply__ready
    jmp ScummV5_Op__error
ScummV5_Op_Multiply__ready:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_PRODUCT
    lda #$0010
    sta.l SAME_SCUMM_LOOP
ScummV5_Op_Multiply__loop:
    .a16
    .i16
    lda.l SAME_SCUMM_OPERAND
    and #$0001
    beq ScummV5_Op_Multiply__no_add
    lda.l SAME_SCUMM_PRODUCT
    clc
    adc.l SAME_SCUMM_LHS
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Multiply__no_add:
    lda.l SAME_SCUMM_LHS
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    lsr
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_Op_Multiply__loop
    lda.l SAME_SCUMM_PRODUCT
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Divide:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Divide__operands_ready
    jmp ScummV5_Op__error
ScummV5_Op_Divide__operands_ready:
    lda.l SAME_SCUMM_OPERAND
    bne ScummV5_Op_Divide__nonzero
    sep #$20
    .a8
    lda #SCUMM_ERR_DIVIDE_ZERO
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Divide__nonzero:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    eor.l SAME_SCUMM_OPERAND
    and #$8000
    beq ScummV5_Op_Divide__same_sign
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
    bra ScummV5_Op_Divide__sign_ready
ScummV5_Op_Divide__same_sign:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONDITION
    rep #$20
    .a16
ScummV5_Op_Divide__sign_ready:
    .a16
    lda.l SAME_SCUMM_LHS
    bpl ScummV5_Op_Divide__lhs_positive
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_LHS
ScummV5_Op_Divide__lhs_positive:
    .a16
    lda.l SAME_SCUMM_OPERAND
    bpl ScummV5_Op_Divide__rhs_positive
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_Divide__rhs_positive:
    .a16
    lda #$0000
    sta.l SAME_SCUMM_PRODUCT
    sta.l SAME_SCUMM_REMAINDER
    lda #$0010
    sta.l SAME_SCUMM_LOOP
ScummV5_Op_Divide__loop:
    lda.l SAME_SCUMM_LHS
    asl
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_REMAINDER
    rol
    sta.l SAME_SCUMM_REMAINDER
    lda.l SAME_SCUMM_PRODUCT
    asl
    sta.l SAME_SCUMM_PRODUCT
    lda.l SAME_SCUMM_REMAINDER
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_Divide__next_bit
    sbc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_REMAINDER
    lda.l SAME_SCUMM_PRODUCT
    ora #$0001
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Divide__next_bit:
    lda.l SAME_SCUMM_LOOP
    dec
    sta.l SAME_SCUMM_LOOP
    bne ScummV5_Op_Divide__loop
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_Divide__store
    rep #$20
    .a16
    lda.l SAME_SCUMM_PRODUCT
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_PRODUCT
ScummV5_Op_Divide__store:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PRODUCT
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_And:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_And__ready
    jmp ScummV5_Op__error
ScummV5_Op_And__ready:
    lda.l SAME_SCUMM_LHS
    and.l SAME_SCUMM_OPERAND
    bra ScummV5_Op_Binary__store

ScummV5_Op_Or:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Or__ready
    jmp ScummV5_Op__error
ScummV5_Op_Or__ready:
    lda.l SAME_SCUMM_LHS
    ora.l SAME_SCUMM_OPERAND
ScummV5_Op_Binary__store:
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Increment:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Increment__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Increment__result_ok:
    .a16
    .i16
    jsr ScummV5_ReadResultValue
    inc
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Decrement:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_Decrement__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_Decrement__result_ok:
    jsr ScummV5_ReadResultValue
    dec
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Compare:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadBinaryOperands
    bcc ScummV5_Op_Compare__operands_ready
    jmp ScummV5_Op__error
ScummV5_Op_Compare__operands_ready:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$48
    beq ScummV5_Op_Compare__equal
    cmp #$08
    beq ScummV5_Op_Compare__not_equal
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    eor #$8000
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    eor #$8000
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$7F
    cmp #$44
    beq ScummV5_Op_Compare__less
    cmp #$78
    beq ScummV5_Op_Compare__greater
    cmp #$38
    beq ScummV5_Op_Compare__less_equal
    bra ScummV5_Op_Compare__greater_equal
ScummV5_Op_Compare__equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    beq ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__not_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bne ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__less:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp.l SAME_SCUMM_LHS
    bcc ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__greater:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__less_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    cmp.l SAME_SCUMM_OPERAND
    bcs ScummV5_Op_Compare__true
    bra ScummV5_Op_Compare__false
ScummV5_Op_Compare__greater_equal:
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp.l SAME_SCUMM_LHS
    bcs ScummV5_Op_Compare__true
ScummV5_Op_Compare__false:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CONDITION
    bra ScummV5_Op_Compare__offset
ScummV5_Op_Compare__true:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_Compare__offset:
    jsr ScummV5_ApplyConditionOffset
    bcc ScummV5_Op_Compare__done
    jmp ScummV5_Op__error
ScummV5_Op_Compare__done:
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_CompareZero:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_CompareZero__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_CompareZero__result_ok:
    jsr ScummV5_ReadResultValue
    bne ScummV5_Op_CompareZero__nonzero
    sep #$20
    .a8
    lda #$01
    bra ScummV5_Op_CompareZero__select
ScummV5_Op_CompareZero__nonzero:
    sep #$20
    .a8
    lda #$00
ScummV5_Op_CompareZero__select:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_LAST_OPCODE
    cmp #$28
    beq ScummV5_Op_CompareZero__offset
    lda.l SAME_SCUMM_CONDITION
    eor #$01
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_CompareZero__offset:
    jsr ScummV5_ApplyConditionOffset
    bcc ScummV5_Op_CompareZero__done
    jmp ScummV5_Op__error
ScummV5_Op_CompareZero__done:
    .if SAME_BUILD_SCUMM_M23C_SOUND_CONTROL
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23C_SOUND_CONTROL_HOLD
    beq ScummV5_Op_CompareZero__m23c_continue
    lda #$00
    sta.l SAME_SCUMM_M23C_SOUND_CONTROL_HOLD
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    lda #$04
    sta.l SAME_SCUMM_M23C_PHASE
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_CompareZero__m23c_continue:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M23B_NEGATIVE
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23B_HOLD_AFTER_CONDITION
    beq ScummV5_Op_CompareZero__continue
    lda #$00
    sta.l SAME_SCUMM_M23B_HOLD_AFTER_CONDITION
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_CompareZero__continue:
    .a8
    .endif
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_JumpRelative:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_JumpRelative__offset_ok
    jmp ScummV5_Op__error
ScummV5_Op_JumpRelative__offset_ok:
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_PC
    clc
    adc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_PC
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_Delay:
    rep #$30
    .a16
    .i16
    ; Delay is a three-byte little-endian operand in SCUMM v5.  Decode the
    ; complete operand here instead of nesting three byte-fetch subroutines;
    ; the VM tick can then be pre-empted by NMI without carrying a deep helper
    ; return stack across the interrupt.
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sec
    sbc #$0002
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_Op_Delay__in_range
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Delay__in_range:
    sep #$20
    .a8
    inx
    inx
    jsr ScummV5_FetchSelectedByteAtX
    dex
    dex
    cmp #$00
    beq ScummV5_Op_Delay__high_valid
    lda #SCUMM_ERR_DELAY_RANGE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_Delay__high_valid:
    jsr ScummV5_FetchSelectedByteAtX
    sta.l SAME_SCUMM_OPERAND
    inx
    jsr ScummV5_FetchSelectedByteAtX
    dex
    sta.l SAME_SCUMM_OPERAND+1
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_DELAY
    txa
    clc
    adc #$0003
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_DelayVariable:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_DelayVariable__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_DelayVariable__result_ok:
    .a16
    .i16
    jsr ScummV5_ReadResultValue
    bpl ScummV5_Op_DelayVariable__store
    lda #$0000
ScummV5_Op_DelayVariable__store:
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_DELAYED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_StartScript:
    sep #$20
    .a8
    ; A scheduler-owned script slot is a complete parent context.  Canonical
    ; startScript is valid from an ordinary outer frame and does not depend on
    ; room-entry/exit ownership or a fixture-specific return mode.
ScummV5_Op_StartScript__c4:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StartScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
ScummV5_Op_StartScript__number_stored:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_SCENARIO_START_REQUEST
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_START_CURRENT
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_SCENARIO_START_ACTIVE_BEFORE
    lda.l SAME_SCUMM_C4_SLOT_STATUS+1
    sta.l SAME_SCUMM_SCENARIO_START_STATUS1
    lda.l SAME_SCUMM_C4_SLOT_STATUS+2
    sta.l SAME_SCUMM_SCENARIO_START_STATUS2
    lda.l SAME_SCUMM_C4_SLOT_STATUS+3
    sta.l SAME_SCUMM_SCENARIO_START_STATUS3
    .endif
    lda #$00
    sta.l SAME_SCUMM_C4_ARG_COUNT
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_Op_StartScript__clear_args:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_ARGS,x
    inx
    inx
    cpx #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcc ScummV5_Op_StartScript__clear_args
ScummV5_Op_StartScript__next_arg:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StartScript__arg_selector_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_StartScript__args_done
    pha
    lda.l SAME_SCUMM_C4_ARG_COUNT
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_StartScript__arg_room
    pla
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_room:
    .a8
    pla
    and #$80
    pha
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_StartScript__arg_word_ok
    sep #$20
    .a8
    pla
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_word_ok:
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    pla
    beq ScummV5_Op_StartScript__arg_value_ready
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_StartScript__arg_variable_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__arg_variable_ok:
    sta.l SAME_SCUMM_OPERAND
ScummV5_Op_StartScript__arg_value_ready:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_ARG_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_ARGS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_ARG_COUNT
    inc
    sta.l SAME_SCUMM_C4_ARG_COUNT
    bra ScummV5_Op_StartScript__next_arg
ScummV5_Op_StartScript__args_done:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__normal_args_done
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_StartScript__chain_retired
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_StartScript__chain_retired:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_Op_StartScript__chain_target
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_StartScript__chain_target:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_FLAGS
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__normal_args_done:
    .a8
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_Op_StartScript__has_script
    jmp ScummV5_Op_StartScript__no_script
ScummV5_Op_StartScript__has_script:
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$40
    bne ScummV5_Op_StartScript__allocate
    lda.l SAME_SCUMM_CONDITION
    jsr ScummV5_C4_StopNumber
ScummV5_Op_StartScript__allocate:
    .a8
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_StartScript__scan
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_M25A_FAULT_DEPTH
    lda #$F0
    jsr ScummV5_M25A_Trace
    .endif
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__scan:
    .a8
    lda #$01
    sta.l SAME_SCUMM_C4_SCAN_SLOT
ScummV5_Op_StartScript__scan_next:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    cmp #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcs ScummV5_Op_StartScript__capacity_error
    rep #$30
    .a16
    .i16
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_StartScript__found
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StartScript__found
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    inc
    sta.l SAME_SCUMM_C4_SCAN_SLOT
    bra ScummV5_Op_StartScript__scan_next
ScummV5_Op_StartScript__capacity_error:
    .a8
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__capacity_error_code
    lda #$42
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__capacity_error_code:
    .a8
    lda #SCUMM_ERR_SLOT_CAPACITY
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__found:
    .a8
    .i16
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_SCENARIO_START_SCAN
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_SCENARIO_START_ACTIVE_AFTER
    .endif
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Keep the production allocator observable for the controlled startup
    ; root.  This records the chosen slot before its fields are initialized,
    ; without influencing allocation or dispatch.
    lda.l SAME_SCUMM_SCENARIO_ALLOC_TRACE_COUNT
    cmp #$10
    bcs ScummV5_Op_StartScript__alloc_trace_done
    rep #$30
    .a16
    .i16
    and #$00FF
    asl
    asl
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE,x
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+1,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+2,x
    phx
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_OPERAND+1
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    sta.l SAME_SCUMM_OPERAND+2
    plx
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+3,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+4,x
    lda.l SAME_SCUMM_OPERAND+2
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+5,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE+6,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENARIO_ALLOC_TRACE_COUNT
    inc
    sta.l SAME_SCUMM_SCENARIO_ALLOC_TRACE_COUNT
ScummV5_Op_StartScript__alloc_trace_done:
    .a8
    .i16
    .endif
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    jsl ScummV5_M25_DebugStartAlloc_Far
    .endif
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    tax
    sep #$20
    .a8
    txa
    sta.l SAME_SCUMM_C4_LAST_ALLOCATED
    lda #SCUMM_VM_RUNNING
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda.l SAME_SCUMM_CONDITION
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_CONDITION
    .if SCUMM_V5_NUM_GLOBAL_SCRIPTS == $0100
    jsr ScummV5_M23A_ResolveGlobalScript
    bcs ScummV5_Op_StartScript__m23a_program
    jmp ScummV5_Op_StartScript__mapping_error
    .else
    cmp #SCUMM_V5_NUM_GLOBAL_SCRIPTS
    bcc ScummV5_Op_StartScript__m23a_global
    jsr ScummV5_M23A_ResolveLocalScript
    bcs ScummV5_Op_StartScript__m23a_program
    jmp ScummV5_Op_StartScript__mapping_error
ScummV5_Op_StartScript__m23a_global:
    .a8
    jsr ScummV5_M23A_ResolveGlobalScript
    bcs ScummV5_Op_StartScript__m23a_program
    jmp ScummV5_Op_StartScript__mapping_error
    .endif
ScummV5_Op_StartScript__m23a_program:
    .a8
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    sta.l SAME_SCUMM_SCENARIO_START_PROGRAM
    lda #$01
    sta.l SAME_SCUMM_SCENARIO_START_RESULT
    lda.l SAME_SCUMM_SCENARIO_START_PROGRAM
    .endif
    jmp ScummV5_Op_StartScript__program_ready
    .endif
    cmp #$02
    beq ScummV5_Op_StartScript__program2
    cmp #$03
    beq ScummV5_Op_StartScript__program3
    cmp #$04
    beq ScummV5_Op_StartScript__program4
    cmp #$05
    beq ScummV5_Op_StartScript__program5
    cmp #$06
    beq ScummV5_Op_StartScript__program6
    cmp #$07
    beq ScummV5_Op_StartScript__program7
    cmp #$0A
    beq ScummV5_Op_StartScript__program10
    cmp #$0B
    beq ScummV5_Op_StartScript__program11
    cmp #$0C
    beq ScummV5_Op_StartScript__program12
    cmp #$0D
    beq ScummV5_Op_StartScript__program13
ScummV5_Op_StartScript__mapping_error:
    .a8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    ; A directory may omit a dormant/optional global script.  SCUMM treats
    ; an unavailable startScript target as a no-op after releasing the slot;
    ; it must not poison the parent scheduler with a script error.
    jmp ScummV5_Engine_Frame__complete_success
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__mapping_error_code
    lda #$42
    sta.l SAME_SCUMM_LAST_OPCODE
ScummV5_Op_StartScript__mapping_error_code:
    .a8
    .if SAME_BUILD_SCUMM_M23B
    lda #$A1
    sta.l SAME_SCUMM_M23B_ERROR_SITE
    .endif
    .if SAME_BUILD_SCUMM_M25A_VALIDATOR
    lda.l SAME_SCUMM_M23B_NEST_DEPTH
    sta.l SAME_SCUMM_M25A_FAULT_DEPTH
    lda #$F1
    jsr ScummV5_M25A_Trace
    .endif
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__program2:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD2
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program3:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD3
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program4:
    .a8
    lda #SCUMM_C2_FIXTURE_C4_CHILD4
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program5:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD5
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program6:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD6
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program7:
    .a8
    lda #SCUMM_C2_FIXTURE_C5_CHILD7
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program10:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_CHAIN10
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program11:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_CHAIN11
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program12:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_TARGET12
    bra ScummV5_Op_StartScript__program_ready
ScummV5_Op_StartScript__program13:
    .a8
    lda #SCUMM_C2_FIXTURE_C6_TARGET13
ScummV5_Op_StartScript__program_ready:
    .a8
    sta.l SAME_SCUMM_FETCH_BYTE
    .if SAME_BUILD_SCUMM_M23A
    jsl ScummV5_SlotMarkOrdinaryScript_Far
    .endif
    sep #$10
    .i8
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    tax
    ; A newly allocated C4 slot owns a fresh cutscene depth.  Do not inherit
    ; the reset sentinel from the slot table when a yielded child is reused.
    lda #$00
    sta.l SAME_SCUMM_C19_SLOT_DEPTH,x
    lda.l SAME_SCUMM_FETCH_BYTE
    rep #$10
    .i16
    lda.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_M23A_SLOT_ROOMS,x
    .endif
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$20
    beq ScummV5_Op_StartScript__freeze_flag_ready
    lda #$01
ScummV5_Op_StartScript__freeze_flag_ready:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$40
    beq ScummV5_Op_StartScript__recursive_flag_ready
    lda #$01
ScummV5_Op_StartScript__recursive_flag_ready:
    .a8
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda #$01
    sta.l SAME_SCUMM_C4_SLOT_DIDEXEC,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    inc
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_C4_SLOT_PC,x
    sta.l SAME_SCUMM_C4_SLOT_DELAY,x
    lda.l SAME_SCUMM_C4_SCAN_SLOT
    and #$00FF
    xba
    lsr
    lsr
    sta.l SAME_SCUMM_RESULT_OFFSET
    tax
    lda #$0000
    ldy #$0000
ScummV5_Op_StartScript__clear_locals:
    .a16
    .i16
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    inx
    inx
    iny
    cpy #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_Op_StartScript__clear_locals
    lda.l SAME_SCUMM_RESULT_OFFSET
    tax
    ldy #$0000
ScummV5_Op_StartScript__copy_args:
    .a16
    .i16
    cpy #(SAME_SCUMM_LOCAL_COUNT * 2)
    bcs ScummV5_Op_StartScript__locals_ready
    tya
    tax
    lda.l SAME_SCUMM_C4_ARGS,x
    sta.l SAME_SCUMM_OPERAND
    tya
    clc
    adc.l SAME_SCUMM_RESULT_OFFSET
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    iny
    iny
    bra ScummV5_Op_StartScript__copy_args
ScummV5_Op_StartScript__locals_ready:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23C
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    bne ScummV5_Op_StartScript__m23c_start_recorded
    lda.l SAME_SCUMM_CONDITION
    cmp #SCUMM_M23C_GLOBAL_SCRIPT
    bne ScummV5_Op_StartScript__m23c_start_recorded
    lda #$01
    sta.l SAME_SCUMM_M23C_SCRIPT151_STARTED
ScummV5_Op_StartScript__m23c_start_recorded:
    .a8
    .endif
    lda.l SAME_SCUMM_C4_CHAIN_MODE
    beq ScummV5_Op_StartScript__run_nested
    jsr ScummV5_C4_RunAllocatedNoParent
    php
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    plp
    bcc ScummV5_Op_StartScript__chain_complete
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__chain_complete:
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_StartScript__run_nested:
    jsr ScummV5_C4_RunNestedChild
    bcc ScummV5_Op_StartScript__nested_ok
    jmp ScummV5_Op__error
ScummV5_Op_StartScript__nested_ok:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_M23A && SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_ENABLED
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    tax
    lda.l SAME_SCUMM_C4_SLOT_PROGRAM,x
    cmp #SCUMM_V5_HOLD_AFTER_STARTED_GLOBAL_PROGRAM
    bne ScummV5_Op_StartScript__profile_gate_done
    lda #$01
    sta.l SAME_SCUMM_M23A_HOLD
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_StartScript__profile_gate_done:
    .a8
    .endif
    .if SAME_BUILD_SCUMM_M23C
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    bne ScummV5_Op_StartScript__m23c_status_recorded
    lda.l SAME_SCUMM_CONDITION
    cmp #SCUMM_M23C_GLOBAL_SCRIPT
    bne ScummV5_Op_StartScript__m23c_status_recorded
    lda.l SAME_SCUMM_C4_LAST_ALLOCATED
    tax
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    sta.l SAME_SCUMM_M23C_SCRIPT151_STATUS
ScummV5_Op_StartScript__m23c_status_recorded:
    .a8
    .endif
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StartScript__parent_stopped
ScummV5_Op_StartScript__no_script:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_StartScript__parent_stopped:
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_ChainScript:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_ChainScript__c6
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_ChainScript__c6:
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    beq ScummV5_Op_ChainScript__no_freeze_flag
    lda #$20
ScummV5_Op_ChainScript__no_freeze_flag:
    .a8
    sta.l SAME_SCUMM_C4_CHAIN_FLAGS
    lda.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    beq ScummV5_Op_ChainScript__flags_ready
    lda.l SAME_SCUMM_C4_CHAIN_FLAGS
    ora #$40
    sta.l SAME_SCUMM_C4_CHAIN_FLAGS
ScummV5_Op_ChainScript__flags_ready:
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_ChainScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_ChainScript__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    .if SAME_BUILD_SCUMM_M25_MOVEMENT
    jsl ScummV5_ChainObjectTrace_Far
    .endif
    .if SAME_BUILD_M24RB
    cmp #SAME_M24RB_NEXT_BLOCKER_SCRIPT
    bne ScummV5_Op_ChainScript__m24rb_continue
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    cmp #SCUMM_M23C_TARGET_ROOM
    bne ScummV5_Op_ChainScript__m24rb_continue
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_DELAY
    sep #$20
    .a8
    lda #SCUMM_VM_YIELDED
    sta.l SAME_SCUMM_STATUS
    jmp ScummV5_Engine_Frame__complete_success
ScummV5_Op_ChainScript__m24rb_continue:
    .a8
    .endif
    lda #$01
    sta.l SAME_SCUMM_C4_CHAIN_MODE
    jmp ScummV5_Op_StartScript__number_stored

ScummV5_Op_StopScript:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_StopScript__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_StopScript__number_ok:
    .a8
    beq ScummV5_Op_StopScript__self
    jsr ScummV5_C4_StopNumber
    lda.l SAME_SCUMM_STATUS
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_StopScript__complete
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_StopScript__self:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    tax
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_C4_SLOT_STATUS,x
    lda #$00
    sta.l SAME_SCUMM_C4_SLOT_NUMBER,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    sta.l SAME_SCUMM_C4_SLOT_RECURSIVE,x
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    lda.l SAME_SCUMM_C4_ACTIVE_COUNT
    beq ScummV5_Op_StopScript__self_counted
    dec
    sta.l SAME_SCUMM_C4_ACTIVE_COUNT
ScummV5_Op_StopScript__self_counted:
    .a8
    lda #SCUMM_VM_STOPPED
    sta.l SAME_SCUMM_STATUS
ScummV5_Op_StopScript__complete:
    jmp ScummV5_Engine_Frame__complete_success

ScummV5_Op_FreezeScripts:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    beq ScummV5_Op_FreezeScripts__c20
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_FreezeScripts__c5
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__c5:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_FreezeScripts__flag_ok
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__flag_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_FreezeScripts__unfreeze
    ldx #$0000
ScummV5_Op_FreezeScripts__freeze_scan:
    .a8
    .i16
    txa
    cmp.l SAME_SCUMM_C4_CURRENT_SLOT
    beq ScummV5_Op_FreezeScripts__freeze_next
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_FreezeScripts__freeze_next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_FreezeScripts__freeze_next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_Op_FreezeScripts__freeze_next
    lda.l SAME_SCUMM_CONDITION
    bmi ScummV5_Op_FreezeScripts__freeze_slot
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_RESISTANT,x
    bne ScummV5_Op_FreezeScripts__freeze_next
ScummV5_Op_FreezeScripts__freeze_slot:
    .a8
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    inc
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
ScummV5_Op_FreezeScripts__freeze_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_FreezeScripts__freeze_scan
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FreezeScripts__unfreeze:
    .a8
    .i16
    ldx #$0000
ScummV5_Op_FreezeScripts__unfreeze_scan:
    lda.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
    beq ScummV5_Op_FreezeScripts__unfreeze_next
    dec
    sta.l SAME_SCUMM_C4_SLOT_FREEZE_COUNT,x
ScummV5_Op_FreezeScripts__unfreeze_next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_FreezeScripts__unfreeze_scan
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_FreezeScripts__c20:
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_FreezeScripts__c20_flag_ok
    jmp ScummV5_Op__error
ScummV5_Op_FreezeScripts__c20_flag_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    lda.l SAME_SCUMM_C20_COUNT
    beq ScummV5_Op_FreezeScripts__c20_done
    rep #$30
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_OPERAND
    asl
    sta.l SAME_SCUMM_OPERAND
    ldx #$0000
ScummV5_Op_FreezeScripts__c20_loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_FreezeScripts__c20_unfreeze
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    cmp #$FF
    beq ScummV5_Op_FreezeScripts__c20_error
    inc
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    bra ScummV5_Op_FreezeScripts__c20_next
ScummV5_Op_FreezeScripts__c20_unfreeze:
    .a8
    lda.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
    beq ScummV5_Op_FreezeScripts__c20_next
    dec
    sta.l SAME_SCUMM_C20_RECORDS+SAME_SCUMM_C20_R_FREEZE,x
ScummV5_Op_FreezeScripts__c20_next:
    rep #$30
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C20_RECORD_STRIDE
    tax
    cmp.l SAME_SCUMM_OPERAND
    bcc ScummV5_Op_FreezeScripts__c20_loop
ScummV5_Op_FreezeScripts__c20_done:
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_FreezeScripts__c20_error:
    .a8
    lda #SCUMM_ERR_SENTENCE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_IsScriptRunning:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RETURN_MODE
    bne ScummV5_Op_IsScriptRunning__c5
    .if SAME_BUILD_SCUMM_M23A
    lda.l SAME_SCUMM_M23A_PHASE
    cmp #$02
    beq ScummV5_Op_IsScriptRunning__c5
    .endif
    lda #SCUMM_ERR_SCRIPT
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__c5:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcc ScummV5_Op_IsScriptRunning__result_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__result_ok:
    sep #$20
    .a8
    jsr ScummV5_FetchVarOrDirectByte
    bcc ScummV5_Op_IsScriptRunning__number_ok
    jmp ScummV5_Op__error
ScummV5_Op_IsScriptRunning__number_ok:
    .a8
    sta.l SAME_SCUMM_CONDITION
    ; Slot zero is the scheduler-owned room ENCD frame, not a runnable
    ; global script.  It must not make an authored isScriptRunning(0) query
    ; self-affirm while room entry is still executing.
    ldx #$0001
ScummV5_Op_IsScriptRunning__scan:
    .a8
    .i16
    lda.l SAME_SCUMM_C4_SLOT_STATUS,x
    beq ScummV5_Op_IsScriptRunning__next
    cmp #SCUMM_VM_STOPPED
    beq ScummV5_Op_IsScriptRunning__next
    cmp #SCUMM_VM_ERROR
    beq ScummV5_Op_IsScriptRunning__next
    lda.l SAME_SCUMM_C4_SLOT_NUMBER,x
    cmp.l SAME_SCUMM_CONDITION
    beq ScummV5_Op_IsScriptRunning__true
ScummV5_Op_IsScriptRunning__next:
    .a8
    .i16
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_Op_IsScriptRunning__scan
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next
ScummV5_Op_IsScriptRunning__true:
    rep #$20
    .a16
    lda #$0001
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Engine_Frame__next

ScummV5_Op__error:
    jmp ScummV5_Engine_Frame__error

ScummV5_Op_CursorCommand:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_CursorCommand__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__subop_ok:
    .a8
    sta.l SAME_SCUMM_C7_SUBOP
    and #$1F
    cmp #$01
    beq ScummV5_Op_CursorCommand__cursor_on
    cmp #$02
    beq ScummV5_Op_CursorCommand__cursor_off
    cmp #$03
    beq ScummV5_Op_CursorCommand__userput_on
    cmp #$04
    beq ScummV5_Op_CursorCommand__userput_off
    cmp #$05
    beq ScummV5_Op_CursorCommand__cursor_soft_on
    cmp #$06
    beq ScummV5_Op_CursorCommand__cursor_soft_off
    cmp #$07
    beq ScummV5_Op_CursorCommand__userput_soft_on
    cmp #$08
    bne ScummV5_Op_CursorCommand__check_image
    jmp ScummV5_Op_CursorCommand__userput_soft_off
ScummV5_Op_CursorCommand__check_image:
    .a8
    cmp #$0A
    bne ScummV5_Op_CursorCommand__check_hotspot
    jmp ScummV5_Op_CursorCommand__image
ScummV5_Op_CursorCommand__check_hotspot:
    .a8
    cmp #$0B
    bne ScummV5_Op_CursorCommand__check_cursor_id
    jmp ScummV5_Op_CursorCommand__hotspot
ScummV5_Op_CursorCommand__check_cursor_id:
    .a8
    cmp #$0C
    bne ScummV5_Op_CursorCommand__check_charset_id
    jmp ScummV5_Op_CursorCommand__cursor_id
ScummV5_Op_CursorCommand__check_charset_id:
    .a8
    cmp #$0D
    bne ScummV5_Op_CursorCommand__check_colors
    jmp ScummV5_Op_CursorCommand__charset_id
ScummV5_Op_CursorCommand__check_colors:
    .a8
    cmp #$0E
    bne ScummV5_Op_CursorCommand__unknown
    jmp ScummV5_Op_CursorCommand__colors
ScummV5_Op_CursorCommand__unknown:
    .a8
    lda #SCUMM_ERR_OPCODE
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__cursor_on:
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_off:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_on:
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_off:
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_soft_on:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_CURSOR_STATE
    inc
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_soft_off:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_CURSOR_STATE
    dec
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_soft_on:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_USERPUT_STATE
    inc
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__userput_soft_off:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C7_USERPUT_STATE
    dec
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__image:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__image_first_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__image_first_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_IMAGE
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__image_second_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__image_second_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_CHAR
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__hotspot:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_first_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_first_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_CURSOR
    lda #$40
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_second_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_second_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_X
    lda #$20
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__hotspot_third_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__hotspot_third_ok:
    .a8
    sta.l SAME_SCUMM_C7_HOTSPOT_Y
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__cursor_id:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__cursor_id_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__cursor_id_ok:
    .a8
    sta.l SAME_SCUMM_C7_CURSOR_ID
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__charset_id:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C7_FetchFlaggedByte
    bcc ScummV5_Op_CursorCommand__charset_id_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__charset_id_ok:
    .a8
    sta.l SAME_SCUMM_C7_CHARSET_ID
    jmp ScummV5_Op_CursorCommand__done
ScummV5_Op_CursorCommand__colors:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C7_COLOR_COUNT
ScummV5_Op_CursorCommand__color_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_CursorCommand__color_selector_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_selector_ok:
    .a8
    cmp #$FF
    beq ScummV5_Op_CursorCommand__done
    sta.l SAME_SCUMM_C7_PARAM_INDEX
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    cmp #$10
    bcc ScummV5_Op_CursorCommand__color_room
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    bra ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_room:
    .a8
    lda.l SAME_SCUMM_C7_PARAM_INDEX
    and #$80
    beq ScummV5_Op_CursorCommand__color_direct
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_CursorCommand__color_variable_ref_ok
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_variable_ref_ok:
    .a16
    jsr ScummV5_ReadVariableReference
    bcc ScummV5_Op_CursorCommand__color_store
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_direct:
    jsr ScummV5_FetchWord
    bcc ScummV5_Op_CursorCommand__color_store
    jmp ScummV5_Op_CursorCommand__error
ScummV5_Op_CursorCommand__color_store:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    and #$00FF
    asl
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C7_COLORS,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_COLOR_COUNT
    inc
    sta.l SAME_SCUMM_C7_COLOR_COUNT
    bra ScummV5_Op_CursorCommand__color_loop
ScummV5_Op_CursorCommand__error:
    jmp ScummV5_Op__error
ScummV5_Op_CursorCommand__done:
    sep #$20
    .a8
    lda #$2C
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_Op_StringOps:
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__subop_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__subop_ok:
    .a8
    sta.l SAME_SCUMM_C8_SUBOP
    and #$1F
    cmp #$01
    beq ScummV5_Op_StringOps__load
    cmp #$02
    bne ScummV5_Op_StringOps__check_set
    jmp ScummV5_Op_StringOps__copy
ScummV5_Op_StringOps__check_set:
    .a8
    cmp #$03
    bne ScummV5_Op_StringOps__check_get
    jmp ScummV5_Op_StringOps__set
ScummV5_Op_StringOps__check_get:
    .a8
    cmp #$04
    bne ScummV5_Op_StringOps__check_create
    jmp ScummV5_Op_StringOps__get
ScummV5_Op_StringOps__check_create:
    .a8
    cmp #$05
    bne ScummV5_Op_StringOps__unknown
    jmp ScummV5_Op_StringOps__create
ScummV5_Op_StringOps__unknown:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error

ScummV5_Op_StringOps__load:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__load_id_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__load_loop:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_byte_ok
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_byte_ok:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_stored
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_stored:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    lda.l SAME_SCUMM_C8_VALUE
    beq ScummV5_Op_StringOps__load_done
    cmp #$FF
    beq ScummV5_Op_StringOps__load_control
    bra ScummV5_Op_StringOps__load_loop
ScummV5_Op_StringOps__load_control:
    .a8
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_control_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_control_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_control_stored
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__load_control_stored:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    lda.l SAME_SCUMM_C8_VALUE
    cmp #$01
    beq ScummV5_Op_StringOps__load_loop
    cmp #$02
    beq ScummV5_Op_StringOps__load_loop
    cmp #$03
    beq ScummV5_Op_StringOps__load_loop
    cmp #$08
    beq ScummV5_Op_StringOps__load_loop
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_arg1_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg1_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_arg1_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg1_ok:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    jsr ScummV5_FetchByte
    bcc ScummV5_Op_StringOps__load_arg2_fetched
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg2_fetched:
    .a8
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__load_arg2_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__load_arg2_ok:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    jmp ScummV5_Op_StringOps__load_loop
ScummV5_Op_StringOps__load_done:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    sta.l SAME_SCUMM_C8_SIZES,x
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__create:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__create_id_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__create_size_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_size_ok:
    .a8
    sta.l SAME_SCUMM_C8_LENGTH
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_LENGTH
    sta.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__create_nonempty
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__create_nonempty:
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__create_loop:
    .a8
    lda #$00
    jsr ScummV5_C8_StoreValueAtIndex
    bcc ScummV5_Op_StringOps__create_stored
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__create_stored:
    .a8
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    cmp.l SAME_SCUMM_C8_LENGTH
    bcc ScummV5_Op_StringOps__create_loop
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__copy:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__copy_dest_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__copy_dest_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__copy_source_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__copy_source_ok:
    .a8
    sta.l SAME_SCUMM_C8_SECOND_ID
    cmp.l SAME_SCUMM_C8_STRING_ID
    bne ScummV5_Op_StringOps__copy_distinct
    lda #SCUMM_ERR_ARGUMENTS
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__copy_distinct:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_SECOND_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    sta.l SAME_SCUMM_C8_LENGTH
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_LENGTH
    sta.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__copy_nonempty
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__copy_nonempty:
    .a8
    lda.l SAME_SCUMM_C8_SECOND_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_SOURCE_BASE
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_C8_INDEX
ScummV5_Op_StringOps__copy_loop:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_SOURCE_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    sta.l SAME_SCUMM_C8_VALUE
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_VALUE
    sta.l SAME_SCUMM_C8_DATA,x
    lda.l SAME_SCUMM_C8_INDEX
    inc
    sta.l SAME_SCUMM_C8_INDEX
    cmp.l SAME_SCUMM_C8_LENGTH
    bcc ScummV5_Op_StringOps__copy_loop
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__set:
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_id_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_id_ok:
    .a8
    sta.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_SetDestBase
    sep #$20
    .a8
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_index_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_index_ok:
    .a8
    sta.l SAME_SCUMM_C8_INDEX
    lda #$20
    jsr ScummV5_C8_FetchParam
    bcc ScummV5_Op_StringOps__set_value_ok
    jmp ScummV5_Op_StringOps__error
ScummV5_Op_StringOps__set_value_ok:
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    bne ScummV5_Op_StringOps__set_present
    jmp ScummV5_Op_StringOps__missing
ScummV5_Op_StringOps__set_present:
    .a8
    cmp.l SAME_SCUMM_C8_INDEX
    bcc ScummV5_Op_StringOps__set_oob
    beq ScummV5_Op_StringOps__set_oob
    lda.l SAME_SCUMM_C8_VALUE
    jsr ScummV5_C8_StoreValueAtIndex
    bcs ScummV5_Op_StringOps__error
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__set_oob:
    jmp ScummV5_Op_StringOps__done

ScummV5_Op_StringOps__get:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_Op_StringOps__error
    sep #$20
    .a8
    lda #$80
    jsr ScummV5_C8_FetchParam
    bcs ScummV5_Op_StringOps__error
    sta.l SAME_SCUMM_C8_STRING_ID
    lda #$40
    jsr ScummV5_C8_FetchParam
    bcs ScummV5_Op_StringOps__error
    sta.l SAME_SCUMM_C8_INDEX
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_C8_STRING_ID
    and #$00FF
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_SIZES,x
    beq ScummV5_Op_StringOps__missing
    cmp.l SAME_SCUMM_C8_INDEX
    bcc ScummV5_Op_StringOps__get_zero
    beq ScummV5_Op_StringOps__get_zero
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_DATA,x
    rep #$20
    .a16
    and #$00FF
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__get_zero:
    rep #$20
    .a16
    lda #$0000
    jsr ScummV5_WriteResultValue
    jmp ScummV5_Op_StringOps__done
ScummV5_Op_StringOps__missing:
    .a8
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__error:
    jmp ScummV5_Op__error
ScummV5_Op_StringOps__done:
    sep #$20
    .a8
    lda #$27
    sta.l SAME_SCUMM_LAST_OPCODE
    jmp ScummV5_Engine_Frame__next

ScummV5_C8_FetchParam:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C8_VALUE
    and.l SAME_SCUMM_C8_SUBOP
    beq ScummV5_C8_FetchParam__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C8_FetchParam__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C8_FetchParam__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C8_FetchParam__direct:
    jmp ScummV5_FetchByte
ScummV5_C8_FetchParam__done:
    rts

ScummV5_C8_BaseForId:
    rep #$20
    .a16
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    rts

ScummV5_C8_SetDestBase:
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_STRING_ID
    jsr ScummV5_C8_BaseForId
    sta.l SAME_SCUMM_C8_DEST_BASE
    rts

ScummV5_C8_StoreValueAtIndex:
    rep #$30
    .a16
    .i16
    and #$00FF
    tay
    sep #$20
    .a8
    sta.l SAME_SCUMM_C8_PENDING
    lda.l SAME_SCUMM_C8_INDEX
    cmp #SAME_SCUMM_C8_MAX_BYTES
    bcc ScummV5_C8_StoreValueAtIndex__room
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Source startup contains a long legal-code string whose encoded payload
    ; exceeds the compact 255-byte mutable-string window.  Preserve opcode
    ; consumption and the terminator/control semantics in the bounded target
    ; by dropping bytes beyond the resident window rather than aborting the
    ; enclosing script.  The presentation path is headless for this fixture;
    ; ordinary mutable strings retain the existing bounded storage contract.
    lda.l SAME_SCUMM_C8_PENDING
    clc
    rts
    .else
    lda #SCUMM_ERR_STRING
    jsr ScummV5_SetError
    sec
    rts
    .endif
ScummV5_C8_StoreValueAtIndex__room:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_INDEX
    and #$00FF
    clc
    adc.l SAME_SCUMM_C8_DEST_BASE
    tax
    rep #$20
    .a16
    lda.l SAME_SCUMM_C8_DATA,x
    and #$FF00
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C8_PENDING
    and #$00FF
    ora.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C8_DATA,x
    sep #$20
    .a8
    lda.l SAME_SCUMM_C8_PENDING
    clc
    rts

ScummV5_C8_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C8_ResetState__clear_sizes:
    .a16
    .i16
    sta.l SAME_SCUMM_C8_SIZES,x
    inx
    inx
    cpx #SAME_SCUMM_C8_SIZE_TABLE_BYTES
    bcc ScummV5_C8_ResetState__clear_sizes
    rts

ScummV5_C7_FetchFlaggedByte:
    sep #$20
    .a8
    sta.l SAME_SCUMM_C7_PARAM_INDEX
    and.l SAME_SCUMM_C7_SUBOP
    beq ScummV5_C7_FetchFlaggedByte__direct
    jsr ScummV5_FetchWord
    bcs ScummV5_C7_FetchFlaggedByte__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_C7_FetchFlaggedByte__done
    sep #$20
    .a8
    clc
    rts
ScummV5_C7_FetchFlaggedByte__direct:
    jmp ScummV5_FetchByte
ScummV5_C7_FetchFlaggedByte__done:
    rts

ScummV5_C7_ResetState:
    rep #$30
    .a16
    .i16
    lda #$0000
    ldx #$0000
ScummV5_C7_ResetState__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_C7_CURSOR_STATE,x
    inx
    inx
    cpx #SAME_SCUMM_C7_STATE_SIZE
    bcc ScummV5_C7_ResetState__clear
    lda #$0001
    sta.l SAME_SCUMM_C7_CURSOR_STATE
    sta.l SAME_SCUMM_C7_USERPUT_STATE
    rts

; ---------------------------------------------------------------------------
; Decoder helpers. C1-C3 use sixteen globals; C4 additionally resolves the v5
; $4000 local namespace into the current slot's 32-word local block.
; ---------------------------------------------------------------------------
ScummV5_ReadBinaryOperands:
    rep #$30
    .a16
    .i16
    jsr ScummV5_ReadResultOffset
    bcs ScummV5_ReadBinaryOperands__done
    jsr ScummV5_ReadResultValue
    sta.l SAME_SCUMM_LHS
    jsr ScummV5_FetchVarOrDirectWord
    bcs ScummV5_ReadBinaryOperands__done
    sta.l SAME_SCUMM_OPERAND
    clc
ScummV5_ReadBinaryOperands__done:
    rts

ScummV5_ApplyConditionOffset:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcs ScummV5_ApplyConditionOffset__done
    sta.l SAME_SCUMM_OPERAND
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONDITION
    bne ScummV5_ApplyConditionOffset__success
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    clc
    adc.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_PC
ScummV5_ApplyConditionOffset__success:
    clc
ScummV5_ApplyConditionOffset__done:
    rts

ScummV5_ReadResultOffset:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcc ScummV5_ReadResultOffset__reference_fetched
    rts
ScummV5_ReadResultOffset__reference_fetched:
    .a16
    .i16
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_LHS
    and #$2000
    beq ScummV5_ReadResultOffset__direct
    lda.l SAME_SCUMM_LHS
    and #$0FFF
    sta.l SAME_SCUMM_PRODUCT
    jsr ScummV5_FetchWord
    bcc ScummV5_ReadResultOffset__index_fetched
    rts
ScummV5_ReadResultOffset__index_fetched:
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    and #$2000
    beq ScummV5_ReadResultOffset__literal_index
    ; Preserve the outer namespace/base reference.  Resolving the index is a
    ; nested variable read and therefore reuses SAME_SCUMM_LHS; without this
    ; save an indexed bit reference such as $A000[$6003] is misclassified as
    ; a local reference after the index lookup.
    lda.l SAME_SCUMM_LHS
    pha
    lda.l SAME_SCUMM_OPERAND
    and #$DFFF
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_ReadResultOffset__index_variable_error
    sta.l SAME_SCUMM_OPERAND
    pla
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    bra ScummV5_ReadResultOffset__add_index
ScummV5_ReadResultOffset__index_variable_error:
    pla
    sec
    rts
ScummV5_ReadResultOffset__literal_index:
    .a16
    lda.l SAME_SCUMM_OPERAND
    and #$0FFF
ScummV5_ReadResultOffset__add_index:
    clc
    adc.l SAME_SCUMM_PRODUCT
    bcs ScummV5_ReadResultOffset__variable_error
    bra ScummV5_ReadResultOffset__range_check
ScummV5_ReadResultOffset__direct:
    .a16
    lda.l SAME_SCUMM_LHS
    and #$0FFF
ScummV5_ReadResultOffset__range_check:
    .a16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LHS
    bit #$8000
    bne ScummV5_ReadResultOffset__bit_range
    bit #$4000
    bne ScummV5_ReadResultOffset__local_range
    lda.l SAME_SCUMM_OPERAND
    cmp #SAME_SCUMM_VARIABLE_COUNT
    bcc ScummV5_ReadResultOffset__global_valid
ScummV5_ReadResultOffset__variable_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__bit_range:
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp #$1000
    bcc ScummV5_ReadResultOffset__bit_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_BIT_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__bit_valid:
    .a16
    ora #$4000
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts
ScummV5_ReadResultOffset__local_range:
    .a16
    lda.l SAME_SCUMM_OPERAND
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_ReadResultOffset__local_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadResultOffset__local_valid:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    xba
    lsr
    lsr
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    asl
    clc
    adc.l SAME_SCUMM_LHS
    ora #$8000
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts
ScummV5_ReadResultOffset__global_valid:
    .a16
    lda.l SAME_SCUMM_OPERAND
    .if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
    cmp #$0010
    bcc ScummV5_ReadResultOffset__global_low
    asl
    ora #$2000
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
    rts
ScummV5_ReadResultOffset__global_low:
    .a16
    lda.l SAME_SCUMM_OPERAND
    .endif
    asl
    sta.l SAME_SCUMM_RESULT_OFFSET
    clc
ScummV5_ReadResultOffset__done:
    rts

ScummV5_FetchVarOrDirectWord:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    bne ScummV5_FetchVarOrDirectWord__variable
    rep #$30
    .a16
    .i16
    jmp ScummV5_FetchWord
ScummV5_FetchVarOrDirectWord__variable:
    rep #$30
    .a16
    .i16
    jsr ScummV5_FetchWord
    bcs ScummV5_FetchVarOrDirectWord__done
    jmp ScummV5_ReadVariableReference
ScummV5_FetchVarOrDirectWord__done:
    rts

ScummV5_FetchVarOrDirectByte:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    and #$80
    bne ScummV5_FetchVarOrDirectByte__variable
    jmp ScummV5_FetchByte
ScummV5_FetchVarOrDirectByte__variable:
    jsr ScummV5_FetchWord
    bcs ScummV5_FetchVarOrDirectByte__done
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_FetchVarOrDirectByte__done
    sep #$20
    .a8
    clc
ScummV5_FetchVarOrDirectByte__done:
    rts

ScummV5_ReadVariableReference:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_LHS
    and #$2000
    beq ScummV5_ReadVariableReference__resolved
    lda.l SAME_SCUMM_LHS
    and #$0FFF
    sta.l SAME_SCUMM_PRODUCT
    jsr ScummV5_FetchWord
    bcc ScummV5_ReadVariableReference__index_fetched
    rts
ScummV5_ReadVariableReference__index_fetched:
    .a16
    sta.l SAME_SCUMM_OPERAND
    and #$2000
    beq ScummV5_ReadVariableReference__literal_index
    lda.l SAME_SCUMM_LHS
    pha
    lda.l SAME_SCUMM_OPERAND
    and #$DFFF
    jsr ScummV5_ReadVariableReference
    bcs ScummV5_ReadVariableReference__index_variable_error
    sta.l SAME_SCUMM_OPERAND
    pla
    sta.l SAME_SCUMM_LHS
    lda.l SAME_SCUMM_OPERAND
    bra ScummV5_ReadVariableReference__add_index
ScummV5_ReadVariableReference__index_variable_error:
    pla
    sec
    rts
ScummV5_ReadVariableReference__literal_index:
    .a16
    lda.l SAME_SCUMM_OPERAND
    and #$0FFF
ScummV5_ReadVariableReference__add_index:
    .a16
    clc
    adc.l SAME_SCUMM_PRODUCT
    bcs ScummV5_ReadVariableReference__global_error
    cmp #$1000
    bcs ScummV5_ReadVariableReference__global_error
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_LHS
    and #$C000
    ora.l SAME_SCUMM_OPERAND
    bra ScummV5_ReadVariableReference__dispatch
ScummV5_ReadVariableReference__global_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__resolved:
    .a16
    lda.l SAME_SCUMM_LHS
ScummV5_ReadVariableReference__dispatch:
    .a16
    bit #$8000
    bne ScummV5_ReadVariableReference__bit
    bit #$4000
    bne ScummV5_ReadVariableReference__local
    cmp #SAME_SCUMM_VARIABLE_COUNT
    bcc ScummV5_ReadVariableReference__global_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__bit:
    .a16
    and #$7FFF
    cmp #$1000
    bcc ScummV5_ReadVariableReference__bit_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_BIT_VARIABLE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__bit_valid:
    jmp ScummV5_C7_ReadBit
ScummV5_ReadVariableReference__global_valid:
    .a16
    .i16
    .if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
    cmp #$0010
    bcc ScummV5_ReadVariableReference__global_low
    asl
    tax
    lda.l SAME_SCUMM_M23B_VARIABLES,x
    clc
    rts
ScummV5_ReadVariableReference__global_low:
    .a16
    .i16
    lda.l SAME_SCUMM_LHS
    and #$0FFF
    .endif
    asl
    tax
    lda.l SAME_SCUMM_VARIABLES,x
    clc
    rts
ScummV5_ReadVariableReference__local:
    .a16
    and #$0FFF
    cmp #SAME_SCUMM_LOCAL_COUNT
    bcc ScummV5_ReadVariableReference__local_valid
    sep #$20
    .a8
    lda #SCUMM_ERR_LOCAL
    jsr ScummV5_SetError
    sec
    rts
ScummV5_ReadVariableReference__local_valid:
    .a16
    asl
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    and #$00FF
    xba
    lsr
    lsr
    clc
    adc.l SAME_SCUMM_OPERAND
    tax
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    clc
    rts

ScummV5_ReadResultValue:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_ReadResultValue__bit
    bmi ScummV5_ReadResultValue__local
    .if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
    bit #$2000
    bne ScummV5_ReadResultValue__m23b
    .endif
    tax
    lda.l SAME_SCUMM_VARIABLES,x
    rts
ScummV5_ReadResultValue__local:
    .a16
    and #$7FFF
    tax
    lda.l SAME_SCUMM_C4_SLOT_LOCALS,x
    rts
.if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
ScummV5_ReadResultValue__m23b:
    .a16
    and #$1FFF
    tax
    lda.l SAME_SCUMM_M23B_VARIABLES,x
    rts
.endif
ScummV5_ReadResultValue__bit:
    .a16
    lda.l SAME_SCUMM_RESULT_OFFSET
    and #$0FFF
    jmp ScummV5_C7_ReadBit

ScummV5_WriteResultValue:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_OPERAND
    lda.l SAME_SCUMM_RESULT_OFFSET
    bit #$4000
    bne ScummV5_WriteResultValue__bit
    bmi ScummV5_WriteResultValue__local
    .if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
    bit #$2000
    bne ScummV5_WriteResultValue__m23b
    .endif
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_VARIABLES,x
    rts
ScummV5_WriteResultValue__local:
    .a16
    and #$7FFF
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_C4_SLOT_LOCALS,x
    rts
.if SAME_BUILD_SCUMM_M23B && !SAME_BUILD_SCUMM_PHASE6HB && !SAME_BUILD_SCUMM_PHASE6LA1D
ScummV5_WriteResultValue__m23b:
    .a16
    and #$1FFF
    tax
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_M23B_VARIABLES,x
    rts
.endif
ScummV5_WriteResultValue__bit:
    jmp ScummV5_C7_WriteBitResult

ScummV5_C7_ReadBit:
    rep #$30
    .a16
    .i16
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_BITS,x
    and.l SAME_SCUMM_FETCH_BYTE
    beq ScummV5_C7_ReadBit__zero
    rep #$20
    .a16
    lda #$0001
    clc
    rts
ScummV5_C7_ReadBit__zero:
    rep #$20
    .a16
    lda #$0000
    clc
    rts

ScummV5_C7_WriteBitResult:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_RESULT_OFFSET
    and #$0FFF
    sta.l SAME_SCUMM_LHS
    and #$0007
    tax
    sep #$20
    .a8
    lda.l ScummV5_C7_BitMasks,x
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_OPERAND
    beq ScummV5_C7_WriteBitResult__clear
    sep #$20
    .a8
    lda.l SAME_SCUMM_C7_BITS,x
    ora.l SAME_SCUMM_FETCH_BYTE
    sta.l SAME_SCUMM_C7_BITS,x
    rep #$20
    .a16
    rts
ScummV5_C7_WriteBitResult__clear:
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    eor #$FF
    and.l SAME_SCUMM_C7_BITS,x
    sta.l SAME_SCUMM_C7_BITS,x
    rep #$20
    .a16
    rts

ScummV5_C7_BitMasks:
    .byte $01,$02,$04,$08,$10,$20,$40,$80

ScummV5_FetchWord:
    rep #$10
    .i16
    sep #$20
    .a8
    jsr ScummV5_FetchByte
    bcs ScummV5_FetchWord__done
    sta.l SAME_SCUMM_OPERAND
    jsr ScummV5_FetchByte
    bcs ScummV5_FetchWord__done
    sta.l SAME_SCUMM_OPERAND+1
    rep #$20
    .a16
    lda.l SAME_SCUMM_OPERAND
    clc
ScummV5_FetchWord__done:
    rts

ScummV5_FetchByte:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PC
    tax
    jsr ScummV5_GetProgramSize
    sta.l SAME_SCUMM_PROGRAM_SIZE
    txa
    cmp.l SAME_SCUMM_PROGRAM_SIZE
    bcc ScummV5_FetchByte__valid
    ; C4-owned global/local slots may be resumed at the exact end of a
    ; resource after their terminal opcode was committed.  Treat that as the
    ; scheduler's normal stop boundary; room slot zero keeps the strict fault
    ; below so malformed room payloads remain diagnosable.
    sep #$20
    .a8
    lda.l SAME_SCUMM_C4_CURRENT_SLOT
    beq ScummV5_FetchByte__range_error
    lda #$A0
    clc
    rts
ScummV5_FetchByte__range_error:
    sep #$20
    .a8
    lda #SCUMM_ERR_PC_RANGE
    jsr ScummV5_SetError
    sec
    rts
ScummV5_FetchByte__valid:
    sep #$20
    .a8
    jsr ScummV5_FetchSelectedByteAtX
    sta.l SAME_SCUMM_FETCH_BYTE
    rep #$20
    .a16
    txa
    inc
    sta.l SAME_SCUMM_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_FETCH_BYTE
    clc
    rts

ScummV5_GetProgramSize:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    .if SAME_BUILD_SCUMM_M23A
    jsr ScummV5_M23A_GetProgramSize
    bcs ScummV5_GetProgramSize__m23a
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    .endif
    cmp #SCUMM_C2_FIXTURE_EXTENDED
    bne ScummV5_GetProgramSize__unknown
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_EXTENDED_SIZE
    rts
    .if SAME_BUILD_SCUMM_M23A
ScummV5_GetProgramSize__m23a:
    rts
    .endif
ScummV5_GetProgramSize__unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_UNKNOWN_OPCODE
    bne ScummV5_GetProgramSize__bad_variable
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_UNKNOWN_OPCODE_SIZE
    rts
ScummV5_GetProgramSize__bad_variable:
    .a8
    cmp #SCUMM_C2_FIXTURE_BAD_VARIABLE
    bne ScummV5_GetProgramSize__truncated
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_BAD_VARIABLE_SIZE
    rts
ScummV5_GetProgramSize__truncated:
    .a8
    cmp #SCUMM_C2_FIXTURE_TRUNCATED_OPERAND
    bne ScummV5_GetProgramSize__budget
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_TRUNCATED_OPERAND_SIZE
    rts
ScummV5_GetProgramSize__budget:
    .a8
    cmp #SCUMM_C2_FIXTURE_BUDGET_EXHAUSTION
    bne ScummV5_GetProgramSize__divide_zero
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_BUDGET_EXHAUSTION_SIZE
    rts
ScummV5_GetProgramSize__divide_zero:
    .a8
    cmp #SCUMM_C2_FIXTURE_DIVISION_BY_ZERO
    bne ScummV5_GetProgramSize__jump_escape
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_DIVISION_BY_ZERO_SIZE
    rts
ScummV5_GetProgramSize__jump_escape:
    .a8
    cmp #SCUMM_C2_FIXTURE_JUMP_ESCAPE
    bne ScummV5_GetProgramSize__delay_range
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_JUMP_ESCAPE_SIZE
    rts
ScummV5_GetProgramSize__delay_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_DELAY_RANGE
    bne ScummV5_GetProgramSize__c3_operands
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_DELAY_RANGE_SIZE
    rts
ScummV5_GetProgramSize__c3_operands:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_OPERANDS
    bne ScummV5_GetProgramSize__c3_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_OPERANDS_SIZE
    rts
ScummV5_GetProgramSize__c3_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    bne ScummV5_GetProgramSize__c3_slot0
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c3_slot0:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT0
    bne ScummV5_GetProgramSize__c3_slot1
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SLOT0_SIZE
    rts
ScummV5_GetProgramSize__c3_slot1:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT1
    bne ScummV5_GetProgramSize__c3_bit
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_SLOT1_SIZE
    rts
ScummV5_GetProgramSize__c3_bit:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_BIT_VARIABLE
    bne ScummV5_GetProgramSize__c4_lifecycle
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C3_BIT_VARIABLE_SIZE
    rts
ScummV5_GetProgramSize__c4_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    bne ScummV5_GetProgramSize__c4_child2
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_LIFECYCLE_SIZE
    rts
ScummV5_GetProgramSize__c4_child2:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD2
    bne ScummV5_GetProgramSize__c4_child3
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD2_SIZE
    rts
ScummV5_GetProgramSize__c4_child3:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD3
    bne ScummV5_GetProgramSize__c4_child4
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD3_SIZE
    rts
ScummV5_GetProgramSize__c4_child4:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD4
    bne ScummV5_GetProgramSize__c4_capacity
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CHILD4_SIZE
    rts
ScummV5_GetProgramSize__c4_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    bne ScummV5_GetProgramSize__c5_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C4_CAPACITY_SIZE
    rts
ScummV5_GetProgramSize__c5_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    bne ScummV5_GetProgramSize__c5_child5
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c5_child5:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD5
    bne ScummV5_GetProgramSize__c5_child6
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD5_SIZE
    rts
ScummV5_GetProgramSize__c5_child6:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD6
    bne ScummV5_GetProgramSize__c5_child7
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD6_SIZE
    rts
ScummV5_GetProgramSize__c5_child7:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD7
    bne ScummV5_GetProgramSize__c6_scheduler
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C5_CHILD7_SIZE
    rts
ScummV5_GetProgramSize__c6_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_GetProgramSize__c6_chain10
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_SCHEDULER_SIZE
    rts
ScummV5_GetProgramSize__c6_chain10:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN10
    bne ScummV5_GetProgramSize__c6_target12
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CHAIN10_SIZE
    rts
ScummV5_GetProgramSize__c6_target12:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET12
    bne ScummV5_GetProgramSize__c6_chain11
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_TARGET12_SIZE
    rts
ScummV5_GetProgramSize__c6_chain11:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN11
    bne ScummV5_GetProgramSize__c6_target13
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CHAIN11_SIZE
    rts
ScummV5_GetProgramSize__c6_target13:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET13
    bne ScummV5_GetProgramSize__c6_missing
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_TARGET13_SIZE
    rts
ScummV5_GetProgramSize__c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_GetProgramSize__c6_capacity
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_MISSING_SIZE
    rts
ScummV5_GetProgramSize__c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_GetProgramSize__s5_binding
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C6_CAPACITY_SIZE
    rts
ScummV5_GetProgramSize__s5_binding:
    .a8
    cmp #SCUMM_C2_FIXTURE_S5_BINDING
    bne ScummV5_GetProgramSize__c7_cursor_bits
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_S5_BINDING_SIZE
    rts
ScummV5_GetProgramSize__c7_cursor_bits:
    .a8
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    bne ScummV5_GetProgramSize__c8_string_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C7_CURSOR_BITS_SIZE
    rts
ScummV5_GetProgramSize__c8_string_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_GetProgramSize__c9_set_var_range
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C8_STRING_OPS_SIZE
    rts
ScummV5_GetProgramSize__c9_set_var_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_GetProgramSize__c10_room_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C9_SET_VAR_RANGE_SIZE
    rts
ScummV5_GetProgramSize__c10_room_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_GetProgramSize__c11_random
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C10_ROOM_OPS_SIZE
    rts
ScummV5_GetProgramSize__c11_random:
    .a8
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_GetProgramSize__c12_pseudo_room
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C11_RANDOM_SIZE
    rts
ScummV5_GetProgramSize__c12_pseudo_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_GetProgramSize__c13_resource_routines
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C12_PSEUDO_ROOM_SIZE
    rts
ScummV5_GetProgramSize__c13_resource_routines:
    .a8
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_GetProgramSize__c14_actor_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C13_RESOURCE_ROUTINES_SIZE
    rts
ScummV5_GetProgramSize__c14_actor_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    bne ScummV5_GetProgramSize__c15_actor_follow_camera
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C14_ACTOR_OPS_SIZE
    rts
ScummV5_GetProgramSize__c15_actor_follow_camera:
    .a8
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_GetProgramSize__c16_set_class
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C15_ACTOR_FOLLOW_CAMERA_SIZE
    rts
ScummV5_GetProgramSize__c16_set_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    bne ScummV5_GetProgramSize__c17_verb_ops
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C16_SET_CLASS_SIZE
    rts
ScummV5_GetProgramSize__c17_verb_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    bne ScummV5_GetProgramSize__c18_expression
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C17_VERB_OPS_SIZE
    rts
ScummV5_GetProgramSize__c18_expression:
    .a8
    cmp #SCUMM_C2_FIXTURE_C18_EXPRESSION
    bne ScummV5_GetProgramSize__c19_cutscene
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C18_EXPRESSION_SIZE
    rts
ScummV5_GetProgramSize__c19_cutscene:
    .a8
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_GetProgramSize__c20_do_sentence
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C19_CUTSCENE_SIZE
    rts
ScummV5_GetProgramSize__c20_do_sentence:
    .a8
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_GetProgramSize__c21_draw_object
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C20_DO_SENTENCE_SIZE
    rts
ScummV5_GetProgramSize__c21_draw_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    bne ScummV5_GetProgramSize__c22_null_room
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C21_DRAW_OBJECT_SIZE
    rts
ScummV5_GetProgramSize__c22_null_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    bne ScummV5_GetProgramSize__c23_print
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C22_NULL_ROOM_SIZE
    rts
ScummV5_GetProgramSize__c23_print:
    .a8
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_GetProgramSize__c24_override_sentinel
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C23_PRINT_SIZE
    rts
ScummV5_GetProgramSize__c24_override_sentinel:
    .a8
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_GetProgramSize__c25_sound_kludge
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C24_OVERRIDE_SENTINEL_SIZE
    rts
ScummV5_GetProgramSize__c25_sound_kludge:
    .a8
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_GetProgramSize__c26_save_restore_verbs
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C25_SOUND_KLUDGE_SIZE
    rts
ScummV5_GetProgramSize__c26_save_restore_verbs:
    .a8
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_GetProgramSize__c28_animate_actor
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C26_SAVE_RESTORE_VERBS_SIZE
    rts
ScummV5_GetProgramSize__c28_animate_actor:
    .a8
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    bne ScummV5_GetProgramSize__c29_actor_from_pos
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C28_ANIMATE_ACTOR_SIZE
    rts
ScummV5_GetProgramSize__c29_actor_from_pos:
    .a8
    cmp #SCUMM_C2_FIXTURE_C29_ACTOR_FROM_POS
    bne ScummV5_GetProgramSize__c30_find_object
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C29_ACTOR_FROM_POS_SIZE
    rts
ScummV5_GetProgramSize__c30_find_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C30_FIND_OBJECT
    bne ScummV5_GetProgramSize__c31_put_actor_in_room
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C30_FIND_OBJECT_SIZE
    rts
ScummV5_GetProgramSize__c31_put_actor_in_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C31_PUT_ACTOR_IN_ROOM
    bne ScummV5_GetProgramSize__c32_put_actor_at_object
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C31_PUT_ACTOR_IN_ROOM_SIZE
    rts
ScummV5_GetProgramSize__c32_put_actor_at_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C32_PUT_ACTOR_AT_OBJECT
    .if SAME_BUILD_SCUMM_M23A == 0
    bne ScummV5_GetProgramSize__matrix_set_box_flags
    .else
    .if SAME_BUILD_SCUMM_M19
    bne ScummV5_GetProgramSize__m19_monkey_music
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_C32_PUT_ACTOR_AT_OBJECT_SIZE
    rts
    .if SAME_BUILD_SCUMM_M23A == 0
ScummV5_GetProgramSize__matrix_set_box_flags:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SET_BOX_FLAGS
    bne ScummV5_GetProgramSize__matrix_missing
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_SET_BOX_FLAGS_SIZE
    rts
ScummV5_GetProgramSize__matrix_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_MISSING
    bne ScummV5_GetProgramSize__matrix_invalid
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_MISSING_SIZE
    rts
ScummV5_GetProgramSize__matrix_invalid:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_INVALID
    bne ScummV5_GetProgramSize__matrix_subop2
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_INVALID_SIZE
    rts
ScummV5_GetProgramSize__matrix_subop2:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP2
    bne ScummV5_GetProgramSize__matrix_subop3
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_SUBOP2_SIZE
    rts
ScummV5_GetProgramSize__matrix_subop3:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP3
    bne ScummV5_GetProgramSize__matrix_subop4
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_SUBOP3_SIZE
    rts
ScummV5_GetProgramSize__matrix_subop4:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP4
    bne ScummV5_GetProgramSize__matrix_unknown
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_SUBOP4_SIZE
    rts
ScummV5_GetProgramSize__matrix_unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_UNKNOWN
    .if SAME_BUILD_SCUMM_M19
    bne ScummV5_GetProgramSize__m19_monkey_music
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_MATRIX_UNKNOWN_SIZE
    rts
    .endif
    .if SAME_BUILD_SCUMM_M19
ScummV5_GetProgramSize__m19_monkey_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M19_MONKEY_MUSIC
    .if SAME_BUILD_SCUMM_M20
    bne ScummV5_GetProgramSize__m20_start_music
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M19_MONKEY_MUSIC_SIZE
    rts
    .if SAME_BUILD_SCUMM_M20
ScummV5_GetProgramSize__m20_start_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_START_MUSIC
    bne ScummV5_GetProgramSize__m20_save_music
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M20_START_MUSIC_SIZE
    rts
ScummV5_GetProgramSize__m20_save_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_SAVE_MUSIC
    bne ScummV5_GetProgramSize__m20_load_music
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M20_SAVE_MUSIC_SIZE
    rts
ScummV5_GetProgramSize__m20_load_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_LOAD_MUSIC
    bne ScummV5_GetProgramSize__m20_stop_save_music
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M20_LOAD_MUSIC_SIZE
    rts
ScummV5_GetProgramSize__m20_stop_save_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_STOP_SAVE_MUSIC
    .if SAME_BUILD_SCUMM_M21
    bne ScummV5_GetProgramSize__m21_fate_room49_hook14
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M20_STOP_SAVE_MUSIC_SIZE
    rts
    .if SAME_BUILD_SCUMM_M21
ScummV5_GetProgramSize__m21_fate_room49_hook14:
    .a8
    cmp #SCUMM_C2_FIXTURE_M21_FATE_ROOM49_HOOK14
    .if SAME_BUILD_SCUMM_M22
    bne ScummV5_GetProgramSize__m22_hooked
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M21_FATE_ROOM49_HOOK14_SIZE
    rts
    .if SAME_BUILD_SCUMM_M22
ScummV5_GetProgramSize__m22_hooked:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_FATE_ROOM49_ROOM63_HOOK8
    bne ScummV5_GetProgramSize__m22_control
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M22_FATE_ROOM49_ROOM63_HOOK8_SIZE
    rts
ScummV5_GetProgramSize__m22_control:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_FATE_ROOM49_NO_HOOK8
    bne ScummV5_GetProgramSize__m22_load
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M22_FATE_ROOM49_NO_HOOK8_SIZE
    rts
ScummV5_GetProgramSize__m22_load:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_LOAD_MUSIC
    bne ScummV5_GetProgramSize__m22_lifetime
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M22_LOAD_MUSIC_SIZE
    rts
ScummV5_GetProgramSize__m22_lifetime:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_HOOK8_LIFETIME
    .if SAME_BUILD_SCUMM_M23A
    bne ScummV5_GetProgramSize__m23a_room49
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M22_HOOK8_LIFETIME_SIZE
    rts
    .if SAME_BUILD_SCUMM_M23A
ScummV5_GetProgramSize__m23a_room49:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_AUTH_ROOM49
    bne ScummV5_GetProgramSize__m23a_room63
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M23A_AUTH_ROOM49_SIZE
    rts
ScummV5_GetProgramSize__m23a_room63:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_AUTH_ROOM63
    bne ScummV5_GetProgramSize__m23a_lifecycle
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M23A_AUTH_ROOM63_SIZE
    rts
ScummV5_GetProgramSize__m23a_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_LIFECYCLE
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE
    bne ScummV5_GetProgramSize__m23c_if_class
    .else
    bne ScummV5_GetProgramSize__c1
    .endif
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M23A_LIFECYCLE_SIZE
    rts
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE
ScummV5_GetProgramSize__m23c_if_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS
    bne ScummV5_GetProgramSize__m23c_if_class_malformed
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M23C_IF_CLASS_SIZE
    rts
ScummV5_GetProgramSize__m23c_if_class_malformed:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS_MALFORMED
    bne ScummV5_GetProgramSize__c1
    rep #$20
    .a16
    lda #SCUMM_C2_PROGRAM_M23C_IF_CLASS_MALFORMED_SIZE
    rts
    .endif
    .endif
    .endif
    .endif
    .endif
    .endif
ScummV5_GetProgramSize__c1:
    rep #$20
    .a16
    lda #SCUMM_V5_CONFORMANCE_PROGRAM_SIZE
    rts

ScummV5_FetchSelectedByteAtX:
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    .if SAME_BUILD_SCUMM_M23A
    jsr ScummV5_M23A_FetchProgramByte
    bcc ScummV5_FetchSelectedByteAtX__m23a
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    .endif
    cmp #SCUMM_C2_FIXTURE_EXTENDED
    bne ScummV5_FetchSelectedByteAtX__unknown
    lda.l ScummV5_C2_Program_extended,x
    rts
    .if SAME_BUILD_SCUMM_M23A
ScummV5_FetchSelectedByteAtX__m23a:
    rts
    .endif
ScummV5_FetchSelectedByteAtX__unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_UNKNOWN_OPCODE
    bne ScummV5_FetchSelectedByteAtX__bad_variable
    lda.l ScummV5_C2_Program_unknown_opcode,x
    rts
ScummV5_FetchSelectedByteAtX__bad_variable:
    .a8
    cmp #SCUMM_C2_FIXTURE_BAD_VARIABLE
    bne ScummV5_FetchSelectedByteAtX__truncated
    lda.l ScummV5_C2_Program_bad_variable,x
    rts
ScummV5_FetchSelectedByteAtX__truncated:
    .a8
    cmp #SCUMM_C2_FIXTURE_TRUNCATED_OPERAND
    bne ScummV5_FetchSelectedByteAtX__budget
    lda.l ScummV5_C2_Program_truncated_operand,x
    rts
ScummV5_FetchSelectedByteAtX__budget:
    .a8
    cmp #SCUMM_C2_FIXTURE_BUDGET_EXHAUSTION
    bne ScummV5_FetchSelectedByteAtX__divide_zero
    lda.l ScummV5_C2_Program_budget_exhaustion,x
    rts
ScummV5_FetchSelectedByteAtX__divide_zero:
    .a8
    cmp #SCUMM_C2_FIXTURE_DIVISION_BY_ZERO
    bne ScummV5_FetchSelectedByteAtX__jump_escape
    lda.l ScummV5_C2_Program_division_by_zero,x
    rts
ScummV5_FetchSelectedByteAtX__jump_escape:
    .a8
    cmp #SCUMM_C2_FIXTURE_JUMP_ESCAPE
    bne ScummV5_FetchSelectedByteAtX__delay_range
    lda.l ScummV5_C2_Program_jump_escape,x
    rts
ScummV5_FetchSelectedByteAtX__delay_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_DELAY_RANGE
    bne ScummV5_FetchSelectedByteAtX__c3_operands
    lda.l ScummV5_C2_Program_delay_range,x
    rts
ScummV5_FetchSelectedByteAtX__c3_operands:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_OPERANDS
    bne ScummV5_FetchSelectedByteAtX__c3_scheduler
    lda.l ScummV5_C2_Program_c3_operands,x
    rts
ScummV5_FetchSelectedByteAtX__c3_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c3_slot0
    lda.l ScummV5_C2_Program_c3_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c3_slot0:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT0
    bne ScummV5_FetchSelectedByteAtX__c3_slot1
    lda.l ScummV5_C2_Program_c3_slot0,x
    rts
ScummV5_FetchSelectedByteAtX__c3_slot1:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_SLOT1
    bne ScummV5_FetchSelectedByteAtX__c3_bit
    lda.l ScummV5_C2_Program_c3_slot1,x
    rts
ScummV5_FetchSelectedByteAtX__c3_bit:
    .a8
    cmp #SCUMM_C2_FIXTURE_C3_BIT_VARIABLE
    bne ScummV5_FetchSelectedByteAtX__c4_lifecycle
    lda.l ScummV5_C2_Program_c3_bit_variable,x
    rts
ScummV5_FetchSelectedByteAtX__c4_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_LIFECYCLE
    bne ScummV5_FetchSelectedByteAtX__c4_child2
    lda.l ScummV5_C2_Program_c4_lifecycle,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child2:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD2
    bne ScummV5_FetchSelectedByteAtX__c4_child3
    lda.l ScummV5_C2_Program_c4_child2,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child3:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD3
    bne ScummV5_FetchSelectedByteAtX__c4_child4
    lda.l ScummV5_C2_Program_c4_child3,x
    rts
ScummV5_FetchSelectedByteAtX__c4_child4:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CHILD4
    bne ScummV5_FetchSelectedByteAtX__c4_capacity
    lda.l ScummV5_C2_Program_c4_child4,x
    rts
ScummV5_FetchSelectedByteAtX__c4_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C4_CAPACITY
    bne ScummV5_FetchSelectedByteAtX__c5_scheduler
    lda.l ScummV5_C2_Program_c4_capacity,x
    rts
ScummV5_FetchSelectedByteAtX__c5_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c5_child5
    lda.l ScummV5_C2_Program_c5_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child5:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD5
    bne ScummV5_FetchSelectedByteAtX__c5_child6
    lda.l ScummV5_C2_Program_c5_child5,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child6:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD6
    bne ScummV5_FetchSelectedByteAtX__c5_child7
    lda.l ScummV5_C2_Program_c5_child6,x
    rts
ScummV5_FetchSelectedByteAtX__c5_child7:
    .a8
    cmp #SCUMM_C2_FIXTURE_C5_CHILD7
    bne ScummV5_FetchSelectedByteAtX__c6_scheduler
    lda.l ScummV5_C2_Program_c5_child7,x
    rts
ScummV5_FetchSelectedByteAtX__c6_scheduler:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_SCHEDULER
    bne ScummV5_FetchSelectedByteAtX__c6_chain10
    lda.l ScummV5_C2_Program_c6_scheduler,x
    rts
ScummV5_FetchSelectedByteAtX__c6_chain10:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN10
    bne ScummV5_FetchSelectedByteAtX__c6_target12
    lda.l ScummV5_C2_Program_c6_chain10,x
    rts
ScummV5_FetchSelectedByteAtX__c6_target12:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET12
    bne ScummV5_FetchSelectedByteAtX__c6_chain11
    lda.l ScummV5_C2_Program_c6_target12,x
    rts
ScummV5_FetchSelectedByteAtX__c6_chain11:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CHAIN11
    bne ScummV5_FetchSelectedByteAtX__c6_target13
    lda.l ScummV5_C2_Program_c6_chain11,x
    rts
ScummV5_FetchSelectedByteAtX__c6_target13:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_TARGET13
    bne ScummV5_FetchSelectedByteAtX__c6_missing
    lda.l ScummV5_C2_Program_c6_target13,x
    rts
ScummV5_FetchSelectedByteAtX__c6_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_MISSING
    bne ScummV5_FetchSelectedByteAtX__c6_capacity
    lda.l ScummV5_C2_Program_c6_missing,x
    rts
ScummV5_FetchSelectedByteAtX__c6_capacity:
    .a8
    cmp #SCUMM_C2_FIXTURE_C6_CAPACITY
    bne ScummV5_FetchSelectedByteAtX__s5_binding
    lda.l ScummV5_C2_Program_c6_capacity,x
    rts
ScummV5_FetchSelectedByteAtX__s5_binding:
    .a8
    cmp #SCUMM_C2_FIXTURE_S5_BINDING
    bne ScummV5_FetchSelectedByteAtX__c7_cursor_bits
    lda.l ScummV5_C2_Program_s5_binding,x
    rts
ScummV5_FetchSelectedByteAtX__c7_cursor_bits:
    .a8
    cmp #SCUMM_C2_FIXTURE_C7_CURSOR_BITS
    bne ScummV5_FetchSelectedByteAtX__c8_string_ops
    lda.l ScummV5_C2_Program_c7_cursor_bits,x
    rts
ScummV5_FetchSelectedByteAtX__c8_string_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C8_STRING_OPS
    bne ScummV5_FetchSelectedByteAtX__c9_set_var_range
    lda.l ScummV5_C2_Program_c8_string_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c9_set_var_range:
    .a8
    cmp #SCUMM_C2_FIXTURE_C9_SET_VAR_RANGE
    bne ScummV5_FetchSelectedByteAtX__c10_room_ops
    lda.l ScummV5_C2_Program_c9_set_var_range,x
    rts
ScummV5_FetchSelectedByteAtX__c10_room_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C10_ROOM_OPS
    bne ScummV5_FetchSelectedByteAtX__c11_random
    lda.l ScummV5_C2_Program_c10_room_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c11_random:
    .a8
    cmp #SCUMM_C2_FIXTURE_C11_RANDOM
    bne ScummV5_FetchSelectedByteAtX__c12_pseudo_room
    lda.l ScummV5_C2_Program_c11_random,x
    rts
ScummV5_FetchSelectedByteAtX__c12_pseudo_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C12_PSEUDO_ROOM
    bne ScummV5_FetchSelectedByteAtX__c13_resource_routines
    lda.l ScummV5_C2_Program_c12_pseudo_room,x
    rts
ScummV5_FetchSelectedByteAtX__c13_resource_routines:
    .a8
    cmp #SCUMM_C2_FIXTURE_C13_RESOURCE_ROUTINES
    bne ScummV5_FetchSelectedByteAtX__c14_actor_ops
    lda.l ScummV5_C2_Program_c13_resource_routines,x
    rts
ScummV5_FetchSelectedByteAtX__c14_actor_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C14_ACTOR_OPS
    bne ScummV5_FetchSelectedByteAtX__c15_actor_follow_camera
    lda.l ScummV5_C2_Program_c14_actor_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c15_actor_follow_camera:
    .a8
    cmp #SCUMM_C2_FIXTURE_C15_ACTOR_FOLLOW_CAMERA
    bne ScummV5_FetchSelectedByteAtX__c16_set_class
    lda.l ScummV5_C2_Program_c15_actor_follow_camera,x
    rts
ScummV5_FetchSelectedByteAtX__c16_set_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_C16_SET_CLASS
    bne ScummV5_FetchSelectedByteAtX__c17_verb_ops
    lda.l ScummV5_C2_Program_c16_set_class,x
    rts
ScummV5_FetchSelectedByteAtX__c17_verb_ops:
    .a8
    cmp #SCUMM_C2_FIXTURE_C17_VERB_OPS
    bne ScummV5_FetchSelectedByteAtX__c18_expression
    lda.l ScummV5_C2_Program_c17_verb_ops,x
    rts
ScummV5_FetchSelectedByteAtX__c18_expression:
    .a8
    cmp #SCUMM_C2_FIXTURE_C18_EXPRESSION
    bne ScummV5_FetchSelectedByteAtX__c19_cutscene
    lda.l ScummV5_C2_Program_c18_expression,x
    rts
ScummV5_FetchSelectedByteAtX__c19_cutscene:
    .a8
    cmp #SCUMM_C2_FIXTURE_C19_CUTSCENE
    bne ScummV5_FetchSelectedByteAtX__c20_do_sentence
    lda.l ScummV5_C2_Program_c19_cutscene,x
    rts
ScummV5_FetchSelectedByteAtX__c20_do_sentence:
    .a8
    cmp #SCUMM_C2_FIXTURE_C20_DO_SENTENCE
    bne ScummV5_FetchSelectedByteAtX__c21_draw_object
    lda.l ScummV5_C2_Program_c20_do_sentence,x
    rts
ScummV5_FetchSelectedByteAtX__c21_draw_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C21_DRAW_OBJECT
    bne ScummV5_FetchSelectedByteAtX__c22_null_room
    lda.l ScummV5_C2_Program_c21_draw_object,x
    rts
ScummV5_FetchSelectedByteAtX__c22_null_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C22_NULL_ROOM
    bne ScummV5_FetchSelectedByteAtX__c23_print
    lda.l ScummV5_C2_Program_c22_null_room,x
    rts
ScummV5_FetchSelectedByteAtX__c23_print:
    .a8
    cmp #SCUMM_C2_FIXTURE_C23_PRINT
    bne ScummV5_FetchSelectedByteAtX__c24_override_sentinel
    lda.l ScummV5_C2_Program_c23_print,x
    rts
ScummV5_FetchSelectedByteAtX__c24_override_sentinel:
    .a8
    cmp #SCUMM_C2_FIXTURE_C24_OVERRIDE_SENTINEL
    bne ScummV5_FetchSelectedByteAtX__c25_sound_kludge
    lda.l ScummV5_C2_Program_c24_override_sentinel,x
    rts
ScummV5_FetchSelectedByteAtX__c25_sound_kludge:
    .a8
    cmp #SCUMM_C2_FIXTURE_C25_SOUND_KLUDGE
    bne ScummV5_FetchSelectedByteAtX__c26_save_restore_verbs
    lda.l ScummV5_C2_Program_c25_sound_kludge,x
    rts
ScummV5_FetchSelectedByteAtX__c26_save_restore_verbs:
    .a8
    cmp #SCUMM_C2_FIXTURE_C26_SAVE_RESTORE_VERBS
    bne ScummV5_FetchSelectedByteAtX__c28_animate_actor
    lda.l ScummV5_C2_Program_c26_save_restore_verbs,x
    rts
ScummV5_FetchSelectedByteAtX__c28_animate_actor:
    .a8
    cmp #SCUMM_C2_FIXTURE_C28_ANIMATE_ACTOR
    bne ScummV5_FetchSelectedByteAtX__c29_actor_from_pos
    lda.l ScummV5_C2_Program_c28_animate_actor,x
    rts
ScummV5_FetchSelectedByteAtX__c29_actor_from_pos:
    .a8
    cmp #SCUMM_C2_FIXTURE_C29_ACTOR_FROM_POS
    bne ScummV5_FetchSelectedByteAtX__c30_find_object
    lda.l ScummV5_C2_Program_c29_actor_from_pos,x
    rts
ScummV5_FetchSelectedByteAtX__c30_find_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C30_FIND_OBJECT
    bne ScummV5_FetchSelectedByteAtX__c31_put_actor_in_room
    lda.l ScummV5_C2_Program_c30_find_object,x
    rts
ScummV5_FetchSelectedByteAtX__c31_put_actor_in_room:
    .a8
    cmp #SCUMM_C2_FIXTURE_C31_PUT_ACTOR_IN_ROOM
    bne ScummV5_FetchSelectedByteAtX__c32_put_actor_at_object
    lda.l ScummV5_C2_Program_c31_put_actor_in_room,x
    rts
ScummV5_FetchSelectedByteAtX__c32_put_actor_at_object:
    .a8
    cmp #SCUMM_C2_FIXTURE_C32_PUT_ACTOR_AT_OBJECT
    .if SAME_BUILD_SCUMM_M23A == 0
    bne ScummV5_FetchSelectedByteAtX__matrix_set_box_flags
    .else
    .if SAME_BUILD_SCUMM_M19
    bne ScummV5_FetchSelectedByteAtX__m19_monkey_music
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    .endif
    lda.l ScummV5_C2_Program_c32_put_actor_at_object,x
    rts
    .if SAME_BUILD_SCUMM_M23A == 0
ScummV5_FetchSelectedByteAtX__matrix_set_box_flags:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SET_BOX_FLAGS
    bne ScummV5_FetchSelectedByteAtX__matrix_missing
    lda.l ScummV5_C2_Program_matrix_set_box_flags,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_missing:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_MISSING
    bne ScummV5_FetchSelectedByteAtX__matrix_invalid
    lda.l ScummV5_C2_Program_matrix_missing,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_invalid:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_INVALID
    bne ScummV5_FetchSelectedByteAtX__matrix_subop2
    lda.l ScummV5_C2_Program_matrix_invalid,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_subop2:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP2
    bne ScummV5_FetchSelectedByteAtX__matrix_subop3
    lda.l ScummV5_C2_Program_matrix_subop2,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_subop3:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP3
    bne ScummV5_FetchSelectedByteAtX__matrix_subop4
    lda.l ScummV5_C2_Program_matrix_subop3,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_subop4:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_SUBOP4
    bne ScummV5_FetchSelectedByteAtX__matrix_unknown
    lda.l ScummV5_C2_Program_matrix_subop4,x
    rts
ScummV5_FetchSelectedByteAtX__matrix_unknown:
    .a8
    cmp #SCUMM_C2_FIXTURE_MATRIX_UNKNOWN
    .if SAME_BUILD_SCUMM_M19
    bne ScummV5_FetchSelectedByteAtX__m19_monkey_music
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_matrix_unknown,x
    rts
    .endif
    .if SAME_BUILD_SCUMM_M19
ScummV5_FetchSelectedByteAtX__m19_monkey_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M19_MONKEY_MUSIC
    .if SAME_BUILD_SCUMM_M20
    bne ScummV5_FetchSelectedByteAtX__m20_start_music
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_m19_monkey_music,x
    rts
    .if SAME_BUILD_SCUMM_M20
ScummV5_FetchSelectedByteAtX__m20_start_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_START_MUSIC
    bne ScummV5_FetchSelectedByteAtX__m20_save_music
    lda.l ScummV5_C2_Program_m20_start_music,x
    rts
ScummV5_FetchSelectedByteAtX__m20_save_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_SAVE_MUSIC
    bne ScummV5_FetchSelectedByteAtX__m20_load_music
    lda.l ScummV5_C2_Program_m20_save_music,x
    rts
ScummV5_FetchSelectedByteAtX__m20_load_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_LOAD_MUSIC
    bne ScummV5_FetchSelectedByteAtX__m20_stop_save_music
    lda.l ScummV5_C2_Program_m20_load_music,x
    rts
ScummV5_FetchSelectedByteAtX__m20_stop_save_music:
    .a8
    cmp #SCUMM_C2_FIXTURE_M20_STOP_SAVE_MUSIC
    .if SAME_BUILD_SCUMM_M21
    bne ScummV5_FetchSelectedByteAtX__m21_fate_room49_hook14
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_m20_stop_save_music,x
    rts
    .if SAME_BUILD_SCUMM_M21
ScummV5_FetchSelectedByteAtX__m21_fate_room49_hook14:
    .a8
    cmp #SCUMM_C2_FIXTURE_M21_FATE_ROOM49_HOOK14
    .if SAME_BUILD_SCUMM_M22
    bne ScummV5_FetchSelectedByteAtX__m22_hooked
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_m21_fate_room49_hook14,x
    rts
    .if SAME_BUILD_SCUMM_M22
ScummV5_FetchSelectedByteAtX__m22_hooked:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_FATE_ROOM49_ROOM63_HOOK8
    bne ScummV5_FetchSelectedByteAtX__m22_control
    lda.l ScummV5_C2_Program_m22_fate_room49_room63_hook8,x
    rts
ScummV5_FetchSelectedByteAtX__m22_control:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_FATE_ROOM49_NO_HOOK8
    bne ScummV5_FetchSelectedByteAtX__m22_load
    lda.l ScummV5_C2_Program_m22_fate_room49_no_hook8,x
    rts
ScummV5_FetchSelectedByteAtX__m22_load:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_LOAD_MUSIC
    bne ScummV5_FetchSelectedByteAtX__m22_lifetime
    lda.l ScummV5_C2_Program_m22_load_music,x
    rts
ScummV5_FetchSelectedByteAtX__m22_lifetime:
    .a8
    cmp #SCUMM_C2_FIXTURE_M22_HOOK8_LIFETIME
    .if SAME_BUILD_SCUMM_M23A
    bne ScummV5_FetchSelectedByteAtX__m23a_room49
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_m22_hook8_lifetime,x
    rts
    .if SAME_BUILD_SCUMM_M23A
ScummV5_FetchSelectedByteAtX__m23a_room49:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_AUTH_ROOM49
    bne ScummV5_FetchSelectedByteAtX__m23a_room63
    lda.l ScummV5_C2_Program_m23a_auth_room49,x
    rts
ScummV5_FetchSelectedByteAtX__m23a_room63:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_AUTH_ROOM63
    bne ScummV5_FetchSelectedByteAtX__m23a_lifecycle
    lda.l ScummV5_C2_Program_m23a_auth_room63,x
    rts
ScummV5_FetchSelectedByteAtX__m23a_lifecycle:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23A_LIFECYCLE
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE
    bne ScummV5_FetchSelectedByteAtX__m23c_if_class
    .else
    bne ScummV5_FetchSelectedByteAtX__c1
    .endif
    lda.l ScummV5_C2_Program_m23a_lifecycle,x
    rts
    .if SAME_BUILD_SCUMM_M23C_CLASS_CONFORMANCE
ScummV5_FetchSelectedByteAtX__m23c_if_class:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS
    bne ScummV5_FetchSelectedByteAtX__m23c_if_class_malformed
    lda.l ScummV5_C2_Program_m23c_if_class,x
    rts
ScummV5_FetchSelectedByteAtX__m23c_if_class_malformed:
    .a8
    cmp #SCUMM_C2_FIXTURE_M23C_IF_CLASS_MALFORMED
    bne ScummV5_FetchSelectedByteAtX__c1
    lda.l ScummV5_C2_Program_m23c_if_class_malformed,x
    rts
    .endif
    .endif
    .endif
    .endif
    .endif
    .endif
ScummV5_FetchSelectedByteAtX__c1:
.if SAME_BUILD_SCUMM_PHASE6LA1D
    ; The authored M25 personality has no C2 fixture selector.  Keep the
    ; production image independent of the validation-only conformance blob.
    sep #$20
    .a8
    lda #$00
.else
    lda.l ScummV5_Conformance_Program,x
.endif
    rts

ScummV5_SetError:
    sep #$20
    .a8
    pha
    lda.l $7E5500
    inc
    sta.l $7E5500
    pla
    .if SAME_BUILD_SCUMM_SCENARIO_FIXTURE
    ; Capture the first-class error at the common setter, before the caller's
    ; error path can restore a slot or change the active program context.
    sta.l SAME_SCUMM_SCENARIO_ERROR_CODE
    lda.l $7E5500
    sta.l SAME_SCUMM_SCENARIO_ERROR_COUNT
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_SCENARIO_ERROR_PROGRAM
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l SAME_SCUMM_SCENARIO_ERROR_PC
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l SAME_SCUMM_SCENARIO_ERROR_OPCODE
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l SAME_SCUMM_SCENARIO_ERROR_ROOM
    ; The error code is still on the stack from the entry PHA; the JSR
    ; return address therefore begins at S+2.
    lda 2,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_RET
    lda 3,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_RET+1
    lda 1,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK
    lda 2,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+1
    lda 3,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+2
    lda 4,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+3
    lda 5,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+4
    lda 6,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+5
    lda 7,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+6
    lda 8,s
    sta.l SAME_SCUMM_SCENARIO_ERROR_STACK+7
    rep #$20
    .a16
    lda.l SAME_SCUMM_LHS
    sta.l SAME_SCUMM_SCENARIO_ERROR_LHS
    lda.l SAME_SCUMM_OPERAND
    sta.l SAME_SCUMM_SCENARIO_ERROR_OPERAND
    lda.l SAME_SCUMM_RESULT_OFFSET
    sta.l SAME_SCUMM_SCENARIO_ERROR_RESULT
    .endif
    ; Restore the error code in A for the existing state publication below.
    lda.l SAME_SCUMM_SCENARIO_ERROR_CODE
    sta.l $7E5501
    sta.l $7E5457
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l $7E5502
    sta.l $7E5458
    rep #$20
    .a16
    lda.l SAME_SCUMM_PC
    sta.l $7E5503
    sta.l $7E5459
    sep #$20
    .a8
    lda.l SAME_SCUMM_LAST_OPCODE
    sta.l $7E5505
    sta.l $7E545B
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    sta.l $7E5506
    lda.l $7E5457
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    rts

.if SAME_BUILD_SCUMM_PHASE6LA1D == $00
.include "../generated/scumm_v5_conformance.inc.pasm"
.endif
