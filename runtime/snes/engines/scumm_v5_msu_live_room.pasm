; Feature-gated live SCUMM room resources backed by checked SAMEPKG reads.
; The existing code-window cache remains reserved for executable bodies and
; the short SC5ROOM validation record. Live metadata is staged in the packed
; SA-1 incoming-room allocation, committed only after outgoing EXCD, and
; retained in the mode-3 diagnostic-fixture alias (mutually exclusive with
; its conformance engine). Visual pixels and
; palette are fetched into their own audited BWRAM allocations.

.bank 84
.org $8000

SCUMM_LIVE_ROOM_DIRECTORY_OFFSET = SAME_SCUMM_LIVE_ROOM_CONTROL+$0E
SCUMM_LIVE_ROOM_TEMP0 = SAME_SCUMM_LIVE_ROOM_CONTROL+$10
SCUMM_LIVE_ROOM_TEMP1 = SAME_SCUMM_LIVE_ROOM_CONTROL+$12
SCUMM_LIVE_ROOM_TEMP2 = SAME_SCUMM_LIVE_ROOM_CONTROL+$14
SCUMM_LIVE_ROOM_TEMP3 = SAME_SCUMM_LIVE_ROOM_CONTROL+$16
SCUMM_LIVE_ROOM_TEMP4 = SAME_SCUMM_LIVE_ROOM_CONTROL+$18
SCUMM_LIVE_ROOM_TEMP5 = SAME_SCUMM_LIVE_ROOM_CONTROL+$1A
SCUMM_LIVE_ROOM_TEMP_BYTE = SAME_SCUMM_LIVE_ROOM_CONTROL+$1C
; Persistent diagnostic checkpoint for the SC5LIVE validator.  $1D is the
; loader's per-frame transient state and is intentionally not used here.
SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT = SAME_SCUMM_LIVE_ROOM_CONTROL+$3D

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
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
; Sectioned v4 chunks are installed into the active metadata allocation only
; after outgoing EXCD. Validate the installed record there; v2/v3 retain the
; single pending-record validation path.
SCUMM_LIVE_ROOM_VALIDATION_BASE = SAME_SCUMM_LIVE_ROOM_STAGING_BASE
.else
SCUMM_LIVE_ROOM_VALIDATION_BASE = SCUMM_LIVE_ROOM_PENDING
.endif

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
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    cmp #$FF
    beq ScummV5_MsuLiveRoom_Start_Far__provider_idle
    jmp ScummV5_MsuLiveRoom_Start_Far__wait
ScummV5_MsuLiveRoom_Start_Far__provider_idle:
    .a8
    lda.l SCUMM_LIVE_ROOM_STAGE
    cmp #SCUMM_LIVE_ROOM_STAGE_METADATA
    bne ScummV5_MsuLiveRoom_Start_Far__not_metadata
    jmp ScummV5_MsuLiveRoom_Start_Far__metadata
ScummV5_MsuLiveRoom_Start_Far__not_metadata:
    .a8
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #SCUMM_LIVE_ROOM_STAGE_INSTALL
    bne ScummV5_MsuLiveRoom_Start_Far__not_install
    jmp ScummV5_MsuLiveRoom_Start_Far__install
ScummV5_MsuLiveRoom_Start_Far__not_install:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_ROUTES
    bne ScummV5_MsuLiveRoom_Start_Far__not_routes
    jmp ScummV5_MsuLiveRoom_Start_Far__routes
ScummV5_MsuLiveRoom_Start_Far__not_routes:
    .a8
.endif
    cmp #SCUMM_LIVE_ROOM_STAGE_PALETTE
    bne ScummV5_MsuLiveRoom_Start_Far__not_palette
    jmp ScummV5_MsuLiveRoom_Start_Far__palette
ScummV5_MsuLiveRoom_Start_Far__not_palette:
    .a8
    .if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #SCUMM_LIVE_ROOM_STAGE_INSTALL
    bne ScummV5_MsuLiveRoom_Start_Far__dispatch_not_install
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__install
ScummV5_MsuLiveRoom_Start_Far__dispatch_not_install:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_ROUTES
    bne ScummV5_MsuLiveRoom_Start_Far__dispatch_not_routes
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__routes
ScummV5_MsuLiveRoom_Start_Far__dispatch_not_routes:
    .a8
    .endif
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
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_LIVE_ROOM_COUNT
    bcc ScummV5_MsuLiveRoom_Start_Far__metadata_v4_room_ok
    sep #$20
    .a8
    lda #$A5
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__metadata_v4_room_ok:
    sta.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0 ; room * 13
    tax
    sep #$20
    .a8
    inx
    inx
    inx
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH+1
    inx
    inx
    inx
    inx
    inx ; skip all four CRC bytes: chunk-first index is record byte +10
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SCUMM_LIVE_ROOM_CHUNK_FIRST
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SCUMM_LIVE_ROOM_CHUNK_FIRST+1
    inx
    lda.l ScummV5_MsuLiveRoomRecords,x
    sta.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    jsl ScummV5_MsuLiveRoom_PrepareChunkRead_Far
    bcs ScummV5_MsuLiveRoom_Start_Far__metadata_v4_prepared
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__metadata_v4_prepared:
    jmp ScummV5_MsuLiveRoom_Start_Far__read
.else
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_LIVE_ROOM_COUNT
    bcc ScummV5_MsuLiveRoom_Start_Far__metadata_room_ok
    sep #$20
    .a8
    lda #$A5
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
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
    sep #$20
    .a8
    lda #$A6
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__metadata_length_ok:
    .a16
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_CAPACITY
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
.endif

.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
ScummV5_MsuLiveRoom_Start_Far__install:
    .a8
    lda #$01
    sta.l SCUMM_LIVE_ROOM_CHUNK_MODE
    jsl ScummV5_MsuLiveRoom_PrepareChunkRead_Far
    bcs ScummV5_MsuLiveRoom_Start_Far__install_prepared
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__install_prepared:
    jmp ScummV5_MsuLiveRoom_Start_Far__read

; Read one table row from the generated chunk directory. Every fetch has its
; own expected CRC; active writes are post-EXCD only and remain unpublished
; until the final chunk completes.
ScummV5_MsuLiveRoom_PrepareChunkRead_Far:
    php
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_CHUNK_FIRST
    clc
    adc.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    cmp #SCUMM_MSU1_LIVE_CHUNK_COUNT
    bcc ScummV5_MsuLiveRoom_PrepareChunkRead_Far__directory_index_ok
    jmp ScummV5_MsuLiveRoom_PrepareChunkRead_Far__invalid
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__directory_index_ok:
    sta.l SCUMM_LIVE_ROOM_TEMP0
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; *2
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1 ; *10
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuLiveRoomChunkRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    beq ScummV5_MsuLiveRoom_PrepareChunkRead_Far__invalid
    cmp #$0801
    bcc ScummV5_MsuLiveRoom_PrepareChunkRead_Far__length_ok
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__invalid:
    plp
    clc
    rtl
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__length_ok:
    lda.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_CHUNK_START ; index * 2048
    ; Require each generated row to be the exact contiguous page implied by
    ; the checked complete-record length.
    lda.l SCUMM_LIVE_ROOM_CHUNK_START
    cmp.l SCUMM_LIVE_ROOM_READ_LENGTH
    bcc ScummV5_MsuLiveRoom_PrepareChunkRead_Far__start_in_body
    jmp ScummV5_MsuLiveRoom_PrepareChunkRead_Far__invalid
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__start_in_body:
    .a16
    lda.l SCUMM_LIVE_ROOM_READ_LENGTH
    sec
    sbc.l SCUMM_LIVE_ROOM_CHUNK_START
    cmp #$0800
    bcc ScummV5_MsuLiveRoom_PrepareChunkRead_Far__expected_short
    lda #$0800
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__expected_short:
    cmp.l SAME_MSU1_REQUEST_LENGTH
    beq ScummV5_MsuLiveRoom_PrepareChunkRead_Far__exact_length
    jmp ScummV5_MsuLiveRoom_PrepareChunkRead_Far__invalid
