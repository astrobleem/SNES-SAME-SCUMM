; Complete scene transaction over the existing source-cel compositor.
; Metadata lives in carrier-audited S-CPU storage. One checked actor buffer,
; one room underlay journal, one INDEX8 surface and one final PRESENT.
.bank 85
.org $8000
ScummV5_Scene_Tick_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_M23A_PHASE
    and #$00FF
    cmp #$0004
    bcc ScummV5_Scene_Tick__lifecycle_ready
    jml ScummV5_Scene_Tick__done
ScummV5_Scene_Tick__lifecycle_ready:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_PHASE
    beq ScummV5_Scene_Tick__idle
    jml ScummV5_Scene_Tick__done
ScummV5_Scene_Tick__idle:
    .a16
    .i16
    lda.l SAME_SCUMM_C14_INITIALIZED
    and #$00FF
    bne ScummV5_Scene_Tick__initialized
    jsl ScummV5_Controller_PublishActorVisualSingle_Far
    jml ScummV5_Scene_Tick__done
ScummV5_Scene_Tick__initialized:
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_ROOM_READY
    and #$00FF
    bne ScummV5_Scene_Tick__room
    jml ScummV5_Scene_Tick__done
ScummV5_Scene_Tick__room:
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Scene_Tick__ready
    jml ScummV5_Scene_Tick__done
ScummV5_Scene_Tick__ready:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_SCENE_ACTOR
ScummV5_Scene_Tick__actor:
    .a16
    .i16
    jsl ScummV5_Scene_LoadAnimation_Far
    jsl ScummV5_Controller_PublishActorVisualSingle_Far
    jsl ScummV5_Scene_SaveAnimation_Far
    jsl ScummV5_Scene_Snapshot_Far
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ACTOR
    inc
    sta.l SAME_SCUMM_SCENE_ACTOR
    cmp #$0020
    bcc ScummV5_Scene_Tick__actor
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_SCUMM_SCENE_ROOM_EPOCH
    bne ScummV5_Scene_Tick__changed
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    cmp.l SAME_SCUMM_SCENE_SOURCE_X
    bne ScummV5_Scene_Tick__changed
    lda.l SAME_VIDEO_SURFACE_SOURCE_Y
    cmp.l SAME_SCUMM_SCENE_SOURCE_Y
    bne ScummV5_Scene_Tick__changed
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    cmp.l SAME_SCUMM_SCENE_PALETTE_EPOCH
    bne ScummV5_Scene_Tick__changed
    lda.l SAME_SCUMM_SCENE_INITIALIZED
    bne ScummV5_Scene_Tick__restore_primary
ScummV5_Scene_Tick__changed:
    .a16
    .i16
    lda #$0001
    sta.l SAME_SCUMM_SCENE_DIRTY
ScummV5_Scene_Tick__restore_primary:
    .a16
    .i16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    sta.l SAME_SCUMM_SCENE_ACTOR
    jsl ScummV5_Scene_LoadSnapshot_Far
ScummV5_Scene_Tick__done:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

ScummV5_Scene_LoadAnimation_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    tax

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$00,x
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_FRAME

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$01,x
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_DIRECTION

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$02,x
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_COSTUME

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$03,x
    sta.l SAME_SCUMM_ACTOR_POSE_OBSERVED

    rep #$20
    .a16

    lda.l SAME_SCUMM_SCENE_ANIMATION+$04,x
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_X

    rep #$20
    .a16

    lda.l SAME_SCUMM_SCENE_ANIMATION+$06,x
    sta.l SAME_SCUMM_ACTOR_POSE_LAST_Y

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$08,x
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$09,x
    sta.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$0A,x
    sta.l SAME_SCUMM_ACTOR_POSE_LOOP_START

    sep #$20
    .a8

    lda.l SAME_SCUMM_SCENE_ANIMATION+$0B,x
    sta.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH

    rep #$20
    .a16

    lda.l SAME_SCUMM_SCENE_ANIMATION+$0C,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID

    rep #$20
    .a16

    lda.l SAME_SCUMM_SCENE_ANIMATION+$0E,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID+2

    rep #$20
    .a16
    txa
    asl
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$09,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    rep #$20
    .a16
    ; Sampling an actor must not mutate the last published primary pose.
    ; RENDER_X/Y belong exclusively to the completed scene publication.
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_SCENE_ACTOR_BASE
    lda.l SAME_SCUMM_SCENE_ACTOR
    and #$0007
    tax
    lda.l ScummV5_C7_BitMasks,x
    and #$00FF
    sta.l SAME_SCUMM_SCENE_TEMP
    lda.l SAME_SCUMM_SCENE_ACTOR
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_ACTOR_EXPLICIT_ANIMATION,x
    and.l SAME_SCUMM_SCENE_TEMP
    sta.l SAME_SCUMM_SCENE_EXPLICIT

    plp
    rtl

