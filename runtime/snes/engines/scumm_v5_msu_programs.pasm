; Checked SAMEPKG-backed SCUMM v5 ProgramUnit body cache.
;
; The 8-bit VM selector remains an ephemeral resident handle. This layer maps
; it to the canonical 16-bit ProgramUnit ID, requests a complete CRC-checked
; body from SAME storage, and only then enters the unchanged interpreter.
; Two 2-KiB cache windows are intentionally bounded; active nested executions
; pin their windows until the interpreter returns. Yielded C4 activations keep
; their canonical selector ownership and refetch on resume.

SCUMM_MSU_CACHE_EMPTY    = $00
SCUMM_MSU_CACHE_LOADING  = $01
SCUMM_MSU_CACHE_READY    = $02
SCUMM_MSU_CACHE_FAILED   = $FF
SCUMM_MSU_ROOM_IDLE      = $00
SCUMM_MSU_ROOM_REQUESTED = $01
SCUMM_MSU_ROOM_READING   = $02
SCUMM_MSU_ROOM_VALIDATED = $03
SCUMM_MSU_ROOM_FAILED    = $FF
SCUMM_MSU_ROOM_HEADER_BYTES = $00E8
SCUMM_MSU_ROOM_SCRIPT_BYTES = $0060
SCUMM_MSU_ROOM_TRAILER_BYTES = $0020

.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
SCUMM_LIVE_ROOM_BASE = SAME_SCUMM_LIVE_ROOM_STAGING_BASE
SCUMM_LIVE_ROOM_PENDING = SAME_SCUMM_LIVE_ROOM_PENDING_BASE
SCUMM_LIVE_ROOM_STAGE = SAME_SCUMM_LIVE_ROOM_CONTROL+$00
SCUMM_LIVE_ROOM_VALID = SAME_SCUMM_LIVE_ROOM_CONTROL+$01
SCUMM_LIVE_ROOM_READ_LENGTH = SAME_SCUMM_LIVE_ROOM_CONTROL+$02
SCUMM_LIVE_ROOM_WIDTH = SAME_SCUMM_LIVE_ROOM_CONTROL+$04
SCUMM_LIVE_ROOM_HEIGHT = SAME_SCUMM_LIVE_ROOM_CONTROL+$06
SCUMM_LIVE_ROOM_PITCH = SAME_SCUMM_LIVE_ROOM_CONTROL+$08
SCUMM_LIVE_ROOM_COPY_INDEX = SAME_SCUMM_LIVE_ROOM_CONTROL+$0A
; Transaction validity is cleared when a new incoming resource request starts.
; The active visual has a separate lifetime and remains valid until the next
; checked pixel/palette pair is atomically published to the video surface.
SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID = SAME_SCUMM_LIVE_ROOM_CONTROL+$21
; M24R-B may be re-entered while the incoming visual is fetched. This
; transaction bit makes retiring the outgoing resolver bundle idempotent.
SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED = SAME_SCUMM_LIVE_ROOM_CONTROL+$22
SCUMM_LIVE_ROOM_MAGIC = $004C ; 'SC5LIVE' prefix checked bytewise
SCUMM_LIVE_ROOM_HEADER_SIZE = $0052
SCUMM_LIVE_ROOM_MAX_SIZE = $0800
SCUMM_LIVE_ROOM_STAGE_COOKED = $00
SCUMM_LIVE_ROOM_STAGE_METADATA = $01
SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY = $02
SCUMM_LIVE_ROOM_STAGE_PALETTE = $03
SCUMM_LIVE_ROOM_STAGE_PIXELS = $04
SCUMM_LIVE_ROOM_STAGE_COMMIT_READY = $05
.endif

ScummV5_MsuProgram_Reset_Far:
    php
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ID0
    sta.l SAME_SCUMM_MSU_CACHE_ID1
    lda #$0000
    sta.l SAME_SCUMM_MSU_CACHE_SIZE0
    sta.l SAME_SCUMM_MSU_CACHE_SIZE1
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION0
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION1
    sta.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    sta.l SAME_SCUMM_MSU_CACHE_PEAK_COUNT
    sta.l SAME_SCUMM_MSU_CACHE_LOADS
    sta.l SAME_SCUMM_MSU_CACHE_EVICTIONS
    sta.l SAME_SCUMM_MSU_CACHE_FAILURES
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    phx ; Preserve the caller's 16-bit X before narrowing the index width.
    sep #$10
    .i8
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
    sta.l SAME_SCUMM_MSU_CACHE_STATE1
    sta.l SAME_SCUMM_MSU_CACHE_PINS0
    sta.l SAME_SCUMM_MSU_CACHE_PINS1
    sta.l SAME_SCUMM_MSU_EXEC_DEPTH
    sta.l SAME_SCUMM_MSU_DIRECT_ROOM_CALL
    sta.l SAME_SCUMM_MSU_LAST_SELECTOR
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
    sta.l SAME_SCUMM_MSU_C19_ERROR_STAGE
    sta.l SAME_SCUMM_MSU_C19_ERROR_OPCODE
    sta.l SAME_SCUMM_MSU_C19_ERROR_PROGRAM
    sta.l SAME_SCUMM_MSU_C19_ERROR_SLOT
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_MSU_PROCESS_TURNS
    sta.l SAME_SCUMM_MSU_FRAME_ENTRIES
    sta.l SAME_SCUMM_MSU_ENGINE_RETURNS
    sta.l SAME_SCUMM_MSU_RESOLVE_CALLS
    sta.l SAME_SCUMM_MSU_C19_ERROR_PC
    sta.l SAME_SCUMM_MSU_ROOM_REQUESTS
    sta.l SAME_SCUMM_MSU_ROOM_VALIDATIONS
    sta.l SAME_SCUMM_MSU_ROOM_FAILURES
    sta.l SAME_SCUMM_MSU_MAX_FETCH_LATENCY
    sta.l SAME_SCUMM_MSU_ROOM_START_FRAME
    sta.l SAME_SCUMM_MSU_ROOM_LAST_LENGTH
    sta.l SAME_SCUMM_MSU_ROOM_SCRIPT_COUNT
    sta.l SAME_SCUMM_MSU_ROOM_DATA_OFFSET
    sta.l SAME_SCUMM_MSU_ROOM_TEMP
    sep #$20
    .a8
    sta.l SAME_SCUMM_MSU_PROCESS_LAST_STATUS
    sta.l SAME_SCUMM_MSU_FRAME_STAGE
    ldx #$0000
