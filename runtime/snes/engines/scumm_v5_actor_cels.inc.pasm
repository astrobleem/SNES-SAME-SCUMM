; Ordered source-cel scaling. Same checked actor scratch and INDEX8 service;
; no second pixel buffer. All phase arithmetic wraps at 256, not at cel edges.
; Called with exclusive actor composition ownership.

; A=initial phase, X=sample count, Y=scale, C=forward (clear=backward).
; Returns A=count(table[phase] < scale), preserves X/Y/P/DB/D.
; Strict comparison is required for anchor offsets even at scale 255.
ScummV5_Cel_Count_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phx ; private remaining count, original X below it
    phy
    and #$00FF
    tax
    ldy #$0000
    bcc ScummV5_Cel_Count__back
ScummV5_Cel_Count__forward:
    .a16
    .i16
    lda 3,s
    beq ScummV5_Cel_Count__done
    lda.l ScummV5_Cel_ScaleTable,x
    and #$00FF
    cmp 1,s
    bcs ScummV5_Cel_Count__forward_skip
    iny
ScummV5_Cel_Count__forward_skip:
    .a16
    .i16
    txa
    inc
    and #$00FF
    tax
    lda 3,s
    dec
    sta 3,s
    bra ScummV5_Cel_Count__forward
ScummV5_Cel_Count__back:
    .a16
    .i16
    lda 3,s
    beq ScummV5_Cel_Count__done
    lda.l ScummV5_Cel_ScaleTable,x
    and #$00FF
    cmp 1,s
    bcs ScummV5_Cel_Count__back_skip
    iny
ScummV5_Cel_Count__back_skip:
    .a16
    .i16
    txa
    dec
    and #$00FF
    tax
    lda 3,s
    dec
    sta 3,s
    bra ScummV5_Cel_Count__back
ScummV5_Cel_Count__done:
    .a16
    .i16
    tya
    sta 7,s
    ply
    pla ; discard private count
    plx
    pla
    plp
    rtl

; Cel RX/RY already include cumulative limb motion. Feet are source-space
; viewport coordinates. Independent X/Y scale bytes are snapshotted in ticket.
; Preserves registers; C=1 means signed coordinate overflow (fail closed).
ScummV5_Cel_Origin_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_CEL_TICKET_SCALE
    and #$00FF
    sta.l SAME_SCUMM_CEL_SCALE_X
    lda.l SAME_SCUMM_CEL_TICKET_SCALE
    xba
    and #$00FF
    sta.l SAME_SCUMM_CEL_SCALE_Y
    lda #$0001
    sta.l SAME_SCUMM_CEL_XSTEP
    lda.l SAME_SCUMM_CEL_DIRECTION
    and #$00FF
    bne ScummV5_Cel_Origin__right
    lda #$FFFF
    sta.l SAME_SCUMM_CEL_XSTEP
ScummV5_Cel_Origin__right:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_TICKET_SCALE
    cmp #$FFFF
    bne ScummV5_Cel_Origin__scaled
    lda #$0080
    sta.l SAME_SCUMM_CEL_PHASE_X
    sta.l SAME_SCUMM_CEL_PHASE_Y
    lda.l SAME_SCUMM_CEL_RX
    sta.l SAME_SCUMM_CEL_TEMP
    bra ScummV5_Cel_Origin__signed_x
ScummV5_Cel_Origin__scaled:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_RX
    bpl ScummV5_Cel_Origin__abs_x
    eor #$FFFF
    inc
ScummV5_Cel_Origin__abs_x:
    .a16
    .i16
    tax
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Origin__phase_left
    lda #$0080
    sec
    sbc.l SAME_SCUMM_CEL_TEMP
    bra ScummV5_Cel_Origin__phase_x
ScummV5_Cel_Origin__phase_left:
    .a16
    .i16
    lda #$0080
    clc
    adc.l SAME_SCUMM_CEL_TEMP
ScummV5_Cel_Origin__phase_x:
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_CEL_PHASE_X
    lda.l SAME_SCUMM_CEL_SCALE_X
    tay
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Origin__count_left
    lda.l SAME_SCUMM_CEL_PHASE_X
    sec
    bra ScummV5_Cel_Origin__count_x
ScummV5_Cel_Origin__count_left:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PHASE_X
    clc
ScummV5_Cel_Origin__count_x:
    .a16
    .i16
    jsl ScummV5_Cel_Count_Far
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_RX
    bpl ScummV5_Cel_Origin__signed_x
    lda.l SAME_SCUMM_CEL_TEMP
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_CEL_TEMP
ScummV5_Cel_Origin__signed_x:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Origin__subtract_x
    lda.l SAME_SCUMM_ACTOR_FOOT_SCREEN_X
    clc
    adc.l SAME_SCUMM_CEL_TEMP
    bra ScummV5_Cel_Origin__store_x