ScummV5_Scene_SaveAnimation_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    tax

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_LAST_FRAME
    sta.l SAME_SCUMM_SCENE_ANIMATION+$00,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_LAST_DIRECTION
    sta.l SAME_SCUMM_SCENE_ANIMATION+$01,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_LAST_COSTUME
    sta.l SAME_SCUMM_SCENE_ANIMATION+$02,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_OBSERVED
    sta.l SAME_SCUMM_SCENE_ANIMATION+$03,x

    rep #$20
    .a16

    lda.l SAME_SCUMM_ACTOR_POSE_LAST_X
    sta.l SAME_SCUMM_SCENE_ANIMATION+$04,x

    rep #$20
    .a16

    lda.l SAME_SCUMM_ACTOR_POSE_LAST_Y
    sta.l SAME_SCUMM_SCENE_ANIMATION+$06,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_SCENE_ANIMATION+$08,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_ANIM_COUNTER
    sta.l SAME_SCUMM_SCENE_ANIMATION+$09,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0A,x

    sep #$20
    .a8

    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_LENGTH
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0B,x

    rep #$20
    .a16

    lda.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0C,x

    rep #$20
    .a16

    lda.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID+2
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0E,x

    plp
    rtl

ScummV5_Scene_Snapshot_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    ldx #$0000
    lda #$0000
ScummV5_Scene_Snapshot__clear:
    .a16
    .i16
    sta.l SAME_SCUMM_SCENE_ROW,x
    inx
    inx
    cpx #$0020
    bcc ScummV5_Scene_Snapshot__clear

    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_SCENE_ROW+$00

    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_SCENE_ROW+$02

    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    sta.l SAME_SCUMM_SCENE_ROW+$04

    rep #$20
    .a16
    lda.l SAME_SCUMM_CEL_DESIRED_SCALE
    sta.l SAME_SCUMM_SCENE_ROW+$06

    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_SCENE_ROW+$08

    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    sta.l SAME_SCUMM_SCENE_ROW+$09

    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_SCENE_ROW+$0A

    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION
    sta.l SAME_SCUMM_SCENE_ROW+$0B

    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_SCENE_ROW+$0C

    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_SCENE_ROW+$0D

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_ACTOR_BASE
    tax
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ELEVATION,x
    sta.l SAME_SCUMM_SCENE_ROW+$0E
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_SCENE_ROW+$10
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_FORCE_CLIP,x
    sta.l SAME_SCUMM_SCENE_ROW+$12
    lda.l SAME_SCUMM_SCENE_ACTOR
    tax
    lda.l SAME_SCUMM_PUT_ACTOR_WALKBOX,x
    and #$00FF
    sta.l SAME_SCUMM_SCENE_ROW+$14
    jsl ScummV5_Scene_SnapshotMaskPolicy_Far
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ROW+$08
    and #$00FF
    bne ScummV5_Scene_Snapshot__costume
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_SCENE_ROW+$09
ScummV5_Scene_Snapshot__costume:
    .a16
    .i16
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    asl
    sta.l SAME_SCUMM_SCENE_TEMP
    ldy #$0000
ScummV5_Scene_Snapshot__compare:
    .a16
    .i16
    tyx
    lda.l SAME_SCUMM_SCENE_ROW,x
    pha
    tya
    clc
    adc.l SAME_SCUMM_SCENE_TEMP
    tax
    pla
    cmp.l SAME_SCUMM_SCENE_SNAPSHOTS,x
    beq ScummV5_Scene_Snapshot__same
    sta.l SAME_SCUMM_SCENE_SNAPSHOTS,x
    lda #$0001
    sta.l SAME_SCUMM_SCENE_DIRTY
