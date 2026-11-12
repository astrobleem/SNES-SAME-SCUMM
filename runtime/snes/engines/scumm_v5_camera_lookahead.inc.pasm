; One checked strip of camera lookahead. Pixel storage is the existing shared
; pending prefix, borrowed only AFTER composition has copied the current strip
; into the locked INDEX8 surface at an aligned origin. The facade rejects
; partial edges whose conversion still needs the prefix.
; No speculative display writes: BeginScroll still proves the
; destination is unreferenced before the next real publication uses it.
; The immutable ticket is 24 audited bytes at $7E2EE8..$7E2EFF.

ScummV5_Camera_AheadReconcile_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CAMERA_AHEAD_STATE
    cmp #$01
    beq ScummV5_Camera_AheadReconcile__reading
    clc
    rtl
ScummV5_Camera_AheadReconcile__reading:
    .a8
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READING
    bne ScummV5_Camera_AheadReconcile__complete
    clc
    rtl
ScummV5_Camera_AheadReconcile__complete:
    .a8
    cmp #SAME_MSU1_STATE_READ_OK
    bne ScummV5_Camera_AheadReconcile__failed
    rep #$30
    .a16
    .i16
    lda.l SAME_MSU1_REQUEST_OFFSET
    cmp.l SAME_SCUMM_CAMERA_AHEAD_OFFSET
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    cmp.l SAME_SCUMM_CAMERA_AHEAD_OFFSET+2
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_REQUEST_LENGTH
    cmp.l SAME_SCUMM_CAMERA_AHEAD_LENGTH
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_REQUEST_LENGTH+2
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_EXPECTED_CRC
    cmp.l SAME_SCUMM_CAMERA_AHEAD_CRC
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_EXPECTED_CRC+2
    cmp.l SAME_SCUMM_CAMERA_AHEAD_CRC+2
    bne ScummV5_Camera_AheadReconcile__failed
    lda.l SAME_MSU1_DESTINATION
    cmp #SAME_SCUMM_LIVE_ROOM_PENDING_BASE&$FFFF
    bne ScummV5_Camera_AheadReconcile__failed
    sep #$20
    .a8
    lda.l SAME_MSU1_DESTINATION+2
    cmp #$40
    bne ScummV5_Camera_AheadReconcile__failed
    lda #$02
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE ; publish only after complete CRC acceptance
    clc
    rtl
ScummV5_Camera_AheadReconcile__failed:
    .a8
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE
    jml ScummV5_Camera_Invalid_Far

; A foreground actor may discard READY data. Never release a destination
; while its accepted checked transfer can still write into it.
ScummV5_Camera_AheadRelease_Far:
    php
    sep #$20
    .a8
    lda.l SAME_SCUMM_CAMERA_AHEAD_STATE
    cmp #$02
    bne ScummV5_Camera_AheadRelease__done
    lda #$00
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE
    lda.l SAME_SCUMM_VIEWPORT_STATE
    bne ScummV5_Camera_AheadRelease__done
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ROOM
    bne ScummV5_Camera_AheadRelease__done
    lda #$00
    sta.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    sta.l SAME_SCUMM_VIEWPORT_MODE
ScummV5_Camera_AheadRelease__done:
    plp
    rtl

; C clear is a hit. A stale direction/room/epoch is a miss, never a publication.
; Normal Prepare has already checked the next physical slot and bounds.
ScummV5_Camera_AheadConsume_Far:
    sep #$20
    .a8
    lda.l SAME_SCUMM_CAMERA_AHEAD_STATE
    cmp #$02
    beq ScummV5_Camera_AheadConsume__ready
    sec
    rtl
ScummV5_Camera_AheadConsume__ready:
    .a8
    lda.l SAME_SCUMM_CAMERA_AHEAD_ROOM
    cmp.l SAME_VIDEO_SURFACE_ROOM
    bne ScummV5_Camera_AheadConsume__miss
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_AHEAD_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    bne ScummV5_Camera_AheadConsume__miss
    lda.l SAME_SCUMM_CAMERA_AHEAD_COLUMN
    cmp.l SAME_SCUMM_VIEWPORT_STRIP
    bne ScummV5_Camera_AheadConsume__miss
    lda.l SAME_SCUMM_CAMERA_AHEAD_LENGTH
    cmp.l SAME_SCUMM_VIEWPORT_STRIP_BYTES
    bne ScummV5_Camera_AheadConsume__miss
    lda.l SAME_SCUMM_CAMERA_AHEAD_GENERATION+2
    tay
    lda.l SAME_SCUMM_CAMERA_AHEAD_GENERATION
    tax
    lda.l SAME_SCUMM_CAMERA_AHEAD_ORIGIN
    jsl Same_VideoSurface_LookaheadMatches_Far
    bcs ScummV5_Camera_AheadConsume__miss
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE
    lda #SCUMM_MSU_ROOM_VALIDATED
    sta.l SAME_SCUMM_MSU_ROOM_STATE
    rep #$20
    .a16
    lda.l SAME_SCUMM_CAMERA_AHEAD_HITS
    inc
    sta.l SAME_SCUMM_CAMERA_AHEAD_HITS
    ; Provider fields may now describe another completed client. The immutable
    ; accepted ticket above, not that mutable descriptor, supplies the length.
    jsl ScummV5_Camera_ConsumeStrip__length_ok
    bcc ScummV5_Camera_AheadConsume__installed
    ; A checked ticket hit with invalid installation geometry is a failure,
    ; not a cache miss that may silently issue another read.
    jml ScummV5_Camera_Invalid_Far