ScummV5_Cel_Origin__subtract_x:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_FOOT_SCREEN_X
    sec
    sbc.l SAME_SCUMM_CEL_TEMP
ScummV5_Cel_Origin__store_x:
    .a16
    .i16
    bvc ScummV5_Cel_Origin__x_ok
    jml ScummV5_Cel_Origin__bad
ScummV5_Cel_Origin__x_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_CEL_ORIGIN_X
    lda.l SAME_SCUMM_CEL_RY
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_TICKET_SCALE
    cmp #$FFFF
    beq ScummV5_Cel_Origin__signed_y
    lda.l SAME_SCUMM_CEL_RY
    bpl ScummV5_Cel_Origin__abs_y
    eor #$FFFF
    inc
ScummV5_Cel_Origin__abs_y:
    .a16
    .i16
    tax
    sta.l SAME_SCUMM_CEL_TEMP
    lda #$0080
    sec
    sbc.l SAME_SCUMM_CEL_TEMP
    and #$00FF
    sta.l SAME_SCUMM_CEL_PHASE_Y
    lda.l SAME_SCUMM_CEL_SCALE_Y
    tay
    lda.l SAME_SCUMM_CEL_PHASE_Y
    sec
    jsl ScummV5_Cel_Count_Far
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_RY
    bpl ScummV5_Cel_Origin__signed_y
    lda.l SAME_SCUMM_CEL_TEMP
    eor #$FFFF
    inc
    sta.l SAME_SCUMM_CEL_TEMP
ScummV5_Cel_Origin__signed_y:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_FOOT_SCREEN_Y
    clc
    adc.l SAME_SCUMM_CEL_TEMP
    bvs ScummV5_Cel_Origin__bad
    sta.l SAME_SCUMM_CEL_ORIGIN_Y
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cel_Origin__bad:
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

ScummV5_Cel_ScaleTable:
    .byte $FF, $FD, $7D, $BD, $3D, $DD, $5D, $9D, $1D, $ED, $6D, $AD, $2D, $CD, $4D, $8D
    .byte $0D, $F5, $75, $B5, $35, $D5, $55, $95, $15, $E5, $65, $A5, $25, $C5, $45, $85
    .byte $05, $F9, $79, $B9, $39, $D9, $59, $99, $19, $E9, $69, $A9, $29, $C9, $49, $89
    .byte $09, $F1, $71, $B1, $31, $D1, $51, $91, $11, $E1, $61, $A1, $21, $C1, $41, $81
    .byte $01, $FB, $7B, $BB, $3B, $DB, $5B, $9B, $1B, $EB, $6B, $AB, $2B, $CB, $4B, $8B
    .byte $0B, $F3, $73, $B3, $33, $D3, $53, $93, $13, $E3, $63, $A3, $23, $C3, $43, $83
    .byte $03, $F7, $77, $B7, $37, $D7, $57, $97, $17, $E7, $67, $A7, $27, $C7, $47, $87
    .byte $07, $EF, $6F, $AF, $2F, $CF, $4F, $8F, $0F, $DF, $5F, $9F, $1F, $BF, $3F, $7F
    .byte $00, $80, $40, $C0, $20, $A0, $60, $E0, $10, $90, $50, $D0, $30, $B0, $70, $F0
    .byte $08, $88, $48, $C8, $28, $A8, $68, $E8, $18, $98, $58, $D8, $38, $B8, $78, $F8
    .byte $04, $84, $44, $C4, $24, $A4, $64, $E4, $14, $94, $54, $D4, $34, $B4, $74, $F4
    .byte $0C, $8C, $4C, $CC, $2C, $AC, $6C, $EC, $1C, $9C, $5C, $DC, $3C, $BC, $7C, $FC
    .byte $02, $82, $42, $C2, $22, $A2, $62, $E2, $12, $92, $52, $D2, $32, $B2, $72, $F2
    .byte $0A, $8A, $4A, $CA, $2A, $AA, $6A, $EA, $1A, $9A, $5A, $DA, $3A, $BA, $7A, $FA
    .byte $06, $86, $46, $C6, $26, $A6, $66, $E6, $16, $96, $56, $D6, $36, $B6, $76, $F6
    .byte $0E, $8E, $4E, $CE, $2E, $AE, $6E, $EE, $1E, $9E, $5E, $DE, $3E, $BE, $7E, $FE

; Read the ordered, source-neutral 32-byte cel descriptor. The entire table
; is compiler ROM metadata; executable pixels remain exclusively in SC5ACT.
ScummV5_Cel_Load_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phb
    lda.l SAME_SCUMM_CEL_CURSOR
    cmp #SCUMM_V5_ACTOR_CEL_COUNT
    bcc ScummV5_Cel_Load__index_ok
    jml ScummV5_Cel_Load__bad