ScummV5_Scene_Snapshot__same:
    .a16
    .i16
    iny
    iny
    cpy #$0018
    bcc ScummV5_Scene_Snapshot__compare
    plp
    rtl
; Mask policy is part of the immutable scene key, not sampled midway
; through a checked pose. Class changes therefore dirty the complete scene.
ScummV5_Scene_SnapshotMaskPolicy_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    phx
    lda.l SAME_SCUMM_SCENE_ROW+$09
    and #$00FF
    beq ScummV5_Scene_MaskPolicy__done
    ldx #$0000
ScummV5_Scene_MaskPolicy__class:
    .a16
    .i16
    lda.l SAME_SCUMM_C16_RECORDS,x
    and #$00FF
    beq ScummV5_Scene_MaskPolicy__next
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_OBJECT,x
    cmp.l SAME_SCUMM_SCENE_ACTOR
    bne ScummV5_Scene_MaskPolicy__next
    lda.l SAME_SCUMM_C16_RECORDS+SAME_SCUMM_C16_R_MASK+2,x
    and #$0008
    sta.l SAME_SCUMM_SCENE_ROW+$16
    bra ScummV5_Scene_MaskPolicy__box
ScummV5_Scene_MaskPolicy__next:
    .a16
    .i16
    txa
    clc
    adc #SAME_SCUMM_C16_RECORD_STRIDE
    tax
    cpx #(SAME_SCUMM_C16_RECORD_COUNT*SAME_SCUMM_C16_RECORD_STRIDE)
    bcc ScummV5_Scene_MaskPolicy__class
ScummV5_Scene_MaskPolicy__box:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ROW+$12
    ora.l SAME_SCUMM_SCENE_ROW+$16
    bne ScummV5_Scene_MaskPolicy__done
    ; Reuse the installed room's existing reverse-order box query. A zero
    ; adjustment distance means containment, rather than a nearest-box guess.
    lda.l SAME_SCUMM_SCENE_ROW+$00
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_X
    lda.l SAME_SCUMM_SCENE_ROW+$02
    sec
    sbc.l SAME_SCUMM_SCENE_ROW+$0E
    sta.l SAME_SCUMM_PUT_ACTOR_REQUEST_Y
    jsl ScummV5_PutActor_Adjust_Far
    rep #$30
    .a16
    .i16
    lda #$00FF
    sta.l SAME_SCUMM_SCENE_ROW+$14
    lda.l SAME_SCUMM_PUT_ACTOR_BEST_DISTANCE
    bne ScummV5_Scene_MaskPolicy__done
    lda.l SAME_SCUMM_PUT_ACTOR_RESULT_BOX
    and #$00FF
    sta.l SAME_SCUMM_SCENE_ROW+$14
ScummV5_Scene_MaskPolicy__done:
    .a16
    .i16
    plx
    plp
    rtl

ScummV5_Scene_LoadSnapshot_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    asl
    tax
    asl
    sta.l SAME_SCUMM_SCENE_ACTOR_BASE

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$00,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_X

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$02,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_Y

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$04,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_FACING

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$06,x
    sta.l SAME_SCUMM_CEL_DESIRED_SCALE

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$08,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$09,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$0A,x
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$0B,x
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_DIRECTION

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$0C,x
    sta.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP

    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$0D,x
    sta.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT

    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$0E,x
    sta.l SAME_SCUMM_SCENE_ELEVATION
    txa
    lsr
    tax
    lda.l SAME_SCUMM_SCENE_ANIMATION+$0C,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID
    lda.l SAME_SCUMM_SCENE_ANIMATION+$0E,x
    sta.l SAME_SCUMM_ACTOR_PALETTE_OVERRIDE_VALID+2
    plp
    rtl

; Choose authoritative source Y order; ascending actor scan resolves ties.
ScummV5_Scene_Next_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    lda #$FFFF
    sta.l SAME_SCUMM_SCENE_BEST
    sta.l SAME_SCUMM_SCENE_BEST_Y
    lda #$0000
    sta.l SAME_SCUMM_SCENE_SCAN