ScummV5_MsuLiveRoom_PrepareChunkRead_Far__exact_length:
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_MSU1_DEST_CAPACITY
    rep #$20
    .a16
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_CAPACITY
    sta.l SAME_MSU1_DEST_CAPACITY
    sep #$20
    .a8
    lda #<SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION
    lda #>SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    sta.l SAME_MSU1_DESTINATION+1
    lda #SAME_SCUMM_LIVE_ROOM_PENDING_BANK
    sta.l SAME_MSU1_DESTINATION+2
    plp
    sec
    rtl

ScummV5_MsuLiveRoom_Start_Far__routes:
    rep #$20
    .a16
    lda.l SAME_SCUMM_MSU_ROOM_ID
    and #$00FF
    cmp #SCUMM_MSU1_LIVE_ROOM_COUNT
    bcc ScummV5_MsuLiveRoom_Start_Far__routes_room_ok
    sep #$20
    .a8
    lda #$A5
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__routes_room_ok:
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0 ; room * 10
    tax
    sep #$20
    .a8
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+1
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+2
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_OFFSET+3
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_REQUEST_LENGTH+1
    lda #$00
    sta.l SAME_MSU1_REQUEST_LENGTH+2
    sta.l SAME_MSU1_REQUEST_LENGTH+3
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+1
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+2
    inx
    lda.l ScummV5_MsuLiveRouteRecords,x
    sta.l SAME_MSU1_EXPECTED_CRC+3
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #SAME_SCUMM_LIVE_ROOM_PENDING_CAPACITY+1
    bcc ScummV5_MsuLiveRoom_Start_Far__routes_length_ok
    sep #$20
    .a8
    lda #$A6
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__routes_length_ok:
    .a16
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
.endif

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
    beq ScummV5_MsuLiveRoom_Start_Far__width_high_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__width_high_ok:
    .a8
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$E0
    beq ScummV5_MsuLiveRoom_Start_Far__height_low_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__height_low_ok:
    .a8
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$00
    beq ScummV5_MsuLiveRoom_Start_Far__height_high_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__height_high_ok:
    .a8
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$00
    beq ScummV5_MsuLiveRoom_Start_Far__pitch_low_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__pitch_low_ok:
    .a8
    inx
    lda.l ScummV5_MsuVisualRecords,x
    cmp #$01
    beq ScummV5_MsuLiveRoom_Start_Far__pitch_high_ok
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
ScummV5_MsuLiveRoom_Start_Far__pitch_high_ok:
    .a8
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
    bcc ScummV5_MsuLiveRoom_Start_Far__read_started
    lda #$A7
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    jmp ScummV5_MsuLiveRoom_Start_Far__invalid
.a8
ScummV5_MsuLiveRoom_Start_Far__read_started:
    .a8
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
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #SCUMM_LIVE_ROOM_STAGE_INSTALL
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_install
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__install
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_install:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_ROUTES
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_routes
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__routes
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_routes:
    .a8
.endif
    cmp #SCUMM_LIVE_ROOM_STAGE_PALETTE
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_palette
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__palette
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_palette:
    .a8
    cmp #SCUMM_LIVE_ROOM_STAGE_PIXELS
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_pixels
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__pixels
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__not_pixels:
    jml ScummV5_MsuRoom_Service_Far__fail
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata:
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    lda.l SCUMM_LIVE_ROOM_CHUNK_MODE
    beq ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_preflight
    jml ScummV5_MsuRoom_Service_Far__fail
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_preflight:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_advance
    jsl ScummV5_LiveRoom_ValidateSectionedHeader_Far
    bcc ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_advance
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_advance:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    cmp.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_done
    sep #$20
    .a8
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__metadata_done:
    sep #$20
    .a8
    lda #$00
    sta.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    lda #SCUMM_LIVE_ROOM_STAGE_ROUTES
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
.else
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
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready
.endif
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__routes:
    jsl ScummV5_LiveRoom_ValidateRouteDirectory_Far
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad
    sep #$20
    .a8
    lda #$C6 ; checked route directory passed
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_CHUNK_MODE
    bne ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__routes_install
    lda #SCUMM_LIVE_ROOM_STAGE_PREFLIGHT_READY
    sta.l SCUMM_LIVE_ROOM_STAGE
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__routes_install:
    ; Route payload was authenticated during preflight, but the bounded
    ; pending window is reused for metadata installation. Re-fetching here
    ; makes the exact bytes consumed by matrix expansion independently
    ; checked immediately before publication.
    jsl ScummV5_LiveRoom_ExpandRoutes_Far
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad
    sep #$20
    .a8
    lda #$C7 ; route matrix expanded into the existing engine table
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    lda #$01
    sta.l SCUMM_LIVE_ROOM_VALID
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_VALID
    lda #SCUMM_LIVE_ROOM_STAGE_INSTALL_READY
    sta.l SCUMM_LIVE_ROOM_STAGE
    jml ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__ready

ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__install:
    jsl ScummV5_LiveRoom_InstallVerifiedChunk_Far
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_CHUNK_INDEX
    cmp.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__install_complete
    sep #$20
    .a8
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl
ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__install_complete:
    jsl ScummV5_LiveRoom_Validate_Far
    bcs ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad
    sep #$20
    .a8
    lda #SCUMM_LIVE_ROOM_STAGE_ROUTES
    sta.l SCUMM_LIVE_ROOM_STAGE
    lda #SCUMM_MSU_ROOM_REQUESTED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    clc
    rtl

ScummV5_MsuLiveRoom_ValidateCompletedRead_Far__bad:
    jml ScummV5_MsuRoom_Service_Far__fail
.endif

.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
; The provider CRC covers bytes as they arrive. Copy only its checked pending
; page into active metadata; no live consumer can observe the record until
; the complete record has passed structural validation.
ScummV5_LiveRoom_InstallVerifiedChunk_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    lda.l SAME_MSU1_REQUEST_LENGTH
    beq ScummV5_LiveRoom_InstallVerifiedChunk_Far__invalid
    sep #$20
    .a8
    lda #SAME_SCUMM_LIVE_ROOM_ACTIVE_BANK
    pha
    plb ; use the explicitly audited active BWRAM bank for indexed stores
    rep #$20
    .a16
    lda.l SAME_MSU1_REQUEST_LENGTH
    pha ; bounded byte-copy counter; depth stays constant through the loop
    ldx #$0000 ; pending reads always begin at its checked staging base
    ; Source chunks live at the pending staging offset, while the active
    ; SC5LIVE record starts at offset zero in its separate BWRAM allocation.
    lda.l SCUMM_LIVE_ROOM_CHUNK_START
    tay
ScummV5_LiveRoom_InstallVerifiedChunk_Far__copy:
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta SAME_SCUMM_LIVE_ROOM_STAGING_OFFSET,y
    rep #$20
    .a16
    inx
    iny
    pla
    dec
    beq ScummV5_LiveRoom_InstallVerifiedChunk_Far__copied
    pha
    bra ScummV5_LiveRoom_InstallVerifiedChunk_Far__copy
ScummV5_LiveRoom_InstallVerifiedChunk_Far__copied:
    plb
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_LiveRoom_InstallVerifiedChunk_Far__invalid:
    plb
    ply
    plx
    pla
    plp
    sec
    rtl