ScummV5_Cel_Load__index_ok:
    .a16
    .i16
    and #$FC00
    xba
    lsr
    lsr
    clc
    adc #SCUMM_V5_ACTOR_CEL_FIRST_BANK
    sep #$20
    .a8
    pha
    plb
    rep #$20
    .a16
    lda.l SAME_SCUMM_CEL_CURSOR
    and #$03FF
    asl
    asl
    asl
    asl
    asl
    tax
    lda $8000,x
    sta.l SAME_SCUMM_CEL_WIDTH
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_CEL_HEIGHT
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_CEL_RX
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_CEL_RY
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_CEL_MX
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_CEL_MY
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_FIRST
    inx
    inx
    lda $8000,x
    sta.l SAME_SCUMM_ACTOR_SPAN_COUNT
    lda.l SAME_SCUMM_CEL_WIDTH
    beq ScummV5_Cel_Load__bad
    cmp #$0201
    bcs ScummV5_Cel_Load__bad
    lda.l SAME_SCUMM_CEL_HEIGHT
    beq ScummV5_Cel_Load__bad
    cmp #$0201
    bcs ScummV5_Cel_Load__bad
    lda.l SAME_SCUMM_CEL_RX
    clc
    adc.l SAME_SCUMM_CEL_CUM_X
    bvs ScummV5_Cel_Load__bad
    sta.l SAME_SCUMM_CEL_RX
    lda.l SAME_SCUMM_CEL_RY
    clc
    adc.l SAME_SCUMM_CEL_CUM_Y
    bvs ScummV5_Cel_Load__bad
    sta.l SAME_SCUMM_CEL_RY
    lda.l SAME_SCUMM_CEL_CUM_X
    clc
    adc.l SAME_SCUMM_CEL_MX
    bvs ScummV5_Cel_Load__bad
    sta.l SAME_SCUMM_CEL_CUM_X
    lda.l SAME_SCUMM_CEL_CUM_Y
    sec
    sbc.l SAME_SCUMM_CEL_MY
    bvs ScummV5_Cel_Load__bad
    sta.l SAME_SCUMM_CEL_CUM_Y
    plb
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cel_Load__bad:
    .a16
    .i16
    plb
    plx
    pla
    plp
    sec
    rtl

; Convert the current global span index into a checked bank/local descriptor.
; Does not change the iterator. Each cel preserves increasing source X per row.
ScummV5_Cel_Span_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    and #$F000
    xba
    lsr
    lsr
    lsr
    lsr
    cmp #SCUMM_V5_ACTOR_SPAN_BANK_COUNT
    bcs ScummV5_Cel_Span__bad
    sep #$20
    .a8
    sta.l SAME_SCUMM_ACTOR_SPAN_PAGE
    rep #$20
    .a16
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    pha
    and #$0FFF
    asl
    asl
    asl
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    jsl ScummV5_ActorPose_LoadSpan_Far
    pla
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    cmp.l SAME_SCUMM_CEL_WIDTH
    bcs ScummV5_Cel_Span__bad
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    cmp.l SAME_SCUMM_CEL_HEIGHT
    bcs ScummV5_Cel_Span__bad
    lda.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    beq ScummV5_Cel_Span__bad
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_X
    bcs ScummV5_Cel_Span__bad
    cmp.l SAME_SCUMM_CEL_WIDTH
    bcc ScummV5_Cel_Span__range_ok
    bne ScummV5_Cel_Span__bad
ScummV5_Cel_Span__range_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    bcs ScummV5_Cel_Span__bad
    cmp.l SAME_SCUMM_CEL_TOTAL_BYTES
    bcc ScummV5_Cel_Span__ok
    bne ScummV5_Cel_Span__bad
ScummV5_Cel_Span__ok:
    .a16
    .i16
    pla
    plp
    clc
    rtl
ScummV5_Cel_Span__bad:
    .a16
    .i16
    pla
    plp
    sec
    rtl

; Calculate the sampled row and first destination column for a source span.
; C=1 means the row is vertically skipped/offscreen. Horizontal collapsed
; columns are still drawn in source order, including their last opaque color.
ScummV5_Cel_Project_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda.l SAME_SCUMM_CEL_PHASE_Y
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_Y
    and #$00FF
    tax
    lda.l SAME_SCUMM_CEL_SCALE_Y
    cmp #$00FF
    beq ScummV5_Cel_Project__full_y
    lda.l ScummV5_Cel_ScaleTable,x
    and #$00FF
    cmp.l SAME_SCUMM_CEL_SCALE_Y
    bcc ScummV5_Cel_Project__sample_y
    jml ScummV5_Cel_Project__skip