ScummV5_MsuProgram_Reset_Far__pending:
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_SLOT,x
    sta.l SAME_SCUMM_MSU_PENDING_CHILD_PROGRAM,x
    inx
    cpx #SCUMM_V5_MAX_SCRIPT_SLOTS
    bcc ScummV5_MsuProgram_Reset_Far__pending
    lda #$FF
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    sta.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    sta.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
    sta.l SAME_SCUMM_MSU_ROOM_CACHE_SLOT
    lda #SCUMM_MSU_ROOM_IDLE
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda #SCUMM_LIVE_ROOM_STAGE_COOKED
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #$00
    sta.l SCUMM_LIVE_ROOM_VALID
    sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID
    sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$20
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F
    .endif
    jsl Same_Msu1_InitBegin_FarEntry
    bcs ScummV5_MsuProgram_Reset_Far__failed
    rep #$10
    .i16
    plx
    plp
    clc
    rtl
ScummV5_MsuProgram_Reset_Far__failed:
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    rep #$10
    .i16
    plx
    plp
    sec
    rtl

; Carry set only after the provider has authenticated the package prefix and
; reached READY/READ_OK. Initialization and body transfer are frame-driven.
ScummV5_MsuProgram_FrameReady_Far:
    jsl ScummV5_MsuRoom_Service_Far
    bcs ScummV5_MsuProgram_FrameReady_Far__provider
    cmp #$FF
    beq ScummV5_MsuProgram_FrameReady_Far__room_failed
ScummV5_MsuProgram_FrameReady_Far__room_failed:
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_ERROR
    beq ScummV5_MsuProgram_FrameReady_Far__not_ready
    lda #SCUMM_VM_WAIT_RESOURCE
    sta.l SAME_SCUMM_STATUS
ScummV5_MsuProgram_FrameReady_Far__not_ready:
    clc
    rtl
ScummV5_MsuProgram_FrameReady_Far__provider:
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READY
    beq ScummV5_MsuProgram_FrameReady_Far__ready
    cmp #SAME_MSU1_STATE_READ_OK
    beq ScummV5_MsuProgram_FrameReady_Far__ready
    cmp #SAME_MSU1_STATE_ERROR
    beq ScummV5_MsuProgram_FrameReady_Far__failed
    bra ScummV5_MsuProgram_FrameReady_Far__wait
ScummV5_MsuProgram_FrameReady_Far__ready:
    sec
    rtl
ScummV5_MsuProgram_FrameReady_Far__failed:
    .a8
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda #$96
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F
    .endif
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    lda #SCUMM_VM_ERROR
    sta.l SAME_SCUMM_STATUS
    clc
    rtl

ScummV5_MsuProgram_FrameReady_Far__wait:
    .a8
    lda #SCUMM_VM_WAIT_RESOURCE
    sta.l SAME_SCUMM_STATUS
    clc
    rtl

; M23A calls this only after its existing compiled-room record passes the ROM
; validator. The external cooked SC5ROOM record is then fetched and checked
; before ResourceReady can execute EXCD or retire the outgoing bundle.
ScummV5_MsuRoom_Request_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_ROOM_STATE
    cmp #SCUMM_MSU_ROOM_REQUESTED
    beq ScummV5_MsuRoom_Request_Far__coalesced
    cmp #SCUMM_MSU_ROOM_READING
    beq ScummV5_MsuRoom_Request_Far__coalesced
    lda.l SAME_SCUMM_M23A_PENDING_ROOM
    sta.l SAME_SCUMM_MSU_ROOM_ID
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$0C
    lda #SCUMM_LIVE_ROOM_STAGE_COOKED
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #$00
    sta.l SCUMM_LIVE_ROOM_VALID
    sta.l SCUMM_LIVE_ROOM_OLD_BUNDLE_RELEASED
    .endif
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_REQUESTS
    inc
    sta.l SAME_SCUMM_MSU_ROOM_REQUESTS
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_SCUMM_MSU_ROOM_START_FRAME
    plp
    clc
    rtl
ScummV5_MsuRoom_Request_Far__coalesced:
    plp
    clc
    rtl

; Nonblocking room-resource state machine. A read owns one unpinned body-cache
; window only while transfer/validation runs; after parsing, the window is
; invalidated before M23A starts EXCD. In live-room mode the validated
; SC5LIVE/SC5VIS resources become the source for implemented room consumers;
; legacy mode continues to use its generated ROM-backed room directories.
ScummV5_MsuRoom_Service_Far:
    sep #$20
    .a8
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda #$A0
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1D
.endif
    lda.l SAME_SCUMM_MSU_ROOM_STATE
    cmp #SCUMM_MSU_ROOM_IDLE
    bne ScummV5_MsuRoom_Service_Far__check_validated
    jmp ScummV5_MsuRoom_Service_Far__no_request
ScummV5_MsuRoom_Service_Far__check_validated:
    .a8
    cmp #SCUMM_MSU_ROOM_VALIDATED
    bne ScummV5_MsuRoom_Service_Far__check_failed
    jmp ScummV5_MsuRoom_Service_Far__ready
ScummV5_MsuRoom_Service_Far__check_failed:
    .a8
    cmp #SCUMM_MSU_ROOM_FAILED
    bne ScummV5_MsuRoom_Service_Far__check_requested
    jmp ScummV5_MsuRoom_Service_Far__failed