.endif

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

.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
; Validate the first SC5LIVE chunk and generated chunk span before following
; any directory entry. The complete active record is revalidated after the
; post-EXCD chunk installation. Carry clear means valid.
ScummV5_LiveRoom_ValidateSectionedHeader_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$08
    cmp #$0004
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__version_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__version_ok:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$0A
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__header_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__header_ok:
    .a8
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$0C
    cmp.l SAME_SCUMM_LIVE_ROOM_CONTROL+$0C
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__room_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__room_ok:
    .a16
    rep #$20
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$30
    cmp.l SCUMM_LIVE_ROOM_READ_LENGTH
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_equal
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_equal:
    .a16
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bcs ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_min_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_min_ok:
    .a16
    cmp #SCUMM_LIVE_ROOM_MAX_SIZE+1
    bcc ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_max_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__length_max_ok:
    .a16
    ; chunks = ceil(length / 2048)
    clc
    adc #$07FF
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_count_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_count_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_CHUNK_FIRST
    bcc ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_end_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_end_ok:
    .a16
    cmp #SCUMM_MSU1_LIVE_CHUNK_COUNT+1
    bcc ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_span_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__chunk_span_ok:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$0E
    and #$00FF
    cmp #$0041
    bcc ScummV5_LiveRoom_ValidateSectionedHeader_Far__box_count_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__box_count_ok:
    .a16
    sta.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    clc
    adc #SCUMM_LIVE_ROOM_HEADER_SIZE
    sta.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$1E
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_extent:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_done
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0012
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_extent
ScummV5_LiveRoom_ValidateSectionedHeader_Far__geometry_done:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$22
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__portal_offset_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__portal_offset_ok:
    .a16
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$20
    cmp #$FFFF
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__route_sentinel_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__route_sentinel_ok:
    .a16
    ; Portal header (7) and its (box_count+1) row offsets precede objects.
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    asl
    clc
    adc #$0009
    clc
    adc.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$22
    cmp.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$24
    bcc ScummV5_LiveRoom_ValidateSectionedHeader_Far__portal_prefix_ok
    beq ScummV5_LiveRoom_ValidateSectionedHeader_Far__portal_prefix_ok
    jmp ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad
ScummV5_LiveRoom_ValidateSectionedHeader_Far__portal_prefix_ok:
    .a16
    clc
    rtl
ScummV5_LiveRoom_ValidateSectionedHeader_Far__bad:
    sec
    rtl

; Validate route directory/row bounds, encoding modes, and expanded values
; before any lifecycle retirement. Route record bytes are in physical pending
; storage (not the v4 active-record alias).
ScummV5_LiveRoom_ValidateRouteDirectory_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp #$0006
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__minimum_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__minimum_ok:
    .a16
    cmp #SAME_SCUMM_LIVE_ROOM_PENDING_CAPACITY+1
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__length_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__length_ok:
    sta.l SCUMM_LIVE_ROOM_ROUTE_LENGTH
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE
    cmp #$01
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__version_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__version_ok:
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$01
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__box_count_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__box_count_ok:
    .a8
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0006
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; canonical directory size
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$02
    cmp.l SCUMM_LIVE_ROOM_COPY_INDEX
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__directory_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__directory_ok:
    lda.l SCUMM_LIVE_ROOM_ROUTE_LENGTH
    sec
    sbc.l SCUMM_LIVE_ROOM_COPY_INDEX
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__payload_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__payload_ok:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; payload length
    ; The first row offset is canonically zero.
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    clc
    adc #$0004
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__first_offset_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__first_offset_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    bne ScummV5_LiveRoom_ValidateRouteDirectory_Far__has_rows
    jml ScummV5_LiveRoom_ValidateRouteDirectory_Far__empty
ScummV5_LiveRoom_ValidateRouteDirectory_Far__has_rows:
    .a16
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; row
ScummV5_LiveRoom_ValidateRouteDirectory_Far__row:
    .a16
    ; Read adjacent row offsets from 4+box_count+2*row.
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    clc
    adc #$0004
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; relative start
    inx
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; relative end
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__offset_order_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__offset_order_ok:
    cmp.l SCUMM_LIVE_ROOM_TEMP5
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__offset_bound_ok
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__offset_bound_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__offset_bound_ok:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    inc
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bne ScummV5_LiveRoom_ValidateRouteDirectory_Far__not_last
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_TEMP5
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__last_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__last_ok:
ScummV5_LiveRoom_ValidateRouteDirectory_Far__not_last:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; absolute source start
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; absolute source end
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0004
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    cmp #$0000
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw
    cmp #$0001
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle
    cmp #$0002
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_dispatch
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_dispatch:
    jml ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse

ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP1
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_begin
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_begin:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP3
ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_loop:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_has_value
    jml ScummV5_LiveRoom_ValidateRouteDirectory_Far__row_done
ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_has_value:
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    cmp #$FF
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_value_ok
    rep #$20
    .a16
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_value_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_value_ok:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP3
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP3
    bra ScummV5_LiveRoom_ValidateRouteDirectory_Far__raw_loop

ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP1
    and #$0001
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_even
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_even:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; source cursor
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; expanded cells
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_loop:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_done
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    bne ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_count_nonzero
    jml ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_count_nonzero:
    .a8
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_nonmissing:
    ; $FF is the SCUMM no-route sentinel. Raw rows preserve it, so RLE rows
    ; must accept the same value instead of rejecting valid disconnected boxes.
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    and #$00FF
    cmp #$00FF
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_ok
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_value_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_sum_ok
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_sum_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_sum_ok:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP4
    lda.l SCUMM_LIVE_ROOM_TEMP3
    clc
    adc #$0002
    sta.l SCUMM_LIVE_ROOM_TEMP3
    bra ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_loop
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_done:
    lda.l SCUMM_LIVE_ROOM_TEMP4
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_row_complete
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__rle_row_complete:
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__row_done

ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP1
    and #$0001
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_even
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_even:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP3
    lda #$FFFF
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; previous destination
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_loop:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__row_done
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_destination_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_destination_ok:
    .a8
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    cmp #$FF
    bne ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_ok
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_ok:
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_in_range
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_value_in_range:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP4
    cmp #$FFFF
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_first_pair
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_TEMP4
    bcc ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad
    bra ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_first
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_first_pair:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_first:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP4
    lda.l SCUMM_LIVE_ROOM_TEMP3
    clc
    adc #$0002
    sta.l SCUMM_LIVE_ROOM_TEMP3
    bra ScummV5_LiveRoom_ValidateRouteDirectory_Far__sparse_loop

ScummV5_LiveRoom_ValidateRouteDirectory_Far__row_done:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    bcs ScummV5_LiveRoom_ValidateRouteDirectory_Far__all_rows_done
    jmp ScummV5_LiveRoom_ValidateRouteDirectory_Far__row
ScummV5_LiveRoom_ValidateRouteDirectory_Far__all_rows_done:
    clc
    rtl
ScummV5_LiveRoom_ValidateRouteDirectory_Far__empty:
    .a16
    lda.l SCUMM_LIVE_ROOM_ROUTE_LENGTH
    cmp #$0006
    beq ScummV5_LiveRoom_ValidateRouteDirectory_Far__all_rows_done
ScummV5_LiveRoom_ValidateRouteDirectory_Far__bad:
    sec
    rtl

; Expand already authenticated and structurally validated rows to SAME's
; existing 64-byte-stride route matrix. This runs after EXCD, before the new
; room is published to SCUMM consumers.
ScummV5_LiveRoom_ExpandRoutes_Far:
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_ROUTE_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; box count
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; row
ScummV5_LiveRoom_ExpandRoutes_Far__row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_ExpandRoutes_Far__row_active
    jml ScummV5_LiveRoom_ExpandRoutes_Far__done
