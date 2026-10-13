; Feature-gated live SCUMM room resources backed by checked SAMEPKG reads.
; The existing code-window cache remains reserved for executable bodies and
; the short SC5ROOM validation record.  Live metadata is staged in the SA-1
; dedicated 2-KiB incoming buffer, committed only after outgoing EXCD, and
; retained in the mode-3 diagnostic-fixture alias (mutually exclusive with
; its conformance engine). Visual pixels and
; palette are fetched into their own audited BWRAM allocations.

.bank 83
.org $8000

SCUMM_LIVE_ROOM_DIRECTORY_OFFSET = SAME_SCUMM_LIVE_ROOM_CONTROL+$0E
SCUMM_LIVE_ROOM_TEMP0 = SAME_SCUMM_LIVE_ROOM_CONTROL+$10
SCUMM_LIVE_ROOM_TEMP1 = SAME_SCUMM_LIVE_ROOM_CONTROL+$12
SCUMM_LIVE_ROOM_TEMP2 = SAME_SCUMM_LIVE_ROOM_CONTROL+$14
SCUMM_LIVE_ROOM_TEMP3 = SAME_SCUMM_LIVE_ROOM_CONTROL+$16
SCUMM_LIVE_ROOM_TEMP4 = SAME_SCUMM_LIVE_ROOM_CONTROL+$18
SCUMM_LIVE_ROOM_TEMP5 = SAME_SCUMM_LIVE_ROOM_CONTROL+$1A
SCUMM_LIVE_ROOM_TEMP_BYTE = SAME_SCUMM_LIVE_ROOM_CONTROL+$1C

SCUMM_LIVE_ROOM_BOX_FLAGS_OFFSET = $001C
SCUMM_LIVE_ROOM_GEOMETRY_OFFSET = $001E
SCUMM_LIVE_ROOM_ROUTES_OFFSET = $0020
SCUMM_LIVE_ROOM_PORTALS_OFFSET = $0022
SCUMM_LIVE_ROOM_OBJECTS_OFFSET = $0024
SCUMM_LIVE_ROOM_NAMES_OFFSET = $0026
SCUMM_LIVE_ROOM_OBJECT_WALK_OFFSET = $0028
SCUMM_LIVE_ROOM_VERBS_OFFSET = $002A
SCUMM_LIVE_ROOM_LOCALS_OFFSET = $002C
SCUMM_LIVE_ROOM_BUNDLE_OFFSET = $002E
SCUMM_LIVE_ROOM_BOX_COUNT = $000E
SCUMM_LIVE_ROOM_OBJECT_COUNT = $0010
SCUMM_LIVE_ROOM_VERB_COUNT = $0012
SCUMM_LIVE_ROOM_LOCAL_COUNT = $0014
SCUMM_LIVE_ROOM_BUNDLE_COUNT = $0016

; Initiate the next checked read for stages METADATA, PALETTE, or PIXELS.
; The incoming room number indexes compiler-generated directories; no ROM
; copy of the live resource payload is consulted here.
ScummV5_MsuLiveRoom_Start_Far:
    sep #$20
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_MsuLiveRoom_Start_Far__not_waiting
    jmp ScummV5_MsuLiveRoom_Start_Far__wait
ScummV5_MsuLiveRoom_Start_Far__not_waiting:
    .a8
    lda.l SCUMM_LIVE_ROOM_STAGE
    cmp #SCUMM_LIVE_ROOM_STAGE_METADATA
    bne ScummV5_MsuLiveRoom_Start_Far__not_metadata
    jmp ScummV5_MsuLiveRoom_Start_Far__metadata
ScummV5_MsuLiveRoom_Start_Far__not_metadata:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_PALETTE
    bne ScummV5_MsuLiveRoom_Start_Far__not_palette
    jmp ScummV5_MsuLiveRoom_Start_Far__palette
ScummV5_MsuLiveRoom_Start_Far__not_palette:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_PIXELS
    bne ScummV5_MsuLiveRoom_Start_Far__not_pixels
    jmp ScummV5_MsuLiveRoom_Start_Far__pixels