ScummV5_Scene_Next__scan:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_SCAN
    and #$0007
    tax
    lda.l ScummV5_C7_BitMasks,x
    and #$00FF
    sta.l SAME_SCUMM_SCENE_TEMP
    lda.l SAME_SCUMM_SCENE_SCAN
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_SCENE_VISITED,x
    and.l SAME_SCUMM_SCENE_TEMP
    bne ScummV5_Scene_Next__skip
    lda.l SAME_SCUMM_SCENE_SCAN
    asl
    asl
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$09,x
    and #$00FF
    beq ScummV5_Scene_Next__skip
    lda.l SAME_SCUMM_SCENE_BEST
    cmp #$FFFF
    beq ScummV5_Scene_Next__first
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$02,x
    eor #$8000
    cmp.l SAME_SCUMM_SCENE_BEST_Y
    bcs ScummV5_Scene_Next__skip
    bra ScummV5_Scene_Next__choose
ScummV5_Scene_Next__first:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_SNAPSHOTS+$02,x
    eor #$8000
ScummV5_Scene_Next__choose:
    .a16
    .i16
    sta.l SAME_SCUMM_SCENE_BEST_Y
    lda.l SAME_SCUMM_SCENE_SCAN
    sta.l SAME_SCUMM_SCENE_BEST
ScummV5_Scene_Next__skip:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_SCAN
    inc
    sta.l SAME_SCUMM_SCENE_SCAN
    cmp #$0020
    bcc ScummV5_Scene_Next__scan
    lda.l SAME_SCUMM_SCENE_BEST
    cmp #$FFFF
    beq ScummV5_Scene_Next__empty
    sta.l SAME_SCUMM_SCENE_ACTOR
    jsl ScummV5_Scene_LoadSnapshot_Far
    lda #$0000
    sta.l SAME_SCUMM_SCENE_STARTED
    sta.l SAME_SCUMM_SCENE_ACTOR_DONE
    sta.l SAME_SCUMM_MASK_STATE
    sta.l SAME_SCUMM_MASK_PLANE
    sta.l SAME_SCUMM_CEL_CHUNK
    lda.l SAME_SCUMM_SCENE_PHASE
    cmp #$0001
    bne ScummV5_Scene_Next__bounds_ready
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    asl
    tax
    lda #$FFFF
    sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$18,x
    sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1A,x
    lda #$0000
    sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1C,x
    sta.l SAME_SCUMM_SCENE_SNAPSHOTS+$1E,x
ScummV5_Scene_Next__bounds_ready:
    .a16
    .i16
    lda #$0000
    sep #$20
    .a8
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    plp
    sec
    rtl
ScummV5_Scene_Next__empty:
    .a16
    .i16
    plp
    clc
    rtl

ScummV5_Scene_Mark_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_ACTOR
    and #$0007
    tax
    lda.l ScummV5_C7_BitMasks,x
    and #$00FF
    sta.l SAME_SCUMM_SCENE_TEMP
    lda.l SAME_SCUMM_SCENE_ACTOR
    lsr
    lsr
    lsr
    tax
    lda.l SAME_SCUMM_SCENE_VISITED,x
    ora.l SAME_SCUMM_SCENE_TEMP
    sep #$20
    .a8
    sta.l SAME_SCUMM_SCENE_VISITED,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_SCENE_ACTOR
    asl
    asl
    asl
    asl
    tax
    lda.l SAME_SCUMM_ACTOR_POSE_LOOP_START
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0A,x
    plp
    rtl

ScummV5_Scene_Render_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    ; Incoming room reads/installation own the active metadata alias. Even
    ; between actor chunks (scratch NONE), an old scene must not restart.
    lda.l SAME_SCUMM_M23A_PHASE
    and #$00FF
    cmp #$0004
    bcc ScummV5_Scene_Render__lifecycle_ready
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__lifecycle_ready:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_PHASE
    cmp #$0004
    bne ScummV5_Scene_Render__not_wait
    jml ScummV5_Scene_Render__wait
ScummV5_Scene_Render__not_wait:
    .a16
    .i16
    cmp #$0003
    bne ScummV5_Scene_Render__not_present
    jml ScummV5_Scene_Render__present