ScummV5_LiveRoom_ExpandRoutes_Far__row_active:
    .a16
    ; X = 4 + box_count + 2*row; resolve relative input cursors.
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc #$0004
    tax
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP1
    inx
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP3
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$02
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; absolute input cursor
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE+$02
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP3
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; absolute input end
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; output row*64
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0004
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    cmp #$0000
    beq ScummV5_LiveRoom_ExpandRoutes_Far__raw
    cmp #$0001
    beq ScummV5_LiveRoom_ExpandRoutes_Far__rle
    cmp #$0002
    beq ScummV5_LiveRoom_ExpandRoutes_Far__sparse_dispatch
    jmp ScummV5_LiveRoom_ExpandRoutes_Far__bad
ScummV5_LiveRoom_ExpandRoutes_Far__sparse_dispatch:
    jml ScummV5_LiveRoom_ExpandRoutes_Far__sparse

ScummV5_LiveRoom_ExpandRoutes_Far__raw:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; input cursor
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; output column
ScummV5_LiveRoom_ExpandRoutes_Far__raw_loop:
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_ExpandRoutes_Far__raw_has_cell
    jml ScummV5_LiveRoom_ExpandRoutes_Far__next_row
ScummV5_LiveRoom_ExpandRoutes_Far__raw_has_cell:
    lda.l SCUMM_LIVE_ROOM_TEMP5
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP4
    clc
    adc.l SCUMM_LIVE_ROOM_COPY_INDEX
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_ROUTES,x
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP5
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP5
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    bra ScummV5_LiveRoom_ExpandRoutes_Far__raw_loop

ScummV5_LiveRoom_ExpandRoutes_Far__rle:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; input cursor
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; expanded output column
ScummV5_LiveRoom_ExpandRoutes_Far__rle_pair:
    lda.l SCUMM_LIVE_ROOM_TEMP5
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    bcc ScummV5_LiveRoom_ExpandRoutes_Far__rle_has_pair
    jml ScummV5_LiveRoom_ExpandRoutes_Far__next_row
ScummV5_LiveRoom_ExpandRoutes_Far__rle_has_pair:
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE ; run count
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; end output column for this run
ScummV5_LiveRoom_ExpandRoutes_Far__rle_cells:
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcs ScummV5_LiveRoom_ExpandRoutes_Far__rle_next_pair
    lda.l SCUMM_LIVE_ROOM_TEMP4
    clc
    adc.l SCUMM_LIVE_ROOM_COPY_INDEX
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_ROUTES,x
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    bra ScummV5_LiveRoom_ExpandRoutes_Far__rle_cells
ScummV5_LiveRoom_ExpandRoutes_Far__rle_next_pair:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP5
    clc
    adc #$0002
    sta.l SCUMM_LIVE_ROOM_TEMP5
    bra ScummV5_LiveRoom_ExpandRoutes_Far__rle_pair

ScummV5_LiveRoom_ExpandRoutes_Far__sparse:
    .a16
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
ScummV5_LiveRoom_ExpandRoutes_Far__sparse_fill:
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcs ScummV5_LiveRoom_ExpandRoutes_Far__sparse_pairs_start
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
    sep #$20
    .a8
    lda #$FF
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_ROUTES,x
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    bra ScummV5_LiveRoom_ExpandRoutes_Far__sparse_fill
ScummV5_LiveRoom_ExpandRoutes_Far__sparse_pairs_start:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; input cursor
ScummV5_LiveRoom_ExpandRoutes_Far__sparse_pairs:
    lda.l SCUMM_LIVE_ROOM_TEMP5
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    bcs ScummV5_LiveRoom_ExpandRoutes_Far__next_row
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE ; destination
    inx
    lda.l SAME_SCUMM_LIVE_ROOM_PENDING_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    sta.l SAME_SCUMM_MATRIX_DYNAMIC_ROUTES,x
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP5
    clc
    adc #$0002
    sta.l SCUMM_LIVE_ROOM_TEMP5
    bra ScummV5_LiveRoom_ExpandRoutes_Far__sparse_pairs

ScummV5_LiveRoom_ExpandRoutes_Far__next_row:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP0
    jmp ScummV5_LiveRoom_ExpandRoutes_Far__row
ScummV5_LiveRoom_ExpandRoutes_Far__done:
    clc
    rtl
ScummV5_LiveRoom_ExpandRoutes_Far__bad:
    sec
    rtl
.endif

; Validate SC5LIVE after the storage provider has authenticated its CRC.
; The compiler emits canonical, contiguous table offsets and the exact room
; record length; this guard repeats identity/schema/bounds checks before the
; record becomes the active source for existing SCUMM consumers.
ScummV5_LiveRoom_Validate_Far:
    .a8
    lda #$B0
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    sep #$20
    .a8
    ldx #$0000
ScummV5_LiveRoom_Validate_Far__magic:
    .a8
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    cmp.l ScummV5_LiveRoom_Magic,x
    beq ScummV5_LiveRoom_Validate_Far__magic_match
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__magic_match:
    .a8
    inx
    cpx #$0008
    bcc ScummV5_LiveRoom_Validate_Far__magic
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$08
    cmp #$0002
    beq ScummV5_LiveRoom_Validate_Far__version_ok
    cmp #$0003
    beq ScummV5_LiveRoom_Validate_Far__version_ok
    .if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #$0004
    beq ScummV5_LiveRoom_Validate_Far__version_ok
    .endif
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__version_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$0A
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    beq ScummV5_LiveRoom_Validate_Far__header_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__header_ok:
    .a16
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$0C
    cmp.l SAME_SCUMM_LIVE_ROOM_CONTROL+$0C
    beq ScummV5_LiveRoom_Validate_Far__room_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__room_ok:
    .a8
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$0D
    and #$FE
    beq ScummV5_LiveRoom_Validate_Far__flags_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__flags_ok:
    .a8
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$30
    cmp.l SCUMM_LIVE_ROOM_READ_LENGTH
    beq ScummV5_LiveRoom_Validate_Far__length_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__length_ok:
    .a16
    sep #$20
    .a8
    lda #$C1 ; identity/schema/length checks passed
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    rep #$20
    .a16
    ; The checkpoint write above leaves A=$00C1 after REP. Reload the
    ; validated u16 length before applying either allocation-bound check.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$30
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    bcs ScummV5_LiveRoom_Validate_Far__minimum_size_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__minimum_size_ok:
    .a16
    cmp #SCUMM_LIVE_ROOM_MAX_SIZE+1
    bcc ScummV5_LiveRoom_Validate_Far__maximum_size_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__maximum_size_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$1C
    cmp #SCUMM_LIVE_ROOM_HEADER_SIZE
    beq ScummV5_LiveRoom_Validate_Far__first_offset_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__first_offset_ok:
    .a16
    sep #$20
    .a8
    lda #$C2 ; section offsets and portal directory are being checked
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    rep #$20
    .a16
    ; SC5LIVE v3 uses a sorted fixed-width pair directory. v4 uses packed
    ; row-local pairs; both are validated against the object-section boundary.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$08
    cmp #$0003
    beq ScummV5_LiveRoom_Validate_Far__portal_v3_start
    .if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #$0004
    bne ScummV5_LiveRoom_Validate_Far__portal_v4_dispatch_done
    jml ScummV5_LiveRoom_Validate_Far__portal_v4_start
ScummV5_LiveRoom_Validate_Far__portal_v4_dispatch_done:
    .endif
    jmp ScummV5_LiveRoom_Validate_Far__portal_v3_done