ScummV5_MsuLiveRoom_Start_Far__not_pixels:
    sec
    rtl
ScummV5_MsuLiveRoom_Start_Far__metadata:
    .a8
.if SAME_SCUMM_MSU1_LIVE_ROOM_PCM_TEST_TRACK > 0
    ; Optional diagnostic: start one looping MSU PCM track when the first
    ; package-backed room transaction begins. This tests data/audio overlap;
    ; no SCUMM semantic command or production profile depends on the hook.
    lda.l SAME_SCUMM_LIVE_ROOM_CONTROL+$20
    bne ScummV5_MsuLiveRoom_Start_Far__pcm_started
    lda #$01
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$20
    rep #$30
    .a16
    .i16
    lda #SAME_SCUMM_MSU1_LIVE_ROOM_PCM_TEST_TRACK
    ldx #$0001
    jsl Same_Msu1_Audio_Play_Far
    sep #$20
    .a8
ScummV5_MsuLiveRoom_Start_Far__pcm_started:
    .a8
.endif
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_LIVE_ROOM_COUNT
    bcc ScummV5_MsuLiveRoom_Start_Far__metadata_room_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__metadata_room_ok:
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0 ; room * 10
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH+1
    inx
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #SCUMM_LIVE_ROOM_MAX_SIZE+1
    bcc ScummV5_MsuLiveRoom_Start_Far__metadata_length_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__metadata_length_ok:
    .a16
    lda #SCUMM_LIVE_ROOM_MAX_SIZE
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #<SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION+1
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
    sta.l SAME_MSU1_DESTINATION+2
    jmp ScummV5_MsuLiveRoom_Start_Far__read

ScummV5_MsuLiveRoom_Start_Far__palette:
ScummV5_MsuLiveRoom_Start_Far__pixels:
    ; The compiler directory stores one 26-byte record per source room:
    ; pixel off/len/CRC, palette off/len/CRC, width/height/pitch.
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_VISUAL_COUNT
    bcc ScummV5_MsuLiveRoom_Start_Far__visual_room_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__visual_room_ok:
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; room * 2
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; room * 8
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    tax ; (room * 13) * 2 = room * 26
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_STAGE
    cmp #SCUMM_LIVE_ROOM_STAGE_PALETTE
    bne ScummV5_MsuLiveRoom_Start_Far__pixels_row
    jmp ScummV5_MsuLiveRoom_Start_Far__palette_row
ScummV5_MsuLiveRoom_Start_Far__pixels_row:
    ; Pixel descriptor fields at byte offsets 0,4,6.
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH+1
    inx
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #$E000
    beq ScummV5_MsuLiveRoom_Start_Far__pixel_length_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__pixel_length_ok:
    .a16
    lda #$E000
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #$00
    sta.l SAME_MSU1_DESTINATION
    sta.l SAME_MSU1_DESTINATION+1
    lda #SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BANK
    sta.l SAME_MSU1_DESTINATION+2
    jmp ScummV5_MsuLiveRoom_Start_Far__read

ScummV5_MsuLiveRoom_Start_Far__palette_row:
    ; Palette descriptor fields at byte offsets 10,14,16. The dimensions are
    ; checked here because the current mode-3 live surface is exactly 256x224.
    rep #$20
    .a16
    txa
    sta.l SCUMM_LIVE_ROOM_DIRECTORY_OFFSET
    txa
    clc
    adc #$000A
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH+1
    inx
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuVisualRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$00
    ; X now addresses the width word (row+20); the first byte is 00 for 256.
    beq ScummV5_MsuLiveRoom_Start_Far__width_low_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__width_low_ok:
    .a8
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$01
    bne ScummV5_MsuLiveRoom_Start_Far__invalid
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$E0
    bne ScummV5_MsuLiveRoom_Start_Far__invalid
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$00
    bne ScummV5_MsuLiveRoom_Start_Far__invalid
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$00
    bne ScummV5_MsuLiveRoom_Start_Far__invalid
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$01
    bne ScummV5_MsuLiveRoom_Start_Far__invalid
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #$0300
    beq ScummV5_MsuLiveRoom_Start_Far__palette_length_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__palette_length_ok:
    .a16
    lda #$0300
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #<SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE
    sta.l SAME_MSU1_DESTINATION+1
    lda #$40
    sta.l SAME_MSU1_DESTINATION+2