ScummV5_Cel_Project__sample_y:
    .a16
    .i16
    ; Rows are canonical and increasing. Count only the newly crossed source
    ; rows; multiple opaque spans on one row reuse the same scaled ordinate.
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    sec
    sbc.l SAME_SCUMM_CEL_ROW_PHASE
    tax
    lda.l SAME_SCUMM_CEL_SCALE_Y
    tay
    lda.l SAME_SCUMM_CEL_PHASE_Y
    clc
    adc.l SAME_SCUMM_CEL_ROW_PHASE
    and #$00FF
    sec
    jsl ScummV5_Cel_Count_Far
    clc
    adc.l SAME_SCUMM_CEL_PIXEL
    sta.l SAME_SCUMM_CEL_PIXEL
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    sta.l SAME_SCUMM_CEL_ROW_PHASE
    lda.l SAME_SCUMM_CEL_PIXEL
    bra ScummV5_Cel_Project__row
ScummV5_Cel_Project__full_y:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
ScummV5_Cel_Project__row:
    .a16
    .i16
    clc
    adc.l SAME_SCUMM_CEL_ORIGIN_Y
    bvs ScummV5_Cel_Project__skip
    bmi ScummV5_Cel_Project__skip
    cmp #SAME_VIDEO_SCENE_BOTTOM
    bcs ScummV5_Cel_Project__skip
    sta.l SAME_SCUMM_CEL_Y
    lda.l SAME_SCUMM_CEL_SCALE_X
    cmp #$00FF
    beq ScummV5_Cel_Project__full_x
    tay
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    tax
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Project__left_count
    lda.l SAME_SCUMM_CEL_PHASE_X
    sec
    bra ScummV5_Cel_Project__count_x
ScummV5_Cel_Project__left_count:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PHASE_X
    clc
ScummV5_Cel_Project__count_x:
    .a16
    .i16
    jsl ScummV5_Cel_Count_Far
    bra ScummV5_Cel_Project__x_counted
ScummV5_Cel_Project__full_x:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_X
ScummV5_Cel_Project__x_counted:
    .a16
    .i16
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Project__left
    lda.l SAME_SCUMM_CEL_ORIGIN_X
    clc
    adc.l SAME_SCUMM_CEL_TEMP
    sta.l SAME_SCUMM_CEL_X
    lda.l SAME_SCUMM_CEL_PHASE_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_X
    bra ScummV5_Cel_Project__phase
ScummV5_Cel_Project__left:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_ORIGIN_X
    sec
    sbc.l SAME_SCUMM_CEL_TEMP
    sta.l SAME_SCUMM_CEL_X
    lda.l SAME_SCUMM_CEL_PHASE_X
    sec
    sbc.l SAME_SCUMM_ACTOR_SPAN_X
ScummV5_Cel_Project__phase:
    .a16
    .i16
    and #$00FF
    sta.l SAME_SCUMM_CEL_PIXEL_PHASE
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cel_Project__skip:
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; Three passes over immutable cel metadata: validate, capture old background,
; then draw checked chunks. No publication is allowed until the last chunk.
ScummV5_Cel_Compose_Far:
    .a16
    .i16
    php
    cld
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    ; Hiding an actor restores its old journal in the caller and needs no
    ; costume request. Never reuse the last visible cel directory to draw it.
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_VISIBLE
    and #$00FF
    bne ScummV5_Cel_Compose__visible
    ; There is no checked-read ticket for an invisible pose, but its committed
    ; scale cache key must still match the desired snapshot. A stale ticket
    ; would manufacture a full PRESENT on every writable turn while hidden.
    lda.l SAME_SCUMM_CEL_DESIRED_SCALE
    sta.l SAME_SCUMM_CEL_TICKET_SCALE
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    jml ScummV5_Cel_Compose__complete
ScummV5_Cel_Compose__visible:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_TICKET_ROOM_EPOCH
    cmp.l SAME_VIDEO_SURFACE_ROOM_GENERATION
    beq ScummV5_Cel_Compose__epoch_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__epoch_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_TICKET_COSTUME_EPOCH
    cmp.l SAME_SCUMM_ACTOR_POSE_GENERATION
    beq ScummV5_Cel_Compose__pose_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__pose_ok:
    .a16
    .i16
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Cel_Compose__writable
    jml ScummV5_Cel_Compose__retry
ScummV5_Cel_Compose__writable:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_VALID
    and #$00FF
    beq ScummV5_Cel_Compose__first
    lda #$0002
    sta.l SAME_SCUMM_CEL_PASS
    jml ScummV5_Cel_Compose__pass
ScummV5_Cel_Compose__first:
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_CEL_PASS
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_X
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_X
    bvc ScummV5_Cel_Compose__foot_x
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__foot_x:
    .a16
    .i16
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_X
    bvc ScummV5_Cel_Compose__foot_x_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__foot_x_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_ACTOR_FOOT_SCREEN_X
    lda.l SAME_SCUMM_CONTROLLER_DESIRED_Y
    sec
    sbc.l SAME_SCUMM_C14_ACTORS+(SCUMM_V5_ACTOR_RENDER_ID*$40)+SAME_SCUMM_C14_A_ELEVATION
    bvc ScummV5_Cel_Compose__elevation_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__elevation_ok:
    .a16
    .i16
    sec
    sbc.l SAME_VIDEO_SURFACE_SOURCE_Y
    bvc ScummV5_Cel_Compose__foot_y
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__foot_y:
    .a16
    .i16
    clc
    adc.l SAME_VIDEO_SURFACE_DEST_Y
    bvc ScummV5_Cel_Compose__foot_y_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__foot_y_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_ACTOR_FOOT_SCREEN_Y