ScummV5_LiveRoom_Validate_Far__portal_v3_start:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$22
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; portal section
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$24
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; object section
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    bcs ScummV5_LiveRoom_Validate_Far__portal_section_order_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_section_order_ok:
    .a16
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP0
    cmp #$0004
    bcs ScummV5_LiveRoom_Validate_Far__portal_header_available
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_header_available:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; edge count
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; unique descriptor count
    lda.l SCUMM_LIVE_ROOM_TEMP3
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_Validate_Far__portal_count_ok
    beq ScummV5_LiveRoom_Validate_Far__portal_count_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_count_ok:
    .a16
    ; edge_count cannot exceed box_count squared.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$0E
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_TEMP5
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP0
ScummV5_LiveRoom_Validate_Far__portal_box_square:
    lda.l SCUMM_LIVE_ROOM_TEMP5
    beq ScummV5_LiveRoom_Validate_Far__portal_pair_bound
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP5
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP5
    bra ScummV5_LiveRoom_Validate_Far__portal_box_square
ScummV5_LiveRoom_Validate_Far__portal_pair_bound:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$20
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    bcc ScummV5_LiveRoom_Validate_Far__portal_offset_no_overflow
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_offset_no_overflow:
    .a16
    cmp.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$22
    beq ScummV5_LiveRoom_Validate_Far__portal_offset_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_offset_ok:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    bcc ScummV5_LiveRoom_Validate_Far__portal_pairs_fit
    beq ScummV5_LiveRoom_Validate_Far__portal_pairs_fit
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_pairs_fit:
    .a16
    ; Prove edge_count*4 fits between the portal header and object section,
    ; then prove descriptors occupy the exact remaining bytes.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$22
    clc
    adc #$0004
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$24
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP0
    lsr
    lsr
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcs ScummV5_LiveRoom_Validate_Far__portal_rows_fit
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_rows_fit:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; pair-row byte count
    lda.l SCUMM_LIVE_ROOM_TEMP3
    asl
    asl
    asl
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP3 ; descriptor_count * 7
    sta.l SCUMM_LIVE_ROOM_TEMP5
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$22
    clc
    adc #$0004
    bcc ScummV5_LiveRoom_Validate_Far__portal_start_no_overflow
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_start_no_overflow:
    .a16
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    bcc ScummV5_LiveRoom_Validate_Far__portal_rows_no_overflow
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_rows_no_overflow:
    .a16
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP5
    bcc ScummV5_LiveRoom_Validate_Far__portal_descriptors_no_overflow
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_descriptors_no_overflow:
    .a16
    cmp.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$24
    bne ScummV5_LiveRoom_Validate_Far__portal_v3_not_done
    jml ScummV5_LiveRoom_Validate_Far__portal_v3_done
ScummV5_LiveRoom_Validate_Far__portal_v3_not_done:
    jmp ScummV5_LiveRoom_Validate_Far__bad
.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
ScummV5_LiveRoom_Validate_Far__portal_v4_start:
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$22
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; portal offset
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$24
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; object offset
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    bcs ScummV5_LiveRoom_Validate_Far__portal_v4_order
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_order:
    .a16
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP0
    cmp #$0007
    bcs ScummV5_LiveRoom_Validate_Far__portal_v4_header
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_header:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; edge count
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; descriptor count
    lda.l SCUMM_LIVE_ROOM_TEMP3
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_Validate_Far__portal_v4_counts
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_counts
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_counts:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$0E
    and #$00FF
    cmp #$0041
    bcc ScummV5_LiveRoom_Validate_Far__portal_v4_boxes
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_boxes:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; box count
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0004
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    cmp #$01
    bcs ScummV5_LiveRoom_Validate_Far__portal_pair_width_min_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_pair_width_min_ok:
    .a8
    cmp #$04
    bcc ScummV5_LiveRoom_Validate_Far__portal_pair_width_max_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_pair_width_max_ok:
    .a8
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; pair byte width
    inx
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    cmp #$01
    bcs ScummV5_LiveRoom_Validate_Far__destination_bits_min_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__destination_bits_min_ok:
    .a8
    cmp #$07
    bcc ScummV5_LiveRoom_Validate_Far__destination_bits_max_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__destination_bits_max_ok:
    .a8
    inx
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    cmp #$01
    bcs ScummV5_LiveRoom_Validate_Far__descriptor_bits_min_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__descriptor_bits_min_ok:
    .a8
    cmp #$11
    bcc ScummV5_LiveRoom_Validate_Far__descriptor_bits_max_ok
    jml ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__descriptor_bits_max_ok:
    .a8
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP4
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP4
    ; Compute the exact extent using bounded multiplication loops.
    lda.l SCUMM_LIVE_ROOM_TEMP5
    inc
    asl
    clc
    adc #$0007
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH ; cursor after row offsets
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_TEMP1
ScummV5_LiveRoom_Validate_Far__portal_v4_pair_extent:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_pairs_done
    lda.l SCUMM_LIVE_ROOM_READ_LENGTH
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_Validate_Far__portal_v4_pair_extent
ScummV5_LiveRoom_Validate_Far__portal_v4_pairs_done:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    sta.l SCUMM_LIVE_ROOM_TEMP1
ScummV5_LiveRoom_Validate_Far__portal_v4_descriptor_extent:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_extent_done
    lda.l SCUMM_LIVE_ROOM_READ_LENGTH
    clc
    adc #$0007
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_Validate_Far__portal_v4_descriptor_extent
ScummV5_LiveRoom_Validate_Far__portal_v4_extent_done:
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$24
    cmp.l SCUMM_LIVE_ROOM_READ_LENGTH
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_rows_start
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_rows_start:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0007
    tax
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_rows_first_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_rows_first_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; edge count for row endpoint checks
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; previous row offset
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; row number
ScummV5_LiveRoom_Validate_Far__portal_v4_rows:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    cmp.l SCUMM_LIVE_ROOM_TEMP5
    bcs ScummV5_LiveRoom_Validate_Far__portal_v4_rows_done
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    bcc ScummV5_LiveRoom_Validate_Far__portal_v4_bad_row
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    bcc ScummV5_LiveRoom_Validate_Far__portal_v4_row_ok
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_row_ok
ScummV5_LiveRoom_Validate_Far__portal_v4_bad_row:
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_row_ok:
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP1
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_Validate_Far__portal_v4_rows
ScummV5_LiveRoom_Validate_Far__portal_v4_rows_done:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_Validate_Far__portal_v4_done
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__portal_v4_done:
    jmp ScummV5_LiveRoom_Validate_Far__portal_v3_done