ScummV5_MsuLiveRoom_Start_Far__read:
    sep #$20
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
    bcs ScummV5_MsuLiveRoom_Start_Far__invalid
    lda #$FF
    sta.l SAME_SCUMM_MSU_ROOM_CACHE_SLOT
    lda #SCUMM_MSU_ROOM_READING
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_MsuLiveRoom_Start_Far__wait:
    clc
    rtl
ScummV5_MsuLiveRoom_Start_Far__invalid:
    .a8
    lda #$95
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F
    sec
    rtl

; Called only after SAME has completed its range-checked transfer and CRC.
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far:
    .a8
    lda #$A3
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1D
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_STAGE
    cmp #SCUMM_LIVE_ROOM_STAGE_METADATA
    beq ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata
    cmp #SCUMM_LIVE_ROOM_STAGE_PALETTE
    beq ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__palette
    cmp #SCUMM_LIVE_ROOM_STAGE_PIXELS
    beq ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__pixels
    jml ScummV5_MsuRoom_Service_Far__fail
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata:
    jsl ScummV5_LiveRoom_Validate_Far
    bcc ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_ok
    jml ScummV5_MsuRoom_Service_Far__fail
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_ok:
    .a8
    lda #$A4
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1D
    .a8
    lda #SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY
    sta.l SCUMM_LIVE_ROOM_STAGE
    bra ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__palette:
    .a8
    lda #SCUMM_LIVE_ROOM_STAGE_PIXELS
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__pixels:
    .a8
    lda #SCUMM_LIVE_ROOM_STAGE_COMMIT_READY
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #$01
    sta.l SCUMM_LIVE_ROOM_VALID
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready:
    .a8
    lda #SCUMM_MSU_ROOM_VALIDATED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    lda #$05
    sta.l SAME_SCUMM_M23A_PHASE
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_VALIDATIONS
    inc
    sta.l SAME_SCUMM_MSU_ROOM_VALIDATIONS
    sec
    rtl

; Validate SC5LIVE after the storage provider has authenticated its CRC.
; The compiler emits canonical, contiguous table offsets and the exact room
; record length; this guard repeats identity/schema/bounds checks before the
; record becomes the active source for existing SCUMM consumers.
ScummV5_LiveRoom_Validate_Far:
    .a8
    lda #$B0
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    sep #$20
    .a8
    ldx #$0000
ScummV5_LiveRoom_Validate_Far__magic:
    .a8
    lda.l SCUMM_LIVE_ROOM_PENDING,x
    cmp.l ScummV5_LiveRoom_Magic,x
    bne ScummV5_LiveRoom_Validate_Far__bad
    inx
    cpx #$0008
    bcc ScummV5_LiveRoom_Validate_Far__magic
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_PENDING+$08
    cmp #$0001
    bne ScummV5_LiveRoom_Validate_Far__bad
    lda.l SCUMM_LIVE_ROOM_PENDING+$0A
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bne ScummV5_LiveRoom_Validate_Far__bad
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_PENDING+$0C
    cmp.l SAME_SCUMM_LIVE_ROOM_CONTROL+$0C
    bne ScummV5_LiveRoom_Validate_Far__bad
    lda.l SCUMM_LIVE_ROOM_PENDING+$0D
    and #$FE
    bne ScummV5_LiveRoom_Validate_Far__bad
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_PENDING+$30
    cmp.l SCUMM_LIVE_ROOM_READ_LENGTH
    bne ScummV5_LiveRoom_Validate_Far__bad
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bcc ScummV5_LiveRoom_Validate_Far__bad
    cmp #SCUMM_LIVE_ROOM_MAX_SIZE+1
    bcs ScummV5_LiveRoom_Validate_Far__bad
    lda.l SCUMM_LIVE_ROOM_PENDING+$1C
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bne ScummV5_LiveRoom_Validate_Far__bad
    ; The final bundle table must terminate exactly at total_size. This also
    ; rejects malformed counts/offsets before any native consumer indexes it.
    lda.l SCUMM_LIVE_ROOM_PENDING+$2E
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_PENDING+$16
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SCUMM_LIVE_ROOM_PENDING+$30
    bne ScummV5_LiveRoom_Validate_Far__bad
    sep #$20
    .a8
    lda #$B1
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    clc
    rtl