ScummV5_MsuRoom_Service_Far__check_requested:
    .a8
    cmp #SCUMM_MSU_ROOM_REQUESTED
    beq ScummV5_MsuRoom_Service_Far__start
    cmp #SCUMM_MSU_ROOM_READING
    beq ScummV5_MsuRoom_Service_Far__poll
    jmp ScummV5_MsuRoom_Service_Far__fail
ScummV5_MsuRoom_Service_Far__start:
    jsl ScummV5_MsuRoom_Start_Far
    bcs ScummV5_MsuRoom_Service_Far__fail
    clc
    rtl
ScummV5_MsuRoom_Service_Far__poll:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READ_OK
    beq ScummV5_MsuRoom_Service_Far__validate
    cmp #SAME_MSU1_STATE_ERROR
    beq ScummV5_MsuRoom_Service_Far__fail
    clc
    rtl
ScummV5_MsuRoom_Service_Far__validate:
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    .a8
    lda #$A1
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1D
    lda.l SCUMM_LIVE_ROOM_STAGE
    beq ScummV5_MsuRoom_Service_Far__validate_cooked
    lda #$A2
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1D
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far
ScummV5_MsuRoom_Service_Far__validate_cooked:
    .a8
.endif
    jsl ScummV5_MsuRoom_Validate_Far
    bcs ScummV5_MsuRoom_Service_Far__fail
    jsl ScummV5_MsuRoom_ReleaseWindow_Far
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda #SCUMM_LIVE_ROOM_STAGE_METADATA
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
.endif
    sep #$20
    .a8
    lda #SCUMM_MSU_ROOM_VALIDATED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    lda #$05 ; M23A resource ready; existing EXCD/commit/ENCD order follows.
    sta.l SAME_SCUMM_M23A_PHASE
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_VALIDATIONS
    inc
    sta.l SAME_SCUMM_MSU_ROOM_VALIDATIONS
    lda.l SAME_FRAME_COUNTER
    sec
    sbc.l SAME_SCUMM_MSU_ROOM_START_FRAME
    cmp.l SAME_SCUMM_MSU_MAX_FETCH_LATENCY
    bcc ScummV5_MsuRoom_Service_Far__latency_done
    sta.l SAME_SCUMM_MSU_MAX_FETCH_LATENCY
ScummV5_MsuRoom_Service_Far__latency_done:
    sec
    rtl
ScummV5_MsuRoom_Service_Far__ready:
    sec
    rtl
ScummV5_MsuRoom_Service_Far__no_request:
    sec
    rtl
ScummV5_MsuRoom_Service_Far__failed:
    .a8
    clc
    lda #$FF
    rtl
ScummV5_MsuRoom_Service_Far__fail:
    ; If a transfer had claimed the window, invalidate it without touching an
    ; unrelated READY body when descriptor validation failed before install.
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_LOADING
    bne ScummV5_MsuRoom_Service_Far__mark_failed
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID0
    cmp #$FFFF
    bne ScummV5_MsuRoom_Service_Far__mark_failed
    jsl ScummV5_MsuRoom_ReleaseWindow_Far
ScummV5_MsuRoom_Service_Far__mark_failed:
    sep #$20
    .a8
    .if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda #$91
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F
    .endif
    lda #SCUMM_MSU_ROOM_FAILED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    lda #$06
    sta.l SAME_SCUMM_M23A_PHASE
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_FAILURES
    inc
    sta.l SAME_SCUMM_MSU_ROOM_FAILURES
    sep #$20
    .a8
    lda #$FF
    rtl

; Choose a free cache window, copy the compiler-owned room descriptor, then
; begin the existing SAMEPKG checked read. If both windows are transiently
; pinned, this frame simply waits; it never overwrites a live interpreter.
ScummV5_MsuRoom_Start_Far:
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
    lda.l SCUMM_LIVE_ROOM_STAGE
    beq ScummV5_MsuRoom_Start_Far__legacy
    jml ScummV5_MsuRoom_Start_Far__live
.endif
ScummV5_MsuRoom_Start_Far__legacy:
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_MsuRoom_Start_Far__provider_idle
    clc
    rtl
ScummV5_MsuRoom_Start_Far__provider_idle:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_PINS0
    beq ScummV5_MsuRoom_Start_Far__window_free
    jmp ScummV5_MsuRoom_Start_Far__window_busy
ScummV5_MsuRoom_Start_Far__window_free:
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_ROOM_CACHE_SLOT
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_ROOM_COUNT
    bcc ScummV5_MsuRoom_Start_Far__room_in_range
    sec
    rtl
ScummV5_MsuRoom_Start_Far__room_in_range:
    asl
    sta.l SAME_SCUMM_MSU_ROOM_TEMP
    asl
    asl
    clc
    adc.l SAME_SCUMM_MSU_ROOM_TEMP ; room id * 10
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    inx
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    bne ScummV5_MsuRoom_Start_Far__length_nonzero
    jmp ScummV5_MsuRoom_Start_Far__invalid_descriptor
ScummV5_MsuRoom_Start_Far__length_nonzero:
    .a16
    cmp #SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE+1
    bcc ScummV5_MsuRoom_Start_Far__length_valid
    jmp ScummV5_MsuRoom_Start_Far__invalid_descriptor
ScummV5_MsuRoom_Start_Far__length_valid:
    sta.l SAME_SCUMM_MSU_ROOM_LAST_LENGTH
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MSU1_DESTINATION
    lda #$10
    sta.l SAME_MSU1_DESTINATION+1
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
    rep #$20
    .a16
    lda #SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MSU1_FLAGS
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_READY
    bne ScummV5_MsuRoom_Start_Far__prepare0
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    dec
    sta.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    lda.l SAME_SCUMM_MSU_CACHE_EVICTIONS
    inc
    sta.l SAME_SCUMM_MSU_CACHE_EVICTIONS
    sep #$20
    .a8