ScummV5_Cel_Compose__pass:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda #$0000
    sta.l SAME_SCUMM_CEL_CUM_X
    sta.l SAME_SCUMM_CEL_CUM_Y
    sta.l SAME_SCUMM_CEL_PIXEL
    lda.l SAME_SCUMM_CEL_FIRST
    sta.l SAME_SCUMM_CEL_CURSOR
    lda.l SAME_SCUMM_CEL_COUNT
    sta.l SAME_SCUMM_CEL_REMAIN
ScummV5_Cel_Compose__cel:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_REMAIN
    bne ScummV5_Cel_Compose__cel_body
    jml ScummV5_Cel_Compose__pass_done
ScummV5_Cel_Compose__cel_body:
    .a16
    .i16
    jsl ScummV5_Cel_Load_Far
    bcc ScummV5_Cel_Compose__loaded
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__loaded:
    .a16
    .i16
    jsl ScummV5_Cel_Origin_Far
    bcc ScummV5_Cel_Compose__origin
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__origin:
    .a16
    .i16
    ; Unscaled extents bound every reduced coordinate. Reject signed wrap
    ; before capture, even when the cel is completely outside the viewport.
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Compose__extent_left
    lda.l SAME_SCUMM_CEL_ORIGIN_X
    clc
    adc.l SAME_SCUMM_CEL_WIDTH
    bra ScummV5_Cel_Compose__extent_x
ScummV5_Cel_Compose__extent_left:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_ORIGIN_X
    sec
    sbc.l SAME_SCUMM_CEL_WIDTH
ScummV5_Cel_Compose__extent_x:
    .a16
    .i16
    bvc ScummV5_Cel_Compose__extent_y
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__extent_y:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_ORIGIN_Y
    clc
    adc.l SAME_SCUMM_CEL_HEIGHT
    bvc ScummV5_Cel_Compose__extents_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__extents_ok:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_FIRST
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_COUNT
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    lda #$FFFF
    sta.l SAME_SCUMM_CEL_ROW_PHASE ; previous source row for canonical validation
    lda #$0000
    sta.l SAME_SCUMM_CEL_TEMP ; prior exclusive source X
    lda.l SAME_SCUMM_CEL_PASS
    beq ScummV5_Cel_Compose__span
    lda #$0000
    sta.l SAME_SCUMM_CEL_ROW_PHASE
    sta.l SAME_SCUMM_CEL_PIXEL ; scaled Y offset, after canonical validation
ScummV5_Cel_Compose__span:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    bne ScummV5_Cel_Compose__span_body
    jml ScummV5_Cel_Compose__next_cel
ScummV5_Cel_Compose__span_body:
    .a16
    .i16
    jsl ScummV5_Cel_Span_Far
    bcc ScummV5_Cel_Compose__span_valid
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__span_valid:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PASS
    bne ScummV5_Cel_Compose__project
    lda.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    cmp.l SAME_SCUMM_CEL_PIXEL
    beq ScummV5_Cel_Compose__canonical_source
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__canonical_source:
    .a16
    .i16
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    sta.l SAME_SCUMM_CEL_PIXEL
    lda.l SAME_SCUMM_CEL_ROW_PHASE
    cmp #$FFFF
    beq ScummV5_Cel_Compose__canonical_row
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    cmp.l SAME_SCUMM_CEL_ROW_PHASE
    bcc ScummV5_Cel_Compose__noncanonical
    bne ScummV5_Cel_Compose__canonical_row
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    cmp.l SAME_SCUMM_CEL_TEMP
    bcs ScummV5_Cel_Compose__canonical_row
ScummV5_Cel_Compose__noncanonical:
    .a16
    .i16
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__canonical_row:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_Y
    sta.l SAME_SCUMM_CEL_ROW_PHASE
    lda.l SAME_SCUMM_ACTOR_SPAN_X
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    sta.l SAME_SCUMM_CEL_TEMP
    jml ScummV5_Cel_Compose__next_span
ScummV5_Cel_Compose__project:
    .a16
    .i16
    ; Do not project or walk pixels belonging entirely to another checked
    ; chunk. Canonical validation/capture still cover the complete pose.
    lda.l SAME_SCUMM_CEL_PASS
    cmp #$0002
    bne ScummV5_Cel_Compose__project_owned
    lda.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    clc
    adc.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    cmp.l SAME_SCUMM_CEL_CHUNK_OFFSET
    bcc ScummV5_Cel_Compose__skip_chunk
    beq ScummV5_Cel_Compose__skip_chunk
    lda.l SAME_SCUMM_CEL_CHUNK_OFFSET
    clc
    adc.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    cmp.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    bcc ScummV5_Cel_Compose__skip_chunk
    beq ScummV5_Cel_Compose__skip_chunk