ScummV5_LiveRoom_Validate_Far__bad:
    sep #$20
    .a8
    lda #$94
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1F
    lda #$B2
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    sec
    rtl

; Publish validated pixels and palette into the existing mode-3 surface. The
; only pixel source is the checked pending BWRAM resource; no ROM visual table
; or row payload is available in this build.
ScummV5_LiveRoom_PublishVisual_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_VALID
    and #$00FF
    cmp #$0001
    bne ScummV5_LiveRoom_PublishVisual_Far__bad
    ldx #$0000
ScummV5_LiveRoom_PublishVisual_Far__pixels:
    .a16
    .i16
    ; The checked 57-KiB SC5VIS pixel payload is staged in the carrier-owned
    ; pixel staging allocation, not the 2-KiB metadata buffer. Publish only
    ; after CRC and descriptor validation.
    lda.l SAME_SCUMM_LIVE_ROOM_PIXEL_STAGE_BASE,x
    sta.l SAME_SCUMM_LIVE_ROOM_SURFACE_BASE,x
    inx
    inx
    cpx #$E000
    bcc ScummV5_LiveRoom_PublishVisual_Far__pixels
    ; The surface service owns backend palette storage. Give it the checked
    ; RGB8 source through its target-neutral request pointer instead of
    ; naming Mode-3 memory from the SCUMM engine.
    sep #$20
    .a8
    lda #<SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE
    lda #>SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$01
    lda #$40
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$02
    jsl Same_VideoSurface_InstallPalette_Far
    rep #$20
    .a16
    lda #$0100
    sta.l SAME_VIDEO_SURFACE_WIDTH
    lda #$00E0
    sta.l SAME_VIDEO_SURFACE_HEIGHT
    lda #$0100
    sta.l SAME_VIDEO_SURFACE_PITCH
    lda #$0000
    sta.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_VIDEO_SURFACE_DEST_X
    sta.l SAME_VIDEO_SURFACE_DEST_Y
    lda #$0100
    sta.l SAME_VIDEO_SURFACE_COPY_WIDTH
    lda #$00E0
    sta.l SAME_VIDEO_SURFACE_COPY_HEIGHT
    sep #$20
    .a8
    ; This is the active-surface lifetime, distinct from VALID for the current
    ; incoming transfer. A later room request may clear transaction VALID
    ; while this installed image remains the surface being presented.
    lda #$01
    sta.l SCUMM_LIVE_ROOM_ACTIVE_VISUAL_VALID
    plp
    clc
    rtl
ScummV5_LiveRoom_PublishVisual_Far__bad:
    plp
    sec
    rtl

; Install only already-validated SC5LIVE metadata into the ordinary SCUMM
; working arrays.  Existing semantic code continues to consume these arrays;
; no parallel parser or alternate object/movement engine is introduced.
ScummV5_LiveRoom_LoadActiveRoom_Far:
    php
    rep #$30
    .a16
    .i16
    phx
    phy
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_MATRIX_BOX_COUNT
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_VALID
    sta.l SAME_SCUMM_MATRIX_EXEC_COUNT
    sta.l SAME_SCUMM_MATRIX_LAST_SUBOP
    sta.l SAME_SCUMM_MATRIX_LAST_BOX
    sta.l SAME_SCUMM_MATRIX_LAST_FLAGS
    sta.l SAME_SCUMM_MATRIX_TRACE_COUNT
    sta.l SAME_SCUMM_PUT_ACTOR_EXEC_COUNT
    sta.l SAME_SCUMM_PUT_ACTOR_ACTOR
    sta.l SAME_SCUMM_PUT_ACTOR_TRACE_COUNT
    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT
    sta.l SAME_SCUMM_SETSTATE_BG_REDRAW
    sta.l SAME_SCUMM_SETSTATE_DIRTY_COUNT
    sta.l SAME_SCUMM_SETSTATE_DRAW_QUEUE_COUNT
    sta.l SAME_SCUMM_SETSTATE_TRACE_COUNT
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SAME_SCUMM_MATRIX_BOX_COUNT
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_FLAGS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP1
    ldx #$0000
