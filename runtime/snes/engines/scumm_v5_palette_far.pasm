; Generic classic-v5 palette producer. Included in visual bank 21 by the
; MSU live-room feature guard; no bank/origin directive or PPU ownership here.
; Generated BASE/DESIRED own 768 bytes each. STATE owns exactly 32 bytes:
; +00 valid, +01 pending (0 clean, 1 desired, 2 prepared),
; +02..06 RGB/first/last arguments, +07 padding,
; +08 index, +0A last, +0C RGB offset, +0E component, +10 multiplicand,
; +12 multiplier, +14 product, +16 bit count, +18 divide scratch (all u16),
; +1A..1F reserved.
; Scratch is synchronous S-CPU state, never NMI-owned.
; Every public entry preserves P/A/X/Y/DB, including carry.
SAME_SCUMM_PALETTE_VALID = SAME_SCUMM_ROOM_PALETTE_STATE+$00
SAME_SCUMM_PALETTE_PENDING = SAME_SCUMM_ROOM_PALETTE_STATE+$01
SAME_SCUMM_PALETTE_ARGS = SAME_SCUMM_ROOM_PALETTE_STATE+$02
SAME_SCUMM_PALETTE_INDEX = SAME_SCUMM_ROOM_PALETTE_STATE+$08
SAME_SCUMM_PALETTE_LAST = SAME_SCUMM_ROOM_PALETTE_STATE+$0A
SAME_SCUMM_PALETTE_OFFSET = SAME_SCUMM_ROOM_PALETTE_STATE+$0C
SAME_SCUMM_PALETTE_COMPONENT = SAME_SCUMM_ROOM_PALETTE_STATE+$0E
SAME_SCUMM_PALETTE_MULTIPLICAND = SAME_SCUMM_ROOM_PALETTE_STATE+$10
SAME_SCUMM_PALETTE_MULTIPLIER = SAME_SCUMM_ROOM_PALETTE_STATE+$12
SAME_SCUMM_PALETTE_PRODUCT = SAME_SCUMM_ROOM_PALETTE_STATE+$14
SAME_SCUMM_PALETTE_BITS = SAME_SCUMM_ROOM_PALETTE_STATE+$16
SAME_SCUMM_PALETTE_DIVIDE = SAME_SCUMM_ROOM_PALETTE_STATE+$18
SAME_SCUMM_PALETTE_DESIRED_BANK = SAME_SCUMM_ROOM_PALETTE_DESIRED / $10000

; Called after the checked room palette has been installed into the surface.
; Only this entry replaces BASE. Incoming preflight/staging never does.
ScummV5_Palette_InstallRoom_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld ; binary arithmetic; PLP restores the caller's decimal flag
    ldx #$0000
ScummV5_Palette_InstallRoom__copy:
    .a16
    .i16
    lda.l SAME_SCUMM_LIVE_ROOM_PALETTE_STAGE,x
    sta.l SAME_SCUMM_ROOM_PALETTE_BASE,x
    sta.l SAME_SCUMM_ROOM_PALETTE_DESIRED,x
    inx
    inx
    cpx #$0300
    bcc ScummV5_Palette_InstallRoom__copy
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_PALETTE_PENDING
    lda #$01
    sta.l SAME_SCUMM_PALETTE_VALID
    jmp ScummV5_Palette_Return

; Validated C10 palette operands are words; only their low bytes are RGB8.
ScummV5_Palette_SetColor_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld ; binary arithmetic; PLP restores the caller's decimal flag
    sep #$20
    .a8
    lda.l SAME_SCUMM_PALETTE_VALID
    bne ScummV5_Palette_SetColor__valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_SetColor__valid:
    rep #$20
    .a16
    lda.l SAME_SCUMM_C10_PARAM0
    cmp #$0100
    bcc ScummV5_Palette_SetColor__channel_0_valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_SetColor__channel_0_valid:
    .a16
    lda.l SAME_SCUMM_C10_PARAM1
    cmp #$0100
    bcc ScummV5_Palette_SetColor__channel_1_valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_SetColor__channel_1_valid:
    .a16
    lda.l SAME_SCUMM_C10_PARAM2
    cmp #$0100
    bcc ScummV5_Palette_SetColor__channel_2_valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_SetColor__channel_2_valid:
    .a16
    lda.l SAME_SCUMM_CONDITION
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_INDEX
    asl
    clc
    adc.l SAME_SCUMM_PALETTE_INDEX
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_C10_PARAM0
    sta.l SAME_SCUMM_ROOM_PALETTE_DESIRED,x
    lda.l SAME_SCUMM_C10_PARAM1
    sta.l SAME_SCUMM_ROOM_PALETTE_DESIRED+$01,x
    lda.l SAME_SCUMM_C10_PARAM2
    sta.l SAME_SCUMM_ROOM_PALETTE_DESIRED+$02,x
    lda #$01
    sta.l SAME_SCUMM_PALETTE_PENDING
    jmp ScummV5_Palette_Return

