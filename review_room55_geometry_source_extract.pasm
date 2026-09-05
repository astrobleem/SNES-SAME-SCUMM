; Exact generated accessor body excerpt from
; runtime/snes/generated/scumm_v5_room_data.inc.pasm (room55 record dispatch).
; This is a screened source extract, not a game payload.
ScummV5_PutActor_LoadGeometry__room55:
    rep #$20
    .a16
    cpx #$0040
    bcs ScummV5_PutActor_LoadGeometry__fail_room55
    txa
    asl
    sta.l SAME_SCUMM_PUT_ACTOR_TEMP0
    asl
    asl
    asl
    clc
    adc.l SAME_SCUMM_PUT_ACTOR_TEMP0
    tax
ScummV5_PutActor_LoadGeometry__copy_room55:
    .a16
    .i16
    lda.l ScummV5_PutActor_Record_2_Geometry+00,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+00
    lda.l ScummV5_PutActor_Record_2_Geometry+02,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+02
    lda.l ScummV5_PutActor_Record_2_Geometry+04,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+04
    lda.l ScummV5_PutActor_Record_2_Geometry+06,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+06
    lda.l ScummV5_PutActor_Record_2_Geometry+08,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+08
    lda.l ScummV5_PutActor_Record_2_Geometry+10,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+10
    lda.l ScummV5_PutActor_Record_2_Geometry+12,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+12
    lda.l ScummV5_PutActor_Record_2_Geometry+14,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+14
    lda.l ScummV5_PutActor_Record_2_Geometry+16,x
    sta.l SAME_SCUMM_PUT_ACTOR_GEOMETRY_WORK+16
    sep #$20
    .a8
    clc
    rtl
ScummV5_PutActor_LoadGeometry__fail_room55:
    sep #$20
    .a8
    sec
    rtl