.endif
ScummV5_LiveRoom_Validate_Far__portal_v3_done:
    .a16
    sep #$20
    .a8
    lda #$C3 ; portal directory and movement metadata passed
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    rep #$20
    .a16
    ; SC5LIVE v2 stores one (u8 byte length, bytes) name row per object, in
    ; object-table order. Walk exactly object_count rows and require the table
    ; to end at object-walk. Package CRC authenticates bytes; these checks
    ; protect the native consumer offsets.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$26
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; names cursor
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$28
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; object-walk offset
    cmp.l SCUMM_LIVE_ROOM_TEMP0
    bcs ScummV5_LiveRoom_Validate_Far__names_order_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__names_order_ok:
    .a16
    cmp.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$30
    bcc ScummV5_LiveRoom_Validate_Far__names_bound_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__names_bound_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$10
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; name rows remaining
ScummV5_LiveRoom_Validate_Far__name_row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_Validate_Far__names_done
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0001
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcc ScummV5_LiveRoom_Validate_Far__name_length_available
    beq ScummV5_LiveRoom_Validate_Far__name_length_available
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__name_length_available:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    rep #$20
    .a16
    and #$00FF
    cmp #$0021
    bcc ScummV5_LiveRoom_Validate_Far__name_size_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__name_size_ok:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; name byte count
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0001
    adc.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcc ScummV5_LiveRoom_Validate_Far__name_within_table
    beq ScummV5_LiveRoom_Validate_Far__name_within_table
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__name_within_table:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    jmp ScummV5_LiveRoom_Validate_Far__name_row
ScummV5_LiveRoom_Validate_Far__names_done:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_Validate_Far__names_exact
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__names_exact:
    .a16
    sep #$20
    .a8
    lda #$C4 ; object-name rows passed
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    rep #$20
    .a16
    ; The final bundle table must terminate exactly at total_size. This also
    ; rejects malformed counts/offsets before any native consumer indexes it.
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$2E
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$16
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$3E ; diagnostic expected terminal offset
    cmp.l SCUMM_LIVE_ROOM_VALIDATION_BASE+$30
    beq ScummV5_LiveRoom_Validate_Far__bundle_extent_ok
    jmp ScummV5_LiveRoom_Validate_Far__bad
ScummV5_LiveRoom_Validate_Far__bundle_extent_ok:
    sep #$20
    .a8
    lda #$C5
    sta.l SCUMM_LIVE_ROOM_VALIDATE_CHECKPOINT
    sep #$20
    .a8
    lda #$B1
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$1E
    clc
    rtl
ScummV5_LiveRoom_Validate_Far__bad:
    sep #$20
    .a8
    rep #$10
    .i16
    ldx #$0000
ScummV5_LiveRoom_Validate_Far__capture_prefix:
    lda.l SCUMM_LIVE_ROOM_VALIDATION_BASE,x
    sta.l SAME_SCUMM_LIVE_ROOM_CONTROL+$34,x
    inx
    .a8
    cpx #$0008
    bcc ScummV5_LiveRoom_Validate_Far__capture_prefix
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

; Translate the compiler-owned compact OBNA table into SAME's existing object-name
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
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; current variable-length row
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; parallel object-table row index
ScummV5_LiveRoom_LoadNames_Far__row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP3
    bne ScummV5_LiveRoom_LoadNames_Far__has_row
    jmp ScummV5_LiveRoom_LoadNames_Far__done
ScummV5_LiveRoom_LoadNames_Far__has_row:
    .a16
    ; Name rows follow the existing object table exactly; recover the canonical
    ; object ID from that record rather than duplicating it in SC5LIVE.
    lda.l SCUMM_LIVE_ROOM_TEMP1
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP1
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    adc.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECTS_OFFSET
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
    tax
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    rep #$20
    .a16
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_WIDTH ; name length
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0001
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; source string offset
    ; Clear the previous room's tail so shorter names cannot expose stale bytes.
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
ScummV5_LiveRoom_LoadNames_Far__clear:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp #$0020
    bcs ScummV5_LiveRoom_LoadNames_Far__copy_start
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_OBJECT_NAMES,x
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    inc
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    bra ScummV5_LiveRoom_LoadNames_Far__clear
ScummV5_LiveRoom_LoadNames_Far__copy_start:
    .a16
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
ScummV5_LiveRoom_LoadNames_Far__char:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp.l SCUMM_LIVE_ROOM_WIDTH
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
    adc #$0001
    clc
    adc.l SCUMM_LIVE_ROOM_WIDTH
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP1
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
    bcc ScummV5_LiveRoom_NextBox_Far__source_valid
    jml ScummV5_LiveRoom_NextBox_Far__bad
ScummV5_LiveRoom_NextBox_Far__source_valid:
    lda.l SAME_SCUMM_MOVE_ROUTE_DEST
    cmp.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    bcc ScummV5_LiveRoom_NextBox_Far__destination_valid
    jml ScummV5_LiveRoom_NextBox_Far__bad
ScummV5_LiveRoom_NextBox_Far__destination_valid:
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE+$08
    cmp #$0004
    bne ScummV5_LiveRoom_NextBox_Far__legacy
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    and #$00FF
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SAME_SCUMM_MOVE_ROUTE_DEST
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_MATRIX_DYNAMIC_ROUTES,x
    cmp #$FF
    beq ScummV5_LiveRoom_NextBox_Far__bad
    sec
    rtl
ScummV5_LiveRoom_NextBox_Far__legacy:
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
    .a16
    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT
    and #$00FF ; ROUTE_NEXT is u8 and is adjacent to PORTAL_TYPE.
    sta.l SCUMM_LIVE_ROOM_TEMP5
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP5
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_BASE+$08
    cmp #$0003
    beq ScummV5_LiveRoom_Portal_Far__v3
    .if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
    cmp #$0004
    beq ScummV5_LiveRoom_Portal_Far__v4
    .endif
    ; Pair matrix stores a sparse portal-record index, FFFF means no portal.
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp #$FFFF
    beq ScummV5_LiveRoom_Portal_Far__v2_no_portal
    jmp ScummV5_LiveRoom_Portal_Far__has_portal
ScummV5_LiveRoom_Portal_Far__v2_no_portal:
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__v4:
    jsl ScummV5_LiveRoom_PortalV4_Far
    bcc ScummV5_LiveRoom_Portal_Far__v4_missing
    jml ScummV5_LiveRoom_Portal_Far__load_descriptor
ScummV5_LiveRoom_Portal_Far__v4_missing:
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__v3:
    .a16
    ; Binary search the sorted v3 pair directory by source*box_count+next.
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; high = edge_count
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; low
ScummV5_LiveRoom_Portal_Far__v3_search:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcc ScummV5_LiveRoom_Portal_Far__v3_search_step
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__v3_search_step:
    .a16
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    lsr
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; midpoint
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    clc
    adc #$0004
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; pair row offset
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SCUMM_LIVE_ROOM_TEMP2
    beq ScummV5_LiveRoom_Portal_Far__v3_found
    bcc ScummV5_LiveRoom_Portal_Far__v3_search_lower
    lda.l SCUMM_LIVE_ROOM_TEMP3
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_Portal_Far__v3_search
ScummV5_LiveRoom_Portal_Far__v3_search_lower:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP0
    bra ScummV5_LiveRoom_Portal_Far__v3_search
ScummV5_LiveRoom_Portal_Far__v3_found:
    .a16
    lda.l SCUMM_LIVE_ROOM_BASE,x
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; descriptor index
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; edge count
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SCUMM_LIVE_ROOM_TEMP3
    bcc ScummV5_LiveRoom_Portal_Far__v3_bad_descriptor_index
    bne ScummV5_LiveRoom_Portal_Far__v3_descriptor_index_ok
ScummV5_LiveRoom_Portal_Far__v3_bad_descriptor_index:
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__v3_descriptor_index_ok:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    clc
    adc #$0004
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP4
    lda.l SCUMM_LIVE_ROOM_TEMP3
    asl
    asl
    asl
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP3
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
    jmp ScummV5_LiveRoom_Portal_Far__load_descriptor
ScummV5_LiveRoom_Portal_Far__has_portal:
    .a16
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; sparse portal record index
    ; Portal records follow the u16 pair-index matrix (box_count squared).
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP2
ScummV5_LiveRoom_Portal_Far__square:
    lda.l SCUMM_LIVE_ROOM_TEMP0
    beq ScummV5_LiveRoom_Portal_Far__records
    lda.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP0
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP0
    bra ScummV5_LiveRoom_Portal_Far__square