ScummV5_Palette_Intensity_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld ; binary arithmetic; PLP restores the caller's decimal flag
    sep #$20
    .a8
    lda.l SAME_SCUMM_PALETTE_VALID
    bne ScummV5_Palette_Intensity__valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_Intensity__valid:
    .a8
    ldx #$0000
ScummV5_Palette_Intensity__copy:
    .a8
    .i16
    lda.l SAME_SCUMM_C10_INTENSITY,x
    sta.l SAME_SCUMM_PALETTE_ARGS,x
    inx
    cpx #$0005
    bcc ScummV5_Palette_Intensity__copy
    jmp ScummV5_Palette_ApplyIntensity

ScummV5_Palette_RgbIntensity_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld ; binary arithmetic; PLP restores the caller's decimal flag
    sep #$20
    .a8
    lda.l SAME_SCUMM_PALETTE_VALID
    bne ScummV5_Palette_RgbIntensity__valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_RgbIntensity__valid:
    .a8
    ldx #$0000
ScummV5_Palette_RgbIntensity__copy:
    .a8
    .i16
    lda.l SAME_SCUMM_C10_RGB_INTENSITY,x
    sta.l SAME_SCUMM_PALETTE_ARGS,x
    inx
    cpx #$0005
    bcc ScummV5_Palette_RgbIntensity__copy

; Shared by the two public intensity entries; operands have already passed
; C10 validation. Reject reversed ranges defensively without publishing.
ScummV5_Palette_ApplyIntensity:
    rep #$30
    .a16
    .i16
    lda.l SAME_SCUMM_PALETTE_ARGS+$04
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_LAST
    lda.l SAME_SCUMM_PALETTE_ARGS+$03
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_INDEX
    cmp.l SAME_SCUMM_PALETTE_LAST
    bcc ScummV5_Palette_ApplyIntensity__color
    beq ScummV5_Palette_ApplyIntensity__color
    jmp ScummV5_Palette_Return
ScummV5_Palette_ApplyIntensity__color:
    .a16
    lda.l SAME_SCUMM_PALETTE_INDEX
    asl
    clc
    adc.l SAME_SCUMM_PALETTE_INDEX
    sta.l SAME_SCUMM_PALETTE_OFFSET
    lda #$0000
    sta.l SAME_SCUMM_PALETTE_COMPONENT
ScummV5_Palette_ApplyIntensity__component:
    .a16
    lda.l SAME_SCUMM_PALETTE_COMPONENT
    tax
    lda.l SAME_SCUMM_PALETTE_ARGS,x
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_MULTIPLIER
    txa
    clc
    adc.l SAME_SCUMM_PALETTE_OFFSET
    tax
    sep #$20
    .a8
    lda.l SAME_SCUMM_ROOM_PALETTE_BASE,x
    rep #$20
    .a16
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_MULTIPLICAND
    lda #$0000
    sta.l SAME_SCUMM_PALETTE_PRODUCT
    lda #$0008
    sta.l SAME_SCUMM_PALETTE_BITS
ScummV5_Palette_ApplyIntensity__multiply:
    .a16
    lda.l SAME_SCUMM_PALETTE_MULTIPLIER
    lsr
    sta.l SAME_SCUMM_PALETTE_MULTIPLIER
    bcc ScummV5_Palette_ApplyIntensity__no_add
    lda.l SAME_SCUMM_PALETTE_PRODUCT
    clc
    adc.l SAME_SCUMM_PALETTE_MULTIPLICAND
    sta.l SAME_SCUMM_PALETTE_PRODUCT
ScummV5_Palette_ApplyIntensity__no_add:
    .a16
    lda.l SAME_SCUMM_PALETTE_MULTIPLICAND
    asl
    sta.l SAME_SCUMM_PALETTE_MULTIPLICAND
    lda.l SAME_SCUMM_PALETTE_BITS
    dec
    sta.l SAME_SCUMM_PALETTE_BITS
    bne ScummV5_Palette_ApplyIntensity__multiply
    ; For 0 <= product <= 65025, floor(product/255) equals
    ; (product + 1 + (product >> 8)) >> 8, without 16-bit overflow.
    lda.l SAME_SCUMM_PALETTE_PRODUCT
    xba
    and #$00FF
    sta.l SAME_SCUMM_PALETTE_DIVIDE
    lda.l SAME_SCUMM_PALETTE_PRODUCT
    clc
    adc #$0001
    clc
    adc.l SAME_SCUMM_PALETTE_DIVIDE
    xba
    and #$00FF
    cmp #$00FD
    bcc ScummV5_Palette_ApplyIntensity__color_ready
    lda #$00FC
