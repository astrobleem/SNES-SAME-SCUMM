; Semantic admission for classic animateActor requests. A is the raw request,
; X the validated C14 actor base. C=1 leaves the existing decoded chore alone.
; Direction-only requests still reach ObserveAnimate in the caller. No resource
; read, renderer transaction, or shared scratch is borrowed by this routine.
ScummV5_ActorAnimation_Admission_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_COSTUME,x
    and #$00FF
    pha
    lda 7,s
    and #$00FF
    cmp #$00F4
    bcc ScummV5_ActorAnimation__frame
    cmp #$00FC
    bcs ScummV5_ActorAnimation__stand
    brl ScummV5_ActorAnimation__unchanged_without_index
ScummV5_ActorAnimation__stand:
    .a16
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_STAND_FRAME,x
    and #$00FF
ScummV5_ActorAnimation__frame:
    .a16
    asl
    asl
    pha ; animation index, direction added below
    lda.l SAME_SCUMM_C14_ACTORS+SAME_SCUMM_C14_A_ROOM,x
    and #$00FF
    sep #$20
    .a8
    cmp.l SAME_SCUMM_M23A_ACTIVE_ROOM
    beq ScummV5_ActorAnimation__current_room
    brl ScummV5_ActorAnimation__unchanged
ScummV5_ActorAnimation__current_room:
    rep #$20
    .a16
    lda 3,s
    bne ScummV5_ActorAnimation__costume
    brl ScummV5_ActorAnimation__unchanged
ScummV5_ActorAnimation__costume:
    .a16
    txa
    lsr
    lsr
    lsr
    lsr
    lsr ; actor base / 32 = facing word index
    tax
    lda.l SAME_SCUMM_ACTOR_FACINGS,x
    cmp #$0047
    bcc ScummV5_ActorAnimation__north
    cmp #$006E
    bcc ScummV5_ActorAnimation__east
    cmp #$00FC
    bcc ScummV5_ActorAnimation__south
    cmp #$0122
    bcc ScummV5_ActorAnimation__west
ScummV5_ActorAnimation__north:
    .a16
    lda #$0003
    bra ScummV5_ActorAnimation__direction
ScummV5_ActorAnimation__east:
    .a16
    lda #$0001
    bra ScummV5_ActorAnimation__direction
ScummV5_ActorAnimation__south:
    .a16
    lda #$0002
    bra ScummV5_ActorAnimation__direction
ScummV5_ActorAnimation__west:
    .a16
    lda #$0000
ScummV5_ActorAnimation__direction:
    .a16
    clc
    adc 1,s
    tay
    pla
    tya
    pha
    ldx #$0000
ScummV5_ActorAnimation__find:
    .a16
    .i16
    cpx #(SCUMM_V5_ACTOR_ANIMATION_MASK_COUNT*33)
    bcs ScummV5_ActorAnimation__accept ; unknown costume still fails in checked lookup
    lda.l ScummV5_ActorAnimationMasks,x
    and #$00FF
    cmp 3,s
    beq ScummV5_ActorAnimation__found
    txa
    clc
    adc #$0021
    tax
    bra ScummV5_ActorAnimation__find
ScummV5_ActorAnimation__found:
    .a16
    txa
    tay
    lda 1,s
    cmp #$0100
    bcs ScummV5_ActorAnimation__unchanged
    lsr
    lsr
    lsr
    inc
    pha
    tya
    clc
    adc 1,s
    tax
    pla
    lda.l ScummV5_ActorAnimationMasks,x
    and #$00FF
    pha
    lda 3,s
    and #$0007
    tax
    lda.l ScummV5_C7_BitMasks,x
    and #$00FF
    and 1,s
    tax
    pla
    cpx #$0000
    beq ScummV5_ActorAnimation__unchanged
ScummV5_ActorAnimation__accept:
    rep #$30
    .a16
    .i16
    pla
    pla
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_ActorAnimation__unchanged:
    rep #$30
    .a16
    .i16
    pla
ScummV5_ActorAnimation__unchanged_without_index:
    rep #$30
    .a16
    .i16
    pla
    ply
    plx
    pla
    plp
    sec
    rtl