ScummV5_LiveRoom_Portal_Far__records:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; sparse descriptor-array offset
    lda.l SCUMM_LIVE_ROOM_TEMP3
    asl
    asl
    asl
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP3 ; record index * 7
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    tax
ScummV5_LiveRoom_Portal_Far__load_descriptor:
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SAME_SCUMM_MOVE_PORTAL_TYPE
    cmp #$01
    beq ScummV5_LiveRoom_Portal_Far__descriptor_kind_ok
    cmp #$02
    bne ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_Portal_Far__descriptor_kind_ok:
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

; Superseded draft kept out of assembled images while the compact resolver
; below is the active v4 implementation.
.if 0
; Lookup one sparse row-local v4 portal pair. X returns the existing seven-byte
; descriptor in the active metadata record; the shared descriptor consumer is
; unchanged. The whole directory is structurally validated before publication.
ScummV5_LiveRoom_PortalV4_Far:
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; portal section offset
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH ; edge count
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_LENGTH ; descriptor count
    inx
    inx
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; pair byte width
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE ; destination bit width
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP4
    and #$00FF
    cmp #$0001
    beq ScummV5_LiveRoom_PortalV4_Far__pair_width_ok
    cmp #$0002
    beq ScummV5_LiveRoom_PortalV4_Far__pair_width_ok
    cmp #$0003
    beq ScummV5_LiveRoom_PortalV4_Far__pair_width_ok
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_PortalV4_Far__pair_width_ok:
    ; Pair-array base = portal + 7 + 2*(box_count+1).
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    asl
    clc
    adc #$0009
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_CHUNK_START
    ; Locate this source row's inclusive-start/exclusive-end pair indexes.
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    and #$00FF
    asl
    clc
    adc #$0007
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; row start index
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sec
    sbc.l SCUMM_LIVE_ROOM_TEMP5
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; pair count in row
    beq ScummV5_LiveRoom_PortalV4_Far__not_found
    ; Convert start pair index to byte cursor without a wide multiply.
    lda.l SCUMM_LIVE_ROOM_TEMP5
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; multiplication count
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; byte offset
ScummV5_LiveRoom_PortalV4_Far__cursor_multiply:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_PortalV4_Far__cursor_ready
    lda.l SCUMM_LIVE_ROOM_TEMP5
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_TEMP5
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_PortalV4_Far__cursor_multiply
ScummV5_LiveRoom_PortalV4_Far__cursor_ready:
    lda.l SCUMM_LIVE_ROOM_CHUNK_START
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP5
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; pair cursor
    ; Keep the row's requested destination in a different scratch word.
    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP5
ScummV5_LiveRoom_PortalV4_Far__pair:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    tax
    lda.l SCUMM_LIVE_ROOM_TEMP4
    and #$00FF
    cmp #$0001
    beq ScummV5_LiveRoom_PortalV4_Far__read_one
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; low 16 bits
    sep #$20
    .a8
    lda #$00
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP4
    and #$00FF
    cmp #$0002
    beq ScummV5_LiveRoom_PortalV4_Far__pair_read
    inx
    inx
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    bra ScummV5_LiveRoom_PortalV4_Far__pair_read
ScummV5_LiveRoom_PortalV4_Far__read_one:
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    rep #$20
    .a16
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda #$0000
    sep #$20
    .a8
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
ScummV5_LiveRoom_PortalV4_Far__pair_read:
    ; Extract destination using the declared low-bit width.
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; shift count
    lda #$0001
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
ScummV5_LiveRoom_PortalV4_Far__mask_loop:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    beq ScummV5_LiveRoom_PortalV4_Far__mask_ready
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    asl
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_PortalV4_Far__mask_loop
ScummV5_LiveRoom_PortalV4_Far__mask_ready:
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    dec
    and.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; destination
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_TEMP1
    bcc ScummV5_LiveRoom_Portal_Far__bad
    beq ScummV5_LiveRoom_Portal_Far__bad
    ; Shift the combined packed pair right by destination_bits.
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; shift count
ScummV5_LiveRoom_PortalV4_Far__unpack_loop:
    lda.l SCUMM_LIVE_ROOM_TEMP4
    beq ScummV5_LiveRoom_PortalV4_Far__unpack_done
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    lsr
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    ror
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP4
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP4
    bra ScummV5_LiveRoom_PortalV4_Far__unpack_loop
ScummV5_LiveRoom_PortalV4_Far__unpack_done:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_ROUTE_LENGTH
    bcc ScummV5_LiveRoom_PortalV4_Far__descriptor_ok
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_PortalV4_Far__descriptor_ok:
    lda.l SCUMM_LIVE_ROOM_TEMP1
    cmp.l SCUMM_LIVE_ROOM_TEMP5
    beq ScummV5_LiveRoom_PortalV4_Far__found
    ; Advance the source cursor and try the next pair in this row.
    lda.l SCUMM_LIVE_ROOM_TEMP1
    ; TEMP1 currently contains destination; recover cursor from a dedicated
    ; slot saved before unpacking (SCUMM_LIVE_ROOM_WIDTH).
    lda.l SCUMM_LIVE_ROOM_WIDTH
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_WIDTH
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_PortalV4_Far__not_found
    lda.l SCUMM_LIVE_ROOM_WIDTH
    sta.l SCUMM_LIVE_ROOM_TEMP1
    jmp ScummV5_LiveRoom_PortalV4_Far__pair
ScummV5_LiveRoom_PortalV4_Far__found:
    ; Descriptor table follows the packed pair array.
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; descriptor ID
    lda.l SCUMM_LIVE_ROOM_TEMP0
    clc
    adc #$0009
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    asl
    clc
    adc #$0009
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; pair-array base
    lda.l SCUMM_LIVE_ROOM_READ_LENGTH
    sta.l SCUMM_LIVE_ROOM_TEMP3
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; pair-array byte length
ScummV5_LiveRoom_PortalV4_Far__descriptor_extent:
    lda.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_PortalV4_Far__descriptor_base
    lda.l SCUMM_LIVE_ROOM_TEMP4
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4 ; overwritten below; do not use doubled value
    ; Multiply edge_count by pair_width with the bounded width (1..3).
    lda.l SCUMM_LIVE_ROOM_TEMP4
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP4
    sta.l SCUMM_LIVE_ROOM_TEMP4
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    bra ScummV5_LiveRoom_PortalV4_Far__descriptor_extent
ScummV5_LiveRoom_PortalV4_Far__descriptor_base:
    ; TODO: pair width/edge extent are reconstructed in the follow-up below.
    jmp ScummV5_LiveRoom_Portal_Far__bad
ScummV5_LiveRoom_PortalV4_Far__not_found:
    clc
    rtl
.endif

.if SCUMM_MSU1_LIVE_ROOM_RECORD_SIZE == $000D
; Resolve a packed, sorted v4 portal pair in its source row. Carry set returns
; X at the existing seven-byte descriptor; carry clear means no portal.
ScummV5_LiveRoom_PortalV4_Far:
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_PORTALS_OFFSET
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; portal offset
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_READ_LENGTH ; edge count
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_LENGTH ; descriptor count
    inx
    inx
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_CHUNK_COUNT ; pair width
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP_BYTE ; destination bit count
    rep #$20
    .a16
    ; Pair-array base = portal + 7 + 2*(box_count+1).
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    asl
    clc
    adc #$0009
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    sta.l SCUMM_LIVE_ROOM_CHUNK_START
    ; The row-offset table supplies pair indexes, not byte offsets.
    lda.l SAME_SCUMM_MOVE_ROUTE_SOURCE
    and #$00FF
    asl
    clc
    adc #$0007
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; first pair index
    inx
    inx
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sec
    sbc.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; pairs remaining
    bne ScummV5_LiveRoom_PortalV4_Far__has_pairs
    jml ScummV5_LiveRoom_PortalV4_Far__not_found