ScummV5_MsuRoom_Start_Far__prepare0:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    inc
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION0
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ID0
    lda #$0000
    sta.l SAME_SCUMM_MSU_CACHE_SIZE0
    sep #$20
    .a8
    lda #SCUMM_MSU_CACHE_LOADING
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
ScummV5_MsuRoom_Start_Far__read_begin:
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_SCUMM_MSU_ROOM_START_FRAME
    sep #$20
    .a8
    jsl Same_Msu1_ReadBegin_FarEntry
    bcs ScummV5_MsuRoom_Start_Far__invalid_descriptor
    sep #$20
    .a8
    lda #SCUMM_MSU_ROOM_READING
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_MsuRoom_Start_Far__invalid_descriptor:
    sec
    rtl
ScummV5_MsuRoom_Start_Far__window_busy:
    clc
    rtl
.if SAME_BUILD_SCUMM_MSU1_LIVE_ROOM_RESOURCES
ScummV5_MsuRoom_Start_Far__live:
    jml ScummV5_MsuLiveRoom_Start_Far
.endif

; The generic SAME read CRC authenticates every byte before this parser sees
; the buffer. Validate the existing SC5ROOM v1 header/table geometry without
; interpreting or replacing the SCUMM room payload format.
ScummV5_MsuRoom_Validate_Far:
    php
    rep #$30
    .a16
    .i16
    phx
    sep #$20
    .a8
    ldx #$0000
ScummV5_MsuRoom_Validate_Far__magic:
    .a8
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0,x
    cmp.l ScummV5_MsuRoom_Magic,x
    beq ScummV5_MsuRoom_Validate_Far__magic_match
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__magic_match:
    .a8
    inx
    cpx #$0008
    bcc ScummV5_MsuRoom_Validate_Far__magic
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+8
    cmp #$0001
    beq ScummV5_MsuRoom_Validate_Far__version_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__version_ok:
    .a16
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+10
    cmp #SCUMM_MSU_ROOM_HEADER_BYTES
    beq ScummV5_MsuRoom_Validate_Far__header_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__header_ok:
    .a16
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+12
    cmp #$0001
    bcc ScummV5_MsuRoom_Validate_Far__flags_ok
    beq ScummV5_MsuRoom_Validate_Far__flags_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__flags_ok:
    .a16
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+14
    cmp.l SAME_SCUMM_MSU_ROOM_ID
    beq ScummV5_MsuRoom_Validate_Far__room_low_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__room_low_ok:
    .a8
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+15
    beq ScummV5_MsuRoom_Validate_Far__room_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__room_ok:
    .a8
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+16
    cmp.l SAME_SCUMM_MSU_ROOM_LAST_LENGTH
    beq ScummV5_MsuRoom_Validate_Far__length_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__length_ok:
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+18
    beq ScummV5_MsuRoom_Validate_Far__length_hi_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__length_hi_ok:
    .a16
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+20
    cmp #SCUMM_MSU_ROOM_HEADER_BYTES
    beq ScummV5_MsuRoom_Validate_Far__table_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__table_ok:
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+22
    beq ScummV5_MsuRoom_Validate_Far__table_hi_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__table_hi_ok:
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+24
    sta.l SAME_SCUMM_MSU_ROOM_SCRIPT_COUNT
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+26
    beq ScummV5_MsuRoom_Validate_Far__script_count_hi_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__script_count_hi_ok:
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+28
    sta.l SAME_SCUMM_MSU_ROOM_DATA_OFFSET
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+30
    beq ScummV5_MsuRoom_Validate_Far__room_offset_hi_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__room_offset_hi_ok:
    ; SC5ROOM table offset must equal header + script_count * 96.
    lda.l SAME_SCUMM_MSU_ROOM_SCRIPT_COUNT
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_MSU_ROOM_TEMP
    lda.l SAME_SCUMM_MSU_ROOM_SCRIPT_COUNT
    asl
    asl
    asl
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_MSU_ROOM_TEMP
    clc
    adc #SCUMM_MSU_ROOM_HEADER_BYTES
    cmp.l SAME_SCUMM_MSU_ROOM_DATA_OFFSET
    beq ScummV5_MsuRoom_Validate_Far__script_table_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__script_table_ok:
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0+38
    beq ScummV5_MsuRoom_Validate_Far__reserved_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__reserved_ok:
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_LAST_LENGTH
    sec
    sbc #SCUMM_MSU_ROOM_TRAILER_BYTES
    cmp.l SAME_SCUMM_MSU_ROOM_DATA_OFFSET
    bcs ScummV5_MsuRoom_Validate_Far__bounds_ok
    jmp ScummV5_MsuRoom_Validate_Far__bad
ScummV5_MsuRoom_Validate_Far__bounds_ok:
    plx
    plp
    clc
    rtl
ScummV5_MsuRoom_Validate_Far__bad:
    plx
    plp
    sec
    rtl

; The room record has been fully checked and structurally bounded. Invalidate
; the staging generation before ordinary script fetches may reuse this window.
ScummV5_MsuRoom_ReleaseWindow_Far:
    php
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    inc
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION0
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ID0
    lda #$0000
    sta.l SAME_SCUMM_MSU_CACHE_SIZE0
    sep #$20
    .a8
    lda #SCUMM_MSU_CACHE_EMPTY
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
    plp
    rtl
ScummV5_MsuRoom_Magic:
    .byte $53,$43,$35,$52,$4F,$4F,$4D,$00