ScummV5_Scene_Render__not_present:
    .a16
    .i16
    cmp #$0000
    beq ScummV5_Scene_Render__idle
    jml ScummV5_Scene_Render__service
ScummV5_Scene_Render__idle:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_DIRTY
    bne ScummV5_Scene_Render__dirty
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__dirty:
    .a16
    .i16
    lda.l SAME_SCUMM_CONTROLLER_ROOM_READY
    and #$00FF
    bne ScummV5_Scene_Render__room
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__room:
    .a16
    .i16
    lda.l SAME_SCUMM_CURSOR_PENDING
    beq ScummV5_Scene_Render__cursor_ready
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__cursor_ready:
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Scene_Render__writable
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__writable:
    .a16
    .i16
    jsl Same_VideoSurface_RestoreCursorUnderlay_Far
    bcc ScummV5_Scene_Render__cursor_restored
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__cursor_restored:
    .a16
    .i16
    jsl Same_VideoSurface_RestoreActorUnderlay_Far
    bcc ScummV5_Scene_Render__restored
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__restored:
    .a16
    .i16
    jsl Same_VideoSurface_MergeCursorDamage_Far
    jsl Same_VideoSurface_BeginActorUnderlay_Far
    bcc ScummV5_Scene_Render__begun
    jml ScummV5_Scene_Render__error
ScummV5_Scene_Render__begun:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_SCENE_VISITED
    sta.l SAME_SCUMM_SCENE_VISITED+2
    sta.l SAME_SCUMM_SCENE_JOURNAL_READY
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    sta.l SAME_SCUMM_SCENE_ROOM_EPOCH
    lda.l SAME_VIDEO_SURFACE_SOURCE_X
    sta.l SAME_SCUMM_SCENE_SOURCE_X
    lda.l SAME_VIDEO_SURFACE_SOURCE_Y
    sta.l SAME_SCUMM_SCENE_SOURCE_Y
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    sta.l SAME_SCUMM_SCENE_PALETTE_EPOCH
    lda #$0001
    sta.l SAME_SCUMM_SCENE_PHASE
    sta.l SAME_SCUMM_CURSOR_COMPOSING
    .if SAME_VIDEO_OVERLAY_INDEXED
    sta.l SAME_VIDEO_SURFACE_COMPOSITION_OWNER
    .endif
    sep #$20
    .a8
    sta.l SAME_SCUMM_CEL_VALID
    rep #$20
    .a16
    jsl ScummV5_Scene_Next_Far
    bcs ScummV5_Scene_Render__service
    jml ScummV5_Scene_Render__pass_done
ScummV5_Scene_Render__service:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_SCUMM_SCENE_ROOM_EPOCH
    bne ScummV5_Scene_Render__stale
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    cmp.l SAME_SCUMM_SCENE_PALETTE_EPOCH
    beq ScummV5_Scene_Render__identity
ScummV5_Scene_Render__stale:
    .a16
    .i16
    jsl ScummV5_ActorPose_Cancel_Far
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__identity:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_PHASE
    cmp #$0002
    bne ScummV5_Scene_Render__mask_ready
    jsl ScummV5_Mask_Ensure_Far
    bcs ScummV5_Scene_Render__mask_ready
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__mask_ready:
    .a16
    .i16
    jsl ScummV5_ActorPose_Ensure_Far
    bcs ScummV5_Scene_Render__checked
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__checked:
    .a16
    .i16
    jsl ScummV5_ActorPose_Compose_Far
    php
    rep #$20
    .a16
    lda.l SAME_SCUMM_ERROR
    and #$00FF
    beq ScummV5_Scene_Render__compose_valid
    plp
    jsl ScummV5_ActorPose_Cancel_Far
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__compose_valid:
    .a16
    .i16
    plp
    bcc ScummV5_Scene_Render__actor_complete
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__actor_complete:
    .a16
    .i16
    jsl ScummV5_Scene_Mark_Far
    jsl ScummV5_Scene_Next_Far
    bcc ScummV5_Scene_Render__pass_done
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__pass_done:
    .a16
    .i16
    lda.l SAME_SCUMM_SCENE_PHASE
    cmp #$0001
    bne ScummV5_Scene_Render__drawn
    jsl Same_VideoSurface_CommitActorUnderlay_Far
    bcc ScummV5_Scene_Render__captured
    jml ScummV5_Scene_Render__error