ScummV5_LiveRoom_LoadActiveRoom_Far__flags:
    txa
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    bcs ScummV5_LiveRoom_LoadActiveRoom_Far__objects_start
    txa
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    pha
    txa
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP1
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_SCUMM_MATRIX_BOX_FLAGS,x
    rep #$20
    .a16
    inx
    bra ScummV5_LiveRoom_LoadActiveRoom_Far__flags
ScummV5_LiveRoom_LoadActiveRoom_Far__objects_start:
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SAME_SCUMM_SETSTATE_LOCAL_COUNT
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_TEMP2
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_TEMP2
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    adc.l SCUMM_LIVE_ROOM_TEMP2 ; 11 bytes per cooked object record
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECTS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP2
    ldx #$0000
ScummV5_LiveRoom_LoadActiveRoom_Far__objects:
    txa
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcs ScummV5_LiveRoom_LoadActiveRoom_Far__names
    txa
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    pha
    txa
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP2
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_SCUMM_SETSTATE_LOCAL_RECORDS,x
    rep #$20
    .a16
    inx
    bra ScummV5_LiveRoom_LoadActiveRoom_Far__objects
ScummV5_LiveRoom_LoadActiveRoom_Far__names:
    jsl ScummV5_LiveRoom_LoadNames_Far
    ply
    plx
    plp
    rtl

; Translate the compiler-owned OBNA table into SAME's existing object-name
; cache. Names remain resource-owned but consumers keep their established API.
ScummV5_LiveRoom_LoadNames_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; object rows remaining
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_NAMES_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; current 34-byte row
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1
ScummV5_LiveRoom_LoadNames_Far__row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP3
    bne ScummV5_LiveRoom_LoadNames_Far__has_row
    jmp ScummV5_LiveRoom_LoadNames_Far__done
ScummV5_LiveRoom_LoadNames_Far__has_row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; object id
    asl
    asl
    asl
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; destination name offset
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0002
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; source string offset
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_WIDTH ; name length
ScummV5_LiveRoom_LoadNames_Far__char:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp #$0020
    bcs ScummV5_LiveRoom_LoadNames_Far__store_length
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP5
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    sta.l SAME_SCUMM_OBJECT_NAMES,x
    beq ScummV5_LiveRoom_LoadNames_Far__length_done
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_WIDTH
    inc
    sta.l SCUMM_LIVE_ROOM_WIDTH
ScummV5_LiveRoom_LoadNames_Far__length_done:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    bra ScummV5_LiveRoom_LoadNames_Far__char
ScummV5_LiveRoom_LoadNames_Far__store_length:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp #$0400
    bcs ScummV5_LiveRoom_LoadNames_Far__next
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_WIDTH
    sta.l SAME_SCUMM_OBJECT_NAME_LENGTH,x
ScummV5_LiveRoom_LoadNames_Far__next:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0022
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    jmp ScummV5_LiveRoom_LoadNames_Far__row
ScummV5_LiveRoom_LoadNames_Far__done:
    plp
    rtl

ScummV5_LiveRoom_LoadGeometry_Far:
    rep #$30
    .a16
    .i16
    txa
    sta.l SCUMM_LIVE_ROOM_TEMP0
    txa
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcs ScummV5_LiveRoom_LoadGeometry_Far__bad
    txa
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP1
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_GEOMETRY_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; source offset
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; destination byte offset
ScummV5_LiveRoom_LoadGeometry_Far__copy:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    pha
    lda.l SCUMM_LIVE_ROOM_TEMP1
    tax
    pla
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK,x
    lda.l SCUMM_LIVE_ROOM_TEMP0
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    inc
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP1
    cmp #$0012
    bcc ScummV5_LiveRoom_LoadGeometry_Far__copy
    sep #$20
    .a8
    clc
    rtl