; Resolve current selector -> canonical ProgramUnit -> READY cache slot.
; Return: carry set, A=slot 0/1 when ready; carry clear, A=0 while pending;
; carry clear, A=$FFFF on explicit failure.
ScummV5_MsuProgram_EnsureSelected_Far:
    php
    rep #$30
    .a16
    .i16
    sep #$20
    .a8
    lda.l SAME_SCUMM_PROGRAM_SELECT
    jsl ScummV5_Resident_ProgramUnitForSelector_Far
    bcs ScummV5_MsuProgram_EnsureSelected_Far__selector_valid
    jmp ScummV5_MsuProgram_EnsureSelected_Far__failed
ScummV5_MsuProgram_EnsureSelected_Far__selector_valid:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_EXPECTED_ID
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    jsl ScummV5_MsuProgram_ReconcileRead_Far
    bcc ScummV5_MsuProgram_EnsureSelected_Far__read_reconciled
    jmp ScummV5_MsuProgram_EnsureSelected_Far__provider_failed
ScummV5_MsuProgram_EnsureSelected_Far__read_reconciled:

    ; Existing matching READY/LOADING slot.
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    beq ScummV5_MsuProgram_EnsureSelected_Far__check_slot1
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID0
    cmp.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    beq ScummV5_MsuProgram_EnsureSelected_Far__slot0_match
    sep #$20
    .a8
ScummV5_MsuProgram_EnsureSelected_Far__check_slot1:
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    beq ScummV5_MsuProgram_EnsureSelected_Far__find_slot
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID1
    cmp.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    beq ScummV5_MsuProgram_EnsureSelected_Far__slot1_match
    bra ScummV5_MsuProgram_EnsureSelected_Far__find_slot

ScummV5_MsuProgram_EnsureSelected_Far__slot0_match:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_READY
    beq ScummV5_MsuProgram_EnsureSelected_Far__slot0_ready
    cmp #SCUMM_MSU_CACHE_FAILED
    bne ScummV5_MsuProgram_EnsureSelected_Far__slot0_pending
    jmp ScummV5_MsuProgram_EnsureSelected_Far__provider_failed
ScummV5_MsuProgram_EnsureSelected_Far__slot0_pending:
    jmp ScummV5_MsuProgram_EnsureSelected_Far__pending
ScummV5_MsuProgram_EnsureSelected_Far__slot1_match:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    cmp #SCUMM_MSU_CACHE_READY
    beq ScummV5_MsuProgram_EnsureSelected_Far__slot1_ready
    cmp #SCUMM_MSU_CACHE_FAILED
    bne ScummV5_MsuProgram_EnsureSelected_Far__slot1_pending
    jmp ScummV5_MsuProgram_EnsureSelected_Far__provider_failed
ScummV5_MsuProgram_EnsureSelected_Far__slot1_pending:
    jmp ScummV5_MsuProgram_EnsureSelected_Far__pending
ScummV5_MsuProgram_EnsureSelected_Far__slot0_ready:
    .a8
    lda #$00
    plp
    sec
    rtl
ScummV5_MsuProgram_EnsureSelected_Far__slot1_ready:
    .a8
    lda #$01
    plp
    sec
    rtl

ScummV5_MsuProgram_EnsureSelected_Far__find_slot:
    ; Only one checked-read cursor exists. Never replace its destination while
    ; a transfer is in flight, even when another activation is also waiting.
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_MsuProgram_EnsureSelected_Far__read_idle
    jmp ScummV5_MsuProgram_EnsureSelected_Far__pending
ScummV5_MsuProgram_EnsureSelected_Far__read_idle:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    beq ScummV5_MsuProgram_EnsureSelected_Far__choose0
    lda.l SAME_SCUMM_MSU_CACHE_PINS0
    bne ScummV5_MsuProgram_EnsureSelected_Far__try1
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_LOADING
    beq ScummV5_MsuProgram_EnsureSelected_Far__try1
    ; Consume an unused second window before evicting an unpinned READY body.
    ; In particular, a nested caller may have suspended its transient pin but
    ; still needs the same bytes immediately after the child returns.
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    beq ScummV5_MsuProgram_EnsureSelected_Far__choose1
    lda #$00
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
    bra ScummV5_MsuProgram_EnsureSelected_Far__chosen
ScummV5_MsuProgram_EnsureSelected_Far__choose0:
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
    bra ScummV5_MsuProgram_EnsureSelected_Far__chosen
ScummV5_MsuProgram_EnsureSelected_Far__try1:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    beq ScummV5_MsuProgram_EnsureSelected_Far__choose1
    lda.l SAME_SCUMM_MSU_CACHE_PINS1
    beq ScummV5_MsuProgram_EnsureSelected_Far__slot1_unpinned
    jmp ScummV5_MsuProgram_EnsureSelected_Far__exhausted
ScummV5_MsuProgram_EnsureSelected_Far__slot1_unpinned:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    cmp #SCUMM_MSU_CACHE_LOADING
    bne ScummV5_MsuProgram_EnsureSelected_Far__slot1_available
    jmp ScummV5_MsuProgram_EnsureSelected_Far__exhausted
ScummV5_MsuProgram_EnsureSelected_Far__slot1_available:
ScummV5_MsuProgram_EnsureSelected_Far__choose1:
    .a8
    lda #$01
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
ScummV5_MsuProgram_EnsureSelected_Far__chosen:
    .a8
    ; Validate the indexed generated record and enforce the exact WRAM bound.
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    cmp #SCUMM_MSU1_PROGRAM_COUNT
    bcc ScummV5_MsuProgram_EnsureSelected_Far__directory_id_valid
    jmp ScummV5_MsuProgram_EnsureSelected_Far__bad_directory
ScummV5_MsuProgram_EnsureSelected_Far__directory_id_valid:
    asl
    sta.l SAME_SCUMM_MSU_CACHE_TABLE_INDEX ; id*2
    asl
    asl
    clc
    adc.l SAME_SCUMM_MSU_CACHE_TABLE_INDEX ; id*10
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    inx
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuProgramRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3

    ; A zero or >2-KiB body cannot be made executable by this bounded cache.
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    ora.l SAME_MSU1_REQUEST_LENGTH+3
    beq ScummV5_MsuProgram_EnsureSelected_Far__length_high_zero
    jmp ScummV5_MsuProgram_EnsureSelected_Far__bad_length
