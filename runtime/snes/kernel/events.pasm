; Fixed-size SAME packet queue.  Required records fail closed; DROP_OK records
; may be discarded and counted.  All packet copies are unrolled so no absolute-
; long indexed-Y instruction can be emitted accidentally.

Same_Event_Reset:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_EVENT_HEAD
    lda #$0000
    sta.l SAME_EVENT_TAIL
    lda #$0000
    sta.l SAME_EVENT_COUNT
    lda #$0000
    sta.l SAME_EVENT_DROPPED
    lda #$0000
    sta.l SAME_EVENT_REJECTED
    lda #$0000
    sta.l SAME_EVENT_SEQUENCE
    plp
    rts

; Input: SAME_EVENT_STAGING fields service/opcode/flags/source/destination/args.
; Output: carry clear if queued, carry set if dropped or rejected.
Same_Event_Push:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_EVENT_COUNT
    cmp #SAME_EVENT_CAPACITY
    bcc Same_Event_Push__space

    sep #$20
    .a8
    lda.l SAME_EVENT_STAGING+SAME_PKT_FLAGS
    and #SAME_FLAG_DROP_OK
    beq Same_Event_Push__reject
    rep #$20
    .a16
    lda.l SAME_EVENT_DROPPED
    inc
    sta.l SAME_EVENT_DROPPED
    plp
    sec
    rts

Same_Event_Push__reject:
    rep #$20
    .a16
    lda.l SAME_EVENT_REJECTED
    inc
    sta.l SAME_EVENT_REJECTED
    plp
    sec
    rts

Same_Event_Push__space:
    sep #$20
    .a8
    lda #SAME_ABI_REVISION
    sta.l SAME_EVENT_STAGING+SAME_PKT_REVISION
    rep #$20
    .a16
    lda.l SAME_EVENT_SEQUENCE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SEQUENCE

    lda.l SAME_EVENT_TAIL
    and #SAME_EVENT_MASK
    asl
    asl
    asl
    asl
    tax

    lda.l SAME_EVENT_STAGING+$00
    sta.l SAME_EVENT_BUFFER+$00,x
    lda.l SAME_EVENT_STAGING+$02
    sta.l SAME_EVENT_BUFFER+$02,x
    lda.l SAME_EVENT_STAGING+$04
    sta.l SAME_EVENT_BUFFER+$04,x
    lda.l SAME_EVENT_STAGING+$06
    sta.l SAME_EVENT_BUFFER+$06,x
    lda.l SAME_EVENT_STAGING+$08
    sta.l SAME_EVENT_BUFFER+$08,x
    lda.l SAME_EVENT_STAGING+$0A
    sta.l SAME_EVENT_BUFFER+$0A,x
    lda.l SAME_EVENT_STAGING+$0C
    sta.l SAME_EVENT_BUFFER+$0C,x
    lda.l SAME_EVENT_STAGING+$0E
    sta.l SAME_EVENT_BUFFER+$0E,x

    lda.l SAME_EVENT_TAIL
    inc
    and #SAME_EVENT_MASK
    sta.l SAME_EVENT_TAIL
    lda.l SAME_EVENT_COUNT
    inc
    sta.l SAME_EVENT_COUNT
    lda.l SAME_EVENT_SEQUENCE
    inc
    sta.l SAME_EVENT_SEQUENCE
    plp
    clc
    rts

; Output: carry clear and packet copied to SAME_EVENT_STAGING; carry set if empty.
Same_Event_Pop:
    php
    rep #$30
    .a16
    .i16
    lda.l SAME_EVENT_COUNT
    bne Same_Event_Pop__present
    plp
    sec
    rts

Same_Event_Pop__present:
    rep #$30
    .a16
    .i16
    lda.l SAME_EVENT_HEAD
    and #SAME_EVENT_MASK
    asl
    asl
    asl
    asl
    tax

    lda.l SAME_EVENT_BUFFER+$00,x
    sta.l SAME_EVENT_STAGING+$00
    lda.l SAME_EVENT_BUFFER+$02,x
    sta.l SAME_EVENT_STAGING+$02
    lda.l SAME_EVENT_BUFFER+$04,x
    sta.l SAME_EVENT_STAGING+$04
    lda.l SAME_EVENT_BUFFER+$06,x
    sta.l SAME_EVENT_STAGING+$06
    lda.l SAME_EVENT_BUFFER+$08,x
    sta.l SAME_EVENT_STAGING+$08
    lda.l SAME_EVENT_BUFFER+$0A,x
    sta.l SAME_EVENT_STAGING+$0A
    lda.l SAME_EVENT_BUFFER+$0C,x
    sta.l SAME_EVENT_STAGING+$0C
    lda.l SAME_EVENT_BUFFER+$0E,x
    sta.l SAME_EVENT_STAGING+$0E

    lda.l SAME_EVENT_HEAD
    inc
    and #SAME_EVENT_MASK
    sta.l SAME_EVENT_HEAD
    lda.l SAME_EVENT_COUNT
    dec
    sta.l SAME_EVENT_COUNT
    plp
    clc
    rts

; Clear staging and set common source/destination fields for an engine request.
Same_Event_StageEngine:
    php
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_EVENT_STAGING+$00
    lda #$0000
    sta.l SAME_EVENT_STAGING+$02
    lda #$0000
    sta.l SAME_EVENT_STAGING+$04
    lda #$0000
    sta.l SAME_EVENT_STAGING+$06
    lda #$0000
    sta.l SAME_EVENT_STAGING+$08
    lda #$0000
    sta.l SAME_EVENT_STAGING+$0A
    lda #$0000
    sta.l SAME_EVENT_STAGING+$0C
    lda #$0000
    sta.l SAME_EVENT_STAGING+$0E
    sep #$20
    .a8
    lda #SAME_ENDPOINT_ENGINE
    sta.l SAME_EVENT_STAGING+SAME_PKT_SOURCE
    lda #SAME_ENDPOINT_KERNEL
    sta.l SAME_EVENT_STAGING+SAME_PKT_DESTINATION
    plp
    rts


; SAME 0.1 compatibility wrapper.
Same_Event_StageTarget:
    jsr Same_Event_StageEngine
    rts