ScummV5_LiveRoom_LoadGeometry_Far__bad:
    sep #$20
    .a8
    sec
    rtl

; Matrix next-box byte lookup, preserving the existing A=u8/carry contract.
ScummV5_LiveRoom_NextBox_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcs ScummV5_LiveRoom_NextBox_Far__bad
    lda.l SAME_SCUMM_MOVE_ROUTE_DEST
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcs ScummV5_LiveRoom_NextBox_Far__bad
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP2
ScummV5_LiveRoom_NextBox_Far__multiply:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    beq ScummV5_LiveRoom_NextBox_Far__index
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP0
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP0
    bra ScummV5_LiveRoom_NextBox_Far__multiply
ScummV5_LiveRoom_NextBox_Far__index:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SAME_SCUMM_MOVE_ROUTE_DEST
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_ROUTES_OFFSET
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp #$FF
    beq ScummV5_LiveRoom_NextBox_Far__bad
    sec
    rtl
ScummV5_LiveRoom_NextBox_Far__bad:
    sep #$20
    .a8
    clc
    rtl

ScummV5_LiveRoom_Portal_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcc ScummV5_LiveRoom_Portal_Far__source_ok
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__source_ok:
    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcc ScummV5_LiveRoom_Portal_Far__next_ok
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__next_ok:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP2
ScummV5_LiveRoom_Portal_Far__multiply:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    beq ScummV5_LiveRoom_Portal_Far__index
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP0
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP0
    bra ScummV5_LiveRoom_Portal_Far__multiply
ScummV5_LiveRoom_Portal_Far__index:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SAME_SCUMM_MOVE_ROUTE_NEXT
    sta.l SCUMM_LIVE_ROOM_TEMP2
    asl
    asl
    asl
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP2 ; index * 7
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_PORTAL_TYPE
    beq ScummV5_LiveRoom_Portal_Far__bad
    inx
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_PORTAL_FIXED
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_PORTAL_LOW
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_PORTAL_HIGH
    sep #$20
    .a8
    sec
    rtl
ScummV5_LiveRoom_Portal_Far__bad:
    sep #$20
    .a8
    clc
    rtl

ScummV5_LiveRoom_ObjectWalk_Far:
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_WALK_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0
ScummV5_LiveRoom_ObjectWalk_Far__loop:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_ObjectWalk_Far__bad
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_MOVE_OBJECT
    beq ScummV5_LiveRoom_ObjectWalk_Far__found
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$000C
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_ObjectWalk_Far__loop
ScummV5_LiveRoom_ObjectWalk_Far__found:
    .a16
    txa
    clc
    adc #$0002
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_REQUEST_X
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_REQUEST_Y
    sep #$20
    .a8
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_QUERY_DIR
    inx
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_X
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_Y
    inx
    inx
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    sec
    rtl
ScummV5_LiveRoom_ObjectWalk_Far__bad:
    sep #$20
    .a8
    clc
    rtl

; Locate a room-local script by source LSCR number in the active record.
ScummV5_LiveRoom_ResolveLocalScript_Far:
    php
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_LOCAL_SCRIPT
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_LOCAL_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_LOCALS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0
ScummV5_LiveRoom_ResolveLocalScript_Far__loop:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_ResolveLocalScript_Far__missing
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_RESIDENT_LOCAL_SCRIPT
    beq ScummV5_LiveRoom_ResolveLocalScript_Far__found
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0003
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_ResolveLocalScript_Far__loop
ScummV5_LiveRoom_ResolveLocalScript_Far__found:
    rep #$20
    .a16
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcs ScummV5_LiveRoom_ResolveLocalScript_Far__resolved
    plp
    clc
    rtl
ScummV5_LiveRoom_ResolveLocalScript_Far__resolved:
    plp
    sec
    rtl