ScummV5_Camera_AheadConsume__installed:
    clc
    rtl
ScummV5_Camera_AheadConsume__miss:
    .a8
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE
    sec
    rtl

; Late visual phase only. One speculative request at most, no synchronous
; transfer, no scheduler wait, and no queueing ahead of a required client.
ScummV5_Camera_AheadService_Far:
    php
    jsl ScummV5_Camera_AheadReconcile_Far
    bcc ScummV5_Camera_AheadService__check
    plp
    rtl
ScummV5_Camera_AheadService__check:
    .a8
    lda.l SAME_SCUMM_CAMERA_AHEAD_STATE
    ora.l SAME_SCUMM_M23A_PHASE
    beq ScummV5_Camera_AheadService__idle
    jmp ScummV5_Camera_AheadService__done
ScummV5_Camera_AheadService__idle:
    .a8
    lda.l SAME_SCUMM_VIEWPORT_STATE
    cmp #$04
    beq ScummV5_Camera_AheadService__publication
    jmp ScummV5_Camera_AheadService__done
ScummV5_Camera_AheadService__publication:
    .a8
    ; The surface service owns conversion lifetime and off-screen geometry.
    jsl Same_VideoSurface_PlanLookahead_Far
    bcc ScummV5_Camera_AheadService__missing
    jmp ScummV5_Camera_AheadService__done
ScummV5_Camera_AheadService__missing:
    .a16
    sta.l SAME_SCUMM_CAMERA_AHEAD_COLUMN
    txa
    sta.l SAME_SCUMM_CAMERA_AHEAD_ORIGIN
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_SCRATCH_OWNER
    cmp #SAME_SCUMM_ACTOR_SCRATCH_OWNER_ROOM
    bne ScummV5_Camera_AheadService__done
    lda.l SAME_SCUMM_ACTOR_POSE_STATE
    bne ScummV5_Camera_AheadService__done
    lda.l SAME_SCUMM_MSU_CACHE_REQUEST_SLOT
    cmp #$FF
    bne ScummV5_Camera_AheadService__done
    lda.l SAME_SCUMM_MSU_ROOM_STATE
    cmp #SCUMM_MSU_ROOM_VALIDATED
    bne ScummV5_Camera_AheadService__done
    lda.l SAME_MSU1_STATUS
    cmp #SAME_MSU1_STATE_READY
    beq ScummV5_Camera_AheadService__admit
    cmp #SAME_MSU1_STATE_READ_OK
    bne ScummV5_Camera_AheadService__done
ScummV5_Camera_AheadService__admit:
    .a8
    jsl ScummV5_Camera_AheadBegin_Far
ScummV5_Camera_AheadService__done:
    plp
    rtl

ScummV5_Camera_AheadBegin_Far:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_VIEWPORT_STRIP
    pha
    lda.l SAME_SCUMM_CAMERA_AHEAD_COLUMN
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    jsl ScummV5_Camera_BuildStripRequest_Far
    rep #$20
    .a16
    pla
    sta.l SAME_SCUMM_VIEWPORT_STRIP
    bcs ScummV5_Camera_AheadBegin__failed
    lda.l SAME_MSU1_REQUEST_LENGTH
    sta.l SAME_SCUMM_CAMERA_AHEAD_LENGTH
    lda.l SAME_MSU1_REQUEST_OFFSET
    sta.l SAME_SCUMM_CAMERA_AHEAD_OFFSET
    lda.l SAME_MSU1_REQUEST_OFFSET+2
    sta.l SAME_SCUMM_CAMERA_AHEAD_OFFSET+2
    lda.l SAME_MSU1_EXPECTED_CRC
    sta.l SAME_SCUMM_CAMERA_AHEAD_CRC
    lda.l SAME_MSU1_EXPECTED_CRC+2
    sta.l SAME_SCUMM_CAMERA_AHEAD_CRC+2
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_CAMERA_AHEAD_EPOCH
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_SCUMM_CAMERA_AHEAD_GENERATION
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION+2
    sta.l SAME_SCUMM_CAMERA_AHEAD_GENERATION+2
    sep #$20
    .a8
    lda.l SAME_VIDEO_SURFACE_ROOM
    sta.l SAME_SCUMM_CAMERA_AHEAD_ROOM
    lda #$00
    sta.l SAME_MSU1_FLAGS
    jsl Same_Msu1_ReadBegin_FarEntry
    bcs ScummV5_Camera_AheadBegin__failed
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CAMERA_AHEAD_STATE
    clc
    rtl
ScummV5_Camera_AheadBegin__failed:
    .a8
    jml ScummV5_Camera_Invalid_Far