ScummV5_Cel_Compose__project_owned:
    .a16
    .i16
    jsl ScummV5_Cel_Project_Far
    bcc ScummV5_Cel_Compose__row_visible
ScummV5_Cel_Compose__skip_chunk:
    .a16
    .i16
    jml ScummV5_Cel_Compose__next_span
ScummV5_Cel_Compose__row_visible:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PASS
    cmp #$0001
    beq ScummV5_Cel_Compose__capture_row
    jml ScummV5_Cel_Compose__draw_row
ScummV5_Cel_Compose__capture_row:
    .a16
    .i16
    ; A source run maps monotonically, including repeated destinations when
    ; X reduction does not advance. Its first/last pixel give exact capture
    ; coverage; walking every pixel just to find these bounds is unnecessary.
    lda.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    dec
    tax
    lda.l SAME_SCUMM_CEL_SCALE_X
    cmp #$00FF
    beq ScummV5_Cel_Compose__capture_full
    tay
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Compose__capture_back
    lda.l SAME_SCUMM_CEL_PIXEL_PHASE
    sec
    bra ScummV5_Cel_Compose__capture_count
ScummV5_Cel_Compose__capture_back:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PIXEL_PHASE
    clc
ScummV5_Cel_Compose__capture_count:
    .a16
    .i16
    jsl ScummV5_Cel_Count_Far
    bra ScummV5_Cel_Compose__capture_extent
ScummV5_Cel_Compose__capture_full:
    .a16
    .i16
    txa
ScummV5_Cel_Compose__capture_extent:
    .a16
    .i16
    sta.l SAME_SCUMM_CEL_TEMP
    lda.l SAME_SCUMM_CEL_XSTEP
    bmi ScummV5_Cel_Compose__capture_left
    lda.l SAME_SCUMM_CEL_X
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
    clc
    adc.l SAME_SCUMM_CEL_TEMP
    inc
    bra ScummV5_Cel_Compose__capture_clip
ScummV5_Cel_Compose__capture_left:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_X
    sec
    sbc.l SAME_SCUMM_CEL_TEMP
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
    lda.l SAME_SCUMM_CEL_X
    inc
ScummV5_Cel_Compose__capture_clip:
    .a16
    .i16
    bpl ScummV5_Cel_Compose__capture_nonnegative
    jml ScummV5_Cel_Compose__next_span
ScummV5_Cel_Compose__capture_nonnegative:
    .a16
    .i16
    cmp #$0101
    bcc ScummV5_Cel_Compose__capture_right_ok
    lda #$0100
ScummV5_Cel_Compose__capture_right_ok:
    .a16
    .i16
    sta.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    lda.l SAME_SCUMM_ACTOR_CLIP_LEFT
    bpl ScummV5_Cel_Compose__capture_left_ok
    lda #$0000
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
ScummV5_Cel_Compose__capture_left_ok:
    .a16
    .i16
    jml ScummV5_Cel_Compose__row_done
ScummV5_Cel_Compose__draw_row:
    .a16
    .i16
    lda #$0100
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
    lda #$0000
    sta.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    sta.l SAME_SCUMM_CEL_LOOP
ScummV5_Cel_Compose__pixel_loop:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_LOOP
    cmp.l SAME_SCUMM_ACTOR_SPAN_LENGTH
    bcc ScummV5_Cel_Compose__pixel_body
    jml ScummV5_Cel_Compose__row_done
ScummV5_Cel_Compose__pixel_body:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_X
    cmp #$0100
    bcs ScummV5_Cel_Compose__advance
    lda.l SAME_SCUMM_CEL_PASS
    cmp #$0002
    beq ScummV5_Cel_Compose__draw
    lda.l SAME_SCUMM_CEL_X
    cmp.l SAME_SCUMM_ACTOR_CLIP_LEFT
    bcs ScummV5_Cel_Compose__capture_right
    sta.l SAME_SCUMM_ACTOR_CLIP_LEFT
ScummV5_Cel_Compose__capture_right:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_X
    inc
    cmp.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    bcc ScummV5_Cel_Compose__advance
    sta.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    bra ScummV5_Cel_Compose__advance