ScummV5_LiveRoom_PortalV4_Far__has_pairs:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; multiply counter
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; byte offset to first pair
ScummV5_LiveRoom_PortalV4_Far__cursor_offset:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP5
    beq ScummV5_LiveRoom_PortalV4_Far__cursor_ready
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_TEMP5
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP5
    bra ScummV5_LiveRoom_PortalV4_Far__cursor_offset
ScummV5_LiveRoom_PortalV4_Far__cursor_ready:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    clc
    adc.l SCUMM_LIVE_ROOM_CHUNK_START
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; current pair cursor
    lda.l SAME_SCUMM_MOVE_ROUTE_NEXT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP5 ; requested destination
ScummV5_LiveRoom_PortalV4_Far__scan:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    tax
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    cmp #$0001
    beq ScummV5_LiveRoom_PortalV4_Far__pair_one
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; low 16 bits
    sep #$20
    .a8
    lda #$00
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    cmp #$0002
    beq ScummV5_LiveRoom_PortalV4_Far__packed_pair_ready
    inx
    inx
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    bra ScummV5_LiveRoom_PortalV4_Far__packed_pair_ready
ScummV5_LiveRoom_PortalV4_Far__pair_one:
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_BASE,x
    rep #$20
    .a16
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda #$0000
    sep #$20
    .a8
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
ScummV5_LiveRoom_PortalV4_Far__packed_pair_ready:
    .a16
    ; Low destination bits form mask (1 << destination_bits) - 1.
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP4 ; shift count
    lda #$0001
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
ScummV5_LiveRoom_PortalV4_Far__mask:
    lda.l SCUMM_LIVE_ROOM_TEMP4
    beq ScummV5_LiveRoom_PortalV4_Far__mask_done
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    asl
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX
    lda.l SCUMM_LIVE_ROOM_TEMP4
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP4
    bra ScummV5_LiveRoom_PortalV4_Far__mask
ScummV5_LiveRoom_PortalV4_Far__mask_done:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    dec
    and.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; destination
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_BOX_COUNT
    and #$00FF
    cmp.l SCUMM_LIVE_ROOM_COPY_INDEX
    bcs ScummV5_LiveRoom_PortalV4_Far__destination_may_fit
    jml ScummV5_LiveRoom_PortalV4_Far__not_found
ScummV5_LiveRoom_PortalV4_Far__destination_may_fit:
    bne ScummV5_LiveRoom_PortalV4_Far__destination_valid
    jml ScummV5_LiveRoom_PortalV4_Far__not_found
ScummV5_LiveRoom_PortalV4_Far__destination_valid:
    .a16
    ; Decode descriptor_id = packed_pair >> destination_bits.
    lda.l SCUMM_LIVE_ROOM_TEMP_BYTE
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP4
ScummV5_LiveRoom_PortalV4_Far__unpack:
    lda.l SCUMM_LIVE_ROOM_TEMP4
    beq ScummV5_LiveRoom_PortalV4_Far__unpack_done
    sep #$20
    .a8
    lda.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    lsr
    sta.l SCUMM_LIVE_ROOM_ROUTE_VALUE
    rep #$20
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP2
    ror
    sta.l SCUMM_LIVE_ROOM_TEMP2
    lda.l SCUMM_LIVE_ROOM_TEMP4
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP4
    bra ScummV5_LiveRoom_PortalV4_Far__unpack
ScummV5_LiveRoom_PortalV4_Far__unpack_done:
    lda.l SCUMM_LIVE_ROOM_TEMP2
    cmp.l SCUMM_LIVE_ROOM_ROUTE_LENGTH
    bcc ScummV5_LiveRoom_PortalV4_Far__descriptor_valid
    jmp ScummV5_LiveRoom_PortalV4_Far__not_found
ScummV5_LiveRoom_PortalV4_Far__descriptor_valid:
    .a16
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    cmp.l SCUMM_LIVE_ROOM_TEMP5
    beq ScummV5_LiveRoom_PortalV4_Far__found
    ; Advance cursor by pair width and scan the next record in this row.
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_PortalV4_Far__not_found
    jmp ScummV5_LiveRoom_PortalV4_Far__scan
ScummV5_LiveRoom_PortalV4_Far__found:
    .a16
    ; Descriptor array starts after all packed pairs. Re-read edge count and
    ; compute its byte extent using the validated one-to-three-byte width.
    lda.l SCUMM_LIVE_ROOM_TEMP2
    sta.l SCUMM_LIVE_ROOM_COPY_INDEX ; descriptor ID
    lda.l SCUMM_LIVE_ROOM_TEMP0
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    sta.l SCUMM_LIVE_ROOM_TEMP3 ; edges remaining
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; pair bytes
ScummV5_LiveRoom_PortalV4_Far__edge_extent:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP3
    beq ScummV5_LiveRoom_PortalV4_Far__descriptor_table
    lda.l SCUMM_LIVE_ROOM_CHUNK_COUNT
    and #$00FF
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda.l SCUMM_LIVE_ROOM_TEMP3
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP3
    bra ScummV5_LiveRoom_PortalV4_Far__edge_extent
ScummV5_LiveRoom_PortalV4_Far__descriptor_table:
    lda.l SCUMM_LIVE_ROOM_CHUNK_START
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    sta.l SCUMM_LIVE_ROOM_TEMP1 ; descriptor table base
    lda.l SCUMM_LIVE_ROOM_COPY_INDEX
    asl
    asl
    asl
    sec
    sbc.l SCUMM_LIVE_ROOM_COPY_INDEX ; descriptor id * 7
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP1
    tax
    sec
    rtl
ScummV5_LiveRoom_PortalV4_Far__not_found:
    clc
    rtl
.endif

ScummV5_LiveRoom_ObjectWalk_Far:
    rep #$30
    .a16
    .i16
    lda.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_COUNT
    and #$00FF
    sta.l SCUMM_LIVE_ROOM_TEMP1
    lda #$0000
    sta.l SCUMM_LIVE_ROOM_TEMP0 ; parallel object row index
ScummV5_LiveRoom_ObjectWalk_Far__loop:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP1
    bne ScummV5_LiveRoom_ObjectWalk_Far__has_row
    jmp ScummV5_LiveRoom_ObjectWalk_Far__bad
ScummV5_LiveRoom_ObjectWalk_Far__has_row:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; object index * 2
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    adc.l SCUMM_LIVE_ROOM_TEMP0 ; object index * 11
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECTS_OFFSET
    tax
    lda.l SCUMM_LIVE_ROOM_BASE,x
    cmp.l SAME_SCUMM_MOVE_OBJECT
    beq ScummV5_LiveRoom_ObjectWalk_Far__found
    lda.l SCUMM_LIVE_ROOM_TEMP0
    inc
    sta.l SCUMM_LIVE_ROOM_TEMP0
    lda.l SCUMM_LIVE_ROOM_TEMP1
    dec
    sta.l SCUMM_LIVE_ROOM_TEMP1
    bra ScummV5_LiveRoom_ObjectWalk_Far__loop
ScummV5_LiveRoom_ObjectWalk_Far__found:
    .a16
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    sta.l SCUMM_LIVE_ROOM_TEMP2 ; object index * 2
    lda.l SCUMM_LIVE_ROOM_TEMP0
    asl
    asl
    asl
    clc
    adc.l SCUMM_LIVE_ROOM_TEMP2
    clc
    adc.l SCUMM_LIVE_ROOM_BASE+SCUMM_LIVE_ROOM_OBJECT_WALK_OFFSET
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