ScummV5_MsuProgram_EnsureSelected_Far__length_high_zero:
    lda.l SAME_MSU1_REQUEST_LENGTH
    bne ScummV5_MsuProgram_EnsureSelected_Far__length_nonzero
    jmp ScummV5_MsuProgram_EnsureSelected_Far__bad_length
ScummV5_MsuProgram_EnsureSelected_Far__length_nonzero:
    .a16
    cmp #SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE+1
    bcc ScummV5_MsuProgram_EnsureSelected_Far__length_in_bounds
    jmp ScummV5_MsuProgram_EnsureSelected_Far__bad_length
ScummV5_MsuProgram_EnsureSelected_Far__length_in_bounds:
    sta.l SAME_SCUMM_MSU_CACHE_TEMP
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_RETURN_P
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT

    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    beq ScummV5_MsuProgram_EnsureSelected_Far__target0
    lda #$00
    sta.l SAME_MSU1_DESTINATION
    lda #$18
    sta.l SAME_MSU1_DESTINATION+1
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
    bra ScummV5_MsuProgram_EnsureSelected_Far__destination_ready
ScummV5_MsuProgram_EnsureSelected_Far__target0:
    .a8
    lda #$00
    sta.l SAME_MSU1_DESTINATION
    lda #$10
    sta.l SAME_MSU1_DESTINATION+1
    lda #$7E
    sta.l SAME_MSU1_DESTINATION+2
ScummV5_MsuProgram_EnsureSelected_Far__destination_ready:
    rep #$20
    .a16
    lda #SAME_SCUMM_MSU_PROGRAM_CACHE_SLOT_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    ; Preserve the new canonical ID, increment the buffer generation, and
    ; publish LOADING before starting provider work; READY is never partial.
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    and #$00FF
    beq ScummV5_MsuProgram_EnsureSelected_Far__install0
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    cmp #SCUMM_MSU_CACHE_READY
    bne ScummV5_MsuProgram_EnsureSelected_Far__install1_empty
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    dec
    sta.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    lda.l SAME_SCUMM_MSU_CACHE_EVICTIONS
    inc
    sta.l SAME_SCUMM_MSU_CACHE_EVICTIONS
ScummV5_MsuProgram_EnsureSelected_Far__install1_empty:
    .a16
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    sta.l SAME_SCUMM_MSU_CACHE_ID1
    lda.l SAME_SCUMM_MSU_CACHE_TEMP
    sta.l SAME_SCUMM_MSU_CACHE_SIZE1
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION1
    inc
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION1
    sep #$20
    .a8
    lda #SCUMM_MSU_CACHE_LOADING
    sta.l SAME_SCUMM_MSU_CACHE_STATE1
    lda #$01
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    bra ScummV5_MsuProgram_EnsureSelected_Far__request
ScummV5_MsuProgram_EnsureSelected_Far__install0:
    .a8
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_READY
    bne ScummV5_MsuProgram_EnsureSelected_Far__install0_empty
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    dec
    sta.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    lda.l SAME_SCUMM_MSU_CACHE_EVICTIONS
    inc
    sta.l SAME_SCUMM_MSU_CACHE_EVICTIONS
ScummV5_MsuProgram_EnsureSelected_Far__install0_empty:
    .a16
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_ID
    sta.l SAME_SCUMM_MSU_CACHE_ID0
    lda.l SAME_SCUMM_MSU_CACHE_TEMP
    sta.l SAME_SCUMM_MSU_CACHE_SIZE0
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    inc
    sta.l SAME_SCUMM_MSU_CACHE_GENERATION0
    sep #$20
    .a8
    lda #SCUMM_MSU_CACHE_LOADING
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
    lda #$00
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
ScummV5_MsuProgram_EnsureSelected_Far__request:
    .a8
    lda #$00
    sta.l SAME_MSU1_FLAGS
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sta.l SAME_SCUMM_MSU_ROOM_START_FRAME
    sep #$20
    .a8
    jsl Same_Msu1_ReadBegin_FarEntry
    bcs ScummV5_MsuProgram_EnsureSelected_Far__read_failed
    lda #$00
    plp
    clc
    rtl

ScummV5_MsuProgram_EnsureSelected_Far__read_failed:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    beq ScummV5_MsuProgram_EnsureSelected_Far__read_failed0
    lda #SCUMM_MSU_CACHE_FAILED
    sta.l SAME_SCUMM_MSU_CACHE_STATE1
    bra ScummV5_MsuProgram_EnsureSelected_Far__read_failed_count
ScummV5_MsuProgram_EnsureSelected_Far__read_failed0:
    .a8
    lda #SCUMM_MSU_CACHE_FAILED
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
ScummV5_MsuProgram_EnsureSelected_Far__read_failed_count:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_FAILURES
    inc
    sta.l SAME_SCUMM_MSU_CACHE_FAILURES
ScummV5_MsuProgram_EnsureSelected_Far__provider_failed:
    rep #$20
    .a16
    lda #$FFFF
    plp
    clc
    rtl
ScummV5_MsuProgram_EnsureSelected_Far__bad_directory:
ScummV5_MsuProgram_EnsureSelected_Far__bad_length:
    sep #$20
    .a8
    lda #SCUMM_MSU_CACHE_FAILED
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
ScummV5_MsuProgram_EnsureSelected_Far__failed:
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    rep #$20
    .a16
    lda #$FFFF
    plp
    clc
    rtl
ScummV5_MsuProgram_EnsureSelected_Far__exhausted:
    sep #$20
    .a8
    lda #SCUMM_ERR_RESIDENCY_EXHAUSTED
    sta.l SAME_SCUMM_ERROR
    rep #$20
    .a16
    lda #$FFFF
    plp
    clc
    rtl