ScummV5_LiveRoom_ResolveLocalScript_Far__missing:
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Eagerly bind/unbind exactly the ProgramUnits listed in the validated active
; room bundle table. The generated ROM directory remains absent in this mode.
ScummV5_LiveRoom_LoadBundle_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BUNDLE_COUNT
    cmp #$0100
    bcs ScummV5_LiveRoom_LoadBundle_Far__bad
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BUNDLE_OFFSET
    sta.l SCUMM_LIVE_ROOM_DIRECTORY_OFFSET
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
ScummV5_LiveRoom_LoadBundle_Far__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    beq ScummV5_LiveRoom_LoadBundle_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_DIRECTORY_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcc ScummV5_LiveRoom_LoadBundle_Far__rollback
    jsl ScummV5_Resident_PinRoomBundle_Far
    bcs ScummV5_LiveRoom_LoadBundle_Far__rollback
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
    rep #$20
    .a16
    bra ScummV5_LiveRoom_LoadBundle_Far__loop
ScummV5_LiveRoom_LoadBundle_Far__done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_LOADS
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_LOADS
    plp
    sec
    rtl
ScummV5_LiveRoom_LoadBundle_Far__rollback:
    lda.l SAME_SCUMM_M23A_ACTIVE_RECORD
    jsl ScummV5_LiveRoom_ReleaseBundle_Far
    plp
    clc
    rtl
ScummV5_LiveRoom_LoadBundle_Far__bad:
    sep #$20
    .a8
    lda #$03
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

ScummV5_LiveRoom_ReleaseBundle_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BUNDLE_COUNT
    cmp #$0100
    bcs ScummV5_LiveRoom_ReleaseBundle_Far__bad
    sep #$20
    .a8
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BUNDLE_OFFSET
    sta.l SCUMM_LIVE_ROOM_DIRECTORY_OFFSET
    lda #$0000
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
ScummV5_LiveRoom_ReleaseBundle_Far__loop:
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_REMAINING
    beq ScummV5_LiveRoom_ReleaseBundle_Far__done
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_OFFSET
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_DIRECTORY_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    jsl ScummV5_Resident_FindSelectorForProgramUnit_Far
    bcc ScummV5_LiveRoom_ReleaseBundle_Far__next
    sta.l SAME_SCUMM_RESIDENT_SELECTOR
    jsl ScummV5_Resident_UnpinRoomBundle_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_RESIDENT_SELECTOR
    jsl ScummV5_Resident_ReleaseIfUnowned_Far
ScummV5_LiveRoom_ReleaseBundle_Far__next:
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
    rep #$20
    .a16
    bra ScummV5_LiveRoom_ReleaseBundle_Far__loop
ScummV5_LiveRoom_ReleaseBundle_Far__done:
    rep #$20
    .a16
    lda.l SAME_SCUMM_RESIDENT_BUNDLE_RELEASES
    inc
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_RELEASES
    plp
    sec
    rtl
ScummV5_LiveRoom_ReleaseBundle_Far__bad:
    sep #$20
    .a8
    lda #$04
    sta.l SAME_SCUMM_RESIDENT_BUNDLE_FAILURE
    lda #SCUMM_ERR_RESIDENCY_ID
    sta.l SAME_SCUMM_ERROR
    plp
    clc
    rtl

; Find one current object/verb table row. Output entry PC in VERB_RESULT and
; owning carrier ID in TEMP2; fallback verb $FF retains existing semantics.
ScummV5_LiveRoom_VerbQuery_Far:
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_VERB_RESULT
    lda #$FFFF
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_VERB_COUNT
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_VERBS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0
ScummV5_LiveRoom_VerbQuery_Far__loop:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_VerbQuery_Far__absent
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_VERB_OBJECT
    bne ScummV5_LiveRoom_VerbQuery_Far__next
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_VERB_ID
    beq ScummV5_LiveRoom_VerbQuery_Far__found
    cmp #$00FF
    beq ScummV5_LiveRoom_VerbQuery_Far__found
ScummV5_LiveRoom_VerbQuery_Far__next:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0008
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_VerbQuery_Far__loop
ScummV5_LiveRoom_VerbQuery_Far__found:
    .a16
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_VERB_RESULT
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2
ScummV5_LiveRoom_VerbQuery_Far__absent:
    sec
    rtl