ScummV5_Cel_Compose__draw:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_SOURCE
    clc
    adc.l SAME_SCUMM_CEL_LOOP
    sec
    sbc.l SAME_SCUMM_CEL_CHUNK_OFFSET
    bcc ScummV5_Cel_Compose__advance
    cmp.l SAME_SCUMM_ACTOR_TICKET_LENGTH
    bcs ScummV5_Cel_Compose__advance
    ; CanWrite was acquired once for this synchronous composition turn.
    ; Y clipping, X clipping and the accepted ticket length were checked
    ; above. Use the existing target-neutral pixel leaf, not a one-pixel run
    ; which would re-scan ownership and save/restore damage for every byte.
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ACTOR_POSE_BUFFER,x
    pha
    rep #$20
    .a16
    lda.l SAME_SCUMM_CEL_Y
    xba
    ora.l SAME_SCUMM_CEL_X
    tax
    sep #$20
    .a8
    pla
    jsl Same_VideoSurface_WriteIndexedPixel_Far
    rep #$20
    .a16
ScummV5_Cel_Compose__advance:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_SCALE_X
    cmp #$00FF
    beq ScummV5_Cel_Compose__move_x
    lda.l SAME_SCUMM_CEL_PIXEL_PHASE
    tax
    lda.l ScummV5_Cel_ScaleTable,x
    and #$00FF
    cmp.l SAME_SCUMM_CEL_SCALE_X
    bcs ScummV5_Cel_Compose__phase_x
ScummV5_Cel_Compose__move_x:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_X
    clc
    adc.l SAME_SCUMM_CEL_XSTEP
    sta.l SAME_SCUMM_CEL_X
ScummV5_Cel_Compose__phase_x:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PIXEL_PHASE
    clc
    adc.l SAME_SCUMM_CEL_XSTEP
    and #$00FF
    sta.l SAME_SCUMM_CEL_PIXEL_PHASE
    lda.l SAME_SCUMM_CEL_LOOP
    inc
    sta.l SAME_SCUMM_CEL_LOOP
    jml ScummV5_Cel_Compose__pixel_loop
ScummV5_Cel_Compose__row_done:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PASS
    cmp #$0001
    bne ScummV5_Cel_Compose__next_span
    lda.l SAME_SCUMM_ACTOR_CLIP_RIGHT
    sec
    sbc.l SAME_SCUMM_ACTOR_CLIP_LEFT
    bcc ScummV5_Cel_Compose__next_span
    beq ScummV5_Cel_Compose__next_span
    tax
    lda.l SAME_SCUMM_CEL_Y
    xba
    ora.l SAME_SCUMM_ACTOR_CLIP_LEFT
    jsl Same_VideoSurface_CaptureActorRun_Far
    bcc ScummV5_Cel_Compose__next_span
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__next_span:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    inc
    sta.l SAME_SCUMM_ACTOR_SPAN_CURSOR
    lda.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    dec
    sta.l SAME_SCUMM_ACTOR_SPAN_REMAIN
    jml ScummV5_Cel_Compose__span
ScummV5_Cel_Compose__next_cel:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_CURSOR
    inc
    sta.l SAME_SCUMM_CEL_CURSOR
    lda.l SAME_SCUMM_CEL_REMAIN
    dec
    sta.l SAME_SCUMM_CEL_REMAIN
    jml ScummV5_Cel_Compose__cel
ScummV5_Cel_Compose__pass_done:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PASS
    beq ScummV5_Cel_Compose__validated
    cmp #$0001
    beq ScummV5_Cel_Compose__captured
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    rep #$20
    .a16
    lda.l SAME_SCUMM_CEL_CHUNK
    inc
    sta.l SAME_SCUMM_CEL_CHUNK
    cmp.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    bcs ScummV5_Cel_Compose__complete
    ; The checked provider is now free, but the surface transaction remains
    ; exclusive. A future service turn fetches the next immutable chunk.
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jml ScummV5_Cel_Compose__retry
ScummV5_Cel_Compose__validated:
    .a16
    .i16
    lda.l SAME_SCUMM_CEL_PIXEL
    cmp.l SAME_SCUMM_CEL_TOTAL_BYTES
    beq ScummV5_Cel_Compose__coverage_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__coverage_ok:
    .a16
    .i16
    jsl Same_VideoSurface_BeginActorUnderlay_Far
    bcc ScummV5_Cel_Compose__begin_ok
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__begin_ok:
    .a16
    .i16
    lda #$0001
    sta.l SAME_SCUMM_CEL_PASS
    jml ScummV5_Cel_Compose__pass
ScummV5_Cel_Compose__captured:
    .a16
    .i16
    jsl Same_VideoSurface_CommitActorUnderlay_Far
    bcc ScummV5_Cel_Compose__committed
    jml ScummV5_Cel_Compose__invalid
ScummV5_Cel_Compose__committed:
    .a16
    .i16
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_CEL_VALID
    rep #$20
    .a16
    lda #$0002
    sta.l SAME_SCUMM_CEL_PASS
    jml ScummV5_Cel_Compose__pass