ScummV5_Scene_Render__captured:
    .a16
    .i16
    lda #$0001
    sta.l SAME_SCUMM_SCENE_JOURNAL_READY
    lda #$0000
    sta.l SAME_SCUMM_SCENE_VISITED
    sta.l SAME_SCUMM_SCENE_VISITED+2
    lda #$0002
    sta.l SAME_SCUMM_SCENE_PHASE
    jsl ScummV5_Scene_Next_Far
    bcc ScummV5_Scene_Render__drawn
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__drawn:
    .a16
    .i16
    lda #$0003
    sta.l SAME_SCUMM_SCENE_PHASE
ScummV5_Scene_Render__present:
    .a16
    .i16
    jsl ScummV5_Cursor_Draw_Far
    bcc ScummV5_Scene_Render__cursor
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__cursor:
    .a16
    .i16
    jsl Same_VideoSurface_PushDamagePresent_Far
    bcc ScummV5_Scene_Render__submitted
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__submitted:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sta.l SAME_SCUMM_SCENE_PRESENT
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION+2
    sta.l SAME_SCUMM_SCENE_PRESENT+2
    lda #$0004
    sta.l SAME_SCUMM_SCENE_PHASE
    lda #$0000
    sta.l SAME_SCUMM_CURSOR_COMPOSING
    .if SAME_VIDEO_OVERLAY_INDEXED
    sta.l SAME_VIDEO_SURFACE_COMPOSITION_OWNER
    .endif
    sep #$20
    .a8
    sta.l SAME_SCUMM_CEL_VALID
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    rep #$20
    .a16
    lda #SCUMM_V5_ACTOR_RENDER_ID
    sta.l SAME_SCUMM_SCENE_ACTOR
    jsl ScummV5_Scene_LoadSnapshot_Far
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sta.l SAME_SCUMM_CONTROLLER_RENDER_X
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sta.l SAME_SCUMM_CONTROLLER_RENDER_Y
    rep #$20
    .a16
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_FACING
    sta.l SAME_SCUMM_CONTROLLER_RENDER_FACING
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_COSTUME
    sta.l SAME_SCUMM_CONTROLLER_RENDER_COSTUME
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VISIBLE
    sep #$20
    .a8
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_SELECT
    sta.l SAME_SCUMM_CONTROLLER_RENDER_ACTOR_SELECT
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_FRAME
    sta.l SAME_SCUMM_CONTROLLER_RENDER_POSE_FRAME
    lda.l SAME_SCUMM_ACTOR_POSE_DESIRED_STEP
    sta.l SAME_SCUMM_CONTROLLER_RENDER_POSE_STEP
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    rep #$20
    .a16
    lda.l SAME_SCUMM_CEL_DESIRED_SCALE
    sta.l SAME_SCUMM_CEL_RENDER_SCALE
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__wait:
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Scene_Render__ack_ready
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__ack_ready:
    .a16
    .i16
    jsl Same_VideoSurface_ScrollPresented_Far
    bcc ScummV5_Scene_Render__ack_generation
    jml ScummV5_Scene_Render__done
ScummV5_Scene_Render__ack_generation:
    .a16
    .i16
    lda.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    cmp.l SAME_SCUMM_SCENE_ROOM_EPOCH
    beq ScummV5_Scene_Render__ack_room
    jml ScummV5_Scene_Render__stale
ScummV5_Scene_Render__ack_room:
    .a16
    .i16
    ; ScrollPresented proved the entire current generation is committed and
    ; unlocked. Text/cursor producers may already have committed a successor
    ; containing this scene. Compare the full serial, not equality alone.
    ; A negative half-range delta is older (or ambiguous), never completion.
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION
    sec
    sbc.l SAME_SCUMM_SCENE_PRESENT
    lda.l SAME_VIDEO_SURFACE_NEXT_GENERATION+2
    sbc.l SAME_SCUMM_SCENE_PRESENT+2
    bmi ScummV5_Scene_Render__done
    lda #$0000
    sta.l SAME_SCUMM_SCENE_PHASE
    sta.l SAME_SCUMM_SCENE_DIRTY
    lda #$0001
    sta.l SAME_SCUMM_SCENE_INITIALIZED
    lda.l SAME_SCUMM_SCENE_GENERATION
    inc
    sta.l SAME_SCUMM_SCENE_GENERATION
    bne ScummV5_Scene_Render__generation
    lda.l SAME_SCUMM_SCENE_GENERATION+2
    inc
    sta.l SAME_SCUMM_SCENE_GENERATION+2