ScummV5_MsuProgram_EnsureSelected_Far__pending:
    rep #$20
    .a16
    lda #$0000
    plp
    clc
    rtl

; A nested SCUMM call suspends the caller at its already-saved logical PC.
; Release only its transient bytecode-window pin; the resident selector and
; C4 activation remain owned. The caller revalidates/refetches before it can
; fetch another source byte after the child returns.
ScummV5_MsuProgram_SuspendActive_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    cmp #$00
    beq ScummV5_MsuProgram_SuspendActive_Far__slot0
    cmp #$01
    bne ScummV5_MsuProgram_SuspendActive_Far__invalidate
    lda.l SAME_SCUMM_MSU_CACHE_PINS1
    beq ScummV5_MsuProgram_SuspendActive_Far__invalidate
    dec
    sta.l SAME_SCUMM_MSU_CACHE_PINS1
    bra ScummV5_MsuProgram_SuspendActive_Far__invalidate
ScummV5_MsuProgram_SuspendActive_Far__slot0:
    lda.l SAME_SCUMM_MSU_CACHE_PINS0
    beq ScummV5_MsuProgram_SuspendActive_Far__invalidate
    dec
    sta.l SAME_SCUMM_MSU_CACHE_PINS0
ScummV5_MsuProgram_SuspendActive_Far__invalidate:
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    sta.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda #$0000
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    plp
    rtl

; Reacquire the currently selected parent after a nested child. Return A=1/C=1
; when its checked body is READY, A=0/C=0 while a resumable fetch is pending,
; or A=2/C=0 after an explicit storage/directory failure.
ScummV5_MsuProgram_ResumeActive_Far:
    php
    phx
    phy
    rep #$20
    .a16
    jsl ScummV5_MsuProgram_EnsureSelected_Far
    bcc ScummV5_MsuProgram_ResumeActive_Far__not_ready
    sep #$20
    .a8
    sta.l SAME_SCUMM_MSU_CACHE_TEMP
    lda.l SAME_SCUMM_MSU_CACHE_TEMP
    sta.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    lda.l SAME_SCUMM_PROGRAM_SELECT
    sta.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
    lda.l SAME_SCUMM_MSU_CACHE_TEMP
    beq ScummV5_MsuProgram_ResumeActive_Far__pin0
    lda.l SAME_SCUMM_MSU_CACHE_PINS1
    inc
    sta.l SAME_SCUMM_MSU_CACHE_PINS1
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID1
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION1
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    bra ScummV5_MsuProgram_ResumeActive_Far__ready
ScummV5_MsuProgram_ResumeActive_Far__pin0:
    lda.l SAME_SCUMM_MSU_CACHE_PINS0
    inc
    sta.l SAME_SCUMM_MSU_CACHE_PINS0
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID0
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
ScummV5_MsuProgram_ResumeActive_Far__ready:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
    bra ScummV5_MsuProgram_ResumeActive_Far__return
ScummV5_MsuProgram_ResumeActive_Far__not_ready:
    rep #$20
    .a16
    cmp #$FFFF
    beq ScummV5_MsuProgram_ResumeActive_Far__failed
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
    bra ScummV5_MsuProgram_ResumeActive_Far__return
ScummV5_MsuProgram_ResumeActive_Far__failed:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_MSU_CACHE_RETURN_P
ScummV5_MsuProgram_ResumeActive_Far__return:
    ply
    plx
    plp
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_RETURN_P
    cmp #$01
    beq ScummV5_MsuProgram_ResumeActive_Far__return_ready
    clc
    rtl
ScummV5_MsuProgram_ResumeActive_Far__return_ready:
    sec
    rtl

; Convert provider READ_OK into READY only for the request-owned destination.
ScummV5_MsuProgram_ReconcileRead_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    cmp #$FF
    beq ScummV5_MsuProgram_ReconcileRead_Far__none
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READ_OK
    beq ScummV5_MsuProgram_ReconcileRead_Far__ready
    cmp #SAME_MSU1_STATE_ERROR
    beq ScummV5_MsuProgram_ReconcileRead_Far__error
    clc
    rtl
ScummV5_MsuProgram_ReconcileRead_Far__ready:
    .a8
    rep #$20
    .a16
    lda.l SAME_FRAME_COUNTER
    sec
    sbc.l SAME_SCUMM_MSU_ROOM_START_FRAME
    cmp.l SAME_SCUMM_MSU_MAX_FETCH_LATENCY
    bcc ScummV5_MsuProgram_ReconcileRead_Far__latency_done
    sta.l SAME_SCUMM_MSU_MAX_FETCH_LATENCY
ScummV5_MsuProgram_ReconcileRead_Far__latency_done:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    beq ScummV5_MsuProgram_ReconcileRead_Far__ready0
    lda #SCUMM_MSU_CACHE_READY
    sta.l SAME_SCUMM_MSU_CACHE_STATE1
    bra ScummV5_MsuProgram_ReconcileRead_Far__count
ScummV5_MsuProgram_ReconcileRead_Far__ready0:
    .a8
    lda #SCUMM_MSU_CACHE_READY
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
ScummV5_MsuProgram_ReconcileRead_Far__count:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    inc
    sta.l SAME_SCUMM_MSU_CACHE_CURRENT_COUNT
    cmp.l SAME_SCUMM_MSU_CACHE_PEAK_COUNT
    bcc ScummV5_MsuProgram_ReconcileRead_Far__peak_done
    sta.l SAME_SCUMM_MSU_CACHE_PEAK_COUNT
ScummV5_MsuProgram_ReconcileRead_Far__peak_done:
    lda.l SAME_SCUMM_MSU_CACHE_LOADS
    inc
    sta.l SAME_SCUMM_MSU_CACHE_LOADS
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
ScummV5_MsuProgram_ReconcileRead_Far__none:
    clc
    rtl