ScummV5_Palette_ApplyIntensity__color_ready:
    .a16
    pha
    lda.l SAME_SCUMM_PALETTE_OFFSET
    clc
    adc.l SAME_SCUMM_PALETTE_COMPONENT
    tax
    pla
    sep #$20
    .a8
    sta.l SAME_SCUMM_ROOM_PALETTE_DESIRED,x
    rep #$20
    .a16
    lda.l SAME_SCUMM_PALETTE_COMPONENT
    inc
    sta.l SAME_SCUMM_PALETTE_COMPONENT
    cmp #$0003
    bcs ScummV5_Palette_ApplyIntensity__next_color
    brl ScummV5_Palette_ApplyIntensity__component
ScummV5_Palette_ApplyIntensity__next_color:
    .a16
    lda.l SAME_SCUMM_PALETTE_INDEX
    cmp.l SAME_SCUMM_PALETTE_LAST
    beq ScummV5_Palette_ApplyIntensity__done
    inc
    sta.l SAME_SCUMM_PALETTE_INDEX
    brl ScummV5_Palette_ApplyIntensity__color
ScummV5_Palette_ApplyIntensity__done:
    sep #$20
    .a8
    lda #$01
    sta.l SAME_SCUMM_PALETTE_PENDING
    jmp ScummV5_Palette_Return

; Before actor/cursor composition: install desired colors without publishing
; or taking surface ownership. The subsequent scene PRESENT can carry them.
ScummV5_Palette_Prepare_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld ; binary arithmetic; PLP restores the caller's decimal flag
    sep #$20
    .a8
    lda.l SAME_SCUMM_PALETTE_VALID
    bne ScummV5_Palette_Prepare__valid
    jmp ScummV5_Palette_Return
ScummV5_Palette_Prepare__valid:
    .a8
    lda.l SAME_SCUMM_PALETTE_PENDING
    cmp #$01
    beq ScummV5_Palette_Prepare__desired
    jmp ScummV5_Palette_Return
ScummV5_Palette_Prepare__desired:
    .a8
    jsl Same_VideoSurface_CanWrite_Far
    bcc ScummV5_Palette_Prepare__writable
    jmp ScummV5_Palette_Return
ScummV5_Palette_Prepare__writable:
    sep #$20
    .a8
    lda #<SAME_SCUMM_ROOM_PALETTE_DESIRED
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE
    lda #>SAME_SCUMM_ROOM_PALETTE_DESIRED
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$01
    lda #SAME_SCUMM_PALETTE_DESIRED_BANK
    sta.l SAME_VIDEO_SURFACE_PALETTE_SOURCE+$02
    jsl Same_VideoSurface_InstallPalette_Far
    bcc ScummV5_Palette_Prepare__installed
    jmp ScummV5_Palette_Return
ScummV5_Palette_Prepare__installed:
    sep #$20
    .a8
    lda #$02
    sta.l SAME_SCUMM_PALETTE_PENDING
    jmp ScummV5_Palette_Return

; After completed actor/cursor composition and service drain (caller guards
; unfinished composition). The service owns dirty colors until PRESENT enqueue
; succeeds; generation changes alone never acknowledge palette publication.
; Calling Flush alone still performs preparation and publication in order.
ScummV5_Palette_Flush_Far:
    php
    rep #$30
    .a16
    .i16
    pha
    phx
    phy
    phb
    cld
    jsl ScummV5_Palette_Prepare_Far
    sep #$20
    .a8
    lda.l SAME_SCUMM_PALETTE_VALID
    beq ScummV5_Palette_Return
    lda.l SAME_SCUMM_PALETTE_PENDING
    cmp #$02
    bne ScummV5_Palette_Return
    lda.l SAME_VIDEO_SURFACE_PALETTE_DIRTY
    beq ScummV5_Palette_Flush__included
    jsl Same_VideoSurface_CanWrite_Far
    bcs ScummV5_Palette_Return
    sep #$20
    .a8
    lda.l SAME_SCUMM_M23A_ACTIVE_ROOM
    jsl Same_VideoSurface_PushPalettePresent_Far
    bcc ScummV5_Palette_Flush__included
    jmp ScummV5_Palette_Return
ScummV5_Palette_Flush__included:
    sep #$20
    .a8
    lda #$00
    sta.l SAME_SCUMM_PALETTE_PENDING
ScummV5_Palette_Return:
    rep #$30
    .a16
    .i16
    plb
    ply
    plx
    pla
    plp
    rtl