ScummV5_Scene_Render__generation:
    .a16
    .i16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CONTROLLER_RENDER_VALID
    sta.l SAME_SCUMM_CONTROLLER_CURSOR_RENDER_VALID
    bra ScummV5_Scene_Render__done
ScummV5_Scene_Render__error:
    .a16
    .i16
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
ScummV5_Scene_Render__done:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    rtl

ScummV5_Scene_Abort_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_SCENE_PHASE
    beq ScummV5_Scene_Abort__done
    ; Phase 4 owns a complete image already handed to the video service. It
    ; has no partial actor to roll back; publication may still lock it. Leave the
    ; journal intact for normal restoration after that publication retires.
    cmp #$0004
    beq ScummV5_Scene_Abort__clear
    lda.l SAME_SCUMM_SCENE_JOURNAL_READY
    beq ScummV5_Scene_Abort__clear
    jsl Same_VideoSurface_RestoreActorUnderlay_Far
    bcc ScummV5_Scene_Abort__clear
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
ScummV5_Scene_Abort__clear:
    .a16
    .i16
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_SCENE_PHASE
    sta.l SAME_SCUMM_SCENE_INITIALIZED
    sta.l SAME_SCUMM_CURSOR_COMPOSING
    .if SAME_VIDEO_OVERLAY_INDEXED
    sta.l SAME_VIDEO_SURFACE_COMPOSITION_OWNER
    .endif
    sep #$20
    .a8
    sta.l SAME_SCUMM_CEL_VALID
    rep #$20
    .a16
    lda #$0001
    sta.l SAME_SCUMM_SCENE_DIRTY
ScummV5_Scene_Abort__done:
    .a16
    .i16
    rep #$20
    .a16
    pla
    plp
    rtl

; Palette presence belongs to each actor, including opaque output color zero.
ScummV5_Scene_PaletteChanged_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    pha
    lda.l SAME_SCUMM_CONDITION
    and #$0007
    tax
    lda.l ScummV5_C7_BitMasks,x
    and #$00FF
    sta.l SAME_SCUMM_SCENE_TEMP
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    lsr
    lsr
    lsr
    clc
    adc 1,s
    tax
    pla
    sep #$20
    .a8
    lda.l SAME_SCUMM_SCENE_ANIMATION+$0C,x
    ora.l SAME_SCUMM_SCENE_TEMP
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0C,x
    rep #$20
    .a16
    jsl ScummV5_Scene_PaletteEpoch_Far
    plx
    pla
    plp
    rtl
ScummV5_Scene_DefaultActor_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    lda.l SAME_SCUMM_C14_ACTOR
    and #$00FF
    asl
    asl
    asl
    asl
    tax
    lda #$0000
    sta.l SAME_SCUMM_SCENE_ANIMATION,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$02,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$04,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$06,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$08,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0A,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0C,x
    sta.l SAME_SCUMM_SCENE_ANIMATION+$0E,x
    jsl ScummV5_Scene_PaletteEpoch_Far
    plx
    pla
    plp
    rtl
ScummV5_Scene_PaletteEpoch_Far:
    .a16
    .i16
    .a16
    lda.l SAME_SCUMM_ACTOR_POSE_GENERATION
    inc
    bne ScummV5_Scene_PaletteEpoch__valid
    inc
ScummV5_Scene_PaletteEpoch__valid:
    .a16
    .i16
    sta.l SAME_SCUMM_ACTOR_POSE_GENERATION
    lda #$0001
    sta.l SAME_SCUMM_SCENE_DIRTY
    rtl

.include "scumm_v5_actor_masks.inc.pasm"