ScummV5_MsuProgram_ReconcileRead_Far__error:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    beq ScummV5_MsuProgram_ReconcileRead_Far__error0
    lda #SCUMM_MSU_CACHE_FAILED
    sta.l SAME_SCUMM_MSU_CACHE_STATE1
    bra ScummV5_MsuProgram_ReconcileRead_Far__failed_count
ScummV5_MsuProgram_ReconcileRead_Far__error0:
    .a8
    lda #SCUMM_MSU_CACHE_FAILED
    sta.l SAME_SCUMM_MSU_CACHE_STATE0
ScummV5_MsuProgram_ReconcileRead_Far__failed_count:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_FAILURES
    inc
    sta.l SAME_SCUMM_MSU_CACHE_FAILURES
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    sec
    rtl

; The only bytecode read path in this personality. X is the logical script PC.
; A is the current ephemeral selector; it is checked against the active cache
; binding before the byte is returned to the existing decoder.
ScummV5_MsuProgram_FetchByte_Far:
    php
    rep #$30
    .a16
    .i16
    phx
    sep #$20
    .a8
    cmp.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
    bne ScummV5_MsuProgram_FetchByte_Far__stale
    lda.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    cmp #$00
    beq ScummV5_MsuProgram_FetchByte_Far__slot0
    cmp #$01
    bne ScummV5_MsuProgram_FetchByte_Far__stale
    lda.l SAME_SCUMM_MSU_CACHE_STATE1
    cmp #SCUMM_MSU_CACHE_READY
    bne ScummV5_MsuProgram_FetchByte_Far__stale
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID1
    cmp.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    bne ScummV5_MsuProgram_FetchByte_Far__stale16
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION1
    cmp.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    bne ScummV5_MsuProgram_FetchByte_Far__stale16
    txa
    cmp.l SAME_SCUMM_MSU_CACHE_SIZE1
    bcs ScummV5_MsuProgram_FetchByte_Far__range16
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE1,x
    plx
    plp
    clc
    rtl
ScummV5_MsuProgram_FetchByte_Far__slot0:
    .a8
    lda.l SAME_SCUMM_MSU_CACHE_STATE0
    cmp #SCUMM_MSU_CACHE_READY
    bne ScummV5_MsuProgram_FetchByte_Far__stale
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID0
    cmp.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    bne ScummV5_MsuProgram_FetchByte_Far__stale16
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    cmp.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    bne ScummV5_MsuProgram_FetchByte_Far__stale16
    txa
    cmp.l SAME_SCUMM_MSU_CACHE_SIZE0
    bcs ScummV5_MsuProgram_FetchByte_Far__range16
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_PROGRAM_CACHE0,x
    plx
    plp
    clc
    rtl
ScummV5_MsuProgram_FetchByte_Far__range16:
    sep #$20
    .a8
ScummV5_MsuProgram_FetchByte_Far__stale:
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    lda #$00
    plx
    plp
    sec
    rtl
ScummV5_MsuProgram_FetchByte_Far__stale16:
    sep #$20
    .a8
    bra ScummV5_MsuProgram_FetchByte_Far__stale

; Release the currently executing body's transient execution pin and restore
; the enclosing interpreter context (if this was a nested StartScript). A
; yielded activation stores only canonical selector ownership + logical PC;
; its body may be evicted and checked-fetched again on resume.
ScummV5_MsuProgram_Leave_Far:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    sep #$20
    .a8
    lda.l SAME_SCUMM_MSU_EXEC_DEPTH
    bne ScummV5_MsuProgram_Leave_Far__active
    jmp ScummV5_MsuProgram_Leave_Far__done
ScummV5_MsuProgram_Leave_Far__active:
    .a8
    dec
    sta.l SAME_SCUMM_MSU_EXEC_DEPTH
    tax
    lda.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    beq ScummV5_MsuProgram_Leave_Far__unpin0
    cmp #$01
    bne ScummV5_MsuProgram_Leave_Far__restore
    lda.l SAME_SCUMM_MSU_CACHE_PINS1
    beq ScummV5_MsuProgram_Leave_Far__restore
    dec
    sta.l SAME_SCUMM_MSU_CACHE_PINS1
    bra ScummV5_MsuProgram_Leave_Far__restore
ScummV5_MsuProgram_Leave_Far__unpin0:
    lda.l SAME_SCUMM_MSU_CACHE_PINS0
    beq ScummV5_MsuProgram_Leave_Far__restore
    dec
    sta.l SAME_SCUMM_MSU_CACHE_PINS0
ScummV5_MsuProgram_Leave_Far__restore:
    .a8
    lda.l SAME_SCUMM_MSU_EXEC_PREV_SLOT,x
    sta.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    lda.l SAME_SCUMM_MSU_EXEC_PREV_SELECTOR,x
    sta.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
    cmp #$FF
    beq ScummV5_MsuProgram_Leave_Far__no_parent
    lda.l SAME_SCUMM_MSU_ACTIVE_CACHE_SLOT
    beq ScummV5_MsuProgram_Leave_Far__parent0
    cmp #$01
    bne ScummV5_MsuProgram_Leave_Far__no_parent
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID1
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION1
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    bra ScummV5_MsuProgram_Leave_Far__done
ScummV5_MsuProgram_Leave_Far__parent0:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_CACHE_ID0
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda.l SAME_SCUMM_MSU_CACHE_GENERATION0
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    bra ScummV5_MsuProgram_Leave_Far__done
ScummV5_MsuProgram_Leave_Far__no_parent:
    rep #$20
    .a16
    lda #$FFFF
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_ID
    lda #$0000
    sta.l SAME_SCUMM_MSU_CACHE_ACTIVE_GENERATION
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MSU_ACTIVE_SELECTOR
ScummV5_MsuProgram_Leave_Far__done:
    rep #$30
    .a16
    .i16
    ply
    plx
    plp
    rtl