ScummV5_LiveRoom_ObjectProgramResolve_Far:
    jsl ScummV5_LiveRoom_VerbQuery_Far
    lda.l SAME_SCUMM_VERB_RESULT
    beq ScummV5_LiveRoom_ObjectProgramResolve_Far__bad
    lda.l SCUMM_LIVE_ROOM_TEMP2
    jsl ScummV5_Resident_ResolveProgramUnit_Far
    bcc ScummV5_LiveRoom_ObjectProgramResolve_Far__bad
    sep #$20
    .a8
    sec
    rtl
ScummV5_LiveRoom_ObjectProgramResolve_Far__bad:
    sep #$20
    .a8
    lda #SCUMM_ERR_SCRIPT
    sta.l SAME_SCUMM_ERROR
    clc
    rtl

; Controller and direct verb enumeration share the same active-room table.
ScummV5_LiveRoom_VerbFirst_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_VERB_OBJECT
    sta.l SAME_SCUMM_INTERACTION_OBJECT
    lda #$0000
    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST
    lda #$0002 ; enumeration mode: return the first authored verb
    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER
    jml ScummV5_LiveRoom_VerbEnumerate_Far
ScummV5_LiveRoom_GenericVerbFirst_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_INTERACTION_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    jml ScummV5_LiveRoom_VerbFirst_Far
ScummV5_LiveRoom_VerbNext_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_VERB_OBJECT
    sta.l SAME_SCUMM_INTERACTION_OBJECT
    lda #$0000
    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER
    lda #$0000
    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST
    jml ScummV5_LiveRoom_VerbEnumerate_Far
ScummV5_LiveRoom_GenericVerbNext_Far:
    rep #$20
    .a16
    lda.l SAME_SCUMM_INTERACTION_OBJECT
    sta.l SAME_SCUMM_VERB_OBJECT
    jml ScummV5_LiveRoom_VerbNext_Far

ScummV5_LiveRoom_VerbEnumerate_Far:
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_VERB_COUNT
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_VERBS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0
ScummV5_LiveRoom_VerbEnumerate_Far__loop:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_VerbEnumerate_Far__wrap
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_INTERACTION_OBJECT
    bne ScummV5_LiveRoom_VerbEnumerate_Far__next
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp #$00FF
    beq ScummV5_LiveRoom_VerbEnumerate_Far__next
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SAME_SCUMM_INTERACTION_VERB_AFTER
    cmp #$0002
    beq ScummV5_LiveRoom_VerbEnumerate_Far__return
    cmp #$0001
    beq ScummV5_LiveRoom_VerbEnumerate_Far__return
    lda.l SAME_SCUMM_INTERACTION_VERB_FIRST
    bne ScummV5_LiveRoom_VerbEnumerate_Far__compare_current
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SAME_SCUMM_INTERACTION_VERB_FIRST
ScummV5_LiveRoom_VerbEnumerate_Far__compare_current:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SAME_SCUMM_VERB_ID
    bne ScummV5_LiveRoom_VerbEnumerate_Far__next
    lda #$0001
    sta.l SAME_SCUMM_INTERACTION_VERB_AFTER
ScummV5_LiveRoom_VerbEnumerate_Far__next:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0008
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_VerbEnumerate_Far__loop
ScummV5_LiveRoom_VerbEnumerate_Far__return:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SAME_SCUMM_VERB_RESULT
    sec
    rtl
ScummV5_LiveRoom_VerbEnumerate_Far__wrap:
    lda.l SAME_SCUMM_INTERACTION_VERB_FIRST
    beq ScummV5_LiveRoom_VerbEnumerate_Far__miss
    sta.l SAME_SCUMM_VERB_RESULT
    sec
    rtl
ScummV5_LiveRoom_VerbEnumerate_Far__miss:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_VERB_RESULT
    clc
    rtl

ScummV5_LiveRoom_Magic:
    .byte $53,$43,$35,$4C,$49,$56,$45,$00