ScummV5_Cel_Compose__complete:
    .a16
    .i16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CEL_VALID
    lda #$01
    sta.l SAME_SCUMM_ACTOR_POSE_COMPOSED
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cel_Compose__invalid:
    .a16
    .i16
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    lda #$FF
    sta.l SAME_SCUMM_ACTOR_POSE_STATE
    jsl ScummV5_ActorPose_ReleaseBuffer_Far
    ; No PRESENT is issued. A failed partial pose is never a visible image.
ScummV5_Cel_Compose__retry:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; Bind source cel and checked chunk directories before issuing any transfer.
; All logical chunk offsets are contiguous. Total bytes are an explicit u16
; contract, never a wrapped sum. No package pixel address becomes a CPU pointer.
ScummV5_Cel_Bind_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    lda #$0000
    sta.l SAME_SCUMM_CEL_CHUNK
    sta.l SAME_SCUMM_CEL_TOTAL_BYTES
    lda.l SAME_SCUMM_CEL_DESIRED_SCALE
    sta.l SAME_SCUMM_CEL_TICKET_SCALE
    lda.l SAME_SCUMM_ACTOR_POSE_ROW
    clc
    adc #$0013
    tax
    lda.l ScummV5_ActorPoseDirectory,x
    and #$00FE
    cmp #$0080
    beq ScummV5_Cel_Bind__format
    jml ScummV5_Cel_Bind__bad
ScummV5_Cel_Bind__format:
    .a16
    .i16
    lda.l ScummV5_ActorPoseDirectory,x
    and #$0001
    sep #$20
    .a8
    sta.l SAME_SCUMM_CEL_DIRECTION
    rep #$20
    .a16
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_CEL_FIRST
    inx
    inx
    lda.l ScummV5_ActorPoseDirectory,x
    sta.l SAME_SCUMM_CEL_COUNT
    clc
    adc.l SAME_SCUMM_CEL_FIRST
    bcs ScummV5_Cel_Bind__bad
    cmp #SCUMM_V5_ACTOR_CEL_COUNT
    bcc ScummV5_Cel_Bind__cels
    bne ScummV5_Cel_Bind__bad
ScummV5_Cel_Bind__cels:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_CHUNK_FIRST
    clc
    adc.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    bcs ScummV5_Cel_Bind__bad
    cmp #SCUMM_V5_ACTOR_CHUNK_COUNT
    bcc ScummV5_Cel_Bind__chunks
    bne ScummV5_Cel_Bind__bad
ScummV5_Cel_Bind__chunks:
    .a16
    .i16
    lda.l SAME_SCUMM_ACTOR_CHUNK_COUNT
    tay
    lda.l SAME_SCUMM_ACTOR_CHUNK_FIRST
    asl
    asl
    asl
    asl
    clc
    adc #$0008
    tax
ScummV5_Cel_Bind__loop:
    .a16
    .i16
    tya
    beq ScummV5_Cel_Bind__done
    lda.l ScummV5_ActorPoseChunkDirectory,x
    beq ScummV5_Cel_Bind__bad
    cmp #$0801
    bcs ScummV5_Cel_Bind__bad
    sta.l SAME_SCUMM_CEL_TEMP
    txa
    clc
    adc #$0006
    tax
    lda.l ScummV5_ActorPoseChunkDirectory,x
    cmp.l SAME_SCUMM_CEL_TOTAL_BYTES
    bne ScummV5_Cel_Bind__bad
    clc
    adc.l SAME_SCUMM_CEL_TEMP
    bcs ScummV5_Cel_Bind__bad
    sta.l SAME_SCUMM_CEL_TOTAL_BYTES
    txa
    clc
    adc #$000A
    tax
    dey
    bra ScummV5_Cel_Bind__loop
ScummV5_Cel_Bind__done:
    .a16
    .i16
    ply
    plx
    pla
    plp
    clc
    rtl
ScummV5_Cel_Bind__bad:
    .a16
    .i16
    ply
    plx
    pla
    plp
    sec
    rtl

; Room requests supersede actor work. Restore the captured background before
; releasing the composition fence; provider cancellation still drains its
; owned transfer before reusing scratch. No partial actor is published.
ScummV5_Cel_Abort_Far:
    .a16
    .i16
    php
    rep #$30
    .a16
    .i16
    pha
    lda.l SAME_SCUMM_CEL_VALID
    and #$00FF
    beq ScummV5_Cel_Abort__done
    jsl Same_VideoSurface_RestoreActorUnderlay_Far
    bcc ScummV5_Cel_Abort__restored
    sep #$20
    .a8
    lda #SCUMM_ERR_RESOURCE
    sta.l SAME_SCUMM_ERROR
    bra ScummV5_Cel_Abort__done
ScummV5_Cel_Abort__restored:
    .a16
    .i16
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_CEL_VALID
    rep #$20
    .a16
    lda #$0000
    sta.l SAME_SCUMM_CURSOR_COMPOSING
ScummV5_Cel_Abort__done:
    .a16
    .i16
    rep #$30
    .a16
    .i16
    pla
    plp
    rtl
